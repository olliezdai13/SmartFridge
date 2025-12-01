import { Navigate, Outlet, useLocation } from 'react-router-dom'

import Layout from '../components/Layout'
import { useAuth } from '../lib/auth'

function ProtectedLayout() {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="auth-gate">
        <div className="auth-card">
          <p className="muted">Checking your session…</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return (
    <Layout>
      <Outlet />
    </Layout>
  )
}

export default ProtectedLayout
