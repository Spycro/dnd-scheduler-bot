# Security Hardening Checklist

This document captures the current production-readiness review for deploying the scheduler bot with Docker on a VPS. Use it as a reference when hardening the environment.

## Container & Runtime
- Run the container as a dedicated non-root user and ensure `/app` and `/data` are owned by that user before launch.
- Enforce minimum required filesystem permissions on the SQLite volume and mount it read/write only for the bot process.
- Apply CPU and memory limits through your orchestrator (Docker Compose/Swarm/Kubernetes) to prevent resource exhaustion.
- Add a startup/liveness probe that verifies the bot process is responsive (import the bot module or perform a lightweight Discord API check) instead of relying solely on DNS resolution.

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
