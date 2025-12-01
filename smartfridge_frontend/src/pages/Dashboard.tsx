import { useEffect, useState } from 'react'
import { isAxiosError, type AxiosResponse } from 'axios'

import { apiClient } from '../lib/apiClient.ts'

type LatestPayload = {
  latest: {
    id: string
    status: string
    createdAt?: string | null
    updatedAt?: string | null
  } | null
  items: { name: string; quantity: number }[]
  itemCount: number
}

function Dashboard() {
  const [toast, setToast] = useState<string | null>(null)
  const [latest, setLatest] = useState<LatestPayload | null>(null)
  const [loadingLatest, setLoadingLatest] = useState(true)
  const [latestError, setLatestError] = useState<string | null>(null)

  useEffect(() => {
    let timer: number | undefined

    apiClient
      // Override baseURL so healthcheck hits /healthz (proxied by Vite) instead of /api/healthz
      .get('/healthz', { baseURL: '/' })
      .then(() => {
        setToast('Backend is healthy')
        timer = window.setTimeout(() => setToast(null), 4000)
      })
      .catch((err: unknown) => {
        console.error('Health check failed', err)
      })

    apiClient
      .get<LatestPayload>('/latest')
      .then((response: AxiosResponse<LatestPayload>) => {
        setLatest(response.data)
      })
      .catch((error: unknown) => {
        const message = isAxiosError(error)
          ? (error.response?.data as { error?: string } | undefined)?.error
          : null
        setLatestError(message || 'Could not load latest snapshot yet.')
      })
      .finally(() => setLoadingLatest(false))

    return () => {
      if (timer) {
        window.clearTimeout(timer)
      }
    }
  }, [])

  return (
    <>
      {toast && (
        <div className="toast success">
          <span>{toast}</span>
        </div>
      )}

      <section className="page">
        <div className="page-heading">
          <p className="eyebrow">Overview</p>
          <h1>Dashboard</h1>
          <p className="subhead">Quick look at fridge inventory and system health.</p>
        </div>

        <div className="panel-grid">
          <div className="panel status-panel">
            <div className="panel-head">
              <h2>Latest Snapshot</h2>
              {latest?.latest?.status && (
                <span className={`pill badge ${latest.latest.status}`}>
                  {latest.latest.status}
                </span>
              )}
            </div>
            {loadingLatest && <p>Loading latest data…</p>}
            {!loadingLatest && latestError && (
              <p className="muted">{latestError}</p>
            )}
            {!loadingLatest && !latestError && (
              <div className="stat-block">
                <div>
                  <p className="eyebrow">Items detected</p>
                  <p className="stat-value">{latest?.itemCount ?? 0}</p>
                </div>
                <div>
                  <p className="eyebrow">Snapshot ID</p>
                  <p className="muted mono">
                    {latest?.latest?.id ?? '—'}
                  </p>
                </div>
              </div>
            )}
          </div>
          <div className="panel">
            <h2>Health</h2>
            <p>Appliance telemetry and alerts will appear here.</p>
          </div>
          <div className="panel">
            <div className="panel-head">
              <h2>Inventory</h2>
              <span className="muted tiny">
                {loadingLatest
                  ? 'Loading…'
                  : `${latest?.items.length ?? 0} items`}
              </span>
            </div>
            {!loadingLatest && latest?.items.length === 0 && (
              <p className="muted">
                Snap a photo of your fridge to populate the inventory list.
              </p>
            )}
            {loadingLatest && <p className="muted">Pulling fresh data…</p>}
            {!loadingLatest && latest && latest.items.length > 0 && (
              <ul className="inventory-list">
                {latest.items.map((item) => (
                  <li key={item.name} className="inventory-row">
                    <div className="dot" />
                    <span>{item.name}</span>
                    <span className="muted">x{item.quantity}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </section>
    </>
  )
}

export default Dashboard
