import { useEffect, useState } from 'react'
import { apiClient } from '../api'
import SnapshotCarousel from '../components/SnapshotCarousel'
import type { Snapshot } from '../components/SnapshotCard'

// const mockSnapshots: Snapshot[] = [...]

function Dashboard() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const fetchSnapshots = async () => {
      try {
        const response = await apiClient.request<{ snapshots: Snapshot[] }>('/snapshots')
        if (!cancelled) {
          setSnapshots(response.snapshots ?? [])
          setError(null)
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Failed to load snapshots'
          setError(message)
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }
    fetchSnapshots()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <section className="surface dashboard">
      {loading && <p className="muted">Loading snapshots...</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && <SnapshotCarousel snapshots={snapshots} />}
    </section>
  )
}

export default Dashboard
