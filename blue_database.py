"""
Blue Database Module
Handles all persistent storage for memories, preferences, conversations, and more
Uses SQLite for simplicity and portability
"""

import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager
import logging

logger = logging.getLogger("blue.database")


class BlueDatabase:
    """Main database class for Blue's persistent storage"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Conversations table - stores all conversations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT,
                    context_used TEXT,
                    tool_used TEXT,
                    sentiment TEXT,
                    importance INTEGER DEFAULT 5
                )
            """)
            
            # Long-term memories - important facts to remember
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT,
                    memory_type TEXT,
                    content TEXT,
                    context TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    importance INTEGER DEFAULT 5,
                    tags TEXT,
                    UNIQUE(user_name, memory_type, content)
                )
            """)
            
            # User preferences
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT,
                    preference_key TEXT,
                    preference_value TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_name, preference_key)
                )
            """)
            
            # Schedules and reminders
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT,
                    title TEXT,
                    description TEXT,
                    due_datetime DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed BOOLEAN DEFAULT FALSE,
                    recurring TEXT,
                    priority INTEGER DEFAULT 3,
                    category TEXT
                )
            """)
            
            # Tasks and to-do items
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT,
                    title TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    priority INTEGER DEFAULT 3,
                    due_date DATE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME,
                    category TEXT,
                    tags TEXT
                )
            """)
            
            # Notes and memos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT,
                    title TEXT,
                    content TEXT,
                    category TEXT,
                    tags TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Family events (birthdays, anniversaries, etc.)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS family_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_name TEXT,
                    event_type TEXT,
                    event_date DATE,
                    recurring BOOLEAN DEFAULT TRUE,
                    description TEXT,
                    reminder_days_before INTEGER DEFAULT 7
                )
            """)
            
            # Routines and patterns learned
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS routines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT,
                    routine_name TEXT,
                    time_of_day TEXT,
                    day_of_week TEXT,
                    actions TEXT,
                    confidence REAL DEFAULT 0.5,
                    last_occurred DATETIME,
                    occurrence_count INTEGER DEFAULT 1
                )
            """)
            
            # Documents metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE,
                    filepath TEXT,
                    file_hash TEXT,
                    file_size INTEGER,
                    file_type TEXT,
                    uploaded_by TEXT,
                    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_accessed DATETIME,
                    access_count INTEGER DEFAULT 0,
                    indexed_in_rag BOOLEAN DEFAULT FALSE,
                    summary TEXT,
                    tags TEXT
                )
            """)
            
            # Activity log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT,
                    activity_type TEXT,
                    description TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            # System settings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_user 
                ON conversations(user_name, timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_user 
                ON memories(user_name, importance DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminders_due 
                ON reminders(due_datetime, completed)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status 
                ON tasks(user_name, status, due_date)
            """)
            
            logger.info("Database initialized successfully")
    
    # ===== Conversation Management =====
    
    def save_conversation(self, user_name: str, role: str, content: str, 
                         session_id: str = None, tool_used: str = None,
                         context_used: str = None, importance: int = 5) -> int:
        """Save a conversation message"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversations 
                (user_name, role, content, session_id, tool_used, context_used, importance)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_name, role, content, session_id, tool_used, context_used, importance))
            return cursor.lastrowid
    
    def get_recent_conversations(self, user_name: str = None, limit: int = 50) -> List[Dict]:
        """Get recent conversations"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if user_name:
                cursor.execute("""
                    SELECT * FROM conversations 
                    WHERE user_name = ?
                    ORDER BY timestamp DESC LIMIT ?
                """, (user_name, limit))
            else:
                cursor.execute("""
                    SELECT * FROM conversations 
                    ORDER BY timestamp DESC LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_conversation_summary(self, user_name: str, days: int = 7) -> str:
        """Get a summary of recent conversations"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            since = datetime.now() - timedelta(days=days)
            cursor.execute("""
                SELECT content, role FROM conversations
                WHERE user_name = ? AND timestamp > ?
                ORDER BY timestamp ASC
            """, (user_name, since))
            
            conversations = cursor.fetchall()
            if not conversations:
                return "No recent conversations"
            
            # Build summary (this could be enhanced with LLM summarization)
            summary_parts = []
            for conv in conversations[:20]:  # Last 20 exchanges
                role = conv['role']
                content = conv['content'][:100]  # Truncate
                summary_parts.append(f"{role}: {content}")
            
            return "\n".join(summary_parts)
    
    # ===== Memory Management =====
    
    def save_memory(self, user_name: str, memory_type: str, content: str,
                   context: str = None, importance: int = 5, tags: List[str] = None) -> bool:
        """Save a long-term memory"""
        tags_str = json.dumps(tags) if tags else None
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO memories 
                    (user_name, memory_type, content, context, importance, tags)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_name, memory_type, content, context, importance, tags_str))
                return True
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
            return False
    
    def get_memories(self, user_name: str = None, memory_type: str = None,
                    min_importance: int = 3, limit: int = 100) -> List[Dict]:
        """Retrieve memories"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM memories WHERE importance >= ?"
            params = [min_importance]
            
            if user_name:
                query += " AND user_name = ?"
                params.append(user_name)
            
            if memory_type:
                query += " AND memory_type = ?"
                params.append(memory_type)
            
            query += " ORDER BY importance DESC, last_accessed DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            memories = [dict(row) for row in cursor.fetchall()]
            
            # Update access timestamp
            memory_ids = [m['id'] for m in memories]
            if memory_ids:
                placeholders = ','.join('?' * len(memory_ids))
                cursor.execute(f"""
                    UPDATE memories 
                    SET last_accessed = CURRENT_TIMESTAMP,
                        access_count = access_count + 1
                    WHERE id IN ({placeholders})
                """, memory_ids)
            
            return memories
    
    def search_memories(self, query: str, user_name: str = None, limit: int = 10) -> List[Dict]:
        """Search memories by content"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            search_query = f"%{query}%"
            
            if user_name:
                cursor.execute("""
                    SELECT * FROM memories
                    WHERE (content LIKE ? OR context LIKE ?) AND user_name = ?
                    ORDER BY importance DESC, last_accessed DESC
                    LIMIT ?
                """, (search_query, search_query, user_name, limit))
            else:
                cursor.execute("""
                    SELECT * FROM memories
                    WHERE content LIKE ? OR context LIKE ?
                    ORDER BY importance DESC, last_accessed DESC
                    LIMIT ?
                """, (search_query, search_query, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # ===== Preferences =====
    
    def save_preference(self, user_name: str, key: str, value: Any) -> bool:
        """Save or update a user preference"""
        value_str = json.dumps(value) if not isinstance(value, str) else value
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO preferences 
                    (user_name, preference_key, preference_value, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_name, key, value_str))
                return True
        except Exception as e:
            logger.error(f"Error saving preference: {e}")
            return False
    
    def get_preference(self, user_name: str, key: str, default: Any = None) -> Any:
        """Get a user preference"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT preference_value FROM preferences
                WHERE user_name = ? AND preference_key = ?
            """, (user_name, key))
            
            result = cursor.fetchone()
            if result:
                try:
                    return json.loads(result['preference_value'])
                except:
                    return result['preference_value']
            return default
    
    def get_all_preferences(self, user_name: str) -> Dict:
        """Get all preferences for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT preference_key, preference_value FROM preferences
                WHERE user_name = ?
            """, (user_name,))
            
            prefs = {}
            for row in cursor.fetchall():
                try:
                    prefs[row['preference_key']] = json.loads(row['preference_value'])
                except:
                    prefs[row['preference_key']] = row['preference_value']
            
            return prefs
    
    # ===== Reminders & Tasks =====
    
    def create_reminder(self, user_name: str, title: str, due_datetime: datetime,
                       description: str = None, recurring: str = None,
                       priority: int = 3, category: str = None) -> int:
        """Create a new reminder"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reminders 
                (user_name, title, description, due_datetime, recurring, priority, category)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_name, title, description, due_datetime, recurring, priority, category))
            return cursor.lastrowid
    
    def get_due_reminders(self, user_name: str = None, hours_ahead: int = 24) -> List[Dict]:
        """Get reminders that are due soon"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            until = datetime.now() + timedelta(hours=hours_ahead)
            
            if user_name:
                cursor.execute("""
                    SELECT * FROM reminders
                    WHERE user_name = ? AND completed = FALSE 
                    AND due_datetime <= ?
                    ORDER BY due_datetime ASC
                """, (user_name, until))
            else:
                cursor.execute("""
                    SELECT * FROM reminders
                    WHERE completed = FALSE AND due_datetime <= ?
                    ORDER BY due_datetime ASC
                """, (until,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def complete_reminder(self, reminder_id: int) -> bool:
        """Mark a reminder as completed"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE reminders SET completed = TRUE 
                    WHERE id = ?
                """, (reminder_id,))
                return True
        except Exception as e:
            logger.error(f"Error completing reminder: {e}")
            return False
    
    def create_task(self, user_name: str, title: str, description: str = None,
                   priority: int = 3, due_date: datetime = None,
                   category: str = None, tags: List[str] = None) -> int:
        """Create a new task"""
        tags_str = json.dumps(tags) if tags else None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks 
                (user_name, title, description, priority, due_date, category, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_name, title, description, priority, due_date, category, tags_str))
            return cursor.lastrowid
    
    def get_tasks(self, user_name: str, status: str = 'pending',
                 limit: int = 50) -> List[Dict]:
        """Get tasks for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tasks
                WHERE user_name = ? AND status = ?
                ORDER BY priority DESC, due_date ASC
                LIMIT ?
            """, (user_name, status, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def complete_task(self, task_id: int) -> bool:
        """Mark a task as completed"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE tasks 
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (task_id,))
                return True
        except Exception as e:
            logger.error(f"Error completing task: {e}")
            return False
    
    # ===== Notes =====
    
    def create_note(self, user_name: str, title: str, content: str,
                   category: str = None, tags: List[str] = None) -> int:
        """Create a new note"""
        tags_str = json.dumps(tags) if tags else None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notes (user_name, title, content, category, tags)
                VALUES (?, ?, ?, ?, ?)
            """, (user_name, title, content, category, tags_str))
            return cursor.lastrowid
    
    def search_notes(self, user_name: str, query: str, limit: int = 20) -> List[Dict]:
        """Search notes by content"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            search_query = f"%{query}%"
            cursor.execute("""
                SELECT * FROM notes
                WHERE user_name = ? AND (title LIKE ? OR content LIKE ?)
                ORDER BY updated_at DESC
                LIMIT ?
            """, (user_name, search_query, search_query, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # ===== Activity Logging =====
    
    def log_activity(self, user_name: str, activity_type: str, 
                    description: str, metadata: Dict = None):
        """Log an activity"""
        metadata_str = json.dumps(metadata) if metadata else None
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO activity_log 
                (user_name, activity_type, description, metadata)
                VALUES (?, ?, ?, ?)
            """, (user_name, activity_type, description, metadata_str))
    
    def get_activity_stats(self, user_name: str, days: int = 7) -> Dict:
        """Get activity statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            since = datetime.now() - timedelta(days=days)
            
            cursor.execute("""
                SELECT activity_type, COUNT(*) as count
                FROM activity_log
                WHERE user_name = ? AND timestamp > ?
                GROUP BY activity_type
            """, (user_name, since))
            
            stats = {}
            for row in cursor.fetchall():
                stats[row['activity_type']] = row['count']
            
            return stats
    
    # ===== Maintenance =====
    
    def cleanup_old_data(self, days_to_keep: int = 365):
        """Clean up old data based on retention policy"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Clean old conversations (keep only important ones)
            cursor.execute("""
                DELETE FROM conversations
                WHERE timestamp < ? AND importance < 7
            """, (cutoff_date,))
            
            # Clean old activity logs
            cursor.execute("""
                DELETE FROM activity_log
                WHERE timestamp < ?
            """, (cutoff_date,))
            
            logger.info(f"Cleaned up data older than {days_to_keep} days")
    
    def backup_database(self, backup_path: Path):
        """Create a backup of the database"""
        import shutil
        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            tables = ['conversations', 'memories', 'preferences', 'reminders', 
                     'tasks', 'notes', 'documents', 'activity_log']
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                stats[table] = cursor.fetchone()['count']
            
            # Database size
            stats['db_size_mb'] = self.db_path.stat().st_size / (1024 * 1024)
            
            return stats


# ===== Convenience functions =====

def create_database(db_path: Path = None) -> BlueDatabase:
    """Create or connect to the Blue database"""
    if db_path is None:
        try:
            from config import DATABASE_PATH
            db_path = DATABASE_PATH
        except ImportError:
            # Fallback to default location
            db_path = Path(__file__).parent / "data" / "blue.db"

    return BlueDatabase(db_path)


if __name__ == "__main__":
    # Test the database
    db = create_database()
    
    print("Blue Database Test")
    print("=" * 50)
    
    # Test conversation
    conv_id = db.save_conversation("Alex", "user", "Hello Blue!")
    print(f"Saved conversation: {conv_id}")
    
    # Test memory
    db.save_memory("Alex", "preference", "likes coffee in the morning", 
                   importance=8, tags=["routine", "food"])
    print("Saved memory")
    
    # Test reminder
    from datetime import datetime, timedelta
    tomorrow = datetime.now() + timedelta(days=1)
    reminder_id = db.create_reminder("Alex", "Meeting", tomorrow, 
                                     description="Team meeting at 2pm")
    print(f"Created reminder: {reminder_id}")
    
    # Get stats
    stats = db.get_database_stats()
    print("\nDatabase Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nDatabase test completed successfully!")
