import { NextRequest, NextResponse } from "next/server"
import { screenContexts, aiTools, type AIContextPayload, type ScreenContext } from "@/lib/ai-context"

// Security token for AI agent access (in production, use proper auth)
const AI_ACCESS_TOKEN = "rappi_ai_agent_2024"

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  
  // Check for authorization
  const authToken = searchParams.get("token") || request.headers.get("x-ai-token")
  
  if (authToken !== AI_ACCESS_TOKEN) {
    return NextResponse.json(
      { error: "Unauthorized. Provide valid token via ?token= or x-ai-token header" },
      { status: 401 }
    )
  }

  // Get current section from query param
  const section = searchParams.get("section") || "dashboard"
  const storeId = searchParams.get("store_id") || null
  const storeName = searchParams.get("store_name") || null
  const isAuthenticated = searchParams.get("authenticated") === "true"

  // Get base context for the section
  const baseContext = screenContexts[section] || screenContexts.dashboard

  // Build user context
  const userContext: ScreenContext["user_context"] = {
    store_id: storeId,
    store_name: storeName,
    is_authenticated: isAuthenticated,
  }

  // Build full payload
  const payload: AIContextPayload = {
    screen: {
      ...baseContext,
      current_path: `/${section === "dashboard" ? "" : section}`,
      user_context: userContext,
      timestamp: new Date().toISOString(),
    },
    available_tools: aiTools,
    active_tool: searchParams.get("active_tool") || null,
    last_action: searchParams.get("last_action") || null,
    navigation_function: "window.navigateToSection(sectionId)",
  }

  return NextResponse.json(payload, {
    headers: {
      "Content-Type": "application/json",
      "X-AI-Context-Version": "1.0",
      "Access-Control-Allow-Origin": "*",
    },
  })
}

// Handle POST for tool execution simulation
export async function POST(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const authToken = searchParams.get("token") || request.headers.get("x-ai-token")
  
  if (authToken !== AI_ACCESS_TOKEN) {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401 }
    )
  }

  try {
    const body = await request.json()
    const { tool, parameters } = body

    // Validate tool exists
    const toolDef = aiTools.find((t) => t.name === tool)
    if (!toolDef) {
      return NextResponse.json(
        { error: `Unknown tool: ${tool}`, available_tools: aiTools.map((t) => t.name) },
        { status: 400 }
      )
    }

    // Validate required parameters
    const missingParams = Object.entries(toolDef.parameters)
      .filter(([_, config]) => config.required && !parameters[_])
      .map(([key]) => key)

    if (missingParams.length > 0) {
      return NextResponse.json(
        { error: `Missing required parameters: ${missingParams.join(", ")}` },
        { status: 400 }
      )
    }

    // Simulate tool execution (in a real app, this would execute the action)
    return NextResponse.json({
      success: true,
      tool_executed: tool,
      parameters_received: parameters,
      result: {
        status: "simulated",
        message: `Tool '${tool}' would be executed with provided parameters`,
        timestamp: new Date().toISOString(),
      },
    })
  } catch {
    return NextResponse.json(
      { error: "Invalid JSON body" },
      { status: 400 }
    )
  }
}
