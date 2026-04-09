import { NextRequest, NextResponse } from "next/server"
import { drainSessionCommands, touchSession } from "@/lib/ai-socket-server-state"

export const dynamic = "force-dynamic"
export const runtime = "nodejs"

const VALID_TOKENS = ["rappi_ai_agent_2024", "alia_handoff_token"]

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl
  const sessionId = searchParams.get("session_id")
  const token = searchParams.get("token")

  if (!sessionId || !token || !VALID_TOKENS.includes(token)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  touchSession(sessionId, token)
  const commands = drainSessionCommands(sessionId)

  return NextResponse.json(
    { commands, session_id: sessionId, ts: Date.now() },
    {
      headers: {
        "Cache-Control": "no-store",
      },
    }
  )
}
