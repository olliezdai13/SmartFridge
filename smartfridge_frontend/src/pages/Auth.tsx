import type { FormEvent } from 'react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, apiClient } from '../api'
import type { UserProfile } from '../types'

type AuthMode = 'login' | 'signup'

type AuthPageProps = {
  mode: AuthMode
  onAuthSuccess: (user: UserProfile) => void
}

type FormState = {
  name: string
  email: string
  password: string
}

function AuthPage({ mode, onAuthSuccess }: AuthPageProps) {
  const [formState, setFormState] = useState<FormState>({
    name: '',
    email: '',
    password: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const copy = useMemo(
    () =>
      mode === 'login'
        ? {
            heading: 'Log in',
            blurb: 'Access your SmartFridge dashboard and freshness insights.',
            submit: 'Log in',
            switchCta: 'Create account',
            switchLink: '/signup',
            switchCopy: "Don't have an account?",
          }
        : {
            heading: 'Create an account',
            blurb: 'Sign up to start tracking your fridge snapshots and alerts.',
            submit: 'Sign up',
            switchCta: 'Back to login',
            switchLink: '/login',
            switchCopy: 'Already registered?',
          },
    [mode],
  )

  const updateField = (key: keyof FormState, value: string) => {
    setFormState((prev) => ({ ...prev, [key]: value }))
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setSubmitting(true)

    const payload =
      mode === 'signup'
        ? {
            name: formState.name.trim() || undefined,
            email: formState.email.trim(),
            password: formState.password,
          }
        : {
            email: formState.email.trim(),
            password: formState.password,
          }

    try {
      const data = await apiClient.request<{ user: UserProfile }>(
        mode === 'login' ? '/auth/login' : '/auth/signup',
        {
          method: 'POST',
          body: JSON.stringify(payload),
        },
      )
      onAuthSuccess(data.user)
    } catch (err) {
      let message = 'Unable to complete the request.'
      if (err instanceof ApiError) {
        if (typeof err.payload === 'string' && err.payload.trim().length > 0) {
          message = err.payload
        } else if (
          typeof err.payload === 'object' &&
          err.payload !== null &&
          'error' in err.payload &&
          typeof (err.payload as { error?: unknown }).error === 'string'
        ) {
          message = (err.payload as { error?: string }).error as string
        } else if (err.status === 401) {
          message = 'Invalid credentials. Please try again.'
        }
      }
      setError(message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="surface auth-surface">
      <div className="auth-intro">
        <div className="pill secondary">{mode === 'login' ? 'Welcome back' : 'Join us'}</div>
        <h1 className="section-heading">{copy.heading}</h1>
        <p className="muted">{copy.blurb}</p>
      </div>

      <form className="auth-form" onSubmit={handleSubmit}>
        {mode === 'signup' && (
          <div className="form-field">
            <label className="field-label" htmlFor="name">
              Name (optional)
            </label>
            <input
              id="name"
              name="name"
              type="text"
              autoComplete="name"
              className="text-input"
              value={formState.name}
              onChange={(event) => updateField('name', event.target.value)}
              placeholder="Taylor Doe"
              disabled={submitting}
            />
          </div>
        )}

        <div className="form-field">
          <label className="field-label" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            className="text-input"
            value={formState.email}
            onChange={(event) => updateField('email', event.target.value)}
            placeholder="you@example.com"
            disabled={submitting}
          />
        </div>

        <div className="form-field">
          <label className="field-label" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            required
            minLength={5}
            className="text-input"
            value={formState.password}
            onChange={(event) => updateField('password', event.target.value)}
            placeholder="••••••••"
            disabled={submitting}
          />
          <p className="field-hint muted">Minimum 5 characters.</p>
        </div>

        {error ? <p className="field-error">{error}</p> : null}

        <div className="auth-actions">
          <button type="submit" className="primary-btn" disabled={submitting}>
            {submitting ? 'Please wait…' : copy.submit}
          </button>
          <div className="auth-switch">
            <span className="muted">{copy.switchCopy}</span>
            <Link className="link" to={copy.switchLink}>
              {copy.switchCta}
            </Link>
          </div>
        </div>
      </form>
    </section>
  )
}

export default AuthPage
