export type SnapshotContent = {
  name: string
  quantity: number
}

export type Snapshot = {
  id: string
  title: string
  capturedAt: string
  imageUrl: string
  contents: SnapshotContent[]
}

type SnapshotCardProps = {
  snapshot: Snapshot
}

function SnapshotCard({ snapshot }: SnapshotCardProps) {
  return (
    <article className="snapshot-card" aria-label={`${snapshot.title} snapshot`}>
      <div className="snapshot-image">
        <img src={snapshot.imageUrl} alt={`${snapshot.title} view`} loading="lazy" />
        <div className="snapshot-chip">{snapshot.capturedAt}</div>
      </div>

      <div className="snapshot-details">
        <div className="snapshot-details-header">
          <h3 className="snapshot-title">{snapshot.title}</h3>
        </div>

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
      </div>
    </article>
  )
}

export default SnapshotCard
