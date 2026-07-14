import type { AuthTokens, SSEEvent } from '@/types';

/**
 * Prefer same-origin `/api/v1` (proxied via next.config rewrites).
 * Falls back to absolute URL when NEXT_PUBLIC_API_URL is set to a full URL
 * outside the Next app (e.g. production API host).
 */
function resolveApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!configured) return '/api/v1';

  // Absolute URL → use as-is (normalize localhost → 127.0.0.1 for Windows)
  if (/^https?:\/\//i.test(configured)) {
    // In the browser, prefer the Next.js rewrite proxy to avoid CORS.
    if (typeof window !== 'undefined') {
      return '/api/v1';
    }
    return configured.replace('localhost', '127.0.0.1');
  }

  // Relative path
  return configured.startsWith('/') ? configured : `/${configured}`;
}

const API_BASE_URL = resolveApiBaseUrl();

// ============================================
// Token Management — isolated here for future
// migration to httpOnly cookies. No component
// should ever import these directly.
// ============================================

const TOKEN_KEY = 'conduit_access_token';
const REFRESH_KEY = 'conduit_refresh_token';

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(tokens: AuthTokens): void {
  localStorage.setItem(TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

// ============================================
// Request Helpers
// ============================================

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown;
  skipAuth?: boolean;
};

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  try {
    const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(refreshToken),
    });

    if (!res.ok) return null;

    const data: AuthTokens = await res.json();
    setTokens(data);
    return data.access_token;
  } catch {
    return null;
  }
}

/**
 * Core fetch wrapper. All API calls go through here.
 * - Injects JWT Authorization header
 * - Auto-retries on 401 with token refresh
 * - Throws on non-OK responses with parsed error
 */
export async function api<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { body, skipAuth, ...init } = options;
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;

  const headers: Record<string, string> = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(init.headers as Record<string, string>),
  };

  if (!skipAuth) {
    const token = getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  const config: RequestInit = {
    ...init,
    headers,
    body: body !== undefined ? (isFormData ? (body as any) : JSON.stringify(body)) : undefined,
  };

  let res;
  try {
    res = await fetch(`${API_BASE_URL}${endpoint}`, config);
  } catch (err) {
    const message =
      err instanceof TypeError
        ? `Cannot reach API at ${API_BASE_URL}${endpoint}. Is the backend running?`
        : err instanceof Error
          ? err.message
          : 'Network request failed';
    console.error(`Raw fetch error calling ${endpoint}:`, err);
    throw new ApiError(message, 0, { cause: err });
  }

  // Auto-refresh on 401
  if (res.status === 401 && !skipAuth) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers['Authorization'] = `Bearer ${newToken}`;
      try {
        res = await fetch(`${API_BASE_URL}${endpoint}`, { ...config, headers });
      } catch (err) {
        console.error(`Raw fetch error on retry calling ${endpoint}:`, err);
        throw new ApiError(
          `Cannot reach API at ${API_BASE_URL}${endpoint}. Is the backend running?`,
          0,
          { cause: err }
        );
      }
    }
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(
      errorData.detail || errorData.message || 'Request failed',
      res.status,
      errorData
    );
  }

  // Handle 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json();
}

/**
 * Upload files via multipart/form-data
 */
export async function apiUpload<T>(
  endpoint: string,
  formData: FormData
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  // Don't set Content-Type — browser sets it with boundary
  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers,
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(
      errorData.detail || 'Upload failed',
      res.status,
      errorData
    );
  }

  return res.json();
}

// ============================================
// POST-based SSE Streaming
// Uses fetch() → ReadableStream → TextDecoder
// → manual SSE parser. No EventSource.
// ============================================

export async function* apiStream(
  endpoint: string,
  body: unknown,
  signal?: AbortSignal
): AsyncGenerator<SSEEvent> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
    signal,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(
      errorData.detail || 'Stream request failed',
      res.status,
      errorData
    );
  }

  if (!res.body) {
    throw new ApiError('Response body is null', 0);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let currentEvent = 'message';
  let currentData = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      // Keep the last potentially incomplete line in the buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('event:')) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          currentData = line.slice(5).trim();
        } else if (line.trim() === '') {
          // Empty line = end of SSE message
          if (currentData) {
            yield { event: currentEvent, data: currentData };
            currentEvent = 'message';
            currentData = '';
          }
        }
      }
    }

    // Process any remaining data in buffer
    if (currentData) {
      yield { event: currentEvent, data: currentData };
    }
  } finally {
    reader.releaseLock();
  }
}

// ============================================
// Error Class
// ============================================

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}
