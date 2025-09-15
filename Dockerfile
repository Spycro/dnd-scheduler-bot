# syntax=docker/dockerfile:1

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install runtime dependencies (certs, sqlite client for debugging)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for better layer caching
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy application code
COPY src ./src
COPY main.py ./main.py

# Ensure a persistent location for the SQLite database and link default path
RUN mkdir -p /data \
    && ln -s /data/scheduler.db /app/scheduler.db

# Set an explicit healthcheck to ensure the container has network reachability
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import socket,sys;\n\ntry: socket.gethostbyname('discord.com'); sys.exit(0)\nexcept Exception: sys.exit(1)"

# The app reads configuration from environment variables and .env.
# Provide a helpful default command.
CMD ["python", "main.py"]
