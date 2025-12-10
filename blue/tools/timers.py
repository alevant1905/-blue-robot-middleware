"""
Blue Robot Timer and Reminder Tools
====================================
Manage timers, alarms, and reminders with notifications.
"""

from __future__ import annotations

import datetime
import json
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Try to import notification libraries
try:
    from plyer import notification as plyer_notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False


# ================================================================================
# CONFIGURATION
# ================================================================================

TIMERS_DB = os.environ.get("BLUE_TIMERS_DB", "data/timers.db")


class TimerType(Enum):
    TIMER = "timer"  # Countdown from duration
    ALARM = "alarm"  # Fire at specific time
    REMINDER = "reminder"  # Fire at specific time with message


@dataclass
class TimerEntry:
    """Represents a timer, alarm, or reminder."""
    id: str
    timer_type: TimerType
    name: str
    created_at: float
    trigger_at: float
    message: Optional[str] = None
    repeat: Optional[str] = None  # "daily", "weekly", "weekdays", None
    is_active: bool = True
    fired: bool = False

    def time_remaining(self) -> float:
        """Get seconds remaining until trigger."""
        return max(0, self.trigger_at - time.time())

    def time_remaining_str(self) -> str:
        """Get human-readable time remaining."""
        remaining = self.time_remaining()
        if remaining <= 0:
            return "now"

        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        seconds = int(remaining % 60)

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 and hours == 0:  # Only show seconds if < 1 hour
            parts.append(f"{seconds}s")

        return " ".join(parts) if parts else "< 1s"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.timer_type.value,
            "name": self.name,
            "created_at": self.created_at,
            "trigger_at": self.trigger_at,
            "trigger_time": datetime.datetime.fromtimestamp(self.trigger_at).strftime("%Y-%m-%d %H:%M:%S"),
            "message": self.message,
            "repeat": self.repeat,
            "is_active": self.is_active,
            "fired": self.fired,
            "time_remaining": self.time_remaining_str()
        }


# ================================================================================
# TIMER MANAGER
# ================================================================================

