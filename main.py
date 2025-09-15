#!/usr/bin/env python3
"""
D&D Session Scheduler Bot
Main entry point for the Discord bot
"""

import sys
import os
import asyncio

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scheduler_bot.bot import main

if __name__ == "__main__":
    asyncio.run(main())