import { useCallback, useEffect, useState } from 'react'
import { apiClient } from '../api'
import SnapshotCarousel from '../components/SnapshotCarousel'
import type { Snapshot } from '../components/SnapshotCard'

const SNAPSHOT_PAGE_SIZE = 5

type SnapshotResponse = {
  snapshots: Snapshot[]
  hasMore?: boolean
  nextOffset?: number
}

// const mockSnapshots: Snapshot[] = [...]

function Dashboard() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(true)
  const [nextOffset, setNextOffset] = useState(0)

  const applyResponse = useCallback((response: SnapshotResponse, offset: number) => {
    const received = response.snapshots ?? []
    setSnapshots((prev) => {
      const merged = offset === 0 ? received : [...prev, ...received]
      return [...merged].sort((a, b) => {
        const aTime = new Date(a.timestamp).getTime() || 0
        const bTime = new Date(b.timestamp).getTime() || 0
        return bTime - aTime
      })
    })
    const calculatedNextOffset = response.nextOffset ?? offset + received.length
    setNextOffset(calculatedNextOffset)
    setHasMore(response.hasMore ?? received.length === SNAPSHOT_PAGE_SIZE)
  }, [])

  const loadInitialSnapshots = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.request<SnapshotResponse>(
        `/snapshots?limit=${SNAPSHOT_PAGE_SIZE}&offset=0`,
      )
      applyResponse(response, 0)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load snapshots'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [applyResponse])

  const loadMoreSnapshots = useCallback(async () => {
    if (loading || loadingMore || !hasMore) return
    setLoadingMore(true)
    try {
      const response = await apiClient.request<SnapshotResponse>(
        `/snapshots?limit=${SNAPSHOT_PAGE_SIZE}&offset=${nextOffset}`,
      )
      applyResponse(response, nextOffset)
      setError(null)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load more snapshots'
      setError(message)
    } finally {
      setLoadingMore(false)
    }
  }, [applyResponse, hasMore, loading, loadingMore, nextOffset])

  useEffect(() => {
    loadInitialSnapshots()
  }, [loadInitialSnapshots])

  return (
    <section className="surface dashboard">
      {loading && <p className="muted">Loading snapshots...</p>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && (
        <SnapshotCarousel
          snapshots={snapshots}
          hasMore={hasMore}
          loadingMore={loadingMore}
          onRequestMore={loadMoreSnapshots}
        />
      )}
    </section>
  )
}

export default Dashboard
