"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { type AICommand, demoSequences, protocolExamples } from "@/lib/ai-socket-protocol"
import { type Section } from "./sidebar"
import { 
  Terminal, 
  Copy, 
  Check, 
  X, 
  Minimize2, 
  Maximize2,
  Wifi,
  WifiOff,
  Send,
  Play,
  Trash2
} from "lucide-react"

interface AIDebugPanelProps {
  currentSection: Section
  activeTool: string | null
  lastAction: string | null
  sessionId?: string
  onSessionChange?: (sessionId: string | null) => void
  isConnected?: boolean
  commandHistory?: AICommand[]
  onNavigate?: (section: string) => boolean
  onExecuteCommand?: (cmd: AICommand) => Promise<unknown>
}

export function AIDebugPanel({ 
  currentSection, 
  activeTool, 
  lastAction,
  sessionId = "demo_session",
  onSessionChange,
  isConnected = false,
  commandHistory = [],
  onNavigate,
  onExecuteCommand
}: AIDebugPanelProps) {
  const [copied, setCopied] = useState(false)
  const [isMinimized, setIsMinimized] = useState(false)
  const [isVisible, setIsVisible] = useState(false)
  const [customCommand, setCustomCommand] = useState("")
  const [sessionInput, setSessionInput] = useState(sessionId)
  const [activeTab, setActiveTab] = useState<"state" | "history" | "test">("state")
  const [isRunningDemo, setIsRunningDemo] = useState(false)

  // Check URL for ai_debug query param
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    setIsVisible(params.get("ai_debug") === "true")
  }, [])

  useEffect(() => {
    setSessionInput(sessionId)
  }, [sessionId])

  const copyEndpoint = () => {
    const endpoint = `${window.location.origin}/api/ai-socket/sse?session_id=${sessionId}&token=rappi_ai_agent_2024`
    navigator.clipboard.writeText(endpoint)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const runDemoSequence = async (sequenceName: keyof typeof demoSequences) => {
    if (!onExecuteCommand || isRunningDemo) return
    
    setIsRunningDemo(true)
    const sequence = demoSequences[sequenceName]
    
    for (const cmd of sequence) {
      await onExecuteCommand(cmd as AICommand)
      await new Promise(r => setTimeout(r, 100))
    }
    
    setIsRunningDemo(false)
  }

  const executeCustomCommand = async () => {
    if (!onExecuteCommand || !customCommand.trim()) return
    
    try {
      const cmd = JSON.parse(customCommand)
      await onExecuteCommand(cmd)
      setCustomCommand("")
    } catch {
      alert("JSON invalido")
    }
  }

  if (!isVisible) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 w-[380px]">
      <Card className="border-[#FF4940]/30 bg-background/95 shadow-xl backdrop-blur">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <Terminal className="h-4 w-4 text-[#FF4940]" />
            Presentation Control
            {isConnected ? (
              <Badge variant="outline" className="ml-1 gap-1 border-green-500 text-green-600 text-[10px]">
                <Wifi className="h-3 w-3" />
              </Badge>
            ) : (
              <Badge variant="outline" className="ml-1 gap-1 border-red-500 text-red-600 text-[10px]">
                <WifiOff className="h-3 w-3" />
              </Badge>
            )}
          </CardTitle>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={copyEndpoint}
              title="Copy endpoint"
            >
              {copied ? (
                <Check className="h-3 w-3 text-green-500" />
              ) : (
                <Copy className="h-3 w-3" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => setIsMinimized(!isMinimized)}
            >
              {isMinimized ? (
                <Maximize2 className="h-3 w-3" />
              ) : (
                <Minimize2 className="h-3 w-3" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={() => {
                const url = new URL(window.location.href)
                url.searchParams.delete("ai_debug")
                window.history.replaceState({}, "", url)
                setIsVisible(false)
              }}
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        </CardHeader>

        {!isMinimized && (
          <CardContent className="space-y-3 pt-0">
            {/* Tabs */}
            <div className="flex gap-1 border-b pb-1">
              {(["state", "history", "test"] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex-1 rounded-t px-2 py-1 text-xs font-medium transition-colors ${
                    activeTab === tab
                      ? "bg-[#FF4940] text-white"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {tab === "state" && "Estado"}
                  {tab === "history" && "Historial"}
                  {tab === "test" && "Test"}
                </button>
              ))}
            </div>

            {/* State Tab */}
            {activeTab === "state" && (
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded bg-muted p-2">
                    <div className="text-muted-foreground">Seccion</div>
                    <div className="font-medium">{currentSection}</div>
                  </div>
                  <div className="rounded bg-muted p-2">
                    <div className="text-muted-foreground">Session</div>
                    <div className="font-mono text-[10px]">{sessionId.slice(0, 12)}...</div>
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Front objetivo (`session_id`)</div>
                  <div className="flex gap-1">
                    <Input
                      value={sessionInput}
                      onChange={(e) => setSessionInput(e.target.value)}
                      placeholder="demo1"
                      className="h-7 font-mono text-[10px]"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          onSessionChange?.(sessionInput)
                        }
                      }}
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 px-2 text-[10px]"
                      onClick={() => onSessionChange?.(sessionInput)}
                    >
                      Aplicar
                    </Button>
                  </div>
                </div>
                {activeTool && (
                  <Badge className="bg-[#FF4940] text-white">Tool: {activeTool}</Badge>
                )}
                {lastAction && (
                  <div className="rounded bg-muted p-2 text-xs">
                    <div className="text-muted-foreground">Ultima accion</div>
                    <code className="text-[10px]">{lastAction}</code>
                  </div>
                )}
                
                {/* Quick Navigation */}
                <div>
                  <div className="mb-1 text-xs text-muted-foreground">Navegacion rapida</div>
                  <div className="flex flex-wrap gap-1">
                    {["dashboard", "catalog", "finances", "disputes", "schedule", "support"].map(section => (
                      <Button
                        key={section}
                        size="sm"
                        variant={currentSection === section ? "default" : "outline"}
                        className="h-6 px-2 text-[10px]"
                        onClick={() => onNavigate?.(section)}
                      >
                        {section}
                      </Button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* History Tab */}
            {activeTab === "history" && (
              <ScrollArea className="h-48">
                {commandHistory.length === 0 ? (
                  <div className="py-8 text-center text-xs text-muted-foreground">
                    Sin comandos recibidos
                  </div>
                ) : (
                  <div className="space-y-1">
                    {[...commandHistory].reverse().map((cmd, i) => (
                      <div
                        key={i}
                        className="rounded bg-muted p-1.5 text-xs"
                      >
                        <span className="font-medium text-[#FF4940]">{cmd.cmd}</span>
                        {cmd.payload && (
                          <code className="ml-1 text-[10px] text-muted-foreground">
                            {JSON.stringify(cmd.payload).slice(0, 50)}
                          </code>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </ScrollArea>
            )}

            {/* Test Tab */}
            {activeTab === "test" && (
              <div className="space-y-3">
                {/* Demo Sequences */}
                <div>
                  <div className="mb-1 text-xs font-medium text-muted-foreground">Secuencias Demo</div>
                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 flex-1 text-xs"
                      disabled={isRunningDemo}
                      onClick={() => runDemoSequence("login_demo")}
                    >
                      <Play className="mr-1 h-3 w-3" />
                      Login
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 flex-1 text-xs"
                      disabled={isRunningDemo}
                      onClick={() => runDemoSequence("tour_dashboard")}
                    >
                      <Play className="mr-1 h-3 w-3" />
                      Tour
                    </Button>
                  </div>
                </div>

                {/* Quick Commands */}
                <div>
                  <div className="mb-1 text-xs font-medium text-muted-foreground">Comandos rapidos</div>
                  <div className="grid grid-cols-2 gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 justify-start text-[10px]"
                      onClick={() => onExecuteCommand?.(protocolExamples.highlight_field as AICommand)}
                    >
                      Highlight email
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 justify-start text-[10px]"
                      onClick={() => onExecuteCommand?.(protocolExamples.show_success_card as AICommand)}
                    >
                      Show card
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 justify-start text-[10px]"
                      onClick={() => onExecuteCommand?.(protocolExamples.type_email as AICommand)}
                    >
                      Type email
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 justify-start text-[10px]"
                      onClick={() => onExecuteCommand?.(protocolExamples.show_tooltip as AICommand)}
                    >
                      Show tooltip
                    </Button>
                  </div>
                </div>

                {/* Custom Command */}
                <div>
                  <div className="mb-1 text-xs font-medium text-muted-foreground">Comando JSON</div>
                  <div className="flex gap-1">
                    <Input
                      value={customCommand}
                      onChange={(e) => setCustomCommand(e.target.value)}
                      placeholder='{"cmd":"navigate","payload":{"section":"catalog"}}'
                      className="h-7 font-mono text-[10px]"
                      onKeyDown={(e) => e.key === "Enter" && executeCustomCommand()}
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-7 px-2"
                      onClick={executeCustomCommand}
                    >
                      <Send className="h-3 w-3" />
                    </Button>
                  </div>
                </div>

                {/* Clear Overlays */}
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-6 w-full text-xs text-muted-foreground"
                  onClick={() => onExecuteCommand?.({ cmd: "clear_overlays", payload: { scope: "all" } })}
                >
                  <Trash2 className="mr-1 h-3 w-3" />
                  Limpiar overlays
                </Button>
              </div>
            )}
          </CardContent>
        )}
      </Card>
    </div>
  )
}
