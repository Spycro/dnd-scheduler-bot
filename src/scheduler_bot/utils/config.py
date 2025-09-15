from typing import Optional
from ..database import Database

class Config:
    """Configuration management for the bot"""
    
    DEFAULT_CONFIG = {
        'poll_day': 'monday',
        'poll_time': '10:00',
        'deadline_day': 'wednesday', 
        'deadline_time': '18:00',
        'reminder_intervals': '24,48',
        'min_players': '3',
        'scheduling_channel': None,
        'player_role': None
    }
    
    def __init__(self, database: Database):
        self.db = database
        self._initialize_defaults()
    
    def _initialize_defaults(self):
        """Set default configuration values if not present"""
        for key, value in self.DEFAULT_CONFIG.items():
            if value is not None and self.db.get_config(key) is None:
                self.db.set_config(key, value)
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a configuration value"""
        return self.db.get_config(key, default or self.DEFAULT_CONFIG.get(key))
    
    def set(self, key: str, value: str):
        """Set a configuration value"""
        self.db.set_config(key, value)
    
    def get_reminder_intervals(self) -> list[int]:
        """Get reminder intervals as a list of integers (hours)"""
        intervals_str = self.get('reminder_intervals', '24,48')
        return [int(x.strip()) for x in intervals_str.split(',')]
    
    def get_min_players(self) -> int:
        """Get minimum players as integer"""
        return int(self.get('min_players', '3'))