"""
Blue Robot Calendar and Events Tool
====================================
Manage appointments, events, and schedules with calendar integration.

Features:
- Create, edit, delete events
- Recurring events (daily, weekly, monthly)
- Event reminders and notifications
- Calendar views (day, week, month)
- Event search and filtering
- Conflict detection
- Import/export calendar data
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sqlite3
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ================================================================================
# CONFIGURATION
# ================================================================================

CALENDAR_DB = os.environ.get("BLUE_CALENDAR_DB", "data/calendar.db")


class EventType(Enum):
    APPOINTMENT = "appointment"
    MEETING = "meeting"
    REMINDER = "reminder"
    BIRTHDAY = "birthday"
    HOLIDAY = "holiday"
    TASK = "task"
    OTHER = "other"


class RecurrenceType(Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


@dataclass
class CalendarEvent:
    """Represents a calendar event."""
    id: str
    title: str
    description: str
    start_time: float
    end_time: float
    location: Optional[str] = None
    event_type: EventType = EventType.OTHER
    recurrence: RecurrenceType = RecurrenceType.NONE
    reminder_minutes: int = 15
    all_day: bool = False
    created_at: float = field(default_factory=lambda: datetime.datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.datetime.now().timestamp())
    attendees: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    color: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "location": self.location,
            "event_type": self.event_type.value,
            "recurrence": self.recurrence.value,
            "reminder_minutes": self.reminder_minutes,
            "all_day": self.all_day,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "attendees": self.attendees,
            "tags": self.tags,
            "color": self.color,
        }

    def overlaps_with(self, other: CalendarEvent) -> bool:
        """Check if this event overlaps with another."""
        return (self.start_time < other.end_time and
                self.end_time > other.start_time)

    def format_time_range(self) -> str:
        """Format the event time range for display."""
        start_dt = datetime.datetime.fromtimestamp(self.start_time)
        end_dt = datetime.datetime.fromtimestamp(self.end_time)

        if self.all_day:
            return start_dt.strftime("%B %d, %Y (All Day)")

        if start_dt.date() == end_dt.date():
            return f"{start_dt.strftime('%B %d, %Y %I:%M %p')} - {end_dt.strftime('%I:%M %p')}"
        else:
            return f"{start_dt.strftime('%B %d, %Y %I:%M %p')} - {end_dt.strftime('%B %d, %Y %I:%M %p')}"


# ================================================================================
# CALENDAR MANAGER
# ================================================================================

class CalendarManager:
    """Manages calendar events with persistent storage."""

    def __init__(self, db_path: str = CALENDAR_DB):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                location TEXT,
                event_type TEXT,
                recurrence TEXT,
                reminder_minutes INTEGER,
                all_day INTEGER,
                created_at REAL,
                updated_at REAL,
                attendees TEXT,
                tags TEXT,
                color TEXT
            )
        """)

        conn.commit()
        conn.close()

    def create_event(
        self,
        title: str,
        start_time: float,
        end_time: float,
        description: str = "",
        location: Optional[str] = None,
        event_type: EventType = EventType.OTHER,
        recurrence: RecurrenceType = RecurrenceType.NONE,
        reminder_minutes: int = 15,
        all_day: bool = False,
        attendees: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        color: Optional[str] = None,
    ) -> CalendarEvent:
        """Create a new calendar event."""
        event = CalendarEvent(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            location=location,
            event_type=event_type,
            recurrence=recurrence,
            reminder_minutes=reminder_minutes,
            all_day=all_day,
            attendees=attendees or [],
            tags=tags or [],
            color=color,
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.id, event.title, event.description,
            event.start_time, event.end_time, event.location,
            event.event_type.value, event.recurrence.value,
            event.reminder_minutes, 1 if event.all_day else 0,
            event.created_at, event.updated_at,
            json.dumps(event.attendees), json.dumps(event.tags), event.color
        ))

        conn.commit()
        conn.close()

        return event

    def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """Get an event by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_event(row)

    def update_event(self, event_id: str, **updates) -> bool:
        """Update an existing event."""
        event = self.get_event(event_id)
        if not event:
            return False

        # Update fields
        for key, value in updates.items():
            if hasattr(event, key):
                setattr(event, key, value)

        event.updated_at = datetime.datetime.now().timestamp()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE events SET
                title = ?, description = ?, start_time = ?, end_time = ?,
                location = ?, event_type = ?, recurrence = ?, reminder_minutes = ?,
                all_day = ?, updated_at = ?, attendees = ?, tags = ?, color = ?
            WHERE id = ?
        """, (
            event.title, event.description, event.start_time, event.end_time,
            event.location, event.event_type.value, event.recurrence.value,
            event.reminder_minutes, 1 if event.all_day else 0, event.updated_at,
            json.dumps(event.attendees), json.dumps(event.tags), event.color,
            event.id
        ))

        conn.commit()
        conn.close()

        return True

    def delete_event(self, event_id: str) -> bool:
        """Delete an event."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    def get_events_in_range(
        self,
        start_time: float,
        end_time: float,
        event_type: Optional[EventType] = None
    ) -> List[CalendarEvent]:
        """Get all events within a time range."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if event_type:
            cursor.execute("""
                SELECT * FROM events
                WHERE start_time < ? AND end_time > ? AND event_type = ?
                ORDER BY start_time
            """, (end_time, start_time, event_type.value))
        else:
            cursor.execute("""
                SELECT * FROM events
                WHERE start_time < ? AND end_time > ?
                ORDER BY start_time
            """, (end_time, start_time))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_event(row) for row in rows]

    def search_events(self, query: str) -> List[CalendarEvent]:
        """Search events by title, description, or location."""
        query_lower = query.lower()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM events
            WHERE LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(location) LIKE ?
            ORDER BY start_time
        """, (f"%{query_lower}%", f"%{query_lower}%", f"%{query_lower}%"))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_event(row) for row in rows]

    def get_upcoming_events(self, count: int = 10) -> List[CalendarEvent]:
        """Get upcoming events."""
        now = datetime.datetime.now().timestamp()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM events
            WHERE start_time > ?
            ORDER BY start_time
            LIMIT ?
        """, (now, count))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_event(row) for row in rows]

    def check_conflicts(self, event: CalendarEvent) -> List[CalendarEvent]:
        """Check for scheduling conflicts with an event."""
        events = self.get_events_in_range(event.start_time, event.end_time)
        return [e for e in events if e.id != event.id and e.overlaps_with(event)]

    def _row_to_event(self, row: tuple) -> CalendarEvent:
        """Convert database row to CalendarEvent."""
        return CalendarEvent(
            id=row[0],
            title=row[1],
            description=row[2] or "",
            start_time=row[3],
            end_time=row[4],
            location=row[5],
            event_type=EventType(row[6]),
            recurrence=RecurrenceType(row[7]),
            reminder_minutes=row[8],
            all_day=bool(row[9]),
            created_at=row[10],
            updated_at=row[11],
            attendees=json.loads(row[12]) if row[12] else [],
            tags=json.loads(row[13]) if row[13] else [],
            color=row[14],
        )


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_calendar_manager: Optional[CalendarManager] = None


