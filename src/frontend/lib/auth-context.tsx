"use client"

import { createContext, useContext, useState, useCallback, type ReactNode } from "react"

export interface User {
  id: string
  email: string
  name: string
  storeName: string
  storeId: string
  avatar?: string
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<boolean>
  logout: () => void
  register: (data: RegisterData) => Promise<boolean>
  requestPasswordReset: (email: string) => Promise<boolean>
  resetPassword: (token: string, newPassword: string) => Promise<boolean>
}

interface RegisterData {
  email: string
  password: string
  name: string
  storeName: string
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Mock user data
const MOCK_USER: User = {
  id: "usr_001",
  email: "admin@latoscana.com",
  name: "Carlos Mendoza",
  storeName: "Pizzería La Toscana",
  storeId: "store_toscana_001",
  avatar: undefined,
}

// Mock credentials
const MOCK_CREDENTIALS = {
  email: "admin@latoscana.com",
  password: "demo123",
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const login = useCallback(async (email: string, password: string): Promise<boolean> => {
    setIsLoading(true)
    
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))
    
    if (email === MOCK_CREDENTIALS.email && password === MOCK_CREDENTIALS.password) {
      setUser(MOCK_USER)
      setIsLoading(false)
      return true
    }
    
    setIsLoading(false)
    return false
  }, [])

  const logout = useCallback(() => {
    setUser(null)
  }, [])

  const register = useCallback(async (data: RegisterData): Promise<boolean> => {
    setIsLoading(true)
    
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1500))
    
    // Mock successful registration
    const newUser: User = {
      id: `usr_${Date.now()}`,
      email: data.email,
      name: data.name,
      storeName: data.storeName,
      storeId: `store_${Date.now()}`,
    }
    
    setUser(newUser)
    setIsLoading(false)
    return true
  }, [])

  const requestPasswordReset = useCallback(async (email: string): Promise<boolean> => {
    setIsLoading(true)
    
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))
    
    setIsLoading(false)
    // Always return true for demo (email would be sent in real app)
    return email.includes("@")
  }, [])

  const resetPassword = useCallback(async (token: string, newPassword: string): Promise<boolean> => {
    setIsLoading(true)
    
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))
    
    setIsLoading(false)
    // Always return true for demo
    return token.length > 0 && newPassword.length >= 6
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        register,
        requestPasswordReset,
        resetPassword,
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
