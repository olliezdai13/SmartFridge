import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiClient } from '../api'

function Recipes() {
  const [data, setData] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchRecipes = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.request<unknown>('/recipes')
      setData(response)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load recipes'
      setError(message)
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchRecipes()
  }, [fetchRecipes])

  const formattedJson = useMemo(() => {
    if (data === null || data === undefined) return 'No recipes returned.'
    try {
      return JSON.stringify(data, null, 2)
    } catch {
      return 'Unable to format recipe response.'
    }
  }, [data])

  return (
    <section className="surface recipes">
      <div className="recipes-header">
        <div>
          <h2 className="section-heading">Recipes</h2>
          <p className="muted">Live response from the /recipes API.</p>
        </div>
        <button type="button" className="ghost-btn" onClick={fetchRecipes} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>
      {error && <p className="error-text">{error}</p>}
      {!error && (
        <textarea
          className="json-viewer"
          readOnly
          spellCheck={false}
          value={loading ? 'Loading recipes…' : formattedJson}
          aria-label="Recipes response"
          wrap="off"
        />
      )}
    </section>
  )
}

export default Recipes
