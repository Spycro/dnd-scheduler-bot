# D&D Session Scheduler Bot

A Discord bot that automates the weekly availability polling process for D&D groups, tracks responses, and sends reminders to ensure timely feedback from all players.

## Features

- **Weekly Availability Polls**: Automatically posts availability polls on a configurable schedule
- **Response Tracking**: Tracks which players have responded with emoji reactions
- **Reminder System**: Sends reminders to players who haven't responded
- **Summary Reports**: Generates availability summaries with recommendations
- **Slash Commands**: Modern Discord slash command interface

## Quick Start

1. **Clone and install dependencies**:
   ```bash
   git clone <repository-url>
   cd scheduler-bot
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
| `/schedule-status` | Show current week's responses | Everyone |
| `/schedule-config` | Configure poll timing and settings | Admin |

## Configuration

Use `/schedule-config` to set:
- **Poll day/time**: When weekly polls are sent
- **Deadline day/time**: When responses are due
- **Minimum players**: Required for session recommendations

## Reactions

Players respond to polls using these emoji reactions:
- 📅 Both Saturday and Sunday
- 🇸 Saturday only
- ☀️ Sunday only
- ❌ Neither day

## Project Structure

```
scheduler-bot/
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

## License

MIT License