"""
Blue Robot Habit Tracking Tool
===============================
Track daily habits, build streaks, and achieve goals.

Features:
- Track daily, weekly, or custom habits
- Streak counting and motivation
- Goal setting with progress tracking
- Habit statistics and insights
- Reminders for habit completion
- Visual progress reports
- Habit chains and dependencies
"""

from __future__ import annotations

import datetime
import json
import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ================================================================================
# CONFIGURATION
# ================================================================================

HABITS_DB = os.environ.get("BLUE_HABITS_DB", "data/habits.db")


class HabitFrequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"  # Custom days of week


class HabitCategory(Enum):
    HEALTH = "health"
    FITNESS = "fitness"
    LEARNING = "learning"
    PRODUCTIVITY = "productivity"
    SOCIAL = "social"
    MINDFULNESS = "mindfulness"
    CREATIVE = "creative"
    FINANCIAL = "financial"
    OTHER = "other"


@dataclass
class Habit:
    """Represents a habit to track."""
    id: str
    name: str
    description: str
    frequency: HabitFrequency
    category: HabitCategory
    target_count: int = 1  # How many times per day/week
    custom_days: List[int] = field(default_factory=list)  # 0=Monday, 6=Sunday
    reminder_time: Optional[str] = None  # HH:MM format
    active: bool = True
    created_at: float = field(default_factory=lambda: datetime.datetime.now().timestamp())
    current_streak: int = 0
    best_streak: int = 0
    total_completions: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "frequency": self.frequency.value,
            "category": self.category.value,
            "target_count": self.target_count,
            "custom_days": self.custom_days,
            "reminder_time": self.reminder_time,
            "active": self.active,
            "created_at": self.created_at,
            "current_streak": self.current_streak,
            "best_streak": self.best_streak,
            "total_completions": self.total_completions,
        }

    def is_due_today(self) -> bool:
        """Check if habit is due today."""
        if not self.active:
            return False

        today = datetime.datetime.now().weekday()

        if self.frequency == HabitFrequency.DAILY:
            return True
        elif self.frequency == HabitFrequency.WEEKLY:
            return today == 0  # Monday
        elif self.frequency == HabitFrequency.CUSTOM:
            return today in self.custom_days

        return False


@dataclass
class HabitCompletion:
    """Represents a habit completion entry."""
    id: str
    habit_id: str
    completed_at: float
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "habit_id": self.habit_id,
            "completed_at": self.completed_at,
            "notes": self.notes,
        }


# ================================================================================
# HABIT MANAGER
# ================================================================================