class TimerManager:
    """Manages all timers, alarms, and reminders."""

    def __init__(self, db_path: str = TIMERS_DB):
        self.db_path = db_path
        self.timers: Dict[str, TimerEntry] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[TimerEntry], None]] = []

        self._init_db()
        self._load_timers()

    def _init_db(self):
        """Initialize the database."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS timers (
                id TEXT PRIMARY KEY,
                timer_type TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at REAL NOT NULL,
                trigger_at REAL NOT NULL,
                message TEXT,
                repeat TEXT,
                is_active INTEGER DEFAULT 1,
                fired INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def _load_timers(self):
        """Load active timers from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM timers WHERE is_active = 1")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            entry = TimerEntry(
                id=row[0],
                timer_type=TimerType(row[1]),
                name=row[2],
                created_at=row[3],
                trigger_at=row[4],
                message=row[5],
                repeat=row[6],
                is_active=bool(row[7]),
                fired=bool(row[8])
            )
            self.timers[entry.id] = entry

    def _save_timer(self, entry: TimerEntry):
        """Save timer to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO timers
            (id, timer_type, name, created_at, trigger_at, message, repeat, is_active, fired)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.id, entry.timer_type.value, entry.name, entry.created_at,
            entry.trigger_at, entry.message, entry.repeat,
            1 if entry.is_active else 0, 1 if entry.fired else 0
        ))
        conn.commit()
        conn.close()

    def _delete_timer_db(self, timer_id: str):
        """Delete timer from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM timers WHERE id = ?", (timer_id,))
        conn.commit()
        conn.close()

    def add_callback(self, callback: Callable[[TimerEntry], None]):
        """Add a callback for when timers fire."""
        self._callbacks.append(callback)

    def _notify(self, entry: TimerEntry):
        """Send notification when timer fires."""
        title = f"Blue: {entry.timer_type.value.title()}"
        message = entry.message or entry.name

        # Play sound
        if WINSOUND_AVAILABLE:
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass

        # Show notification
        if PLYER_AVAILABLE:
            try:
                plyer_notification.notify(
                    title=title,
                    message=message,
                    app_name="Blue Assistant",
                    timeout=10
                )
            except Exception as e:
                print(f"[TIMER] Notification error: {e}")

        # Call registered callbacks
        for callback in self._callbacks:
            try:
                callback(entry)
            except Exception as e:
                print(f"[TIMER] Callback error: {e}")

        print(f"[TIMER] Fired: {entry.name} - {message}")

    def _check_timers(self):
        """Check and fire due timers."""
        now = time.time()

        with self._lock:
            for timer_id, entry in list(self.timers.items()):
                if not entry.is_active or entry.fired:
                    continue

                if entry.trigger_at <= now:
                    # Fire the timer
                    self._notify(entry)

                    if entry.repeat:
                        # Reschedule repeating timer
                        entry.trigger_at = self._get_next_repeat(entry)
                        self._save_timer(entry)
                    else:
                        # Mark as fired
                        entry.fired = True
                        entry.is_active = False
                        self._save_timer(entry)

    def _get_next_repeat(self, entry: TimerEntry) -> float:
        """Calculate next trigger time for repeating timer."""
        now = datetime.datetime.now()
        trigger_dt = datetime.datetime.fromtimestamp(entry.trigger_at)

        if entry.repeat == "daily":
            next_dt = trigger_dt + datetime.timedelta(days=1)
            while next_dt <= now:
                next_dt += datetime.timedelta(days=1)
        elif entry.repeat == "weekly":
            next_dt = trigger_dt + datetime.timedelta(weeks=1)
            while next_dt <= now:
                next_dt += datetime.timedelta(weeks=1)
        elif entry.repeat == "weekdays":
            next_dt = trigger_dt + datetime.timedelta(days=1)
            while next_dt <= now or next_dt.weekday() >= 5:  # Skip weekends
                next_dt += datetime.timedelta(days=1)
        else:
            return entry.trigger_at

        return next_dt.timestamp()

    def _run_loop(self):
        """Background loop to check timers."""
        while self._running:
            self._check_timers()
            time.sleep(1)  # Check every second

    def start(self):
        """Start the timer manager background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("[TIMER] Timer manager started")

    def stop(self):
        """Stop the timer manager."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        print("[TIMER] Timer manager stopped")

    def create_timer(self, duration_seconds: int, name: str = None) -> TimerEntry:
        """Create a countdown timer."""
        timer_id = str(uuid.uuid4())[:8]
        now = time.time()

        if not name:
            mins = duration_seconds // 60
            secs = duration_seconds % 60
            if mins > 0:
                name = f"{mins} minute timer" if secs == 0 else f"{mins}m {secs}s timer"
            else:
                name = f"{secs} second timer"

        entry = TimerEntry(
            id=timer_id,
            timer_type=TimerType.TIMER,
            name=name,
            created_at=now,
            trigger_at=now + duration_seconds,
            message=f"Timer complete: {name}"
        )

        with self._lock:
            self.timers[timer_id] = entry
            self._save_timer(entry)

        return entry

    def create_alarm(self, hour: int, minute: int, name: str = None,
                    repeat: str = None) -> TimerEntry:
        """Create an alarm for a specific time."""
        timer_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now()

        # Set alarm time for today
        alarm_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If time has passed today, set for tomorrow
        if alarm_dt <= now:
            alarm_dt += datetime.timedelta(days=1)

        if not name:
            name = f"Alarm for {hour:02d}:{minute:02d}"

        entry = TimerEntry(
            id=timer_id,
            timer_type=TimerType.ALARM,
            name=name,
            created_at=time.time(),
            trigger_at=alarm_dt.timestamp(),
            message=f"Alarm: {name}",
            repeat=repeat
        )

        with self._lock:
            self.timers[timer_id] = entry
            self._save_timer(entry)

        return entry

    def create_reminder(self, message: str, trigger_at: float = None,
                       delay_seconds: int = None, hour: int = None,
                       minute: int = None, repeat: str = None) -> TimerEntry:
        """Create a reminder with a message."""
        timer_id = str(uuid.uuid4())[:8]
        now = time.time()

        if trigger_at:
            target_time = trigger_at
        elif delay_seconds:
            target_time = now + delay_seconds
        elif hour is not None and minute is not None:
            dt = datetime.datetime.now()
            target_dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target_dt.timestamp() <= now:
                target_dt += datetime.timedelta(days=1)
            target_time = target_dt.timestamp()
        else:
            # Default: 1 hour from now
            target_time = now + 3600

        name = f"Reminder: {message[:30]}..." if len(message) > 30 else f"Reminder: {message}"

        entry = TimerEntry(
            id=timer_id,
            timer_type=TimerType.REMINDER,
            name=name,
            created_at=now,
            trigger_at=target_time,
            message=message,
            repeat=repeat
        )

        with self._lock:
            self.timers[timer_id] = entry
            self._save_timer(entry)

        return entry

    def cancel_timer(self, timer_id: str) -> bool:
        """Cancel a timer by ID."""
        with self._lock:
            if timer_id in self.timers:
                entry = self.timers[timer_id]
                entry.is_active = False
                self._save_timer(entry)
                del self.timers[timer_id]
                return True
        return False

    def cancel_by_name(self, name: str) -> int:
        """Cancel timers matching a name pattern."""
        cancelled = 0
        name_lower = name.lower()

        with self._lock:
            for timer_id, entry in list(self.timers.items()):
                if name_lower in entry.name.lower():
                    entry.is_active = False
                    self._save_timer(entry)
                    del self.timers[timer_id]
                    cancelled += 1

        return cancelled

    def list_timers(self, timer_type: TimerType = None) -> List[TimerEntry]:
        """List active timers."""
        with self._lock:
            timers = list(self.timers.values())

        if timer_type:
            timers = [t for t in timers if t.timer_type == timer_type]

        return sorted(timers, key=lambda t: t.trigger_at)

    def get_timer(self, timer_id: str) -> Optional[TimerEntry]:
        """Get a specific timer."""
        return self.timers.get(timer_id)

    def clear_all(self, timer_type: TimerType = None) -> int:
        """Clear all timers of a type (or all if type is None)."""
        cleared = 0

        with self._lock:
            for timer_id, entry in list(self.timers.items()):
                if timer_type is None or entry.timer_type == timer_type:
                    entry.is_active = False
                    self._save_timer(entry)
                    del self.timers[timer_id]
                    cleared += 1

        return cleared


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_timer_manager: Optional[TimerManager] = None


