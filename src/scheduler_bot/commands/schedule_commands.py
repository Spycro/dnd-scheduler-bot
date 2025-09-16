import discord
from discord.ext import commands
from discord import app_commands
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ScheduleCommands(commands.Cog):
    """Commands for managing scheduling polls"""
    
    def __init__(self, bot):
        self.bot = bot
        self.bot.poll_manager.bot = bot  # Set bot reference for poll manager
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is an admin"""
        admin_ids = os.getenv('ADMIN_USER_IDS', '').split(',')
        return str(user_id) in admin_ids
    
    @app_commands.command(name="schedule-init", description="Set up scheduling in the current channel")
    @app_commands.describe(channel="Channel for scheduling polls (defaults to current channel)")
    async def schedule_init(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Initialize scheduling in a channel"""
        if not self.is_admin(interaction.user.id):
            await interaction.response.send_message("❌ Only admins can use this command.", ephemeral=True)
            return
        
        target_channel = channel or interaction.channel
        
        # Set the scheduling channel
        self.bot.config.set('scheduling_channel', str(target_channel.id))
        
        embed = discord.Embed(
            title="✅ Scheduling Initialized",
            description=f"Scheduling polls will be sent to {target_channel.mention}",
            color=0x00ff00
        )
        
        await interaction.response.send_message(embed=embed)
        logger.info(f"Scheduling initialized for channel {target_channel.id} by {interaction.user}")
    
    @app_commands.command(name="schedule-now", description="Create an availability poll immediately")
    async def schedule_now(self, interaction: discord.Interaction):
        """Create an immediate availability poll"""
        if not self.is_admin(interaction.user.id):
            await interaction.response.send_message("❌ Only admins can use this command.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            poll_id = await self.bot.poll_manager.create_weekly_poll(propagate=True)
            await interaction.followup.send("✅ Availability poll created!")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to create poll: {str(e)}")
            logger.error(f"Failed to create immediate poll: {e}")
    
    @app_commands.command(name="schedule-status", description="Show current week's availability responses")
    async def schedule_status(self, interaction: discord.Interaction):
        """Show current poll status"""
        channel_id = self.bot.config.get('scheduling_channel')
        if not channel_id:
            await interaction.response.send_message("❌ Scheduling not set up. Use `/schedule-init` first.", ephemeral=True)
            return
        
        # Get active poll
        active_poll = self.bot.db.get_active_poll(channel_id)
        if not active_poll:
            await interaction.response.send_message("📭 No active poll found.", ephemeral=True)
            return
        
        poll_id, message_id, _, created_at, deadline = active_poll
        responses = self.bot.db.get_poll_responses(poll_id)
        
        embed = discord.Embed(
            title="📊 Current Availability Status",
            color=0x5865F2
        )
        
        if responses:
            saturday_users = []
            sunday_users = []
            
            for user_id, user_name, saturday, sunday, responded_at in responses:
                if saturday:
                    saturday_users.append(user_name)
                if sunday:
                    sunday_users.append(user_name)
            
            embed.add_field(
                name=f"Saturday ({len(saturday_users)} players)",
                value=", ".join(saturday_users) or "None",
                inline=False
            )
            
            embed.add_field(
                name=f"Sunday ({len(sunday_users)} players)",
                value=", ".join(sunday_users) or "None", 
                inline=False
            )
            
            # Recommendation
            min_players = self.bot.config.get_min_players()
            if len(saturday_users) >= min_players and len(sunday_users) >= min_players:
                if len(sunday_users) > len(saturday_users):
                    embed.add_field(name="🎯 Recommendation", value="Sunday has better availability!", inline=False)
                elif len(saturday_users) > len(sunday_users):
                    embed.add_field(name="🎯 Recommendation", value="Saturday has better availability!", inline=False)
                else:
                    embed.add_field(name="🎯 Recommendation", value="Both days have equal availability!", inline=False)
            elif len(saturday_users) >= min_players:
                embed.add_field(name="🎯 Recommendation", value="Saturday meets minimum players!", inline=False)
            elif len(sunday_users) >= min_players:
                embed.add_field(name="🎯 Recommendation", value="Sunday meets minimum players!", inline=False)
            else:
                embed.add_field(name="⚠️ Status", value="Neither day meets minimum player requirement", inline=False)
        
        else:
            embed.description = "No responses yet."
        
        # Add deadline info
        deadline_dt = datetime.fromisoformat(deadline)
        embed.add_field(
            name="Deadline",
            value=f"<t:{int(deadline_dt.timestamp())}:R>",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="schedule-config", description="Configure bot settings")
    @app_commands.describe(
        poll_day="Day to send weekly polls (monday, tuesday, etc.)",
        poll_time="Time to send polls (HH:MM format, 24-hour)",
        deadline_day="Day responses are due",
        deadline_time="Time responses are due (HH:MM format, 24-hour)",
        min_players="Minimum players needed for a session"
    )
    async def schedule_config(self, interaction: discord.Interaction,
                            poll_day: str = None,
                            poll_time: str = None,
                            deadline_day: str = None,
                            deadline_time: str = None,
                            min_players: int = None):
        """Configure bot settings"""
        if not self.is_admin(interaction.user.id):
            await interaction.response.send_message("❌ Only admins can use this command.", ephemeral=True)
            return
        
        changes = []
        
        if poll_day:
            valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            if poll_day.lower() not in valid_days:
                await interaction.response.send_message("❌ Invalid poll day. Use: " + ", ".join(valid_days), ephemeral=True)
                return
            self.bot.config.set('poll_day', poll_day.lower())
            changes.append(f"Poll day: {poll_day.title()}")
        
        if poll_time:
            try:
                # Validate time format
                hour, minute = map(int, poll_time.split(':'))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError()
                self.bot.config.set('poll_time', poll_time)
                changes.append(f"Poll time: {poll_time}")
            except ValueError:
                await interaction.response.send_message("❌ Invalid time format. Use HH:MM (24-hour format)", ephemeral=True)
                return
        
        if deadline_day:
            valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            if deadline_day.lower() not in valid_days:
                await interaction.response.send_message("❌ Invalid deadline day. Use: " + ", ".join(valid_days), ephemeral=True)
                return
            self.bot.config.set('deadline_day', deadline_day.lower())
            changes.append(f"Deadline day: {deadline_day.title()}")
        
        if deadline_time:
            try:
                hour, minute = map(int, deadline_time.split(':'))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError()
                self.bot.config.set('deadline_time', deadline_time)
                changes.append(f"Deadline time: {deadline_time}")
            except ValueError:
                await interaction.response.send_message("❌ Invalid time format. Use HH:MM (24-hour format)", ephemeral=True)
                return
        
        if min_players is not None:
            if min_players < 1:
                await interaction.response.send_message("❌ Minimum players must be at least 1", ephemeral=True)
                return
            self.bot.config.set('min_players', str(min_players))
            changes.append(f"Minimum players: {min_players}")
        
        if not changes:
            # Show current config
            embed = discord.Embed(
                title="⚙️ Current Configuration",
                color=0x5865F2
            )
            
            config_items = [
                ('Poll Day', self.bot.config.get('poll_day').title()),
                ('Poll Time', self.bot.config.get('poll_time')),
                ('Deadline Day', self.bot.config.get('deadline_day').title()),
                ('Deadline Time', self.bot.config.get('deadline_time')),
                ('Minimum Players', self.bot.config.get('min_players')),
                ('Scheduling Channel', f"<#{self.bot.config.get('scheduling_channel')}>" if self.bot.config.get('scheduling_channel') else "Not set")
            ]
            
            for name, value in config_items:
                embed.add_field(name=name, value=value, inline=True)
                
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="✅ Configuration Updated",
                description="\n".join(f"• {change}" for change in changes),
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed)
            
        logger.info(f"Configuration updated by {interaction.user}: {changes}")

    @app_commands.command(name="schedule-players", description="Set the Discord role representing all players")
    @app_commands.describe(role="Role that represents players who must be available")
    async def schedule_players(self, interaction: discord.Interaction, role: discord.Role):
        """Configure the player role used to compute 'all players available' feasibility."""
        if not self.is_admin(interaction.user.id):
            await interaction.response.send_message("❌ Only admins can use this command.", ephemeral=True)
            return
        self.bot.config.set('player_role', str(role.id))
        embed = discord.Embed(
            title="✅ Player Role Set",
            description=f"Using role {role.mention} to determine if all players are available.",
            color=0x00ff00
        )
        embed.add_field(name="Note", value=(
            "Ensure 'Server Members Intent' is enabled in the Developer Portal and in the bot, "
            "so the bot can see members of the role. Otherwise feasibility falls back to min_players."
        ), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="schedule-close", description="Close the active poll and lock responses")
    async def schedule_close(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Close the current active poll in the configured or specified channel"""
        if not self.is_admin(interaction.user.id):
            await interaction.response.send_message("❌ Only admins can use this command.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            channel_id = str(channel.id) if channel else self.bot.config.get('scheduling_channel')
            if not channel_id:
                await interaction.followup.send("❌ Scheduling not set up. Use `/schedule-init` or pass a channel.")
                return
            await self.bot.poll_manager.close_active_poll(channel_id)
            await interaction.followup.send("✅ Closed the active poll and locked responses.")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to close poll: {e}")

    @app_commands.command(name="schedule-purge", description="Close all active polls (optionally in a specific channel)")
    async def schedule_purge(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Purge all active polls in the configured channel or across all channels if none configured and none specified."""
        if not self.is_admin(interaction.user.id):
            await interaction.response.send_message("❌ Only admins can use this command.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            channel_id = str(channel.id) if channel else self.bot.config.get('scheduling_channel')
            count = await self.bot.poll_manager.purge_polls(channel_id)
            scope = f"channel <#{channel_id}>" if channel_id else "all channels"
            await interaction.followup.send(f"✅ Closed {count} active poll(s) in {scope}.")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to purge polls: {e}")
