import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Area,
  AreaChart,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Rectangle,
  type RectangleProps,
  type BarProps,
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

const CATEGORY_ORDER: string[] = [
  'PROCESSED_FOODS',
  'FATS_OILS',
  'PROTEIN_FOODS',
  'DAIRY',
  'GRAINS_STARCH',
  'FRUITS_VEGETABLES',
  'OTHER',
]

const sortByPreferredCategory = (a: string, b: string) => {
  const indexA = CATEGORY_ORDER.indexOf(a)
  const indexB = CATEGORY_ORDER.indexOf(b)

  if (indexA === -1 && indexB === -1) return a.localeCompare(b)
  if (indexA === -1) return 1
  if (indexB === -1) return -1

  return indexA - indexB
}

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
  const [snapshots, setSnapshots] = useState<CompositionSnapshot[]>([])
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
          return aTime - bTime
        })
        setCategoryLabels(response.categoryLabels ?? {})
        setSnapshots(sorted)
        setSnapshot(sorted[sorted.length - 1] ?? null)
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

  const categoryKeys = useMemo(() => {
    const labelKeys = Object.keys(categoryLabels ?? {})
    if (labelKeys.length > 0) return [...labelKeys].sort(sortByPreferredCategory)

    const seen = new Set<string>()
    snapshots.forEach((entry) =>
      entry.categoryCounts.forEach((category) => {
        seen.add(category.category)
      }),
    )

    return Array.from(seen).sort(sortByPreferredCategory)
  }, [categoryLabels, snapshots])

  const chartData: ChartDatum[] = useMemo(() => {
    const keys = categoryKeys
    if (keys.length === 0 || !snapshot) return []

    const counts = new Map<string, number>()
    keys.forEach((key) => counts.set(key, 0))

    snapshot.categoryCounts.forEach((entry) => {
      const current = counts.get(entry.category) ?? 0
      counts.set(entry.category, current + (Number.isFinite(entry.count) ? entry.count : 0))
    })

    return keys.map((key) => ({
      name: categoryLabels[key] ?? key,
      value: counts.get(key) ?? 0,
    }))
  }, [categoryLabels, categoryKeys, snapshot])

  const centeredBarDomain: [number, number] = useMemo(() => {
    if (chartData.length === 0) return [-1, 1]
    const maxValue = chartData.reduce((max, entry) => Math.max(max, entry.value), 0)
    const safeMax = Math.max(maxValue, 1)
    return [-safeMax, safeMax]
  }, [chartData])

  const areaSeries = useMemo(
    () =>
      categoryKeys.map((key, index) => {
        const palette = [
          '#0f7f93',
          '#f29f05',
          '#5b8def',
          '#ed5f76',
          '#7cc47f',
          '#9d7dd8',
          '#f2c94c',
          '#5f6a86',
          '#0ba49d',
        ]
        return {
          key,
          label: categoryLabels[key] ?? key,
          color: palette[index % palette.length],
        }
      }),
    [categoryKeys, categoryLabels],
  )

  const stackedAreaData = useMemo(() => {
    if (snapshots.length === 0 || categoryKeys.length === 0) return []

    return snapshots.map((entry, index) => {
      const counts = new Map<string, number>()
      categoryKeys.forEach((key) => counts.set(key, 0))

      entry.categoryCounts.forEach((category) => {
        const current = counts.get(category.category) ?? 0
        counts.set(
          category.category,
          current + (Number.isFinite(category.count) ? category.count : 0),
        )
      })

      const parsed = new Date(entry.timestamp)
      const displayLabel = Number.isNaN(parsed.getTime())
        ? `Snapshot ${index + 1}`
        : parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

      const row: Record<string, number | string> = {
        snapshotId: entry.snapshotId,
        name: displayLabel,
        timestamp: entry.timestamp,
      }

      categoryKeys.forEach((key) => {
        row[key] = counts.get(key) ?? 0
      })

      return row
    })
  }, [snapshots, categoryKeys])

  const capturedLabel = formatCapturedAt(snapshot?.timestamp)
  const hasData = chartData.length > 0
  const hasHistory = stackedAreaData.length > 0

  const renderCenteredBar: BarProps['shape'] = (props: any) => {
    const { x = 0, y = 0, width = 0, height = 0, radius } = (props ?? {}) as RectangleProps
    const centeredX = x - width / 2
    return (
      <Rectangle
        {...(props as RectangleProps)}
        x={centeredX}
        y={y}
        width={width}
        height={height}
        radius={radius}
      />
    )
  }

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
                    <XAxis
                      type="number"
                      domain={centeredBarDomain}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(value) => String(Math.abs(Number(value)))}
                    />
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
                    <ReferenceLine x={0} stroke="#dfe4ed" strokeWidth={2} />
                    <Bar
                      dataKey="value"
                      radius={[6, 6, 6, 6]}
                      fill="#0f7f93"
                      shape={renderCenteredBar}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="muted">No items found in the latest snapshot.</p>
            )}
          </div>
        )}
      </div>

      {!loading && !error && snapshot && (
        <div className="surface stats-chart">
          <div className="chart-shell">
            <div className="chart-title-row">
              <div>
                <p className="muted">History across snapshots</p>
                <h3 className="card-title">Ingredient composition over time</h3>
              </div>
            </div>

            {hasHistory ? (
              <div className="chart-area">
                <ResponsiveContainer width="100%" height={360}>
                  <AreaChart
                    data={stackedAreaData}
                    margin={{ top: 12, right: 24, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" tickLine={false} axisLine={false} />
                    <YAxis tickLine={false} axisLine={false} />
                    <Tooltip
                      labelFormatter={(label, payload) => {
                        const ts = (payload?.[0]?.payload as { timestamp?: string } | undefined)
                          ?.timestamp
                        const parsed = ts ? new Date(ts) : null
                        if (parsed && !Number.isNaN(parsed.getTime())) {
                          return `Captured ${parsed.toLocaleString()}`
                        }
                        return `Snapshot ${label}`
                      }}
                      contentStyle={{
                        borderRadius: 12,
                        border: '1px solid #dfe4ed',
                        boxShadow: '0 12px 30px -20px rgba(13, 24, 59, 0.3)',
                      }}
                    />
                    <Legend />
                    {areaSeries.map((series) => (
                      <Area
                        key={series.key}
                        type="monotone"
                        dataKey={series.key}
                        name={series.label}
                        stackId="composition"
                        stroke={series.color}
                        fill={series.color}
                        fillOpacity={0.22}
                        strokeWidth={2}
                        activeDot={{ r: 4 }}
                      />
                    ))}
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="muted">More snapshots needed to chart your history.</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
