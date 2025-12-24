"""
Blue Robot Journal & Mood Tracker
==================================
Daily journaling with mood tracking, reflection, and mental wellness insights.
"""

# Future imports
from __future__ import annotations

# Standard library
import datetime
import json
import os
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ================================================================================
# CONFIGURATION
# ================================================================================

JOURNAL_DB = os.environ.get("BLUE_JOURNAL_DB", os.path.join("data", "journal.db"))


class MoodLevel(Enum):
    """Mood levels from 1-5"""
    VERY_BAD = 1
    BAD = 2
    NEUTRAL = 3
    GOOD = 4
    VERY_GOOD = 5


class EmotionTag(Enum):
    """Common emotions"""
    HAPPY = "happy"
    SAD = "sad"
    ANXIOUS = "anxious"
    CALM = "calm"
    EXCITED = "excited"
    STRESSED = "stressed"
    GRATEFUL = "grateful"
    ANGRY = "angry"
    LONELY = "lonely"
    CONTENT = "content"
    MOTIVATED = "motivated"
    TIRED = "tired"
    ENERGETIC = "energetic"
    OVERWHELMED = "overwhelmed"
    PEACEFUL = "peaceful"


class EntryType(Enum):
    """Type of journal entry"""
    DAILY = "daily"
    GRATITUDE = "gratitude"
    REFLECTION = "reflection"
    DREAM = "dream"
    GOAL = "goal"
    FREE_FORM = "free_form"


@dataclass
class JournalEntry:
    """Represents a journal entry"""
    id: str
    date: float
    entry_type: EntryType
    title: str
    content: str
    mood: MoodLevel
    emotions: List[str]
    tags: List[str]
    created_at: float
    updated_at: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "date": datetime.datetime.fromtimestamp(self.date).isoformat(),
            "date_human": datetime.datetime.fromtimestamp(self.date).strftime("%b %d, %Y"),
            "entry_type": self.entry_type.value,
            "title": self.title,
            "content": self.content,
            "content_preview": self.content[:100] + "..." if len(self.content) > 100 else self.content,
            "mood": self.mood.value,
            "mood_name": self.mood.name.replace('_', ' ').title(),
            "emotions": self.emotions,
            "tags": self.tags,
            "created_at": datetime.datetime.fromtimestamp(self.created_at).isoformat()
        }


@dataclass
class MoodLog:
    """Represents a simple mood check-in"""
    id: str
    timestamp: float
    mood: MoodLevel
    note: Optional[str]
    emotions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": datetime.datetime.fromtimestamp(self.timestamp).isoformat(),
            "time_human": datetime.datetime.fromtimestamp(self.timestamp).strftime("%b %d, %Y %I:%M %p"),
            "mood": self.mood.value,
            "mood_name": self.mood.name.replace('_', ' ').title(),
            "note": self.note,
            "emotions": self.emotions
        }


@dataclass
class GratitudeEntry:
    """Represents a gratitude entry"""
    id: str
    date: float
    items: List[str]
    created_at: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "date": datetime.datetime.fromtimestamp(self.date).isoformat(),
            "date_human": datetime.datetime.fromtimestamp(self.date).strftime("%b %d, %Y"),
            "items": self.items,
            "count": len(self.items),
            "created_at": datetime.datetime.fromtimestamp(self.created_at).isoformat()
        }


# ================================================================================
# JOURNAL MANAGER
# ================================================================================

