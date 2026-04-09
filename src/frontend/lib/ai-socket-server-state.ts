type SessionCommand = {
  cmd: string
  payload: Record<string, unknown>
  request_id: string
  timestamp: string
}

type SessionClient = {
  id: string
  controller: ReadableStreamDefaultController<Uint8Array>
  connected_at: string
  last_activity: string
}

type SessionState = {
  token: string
  connected_at: string
  last_activity: string
  clients: Map<string, SessionClient>
  queue: SessionCommand[]
}

type ServerState = {
  sessions: Map<string, SessionState>
}

const globalState = globalThis as typeof globalThis & {
  __aiSocketServerState?: ServerState
}

const state =
  globalState.__aiSocketServerState ??
  (globalState.__aiSocketServerState = {
    sessions: new Map<string, SessionState>(),
  })

function encodeSseEvent(event: string, data: unknown) {
  return new TextEncoder().encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`)
}

function getOrCreateSession(sessionId: string, token: string) {
  const now = new Date().toISOString()
  const existing = state.sessions.get(sessionId)

  if (existing) {
    existing.token = token
    existing.last_activity = now
    return existing
  }

  const session: SessionState = {
    token,
    connected_at: now,
    last_activity: now,
    clients: new Map(),
    queue: [],
  }

  state.sessions.set(sessionId, session)
  return session
}

export function registerSessionClient(
  sessionId: string,
  token: string,
  clientId: string,
  controller: ReadableStreamDefaultController<Uint8Array>
) {
  const session = getOrCreateSession(sessionId, token)
  const now = new Date().toISOString()

  session.clients.set(clientId, {
    id: clientId,
    controller,
    connected_at: now,
    last_activity: now,
  })
  session.last_activity = now

  return {
    session_id: sessionId,
    client_id: clientId,
    timestamp: now,
    active_clients: session.clients.size,
  }
}

export function unregisterSessionClient(sessionId: string, clientId: string) {
  const session = state.sessions.get(sessionId)
  if (!session) return

  session.clients.delete(clientId)
  session.last_activity = new Date().toISOString()

  if (session.clients.size === 0) {
    state.sessions.delete(sessionId)
  }
}

export function publishSessionCommand(sessionId: string, command: SessionCommand) {
  const session = state.sessions.get(sessionId)
  if (!session) {
    return {
      delivered: 0,
      active_clients: 0,
    }
  }

  // Always enqueue for polling clients
  session.queue.push(command)
  session.last_activity = new Date().toISOString()

  // Also push via SSE for direct connections
  let delivered = session.queue.length > 0 ? 1 : 0
  for (const [clientId, client] of session.clients.entries()) {
    try {
      client.controller.enqueue(encodeSseEvent("command", command))
      client.last_activity = new Date().toISOString()
    } catch {
      session.clients.delete(clientId)
    }
  }

  return {
    delivered,
    active_clients: session.clients.size,
  }
}

export function drainSessionCommands(sessionId: string): SessionCommand[] {
  const session = state.sessions.get(sessionId)
  if (!session) return []
  const commands = session.queue.splice(0)
  session.last_activity = new Date().toISOString()
  return commands
}

export function touchSession(sessionId: string, token: string) {
  getOrCreateSession(sessionId, token)
}

export function getSessionSnapshot(sessionId: string) {
  const session = state.sessions.get(sessionId)
  if (!session) {
    return null
  }

  return {
    session_id: sessionId,
    token: session.token,
    connected_at: session.connected_at,
    last_activity: session.last_activity,
    active_clients: session.clients.size,
  }
}

