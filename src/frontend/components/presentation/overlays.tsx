"use client"

import { useEffect, useState, useRef } from "react"
import { X, Info, AlertTriangle, CheckCircle, XCircle } from "lucide-react"
import { cn } from "@/lib/utils"

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

// =============================================================================
// HIGHLIGHT OVERLAY
// =============================================================================

interface HighlightOverlayProps {
  highlights: Highlight[]
}

export function HighlightOverlay({ highlights }: HighlightOverlayProps) {
  const [positions, setPositions] = useState<Map<string, DOMRect>>(new Map())

  useEffect(() => {
    const updatePositions = () => {
      const newPositions = new Map<string, DOMRect>()
      highlights.forEach(h => {
        const element = document.querySelector(h.selector) || 
                       document.getElementById(h.selector.replace("#", ""))
        if (element) {
          newPositions.set(h.id, element.getBoundingClientRect())
        }
      })
      setPositions(newPositions)
    }

    updatePositions()
    window.addEventListener("resize", updatePositions)
    window.addEventListener("scroll", updatePositions, true)
    
    const interval = setInterval(updatePositions, 100)

    return () => {
      window.removeEventListener("resize", updatePositions)
      window.removeEventListener("scroll", updatePositions, true)
      clearInterval(interval)
    }
  }, [highlights])

  if (highlights.length === 0) return null

  return (
    <div className="pointer-events-none fixed inset-0 z-[9999]">
      {highlights.map(highlight => {
        const rect = positions.get(highlight.id)
        if (!rect) return null

        const color = highlight.color || "#FF4940"

        return (
          <div key={highlight.id}>
            {/* Highlight box */}
            <div
              className={cn(
                "absolute rounded-lg transition-all",
                highlight.style === "pulse" && "animate-pulse",
                highlight.style === "shake" && "animate-shake",
              )}
              style={{
                top: rect.top - 4,
                left: rect.left - 4,
                width: rect.width + 8,
                height: rect.height + 8,
                boxShadow: highlight.style === "glow" 
                  ? `0 0 20px 5px ${color}40, 0 0 40px 10px ${color}20`
                  : `0 0 0 3px ${color}`,
                border: highlight.style === "outline" ? `3px solid ${color}` : "none",
              }}
            />
            
            {/* Label */}
            {highlight.label && (
              <div
                className="absolute rounded-md px-3 py-1.5 text-sm font-medium text-white shadow-lg"
                style={{
                  top: rect.top - 36,
                  left: rect.left,
                  backgroundColor: color,
                }}
              >
                {highlight.label}
                <div
                  className="absolute left-4 top-full h-0 w-0"
                  style={{
                    borderLeft: "6px solid transparent",
                    borderRight: "6px solid transparent",
                    borderTop: `6px solid ${color}`,
                  }}
                />
              </div>
            )}
          </div>
        )
      })}

      <style jsx global>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-5px); }
          75% { transform: translateX(5px); }
        }
        .animate-shake {
          animation: shake 0.5s ease-in-out infinite;
        }
      `}</style>
    </div>
  )
}

// =============================================================================
// TOOLTIP OVERLAY
// =============================================================================

interface TooltipOverlayProps {
  tooltips: Tooltip[]
}

export function TooltipOverlay({ tooltips }: TooltipOverlayProps) {
  const [positions, setPositions] = useState<Map<string, DOMRect>>(new Map())

  useEffect(() => {
    const updatePositions = () => {
      const newPositions = new Map<string, DOMRect>()
      tooltips.forEach(t => {
        const element = document.querySelector(t.selector) ||
                       document.getElementById(t.selector.replace("#", ""))
        if (element) {
          newPositions.set(t.id, element.getBoundingClientRect())
        }
      })
      setPositions(newPositions)
    }

    updatePositions()
    window.addEventListener("resize", updatePositions)
    window.addEventListener("scroll", updatePositions, true)

    return () => {
      window.removeEventListener("resize", updatePositions)
      window.removeEventListener("scroll", updatePositions, true)
    }
  }, [tooltips])

  if (tooltips.length === 0) return null

  return (
    <div className="pointer-events-none fixed inset-0 z-[10000]">
      {tooltips.map(tooltip => {
        const rect = positions.get(tooltip.id)
        if (!rect) return null

        let top = 0
        let left = 0
        let arrowClass = ""

        switch (tooltip.position) {
          case "top":
            top = rect.top - 40
            left = rect.left + rect.width / 2
            arrowClass = "bottom-0 left-1/2 -translate-x-1/2 translate-y-full border-l-transparent border-r-transparent border-b-transparent border-t-[#1f2937]"
            break
          case "bottom":
            top = rect.bottom + 8
            left = rect.left + rect.width / 2
            arrowClass = "top-0 left-1/2 -translate-x-1/2 -translate-y-full border-l-transparent border-r-transparent border-t-transparent border-b-[#1f2937]"
            break
          case "left":
            top = rect.top + rect.height / 2
            left = rect.left - 8
            arrowClass = "right-0 top-1/2 translate-x-full -translate-y-1/2 border-t-transparent border-b-transparent border-r-transparent border-l-[#1f2937]"
            break
          case "right":
            top = rect.top + rect.height / 2
            left = rect.right + 8
            arrowClass = "left-0 top-1/2 -translate-x-full -translate-y-1/2 border-t-transparent border-b-transparent border-l-transparent border-r-[#1f2937]"
            break
        }

        return (
          <div
            key={tooltip.id}
            className="absolute -translate-x-1/2 -translate-y-1/2 rounded-lg bg-gray-800 px-3 py-2 text-sm text-white shadow-xl"
            style={{ top, left }}
          >
            {tooltip.text}
            <div className={cn("absolute h-0 w-0 border-[6px]", arrowClass)} />
          </div>
        )
      })}
    </div>
  )
}

// =============================================================================
// CARD OVERLAY
// =============================================================================

interface CardOverlayProps {
  cards: Card[]
  onDismiss: (id: string) => void
}

const cardIcons = {
  info: Info,
  warning: AlertTriangle,
  success: CheckCircle,
  error: XCircle,
}

const cardColors = {
  info: "bg-blue-50 border-blue-200 text-blue-800",
  warning: "bg-yellow-50 border-yellow-200 text-yellow-800",
  success: "bg-green-50 border-green-200 text-green-800",
  error: "bg-red-50 border-red-200 text-red-800",
}

const iconColors = {
  info: "text-blue-500",
  warning: "text-yellow-500",
  success: "text-green-500",
  error: "text-red-500",
}

export function CardOverlay({ cards, onDismiss }: CardOverlayProps) {
  if (cards.length === 0) return null

  const centerCards = cards.filter(c => c.position === "center")
  const topRightCards = cards.filter(c => c.position === "top-right")
  const bottomRightCards = cards.filter(c => c.position === "bottom-right")

  return (
    <>
      {/* Center modal */}
      {centerCards.length > 0 && (
        <div className="fixed inset-0 z-[10001] flex items-center justify-center bg-black/50">
          {centerCards.map(card => {
            const Icon = cardIcons[card.type]
            return (
              <div
                key={card.id}
                className={cn(
                  "relative mx-4 max-w-md rounded-xl border-2 p-6 shadow-2xl",
                  cardColors[card.type]
                )}
              >
                {card.dismissible && (
                  <button
                    onClick={() => onDismiss(card.id)}
                    className="absolute right-3 top-3 rounded-full p-1 hover:bg-black/10"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
                <div className="flex items-start gap-4">
                  <Icon className={cn("h-6 w-6 flex-shrink-0", iconColors[card.type])} />
                  <div>
                    <h3 className="font-semibold">{card.title}</h3>
                    <p className="mt-1 text-sm opacity-90">{card.body}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Top right stack */}
      {topRightCards.length > 0 && (
        <div className="fixed right-4 top-4 z-[10001] flex flex-col gap-3">
          {topRightCards.map(card => {
            const Icon = cardIcons[card.type]
            return (
              <div
                key={card.id}
                className={cn(
                  "relative w-80 rounded-lg border p-4 shadow-lg animate-in slide-in-from-right",
                  cardColors[card.type]
                )}
              >
                {card.dismissible && (
                  <button
                    onClick={() => onDismiss(card.id)}
                    className="absolute right-2 top-2 rounded-full p-1 hover:bg-black/10"
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
                <div className="flex items-start gap-3">
                  <Icon className={cn("h-5 w-5 flex-shrink-0", iconColors[card.type])} />
                  <div className="pr-4">
                    <h3 className="text-sm font-semibold">{card.title}</h3>
                    <p className="mt-0.5 text-xs opacity-90">{card.body}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Bottom right stack */}
      {bottomRightCards.length > 0 && (
        <div className="fixed bottom-4 right-4 z-[10001] flex flex-col gap-3">
          {bottomRightCards.map(card => {
            const Icon = cardIcons[card.type]
            return (
              <div
                key={card.id}
                className={cn(
                  "relative w-80 rounded-lg border p-4 shadow-lg animate-in slide-in-from-right",
                  cardColors[card.type]
                )}
              >
                {card.dismissible && (
                  <button
                    onClick={() => onDismiss(card.id)}
                    className="absolute right-2 top-2 rounded-full p-1 hover:bg-black/10"
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
                <div className="flex items-start gap-3">
                  <Icon className={cn("h-5 w-5 flex-shrink-0", iconColors[card.type])} />
                  <div className="pr-4">
                    <h3 className="text-sm font-semibold">{card.title}</h3>
                    <p className="mt-0.5 text-xs opacity-90">{card.body}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </>
  )
}

// =============================================================================
// COMBINED OVERLAY CONTAINER
// =============================================================================

interface PresentationOverlaysProps {
  highlights: Highlight[]
  tooltips: Tooltip[]
  cards: Card[]
  onDismissCard: (id: string) => void
}

export function PresentationOverlays({
  highlights,
  tooltips,
  cards,
  onDismissCard,
}: PresentationOverlaysProps) {
  return (
    <>
      <HighlightOverlay highlights={highlights} />
      <TooltipOverlay tooltips={tooltips} />
      <CardOverlay cards={cards} onDismiss={onDismissCard} />
    </>
  )
}
