import SnapshotCarousel from '../components/SnapshotCarousel'
import type { Snapshot } from '../components/SnapshotCard'

const minutesAgoTimestamp = (minutes: number) =>
  new Date(Date.now() - minutes * 60 * 1000).toISOString()

const yesterdayAtTimestamp = (hour: number, minute: number) => {
  const date = new Date()
  date.setDate(date.getDate() - 1)
  date.setHours(hour, minute, 0, 0)
  return date.toISOString()
}

const mockSnapshots: Snapshot[] = [
  {
    id: 'snapshot-1',
    timestamp: minutesAgoTimestamp(8),
    imageUrl:
      'https://images.unsplash.com/photo-1582719478248-52c9c1f4e5f3?auto=format&fit=crop&w=1200&q=80',
    contents: [
      { name: 'Oat milk', quantity: 2 },
      { name: 'Greek yogurt', quantity: 3 },
      { name: 'Berry jam', quantity: 1 },
      { name: 'Fresh herbs', quantity: 1 },
    ],
  },
  {
    id: 'snapshot-2',
    timestamp: yesterdayAtTimestamp(12, 0),
    imageUrl:
      'https://images.unsplash.com/photo-1502741338009-cac2772e18bc?auto=format&fit=crop&w=1200&q=80',
    contents: [
      { name: 'Spinach bags', quantity: 1 },
      { name: 'Tomatoes', quantity: 6 },
      { name: 'Bell peppers', quantity: 4 },
      { name: 'Blueberries cartons', quantity: 1 },
    ],
  },
  {
    id: 'snapshot-3',
    timestamp: yesterdayAtTimestamp(21, 14),
    imageUrl:
      'https://images.unsplash.com/photo-1613479492651-449289f22f19?auto=format&fit=crop&w=1200&q=80',
    contents: [
      { name: 'Frozen berries bags', quantity: 2 },
      { name: 'Veg dumplings pieces', quantity: 12 },
      { name: 'Ice packs', quantity: 3 },
      { name: 'Vanilla ice cream tubs', quantity: 0 },
    ],
  },
]

function Dashboard() {
  return (
    <section className="surface dashboard">
      <header className="dashboard-header">
        <div>
          <h1 className="section-heading">Dashboard</h1>
        </div>
        <div className="pill secondary">Carousel view</div>
      </header>

      <SnapshotCarousel snapshots={mockSnapshots} />
    </section>
  )
}

export default Dashboard
