"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import type { AICommand, AIResponse, AppState } from "@/lib/ai-socket-protocol"
import { validateCommand } from "@/lib/ai-socket-protocol"

// =============================================================================
// TYPES
// =============================================================================

interface Highlight {
  id: string
  selector: string
  style: "pulse" | "glow" | "outline" | "shake"
  color?: string
  label?: string
}

interface Tooltip {
  id: string
  selector: string
  text: string
  position: "top" | "bottom" | "left" | "right"
}

interface Card {
  id: string
  title: string
  body: string
  type: "info" | "warning" | "success" | "error"
  position: "center" | "top-right" | "bottom-right"
  dismissible: boolean
}

interface PresentationState {
  highlights: Highlight[]
  tooltips: Tooltip[]
  cards: Card[]
  isTyping: boolean
  commandQueue: AICommand[]
  isProcessing: boolean
}

interface UsePresentationControlOptions {
  sessionId: string
  onNavigate?: (section: string) => boolean
  onSetAuthView?: (view: string) => void
  onLogin?: (email: string, password: string) => Promise<boolean>
  onLogout?: () => void
  getFormFields?: () => Record<string, string>
  isAuthenticated?: boolean
  currentSection?: string | null
  authView?: string | null
  user?: { email: string; name: string; storeId: string; storeName: string } | null
}

// =============================================================================
// HOOK
// =============================================================================

