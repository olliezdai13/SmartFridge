export type SnapshotContent = {
  name: string
  quantity: number
}

export type Snapshot = {
  id: string
  timestamp: string
  imageUrl: string
  contents: SnapshotContent[]
}

const transparentPixel = 'data:image/gif;base64,R0lGODlhAQABAAAAACw='

const getTimeOfDayLabel = (date: Date) => {
  const hour = date.getHours()
  if (hour < 5) return 'Late Night'
  if (hour < 12) return 'Morning'
  if (hour < 17) return 'Afternoon'
  if (hour < 21) return 'Evening'
  return 'Night'
}

const formatTime = (date: Date) =>
  new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)

const formatCapturedAt = (date: Date) => {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMinutes = Math.round(diffMs / 60000)

  if (diffMinutes < 1) {
    return 'Captured just now'
  }
  if (diffMinutes < 60) {
    const label = diffMinutes === 1 ? 'minute' : 'minutes'
    return `Captured ${diffMinutes} ${label} ago`
  }

  const diffHours = Math.round(diffMinutes / 60)
  if (diffHours < 24) {
    return `Captured ${diffHours}h ago`
  }

  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  if (date.toDateString() === yesterday.toDateString()) {
    return `Captured yesterday at ${formatTime(date)}`
  }

  return `Captured ${date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })} at ${formatTime(date)}`
}

type SnapshotCardProps = {
  snapshot: Snapshot
  isActive?: boolean
  isLoaded?: boolean
  shouldLoadImage?: boolean
  onImageLoad?: (snapshotId: string) => void
}

function SnapshotCard({
  snapshot,
  isActive = false,
  isLoaded = false,
  shouldLoadImage = false,
  onImageLoad,
}: SnapshotCardProps) {
  const parsedDate = new Date(snapshot.timestamp)
  const hasValidDate = !Number.isNaN(parsedDate.getTime())
  const timeOfDay = hasValidDate ? getTimeOfDayLabel(parsedDate) : 'Recent'
  const displayTitle = `Fridge • ${timeOfDay} Snapshot`
  const capturedAt = hasValidDate ? formatCapturedAt(parsedDate) : 'Captured recently'
  const isLoadingContents = snapshot.contents.length === 0
  const loadingMode: 'lazy' | 'eager' = isActive ? 'eager' : 'lazy'
  const shouldShowImage = shouldLoadImage || isLoaded
  const imgSrc = shouldShowImage ? snapshot.imageUrl : transparentPixel

  return (
    <article className="snapshot-card" aria-label={`${displayTitle} snapshot`}>
      <div className="snapshot-image">
        <img
          src={imgSrc}
          alt={`${displayTitle} view`}
          loading={loadingMode}
          onLoad={() => {
            if (shouldShowImage) {
              onImageLoad?.(snapshot.id)
            }
          }}
        />
        <div className="snapshot-chip">{capturedAt}</div>
      </div>

      <div className="snapshot-details">
        <div className="snapshot-details-header">
          <h3 className="snapshot-title">{displayTitle}</h3>
        </div>

        {isLoadingContents ? (
          <div className="inventory-loading" role="status" aria-live="polite">
            <div className="loading-spinner" aria-hidden="true" />
            <p className="muted">Parsing items from this snapshot...</p>
          </div>
        ) : (
          <ul className="inventory-list" aria-label="Latest fridge contents">
            {snapshot.contents.map((item) => (
              <li key={item.name} className="inventory-row">
                <div className="inventory-name">
                  {item.name}
                </div>
                <div className="inventory-qty">
                  <span>{item.quantity}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </article>
  )
}

export default SnapshotCard
