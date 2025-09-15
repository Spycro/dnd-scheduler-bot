import discord
from datetime import datetime, timedelta
from typing import Optional, Dict, Set
import logging

from ..database import Database

logger = logging.getLogger(__name__)

class PollManager:
    """Manages availability polls and responses"""
    
    REACTION_MAP = {
        '📅': ('both', True, True),     # Both days
        '🇸': ('saturday', True, False),  # Saturday only  
        '☀️': ('sunday', False, True),   # Sunday only
        '❌': ('neither', False, False)   # Neither day
    }
    
    def __init__(self, database: Database):
        self.db = database
        self.bot = None  # Will be set by commands setup
    
    async def create_weekly_poll(self):
        """Create the weekly availability poll"""
        try:
            channel_id = self.db.get_config('scheduling_channel')
            if not channel_id:
                logger.warning("No scheduling channel configured")
                return
            
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                logger.error(f"Could not find channel {channel_id}")
                return
            
            # Check if there's already an active poll
            active_poll = self.db.get_active_poll(channel_id)
            if active_poll:
                logger.info("Active poll already exists, skipping creation")
                return
            
            # Calculate deadline
            deadline = self._calculate_deadline()
            
            # Create poll message
            embed = self._create_poll_embed(deadline)
            message = await channel.send(embed=embed)
            
            # Add reactions
            for emoji in self.REACTION_MAP.keys():
                await message.add_reaction(emoji)
            
            # Save to database
            poll_id = self.db.create_poll(str(message.id), channel_id, deadline)
            
            # Schedule reminders
            await self._schedule_reminders(poll_id, channel_id, deadline)
            
            logger.info(f"Created weekly poll {poll_id} in channel {channel_id}")
            
        except Exception as e:
            logger.error(f"Failed to create weekly poll: {e}")
    
    async def handle_reaction(self, payload: discord.RawReactionActionEvent, added: bool):
        """Handle reaction add/remove events"""
        try:
            # Check if this is a poll message
            poll = self.db.get_active_poll(str(payload.channel_id))
            if not poll or poll[1] != str(payload.message_id):
                return
            
            poll_id = poll[0]
            emoji = str(payload.emoji)
            
            if emoji not in self.REACTION_MAP:
                return
            
            # Get user info
            user = self.bot.get_user(payload.user_id)
            if not user:
                return
            
            if added:
                # Remove other reactions from this user
                await self._remove_other_reactions(payload, emoji)
                
                # Add response to database
                response_type, saturday, sunday = self.REACTION_MAP[emoji]
                self.db.add_response(poll_id, str(user.id), user.display_name, saturday, sunday)
                
                logger.info(f"User {user.display_name} selected {response_type}")
            
            # Update the poll message
            await self._update_poll_message(poll_id, payload.channel_id, payload.message_id)
            
        except Exception as e:
            logger.error(f"Error handling reaction: {e}")
    
    async def _remove_other_reactions(self, payload: discord.RawReactionActionEvent, keep_emoji: str):
        """Remove user's other reactions from the poll"""
        try:
            channel = self.bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            
            for reaction in message.reactions:
                if str(reaction.emoji) != keep_emoji and str(reaction.emoji) in self.REACTION_MAP:
                    await reaction.remove(self.bot.get_user(payload.user_id))
                    
        except Exception as e:
            logger.error(f"Error removing other reactions: {e}")
    
    async def _update_poll_message(self, poll_id: int, channel_id: int, message_id: int):
        """Update the poll message with current responses"""
        try:
            channel = self.bot.get_channel(channel_id)
            message = await channel.fetch_message(message_id)
            
            # Get poll info
            poll_data = self.db.get_active_poll(str(channel_id))
            if not poll_data:
                return
            
            deadline = datetime.fromisoformat(poll_data[4])
            responses = self.db.get_poll_responses(poll_id)
            
            # Create updated embed
            embed = self._create_poll_embed(deadline, responses)
            await message.edit(embed=embed)
            
        except Exception as e:
            logger.error(f"Error updating poll message: {e}")
    
    def _create_poll_embed(self, deadline: datetime, responses: list = None) -> discord.Embed:
        """Create the poll embed message"""
        # Calculate the week date range
        now = datetime.now()
        days_until_saturday = (5 - now.weekday()) % 7
        if days_until_saturday == 0 and now.weekday() == 5:  # If today is Saturday
            days_until_saturday = 0
        saturday = now + timedelta(days=days_until_saturday)
        sunday = saturday + timedelta(days=1)
        
        week_str = f"{saturday.strftime('%b %d')} - {sunday.strftime('%b %d, %Y')}"
        
        embed = discord.Embed(
            title="📊 D&D Session Availability",
            description=f"**Week of {week_str}**\n\nPlease react with your availability for this weekend:",
            color=0x5865F2
        )
        
        embed.add_field(
            name="Options",
            value="📅 Both days\n🇸 Saturday only\n☀️ Sunday only\n❌ Neither day",
            inline=False
        )
        
        embed.add_field(
            name="Deadline",
            value=f"<t:{int(deadline.timestamp())}:F>",
            inline=False
        )
        
        # Add responses if provided
        if responses:
            responded_users = []
            pending_users = []
            
            # Get configured player role or fallback
            player_role_id = self.db.get_config('player_role')
            expected_players = self._get_expected_players(player_role_id)
            
            response_dict = {r[1]: r for r in responses}  # user_name -> response
            
            for player in expected_players:
                if player in response_dict:
                    responded_users.append(f"✅ {player}")
                else:
                    pending_users.append(f"⏳ {player}")
            
            all_status = responded_users + pending_users
            embed.add_field(
                name="Responses",
                value="\n".join(all_status) if all_status else "No responses yet",
                inline=False
            )
        
        embed.set_footer(text="Reminders will be sent to pending players")
        return embed
    
    def _get_expected_players(self, player_role_id: Optional[str]) -> Set[str]:
        """Get list of expected players (placeholder for now)"""
        # TODO: Implement proper player tracking
        return {"Player1", "Player2", "Player3", "Player4", "DM"}
    
    def _calculate_deadline(self) -> datetime:
        """Calculate the deadline for the current poll"""
        deadline_day = self.db.get_config('deadline_day', 'wednesday').lower()
        deadline_time = self.db.get_config('deadline_time', '18:00')
        
        # Parse time
        hour, minute = map(int, deadline_time.split(':'))
        
        # Map day names to weekday numbers
        day_map = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        target_weekday = day_map.get(deadline_day, 2)  # Default to Wednesday
        
        # Calculate days until target weekday
        now = datetime.now()
        days_ahead = target_weekday - now.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        deadline = now + timedelta(days=days_ahead)
        deadline = deadline.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        return deadline
    
    async def _schedule_reminders(self, poll_id: int, channel_id: str, deadline: datetime):
        """Schedule reminders for the poll"""
        # TODO: Implement reminder scheduling
        pass