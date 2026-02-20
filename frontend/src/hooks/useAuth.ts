import { useState, useEffect } from 'react'

export function useAuth() {
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setToken(localStorage.getItem('billingpulse_token'))
    setLoading(false)
  }, [])

  const login = (accessToken: string) => {
    localStorage.setItem('billingpulse_token', accessToken)
    setToken(accessToken)
  }

  const logout = () => {
    localStorage.removeItem('billingpulse_token')
    setToken(null)
  }

  return { token, loading, login, logout }
}