def get_calendar_manager() -> CalendarManager:
    """Get the global calendar manager instance."""
    global _calendar_manager
    if _calendar_manager is None:
        _calendar_manager = CalendarManager()
    return _calendar_manager


# ================================================================================
# COMMAND FUNCTIONS
# ================================================================================

def create_event_cmd(
    title: str,
    start_time: str,
    duration_minutes: int = 60,
    description: str = "",
    location: Optional[str] = None,
    event_type: str = "other",
    all_day: bool = False,
) -> str:
    """
    Create a new calendar event.

    Args:
        title: Event title
        start_time: Start time (ISO format or natural language)
        duration_minutes: Event duration in minutes
        description: Event description
        location: Event location
        event_type: Type of event
        all_day: Whether this is an all-day event

    Returns:
        JSON result
    """
    try:
        manager = get_calendar_manager()

        # Parse start time
        start_dt = parse_datetime(start_time)
        if not start_dt:
            return json.dumps({
                "success": False,
                "error": f"Could not parse start time: {start_time}"
            })

        start_ts = start_dt.timestamp()
        end_ts = start_ts + (duration_minutes * 60)

        # Parse event type
        try:
            evt_type = EventType(event_type.lower())
        except ValueError:
            evt_type = EventType.OTHER

        # Create event
        event = manager.create_event(
            title=title,
            start_time=start_ts,
            end_time=end_ts,
            description=description,
            location=location,
            event_type=evt_type,
            all_day=all_day,
        )

        # Check for conflicts
        conflicts = manager.check_conflicts(event)

        return json.dumps({
            "success": True,
            "event_id": event.id,
            "title": event.title,
            "time": event.format_time_range(),
            "conflicts": len(conflicts),
            "conflict_details": [
                {"title": c.title, "time": c.format_time_range()}
                for c in conflicts
            ] if conflicts else []
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to create event: {str(e)}"
        })


