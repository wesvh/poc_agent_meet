FROM alpine:3.21

ARG TARGETARCH=amd64

RUN apk add --no-cache curl grep && \
    CF_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "arm64" || echo "amd64") && \
    curl -fsSL \
      "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CF_ARCH}" \
      -o /usr/bin/cloudflared && \
    chmod +x /usr/bin/cloudflared

COPY docker/cloudflared/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
