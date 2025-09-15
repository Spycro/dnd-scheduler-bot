from .schedule_commands import ScheduleCommands

async def setup_commands(bot):
    """Set up all command cogs"""
    await bot.add_cog(ScheduleCommands(bot))

__all__ = ['setup_commands']