class JournalManager:
    """Manages journal entries, mood tracking, and reflections"""

    def __init__(self, db_path: str = JOURNAL_DB):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database tables"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Journal entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS journal_entries (
                id TEXT PRIMARY KEY,
                date REAL NOT NULL,
                entry_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                mood INTEGER NOT NULL,
                emotions TEXT,
                tags TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)

        # Mood logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mood_logs (
                id TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                mood INTEGER NOT NULL,
                note TEXT,
                emotions TEXT
            )
        """)

        # Gratitude entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gratitude_entries (
                id TEXT PRIMARY KEY,
                date REAL NOT NULL,
                items TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)

        # Reflection prompts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reflection_prompts (
                id TEXT PRIMARY KEY,
                prompt TEXT NOT NULL,
                category TEXT,
                used_count INTEGER DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()

        # Add default reflection prompts
        self._add_default_prompts()

    def _add_default_prompts(self):
        """Add default reflection prompts"""
        default_prompts = [
            ("What am I grateful for today?", "gratitude"),
            ("What did I learn today?", "growth"),
            ("What challenged me today?", "challenge"),
            ("What made me smile today?", "positive"),
            ("What would I do differently?", "reflection"),
            ("What am I looking forward to?", "future"),
            ("What did I accomplish today?", "achievement"),
            ("Who made a positive impact on my day?", "relationships"),
            ("What am I worried about?", "concerns"),
            ("How did I take care of myself today?", "self_care")
        ]

        conn = self._get_conn()
        cursor = conn.cursor()

        for prompt, category in default_prompts:
            cursor.execute("""
                INSERT OR IGNORE INTO reflection_prompts (id, prompt, category, used_count)
                VALUES (?, ?, ?, 0)
            """, (str(uuid.uuid4())[:8], prompt, category))

        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    # ==================== JOURNAL ENTRIES ====================

    def create_entry(self, title: str, content: str, mood: int,
                    entry_type: str = "daily", emotions: List[str] = None,
                    tags: List[str] = None, date: float = None) -> JournalEntry:
        """Create a new journal entry"""
        entry_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().timestamp()
        entry_date = date if date else now

        try:
            type_enum = EntryType(entry_type.lower())
        except ValueError:
            type_enum = EntryType.FREE_FORM

        entry = JournalEntry(
            id=entry_id,
            date=entry_date,
            entry_type=type_enum,
            title=title,
            content=content,
            mood=MoodLevel(mood),
            emotions=emotions or [],
            tags=tags or [],
            created_at=now,
            updated_at=now
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO journal_entries (id, date, entry_type, title, content, mood, emotions, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (entry.id, entry.date, entry.entry_type.value, entry.title,
              entry.content, entry.mood.value, json.dumps(entry.emotions),
              json.dumps(entry.tags), entry.created_at, entry.updated_at))
        conn.commit()
        conn.close()

        return entry

    def get_entry(self, entry_id: str) -> Optional[JournalEntry]:
        """Get a journal entry by ID"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM journal_entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return JournalEntry(
                id=row[0], date=row[1], entry_type=EntryType(row[2]),
                title=row[3], content=row[4], mood=MoodLevel(row[5]),
                emotions=json.loads(row[6] or "[]"),
                tags=json.loads(row[7] or "[]"),
                created_at=row[8], updated_at=row[9]
            )
        return None

    def get_entries(self, start_date: float = None, end_date: float = None,
                   entry_type: str = None, limit: int = 30) -> List[JournalEntry]:
        """Get journal entries with optional filtering"""
        conn = self._get_conn()
        cursor = conn.cursor()

        sql = "SELECT * FROM journal_entries WHERE 1=1"
        params = []

        if start_date:
            sql += " AND date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND date <= ?"
            params.append(end_date)
        if entry_type:
            sql += " AND entry_type = ?"
            params.append(entry_type.lower())

        sql += " ORDER BY date DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            JournalEntry(
                id=row[0], date=row[1], entry_type=EntryType(row[2]),
                title=row[3], content=row[4], mood=MoodLevel(row[5]),
                emotions=json.loads(row[6] or "[]"),
                tags=json.loads(row[7] or "[]"),
                created_at=row[8], updated_at=row[9]
            )
            for row in rows
        ]

    def search_entries(self, query: str, limit: int = 20) -> List[JournalEntry]:
        """Search journal entries by content"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM journal_entries
            WHERE title LIKE ? OR content LIKE ?
            ORDER BY date DESC LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))
        rows = cursor.fetchall()
        conn.close()

        return [
            JournalEntry(
                id=row[0], date=row[1], entry_type=EntryType(row[2]),
                title=row[3], content=row[4], mood=MoodLevel(row[5]),
                emotions=json.loads(row[6] or "[]"),
                tags=json.loads(row[7] or "[]"),
                created_at=row[8], updated_at=row[9]
            )
            for row in rows
        ]

    # ==================== MOOD TRACKING ====================

    def log_mood(self, mood: int, note: str = None, emotions: List[str] = None) -> MoodLog:
        """Log current mood"""
        log_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().timestamp()

        mood_log = MoodLog(
            id=log_id,
            timestamp=now,
            mood=MoodLevel(mood),
            note=note,
            emotions=emotions or []
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO mood_logs (id, timestamp, mood, note, emotions)
            VALUES (?, ?, ?, ?, ?)
        """, (mood_log.id, mood_log.timestamp, mood_log.mood.value,
              mood_log.note, json.dumps(mood_log.emotions)))
        conn.commit()
        conn.close()

        return mood_log

    def get_mood_history(self, days: int = 7) -> List[MoodLog]:
        """Get mood history for past N days"""
        start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).timestamp()

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM mood_logs
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        """, (start_date,))
        rows = cursor.fetchall()
        conn.close()

        return [
            MoodLog(
                id=row[0], timestamp=row[1], mood=MoodLevel(row[2]),
                note=row[3], emotions=json.loads(row[4] or "[]")
            )
            for row in rows
        ]

    def get_mood_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get mood statistics for period"""
        mood_history = self.get_mood_history(days)

        if not mood_history:
            return {
                "average_mood": 0,
                "total_logs": 0,
                "mood_distribution": {}
            }

        moods = [log.mood.value for log in mood_history]
        avg_mood = sum(moods) / len(moods)

        # Count distribution
        distribution = {}
        for mood_level in MoodLevel:
            count = sum(1 for m in moods if m == mood_level.value)
            if count > 0:
                distribution[mood_level.name.replace('_', ' ').title()] = count

        # Most common emotions
        all_emotions = []
        for log in mood_history:
            all_emotions.extend(log.emotions)

        emotion_counts = {}
        for emotion in all_emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

        top_emotions = sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "average_mood": round(avg_mood, 2),
            "total_logs": len(mood_history),
            "mood_distribution": distribution,
            "top_emotions": dict(top_emotions),
            "period_days": days
        }

    # ==================== GRATITUDE ====================

    def add_gratitude(self, items: List[str], date: float = None) -> GratitudeEntry:
        """Add gratitude entry"""
        entry_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().timestamp()
        entry_date = date if date else now

        gratitude = GratitudeEntry(
            id=entry_id,
            date=entry_date,
            items=items,
            created_at=now
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO gratitude_entries (id, date, items, created_at)
            VALUES (?, ?, ?, ?)
        """, (gratitude.id, gratitude.date, json.dumps(gratitude.items), gratitude.created_at))
        conn.commit()
        conn.close()

        return gratitude

    def get_gratitude_entries(self, days: int = 7) -> List[GratitudeEntry]:
        """Get recent gratitude entries"""
        start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).timestamp()

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM gratitude_entries
            WHERE date >= ?
            ORDER BY date DESC
        """, (start_date,))
        rows = cursor.fetchall()
        conn.close()

        return [
            GratitudeEntry(
                id=row[0], date=row[1], items=json.loads(row[2]),
                created_at=row[3]
            )
            for row in rows
        ]

    # ==================== REFLECTION PROMPTS ====================

    def get_random_prompt(self) -> Optional[str]:
        """Get a random reflection prompt"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, prompt FROM reflection_prompts
            ORDER BY used_count ASC, RANDOM()
            LIMIT 1
        """)
        row = cursor.fetchone()

        if row:
            # Increment usage count
            cursor.execute("UPDATE reflection_prompts SET used_count = used_count + 1 WHERE id = ?", (row[0],))
            conn.commit()

        conn.close()
        return row[1] if row else None


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_journal_manager: Optional[JournalManager] = None


