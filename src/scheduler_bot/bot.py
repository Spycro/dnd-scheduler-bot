import discord
from discord.ext import commands, tasks
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

from .database import Database
from .utils.poll_manager import PollManager, PollResponseView
from .utils.config import Config

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchedulerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        # Prefix commands are not used; disable message content
        intents.message_content = False
        intents.reactions = True
        # Enable members intent so role membership can be checked for feasibility
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.db = Database()
        self.config = Config(self.db)
        self.poll_manager = PollManager(self.db)
        self.scheduler = AsyncIOScheduler()
        
    async def setup_hook(self):
        """Called when the bot is starting up"""
        from .commands import setup_commands
        await setup_commands(self)
        # Register persistent view for poll response buttons
        try:
            self.add_view(PollResponseView(self.poll_manager))
        except Exception as e:
            logger.error(f"Failed to register persistent view: {e}")
        # Sync slash commands. If GUILD_ID is set, sync to that guild for instant availability.
        try:
            guild_id = os.getenv('GUILD_ID')
            if guild_id:
                guild = discord.Object(id=int(guild_id))
                # Copy global commands to the target guild for instant availability
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                logger.info(f"Synced {len(synced)} guild application command(s) to guild {guild_id}")
            else:
                synced = await self.tree.sync()
                logger.info(f"Synced {len(synced)} global application command(s)")
        except Exception as e:
            logger.error(f"Failed to sync application commands: {e}")
        
        # Start the scheduler
        self.scheduler.start()
        logger.info("Bot setup completed")
        
    async def on_ready(self):
        """Called when bot connects to Discord"""
        logger.info(f'{self.user} has connected to Discord!')
        
        # Schedule the weekly poll if configured
        await self._schedule_weekly_poll()
        
    async def on_raw_reaction_add(self, payload):
        """Handle reaction additions"""
        if payload.user_id == self.user.id:
            return
            
        await self.poll_manager.handle_reaction(payload, True)
        
    async def on_raw_reaction_remove(self, payload):
        """Handle reaction removals"""
        if payload.user_id == self.user.id:
            return
            
        await self.poll_manager.handle_reaction(payload, False)
        
    async def _schedule_weekly_poll(self):
        """Schedule the weekly availability poll"""
        poll_day = self.config.get('poll_day', 'monday').lower()
        poll_time = self.config.get('poll_time', '10:00')
        
        try:
            hour, minute = map(int, poll_time.split(':'))
            
            # Map day names to weekday numbers (0=Monday)
            day_map = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            
            weekday = day_map.get(poll_day, 0)
            
            self.scheduler.add_job(
                self.poll_manager.create_weekly_poll,
                'cron',
                day_of_week=weekday,
                hour=hour,
                minute=minute,
                id='weekly_poll'
            )
            
            logger.info(f"Scheduled weekly poll for {poll_day}s at {poll_time}")
            
        except Exception as e:
            logger.error(f"Failed to schedule weekly poll: {e}")

async def main():
    """Main function to run the bot"""
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKEN not found in environment variables")
        return
    
    bot = SchedulerBot()
    
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        await bot.close()
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        await bot.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
