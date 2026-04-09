import { NextRequest, NextResponse } from "next/server"
import { getSessionSnapshot } from "@/lib/ai-socket-server-state"

// Validate session token
const VALID_TOKENS = ["rappi_ai_agent_2024", "alia_handoff_token"]

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const sessionId = searchParams.get("session_id")
  const token = searchParams.get("token")

  // Validate params
  if (!sessionId) {
    return NextResponse.json(
      { error: "session_id is required" },
      { status: 400 }
    )
  }

  if (!token || !VALID_TOKENS.includes(token)) {
    return NextResponse.json(
      { error: "Invalid or missing token" },
      { status: 401 }
    )
  }

  // Check if upgrade header is present (WebSocket request)
  const upgradeHeader = request.headers.get("upgrade")
  
  if (upgradeHeader !== "websocket") {
    // Regular HTTP request - return session info
    const session = getSessionSnapshot(sessionId)
    
    return NextResponse.json({
      session_id: sessionId,
      status: session ? "active" : "not_found",
      connected_at: session?.connected_at,
      last_activity: session?.last_activity,
      active_clients: session?.active_clients ?? 0,
      protocol_version: "1.0",
      supported_commands: [
        "navigate",
        "show_card",
        "highlight",
        "update_field",
        "show_checklist",
        "show_timer",
        "clear",
        "agent_speaking",
        "execute_tool",
        "request_context",
      ],
      documentation: "/api/ai-socket/docs",
    })
  }

  // For WebSocket upgrade - return 426 since Next.js doesn't support native WS
  // The client should use a fallback mechanism or connect to a dedicated WS server
  return NextResponse.json(
    {
      error: "WebSocket upgrade not supported in this endpoint",
      suggestion: "Use Server-Sent Events or polling as fallback",
      fallback_endpoint: "/api/ai-socket/sse",
    },
    { status: 426 }
  )
}

// POST - Send command to session (for server-to-client push simulation)
export async function POST(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const sessionId = searchParams.get("session_id")
  const token = searchParams.get("token")

  // Validate
  if (!sessionId) {
    return NextResponse.json(
      { error: "session_id is required" },
      { status: 400 }
    )
  }

  if (!token || !VALID_TOKENS.includes(token)) {
    return NextResponse.json(
      { error: "Invalid or missing token" },
      { status: 401 }
    )
  }

  try {
    const body = await request.json()
    
    // Validate command structure
    if (!body.cmd || typeof body.cmd !== "string") {
      return NextResponse.json(
        { error: "Invalid command structure. Expected { cmd: string, payload?: object }" },
        { status: 400 }
      )
    }

    const command = {
      cmd: body.cmd,
      payload: body.payload || {},
      request_id: body.request_id || `req_${Date.now()}`,
      timestamp: new Date().toISOString(),
    }
    const session = getSessionSnapshot(sessionId)

    return NextResponse.json({
      ok: !!session,
      active_clients: session?.active_clients ?? 0,
      command_id: command.request_id,
      timestamp: command.timestamp,
      message: session
        ? "Session is active. Send commands to /api/ai-socket/sse for live delivery."
        : "No active subscribers for this session_id.",
    })
  } catch {
    return NextResponse.json(
      { error: "Invalid JSON body" },
      { status: 400 }
    )
  }
}
