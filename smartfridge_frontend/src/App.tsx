import { useEffect, useState } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import { ApiError, apiClient } from './api'
import Toast from './components/Toast'
import './App.css'

function App() {
  const [toast, setToast] = useState<{ message: string; tone: 'success' | 'error' } | null>(null)

  useEffect(() => {
    let clearToast: ReturnType<typeof setTimeout> | undefined

    const showToast = (message: string, tone: 'success' | 'error') => {
      setToast({ message, tone })
      if (clearToast) clearTimeout(clearToast)
      clearToast = setTimeout(() => setToast(null), 5000)
    }

    const checkHealth = async () => {
      try {
        const data = await apiClient.get<{ status?: string; message?: string } | string>('/health')
        const detail =
          typeof data === 'string' ? data : data?.message ?? data?.status ?? 'API healthy'
        showToast(detail, 'success')
      } catch (error) {
        const statusText = error instanceof ApiError ? `${error.status}` : 'network'
        const detail =
          error instanceof ApiError && typeof error.payload === 'string'
            ? error.payload
            : 'Unable to reach API healthcheck'
        showToast(`Healthcheck failed (${statusText}): ${detail}`, 'error')
      }
    }

    void checkHealth()

    return () => {
      if (clearToast) clearTimeout(clearToast)
    }
  }, [])

  return (
    <>
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

      <Toast toast={toast} />
    </>
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