export function usePresentationControl(options: UsePresentationControlOptions) {
  const {
    sessionId,
    onNavigate,
    onSetAuthView,
    onLogin,
    onLogout,
    getFormFields,
    isAuthenticated = false,
    currentSection = null,
    authView = "login",
    user = null,
  } = options

  const [state, setState] = useState<PresentationState>({
    highlights: [],
    tooltips: [],
    cards: [],
    isTyping: false,
    commandQueue: [],
    isProcessing: false,
  })

  const [isConnected, setIsConnected] = useState(false)
  const [commandHistory, setCommandHistory] = useState<AICommand[]>([])

  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const commandQueueRef = useRef<AICommand[]>([])
  const processingRef = useRef(false)
  const processCommandRef = useRef<(command: AICommand) => Promise<AIResponse>>(async () => ({
    type: "error",
    error: "Command processor not ready",
    timestamp: new Date().toISOString(),
  }))

  // ===========================================================================
  // UTILITY FUNCTIONS
  // ===========================================================================

  const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

  const generateId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`

  const setNativeInputValue = (
    element: HTMLInputElement | HTMLTextAreaElement,
    value: string
  ) => {
    const prototype = Object.getPrototypeOf(element) as HTMLInputElement | HTMLTextAreaElement
    const valueSetter = Object.getOwnPropertyDescriptor(prototype, "value")?.set

    if (valueSetter) {
      valueSetter.call(element, value)
    } else {
      element.value = value
    }

    element.dispatchEvent(new InputEvent("input", { bubbles: true, data: value }))
    element.dispatchEvent(new Event("change", { bubbles: true }))
  }

  const getElement = (selector: string): HTMLElement | null => {
    // Try direct selector first
    let element = document.querySelector<HTMLElement>(selector)
    if (element) return element

    // Try by ID
    element = document.getElementById(selector.replace("#", ""))
    if (element) return element

    // Try by data-action
    element = document.querySelector<HTMLElement>(`[data-action="${selector}"]`)
    if (element) return element

    // Try by name attribute
    element = document.querySelector<HTMLElement>(`[name="${selector}"]`)
    if (element) return element

    return null
  }

  // ===========================================================================
  // COMMAND HANDLERS
  // ===========================================================================

  const typeText = useCallback(async (
    selector: string,
    text: string,
    speed = 50,
    clear = true
  ) => {
    const element = getElement(selector) as HTMLInputElement | HTMLTextAreaElement
    if (!element) {
      console.warn(`[Presentation] Element not found: ${selector}`)
      return false
    }

    setState(s => ({ ...s, isTyping: true }))

    // Focus the element
    element.focus()

    // Clear if needed
    if (clear) {
      setNativeInputValue(element, "")
    }

    // Type each character
    let currentValue = clear ? "" : element.value
    for (const char of text) {
      currentValue += char
      setNativeInputValue(element, currentValue)
      await sleep(speed)
    }

    setState(s => ({ ...s, isTyping: false }))
    return true
  }, [])

  const setField = useCallback((selector: string, value: string) => {
    const element = getElement(selector) as HTMLInputElement | HTMLTextAreaElement
    if (!element) {
      console.warn(`[Presentation] Element not found: ${selector}`)
      return false
    }

    setNativeInputValue(element, value)
    return true
  }, [])

  const clearField = useCallback((selector: string) => {
    return setField(selector, "")
  }, [setField])

  const clickButton = useCallback(async (selector: string, delay = 0) => {
    if (delay > 0) await sleep(delay)

    const element = getElement(selector)
    if (!element) {
      console.warn(`[Presentation] Button not found: ${selector}`)
      return false
    }

    // Add visual feedback
    element.classList.add("ring-2", "ring-[#FF4940]", "ring-offset-2")
    await sleep(150)

    element.click()

    await sleep(300)
    element.classList.remove("ring-2", "ring-[#FF4940]", "ring-offset-2")

    return true
  }, [])

  const submitForm = useCallback((formSelector?: string) => {
    const form = formSelector
      ? document.querySelector<HTMLFormElement>(formSelector)
      : document.querySelector<HTMLFormElement>("form")

    if (!form) {
      console.warn(`[Presentation] Form not found`)
      return false
    }

    const submitBtn = form.querySelector<HTMLButtonElement>("[type='submit']")
    if (submitBtn) {
      submitBtn.click()
      return true
    }

    form.requestSubmit()
    return true
  }, [])

  const addHighlight = useCallback((
    selector: string,
    style: "pulse" | "glow" | "outline" | "shake" = "pulse",
    duration = 0,
    color?: string,
    label?: string
  ) => {
    const element = getElement(selector)
    if (!element) {
      console.warn(`[Presentation] Element not found for highlight: ${selector}`)
      return null
    }

    const id = generateId()

    // Add highlight class
    element.setAttribute("data-highlight", id)
    element.setAttribute("data-highlight-style", style)
    if (color) element.style.setProperty("--highlight-color", color)

    const highlight: Highlight = { id, selector, style, color, label }
    setState(s => ({ ...s, highlights: [...s.highlights, highlight] }))

    // Auto-remove after duration
    if (duration > 0) {
      setTimeout(() => removeHighlight(id), duration)
    }

    return id
  }, [])

  const removeHighlight = useCallback((id: string) => {
    setState(s => {
      const highlight = s.highlights.find(h => h.id === id)
      if (highlight) {
        const element = document.querySelector(`[data-highlight="${id}"]`)
        if (element) {
          element.removeAttribute("data-highlight")
          element.removeAttribute("data-highlight-style")
        }
      }
      return { ...s, highlights: s.highlights.filter(h => h.id !== id) }
    })
  }, [])

  const showTooltip = useCallback((
    selector: string,
    text: string,
    position: "top" | "bottom" | "left" | "right" = "top",
    duration = 3000
  ) => {
    const element = getElement(selector)
    if (!element) return null

    const id = generateId()
    const tooltip: Tooltip = { id, selector, text, position }

    setState(s => ({ ...s, tooltips: [...s.tooltips, tooltip] }))

    if (duration > 0) {
      setTimeout(() => removeTooltip(id), duration)
    }

    return id
  }, [])

  const removeTooltip = useCallback((id: string) => {
    setState(s => ({ ...s, tooltips: s.tooltips.filter(t => t.id !== id) }))
  }, [])

  const showCard = useCallback((
    title: string,
    body: string,
    type: "info" | "warning" | "success" | "error" = "info",
    position: "center" | "top-right" | "bottom-right" = "top-right",
    dismissible = true,
    duration = 0
  ) => {
    const id = generateId()
    const card: Card = { id, title, body, type, position, dismissible }

    setState(s => ({ ...s, cards: [...s.cards, card] }))

    if (duration > 0) {
      setTimeout(() => removeCard(id), duration)
    }

    return id
  }, [])

  const removeCard = useCallback((id: string) => {
    setState(s => ({ ...s, cards: s.cards.filter(c => c.id !== id) }))
  }, [])

  const clearOverlays = useCallback((scope: "all" | "highlights" | "tooltips" | "cards" = "all") => {
    setState(s => {
      // Remove all highlight attributes from DOM
      if (scope === "all" || scope === "highlights") {
        document.querySelectorAll("[data-highlight]").forEach(el => {
          el.removeAttribute("data-highlight")
          el.removeAttribute("data-highlight-style")
        })
      }

      return {
        ...s,
        highlights: scope === "all" || scope === "highlights" ? [] : s.highlights,
        tooltips: scope === "all" || scope === "tooltips" ? [] : s.tooltips,
        cards: scope === "all" || scope === "cards" ? [] : s.cards,
      }
    })
  }, [])

  const simulateLogin = useCallback(async (
    email = "admin@latoscana.com",
    password = "demo123",
    typeSpeed = 50
  ) => {
    // Make sure we're on login view
    if (isAuthenticated) return true

    // Type email
    await typeText("#email", email, typeSpeed)
    await sleep(300)

    // Type password
    await typeText("#password", password, typeSpeed)
    await sleep(500)

    // Submit
    if (onLogin) {
      return await onLogin(email, password)
    }

    submitForm()
    return true
  }, [isAuthenticated, typeText, onLogin, submitForm])

  const getState = useCallback((): AppState => {
    return {
      is_authenticated: isAuthenticated,
      auth_view: isAuthenticated ? null : (authView as "login" | "register" | "forgot-password"),
      user: user ? {
        email: user.email,
        name: user.name,
        store_id: user.storeId,
        store_name: user.storeName,
      } : null,
      current_section: currentSection,
      active_overlays: {
        highlights: state.highlights.map(h => h.selector),
        tooltips: state.tooltips.map(t => t.selector),
        cards: state.cards.map(c => c.id),
      },
      form_fields: getFormFields ? getFormFields() : {},
      is_connected: isConnected,
      session_id: sessionId,
    }
  }, [isAuthenticated, authView, user, currentSection, state, getFormFields, isConnected, sessionId])

  // ===========================================================================
  // COMMAND PROCESSOR
  // ===========================================================================

  const processCommand = useCallback(async (command: AICommand): Promise<AIResponse> => {
    const { cmd, payload = {}, request_id } = command

    try {
      switch (cmd) {
        case "navigate":
          const navSuccess = onNavigate?.(payload.section as string) ?? false
          return { type: navSuccess ? "complete" : "error", request_id, timestamp: new Date().toISOString() }

        case "set_auth_view":
          onSetAuthView?.(payload.view as string)
          return { type: "complete", request_id, timestamp: new Date().toISOString() }

        case "type_text":
          await typeText(
            payload.selector as string,
            payload.text as string,
            payload.speed as number,
            payload.clear as boolean
          )
          return { type: "complete", request_id, timestamp: new Date().toISOString() }

        case "set_field":
          setField(payload.selector as string, payload.value as string)
          return { type: "complete", request_id, timestamp: new Date().toISOString() }

        case "clear_field":
          clearField(payload.selector as string)
          return { type: "complete", request_id, timestamp: new Date().toISOString() }

        case "click_button":
          await clickButton(payload.selector as string, payload.delay as number)
          return { type: "complete", request_id, timestamp: new Date().toISOString() }

        case "submit_form":
          submitForm(payload.formSelector as string)
          return { type: "complete", request_id, timestamp: new Date().toISOString() }

        case "highlight":
          addHighlight(
            payload.selector as string,
            payload.style as "pulse" | "glow" | "outline" | "shake",
            payload.duration as number,
            payload.color as string,
            payload.label as string
          )
          return { type: "complete", request_id, timestamp: new Date().toISOString() }

        case "show_tooltip":
          showTooltip(
            payload.selector as string,
            payload.text as string,
            payload.position as "top" | "bottom" | "left" | "right",
            payload.duration as number
          )
          return { type: "complete", request_id, timestamp: new Date().toISOString() }

        case "show_card":
          showCard(
            payload.title as string,
            payload.body as string,
            payload.type as "info" | "warning" | "success" | "error",
            payload.position as "center" | "top-right" | "bottom-right",
            payload.dismissible as boolean,
            payload.duration as number
          )
          return { type: "complete", request_id, timestamp: new Date().toISOString() }

        case "clear_overlays":
          clearOverlays(payload.scope as "all" | "highlights" | "tooltips" | "cards")
          return { type: "complete", request_id, timestamp: new Date().toISOString() }

        case "simulate_login":
          await simulateLogin(
            payload.email as string,
            payload.password as string,
            payload.typeSpeed as number
          )
          return { type: "complete", request_id, timestamp: new Date().toISOString() }

        case "simulate_logout":
          onLogout?.()
          return { type: "complete", request_id, timestamp: new Date().toISOString() }

        case "get_state":
          return { type: "state", request_id, data: getState(), timestamp: new Date().toISOString() }

        case "wait":
          await sleep(payload.ms as number || 1000)
          return { type: "complete", request_id, timestamp: new Date().toISOString() }

        default:
          return { type: "error", request_id, error: `Unknown command: ${cmd}`, timestamp: new Date().toISOString() }
      }
    } catch (error) {
      return {
        type: "error",
        request_id,
        error: error instanceof Error ? error.message : "Unknown error",
        timestamp: new Date().toISOString(),
      }
    }
  }, [
    onNavigate, onSetAuthView, typeText, setField, clearField, clickButton,
    submitForm, addHighlight, showTooltip, showCard, clearOverlays,
    simulateLogin, onLogout, getState
  ])

  useEffect(() => {
    processCommandRef.current = processCommand
  }, [processCommand])

  const enqueueCommand = useCallback((command: AICommand) => {
    commandQueueRef.current = [...commandQueueRef.current, command]
    setState((prev) => ({
      ...prev,
      commandQueue: commandQueueRef.current,
    }))

    if (processingRef.current) {
      return
    }

    processingRef.current = true
    setState((prev) => ({
      ...prev,
      isProcessing: true,
    }))

    void (async () => {
      try {
        while (commandQueueRef.current.length > 0) {
          const [nextCommand, ...rest] = commandQueueRef.current
          commandQueueRef.current = rest

          setState((prev) => ({
            ...prev,
            commandQueue: commandQueueRef.current,
          }))

          await processCommandRef.current(nextCommand)
        }
      } finally {
        processingRef.current = false
        setState((prev) => ({
          ...prev,
          isProcessing: false,
          commandQueue: commandQueueRef.current,
        }))
      }
    })()
  }, [])

  // ===========================================================================
  // POLLING CONNECTION
  // ===========================================================================

  const connect = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
    }

    const url = `/api/ai-socket/poll?session_id=${sessionId}&token=rappi_ai_agent_2024`

    const poll = async () => {
      try {
        const res = await fetch(url, { cache: "no-store" })
        if (!res.ok) {
          setIsConnected(false)
          return
        }
        const { commands } = await res.json() as { commands: unknown[] }
        setIsConnected(true)
        for (const raw of commands) {
          const command = validateCommand(raw)
          if (command) {
            setCommandHistory(h => [...h.slice(-19), command])
            enqueueCommand(command)
          }
        }
      } catch {
        setIsConnected(false)
      }
    }

    void poll()
    pollIntervalRef.current = setInterval(() => { void poll() }, 1000)
  }, [sessionId, enqueueCommand])

  const disconnect = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
    setIsConnected(false)
  }, [])

  // Auto-connect on mount
  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  // ===========================================================================
  // MANUAL COMMAND EXECUTION (for testing)
  // ===========================================================================

  const executeCommand = useCallback(async (command: AICommand) => {
    setCommandHistory(h => [...h.slice(-19), command])
    enqueueCommand(command)
    return {
      type: "ack",
      request_id: command.request_id,
      timestamp: new Date().toISOString(),
    } satisfies AIResponse
  }, [enqueueCommand])

  // ===========================================================================
  // RETURN
  // ===========================================================================

  return {
    // State
    state,
    isConnected,
    commandHistory,

    // Overlays
    highlights: state.highlights,
    tooltips: state.tooltips,
    cards: state.cards,

    // Actions
    clearOverlays,
    removeCard,

    // Manual control
    executeCommand,
    processCommand,

    // Connection
    connect,
    disconnect,

    // State getter
    getState,
  }
}