def get_timer_manager() -> TimerManager:
    """Get or create the global timer manager."""
    global _timer_manager
    if _timer_manager is None:
        _timer_manager = TimerManager()
        _timer_manager.start()
    return _timer_manager


# ================================================================================
# HELPER FUNCTIONS
# ================================================================================

def parse_duration(text: str) -> Optional[int]:
    """
    Parse duration text into seconds.

    Examples:
        "5 minutes" -> 300
        "1 hour 30 minutes" -> 5400
        "90 seconds" -> 90
        "2h 30m" -> 9000
    """
    text = text.lower().strip()
    total_seconds = 0

    # Pattern: number followed by unit
    patterns = [
        (r'(\d+)\s*(?:hours?|hrs?|h)\b', 3600),
        (r'(\d+)\s*(?:minutes?|mins?|m)\b', 60),
        (r'(\d+)\s*(?:seconds?|secs?|s)\b', 1),
    ]

    import re
    for pattern, multiplier in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            total_seconds += int(match) * multiplier

    return total_seconds if total_seconds > 0 else None


def parse_time(text: str) -> Optional[tuple]:
    """
    Parse time text into (hour, minute).

    Examples:
        "3:30 PM" -> (15, 30)
        "14:00" -> (14, 0)
        "noon" -> (12, 0)
        "midnight" -> (0, 0)
    """
    import re
    text = text.lower().strip()

    # Special times
    if text in ['noon', '12 noon', '12:00 noon']:
        return (12, 0)
    if text in ['midnight', '12 midnight', '12:00 midnight']:
        return (0, 0)

    # 12-hour format: 3:30 PM, 3:30pm, 3pm
    match = re.match(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)', text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        is_pm = 'p' in match.group(3)

        if hour == 12:
            hour = 0 if not is_pm else 12
        elif is_pm:
            hour += 12

        return (hour, minute)

    # 24-hour format: 14:00, 14:30
    match = re.match(r'(\d{1,2}):(\d{2})', text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        if 0 <= hour < 24 and 0 <= minute < 60:
            return (hour, minute)

    return None


def format_timer_list(timers: List[TimerEntry]) -> str:
    """Format a list of timers for display."""
    if not timers:
        return "No active timers."

    lines = []
    for t in timers:
        icon = {"timer": "⏱️", "alarm": "⏰", "reminder": "📝"}.get(t.timer_type.value, "⏱️")
        trigger_time = datetime.datetime.fromtimestamp(t.trigger_at).strftime("%I:%M %p")
        lines.append(f"{icon} [{t.id}] {t.name} - {t.time_remaining_str()} (at {trigger_time})")

    return "\n".join(lines)


# ================================================================================
# EXECUTOR FUNCTIONS
# ================================================================================

def set_timer(duration: str = None, seconds: int = None, name: str = None) -> str:
    """
    Set a countdown timer.

    Args:
        duration: Duration string like "5 minutes", "1 hour 30 minutes"
        seconds: Duration in seconds (alternative to duration string)
        name: Optional name for the timer

    Returns:
        JSON result
    """
    manager = get_timer_manager()

    if seconds:
        duration_secs = seconds
    elif duration:
        duration_secs = parse_duration(duration)
        if not duration_secs:
            return json.dumps({
                "success": False,
                "error": f"Could not parse duration: '{duration}'. Try '5 minutes' or '1 hour 30 minutes'."
            })
    else:
        return json.dumps({
            "success": False,
            "error": "Please specify a duration (e.g., '5 minutes')."
        })

    entry = manager.create_timer(duration_secs, name)

    return json.dumps({
        "success": True,
        "message": f"Timer set for {entry.time_remaining_str()}",
        "timer": entry.to_dict()
    })


def set_alarm(time_str: str = None, hour: int = None, minute: int = None,
              name: str = None, repeat: str = None) -> str:
    """
    Set an alarm for a specific time.

    Args:
        time_str: Time string like "7:30 AM", "14:00"
        hour: Hour (0-23)
        minute: Minute (0-59)
        name: Optional name
        repeat: "daily", "weekly", "weekdays", or None

    Returns:
        JSON result
    """
    manager = get_timer_manager()

    if hour is not None and minute is not None:
        target_hour, target_minute = hour, minute
    elif time_str:
        parsed = parse_time(time_str)
        if not parsed:
            return json.dumps({
                "success": False,
                "error": f"Could not parse time: '{time_str}'. Try '7:30 AM' or '14:00'."
            })
        target_hour, target_minute = parsed
    else:
        return json.dumps({
            "success": False,
            "error": "Please specify a time (e.g., '7:30 AM')."
        })

    entry = manager.create_alarm(target_hour, target_minute, name, repeat)

    trigger_dt = datetime.datetime.fromtimestamp(entry.trigger_at)

    return json.dumps({
        "success": True,
        "message": f"Alarm set for {trigger_dt.strftime('%I:%M %p')} ({entry.time_remaining_str()})",
        "timer": entry.to_dict()
    })


def set_reminder(message: str, when: str = None, delay: str = None) -> str:
    """
    Set a reminder with a message.

    Args:
        message: Reminder message
        when: Time string like "3:00 PM", or "in 30 minutes"
        delay: Duration string like "30 minutes"

    Returns:
        JSON result
    """
    manager = get_timer_manager()

    if not message:
        return json.dumps({
            "success": False,
            "error": "Please provide a reminder message."
        })

    # Parse when/delay
    if delay:
        delay_secs = parse_duration(delay)
        if delay_secs:
            entry = manager.create_reminder(message, delay_seconds=delay_secs)
        else:
            return json.dumps({
                "success": False,
                "error": f"Could not parse delay: '{delay}'"
            })
    elif when:
        # Check if it's a duration ("in X minutes")
        if when.lower().startswith("in "):
            delay_secs = parse_duration(when[3:])
            if delay_secs:
                entry = manager.create_reminder(message, delay_seconds=delay_secs)
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Could not parse time: '{when}'"
                })
        else:
            # Try as time
            parsed = parse_time(when)
            if parsed:
                entry = manager.create_reminder(message, hour=parsed[0], minute=parsed[1])
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Could not parse time: '{when}'. Try '3:00 PM' or 'in 30 minutes'."
                })
    else:
        # Default: 1 hour from now
        entry = manager.create_reminder(message, delay_seconds=3600)

    trigger_dt = datetime.datetime.fromtimestamp(entry.trigger_at)

    return json.dumps({
        "success": True,
        "message": f"Reminder set for {trigger_dt.strftime('%I:%M %p')}: {message}",
        "timer": entry.to_dict()
    })


