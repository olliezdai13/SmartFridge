import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiClient } from '../api'

type UsedIngredient = {
  name: string
  amount?: number
  unit?: string
}

type Recipe = {
  title?: string
  image?: string
  missedIngredientCount?: number
  usedIngredientCount?: number
  usedIngredients?: UsedIngredient[]
  missedIngredients?: UsedIngredient[]
}

type RecipesResponse = {
  recipes?: Recipe[]
}

function Recipes() {
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchRecipes = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await apiClient.request<RecipesResponse>('/recipes')
      const normalizedRecipes = Array.isArray(response.recipes) ? response.recipes : []
      setRecipes(normalizedRecipes)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load recipes'
      setError(message)
      setRecipes([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchRecipes()
  }, [fetchRecipes])

  const recipeRows = useMemo(() => {
    const rows: Recipe[][] = []
    for (let i = 0; i < recipes.length; i += 3) {
      rows.push(recipes.slice(i, i + 3))
    }
    return rows
  }, [recipes])

  return (
    <section className="surface recipes">
      <div className="recipes-header">
        <div>
          <h2 className="section-heading">Recipes</h2>
          <p className="muted">Live matches from the /recipes API.</p>
        </div>
        <button type="button" className="ghost-btn" onClick={fetchRecipes} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>
      {error && <p className="error-text">{error}</p>}
      {!error && (
        <div className="recipes-table-wrapper">
          {loading ? (
            <p className="muted">Loading recipes…</p>
          ) : recipes.length === 0 ? (
            <p className="muted">No recipes available right now. Try refreshing.</p>
          ) : (
            <table className="recipes-table" role="grid" aria-label="Recipes">
              <tbody>
                {recipeRows.map((row, rowIndex) => (
                  <tr key={`recipe-row-${rowIndex}`}>
                    {row.map((recipe, cellIndex) => (
                      <td key={`recipe-${rowIndex}-${cellIndex}`} className="recipe-cell">
                        <article className="recipe-card">
                          <div className="recipe-thumb">
                            {recipe.image ? (
                              <img
                                src={recipe.image}
                                alt={recipe.title ?? 'Recipe image'}
                                loading="lazy"
                              />
                            ) : (
                              <div className="recipe-thumb placeholder">No image</div>
                            )}
                          </div>
                          <div className="recipe-info">
                            <h3 className="recipe-title">{recipe.title ?? 'Untitled recipe'}</h3>
                            <p className="recipe-counts">
                              <span
                                className="recipe-count strong"
                                title={
                                  (recipe.usedIngredients ?? [])
                                    .map((ingredient) => ingredient.name)
                                    .filter(Boolean)
                                    .join(', ') || 'No used ingredients listed'
                                }
                              >
                                {recipe.usedIngredientCount ?? 0} used
                              </span>
                              <span aria-hidden="true"> • </span>
                              <span
                                className="recipe-count"
                                title={
                                  (recipe.missedIngredients ?? [])
                                    .map((ingredient) => ingredient.name)
                                    .filter(Boolean)
                                    .join(', ') || 'No missing ingredients listed'
                                }
                              >
                                {recipe.missedIngredientCount ?? 0} missing
                              </span>
                            </p>
                          </div>
                        </article>
                      </td>
                    ))}
                    {Array.from({ length: Math.max(0, 3 - row.length) }).map((_, fillerIndex) => (
                      <td
                        key={`recipe-empty-${rowIndex}-${fillerIndex}`}
                        className="recipe-cell"
                        aria-hidden="true"
                      />
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </section>
  )
}

export default Recipes
