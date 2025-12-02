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

  constructor(baseUrl = DEFAULT_API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  private buildUrl(path: string) {
    const normalized = path.startsWith('/') ? path : `/${path}`
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

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const requestInit = this.withJsonHeaders(
      {
        credentials: 'include',
        ...init,
      },
      init.body,
    )

    const response = await fetch(this.buildUrl(path), requestInit)
    return this.handleResponse<T>(path, response)
  }

  get<T>(path: string, init?: RequestInit) {
    return this.request<T>(path, { ...init, method: 'GET' })
  }

  post<T>(path: string, body?: unknown, init?: RequestInit) {
    return this.request<T>(path, { ...init, method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined })
  }

  put<T>(path: string, body?: unknown, init?: RequestInit) {
    return this.request<T>(path, { ...init, method: 'PUT', body: body !== undefined ? JSON.stringify(body) : undefined })
  }

  patch<T>(path: string, body?: unknown, init?: RequestInit) {
    return this.request<T>(path, { ...init, method: 'PATCH', body: body !== undefined ? JSON.stringify(body) : undefined })
  }

  delete<T>(path: string, init?: RequestInit) {
    return this.request<T>(path, { ...init, method: 'DELETE' })
  }
}

export const apiClient = new ApiClient()
