"""
Blue Robot Automation and Routines Tool
========================================
Create and manage automation routines by chaining multiple actions together.

Features:
- Create custom routines (e.g., "Good morning", "Bedtime")
- Chain multiple tool actions in sequence
- Conditional execution based on time, weather, etc.
- Scheduled routines
- Voice-activated routines
- Share and import routines
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

# ================================================================================
# CONFIGURATION
# ================================================================================

AUTOMATION_DB = os.environ.get("BLUE_AUTOMATION_DB", "data/automation.db")


class ActionType(Enum):
    """Types of actions that can be automated."""
    MUSIC = "music"  # Play music
    LIGHTS = "lights"  # Control lights
    NOTIFICATION = "notification"  # Send notification
    TIMER = "timer"  # Set timer/alarm
    WEATHER = "weather"  # Get weather
    EMAIL = "email"  # Read/send email
    NOTE = "note"  # Create note
    TASK = "task"  # Create task
    SYSTEM = "system"  # System commands
    WAIT = "wait"  # Pause between actions
    CALENDAR = "calendar"  # Calendar operations


class TriggerType(Enum):
    """Types of triggers for automation."""
    MANUAL = "manual"  # User-initiated
    SCHEDULED = "scheduled"  # Time-based
    VOICE = "voice"  # Voice command
    WEATHER = "weather"  # Weather condition
    LOCATION = "location"  # Location-based
    EVENT = "event"  # Calendar event


class ConditionType(Enum):
    """Types of conditions for conditional execution."""
    TIME = "time"  # Time of day
    WEATHER = "weather"  # Weather condition
    DAY = "day"  # Day of week
    ALWAYS = "always"  # Always execute


@dataclass
class Action:
    """Represents a single action in a routine."""
    action_type: ActionType
    command: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_type": self.action_type.value,
            "command": self.command,
            "parameters": self.parameters,
            "condition": self.condition,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Action:
        """Create Action from dictionary."""
        return Action(
            action_type=ActionType(data["action_type"]),
            command=data["command"],
            parameters=data.get("parameters", {}),
            condition=data.get("condition"),
        )


@dataclass
class Routine:
    """Represents an automation routine."""
    id: str
    name: str
    description: str
    actions: List[Action]
    trigger: TriggerType
    trigger_data: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    created_at: float = field(default_factory=lambda: datetime.datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.datetime.now().timestamp())
    last_run: Optional[float] = None
    run_count: int = 0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "actions": [action.to_dict() for action in self.actions],
            "trigger": self.trigger.value,
            "trigger_data": self.trigger_data,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_run": self.last_run,
            "run_count": self.run_count,
            "tags": self.tags,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Routine:
        """Create Routine from dictionary."""
        return Routine(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            actions=[Action.from_dict(a) for a in data["actions"]],
            trigger=TriggerType(data["trigger"]),
            trigger_data=data.get("trigger_data", {}),
            enabled=data.get("enabled", True),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            last_run=data.get("last_run"),
            run_count=data.get("run_count", 0),
            tags=data.get("tags", []),
        )


# ================================================================================
# AUTOMATION MANAGER
# ================================================================================

class AutomationManager:
    """Manages automation routines with persistent storage."""

    def __init__(self, db_path: str = AUTOMATION_DB):
        self.db_path = db_path
        self._ensure_db()
        self._action_handlers: Dict[ActionType, Callable] = {}

    def _ensure_db(self):
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS routines (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                actions TEXT NOT NULL,
                trigger TEXT NOT NULL,
                trigger_data TEXT,
                enabled INTEGER,
                created_at REAL,
                updated_at REAL,
                last_run REAL,
                run_count INTEGER,
                tags TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS routine_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                routine_id TEXT,
                executed_at REAL,
                success INTEGER,
                duration_ms INTEGER,
                error TEXT,
                FOREIGN KEY (routine_id) REFERENCES routines (id)
            )
        """)

        conn.commit()
        conn.close()

    def register_action_handler(self, action_type: ActionType, handler: Callable):
        """Register a handler function for an action type."""
        self._action_handlers[action_type] = handler

    def create_routine(
        self,
        name: str,
        description: str,
        actions: List[Action],
        trigger: TriggerType = TriggerType.MANUAL,
        trigger_data: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Routine:
        """Create a new routine."""
        routine = Routine(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            actions=actions,
            trigger=trigger,
            trigger_data=trigger_data or {},
            tags=tags or [],
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO routines VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            routine.id, routine.name, routine.description,
            json.dumps([a.to_dict() for a in routine.actions]),
            routine.trigger.value, json.dumps(routine.trigger_data),
            1 if routine.enabled else 0,
            routine.created_at, routine.updated_at, routine.last_run,
            routine.run_count, json.dumps(routine.tags)
        ))

        conn.commit()
        conn.close()

        return routine

    def get_routine(self, routine_id: str) -> Optional[Routine]:
        """Get a routine by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM routines WHERE id = ?", (routine_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_routine(row)

    def list_routines(
        self,
        enabled_only: bool = False,
        trigger: Optional[TriggerType] = None
    ) -> List[Routine]:
        """List all routines."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM routines WHERE 1=1"
        params = []

        if enabled_only:
            query += " AND enabled = 1"

        if trigger:
            query += " AND trigger = ?"
            params.append(trigger.value)

        query += " ORDER BY name"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_routine(row) for row in rows]

    def update_routine(self, routine_id: str, **updates) -> bool:
        """Update an existing routine."""
        routine = self.get_routine(routine_id)
        if not routine:
            return False

        # Update fields
        for key, value in updates.items():
            if hasattr(routine, key):
                setattr(routine, key, value)

        routine.updated_at = datetime.datetime.now().timestamp()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE routines SET
                name = ?, description = ?, actions = ?, trigger = ?,
                trigger_data = ?, enabled = ?, updated_at = ?, tags = ?
            WHERE id = ?
        """, (
            routine.name, routine.description,
            json.dumps([a.to_dict() for a in routine.actions]),
            routine.trigger.value, json.dumps(routine.trigger_data),
            1 if routine.enabled else 0, routine.updated_at,
            json.dumps(routine.tags), routine.id
        ))

        conn.commit()
        conn.close()

        return True

    def delete_routine(self, routine_id: str) -> bool:
        """Delete a routine."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM routines WHERE id = ?", (routine_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    def execute_routine(self, routine_id: str) -> Dict[str, Any]:
        """Execute a routine."""
        routine = self.get_routine(routine_id)
        if not routine:
            return {
                "success": False,
                "error": "Routine not found"
            }

        if not routine.enabled:
            return {
                "success": False,
                "error": "Routine is disabled"
            }

        start_time = time.time()
        results = []
        success = True
        error_msg = None

        try:
            for i, action in enumerate(routine.actions):
                # Check condition if present
                if action.condition and not self._check_condition(action.condition):
                    results.append({
                        "action": i + 1,
                        "skipped": True,
                        "reason": "Condition not met"
                    })
                    continue

                # Execute action
                handler = self._action_handlers.get(action.action_type)
                if not handler:
                    results.append({
                        "action": i + 1,
                        "success": False,
                        "error": f"No handler for action type: {action.action_type.value}"
                    })
                    continue

                try:
                    result = handler(action.command, **action.parameters)
                    results.append({
                        "action": i + 1,
                        "success": True,
                        "result": result
                    })
                except Exception as e:
                    results.append({
                        "action": i + 1,
                        "success": False,
                        "error": str(e)
                    })
                    success = False
                    error_msg = str(e)
                    break

        except Exception as e:
            success = False
            error_msg = str(e)

        duration_ms = int((time.time() - start_time) * 1000)

        # Update routine stats
        routine.last_run = time.time()
        routine.run_count += 1
        self._update_routine_stats(routine)

        # Log execution
        self._log_execution(routine.id, success, duration_ms, error_msg)

        return {
            "success": success,
            "routine_id": routine.id,
            "routine_name": routine.name,
            "actions_executed": len(results),
            "duration_ms": duration_ms,
            "results": results,
            "error": error_msg,
        }

    def _check_condition(self, condition: Dict[str, Any]) -> bool:
        """Check if a condition is met."""
        condition_type = condition.get("type", "always")

        if condition_type == "always":
            return True

        if condition_type == "time":
            # Check time range
            now = datetime.datetime.now()
            start_hour = condition.get("start_hour", 0)
            end_hour = condition.get("end_hour", 23)
            return start_hour <= now.hour <= end_hour

        if condition_type == "day":
            # Check day of week (0=Monday, 6=Sunday)
            now = datetime.datetime.now()
            allowed_days = condition.get("days", [0, 1, 2, 3, 4, 5, 6])
            return now.weekday() in allowed_days

        return True

    def _update_routine_stats(self, routine: Routine):
        """Update routine statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE routines SET last_run = ?, run_count = ? WHERE id = ?
        """, (routine.last_run, routine.run_count, routine.id))

        conn.commit()
        conn.close()

    def _log_execution(
        self,
        routine_id: str,
        success: bool,
        duration_ms: int,
        error: Optional[str]
    ):
        """Log routine execution."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO routine_executions (routine_id, executed_at, success, duration_ms, error)
            VALUES (?, ?, ?, ?, ?)
        """, (routine_id, time.time(), 1 if success else 0, duration_ms, error))

        conn.commit()
        conn.close()

    def _row_to_routine(self, row: tuple) -> Routine:
        """Convert database row to Routine."""
        actions_data = json.loads(row[3])
        trigger_data = json.loads(row[5]) if row[5] else {}
        tags = json.loads(row[11]) if row[11] else []

        return Routine(
            id=row[0],
            name=row[1],
            description=row[2] or "",
            actions=[Action.from_dict(a) for a in actions_data],
            trigger=TriggerType(row[4]),
            trigger_data=trigger_data,
            enabled=bool(row[6]),
            created_at=row[7],
            updated_at=row[8],
            last_run=row[9],
            run_count=row[10],
            tags=tags,
        )


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_automation_manager: Optional[AutomationManager] = None