def list_events_cmd(
    days_ahead: int = 7,
    event_type: Optional[str] = None
) -> str:
    """
    List upcoming events.

    Args:
        days_ahead: Number of days to look ahead
        event_type: Filter by event type (optional)

    Returns:
        JSON result with events
    """
    try:
        manager = get_calendar_manager()

        # Get time range
        now = datetime.datetime.now()
        end = now + datetime.timedelta(days=days_ahead)

        # Parse event type filter
        evt_filter = None
        if event_type:
            try:
                evt_filter = EventType(event_type.lower())
            except ValueError:
                pass

        # Get events
        events = manager.get_events_in_range(
            now.timestamp(),
            end.timestamp(),
            evt_filter
        )

        return json.dumps({
            "success": True,
            "count": len(events),
            "events": [
                {
                    "id": e.id,
                    "title": e.title,
                    "description": e.description,
                    "time": e.format_time_range(),
                    "location": e.location,
                    "type": e.event_type.value,
                    "all_day": e.all_day,
                }
                for e in events
            ]
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to list events: {str(e)}"
        })


def search_events_cmd(query: str) -> str:
    """
    Search for events.

    Args:
        query: Search query

    Returns:
        JSON result with matching events
    """
    try:
        manager = get_calendar_manager()
        events = manager.search_events(query)

        return json.dumps({
            "success": True,
            "count": len(events),
            "events": [
                {
                    "id": e.id,
                    "title": e.title,
                    "description": e.description,
                    "time": e.format_time_range(),
                    "location": e.location,
                }
                for e in events
            ]
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to search events: {str(e)}"
        })


def delete_event_cmd(event_id: str) -> str:
    """
    Delete a calendar event.

    Args:
        event_id: Event ID to delete

    Returns:
        JSON result
    """
    try:
        manager = get_calendar_manager()

        # Get event details before deletion
        event = manager.get_event(event_id)
        if not event:
            return json.dumps({
                "success": False,
                "error": "Event not found"
            })

        # Delete
        success = manager.delete_event(event_id)

        return json.dumps({
            "success": success,
            "deleted_title": event.title if success else None
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to delete event: {str(e)}"
        })


# ================================================================================
# HELPER FUNCTIONS
# ================================================================================

def parse_datetime(time_str: str) -> Optional[datetime.datetime]:
    """
    Parse a datetime string in various formats.

    Supports:
    - ISO format: "2025-12-10T14:30:00"
    - Natural language: "tomorrow at 3pm", "next friday 2:30pm"
    """
    time_str = time_str.strip().lower()
    now = datetime.datetime.now()

    # Try ISO format first
    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]:
        try:
            return datetime.datetime.strptime(time_str, fmt)
        except ValueError:
            continue

    # Natural language parsing
    # Today/Tomorrow
    if "today" in time_str:
        base_date = now.date()
    elif "tomorrow" in time_str:
        base_date = (now + datetime.timedelta(days=1)).date()
    elif "next week" in time_str:
        base_date = (now + datetime.timedelta(days=7)).date()
    else:
        # Try to parse weekday
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for i, day in enumerate(weekdays):
            if day in time_str:
                days_ahead = (i - now.weekday()) % 7
                if days_ahead == 0 and "next" in time_str:
                    days_ahead = 7
                base_date = (now + datetime.timedelta(days=days_ahead)).date()
                break
        else:
            # Default to today
            base_date = now.date()

    # Parse time
    time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(am|pm)?', time_str)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        period = time_match.group(3)

        if period == "pm" and hour < 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0

        return datetime.datetime.combine(base_date, datetime.time(hour, minute))

    # Default to start of day
    return datetime.datetime.combine(base_date, datetime.time(9, 0))


def execute_calendar_command(command: str, **params) -> str:
    """
    Execute a calendar command.

    Args:
        command: Command name
        **params: Command parameters

    Returns:
        JSON result
    """
    commands = {
        "create": create_event_cmd,
        "list": list_events_cmd,
        "search": search_events_cmd,
        "delete": delete_event_cmd,
    }

    handler = commands.get(command)
    if not handler:
        return json.dumps({
            "success": False,
            "error": f"Unknown calendar command: {command}"
        })

    return handler(**params)
