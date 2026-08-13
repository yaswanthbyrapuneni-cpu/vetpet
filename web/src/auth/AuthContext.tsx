import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, ApiError, tokenStore } from '../api/client'
import type { User } from '../types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  error: string | null
  login(email: string, password: string): Promise<boolean>
  logout(): void
  clearError(): void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadUser = useCallback(async () => {
    if (!tokenStore.get()) {
      setLoading(false)
      return
    }
    try {
      setUser(await api.get<User>('/auth/me'))
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) tokenStore.clear()
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadUser()
  }, [loadUser])

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.post<{ access_token: string }>('/auth/login', { email, password })
      tokenStore.set(result.access_token)
      setUser(await api.get<User>('/auth/me'))
      return true
    } catch (caught) {
      tokenStore.clear()
      setError(caught instanceof Error ? caught.message : 'Sign in failed.')
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(() => {
    tokenStore.clear()
    setUser(null)
    setError(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, error, login, logout, clearError: () => setError(null) }),
    [user, loading, error, login, logout],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
