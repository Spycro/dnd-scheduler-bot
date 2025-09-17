# D&D Session Scheduler Bot

A Discord bot that automates the weekly availability polling process for D&D groups, tracks responses, and sends reminders to ensure timely feedback from all players.

## Features

- **Weekly Availability Polls**: Automatically posts availability polls on a configurable schedule with APScheduler.
- **Interactive Responses**: Players respond using persistent Discord buttons, and the bot keeps the embed updated with live tallies.
- **Role-Aware Feasibility**: Optionally require every member of a designated player role to respond before a day is marked as viable.
- **Reminder System**: Automatic reminder job plus manual `/schedule-remind` command with Discord channel or DM delivery modes.
- **Poll Administration**: Close or purge active polls, set configuration, and view real-time status via slash commands.
- **Timezone Awareness**: Configure a guild-wide base timezone and let players opt into localized deadlines and DM reminders.

## Quick Start

1. **Clone and install dependencies**:
   ```bash
   git clone <repository-url>
   cd dnd-scheduler-bot
   pip install -r requirements.txt
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your Discord bot token and settings
   ```

3. **Run the bot**:
   ```bash
   python main.py
   ```

## Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application and bot
3. Copy the bot token to your `.env` file
4. Invite the bot to your server with these permissions:
   - Send Messages
   - Use Slash Commands
   - Add Reactions
   - Read Message History
   - Embed Links

## Commands

| Command | Description | Permission |
|---------|-------------|------------|
| `/schedule-init` | Set up scheduling in current channel | Admin |
| `/schedule-now` | Create immediate availability poll | Admin |
| `/schedule-remind` | Send the configured reminder immediately (channel or DM) | Admin |
| `/schedule-status` | Show current week's responses and recommendation | Everyone |
| `/schedule-config` | Configure poll timing, deadlines, reminder mode, and minimum players | Admin |
| `/schedule-players` | Configure the Discord role that represents all players | Admin |
| `/schedule-close` | Close the currently active poll and lock responses | Admin |
| `/schedule-purge` | Close all active polls in the configured (or specified) channel | Admin |
| `/schedule-timezone` | Set or view personal timezone preferences and DM reminder opt-in | Everyone |

## Configuration

Use `/schedule-config` to set:
- **Poll day/time**: When weekly polls are sent
- **Deadline day/time**: When responses are due
- **Minimum players**: Required for session recommendations
- **Reminder delivery**: Send reminders in-channel or via DM
- **Reminder interval**: Control how often automated reminders are sent
- **Default timezone**: Select the base timezone used for poll and deadline calculations

Additional commands:
- `/schedule-players` to choose which Discord role represents the player roster.
- `/schedule-close` to lock the active poll once a decision is made.
- `/schedule-purge` to force-close any lingering polls in one or all channels.
- `/schedule-remind` to trigger a reminder immediately if you need faster follow-up.
- `/schedule-timezone` to see or update your personal timezone and DM reminder preferences.

## Responding to Polls

Players respond to polls by pressing the interactive buttons attached to each poll message:
- 📅 **Both** – Available on Saturday and Sunday
- 🇸 **Saturday** – Only available on Saturday
- ☀️ **Sunday** – Only available on Sunday
- ❌ **Neither** – Unavailable both days

The bot automatically updates the poll embed to show counts, list respondents, and display whether each day is viable based on your configuration or tracked role.

## Environment Variables

Create a `.env` file (see `.env.example`) with:

| Variable | Description |
|----------|-------------|
| `DISCORD_TOKEN` | **Required.** Discord bot token. |
| `ADMIN_USER_IDS` | Comma-separated Discord user IDs permitted to run admin commands. |
| `DEFAULT_CHANNEL_ID` | Optional default scheduling channel (can also be set via `/schedule-init`). |
| `DATABASE_PATH` | Optional path for the SQLite database file (defaults to `scheduler.db`). |
| `GUILD_ID` | Optional guild ID for faster slash command registration on startup. |
| `REMINDER_CHECK_MINUTES` | Override how often the reminder background job runs (defaults to 60). |
## Timezone Preferences

The bot supports localized deadlines so groups that span multiple regions can stay aligned.

- **Guild default timezone**: Admins can run `/schedule-config default_timezone:<IANA name>` to choose the base timezone for calculating poll creation times and deadlines.
- **Player preferences**: Any user may run `/schedule-timezone` to view their current settings, `/schedule-timezone timezone:Europe/Paris` to register their local timezone, or `/schedule-timezone timezone:clear` to remove it.
- **Reminder opt-in**: `/schedule-timezone dm_reminders:true` enables DM reminders even if the user is not part of the tracked player role.
- **Localized embeds**: When at least one timezone preference is registered, the poll embed adds a "Local deadlines" field that translates the deadline for each timezone and lists who uses it. DM reminders also include a personalized "Your local deadline" line.

## Project Structure

```
dnd-scheduler-bot/
├── main.py                 # Entry point
├── src/scheduler_bot/
│   ├── bot.py              # Main bot class
│   ├── database/
│   │   ├── models.py       # Database operations
│   │   └── __init__.py
│   ├── commands/
│   │   ├── schedule_commands.py  # Slash commands
│   │   └── __init__.py
│   ├── utils/
│   │   ├── config.py       # Configuration management
│   │   ├── poll_manager.py # Poll creation and handling
│   │   └── __init__.py
│   └── __init__.py
├── requirements.txt
├── .env.example
└── README.md
```

## Development

This bot is built with:
- **Python 3.10+**
- **discord.py 2.x** for Discord integration
- **SQLite** for data persistence
- **APScheduler** for scheduled tasks

## Potential Features

Future enhancements that would complement the current feature set include:

- **Multi-day Poll Support**: Allow campaigns that meet on other days or need more than two options per week.
- **Timezone Awareness**: Let each user opt into reminders and embed timestamps localized to their preferred timezone.
- **Calendar Sync**: Export confirmed sessions to Google Calendar, Outlook, or iCal feeds for easy scheduling.
- **Player Availability History**: Track historical responses to highlight chronic conflicts or calculate attendance streaks.
- **Web Dashboard**: Provide a lightweight web UI for reviewing polls, editing configuration, and tracking reminders outside Discord.

## License

MIT License
