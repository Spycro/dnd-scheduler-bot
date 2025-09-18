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

# Create dedicated runtime user and data directories with strict permissions
RUN addgroup --system bot \
    && adduser --system --ingroup bot --home /app --shell /usr/sbin/nologin bot \
    && mkdir -p /app /data \
    && chown bot:bot /app /data \
    && chmod 0750 /app \
    && chmod 0700 /data

WORKDIR /app

# Install Python dependencies first for better layer caching
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

# Copy application code and helper scripts with restricted ownership
COPY --chown=bot:bot src ./src
COPY --chown=bot:bot main.py ./main.py
COPY --chown=bot:bot healthcheck.py ./healthcheck.py
COPY --chown=bot:bot docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# Ensure a persistent location for the SQLite database and link default path
RUN ln -s /data/scheduler.db /app/scheduler.db \
    && chmod 0755 /usr/local/bin/docker-entrypoint.sh

# Set an explicit healthcheck that performs a lightweight Discord auth probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD python /app/healthcheck.py

USER bot

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "main.py"]
