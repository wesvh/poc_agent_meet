FROM python:3.11-slim

WORKDIR /app

# System deps: gcc/libpq for SQLAlchemy + espeak-ng for Piper phonemization
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libc6-dev libpq-dev \
    espeak-ng \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt requirements-agent.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-agent.txt

# ── Kokoro-82M ONNX (ef_dora, Spanish female, ~310 MB onnx + ~26 MB voices) ─
ARG KOKORO_RELEASE=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0

RUN mkdir -p /models && \
    curl -fsSL "${KOKORO_RELEASE}/kokoro-v1.0.onnx"  -o /models/kokoro-v1.0.onnx && \
    curl -fsSL "${KOKORO_RELEASE}/voices-v1.0.bin"    -o /models/voices-v1.0.bin

COPY src/ src/
COPY docker/agent/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
