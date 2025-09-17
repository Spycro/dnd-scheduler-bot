try:
    # Prefer the standard library module if available
    import sqlite3
except ModuleNotFoundError:
    # Fallback to pysqlite3 if Python was built without _sqlite3
    try:
        import pysqlite3 as sqlite3  # type: ignore
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            "SQLite support is not available in this Python build. "
            "Install system SQLite dev libraries and reinstall Python, "
            "or 'pip install pysqlite3-binary' to supply the module."
        ) from e
import os
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any

class Database:
    def __init__(self, db_path: str = "scheduler.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Active polls table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS polls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT UNIQUE,
                    channel_id TEXT,
                    created_at TIMESTAMP,
                    deadline TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # User responses table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    poll_id INTEGER,
                    user_id TEXT,
                    user_name TEXT,
                    saturday BOOLEAN DEFAULT 0,
                    sunday BOOLEAN DEFAULT 0,
                    responded_at TIMESTAMP,
                    FOREIGN KEY (poll_id) REFERENCES polls(id),
                    UNIQUE(poll_id, user_id)
                )
            ''')
            
            # Configuration table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')

            # Reminder tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS poll_reminders (
                    poll_id INTEGER PRIMARY KEY,
                    last_sent_at TIMESTAMP,
                    interval_hours INTEGER NOT NULL DEFAULT 24,
                    delivery_mode TEXT NOT NULL DEFAULT 'channel',
                    FOREIGN KEY (poll_id) REFERENCES polls(id)
                )
            ''')

            # User-specific settings (timezone preferences, reminder opt-in, etc.)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id TEXT PRIMARY KEY,
                    timezone TEXT,
                    dm_opt_in BOOLEAN NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP
                )
            ''')

            conn.commit()

    def create_poll(self, message_id: str, channel_id: str, deadline: datetime) -> int:
        """Create a new poll and return its ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO polls (message_id, channel_id, created_at, deadline)
                VALUES (?, ?, ?, ?)
            ''', (message_id, channel_id, datetime.now(timezone.utc), deadline))
            conn.commit()
            return cursor.lastrowid
    
    def get_active_poll(self, channel_id: str) -> Optional[Tuple]:
        """Get the active poll for a channel"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, message_id, channel_id, created_at, deadline
                FROM polls 
                WHERE channel_id = ? AND is_active = 1
                ORDER BY created_at DESC
                LIMIT 1
            ''', (channel_id,))
            return cursor.fetchone()

    def list_active_polls(self, channel_id: Optional[str] = None) -> List[Tuple]:
        """List all active polls, optionally filtered by channel_id"""
        query = (
            "SELECT id, message_id, channel_id, created_at, deadline FROM polls "
            "WHERE is_active = 1"
        )
        params: Tuple = tuple()
        if channel_id is not None:
            query += " AND channel_id = ?"
            params = (channel_id,)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()

    def get_poll_by_message(self, message_id: str) -> Optional[Tuple]:
        """Get the active poll by its Discord message ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, message_id, channel_id, created_at, deadline
                FROM polls
                WHERE message_id = ? AND is_active = 1
                ORDER BY created_at DESC
                LIMIT 1
            ''', (message_id,))
            return cursor.fetchone()
    
    def add_response(self, poll_id: int, user_id: str, user_name: str, 
                    saturday: bool, sunday: bool):
        """Add or update a user's response to a poll"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO responses
                (poll_id, user_id, user_name, saturday, sunday, responded_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (poll_id, user_id, user_name, saturday, sunday, datetime.now(timezone.utc)))
            conn.commit()
    
    def get_poll_responses(self, poll_id: int) -> List[Tuple]:
        """Get all responses for a poll"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, user_name, saturday, sunday, responded_at
                FROM responses 
                WHERE poll_id = ?
                ORDER BY responded_at
            ''', (poll_id,))
            return cursor.fetchall()
    
    def close_poll(self, poll_id: int):
        """Mark a poll as inactive"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE polls SET is_active = 0 WHERE id = ?
            ''', (poll_id,))
            conn.commit()
    
    def set_config(self, key: str, value: str):
        """Set a configuration value"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)
            ''', (key, value))
            conn.commit()
    
    def get_config(self, key: str, default: str = None) -> Optional[str]:
        """Get a configuration value"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
            result = cursor.fetchone()
            return result[0] if result else default

    def init_poll_reminder(self, poll_id: int, interval_hours: int, delivery_mode: str, *, last_sent_at: Optional[datetime] = None):
        """Ensure a reminder row exists for a poll and initialize its tracking data."""
        if last_sent_at is None:
            last_sent_at = datetime.now(timezone.utc)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO poll_reminders (poll_id, last_sent_at, interval_hours, delivery_mode)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(poll_id) DO UPDATE SET
                    interval_hours = excluded.interval_hours,
                    delivery_mode = excluded.delivery_mode,
                    last_sent_at = COALESCE(poll_reminders.last_sent_at, excluded.last_sent_at)
            ''', (poll_id, last_sent_at, interval_hours, delivery_mode))
            conn.commit()

    def update_poll_reminder_sent(self, poll_id: int, sent_at: datetime):
        """Update the last time a reminder was sent for a poll."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE poll_reminders
                SET last_sent_at = ?
                WHERE poll_id = ?
            ''', (sent_at, poll_id))
            conn.commit()

    def get_user_settings(self, user_id: str) -> Optional[Tuple[str, Optional[str], int, Optional[str]]]:
        """Return the stored settings for a user, if any."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, timezone, dm_opt_in, updated_at
                FROM user_settings
                WHERE user_id = ?
            ''', (user_id,))
            row = cursor.fetchone()
            return row if row else None

    def upsert_user_settings(self, user_id: str, *, timezone_name: Optional[str] = None,
                              dm_opt_in: Optional[bool] = None) -> Dict[str, Any]:
        """Create or update user settings and return the resulting row."""
        current = self.get_user_settings(user_id)
        existing_timezone = current[1] if current else None
        existing_opt_in = bool(current[2]) if current else False

        tz_value = timezone_name if timezone_name is not None else existing_timezone
        opt_in_value = dm_opt_in if dm_opt_in is not None else existing_opt_in

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_settings (user_id, timezone, dm_opt_in, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    timezone = excluded.timezone,
                    dm_opt_in = excluded.dm_opt_in,
                    updated_at = excluded.updated_at
            ''', (user_id, tz_value, int(opt_in_value), datetime.now(timezone.utc)))
            conn.commit()

        # Fetch the updated row to return a consistent view
        updated = self.get_user_settings(user_id)
        if updated is None:
            raise RuntimeError("Failed to persist user settings")
        return {
            'user_id': updated[0],
            'timezone': updated[1],
            'dm_opt_in': bool(updated[2]),
            'updated_at': updated[3],
        }

    def list_user_settings(self) -> List[Tuple[str, Optional[str], int]]:
        """Return all stored user settings."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, timezone, dm_opt_in
                FROM user_settings
            ''')
            return cursor.fetchall()

    def list_user_timezones(self) -> List[Tuple[str, str]]:
        """Return user IDs and timezone names for users that have a timezone configured."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, timezone
                FROM user_settings
                WHERE timezone IS NOT NULL AND timezone != ''
            ''')
            return cursor.fetchall()

    def list_dm_opt_in_users(self) -> List[Tuple[str, Optional[str]]]:
        """Return user IDs (and optional timezone) for users that opted into DM reminders."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, timezone
                FROM user_settings
                WHERE dm_opt_in = 1
            ''')
            return cursor.fetchall()

    def list_active_reminders(self) -> List[Tuple]:
        """Return reminder metadata for all active polls."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.id, p.channel_id, p.message_id, p.created_at, p.deadline,
                       r.last_sent_at, r.interval_hours, r.delivery_mode
                FROM polls p
                JOIN poll_reminders r ON p.id = r.poll_id
                WHERE p.is_active = 1
            ''')
            return cursor.fetchall()

    def delete_poll_reminder(self, poll_id: int):
        """Remove reminder tracking for a poll."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM poll_reminders WHERE poll_id = ?', (poll_id,))
            conn.commit()
