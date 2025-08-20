# syntax=docker/dockerfile:1.7

# ---- Base: Python 3.12 slim ----
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/root/.local/bin:${PATH}"

# Install curl (for uv installer) and build essentials only if needed later
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# ---- Install uv (Astral) ----
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /app

# ---- Copy deps first (better layer caching) ----
# We set compose build.context to repo root, so this will succeed.
COPY requirements.txt /app/requirements.txt

# Install project deps into the system site-packages (no virtualenv needed in container)
RUN uv pip install --system -r /app/requirements.txt

# ---- Copy the server code ----
# Your script path: acp2/chatbot-ui/testbackend/test.py
COPY ./chatbot-ui/testbackend/test.py /app/test.py

# (Optional but recommended) add a non-root user
RUN useradd -m appuser
USER appuser

EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import socket,sys; s=socket.socket(); \
try: s.settimeout(2); s.connect(('127.0.0.1',8090)); sys.exit(0) \
except Exception: sys.exit(1) \
finally: s.close()"


# Default command
CMD ["python", "/app/test.py"]