def get_journal_manager() -> JournalManager:
    """Get or create singleton journal manager instance"""
    global _journal_manager
    if _journal_manager is None:
        _journal_manager = JournalManager()
    return _journal_manager


# ================================================================================
# COMMAND FUNCTIONS
# ================================================================================

def create_journal_entry_cmd(title: str, content: str, mood: int,
                            entry_type: str = "daily", emotions: str = None) -> str:
    """Create a journal entry"""
    manager = get_journal_manager()

    emotion_list = []
    if emotions:
        emotion_list = [e.strip() for e in emotions.split(',')]

    entry = manager.create_entry(title, content, mood, entry_type, emotion_list)

    return json.dumps({
        "status": "success",
        "message": f"Journal entry '{title}' created",
        "entry": entry.to_dict()
    })


def get_journal_entries_cmd(days: int = 7, entry_type: str = None) -> str:
    """Get recent journal entries"""
    manager = get_journal_manager()

    start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).timestamp()
    entries = manager.get_entries(start_date=start_date, entry_type=entry_type)

    return json.dumps({
        "status": "success",
        "count": len(entries),
        "entries": [e.to_dict() for e in entries]
    })


def log_mood_cmd(mood: int, note: str = None, emotions: str = None) -> str:
    """Log current mood"""
    manager = get_journal_manager()

    emotion_list = []
    if emotions:
        emotion_list = [e.strip() for e in emotions.split(',')]

    mood_log = manager.log_mood(mood, note, emotion_list)

    return json.dumps({
        "status": "success",
        "message": f"Mood logged: {mood_log.mood.name.replace('_', ' ').title()}",
        "mood_log": mood_log.to_dict()
    })


def get_mood_stats_cmd(days: int = 30) -> str:
    """Get mood statistics"""
    manager = get_journal_manager()

    stats = manager.get_mood_stats(days)

    return json.dumps({
        "status": "success",
        "stats": stats
    })


def add_gratitude_cmd(items: str) -> str:
    """Add gratitude entry"""
    manager = get_journal_manager()

    item_list = [item.strip() for item in items.split(',')]
    gratitude = manager.add_gratitude(item_list)

    return json.dumps({
        "status": "success",
        "message": f"Added {len(item_list)} gratitude items",
        "gratitude": gratitude.to_dict()
    })


def get_gratitude_list_cmd(days: int = 7) -> str:
    """Get recent gratitude entries"""
    manager = get_journal_manager()

    entries = manager.get_gratitude_entries(days)

    return json.dumps({
        "status": "success",
        "count": len(entries),
        "gratitude_entries": [e.to_dict() for e in entries]
    })


def get_reflection_prompt_cmd() -> str:
    """Get a reflection prompt"""
    manager = get_journal_manager()

    prompt = manager.get_random_prompt()

    if prompt:
        return json.dumps({
            "status": "success",
            "prompt": prompt
        })
    else:
        return json.dumps({
            "status": "error",
            "error": "No prompts available"
        })


__all__ = [
    'JournalManager',
    'JournalEntry',
    'MoodLog',
    'GratitudeEntry',
    'MoodLevel',
    'EmotionTag',
    'EntryType',
    'get_journal_manager',
    'create_journal_entry_cmd',
    'get_journal_entries_cmd',
    'log_mood_cmd',
    'get_mood_stats_cmd',
    'add_gratitude_cmd',
    'get_gratitude_list_cmd',
    'get_reflection_prompt_cmd',
]
