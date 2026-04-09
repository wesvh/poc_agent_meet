#!/usr/bin/env bash
# scripts/tunnel-frontend.sh — Start a Cloudflare quick tunnel on the frontend port.
#
# 1. Launches cloudflared tunnel on localhost:3000
# 2. Waits until the public URL appears in cloudflared's output
# 3. Writes SCREENSHARE_DEFAULT_URL to .env
# 4. Restarts the agent container so it picks up the new screenshare URL
# 5. Prints the public URL
#
# Usage:  ./scripts/tunnel-frontend.sh [port]
#         make tunnel-frontend

set -euo pipefail

PORT="${1:-3000}"
AGENT_CONTAINER="handoff-agent"
ENV_FILE=".env"

# ─── Helpers ──────────────────────────────────────────────────────────────────

log()  { echo "[tunnel-frontend] $*"; }
die()  { echo "[tunnel-frontend] ERROR: $*" >&2; exit 1; }

# ─── Validate prerequisites ───────────────────────────────────────────────────

command -v cloudflared >/dev/null 2>&1 || die "cloudflared not found. Install with: brew install cloudflare/cloudflare/cloudflared"
command -v docker      >/dev/null 2>&1 || die "docker not found"

# ─── Start cloudflared, capture URL ───────────────────────────────────────────

log "Starting cloudflared quick tunnel → http://localhost:${PORT} ..."
log "(it may take 5-15 seconds to get a URL)"

CF_LOG=$(mktemp)
trap 'kill "${CF_PID:-}" 2>/dev/null; rm -f "$CF_LOG"' EXIT INT TERM

cloudflared tunnel --url "http://localhost:${PORT}" --no-autoupdate 2>"$CF_LOG" &
CF_PID=$!

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
    if grep -q "^SCREENSHARE_DEFAULT_URL=" "$ENV_FILE"; then
        sed -i.bak "s|^SCREENSHARE_DEFAULT_URL=.*|SCREENSHARE_DEFAULT_URL=${PUBLIC_URL}|" "$ENV_FILE"
        rm -f "${ENV_FILE}.bak"
        log "Updated SCREENSHARE_DEFAULT_URL in ${ENV_FILE}"
    else
        echo "SCREENSHARE_DEFAULT_URL=${PUBLIC_URL}" >> "$ENV_FILE"
        log "Added SCREENSHARE_DEFAULT_URL to ${ENV_FILE}"
    fi
else
    log "No .env file found — set SCREENSHARE_DEFAULT_URL=${PUBLIC_URL} manually"
fi

# ─── Restart agent so it picks up the new SCREENSHARE_DEFAULT_URL ─────────────

if docker ps --format '{{.Names}}' | grep -q "^${AGENT_CONTAINER}$"; then
    log "Restarting ${AGENT_CONTAINER} with new SCREENSHARE_DEFAULT_URL..."
    docker compose up -d --no-deps agent
    log "Agent restarted"
else
    log "Container ${AGENT_CONTAINER} is not running — start with: make up"
fi

# ─── Print summary ─────────────────────────────────────────────────────────────

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  Frontend tunnel active: ${PUBLIC_URL}"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  SCREENSHARE_DEFAULT_URL updated — agent restarted.              ║"
echo "║  Recall.ai bots will now screenshare this URL.                   ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Press Ctrl+C to stop the tunnel."
echo ""

tail -f "$CF_LOG" &
wait "$CF_PID"
