'use client';

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react';
import { api, setTokens, clearTokens, getToken, getRefreshToken, ApiError } from '@/lib/api';
import { decodeJwtPayload } from '@/lib/utils';
import type { User, UserCreate, UserLogin, AuthTokens } from '@/types';

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: UserLogin) => Promise<void>;
  register: (data: UserCreate) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!user;

  // Hydrate user on mount — only clear tokens on auth failures, not network blips
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setIsLoading(false);
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        const me = await api<User>('/auth/me');
        if (!cancelled) setUser(me);
      } catch (err) {
        if (cancelled) return;
        // Network / server down → keep tokens so a refresh later can succeed
        const isAuthFailure =
          err instanceof ApiError && (err.status === 401 || err.status === 403);
        if (isAuthFailure) {
          clearTokens();
          setUser(null);
        } else {
          console.warn('Auth hydration failed (network). Keeping session tokens.', err);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  // Schedule token refresh
  useEffect(() => {
    if (!user) return;

    const token = getToken();
    if (!token) return;

    const payload = decodeJwtPayload(token);
    if (!payload || typeof payload.exp !== 'number') return;

    const expiresAt = payload.exp * 1000;
    const now = Date.now();
    // Refresh at 80% of TTL
    const refreshAt = now + (expiresAt - now) * 0.8;
    const delay = Math.max(refreshAt - now, 1000);

    const timer = setTimeout(async () => {
      try {
        const tokens = await api<AuthTokens>('/auth/refresh', {
          method: 'POST',
          body: getRefreshToken(),
          skipAuth: true,
        });
        setTokens(tokens);
      } catch {
        // Refresh failed, user will be logged out on next 401
      }
    }, delay);

    return () => clearTimeout(timer);
  }, [user]);

  const login = useCallback(async (credentials: UserLogin) => {
    const tokens = await api<AuthTokens>('/auth/login', {
      method: 'POST',
      body: credentials,
      skipAuth: true,
    });
    setTokens(tokens);
    const userData = await api<User>('/auth/me');
    setUser(userData);
  }, []);

  const register = useCallback(async (data: UserCreate) => {
    await api<User>('/auth/register', {
      method: 'POST',
      body: data,
      skipAuth: true,
    });
    // Auto-login after registration
    await login({ email: data.email, password: data.password });
  }, [login]);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
    // Fire-and-forget server-side logout
    api('/auth/logout', { method: 'POST' }).catch(() => {});
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, isLoading, isAuthenticated, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
