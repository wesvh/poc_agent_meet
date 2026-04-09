"use client"

import { useState, useCallback, useEffect } from "react"
import { AuthProvider, useAuth } from "@/lib/auth-context"
import { LoginForm } from "@/components/auth/login-form"
import { RegisterForm } from "@/components/auth/register-form"
import { ForgotPasswordForm } from "@/components/auth/forgot-password-form"
import { Sidebar, type Section } from "@/components/dashboard/sidebar"
import { DashboardSection } from "@/components/dashboard/sections/dashboard-section"
import { CatalogSection } from "@/components/dashboard/sections/catalog-section"
import { FinancesSection } from "@/components/dashboard/sections/finances-section"
import { DisputesSection } from "@/components/dashboard/sections/disputes-section"
import { ScheduleSection } from "@/components/dashboard/sections/schedule-section"
import { SupportSection } from "@/components/dashboard/sections/support-section"
import { AIDebugPanel } from "@/components/dashboard/ai-debug-panel"
import { PresentationOverlays } from "@/components/presentation/overlays"
import { usePresentationControl } from "@/hooks/use-presentation-control"

type AuthView = "login" | "register" | "forgot-password"

function resolveSessionId() {
  if (typeof window === "undefined") {
    return "demo1"
  }

  const params = new URLSearchParams(window.location.search)
  return params.get("session_id") || "demo1"
}

// =============================================================================
// AUTH SCREEN (with presentation control)
// =============================================================================

interface AuthScreenProps {
  authView: AuthView
  setAuthView: (view: AuthView) => void
}

function AuthScreen({ authView, setAuthView }: AuthScreenProps) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-[#FFF5F5] to-white p-4">
      {authView === "login" && (
        <LoginForm
          onForgotPassword={() => setAuthView("forgot-password")}
          onRegister={() => setAuthView("register")}
        />
      )}
      {authView === "register" && <RegisterForm onBack={() => setAuthView("login")} />}
      {authView === "forgot-password" && (
        <ForgotPasswordForm onBack={() => setAuthView("login")} />
      )}
    </div>
  )
}

// =============================================================================
// DASHBOARD
// =============================================================================

interface DashboardProps {
  currentSection: Section
  setCurrentSection: (section: Section) => void
}

function Dashboard({ currentSection, setCurrentSection }: DashboardProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  const renderSection = () => {
    switch (currentSection) {
      case "dashboard":
        return <DashboardSection />
      case "catalog":
        return <CatalogSection />
      case "finances":
        return <FinancesSection />
      case "disputes":
        return <DisputesSection />
      case "schedule":
        return <ScheduleSection />
      case "support":
        return <SupportSection />
      default:
        return <DashboardSection />
    }
  }

  return (
    <div className="flex h-screen bg-background">
      <Sidebar
        currentSection={currentSection}
        onNavigate={setCurrentSection}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <main className="flex-1 overflow-auto">
        <div className="p-6">{renderSection()}</div>
      </main>
    </div>
  )
}

// =============================================================================
// MAIN APP CONTENT (with presentation control integration)
// =============================================================================

function AppContent() {
  const { isAuthenticated, isLoading, user, login, logout } = useAuth()
  const [authView, setAuthView] = useState<AuthView>("login")
  const [currentSection, setCurrentSection] = useState<Section>("dashboard")
  const [activeTool, setActiveTool] = useState<string | null>(null)
  const [lastAction, setLastAction] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState("demo1")

  useEffect(() => {
    setSessionId(resolveSessionId())
  }, [])

  const handleSessionChange = useCallback((nextSessionId: string | null) => {
    const trimmedSessionId = nextSessionId?.trim() || ""

    if (typeof window === "undefined") return

    const url = new URL(window.location.href)

    if (trimmedSessionId) {
      url.searchParams.set("session_id", trimmedSessionId)
      window.history.replaceState({}, "", url)
      setSessionId(trimmedSessionId)
      return
    }

    url.searchParams.delete("session_id")
    window.history.replaceState({}, "", url)
    setSessionId(resolveSessionId())
  }, [])

  // Navigation handler
  const handleNavigate = useCallback((section: string): boolean => {
    const validSections: Section[] = ["dashboard", "catalog", "finances", "disputes", "schedule", "support"]
    if (validSections.includes(section as Section)) {
      setCurrentSection(section as Section)
      setLastAction(`navigate:${section}`)
      return true
    }
    return false
  }, [])

  // Auth view handler
  const handleSetAuthView = useCallback((view: string) => {
    const validViews: AuthView[] = ["login", "register", "forgot-password"]
    if (validViews.includes(view as AuthView)) {
      setAuthView(view as AuthView)
      setLastAction(`auth_view:${view}`)
    }
  }, [])

  // Login handler for presentation control
  const handleLogin = useCallback(async (email: string, password: string) => {
    const success = await login(email, password)
    if (success) {
      setLastAction("login:success")
    }
    return success
  }, [login])

  // Logout handler
  const handleLogout = useCallback(() => {
    logout()
    setLastAction("logout")
    setAuthView("login")
  }, [logout])

  // Get form fields for state reporting
  const getFormFields = useCallback(() => {
    const fields: Record<string, string> = {}
    const inputs = document.querySelectorAll<HTMLInputElement>("input, textarea, select")
    inputs.forEach(input => {
      if (input.id || input.name) {
        fields[input.id || input.name] = input.value
      }
    })
    return fields
  }, [])

  // Presentation control hook
  const presentation = usePresentationControl({
    sessionId,
    onNavigate: handleNavigate,
    onSetAuthView: handleSetAuthView,
    onLogin: handleLogin,
    onLogout: handleLogout,
    getFormFields,
    isAuthenticated,
    currentSection: isAuthenticated ? currentSection : null,
    authView: isAuthenticated ? null : authView,
    user: user ? {
      email: user.email,
      name: user.name,
      storeId: user.storeId,
      storeName: user.storeName,
    } : null,
  })

  // Loading state
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#FF4940] border-t-transparent" />
      </div>
    )
  }

  return (
    <>
      {/* Main Content */}
      {isAuthenticated ? (
        <Dashboard 
          currentSection={currentSection} 
          setCurrentSection={setCurrentSection}
        />
      ) : (
        <AuthScreen 
          authView={authView} 
          setAuthView={setAuthView}
        />
      )}

      {/* Presentation Overlays */}
      <PresentationOverlays
        highlights={presentation.highlights}
        tooltips={presentation.tooltips}
        cards={presentation.cards}
        onDismissCard={presentation.removeCard}
      />

      {/* Debug Panel - only visible with ?ai_debug=true */}
      <AIDebugPanel
        currentSection={currentSection}
        activeTool={activeTool}
        lastAction={lastAction}
        sessionId={sessionId}
        onSessionChange={handleSessionChange}
        isConnected={presentation.isConnected}
        commandHistory={presentation.commandHistory}
        onNavigate={handleNavigate}
        onExecuteCommand={presentation.executeCommand}
      />
    </>
  )
}

// =============================================================================
// ROOT COMPONENT
// =============================================================================

export default function Home() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}