def get_automation_manager() -> AutomationManager:
    """Get the global automation manager instance."""
    global _automation_manager
    if _automation_manager is None:
        _automation_manager = AutomationManager()
    return _automation_manager


# ================================================================================
# PREDEFINED ROUTINES
# ================================================================================

PREDEFINED_ROUTINES = {
    "good_morning": {
        "name": "Good Morning",
        "description": "Start your day with weather, news, and music",
        "actions": [
            Action(ActionType.WEATHER, "current", {"location": "auto"}),
            Action(ActionType.LIGHTS, "control", {"preset": "energize"}),
            Action(ActionType.MUSIC, "play", {"mood": "upbeat"}),
            Action(ActionType.CALENDAR, "list", {"days_ahead": 1}),
        ]
    },
    "bedtime": {
        "name": "Bedtime",
        "description": "Wind down for the night",
        "actions": [
            Action(ActionType.LIGHTS, "control", {"preset": "sunset"}),
            Action(ActionType.MUSIC, "play", {"mood": "relaxing"}),
            Action(ActionType.TIMER, "set", {"duration": "30 minutes", "name": "Sleep timer"}),
            Action(ActionType.NOTIFICATION, "send", {"message": "Time to sleep!"}),
        ]
    },
    "focus_mode": {
        "name": "Focus Mode",
        "description": "Get into deep work mode",
        "actions": [
            Action(ActionType.NOTIFICATION, "send", {"message": "Entering focus mode"}),
            Action(ActionType.MUSIC, "play", {"mood": "focus"}),
            Action(ActionType.LIGHTS, "control", {"preset": "concentrate"}),
            Action(ActionType.TIMER, "set", {"duration": "25 minutes", "name": "Focus session"}),
        ]
    },
    "party_mode": {
        "name": "Party Mode",
        "description": "Set the mood for a party",
        "actions": [
            Action(ActionType.LIGHTS, "control", {"preset": "party"}),
            Action(ActionType.MUSIC, "play", {"mood": "party"}),
            Action(ActionType.NOTIFICATION, "send", {"message": "Party time!"}),
        ]
    },
}


