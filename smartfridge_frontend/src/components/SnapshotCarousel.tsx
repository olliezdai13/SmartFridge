import { useEffect, useMemo, useRef, useState } from 'react'
import SnapshotCard, { type Snapshot } from './SnapshotCard'

type SnapshotCarouselProps = {
  snapshots: Snapshot[]
  hasMore?: boolean
  loadingMore?: boolean
  onRequestMore?: () => void
}

function SnapshotCarousel({
  snapshots,
  hasMore = false,
  loadingMore = false,
  onRequestMore,
}: SnapshotCarouselProps) {
  const orderedSnapshots = useMemo(() => [...snapshots].reverse(), [snapshots])
  const [activeIndex, setActiveIndex] = useState(0)
  const [initialized, setInitialized] = useState(false)
  const [pendingAdvanceIndex, setPendingAdvanceIndex] = useState<number | null>(null)
  const [loadedSnapshots, setLoadedSnapshots] = useState<Record<string, boolean>>({})
  const [readySnapshots, setReadySnapshots] = useState<Record<string, boolean>>({})

  const maxIndex = Math.max(orderedSnapshots.length - 1, 0)
  const currentIndex = Math.min(activeIndex, maxIndex)
  const canGoPrev = currentIndex > 0 || (hasMore && !loadingMore)
  const canGoNext = currentIndex < maxIndex

  const prevLengthRef = useRef(orderedSnapshots.length)

  useEffect(() => {
    const prevLength = prevLengthRef.current
    const grewBy = orderedSnapshots.length - prevLength

    if (!initialized && orderedSnapshots.length > 0) {
      setActiveIndex(orderedSnapshots.length - 1)
      setInitialized(true)
    } else if (pendingAdvanceIndex !== null && orderedSnapshots.length > pendingAdvanceIndex) {
      setActiveIndex(pendingAdvanceIndex)
      setPendingAdvanceIndex(null)
    } else if (grewBy > 0 && pendingAdvanceIndex === null) {
      setActiveIndex((prev) => Math.min(prev + grewBy, Math.max(orderedSnapshots.length - 1, 0)))
    }

    if (activeIndex > Math.max(orderedSnapshots.length - 1, 0)) {
      setActiveIndex(Math.max(orderedSnapshots.length - 1, 0))
    }

    prevLengthRef.current = orderedSnapshots.length
  }, [activeIndex, initialized, orderedSnapshots.length, pendingAdvanceIndex])

  useEffect(() => {
    setLoadedSnapshots((prev) => {
      // Drop entries for snapshots no longer present to keep the map small.
      const next: Record<string, boolean> = {}
      orderedSnapshots.forEach((snapshot) => {
        if (prev[snapshot.id]) {
          next[snapshot.id] = true
        }
      })
      const sameSize = Object.keys(next).length === Object.keys(prev).length
      if (sameSize && Object.keys(next).every((key) => prev[key])) {
        return prev
      }
      return next
    })
  }, [orderedSnapshots])
  useEffect(() => {
    setReadySnapshots((prev) => {
      const next: Record<string, boolean> = {}
      orderedSnapshots.forEach((snapshot) => {
        if (prev[snapshot.id]) {
          next[snapshot.id] = true
        }
      })
      return next
    })
  }, [orderedSnapshots])
  const handleImageLoad = (snapshotId: string) => {
    setLoadedSnapshots((prev) => (prev[snapshotId] ? prev : { ...prev, [snapshotId]: true }))
  }

  const handlePrev = () => {
    if (currentIndex > 0) {
      setActiveIndex((prev) => Math.max(Math.min(prev, maxIndex) - 1, 0))
      return
    }
    if (hasMore && !loadingMore) {
      setPendingAdvanceIndex(0)
      onRequestMore?.()
    }
  }

  const handleNext = () => {
    if (currentIndex < maxIndex) {
      setActiveIndex((prev) => Math.min(Math.min(prev, maxIndex) + 1, maxIndex))
    }
  }

  useEffect(() => {
    const activeSnapshot = orderedSnapshots[currentIndex]
    if (!activeSnapshot) return
    setReadySnapshots((prev) =>
      prev[activeSnapshot.id] ? prev : { ...prev, [activeSnapshot.id]: true },
    )
  }, [currentIndex, orderedSnapshots])

  if (orderedSnapshots.length === 0) {
    return (
      <div className="surface">
        <p className="muted">No snapshots available yet.</p>
      </div>
    )
  }

  return (
    <section className="snapshot-carousel" aria-label="Fridge snapshot carousel">
      <div className="carousel-header">
        <div className="carousel-copy">
          <h2 className="section-heading">Latest fridge pictures</h2>
          <p className="muted">
            Flip through the most recent uploads to see how contents shifted between snapshots.
          </p>
        </div>
      </div>

      <div className="carousel-stage">
        <button
          type="button"
          className="carousel-nav prev"
          aria-label="View previous snapshot"
          onClick={handlePrev}
          disabled={!canGoPrev}
        >
          ‹
        </button>
        <div
          className="carousel-track"
          style={{ transform: `translateX(-${currentIndex * 100}%)` }}
          aria-live="polite"
        >
          {orderedSnapshots.map((snapshot, index) => (
            <div className="carousel-slide" key={snapshot.id}>
              <SnapshotCard
                snapshot={snapshot}
                isActive={index === currentIndex}
                shouldLoadImage={Boolean(readySnapshots[snapshot.id])}
                isLoaded={Boolean(loadedSnapshots[snapshot.id])}
                onImageLoad={handleImageLoad}
              />
            </div>
          ))}
        </div>
        <button
          type="button"
          className="carousel-nav next"
          aria-label="View next snapshot"
          onClick={handleNext}
          disabled={!canGoNext}
        >
          ›
        </button>
      </div>

      {loadingMore && (
        <p className="muted" aria-live="polite">
          Loading more snapshots...
        </p>
      )}

      <div className="carousel-progress" aria-hidden="true">
        {orderedSnapshots.map((snapshot, index) => (
          <span
            key={snapshot.id}
            className={index === currentIndex ? 'progress-dot active' : 'progress-dot'}
          />
        ))}
      </div>
    </section>
  )
}

export default SnapshotCarousel
