import { useEffect, useState } from 'react'
import SnapshotCard, { type Snapshot } from './SnapshotCard'

type SnapshotCarouselProps = {
  snapshots: Snapshot[]
}

function SnapshotCarousel({ snapshots }: SnapshotCarouselProps) {
  const orderedSnapshots = [...snapshots].reverse()
  const [activeIndex, setActiveIndex] = useState(() => Math.max(orderedSnapshots.length - 1, 0))
  useEffect(() => {
    setActiveIndex(Math.max(orderedSnapshots.length - 1, 0))
  }, [orderedSnapshots.length])
  const maxIndex = Math.max(orderedSnapshots.length - 1, 0)
  const currentIndex = Math.min(activeIndex, maxIndex)
  const canGoPrev = currentIndex > 0
  const canGoNext = currentIndex < maxIndex

  const handlePrev = () => {
    if (canGoPrev) {
      setActiveIndex((prev) => Math.max(Math.min(prev, maxIndex) - 1, 0))
    }
  }

  const handleNext = () => {
    if (canGoNext) {
      setActiveIndex((prev) => Math.min(Math.min(prev, maxIndex) + 1, maxIndex))
    }
  }

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
          {orderedSnapshots.map((snapshot) => (
            <div className="carousel-slide" key={snapshot.id}>
              <SnapshotCard snapshot={snapshot} />
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
