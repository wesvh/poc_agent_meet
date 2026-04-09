#!/bin/sh
# Starts a Cloudflare quick tunnel, captures the public URL,
# writes it to OUTPUT_FILE, then keeps the tunnel alive.
set -e

TARGET_URL="${TARGET_URL:?TARGET_URL env var is required}"
OUTPUT_FILE="${OUTPUT_FILE:?OUTPUT_FILE env var is required}"
LOG_FILE="/tmp/cloudflared.log"

# Clear previous URL so healthcheck doesn't pass stale value on restart
rm -f "$OUTPUT_FILE"

echo "[cloudflared] Starting tunnel → $TARGET_URL"
cloudflared tunnel --url "$TARGET_URL" --no-autoupdate 2>"$LOG_FILE" &
CF_PID=$!

# Wait up to 60 s for the public URL to appear in the log
for i in $(seq 1 60); do
    URL=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "$LOG_FILE" 2>/dev/null | head -1 || true)
    if [ -n "$URL" ]; then
        echo "[cloudflared] Tunnel ready: $URL"
        printf '%s' "$URL" > "$OUTPUT_FILE"
        break
    fi
    sleep 1
done

if [ ! -s "$OUTPUT_FILE" ]; then
    echo "[cloudflared] ERROR: Could not establish tunnel after 60 s"
    cat "$LOG_FILE"
    exit 1
fi

# Keep tunnel running; forward logs to stdout
tail -f "$LOG_FILE" &
wait "$CF_PID"
