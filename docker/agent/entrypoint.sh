#!/bin/bash
# Reads tunnel URLs from the shared /tunnels volume and exports them as env vars
# before starting the agent. Called automatically by docker-compose depends_on,
# but also waits locally in case of minor timing gaps.
set -e

TUNNELS=/tunnels
MAX_WAIT=30

wait_for_url() {
    local file="$1" label="$2"
    for i in $(seq 1 $MAX_WAIT); do
        if [ -s "$file" ]; then
            echo "[agent-init] $label = $(cat "$file")"
            return 0
        fi
        sleep 1
    done
    echo "[agent-init] ERROR: Timed out waiting for $label"
    exit 1
}

wait_for_url "$TUNNELS/agent_url"    "PUBLIC_BASE_URL"
wait_for_url "$TUNNELS/frontend_url" "SCREENSHARE_DEFAULT_URL"

export PUBLIC_BASE_URL="$(cat "$TUNNELS/agent_url")"
export SCREENSHARE_DEFAULT_URL="$(cat "$TUNNELS/frontend_url")"

echo "[agent-init] Tunnels ready — starting agent"

exec uvicorn src.agent.server:app --host 0.0.0.0 --port 8002 --reload
