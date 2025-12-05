import type { CSSProperties } from 'react'

export type SnapshotContent = {
  name: string
  quantity: number
  category?: string | null
  categoryLabel?: string | null
}

export type Snapshot = {
  id: string
  timestamp: string
  imageUrl: string
  contents: SnapshotContent[]
}

const transparentPixel = 'data:image/gif;base64,R0lGODlhAQABAAAAACw='

type ProductCategoryKey =
  | 'FRUITS_VEGETABLES'
  | 'GRAINS_STARCH'
  | 'DAIRY'
  | 'PROTEIN_FOODS'
  | 'FATS_OILS'
  | 'PROCESSED_FOODS'
  | 'OTHER'

type CategoryStyle = {
  label: string
  background: string
  border: string
  chipBg: string
  chipText: string
  dot: string
  shadow: string
}

type CategoryCSSVars = Record<`--${string}`, string>

const CATEGORY_STYLES: Record<ProductCategoryKey, CategoryStyle> = {
  FRUITS_VEGETABLES: {
    label: 'Fruits & Veggies',
    background: '#eef8f1',
    border: '#c6e6cf',
    chipBg: '#e4f4e8',
    chipText: '#0f7f5c',
    dot: '#1c9a6c',
    shadow: 'rgba(17, 128, 95, 0.12)',
  },
  GRAINS_STARCH: {
    label: 'Grains & Starch',
    background: '#fff5e9',
    border: '#f3d9b8',
    chipBg: '#ffeed9',
    chipText: '#a05a11',
    dot: '#d47a1b',
    shadow: 'rgba(212, 122, 27, 0.12)',
  },
  DAIRY: {
    label: 'Dairy',
    background: '#e9f4ff',
    border: '#c8def3',
    chipBg: '#e2f0fb',
    chipText: '#0f6fa4',
    dot: '#1f8bcc',
    shadow: 'rgba(31, 139, 204, 0.12)',
  },
  PROTEIN_FOODS: {
    label: 'Protein',
    background: '#fff0ed',
    border: '#f4c9be',
    chipBg: '#ffe5df',
    chipText: '#b23b1f',
    dot: '#d15639',
    shadow: 'rgba(209, 86, 57, 0.12)',
  },
  FATS_OILS: {
    label: 'Fats & Oils',
    background: '#fffae5',
    border: '#f0e3aa',
    chipBg: '#fff6cf',
    chipText: '#9a810b',
    dot: '#c7a418',
    shadow: 'rgba(201, 164, 24, 0.12)',
  },
  PROCESSED_FOODS: {
    label: 'Processed',
    background: '#f4f0ff',
    border: '#d8cff3',
    chipBg: '#ede7ff',
    chipText: '#5a3ca5',
    dot: '#7a5ed1',
    shadow: 'rgba(122, 94, 209, 0.12)',
  },
  OTHER: {
    label: 'Other',
    background: '#f3f6fb',
    border: '#dbe3ef',
    chipBg: '#edf1f8',
    chipText: '#3b4c6b',
    dot: '#4f6b95',
    shadow: 'rgba(79, 107, 149, 0.12)',
  },
}

const DEFAULT_CATEGORY_STYLE: CategoryStyle = {
  label: 'Uncategorized',
  background: '#f5f7fb',
  border: '#dfe4ed',
  chipBg: '#eef2f8',
  chipText: '#37455f',
  dot: '#6c7a94',
  shadow: 'rgba(108, 122, 148, 0.12)',
}

const getCategoryStyle = (
  category?: string | null,
  categoryLabel?: string | null,
): CategoryStyle => {
  const normalized = (category || '').trim().toUpperCase() as ProductCategoryKey
  const baseStyle = CATEGORY_STYLES[normalized] ?? DEFAULT_CATEGORY_STYLE
  const hasPresetStyle = Boolean(CATEGORY_STYLES[normalized])
  const resolvedLabel = hasPresetStyle
    ? baseStyle.label
    : (categoryLabel || '').trim() || baseStyle.label
  return { ...baseStyle, label: resolvedLabel }
}

const categoryStyleToVars = (style: CategoryStyle): CSSProperties & CategoryCSSVars => ({
  '--category-bg': style.background,
  '--category-border': style.border,
  '--category-chip-bg': style.chipBg,
  '--category-chip-text': style.chipText,
  '--category-dot': style.dot,
  '--category-shadow': style.shadow,
})

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
            <p className="muted">Analyzing fridge contents...</p>
          </div>
        ) : (
          <ul className="inventory-list" aria-label="Latest fridge contents">
            {snapshot.contents.map((item) => {
              const style = getCategoryStyle(item.category, item.categoryLabel)
              const styleVars = categoryStyleToVars(style)
              return (
                <li
                  key={item.name}
                  className="inventory-row"
                  style={styleVars}
                  aria-label={`${item.name} in ${style.label}`}
                >
                  <div className="inventory-name">
                    <span className="inventory-category">
                      <span className="inventory-category-dot" aria-hidden="true" />
                      {style.label}
                    </span>
                    <span className="inventory-label">{item.name}</span>
                  </div>
                  <div className="inventory-qty" aria-label={`Quantity of ${item.name}`}>
                    <span>{item.quantity}</span>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </article>
  )
}

export default SnapshotCard
