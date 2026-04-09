#!/usr/bin/env bash
# scripts/tunnel.sh — Start a Cloudflare quick tunnel on the agent port.
#
# 1. Launches cloudflared tunnel on localhost:8002
# 2. Waits until the public URL appears in cloudflared's output
# 3. Writes PUBLIC_BASE_URL to .env
# 4. Restarts the agent container so it picks up the new URL
# 5. Prints the curl command to create a Recall.ai bot
#
# Usage:  ./scripts/tunnel.sh [port]
#         make tunnel

set -euo pipefail

PORT="${1:-8002}"
AGENT_CONTAINER="handoff-agent"
ENV_FILE=".env"

# ─── Helpers ──────────────────────────────────────────────────────────────────

log()  { echo "[tunnel] $*"; }
die()  { echo "[tunnel] ERROR: $*" >&2; exit 1; }

# ─── Validate prerequisites ───────────────────────────────────────────────────

command -v cloudflared >/dev/null 2>&1 || die "cloudflared not found. Install with: brew install cloudflare/cloudflare/cloudflared"
command -v docker      >/dev/null 2>&1 || die "docker not found"

# ─── Start cloudflared, capture URL ───────────────────────────────────────────

log "Starting cloudflared quick tunnel → http://localhost:${PORT} ..."
log "(it may take 5-15 seconds to get a URL)"

# Temporary file for cloudflared log
CF_LOG=$(mktemp)
trap 'kill "${CF_PID:-}" 2>/dev/null; rm -f "$CF_LOG"' EXIT INT TERM

# Run cloudflared in background, redirect stderr (where the URL appears) to log
cloudflared tunnel --url "http://localhost:${PORT}" --no-autoupdate 2>"$CF_LOG" &
CF_PID=$!

# Wait for the public URL to appear (up to 60 seconds)
PUBLIC_URL=""
for _ in $(seq 1 60); do
    PUBLIC_URL=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "$CF_LOG" 2>/dev/null | head -1 || true)
    if [ -n "$PUBLIC_URL" ]; then
        break
    fi
    sleep 1
done

[ -n "$PUBLIC_URL" ] || die "Could not detect tunnel URL after 60s. Check cloudflared output:\n$(cat "$CF_LOG")"

log "Tunnel URL: ${PUBLIC_URL}"

# ─── Update .env ──────────────────────────────────────────────────────────────

if [ -f "$ENV_FILE" ]; then
    if grep -q "^PUBLIC_BASE_URL=" "$ENV_FILE"; then
        # Update existing line (macOS-compatible sed)
        sed -i.bak "s|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=${PUBLIC_URL}|" "$ENV_FILE"
        rm -f "${ENV_FILE}.bak"
        log "Updated PUBLIC_BASE_URL in ${ENV_FILE}"
    else
        echo "PUBLIC_BASE_URL=${PUBLIC_URL}" >> "$ENV_FILE"
        log "Added PUBLIC_BASE_URL to ${ENV_FILE}"
    fi
else
    log "No .env file found — skipping env update (set PUBLIC_BASE_URL=${PUBLIC_URL} manually)"
fi

# ─── Restart agent container ──────────────────────────────────────────────────

if docker ps --format '{{.Names}}' | grep -q "^${AGENT_CONTAINER}$"; then
    log "Restarting ${AGENT_CONTAINER} with new PUBLIC_BASE_URL..."
    docker compose up -d --no-deps agent
    log "Agent restarted"
else
    log "Container ${AGENT_CONTAINER} is not running — start with: make up"
fi

# ─── Print usage ──────────────────────────────────────────────────────────────

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  Tunnel active:  ${PUBLIC_URL}"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  Create a Recall.ai bot:                                         ║"
echo "║                                                                  ║"
echo "║  curl -X POST http://localhost:${PORT}/recall/bots \\              ║"
echo "║    -H 'Content-Type: application/json' \\                        ║"
echo "║    -d '{\"meeting_url\": \"MEET_URL\", \"store_id\": \"STR001\"}'         ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Press Ctrl+C to stop the tunnel."
echo ""

# ─── Keep running ─────────────────────────────────────────────────────────────

# Show cloudflared output while tunnel runs
tail -f "$CF_LOG" &
wait "$CF_PID"
