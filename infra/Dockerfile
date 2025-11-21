# syntax=docker/dockerfile:1
# QuickDCP - Production API image (fixed)
# - Includes OpenSSL, ffmpeg, openjpeg, xmlstarlet for DCP/QC utilities
# - Installs Python deps from infra/requirements.txt
# - Runs FastAPI app as non-root user on port 8080

FROM debian:stable-slim

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    KILL=0

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl jq zip unzip xz-utils locales tzdata \
    python3 python3-pip \
    ffmpeg xmlstarlet genext2fs e2fsprogs openssl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY infra/requirements.txt /app/
RUN PIP_BREAK_SYSTEM_PACKAGES=1 pip3 install --no-cache-dir -r /app/requirements.txt

# App code
COPY api/ /app/api/
COPY public/ /app/public/
COPY worker/ /app/worker/

# Security: run as non-root
RUN useradd -u 10001 qd && chown -R qd:qd /app
USER 10001

EXPOSE 8080

CMD ["python3", "-m", "api.main"]
