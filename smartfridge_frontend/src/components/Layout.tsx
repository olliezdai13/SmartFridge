import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import type { ReactNode } from 'react'

import { useAuth } from '../lib/auth.tsx'

const navLinks = [{ to: '/dashboard', label: 'Dashboard' }]

type LayoutProps = {
  children?: ReactNode
}

function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [signingOut, setSigningOut] = useState(false)

  async function handleLogout() {
    setSigningOut(true)
    try {
      await logout()
      navigate('/login')
    } finally {
      setSigningOut(false)
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">SmartFridge</div>
        <nav className="app-nav">
          {navLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        {user && (
          <div className="user-meta">
            <div className="user-text">
              <span className="muted tiny">Signed in as</span>
              <span>{user.email}</span>
            </div>
            <button className="ghost-button" onClick={handleLogout} disabled={signingOut}>
              {signingOut ? 'Signing out…' : 'Logout'}
            </button>
          </div>
        )}
      </header>
      <main className="app-main">
        {children ?? <Outlet />}
      </main>
    </div>
  )
}

export default Layout
