const DEFAULT_API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')

export type AuthErrorContext = {
  status: 401 | 403
  path: string
  response: Response
  payload: unknown
}

export type AuthErrorHandler = (context: AuthErrorContext) => void

let authErrorHandler: AuthErrorHandler | undefined

export const registerAuthErrorHandler = (handler: AuthErrorHandler) => {
  authErrorHandler = handler
}

export const clearAuthErrorHandler = () => {
  authErrorHandler = undefined
}

export class ApiError extends Error {
  status: number
  path: string
  payload: unknown

  constructor(message: string, options: { status: number; path: string; payload: unknown }) {
    super(message)
    this.status = options.status
    this.path = options.path
    this.payload = options.payload
  }
}

export class ApiClient {
  private readonly baseUrl: string
  private refreshPromise: Promise<boolean> | null = null

  constructor(baseUrl = DEFAULT_API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  private normalizePath(path: string) {
    return path.startsWith('/') ? path : `/${path}`
  }

  private buildUrl(path: string) {
    const normalized = this.normalizePath(path)
    return `${this.baseUrl}${normalized}`
  }

  private async parseBody(response: Response) {
    if (response.status === 204) return null

    const contentType = response.headers.get('content-type') ?? ''
    if (contentType.includes('application/json')) {
      try {
        return await response.json()
      } catch {
        return null
      }
    }

    try {
      return await response.text()
    } catch {
      return null
    }
  }

  private async handleResponse<T>(path: string, response: Response): Promise<T> {
    const payload = await this.parseBody(response)

    if (response.status === 401 || response.status === 403) {
      authErrorHandler?.({
        status: response.status as 401 | 403,
        path,
        response,
        payload,
      })
    }

    if (!response.ok) {
      const message = typeof payload === 'string' && payload.length > 0 ? payload : 'Request failed'
      throw new ApiError(message, { status: response.status, path, payload })
    }

    return payload as T
  }

  private withJsonHeaders(init: RequestInit, body?: unknown): RequestInit {
    const headers = new Headers(init.headers)
    if (body !== undefined && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }
    return { ...init, headers }
  }

  private shouldAttemptRefresh(path: string, status: number, attemptedRefresh: boolean) {
    if (attemptedRefresh) return false
    if (status !== 401 && status !== 403) return false

    const normalized = this.normalizePath(path)
    const nonRefreshablePaths = new Set(['/auth/login', '/auth/signup', '/auth/logout', '/auth/refresh'])
    return !nonRefreshablePaths.has(normalized)
  }

  private async refreshTokens(): Promise<boolean> {
    if (this.refreshPromise) return this.refreshPromise

    this.refreshPromise = (async () => {
      try {
        const response = await fetch(this.buildUrl('/auth/refresh'), {
          method: 'POST',
          credentials: 'include',
        })
        return response.ok
      } catch {
        return false
      } finally {
        this.refreshPromise = null
      }
    })()

    return this.refreshPromise
  }

  private async requestWithRefresh<T>(path: string, init: RequestInit, attemptedRefresh: boolean): Promise<T> {
    const normalizedPath = this.normalizePath(path)
    const requestInit = this.withJsonHeaders(
      {
        credentials: 'include',
        ...init,
      },
      init.body,
    )

    const response = await fetch(this.buildUrl(normalizedPath), requestInit)

    if (this.shouldAttemptRefresh(normalizedPath, response.status, attemptedRefresh)) {
      const refreshed = await this.refreshTokens()
      if (refreshed) {
        return this.requestWithRefresh<T>(normalizedPath, init, true)
      }
    }

    return this.handleResponse<T>(normalizedPath, response)
  }

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    return this.requestWithRefresh<T>(path, init, false)
  }
}

export const apiClient = new ApiClient()
