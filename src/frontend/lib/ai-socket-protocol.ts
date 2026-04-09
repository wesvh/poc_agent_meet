// AI WebSocket Protocol for Demo/Presentation Control
// Allows remote control of the SPA via WebSocket commands

// =============================================================================
// COMMAND TYPES
// =============================================================================

export type AICommandType =
  // Navigation
  | "navigate"           // Navigate to a section (dashboard, catalog, etc.)
  | "set_auth_view"      // Switch auth view (login, register, forgot-password)
  
  // Input manipulation
  | "type_text"          // Type text into an input field (with typing animation)
  | "set_field"          // Set field value instantly
  | "clear_field"        // Clear a field
  
  // Button/Action
  | "click_button"       // Click a button by ID or data attribute
  | "submit_form"        // Submit a form
  
  // Visual feedback
  | "highlight"          // Highlight an element
  | "show_tooltip"       // Show a tooltip near an element
  | "show_card"          // Show an info card overlay
  | "clear_overlays"     // Clear all visual overlays
  
  // Auth simulation
  | "simulate_login"     // Auto-fill and submit login
  | "simulate_logout"    // Logout the user
  
  // Presentation
  | "show_slide"         // Show a slide full-screen (slide 1-7)
  | "hide_slide"         // Hide the current slide

  // State
  | "get_state"          // Get current app state
  | "wait"               // Wait for X milliseconds

// =============================================================================
// COMMAND PAYLOADS
// =============================================================================

export interface NavigatePayload {
  section: "dashboard" | "catalog" | "finances" | "disputes" | "schedule" | "support"
}

export interface SetAuthViewPayload {
  view: "login" | "register" | "forgot-password"
}

export interface TypeTextPayload {
  selector: string      // CSS selector or field ID
  text: string          // Text to type
  speed?: number        // ms per character (default: 50)
  clear?: boolean       // Clear field before typing (default: true)
}

export interface SetFieldPayload {
  selector: string
  value: string
}

export interface ClearFieldPayload {
  selector: string
}

export interface ClickButtonPayload {
  selector: string      // CSS selector, button ID, or data-action attribute
  delay?: number        // Delay before click in ms
}

export interface SubmitFormPayload {
  formSelector?: string // If not provided, submits the first form
}

export interface HighlightPayload {
  selector: string
  style?: "pulse" | "glow" | "outline" | "shake"
  color?: string        // Custom color (default: Rappi coral)
  duration?: number     // ms, 0 = until cleared
  label?: string        // Optional label to show
}

export interface ShowTooltipPayload {
  selector: string      // Element to attach tooltip to
  text: string
  position?: "top" | "bottom" | "left" | "right"
  duration?: number
}

export interface ShowCardPayload {
  id?: string
  title: string
  body: string
  type: "info" | "warning" | "success" | "error"
  position?: "center" | "top-right" | "bottom-right"
  dismissible?: boolean
  duration?: number
}

export interface ClearOverlaysPayload {
  scope?: "all" | "highlights" | "tooltips" | "cards"
}

export interface SimulateLoginPayload {
  email?: string        // Default: admin@latoscana.com
  password?: string     // Default: demo123
  typeSpeed?: number    // Typing animation speed
}

export interface WaitPayload {
  ms: number
}

export interface ShowSlidePayload {
  slide: number  // 1-7
}

// =============================================================================
// COMMAND STRUCTURE
// =============================================================================

export interface AICommand {
  cmd: AICommandType
  payload?: Record<string, unknown>
  request_id?: string
  timestamp?: string
}

// =============================================================================
// RESPONSE STRUCTURE
// =============================================================================

export interface AIResponse {
  type: "ack" | "state" | "error" | "complete"
  request_id?: string
  data?: unknown
  error?: string
  timestamp: string
}

// =============================================================================
// APP STATE (for get_state command)
// =============================================================================

export interface AppState {
  // Auth
  is_authenticated: boolean
  auth_view: "login" | "register" | "forgot-password" | null
  user: {
    email: string
    name: string
    store_id: string
    store_name: string
  } | null
  
  // Navigation
  current_section: string | null
  
  // UI State
  active_overlays: {
    highlights: string[]
    tooltips: string[]
    cards: string[]
  }
  
  // Form State (current visible form)
  form_fields: Record<string, string>
  
  // Connection
  is_connected: boolean
  session_id: string
}

// =============================================================================
// VALIDATION
// =============================================================================

