import { NavLink, Route, Routes } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import './App.css'

function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">SF</span>
          <div className="brand-text">
            <span className="brand-title">SmartFridge</span>
            <span className="brand-subtitle">Freshness at a glance</span>
          </div>
        </div>
        <nav className="nav-links">
          <NavLink to="/dashboard" className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}>
            Dashboard
          </NavLink>
        </nav>
      </header>

      <main className="app-main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  )
}

function NotFound() {
  return (
    <div className="surface not-found">
      <h2>Page not found</h2>
      <p className="muted">We could not find that page. Try heading back to your dashboard.</p>
    </div>
  )
}

export default App
