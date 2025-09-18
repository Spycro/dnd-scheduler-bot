"""Container health check for the scheduler bot."""
import asyncio
import os

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