def cancel_timer_cmd(timer_id: str = None, name: str = None) -> str:
    """
    Cancel a timer, alarm, or reminder.

    Args:
        timer_id: Timer ID to cancel
        name: Name pattern to match

    Returns:
        JSON result
    """
    manager = get_timer_manager()

    if timer_id:
        if manager.cancel_timer(timer_id):
            return json.dumps({
                "success": True,
                "message": f"Cancelled timer {timer_id}"
            })
        else:
            return json.dumps({
                "success": False,
                "error": f"Timer not found: {timer_id}"
            })
    elif name:
        count = manager.cancel_by_name(name)
        if count > 0:
            return json.dumps({
                "success": True,
                "message": f"Cancelled {count} timer(s) matching '{name}'"
            })
        else:
            return json.dumps({
                "success": False,
                "error": f"No timers found matching '{name}'"
            })
    else:
        return json.dumps({
            "success": False,
            "error": "Please specify a timer ID or name to cancel."
        })


def list_timers_cmd(timer_type: str = None) -> str:
    """
    List active timers.

    Args:
        timer_type: "timer", "alarm", "reminder", or None for all

    Returns:
        JSON result
    """
    manager = get_timer_manager()

    type_enum = None
    if timer_type:
        try:
            type_enum = TimerType(timer_type.lower())
        except ValueError:
            pass

    timers = manager.list_timers(type_enum)

    return json.dumps({
        "success": True,
        "count": len(timers),
        "timers": [t.to_dict() for t in timers],
        "formatted": format_timer_list(timers)
    })


