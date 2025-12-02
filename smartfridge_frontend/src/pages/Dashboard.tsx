type PhotoPlaceholder = {
  id: number
  title: string
  description: string
  timestamp: string
  freshness: string
}

const mockPhotos: PhotoPlaceholder[] = [
  {
    id: 1,
    title: 'Fridge door camera',
    description: 'Most recent snapshot of shelf contents.',
    timestamp: 'Updated just now',
    freshness: 'Awaiting analysis',
  },
  {
    id: 2,
    title: 'Produce drawer',
    description: 'Produce bin visibility placeholder.',
    timestamp: 'Updated 2h ago',
    freshness: 'Detecting freshness',
  },
  {
    id: 3,
    title: 'Freezer overview',
    description: 'Freezer photo placeholder.',
    timestamp: 'Updated yesterday',
    freshness: 'Queued for upload',
  },
]

function Dashboard() {
  return (
    <section className="surface">
      <header>
        <h1 className="section-heading">Dashboard</h1>
        <p className="muted">Stay on top of the latest fridge pictures and freshness insights.</p>
      </header>

      <div className="grid" role="list">
        {mockPhotos.map((photo) => (
          <article key={photo.id} className="card" role="listitem" aria-label={photo.title}>
            <div className="photo-placeholder" aria-hidden="true" />
            <div className="card-body">
              <div className="pill secondary">{photo.freshness}</div>
              <h3 className="card-title">{photo.title}</h3>
              <p className="muted">{photo.description}</p>
              <span className="meta">{photo.timestamp}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

export default Dashboard