const VALID_COMMANDS: AICommandType[] = [
  "navigate",
  "set_auth_view",
  "type_text",
  "set_field",
  "clear_field",
  "click_button",
  "submit_form",
  "highlight",
  "show_tooltip",
  "show_card",
  "clear_overlays",
  "simulate_login",
  "simulate_logout",
  "show_slide",
  "hide_slide",
  "get_state",
  "wait",
]

export function validateCommand(data: unknown): AICommand | null {
  if (!data || typeof data !== "object") return null
  
  const cmd = data as Record<string, unknown>
  
  if (typeof cmd.cmd !== "string") return null
  if (!VALID_COMMANDS.includes(cmd.cmd as AICommandType)) return null
  
  return {
    cmd: cmd.cmd as AICommandType,
    payload: cmd.payload as Record<string, unknown> | undefined,
    request_id: cmd.request_id as string | undefined,
    timestamp: cmd.timestamp as string || new Date().toISOString(),
  }
}

// =============================================================================
// PROTOCOL EXAMPLES (Documentation for AI agents)
// =============================================================================

export const protocolExamples = {
  // Navigation
  navigate_to_catalog: {
    cmd: "navigate",
    payload: { section: "catalog" }
  },
  
  switch_to_register: {
    cmd: "set_auth_view",
    payload: { view: "register" }
  },
  
  // Input manipulation
  type_email: {
    cmd: "type_text",
    payload: {
      selector: "#email",
      text: "admin@latoscana.com",
      speed: 50,
      clear: true
    }
  },
  
  set_password: {
    cmd: "set_field",
    payload: {
      selector: "#password",
      value: "demo123"
    }
  },
  
  // Buttons
  click_login: {
    cmd: "click_button",
    payload: {
      selector: "[data-action='login']",
      delay: 500
    }
  },
  
  submit_login_form: {
    cmd: "submit_form",
    payload: {}
  },
  
  // Visual feedback
  highlight_field: {
    cmd: "highlight",
    payload: {
      selector: "#email",
      style: "pulse",
      duration: 2000,
      label: "Ingresa tu correo aquí"
    }
  },
  
  show_tooltip: {
    cmd: "show_tooltip",
    payload: {
      selector: "#password",
      text: "Mínimo 8 caracteres",
      position: "right",
      duration: 3000
    }
  },
  
  show_success_card: {
    cmd: "show_card",
    payload: {
      title: "Inicio de sesión exitoso",
      body: "Bienvenido al Portal Partners",
      type: "success",
      position: "top-right",
      duration: 3000
    }
  },
  
  // Auth simulation
  auto_login: {
    cmd: "simulate_login",
    payload: {
      email: "admin@latoscana.com",
      password: "demo123",
      typeSpeed: 30
    }
  },
  
  logout: {
    cmd: "simulate_logout",
    payload: {}
  },
  
  // State
  get_current_state: {
    cmd: "get_state",
    payload: {}
  },
  
  // Timing
  wait_2_seconds: {
    cmd: "wait",
    payload: { ms: 2000 }
  },
  
  clear_all: {
    cmd: "clear_overlays",
    payload: { scope: "all" }
  }
}

// =============================================================================
// DEMO SEQUENCES
// =============================================================================

export const demoSequences = {
  login_demo: [
    { cmd: "highlight", payload: { selector: "#email", style: "pulse", duration: 2000 } },
    { cmd: "wait", payload: { ms: 500 } },
    { cmd: "type_text", payload: { selector: "#email", text: "admin@latoscana.com", speed: 40 } },
    { cmd: "wait", payload: { ms: 300 } },
    { cmd: "highlight", payload: { selector: "#password", style: "pulse", duration: 2000 } },
    { cmd: "wait", payload: { ms: 500 } },
    { cmd: "type_text", payload: { selector: "#password", text: "demo123", speed: 60 } },
    { cmd: "wait", payload: { ms: 500 } },
    { cmd: "click_button", payload: { selector: "[type='submit']" } },
  ],
  
  tour_dashboard: [
    { cmd: "show_card", payload: { title: "Dashboard", body: "Aquí puedes ver el resumen de tu negocio", type: "info", duration: 3000 } },
    { cmd: "wait", payload: { ms: 3500 } },
    { cmd: "navigate", payload: { section: "catalog" } },
    { cmd: "show_card", payload: { title: "Catálogo", body: "Gestiona tus productos y precios", type: "info", duration: 3000 } },
    { cmd: "wait", payload: { ms: 3500 } },
    { cmd: "navigate", payload: { section: "finances" } },
    { cmd: "show_card", payload: { title: "Finanzas", body: "Revisa tus pagos y balance", type: "info", duration: 3000 } },
  ]
}
