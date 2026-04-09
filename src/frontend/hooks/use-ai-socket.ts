"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import {
  type AICommand,
  type AIResponse,
  type SessionState,
  type ShowCardPayload,
  type ChecklistItem,
  type UpdateFieldPayload,
  type HighlightPayload,
  type ShowTimerPayload,
  initialSessionState,
  validateCommand,
} from "@/lib/ai-socket-protocol"
import { generateAIContextPayload } from "@/lib/ai-context"

interface UseAISocketOptions {
  sessionId: string
  token: string
  onNavigate?: (view: string) => void
  onToolExecute?: (tool: string, params: Record<string, unknown>) => Promise<unknown>
  userContext?: {
    store_id: string | null
    store_name: string | null
    is_authenticated: boolean
  }
  currentSection?: string
  enabled?: boolean
}

interface UseAISocketReturn {
  isConnected: boolean
  sessionState: SessionState
  lastCommand: AICommand | null
  commandHistory: AICommand[]
  sendResponse: (response: Omit<AIResponse, "timestamp">) => void
  clearCards: () => void
  clearHighlights: () => void
  connectionError: string | null
}

export function useAISocket({
  sessionId,
  token,
  onNavigate,
  onToolExecute,
  userContext,
  currentSection = "dashboard",
  enabled = true,
}: UseAISocketOptions): UseAISocketReturn {
  const [isConnected, setIsConnected] = useState(false)
  const [sessionState, setSessionState] = useState<SessionState>(initialSessionState)
  const [lastCommand, setLastCommand] = useState<AICommand | null>(null)
  const [commandHistory, setCommandHistory] = useState<AICommand[]>([])
  const [connectionError, setConnectionError] = useState<string | null>(null)
  
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const highlightTimeoutsRef = useRef<Map<string, NodeJS.Timeout>>(new Map())
  const cardTimeoutsRef = useRef<Map<string, NodeJS.Timeout>>(new Map())

  // Send response back to server
  const sendResponse = useCallback((response: Omit<AIResponse, "timestamp">) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        ...response,
        timestamp: new Date().toISOString(),
      }))
    }
  }, [])

  // Clear cards manually
  const clearCards = useCallback(() => {
    setSessionState((prev) => ({ ...prev, cards: [] }))
  }, [])

  // Clear highlights manually
  const clearHighlights = useCallback(() => {
    highlightTimeoutsRef.current.forEach((timeout) => clearTimeout(timeout))
    highlightTimeoutsRef.current.clear()
    setSessionState((prev) => ({ ...prev, highlights: new Map() }))
  }, [])

  // Handle incoming commands
  const handleCommand = useCallback(async (command: AICommand) => {
    setLastCommand(command)
    setCommandHistory((prev) => [...prev.slice(-49), command])

    switch (command.cmd) {
      case "navigate": {
        const view = (command.payload as { view: string })?.view
        if (view && onNavigate) {
          onNavigate(view)
          sendResponse({
            type: "ack",
            request_id: command.request_id,
            data: { navigated_to: view },
          })
        }
        break
      }

      case "show_card": {
        const card = command.payload as ShowCardPayload
        const cardId = card.id || `card_${Date.now()}`
        const cardWithId = { ...card, id: cardId }
        
        setSessionState((prev) => ({
          ...prev,
          cards: [...prev.cards, cardWithId],
        }))

        // Auto-dismiss if duration is set
        if (card.duration && card.duration > 0) {
          const timeout = setTimeout(() => {
            setSessionState((prev) => ({
              ...prev,
              cards: prev.cards.filter((c) => c.id !== cardId),
            }))
            cardTimeoutsRef.current.delete(cardId)
          }, card.duration)
          cardTimeoutsRef.current.set(cardId, timeout)
        }

        sendResponse({
          type: "ack",
          request_id: command.request_id,
          data: { card_id: cardId },
        })
        break
      }

      case "highlight": {
        const highlight = command.payload as HighlightPayload
        
        setSessionState((prev) => {
          const newHighlights = new Map(prev.highlights)
          newHighlights.set(highlight.element_id, highlight)
          return { ...prev, highlights: newHighlights }
        })

        // Auto-remove highlight after duration
        if (highlight.duration && highlight.duration > 0) {
          const existingTimeout = highlightTimeoutsRef.current.get(highlight.element_id)
          if (existingTimeout) clearTimeout(existingTimeout)

          const timeout = setTimeout(() => {
            setSessionState((prev) => {
              const newHighlights = new Map(prev.highlights)
              newHighlights.delete(highlight.element_id)
              return { ...prev, highlights: newHighlights }
            })
            highlightTimeoutsRef.current.delete(highlight.element_id)
          }, highlight.duration)
          highlightTimeoutsRef.current.set(highlight.element_id, timeout)
        }

        sendResponse({
          type: "ack",
          request_id: command.request_id,
        })
        break
      }

      case "update_field": {
        const field = command.payload as UpdateFieldPayload
        
        setSessionState((prev) => {
          const newFields = new Map(prev.verified_fields)
          newFields.set(field.field, field)
          return { ...prev, verified_fields: newFields }
        })

        sendResponse({
          type: "ack",
          request_id: command.request_id,
        })
        break
      }

      case "show_checklist": {
        const { items } = command.payload as { title?: string; items: ChecklistItem[] }
        
        setSessionState((prev) => ({
          ...prev,
          checklist: items,
        }))

        sendResponse({
          type: "ack",
          request_id: command.request_id,
        })
        break
      }

      case "show_timer": {
        const timer = command.payload as ShowTimerPayload
        
        setSessionState((prev) => ({
          ...prev,
          timer,
        }))

        sendResponse({
          type: "ack",
          request_id: command.request_id,
        })
        break
      }

      case "clear": {
        const scope = (command.payload as { scope?: string })?.scope || "all"
        
        setSessionState((prev) => {
          const newState = { ...prev }
          
          if (scope === "all" || scope === "cards") {
            newState.cards = []
            cardTimeoutsRef.current.forEach((t) => clearTimeout(t))
            cardTimeoutsRef.current.clear()
          }
          if (scope === "all" || scope === "highlights") {
            newState.highlights = new Map()
            highlightTimeoutsRef.current.forEach((t) => clearTimeout(t))
            highlightTimeoutsRef.current.clear()
          }
          if (scope === "all" || scope === "checklist") {
            newState.checklist = []
          }
          if (scope === "all" || scope === "timer") {
            newState.timer = null
          }
          
          return newState
        })

        sendResponse({
          type: "ack",
          request_id: command.request_id,
        })
        break
      }

      case "agent_speaking": {
        const { is_speaking, message } = command.payload as { is_speaking: boolean; message?: string }
        
        setSessionState((prev) => ({
          ...prev,
          agent_speaking: is_speaking,
          agent_message: message || null,
        }))

        sendResponse({
          type: "ack",
          request_id: command.request_id,
        })
        break
      }

      case "execute_tool": {
        const { tool, parameters } = command.payload as { tool: string; parameters: Record<string, unknown> }
        
        if (onToolExecute) {
          try {
            const result = await onToolExecute(tool, parameters)
            sendResponse({
              type: "tool_result",
              request_id: command.request_id,
              data: result,
            })
          } catch (error) {
            sendResponse({
              type: "error",
              request_id: command.request_id,
              error: error instanceof Error ? error.message : "Tool execution failed",
            })
          }
        } else {
          sendResponse({
            type: "error",
            request_id: command.request_id,
            error: "Tool execution not supported",
          })
        }
        break
      }

      case "request_context": {
        const context = generateAIContextPayload(
          currentSection,
          userContext || { store_id: null, store_name: null, is_authenticated: false },
          null,
          lastCommand?.cmd || null
        )

        sendResponse({
          type: "context",
          request_id: command.request_id,
          data: context,
        })
        break
      }

      default:
        // Unknown command - ignore gracefully
        sendResponse({
          type: "error",
          request_id: command.request_id,
          error: `Unknown command: ${command.cmd}`,
        })
    }
  }, [onNavigate, onToolExecute, sendResponse, currentSection, userContext, lastCommand])

  // WebSocket connection management
  useEffect(() => {
    if (!enabled || !sessionId || !token) return

    const connect = () => {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
      const wsUrl = `${protocol}//${window.location.host}/api/ai-socket?session_id=${sessionId}&token=${token}`

      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        setConnectionError(null)
        setSessionState((prev) => ({ ...prev, is_connected: true }))
        
        // Send initial context
        sendResponse({
          type: "context",
          data: {
            event: "connected",
            session_id: sessionId,
            current_section: currentSection,
            user_context: userContext,
          },
        })
      }

      ws.onmessage = (event) => {
        // Skip binary messages (audio)
        if (event.data instanceof ArrayBuffer) return

        try {
          const data = JSON.parse(event.data)
          const command = validateCommand(data)
          
          if (command) {
            handleCommand(command)
          }
        } catch {
          // Ignore invalid JSON
        }
      }

      ws.onerror = () => {
        setConnectionError("WebSocket connection error")
      }

      ws.onclose = () => {
        setIsConnected(false)
        setSessionState((prev) => ({ ...prev, is_connected: false }))

        // Attempt reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(connect, 3000)
      }
    }

    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
      // Clear all timeouts
      highlightTimeoutsRef.current.forEach((t) => clearTimeout(t))
      cardTimeoutsRef.current.forEach((t) => clearTimeout(t))
    }
  }, [enabled, sessionId, token, handleCommand, sendResponse, currentSection, userContext])

  // Update session state with current section
  useEffect(() => {
    setSessionState((prev) => ({ ...prev, current_section: currentSection }))
  }, [currentSection])

  return {
    isConnected,
    sessionState,
    lastCommand,
    commandHistory,
    sendResponse,
    clearCards,
    clearHighlights,
    connectionError,
  }
}
