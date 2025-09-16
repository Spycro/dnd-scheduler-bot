import discord
from datetime import datetime, timedelta
from typing import Optional, Dict, Set, Tuple
import logging

from ..database import Database

logger = logging.getLogger(__name__)

class PollResponseView(discord.ui.View):
    """Persistent view with buttons to record availability responses."""

    def __init__(self, poll_manager: 'PollManager'):
        # timeout=None makes the view persistent across restarts when added via bot.add_view
        super().__init__(timeout=None)
        self.poll_manager = poll_manager

    async def _handle_vote(self, interaction: discord.Interaction, saturday: bool, sunday: bool, label: str):
        try:
            poll = self.poll_manager.db.get_poll_by_message(str(interaction.message.id))
            if not poll:
                await interaction.response.send_message("❌ This poll is not active anymore.", ephemeral=True)
                return

            poll_id = poll[0]
            user = interaction.user
            self.poll_manager.db.add_response(poll_id, str(user.id), user.display_name, saturday, sunday)

            # Update the poll message embed
            await self.poll_manager._update_poll_message(poll_id, interaction.channel_id, interaction.message.id)

            await interaction.response.send_message(f"✅ Recorded your response: {label}", ephemeral=True)
        except Exception as e:
            logger.error(f"Error handling vote: {e}")
            if interaction.response.is_done():
                await interaction.followup.send("❌ Failed to record your response.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Failed to record your response.", ephemeral=True)

    @discord.ui.button(label="Both", style=discord.ButtonStyle.primary, emoji='📅', custom_id='poll_both')
    async def vote_both(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_vote(interaction, saturday=True, sunday=True, label='Both days')

    @discord.ui.button(label="Saturday", style=discord.ButtonStyle.secondary, emoji='🇸', custom_id='poll_sat')
    async def vote_sat(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_vote(interaction, saturday=True, sunday=False, label='Saturday only')

    @discord.ui.button(label="Sunday", style=discord.ButtonStyle.secondary, emoji='☀️', custom_id='poll_sun')
    async def vote_sun(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_vote(interaction, saturday=False, sunday=True, label='Sunday only')

    @discord.ui.button(label="Neither", style=discord.ButtonStyle.danger, emoji='❌', custom_id='poll_none')
    async def vote_none(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_vote(interaction, saturday=False, sunday=False, label='Neither')


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
    
    async def _resolve_channel(self, channel_id: int):
        """Get a channel by ID, fetching from API if not cached."""
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except Exception as e:
                logger.error(f"Failed to fetch channel {channel_id}: {e}")
                return None
        return channel

    def _missing_creation_permissions(self, channel) -> list:
        """Return a list of human-readable permission names missing for poll creation."""
        # Permissions needed to create the embed and add reactions
        required = {
            'view_channel': 'View Channel',
            'send_messages': 'Send Messages',
            'embed_links': 'Embed Links',
            'read_message_history': 'Read Message History',
        }
        try:
            perms = channel.permissions_for(channel.guild.me)
        except Exception:
            # Fallback: if we cannot determine perms, assume missing
            return list(required.values())

        missing = [name for attr, name in required.items() if not getattr(perms, attr, False)]
        return missing

    async def create_weekly_poll(self, propagate: bool = False):
        """Create the weekly availability poll.

        Returns poll_id on success. If propagate is True, raises on failure; otherwise logs and returns None.
        """
        try:
            channel_id = self.db.get_config('scheduling_channel')
            if not channel_id:
                msg = "No scheduling channel configured"
                if propagate:
                    raise RuntimeError(msg)
                logger.warning(msg)
                return None

            channel = await self._resolve_channel(int(channel_id))
            if not channel:
                msg = f"Could not find or access channel {channel_id}"
                if propagate:
                    raise RuntimeError(msg)
                logger.error(msg)
                return None

            # Check permissions before attempting to send
            missing = self._missing_creation_permissions(channel)
            if missing:
                msg = "Missing permissions in channel: " + ", ".join(missing)
                if propagate:
                    raise RuntimeError(msg)
                logger.error(msg)
                return None

            # Check if there's already an active poll
            active_poll = self.db.get_active_poll(channel_id)
            if active_poll:
                msg = "Active poll already exists, skipping creation"
                if propagate:
                    raise RuntimeError(msg)
                logger.info(msg)
                return None

            # Calculate deadline
            deadline = self._calculate_deadline()

            # Create poll message with buttons
            sat_ok, sun_ok = self._compute_day_feasibility(channel, [])
            embed = self._create_poll_embed(deadline, responses=[], feasibility=(sat_ok, sun_ok))
            view = PollResponseView(self)
            message = await channel.send(embed=embed, view=view)

            # Save to database
            poll_id = self.db.create_poll(str(message.id), channel_id, deadline)

            # Schedule reminders
            await self._schedule_reminders(poll_id, channel_id, deadline)

            logger.info(f"Created weekly poll {poll_id} in channel {channel_id}")
            return poll_id

        except Exception as e:
            if propagate:
                raise
            logger.error(f"Failed to create weekly poll: {e}")
            return None
    
    async def handle_reaction(self, payload: discord.RawReactionActionEvent, added: bool):
        """Deprecated: Reaction handling replaced by buttons."""
        return
    
    async def _remove_other_reactions(self, payload: discord.RawReactionActionEvent, keep_emoji: str):
        """Deprecated: No longer needed when using buttons."""
        return
    
    async def _update_poll_message(self, poll_id: int, channel_id: int, message_id: int):
        """Update the poll message with current responses"""
        try:
            channel = await self._resolve_channel(int(channel_id))
            if channel is None:
                return
            message = await channel.fetch_message(message_id)
            
            # Get poll info
            poll_data = self.db.get_active_poll(str(channel_id))
            if not poll_data:
                return
            
            deadline = datetime.fromisoformat(poll_data[4])
            responses = self.db.get_poll_responses(poll_id)

            # Create updated embed
            sat_ok, sun_ok = self._compute_day_feasibility(channel, responses)
            embed = self._create_poll_embed(deadline, responses, feasibility=(sat_ok, sun_ok))
            await message.edit(embed=embed)
            
        except Exception as e:
            logger.error(f"Error updating poll message: {e}")
    
    def _create_poll_embed(self, deadline: datetime, responses: list = None, closed: bool = False, feasibility: Optional[Tuple[bool, bool]] = None) -> discord.Embed:
        """Create the poll embed message"""
        # Calculate the week date range
        now = datetime.now()
        days_until_saturday = (5 - now.weekday()) % 7
        if days_until_saturday == 0 and now.weekday() == 5:  # If today is Saturday
            days_until_saturday = 0
        saturday = now + timedelta(days=days_until_saturday)
        sunday = saturday + timedelta(days=1)
        
        week_str = f"{saturday.strftime('%b %d')} - {sunday.strftime('%b %d, %Y')}"
        
        title = "📊 D&D Session Availability"
        if closed:
            title += " — CLOSED"
        embed = discord.Embed(
            title=title,
            description=f"**Week of {week_str}**\n\nUse the buttons below to record your availability:",
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
        
        # Day feasibility status (based on role or min_players)
        if feasibility is not None:
            sat_ok, sun_ok = feasibility
            def label(ok: bool) -> str:
                return "✅ Possible" if ok else "❌ Not possible"
            embed.add_field(
                name="Feasibility",
                value=f"Saturday: {label(sat_ok)}\nSunday: {label(sun_ok)}",
                inline=False
            )
        
        # Add responses if provided
        if responses:
            both = []
            sat_only = []
            sun_only = []
            neither = []

            for user_id, user_name, saturday, sunday, responded_at in responses:
                if saturday and sunday:
                    both.append(user_name)
                elif saturday and not sunday:
                    sat_only.append(user_name)
                elif sunday and not saturday:
                    sun_only.append(user_name)
                else:
                    neither.append(user_name)

            def list_or_none(names):
                return ", ".join(names) if names else "None"

            embed.add_field(name=f"Both ({len(both)})", value=list_or_none(both), inline=False)
            embed.add_field(name=f"Saturday ({len(sat_only)})", value=list_or_none(sat_only), inline=False)
            embed.add_field(name=f"Sunday ({len(sun_only)})", value=list_or_none(sun_only), inline=False)
            embed.add_field(name=f"Neither ({len(neither)})", value=list_or_none(neither), inline=False)
        
        if closed:
            embed.set_footer(text="Poll closed — no further responses accepted")
        else:
            embed.set_footer(text="Tap a button below to set your availability")
        return embed

    def _compute_day_feasibility(self, channel, responses: list) -> Tuple[bool, bool]:
        """Compute if a session is possible on Saturday and Sunday.

        If a player_role is set and found in the guild, requires all members with that role to be available.
        Otherwise falls back to meeting min_players.
        """
        # Sets of user IDs available for each day
        available_sat = {r[0] for r in responses if r[2]}
        available_sun = {r[0] for r in responses if r[3]}

        role_id_str = self.db.get_config('player_role')
        try:
            min_players = int(self.db.get_config('min_players', '3'))
        except Exception:
            min_players = 3

        # Prefer strict role-based check when role is configured
        role = None
        if getattr(channel, 'guild', None) and role_id_str:
            try:
                role = channel.guild.get_role(int(role_id_str))
            except Exception:
                role = None
        if role is not None:
            expected_ids = {str(m.id) for m in role.members}
            if expected_ids:
                sat_ok = expected_ids.issubset(available_sat)
                sun_ok = expected_ids.issubset(available_sun)
                return sat_ok, sun_ok
            # If role has no cached members, fall back to threshold to avoid false positives

        # Fallback: threshold by min_players
        sat_ok = len(available_sat) >= min_players
        sun_ok = len(available_sun) >= min_players
        return sat_ok, sun_ok
    
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
        # TODO: Implement reminder scheduling (e.g., APScheduler jobs)
        pass

    async def close_active_poll(self, channel_id: Optional[str] = None) -> bool:
        """Close the active poll in the given or configured channel and update the message UI."""
        if channel_id is None:
            channel_id = self.db.get_config('scheduling_channel')
        if not channel_id:
            raise RuntimeError("No scheduling channel configured")

        poll = self.db.get_active_poll(channel_id)
        if not poll:
            raise RuntimeError("No active poll to close")

        poll_id, message_id, ch_id, created_at, deadline = poll
        # Mark as inactive in DB
        self.db.close_poll(poll_id)

        # Update the message to reflect closure and remove buttons
        channel = await self._resolve_channel(int(ch_id))
        if channel is None:
            raise RuntimeError(f"Could not access channel {ch_id} to update message")
        try:
            message = await channel.fetch_message(int(message_id))
        except Exception as e:
            raise RuntimeError(f"Failed to fetch poll message: {e}")

        responses = self.db.get_poll_responses(poll_id)
        sat_ok, sun_ok = self._compute_day_feasibility(channel, responses)
        embed = self._create_poll_embed(datetime.fromisoformat(deadline), responses, closed=True, feasibility=(sat_ok, sun_ok))
        await message.edit(embed=embed, view=None)
        return True

    async def purge_polls(self, channel_id: Optional[str] = None) -> int:
        """Close all active polls in the given channel or all channels if None.

        Returns the number of polls closed.
        """
        active = self.db.list_active_polls(channel_id)
        count = 0
        for poll_id, message_id, ch_id, created_at, deadline in active:
            try:
                self.db.close_poll(poll_id)
                channel = await self._resolve_channel(int(ch_id))
                if channel:
                    try:
                        message = await channel.fetch_message(int(message_id))
                        responses = self.db.get_poll_responses(poll_id)
                        sat_ok, sun_ok = self._compute_day_feasibility(channel, responses)
                        embed = self._create_poll_embed(datetime.fromisoformat(deadline), responses, closed=True, feasibility=(sat_ok, sun_ok))
                        await message.edit(embed=embed, view=None)
                    except Exception as e:
                        logger.warning(f"Could not edit poll message {message_id} in channel {ch_id}: {e}")
                count += 1
            except Exception as e:
                logger.error(f"Failed to close poll {poll_id}: {e}")
        return count
