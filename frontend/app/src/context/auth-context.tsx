"use client"

import { createContext, useContext, useState, useEffect, type ReactNode } from "react"
import { useRouter } from "next/navigation"
import { jwtDecode } from "jwt-decode"

type User = {
  id: string
  username: string
  scopes: string[]
  isActive: boolean
}

type AuthContextType = {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => void
  hasScope: (scope: string) => boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    // Check for token in localStorage on initial load
    const storedToken = localStorage.getItem("token")
    if (storedToken) {
      try {
        const decoded = jwtDecode<{ sub: string; scopes: string[] }>(storedToken)
        // Check if token is expired
        const currentTime = Date.now() / 1000
        if (decoded.exp && decoded.exp < currentTime) {
          localStorage.removeItem("token")
          setToken(null)
          setUser(null)
        } else {
          setToken(storedToken)
          // Fetch user profile with the token
          fetchUserProfile(storedToken)
        }
      } catch (error) {
        console.error("Invalid token:", error)
        localStorage.removeItem("token")
      }
    }
    setIsLoading(false)
  }, [])

  const fetchUserProfile = async (authToken: string) => {
    try {
      const response = await fetch("/api/v1/users/profile", {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })

      if (response.ok) {
        const userData = await response.json()
        setUser({
          id: userData.id,
          username: userData.username,
          isActive: userData.is_active,
          scopes: userData.scopes || [],
        })
      } else {
        // If profile fetch fails, clear token
        localStorage.removeItem("token")
        setToken(null)
        setUser(null)
      }
    } catch (error) {
      console.error("Error fetching user profile:", error)
      localStorage.removeItem("token")
      setToken(null)
      setUser(null)
    }
  }

  const login = async (username: string, password: string) => {
    setIsLoading(true)
    try {
      const formData = new URLSearchParams()
      formData.append("username", username)
      formData.append("password", password)

      const response = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || "Login failed")
      }

      const data = await response.json()
      const authToken = data.access_token

      // Store token in localStorage
      localStorage.setItem("token", authToken)
      setToken(authToken)

      // Fetch user profile
      await fetchUserProfile(authToken)

      // Redirect to dashboard
      router.push("/dashboard")
    } catch (error) {
      console.error("Login error:", error)
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (username: string, email: string, password: string) => {
    setIsLoading(true)
    try {
      const response = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, email, password }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || "Registration failed")
      }

      // After successful registration, log the user in
      await login(username, password)
    } catch (error) {
      console.error("Registration error:", error)
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem("token")
    setToken(null)
    setUser(null)
    router.push("/login")
  }

  const hasScope = (scope: string) => {
    return user?.scopes?.includes(scope) || false
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        register,
        logout,
        hasScope,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
