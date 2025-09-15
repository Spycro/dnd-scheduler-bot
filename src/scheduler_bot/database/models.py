import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Tuple

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
            
            conn.commit()
    
    def create_poll(self, message_id: str, channel_id: str, deadline: datetime) -> int:
        """Create a new poll and return its ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO polls (message_id, channel_id, created_at, deadline)
                VALUES (?, ?, ?, ?)
            ''', (message_id, channel_id, datetime.now(), deadline))
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
    
    def add_response(self, poll_id: int, user_id: str, user_name: str, 
                    saturday: bool, sunday: bool):
        """Add or update a user's response to a poll"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO responses 
                (poll_id, user_id, user_name, saturday, sunday, responded_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (poll_id, user_id, user_name, saturday, sunday, datetime.now()))
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