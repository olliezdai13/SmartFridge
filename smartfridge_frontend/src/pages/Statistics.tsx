import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { apiClient } from '../api'

type CompositionCategoryCount = {
  category: string
  label?: string | null
  count: number
}

type CompositionSnapshot = {
  snapshotId: string
  timestamp: string
  categoryCounts: CompositionCategoryCount[]
  totalItems: number
}

type CompositionResponse = {
  categoryLabels: Record<string, string>
  snapshots: CompositionSnapshot[]
}

type ChartDatum = { name: string; value: number }

const formatCapturedAt = (timestamp?: string) => {
  if (!timestamp) return 'Latest snapshot'
  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) return 'Latest snapshot'
  return `Captured ${parsed.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })}`
}

export default function Statistics() {
  const [snapshot, setSnapshot] = useState<CompositionSnapshot | null>(null)
  const [categoryLabels, setCategoryLabels] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const fetchComposition = async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await apiClient.request<CompositionResponse>(
          '/statistics/ingredient_composition',
        )
        if (cancelled) return
        const sorted = [...(response.snapshots ?? [])].sort((a, b) => {
          const aTime = new Date(a.timestamp).getTime() || 0
          const bTime = new Date(b.timestamp).getTime() || 0
          return bTime - aTime
        })
        setCategoryLabels(response.categoryLabels ?? {})
        setSnapshot(sorted[0] ?? null)
      } catch (err) {
        if (cancelled) return
        const message = err instanceof Error ? err.message : 'Failed to load statistics'
        setError(message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void fetchComposition()

    return () => {
      cancelled = true
    }
  }, [])

  const chartData: ChartDatum[] = useMemo(() => {
    const keys =
      Object.keys(categoryLabels).length > 0
        ? Object.keys(categoryLabels)
        : snapshot?.categoryCounts.map((entry) => entry.category) ?? []

    if (keys.length === 0) return []

    const counts = new Map<string, number>()
    keys.forEach((key) => counts.set(key, 0))

    snapshot?.categoryCounts.forEach((entry) => {
      const current = counts.get(entry.category) ?? 0
      counts.set(entry.category, current + (Number.isFinite(entry.count) ? entry.count : 0))
    })

    return keys.map((key) => ({
      name: categoryLabels[key] ?? key,
      value: counts.get(key) ?? 0,
    }))
  }, [categoryLabels, snapshot])

  const capturedLabel = formatCapturedAt(snapshot?.timestamp)
  const hasData = chartData.length > 0

  return (
    <div className="statistics">
      <div className="surface stats-header">
        <h1 className="section-heading">Fridge statistics</h1>
        <p className="muted">
          Composition of your latest snapshot. Category totals come straight from the most recent
          upload.
        </p>
      </div>

      <div className="surface stats-chart">
        {loading && <p className="muted">Loading latest snapshot...</p>}
        {error && <p className="error-text">{error}</p>}
        {!loading && !error && !snapshot && <p className="muted">No snapshots available yet.</p>}

        {!loading && !error && snapshot && (
          <div className="chart-shell">
            <div className="chart-title-row">
              <div>
                <p className="muted">{capturedLabel}</p>
                <h3 className="card-title">Items per category</h3>
              </div>
            </div>

            {hasData ? (
              <div className="chart-area">
                <ResponsiveContainer width="100%" height={380}>
                  <BarChart
                    data={chartData}
                    layout="vertical"
                    margin={{ top: 12, right: 24, left: 12, bottom: 8 }}
                    barSize={24}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis type="number" axisLine={false} tickLine={false} />
                    <YAxis
                      dataKey="name"
                      type="category"
                      axisLine={false}
                      tickLine={false}
                      width={140}
                    />
                    <Tooltip
                      cursor={{ fill: 'rgba(15, 127, 147, 0.08)' }}
                      contentStyle={{
                        borderRadius: 12,
                        border: '1px solid #dfe4ed',
                        boxShadow: '0 12px 30px -20px rgba(13, 24, 59, 0.3)',
                      }}
                    />
                    <Bar dataKey="value" radius={[6, 6, 6, 6]} fill="#0f7f93" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="muted">No items found in the latest snapshot.</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