class HabitManager:
    """Manages habit tracking with persistent storage."""

    def __init__(self, db_path: str = HABITS_DB):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                frequency TEXT,
                category TEXT,
                target_count INTEGER,
                custom_days TEXT,
                reminder_time TEXT,
                active INTEGER,
                created_at REAL,
                current_streak INTEGER,
                best_streak INTEGER,
                total_completions INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habit_completions (
                id TEXT PRIMARY KEY,
                habit_id TEXT,
                completed_at REAL,
                notes TEXT,
                FOREIGN KEY (habit_id) REFERENCES habits (id)
            )
        """)

        conn.commit()
        conn.close()

    def create_habit(
        self,
        name: str,
        description: str,
        frequency: HabitFrequency = HabitFrequency.DAILY,
        category: HabitCategory = HabitCategory.OTHER,
        target_count: int = 1,
        custom_days: Optional[List[int]] = None,
        reminder_time: Optional[str] = None,
    ) -> Habit:
        """Create a new habit."""
        habit = Habit(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            frequency=frequency,
            category=category,
            target_count=target_count,
            custom_days=custom_days or [],
            reminder_time=reminder_time,
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO habits VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            habit.id, habit.name, habit.description, habit.frequency.value,
            habit.category.value, habit.target_count, json.dumps(habit.custom_days),
            habit.reminder_time, 1 if habit.active else 0, habit.created_at,
            habit.current_streak, habit.best_streak, habit.total_completions
        ))

        conn.commit()
        conn.close()

        return habit

    def get_habit(self, habit_id: str) -> Optional[Habit]:
        """Get a habit by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM habits WHERE id = ?", (habit_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_habit(row)

    def find_habit_by_name(self, name: str) -> Optional[Habit]:
        """Find a habit by name (case-insensitive)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM habits WHERE LOWER(name) = ? LIMIT 1",
            (name.lower(),)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_habit(row)

    def list_habits(
        self,
        category: Optional[HabitCategory] = None,
        active_only: bool = True,
        due_today: bool = False,
    ) -> List[Habit]:
        """List habits with optional filters."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM habits WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category.value)

        if active_only:
            query += " AND active = 1"

        query += " ORDER BY name"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        habits = [self._row_to_habit(row) for row in rows]

        if due_today:
            habits = [h for h in habits if h.is_due_today()]

        return habits

    def update_habit(self, habit_id: str, **updates) -> bool:
        """Update a habit."""
        habit = self.get_habit(habit_id)
        if not habit:
            return False

        # Update fields
        for key, value in updates.items():
            if hasattr(habit, key):
                setattr(habit, key, value)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE habits SET
                name = ?, description = ?, frequency = ?, category = ?,
                target_count = ?, custom_days = ?, reminder_time = ?, active = ?
            WHERE id = ?
        """, (
            habit.name, habit.description, habit.frequency.value,
            habit.category.value, habit.target_count, json.dumps(habit.custom_days),
            habit.reminder_time, 1 if habit.active else 0, habit.id
        ))

        conn.commit()
        conn.close()

        return True

    def delete_habit(self, habit_id: str) -> bool:
        """Delete a habit."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    def complete_habit(
        self,
        habit_id: str,
        notes: Optional[str] = None,
        completed_at: Optional[float] = None,
    ) -> bool:
        """Mark a habit as completed."""
        habit = self.get_habit(habit_id)
        if not habit:
            return False

        if completed_at is None:
            completed_at = datetime.datetime.now().timestamp()

        completion = HabitCompletion(
            id=str(uuid.uuid4()),
            habit_id=habit_id,
            completed_at=completed_at,
            notes=notes,
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Add completion
        cursor.execute("""
            INSERT INTO habit_completions VALUES (?, ?, ?, ?)
        """, (completion.id, completion.habit_id, completion.completed_at, completion.notes))

        # Update habit stats
        new_streak = self._calculate_streak(habit_id)
        new_total = habit.total_completions + 1
        new_best = max(habit.best_streak, new_streak)

        cursor.execute("""
            UPDATE habits SET
                current_streak = ?,
                best_streak = ?,
                total_completions = ?
            WHERE id = ?
        """, (new_streak, new_best, new_total, habit_id))

        conn.commit()
        conn.close()

        return True

    def get_completions_today(self, habit_id: str) -> int:
        """Get number of completions for a habit today."""
        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_start_ts = today_start.timestamp()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM habit_completions
            WHERE habit_id = ? AND completed_at >= ?
        """, (habit_id, today_start_ts))

        count = cursor.fetchone()[0]
        conn.close()

        return count

    def get_completion_history(
        self,
        habit_id: str,
        days: int = 30
    ) -> List[HabitCompletion]:
        """Get completion history for a habit."""
        cutoff = datetime.datetime.now().timestamp() - (days * 86400)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM habit_completions
            WHERE habit_id = ? AND completed_at >= ?
            ORDER BY completed_at DESC
        """, (habit_id, cutoff))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_completion(row) for row in rows]

    def get_statistics(self, habit_id: str) -> Dict[str, Any]:
        """Get statistics for a habit."""
        habit = self.get_habit(habit_id)
        if not habit:
            return {}

        history = self.get_completion_history(habit_id, days=30)

        # Calculate completion rate for last 30 days
        days_active = min(30, int((datetime.datetime.now().timestamp() - habit.created_at) / 86400))
        completion_rate = (len(history) / max(1, days_active)) * 100 if days_active > 0 else 0

        return {
            "current_streak": habit.current_streak,
            "best_streak": habit.best_streak,
            "total_completions": habit.total_completions,
            "completions_last_30_days": len(history),
            "completion_rate_30_days": round(completion_rate, 1),
            "days_active": days_active,
        }

    def _calculate_streak(self, habit_id: str) -> int:
        """Calculate current streak for a habit."""
        habit = self.get_habit(habit_id)
        if not habit:
            return 0

        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        streak = 0

        # Check backwards from today
        check_date = today
        while True:
            check_date_start = check_date.timestamp()
            check_date_end = (check_date + datetime.timedelta(days=1)).timestamp()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) FROM habit_completions
                WHERE habit_id = ? AND completed_at >= ? AND completed_at < ?
            """, (habit_id, check_date_start, check_date_end))

            count = cursor.fetchone()[0]
            conn.close()

            if count >= habit.target_count:
                streak += 1
                check_date -= datetime.timedelta(days=1)
            else:
                # Allow today to not be completed yet
                if check_date.date() == today.date():
                    check_date -= datetime.timedelta(days=1)
                    continue
                break

        return streak

    def _row_to_habit(self, row: tuple) -> Habit:
        """Convert database row to Habit."""
        return Habit(
            id=row[0],
            name=row[1],
            description=row[2] or "",
            frequency=HabitFrequency(row[3]),
            category=HabitCategory(row[4]),
            target_count=row[5],
            custom_days=json.loads(row[6]) if row[6] else [],
            reminder_time=row[7],
            active=bool(row[8]),
            created_at=row[9],
            current_streak=row[10],
            best_streak=row[11],
            total_completions=row[12],
        )

    def _row_to_completion(self, row: tuple) -> HabitCompletion:
        """Convert database row to HabitCompletion."""
        return HabitCompletion(
            id=row[0],
            habit_id=row[1],
            completed_at=row[2],
            notes=row[3],
        )


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_habit_manager: Optional[HabitManager] = None


def get_habit_manager() -> HabitManager:
    """Get the global habit manager instance."""
    global _habit_manager
    if _habit_manager is None:
        _habit_manager = HabitManager()
    return _habit_manager


# ================================================================================
# COMMAND FUNCTIONS
# ================================================================================

def create_habit_cmd(
    name: str,
    description: str,
    frequency: str = "daily",
    category: str = "other",
    target_count: int = 1,
) -> str:
    """Create a new habit."""
    try:
        manager = get_habit_manager()

        # Parse frequency
        try:
            freq = HabitFrequency(frequency.lower())
        except ValueError:
            freq = HabitFrequency.DAILY

        # Parse category
        try:
            cat = HabitCategory(category.lower())
        except ValueError:
            cat = HabitCategory.OTHER

        habit = manager.create_habit(
            name=name,
            description=description,
            frequency=freq,
            category=cat,
            target_count=target_count,
        )

        return json.dumps({
            "success": True,
            "habit_id": habit.id,
            "name": habit.name,
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to create habit: {str(e)}"
        })


def list_habits_cmd(category: Optional[str] = None, due_today: bool = False) -> str:
    """List habits."""
    try:
        manager = get_habit_manager()

        # Parse category filter
        cat_filter = None
        if category:
            try:
                cat_filter = HabitCategory(category.lower())
            except ValueError:
                pass

        habits = manager.list_habits(cat_filter, active_only=True, due_today=due_today)

        return json.dumps({
            "success": True,
            "count": len(habits),
            "habits": [h.to_dict() for h in habits]
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to list habits: {str(e)}"
        })


def complete_habit_cmd(habit_name: str, notes: Optional[str] = None) -> str:
    """Mark a habit as completed."""
    try:
        manager = get_habit_manager()
        habit = manager.find_habit_by_name(habit_name)

        if not habit:
            return json.dumps({
                "success": False,
                "error": f"Habit not found: {habit_name}"
            })

        success = manager.complete_habit(habit.id, notes=notes)

        if success:
            # Get updated stats
            updated_habit = manager.get_habit(habit.id)
            return json.dumps({
                "success": True,
                "habit": habit.name,
                "current_streak": updated_habit.current_streak if updated_habit else 0,
                "total_completions": updated_habit.total_completions if updated_habit else 0,
            })
        else:
            return json.dumps({
                "success": False,
                "error": "Failed to complete habit"
            })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to complete habit: {str(e)}"
        })


def habit_stats_cmd(habit_name: str) -> str:
    """Get statistics for a habit."""
    try:
        manager = get_habit_manager()
        habit = manager.find_habit_by_name(habit_name)

        if not habit:
            return json.dumps({
                "success": False,
                "error": f"Habit not found: {habit_name}"
            })

        stats = manager.get_statistics(habit.id)

        return json.dumps({
            "success": True,
            "habit": habit.name,
            "statistics": stats
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to get statistics: {str(e)}"
        })


def execute_habit_command(command: str, **params) -> str:
    """Execute a habit command."""
    commands = {
        "create": create_habit_cmd,
        "list": list_habits_cmd,
        "complete": complete_habit_cmd,
        "stats": habit_stats_cmd,
    }

    handler = commands.get(command)
    if not handler:
        return json.dumps({
            "success": False,
            "error": f"Unknown habit command: {command}"
        })

    return handler(**params)
