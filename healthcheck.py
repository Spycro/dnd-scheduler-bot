"""Container health check for the scheduler bot."""
import asyncio
import os
import sys
from pathlib import Path


# Ensure the ``src`` directory is importable when the health check runs in
# isolation (e.g. from Docker health checks) where PYTHONPATH is not set.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from scheduler_bot.bot import SchedulerBot


async def main() -> int:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        return 1

    bot = SchedulerBot()
    try:
        await bot.http.static_login(token.strip())
        return 0
    except Exception:
        return 1
    finally:
        try:
            await bot.http.close()
        finally:
            await bot.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
