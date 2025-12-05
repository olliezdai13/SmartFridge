import { useCallback, useEffect, useRef, useState } from 'react'
import type { ReactElement } from 'react'
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import AuthPage from './pages/Auth'
import Dashboard from './pages/Dashboard'
import Recipes from './pages/Recipes'
import Statistics from './pages/Statistics'
import { ApiError, apiClient, clearAuthErrorHandler, registerAuthErrorHandler } from './api'
import Toast from './components/Toast'
import type { UserProfile } from './types'
import './App.css'

type AuthState = {
  status: 'loading' | 'authenticated' | 'unauthenticated'
  user: UserProfile | null
}

type ToastState = { message: string; tone: 'success' | 'error' } | null

function App() {
  const navigate = useNavigate()
  const location = useLocation()
  const [toast, setToast] = useState<ToastState>(null)
  const [authState, setAuthState] = useState<AuthState>({ status: 'loading', user: null })
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const toastTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const latestPathRef = useRef(location.pathname)

  useEffect(() => {
    latestPathRef.current = location.pathname
  }, [location.pathname])

  const resetToast = useCallback(() => {
    if (toastTimeoutRef.current) {
      clearTimeout(toastTimeoutRef.current)
      toastTimeoutRef.current = null
    }
    setToast(null)
  }, [])

  const showToast = useCallback(
    (message: string, tone: 'success' | 'error') => {
      resetToast()
      setToast({ message, tone })
      toastTimeoutRef.current = setTimeout(() => setToast(null), 5000)
    },
    [resetToast],
  )

  useEffect(() => {
    return () => resetToast()
  }, [resetToast])

  const isAuthPath = useCallback((path: string) => {
    return path.startsWith('/login') || path.startsWith('/signup')
  }, [])

  const redirectToLogin = useCallback(() => {
    setAuthState({ status: 'unauthenticated', user: null })
    resetToast()
    const currentPath = latestPathRef.current
    if (!isAuthPath(currentPath)) {
      navigate('/login', { replace: true })
    }
  }, [isAuthPath, navigate, resetToast])

  useEffect(() => {
    registerAuthErrorHandler(() => {
      redirectToLogin()
    })

    return () => {
      clearAuthErrorHandler()
    }
  }, [redirectToLogin])

  useEffect(() => {
    let cancelled = false

    const bootstrapAuth = async () => {
      try {
        const data = await apiClient.request<{ user: UserProfile }>('/auth/me')
        if (cancelled) return
        setAuthState({ status: 'authenticated', user: data.user })
      } catch (error) {
        if (cancelled) return

        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
          setAuthState({ status: 'unauthenticated', user: null })
          const currentPath = latestPathRef.current
          const onAuthScreen = isAuthPath(currentPath)
          if (!onAuthScreen) {
            navigate('/login', { replace: true })
          }
        } else {
          setAuthState({ status: 'unauthenticated', user: null })
          showToast('Unable to confirm your session. Please log in again.', 'error')
        }
      }
    }

    void bootstrapAuth()

    return () => {
      cancelled = true
    }
  }, [isAuthPath, navigate, showToast])

  const handleAuthSuccess = useCallback(
    (user: UserProfile, mode: 'login' | 'signup') => {
      setAuthState({ status: 'authenticated', user })
      const message = mode === 'login' ? 'Signed in successfully' : 'Account created and signed in'
      showToast(message, 'success')
      navigate('/dashboard', { replace: true })
    },
    [navigate, showToast],
  )

  const handleLogout = useCallback(async () => {
    if (isLoggingOut) return
    setIsLoggingOut(true)
    try {
      await apiClient.request('/auth/logout', { method: 'POST' })
    } catch (error) {
      const detail =
        error instanceof ApiError && typeof error.payload === 'string'
          ? error.payload
          : 'Unable to log out right now'
      showToast(detail, 'error')
    } finally {
      setAuthState({ status: 'unauthenticated', user: null })
      resetToast()
      navigate('/login', { replace: true })
      setIsLoggingOut(false)
    }
  }, [isLoggingOut, navigate, resetToast, showToast])

  const isAuthenticated = authState.status === 'authenticated'
  const isAuthScreen = isAuthPath(location.pathname)

  return (
    <>
      <div className="app-shell">
        {!isAuthScreen && (
          <header className="app-header">
            <div className="brand">
              <span className="brand-mark">SF</span>
              <div className="brand-text">
                <span className="brand-title">SmartFridge</span>
                <span className="brand-subtitle">Freshness at a glance</span>
              </div>
            </div>
            <nav className="nav-links">
              <div className="nav-group">
                <NavLink
                  to="/dashboard"
                  className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
                >
                  Dashboard
                </NavLink>
                <NavLink
                  to="/recipes"
                  className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
                >
                  Recipes
                </NavLink>
                <NavLink
                  to="/statistics"
                  className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
                >
                  Statistics
                </NavLink>
              </div>

              <div className="nav-actions">
                {isAuthenticated ? (
                  <>
                    <span className="user-chip">{authState.user?.name ?? authState.user?.email}</span>
                    <button
                      type="button"
                      className="ghost-btn nav-cta"
                      onClick={handleLogout}
                      disabled={isLoggingOut}
                    >
                      {isLoggingOut ? 'Logging out…' : 'Log out'}
                    </button>
                  </>
                ) : (
                  <>
                    <NavLink
                      to="/login"
                      className={({ isActive }) =>
                        isActive ? 'nav-link nav-cta active' : 'nav-link nav-cta'
                      }
                    >
                      Log in
                    </NavLink>
                    <NavLink
                      to="/signup"
                      className={({ isActive }) =>
                        isActive ? 'nav-link nav-cta primary active' : 'nav-link nav-cta primary'
                      }
                    >
                      Sign up
                    </NavLink>
                  </>
                )}
              </div>
            </nav>
          </header>
        )}

        <main className="app-main">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute authState={authState}>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/recipes"
              element={
                <ProtectedRoute authState={authState}>
                  <Recipes />
                </ProtectedRoute>
              }
            />
            <Route
              path="/statistics"
              element={
                <ProtectedRoute authState={authState}>
                  <Statistics />
                </ProtectedRoute>
              }
            />
            <Route
              path="/login"
              element={
                <AuthRoute authState={authState}>
                  <AuthPage mode="login" onAuthSuccess={(user) => handleAuthSuccess(user, 'login')} />
                </AuthRoute>
              }
            />
            <Route
              path="/signup"
              element={
                <AuthRoute authState={authState}>
                  <AuthPage
                    mode="signup"
                    onAuthSuccess={(user) => handleAuthSuccess(user, 'signup')}
                  />
                </AuthRoute>
              }
            />
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

function ProtectedRoute({ authState, children }: { authState: AuthState; children: ReactElement }) {
  const location = useLocation()

  if (authState.status === 'loading') {
    return <CenteredState title="Checking access" message="Hold on while we confirm your session." />
  }

  if (authState.status === 'unauthenticated') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return children
}

function AuthRoute({ authState, children }: { authState: AuthState; children: ReactElement }) {
  if (authState.status === 'loading') {
    return <CenteredState title="Loading" message="Preparing the login screen..." />
  }

  if (authState.status === 'authenticated') {
    return <Navigate to="/dashboard" replace />
  }

  return children
}

function CenteredState({ title, message }: { title: string; message: string }) {
  return (
    <div className="surface centered-state">
      <h2>{title}</h2>
      <p className="muted">{message}</p>
    </div>
  )
}

export default App
