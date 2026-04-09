import { NextRequest } from "next/server"
import {
  publishSessionCommand,
  registerSessionClient,
  unregisterSessionClient,
} from "@/lib/ai-socket-server-state"

const VALID_TOKENS = ["rappi_ai_agent_2024", "alia_handoff_token"]

// Server-Sent Events endpoint for real-time commands
export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const sessionId = searchParams.get("session_id")
  const token = searchParams.get("token")

  if (!sessionId || !token || !VALID_TOKENS.includes(token)) {
    return new Response(
      JSON.stringify({ error: "Unauthorized" }),
      { status: 401, headers: { "Content-Type": "application/json" } }
    )
  }

  const encoder = new TextEncoder()
  
  const stream = new ReadableStream({
    start(controller) {
      const clientId = crypto.randomUUID()
      const connectionData = registerSessionClient(sessionId, token, clientId, controller)

      controller.enqueue(
        encoder.encode(`event: connected\ndata: ${JSON.stringify(connectionData)}\n\n`)
      )

      // Keep-alive interval
      const keepAliveInterval = setInterval(() => {
        try {
          controller.enqueue(encoder.encode(`: keepalive ${Date.now()}\n\n`))
        } catch {
          clearInterval(keepAliveInterval)
        }
      }, 15000)

      // Cleanup on close
      request.signal.addEventListener("abort", () => {
        clearInterval(keepAliveInterval)
        unregisterSessionClient(sessionId, clientId)
      })
    },
  })

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
    },
  })
}

// POST - Queue command for SSE delivery
export async function POST(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const sessionId = searchParams.get("session_id")
  const token = searchParams.get("token")

  if (!sessionId || !token || !VALID_TOKENS.includes(token)) {
    return new Response(
      JSON.stringify({ error: "Unauthorized" }),
      { status: 401, headers: { "Content-Type": "application/json" } }
    )
  }

  try {
    const body = await request.json()
    
    if (!body.cmd) {
      return new Response(
        JSON.stringify({ error: "Missing cmd field" }),
        { status: 400, headers: { "Content-Type": "application/json" } }
      )
    }

    const command = {
      cmd: body.cmd,
      payload: body.payload || {},
      request_id: body.request_id || `req_${Date.now()}`,
      timestamp: new Date().toISOString(),
    }

    const delivery = publishSessionCommand(sessionId, command)

    if (delivery.delivered === 0) {
      return new Response(
        JSON.stringify({
          ok: false,
          delivered: false,
          active_clients: delivery.active_clients,
          request_id: command.request_id,
          error: `No active subscribers for session_id '${sessionId}'`,
        }),
        {
          status: 409,
          headers: { "Content-Type": "application/json" },
        }
      )
    }

    return new Response(
      JSON.stringify({
        ok: true,
        delivered: true,
        active_clients: delivery.active_clients,
        request_id: command.request_id,
      }),
      { headers: { "Content-Type": "application/json" } }
    )
  } catch {
    return new Response(
      JSON.stringify({ error: "Invalid JSON" }),
      { status: 400, headers: { "Content-Type": "application/json" } }
    )
  }
}
