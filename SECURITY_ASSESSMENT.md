# Security Hardening Checklist

This document captures the current production-readiness review for deploying the scheduler bot with Docker on a VPS. Use it as a reference when hardening the environment.

## Container & Runtime

- **Use a dedicated runtime user.**
  - Update the Dockerfile to create a `bot` user and set `USER bot` for the runtime layer so the Discord token is never handled as root.
  - During deployment (Compose, Swarm, or Kubernetes), pre-create `/data` on the host and `chown -R bot:bot /data` so the SQLite database is writable without escalated privileges.
  - Add an init container or entrypoint step that ensures `/app` and `/data` directories remain owned by `bot` on every launch.

- **Harden filesystem permissions.**
  - Mount the SQLite volume as read/write for the bot and read-only for everything else (`:rw` for the service, `:ro` elsewhere).
  - Restrict directory permissions to `0750` for `/app` and `0700` for `/data` so only the container user can read bot code or database contents.
  - Avoid bind-mounting the entire project directory in production. Prefer copying only the required artefacts into the image and mounting a dedicated `/data` volume.

- **Constrain compute resources.**
  - Add CPU and memory reservations/limits to the `docker-compose.yml` service definition, for example:

    ```yaml
    deploy:
      resources:
        limits:
          cpus: "0.50"
          memory: 512M
        reservations:
          cpus: "0.25"
          memory: 256M
    ```

  - Mirror these limits in production orchestrators so a runaway job or Discord event flood cannot starve neighbouring workloads.

- **Implement health and startup checks.**
  - Replace simple TCP/DNS health checks with a script that imports `main` and executes a quick `asyncio.run(bot.http.static_login())` or another lightweight Discord API check.
  - Wire the script into `HEALTHCHECK` in the Dockerfile or via Compose `healthcheck` stanza with conservative timeouts/backoff.
  - Alert on repeated failures so operators can intervene before the bot is evicted or rate-limited by Discord.

## Dependencies & Image Maintenance
- Replace the loose `>=` version specifiers with pinned versions (and optional hashes) in `requirements.txt` for reproducible builds.
- Regularly rebuild the image to pick up security updates for the base image (`python:3.13-slim`) and Debian packages installed via `apt`.
- Confirm discord.py, APScheduler, and other libraries fully support the selected Python runtime. Consider downgrading to a stable LTS Python release (3.11/3.12) if compatibility issues arise.

## Secrets & Configuration
- Do not mount `.env` files that contain secrets on production hosts. Inject the Discord token and other sensitive values via orchestrator-managed environment variables or Docker secrets.
- Restrict access to configuration files and ensure only the bot user can read them.

## Data Protection & Observability
- Snapshot or back up the `/data` volume regularly to avoid losing the SQLite database.
- Route application logs to centralized storage or monitoring to simplify incident response.
- Add alerting around container health checks and key bot failures.

## Host Hardening
- Harden the VPS with a firewall, automatic OS security updates, and least-privilege SSH access.
- Monitor the host for intrusion attempts and keep Docker engine patches current.

Review this checklist periodically and update it as the bot evolves or new infrastructure options are introduced.