# ================================================================================
# COMMAND FUNCTIONS
# ================================================================================

def create_routine_cmd(
    name: str,
    description: str,
    actions: List[Dict[str, Any]],
    trigger: str = "manual",
) -> str:
    """Create a new routine."""
    try:
        manager = get_automation_manager()

        # Convert action dicts to Action objects
        action_objects = []
        for action_data in actions:
            action_objects.append(Action.from_dict(action_data))

        # Parse trigger
        try:
            trigger_type = TriggerType(trigger.lower())
        except ValueError:
            trigger_type = TriggerType.MANUAL

        routine = manager.create_routine(name, description, action_objects, trigger_type)

        return json.dumps({
            "success": True,
            "routine_id": routine.id,
            "name": routine.name,
            "actions_count": len(routine.actions),
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to create routine: {str(e)}"
        })


def list_routines_cmd(enabled_only: bool = False) -> str:
    """List all routines."""
    try:
        manager = get_automation_manager()
        routines = manager.list_routines(enabled_only=enabled_only)

        return json.dumps({
            "success": True,
            "count": len(routines),
            "routines": [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "actions_count": len(r.actions),
                    "trigger": r.trigger.value,
                    "enabled": r.enabled,
                    "last_run": r.last_run,
                    "run_count": r.run_count,
                }
                for r in routines
            ]
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to list routines: {str(e)}"
        })


def execute_routine_cmd(routine_id: str) -> str:
    """Execute a routine."""
    try:
        manager = get_automation_manager()
        result = manager.execute_routine(routine_id)
        return json.dumps(result)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to execute routine: {str(e)}"
        })


def delete_routine_cmd(routine_id: str) -> str:
    """Delete a routine."""
    try:
        manager = get_automation_manager()
        success = manager.delete_routine(routine_id)

        return json.dumps({
            "success": success,
            "message": "Routine deleted" if success else "Routine not found"
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to delete routine: {str(e)}"
        })


def install_predefined_routine(routine_key: str) -> str:
    """Install a predefined routine."""
    try:
        if routine_key not in PREDEFINED_ROUTINES:
            return json.dumps({
                "success": False,
                "error": f"Unknown predefined routine: {routine_key}"
            })

        manager = get_automation_manager()
        template = PREDEFINED_ROUTINES[routine_key]

        routine = manager.create_routine(
            name=template["name"],
            description=template["description"],
            actions=template["actions"],
            trigger=TriggerType.MANUAL,
        )

        return json.dumps({
            "success": True,
            "routine_id": routine.id,
            "name": routine.name,
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to install routine: {str(e)}"
        })


def execute_automation_command(command: str, **params) -> str:
    """Execute an automation command."""
    commands = {
        "create": create_routine_cmd,
        "list": list_routines_cmd,
        "execute": execute_routine_cmd,
        "delete": delete_routine_cmd,
        "install": install_predefined_routine,
    }

    handler = commands.get(command)
    if not handler:
        return json.dumps({
            "success": False,
            "error": f"Unknown automation command: {command}"
        })

    return handler(**params)
