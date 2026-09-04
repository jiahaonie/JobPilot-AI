const DEFAULT_TIMEOUT_MS = 15_000
const LONG_OPERATION_TIMEOUT_MS = 120_000
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '/api/v1').replace(/\/$/, '')

export class ApiError extends Error {
  readonly status: number | null

  constructor(
    message: string,
    status: number | null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  timeoutMs?: number
}

function formatDetail(detail: unknown): string | null {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (!item || typeof item !== 'object') return String(item)
        const record = item as Record<string, unknown>
        return typeof record.msg === 'string' ? record.msg : JSON.stringify(item)
      })
      .join('；')
  }
  return null
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(
    () => controller.abort(),
    options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
  )
  const headers = new Headers(options.headers)
  let body: BodyInit | undefined

  if (options.body instanceof FormData) {
    body = options.body
  } else if (options.body !== undefined) {
    headers.set('Content-Type', 'application/json')
    body = JSON.stringify(options.body)
  }

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      body,
      headers,
      signal: controller.signal,
    })

    if (response.status === 204) return undefined as T

    const contentType = response.headers.get('content-type') ?? ''
    const payload: unknown = contentType.includes('application/json')
      ? await response.json()
      : await response.text()

    if (!response.ok) {
      const detail =
        payload && typeof payload === 'object'
          ? formatDetail((payload as Record<string, unknown>).detail)
          : null
      throw new ApiError(detail ?? `请求失败（${response.status}）`, response.status)
    }
    return payload as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('请求超时，请确认后端服务状态后重试', null)
    }
    throw new ApiError('无法连接后端服务，请确认 FastAPI 已启动', null)
  } finally {
    window.clearTimeout(timeout)
  }
}

export const longOperation = { timeoutMs: LONG_OPERATION_TIMEOUT_MS }