def execute_timer_command(action: str, params: Dict[str, Any] = None) -> str:
    """
    Execute a timer-related command.

    Args:
        action: The action to perform
        params: Parameters for the action

    Returns:
        JSON result
    """
    if params is None:
        params = {}

    action_lower = action.lower().strip()

    # Set timer
    if action_lower in ['set_timer', 'timer', 'countdown']:
        return set_timer(
            duration=params.get('duration'),
            seconds=params.get('seconds'),
            name=params.get('name')
        )

    # Set alarm
    elif action_lower in ['set_alarm', 'alarm', 'wake']:
        return set_alarm(
            time_str=params.get('time'),
            hour=params.get('hour'),
            minute=params.get('minute'),
            name=params.get('name'),
            repeat=params.get('repeat')
        )

    # Set reminder
    elif action_lower in ['set_reminder', 'reminder', 'remind', 'remind_me']:
        return set_reminder(
            message=params.get('message', ''),
            when=params.get('when'),
            delay=params.get('delay')
        )

    # Cancel
    elif action_lower in ['cancel', 'cancel_timer', 'stop', 'delete']:
        return cancel_timer_cmd(
            timer_id=params.get('id'),
            name=params.get('name')
        )

    # List
    elif action_lower in ['list', 'list_timers', 'show', 'show_timers']:
        return list_timers_cmd(params.get('type'))

    # Clear all
    elif action_lower in ['clear', 'clear_all']:
        manager = get_timer_manager()
        type_enum = None
        if params.get('type'):
            try:
                type_enum = TimerType(params['type'].lower())
            except ValueError:
                pass
        count = manager.clear_all(type_enum)
        return json.dumps({
            "success": True,
            "message": f"Cleared {count} timer(s)"
        })

    else:
        return json.dumps({
            "success": False,
            "error": f"Unknown timer action: {action}",
            "available_actions": [
                "set_timer", "set_alarm", "set_reminder",
                "cancel", "list", "clear"
            ]
        })


__all__ = [
    'TimerManager',
    'TimerEntry',
    'TimerType',
    'get_timer_manager',
    'set_timer',
    'set_alarm',
    'set_reminder',
    'cancel_timer_cmd',
    'list_timers_cmd',
    'execute_timer_command',
    'parse_duration',
    'parse_time',
]
