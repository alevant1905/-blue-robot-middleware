"""
Simple detectors for straightforward intent patterns.

Includes: Automation, Contacts, Habits, Notes, Timers, System, Utilities, MediaLibrary, Locations
"""

from typing import Dict, List, Optional
from .base import BaseDetector
from ..models import ToolIntent
from ..constants import ToolPriority


class AutomationDetector(BaseDetector):
    """Detects automation and routine intents."""

    def detect(self, message: str, msg_lower: str, context: Dict) -> List[ToolIntent]:
        strong_signals = [
            'run routine', 'execute routine', 'run automation', 'good morning',
            'good night', 'start routine', 'trigger routine'
        ]

        if any(s in msg_lower for s in strong_signals):
            return [ToolIntent(
                tool_name='run_routine',
                confidence=0.90,
                priority=ToolPriority.HIGH,
                reason="automation/routine keywords",
                extracted_params={}
            )]
        return []


class ContactsDetector(BaseDetector):
    """Detects contact management intents."""

    def detect(self, message: str, msg_lower: str, context: Dict) -> List[ToolIntent]:
        list_signals = ['show contacts', 'list contacts', 'my contacts', 'all contacts']
        add_signals = ['add contact', 'create contact', 'new contact', 'save contact']

        if any(s in msg_lower for s in list_signals):
            return [ToolIntent(
                tool_name='list_contacts',
                confidence=0.90,
                priority=ToolPriority.MEDIUM,
                reason="list contacts keywords",
                extracted_params={}
            )]
        elif any(s in msg_lower for s in add_signals):
            return [ToolIntent(
                tool_name='add_contact',
                confidence=0.90,
                priority=ToolPriority.MEDIUM,
                reason="add contact keywords",
                extracted_params={}
            )]
        return []


class HabitsDetector(BaseDetector):
    """Detects habit tracking intents."""

    def detect(self, message: str, msg_lower: str, context: Dict) -> List[ToolIntent]:
        complete_signals = ['completed', 'finished', 'did my', 'done with']
        create_signals = ['track habit', 'create habit', 'new habit', 'start tracking']

        if any(s in msg_lower for s in complete_signals) and 'habit' in msg_lower:
            return [ToolIntent(
                tool_name='complete_habit',
                confidence=0.85,
                priority=ToolPriority.MEDIUM,
                reason="habit completion keywords",
                extracted_params={}
            )]
        elif any(s in msg_lower for s in create_signals):
            return [ToolIntent(
                tool_name='create_habit',
                confidence=0.90,
                priority=ToolPriority.MEDIUM,
                reason="habit creation keywords",
                extracted_params={}
            )]
        return []


class NotesDetector(BaseDetector):
    """Detects notes and tasks intents."""

    def detect(self, message: str, msg_lower: str, context: Dict) -> List[ToolIntent]:
        create_signals = ['create note', 'add note', 'make a note', 'save note', 'write note']
        task_signals = ['add task', 'create task', 'new task', 'add to do', 'add todo']
        list_signals = ['show notes', 'list notes', 'my notes', 'show tasks', 'list tasks']

        if any(s in msg_lower for s in create_signals):
            return [ToolIntent(
                tool_name='create_note',
                confidence=0.85,
                priority=ToolPriority.MEDIUM,
                reason="note creation keywords",
                extracted_params={}
            )]
        elif any(s in msg_lower for s in task_signals):
            return [ToolIntent(
                tool_name='create_task',
                confidence=0.85,
                priority=ToolPriority.MEDIUM,
                reason="task creation keywords",
                extracted_params={}
            )]
        elif any(s in msg_lower for s in list_signals):
            return [ToolIntent(
                tool_name='list_notes',
                confidence=0.85,
                priority=ToolPriority.MEDIUM,
                reason="list notes/tasks keywords",
                extracted_params={}
            )]
        return []


class TimersDetector(BaseDetector):
    """Detects timer and reminder intents."""

    def detect(self, message: str, msg_lower: str, context: Dict) -> List[ToolIntent]:
        timer_signals = ['set timer', 'start timer', 'timer for', 'countdown']
        reminder_signals = ['remind me', 'set reminder', 'reminder to', 'reminder for']

        if any(s in msg_lower for s in timer_signals):
            return [ToolIntent(
                tool_name='set_timer',
                confidence=0.90,
                priority=ToolPriority.HIGH,
                reason="timer keywords",
                extracted_params={}
            )]
        elif any(s in msg_lower for s in reminder_signals):
            return [ToolIntent(
                tool_name='set_reminder',
                confidence=0.90,
                priority=ToolPriority.HIGH,
                reason="reminder keywords",
                extracted_params={}
            )]
        return []


class SystemDetector(BaseDetector):
    """Detects system control intents."""

    def detect(self, message: str, msg_lower: str, context: Dict) -> List[ToolIntent]:
        clipboard_signals = ['copy', 'clipboard', 'paste']
        screenshot_signals = ['screenshot', 'screen capture', 'capture screen']
        volume_signals = ['volume up', 'volume down', 'mute', 'unmute']
        launch_signals = ['open', 'launch', 'start'] if any(app in msg_lower for app in ['chrome', 'firefox', 'notepad', 'calculator']) else []

        if any(s in msg_lower for s in screenshot_signals):
            return [ToolIntent(
                tool_name='take_screenshot',
                confidence=0.90,
                priority=ToolPriority.MEDIUM,
                reason="screenshot keywords",
                extracted_params={}
            )]
        elif any(s in msg_lower for s in clipboard_signals):
            return [ToolIntent(
                tool_name='clipboard_operation',
                confidence=0.75,
                priority=ToolPriority.LOW,
                reason="clipboard keywords",
                extracted_params={}
            )]
        elif launch_signals:
            return [ToolIntent(
                tool_name='launch_application',
                confidence=0.85,
                priority=ToolPriority.MEDIUM,
                reason="launch app keywords",
                extracted_params={}
            )]
        return []


class UtilitiesDetector(BaseDetector):
    """Detects utility operations."""

    def detect(self, message: str, msg_lower: str, context: Dict) -> List[ToolIntent]:
        calc_signals = ['calculate', 'math', 'compute', 'what is', 'how much is']
        date_signals = ['what day', 'what date', 'today\'s date', 'current date']

        if any(s in msg_lower for s in calc_signals) and any(op in msg_lower for op in ['+', '-', '*', '/', 'plus', 'minus', 'times', 'divided']):
            return [ToolIntent(
                tool_name='calculate',
                confidence=0.85,
                priority=ToolPriority.LOW,
                reason="calculation keywords",
                extracted_params={}
            )]
        elif any(s in msg_lower for s in date_signals):
            return [ToolIntent(
                tool_name='get_date_time',
                confidence=0.90,
                priority=ToolPriority.LOW,
                reason="date/time query",
                extracted_params={}
            )]
        return []


class MediaLibraryDetector(BaseDetector):
    """Detects media library (podcasts) intents."""

    def detect(self, message: str, msg_lower: str, context: Dict) -> List[ToolIntent]:
        podcast_signals = ['add podcast', 'subscribe to podcast', 'new podcast', 'podcast feed']
        list_signals = ['list podcasts', 'show podcasts', 'my podcasts']

        if any(s in msg_lower for s in podcast_signals):
            return [ToolIntent(
                tool_name='add_podcast',
                confidence=0.90,
                priority=ToolPriority.MEDIUM,
                reason="add podcast keywords",
                extracted_params={}
            )]
        elif any(s in msg_lower for s in list_signals):
            return [ToolIntent(
                tool_name='list_podcasts',
                confidence=0.90,
                priority=ToolPriority.MEDIUM,
                reason="list podcasts keywords",
                extracted_params={}
            )]
        return []


class LocationsDetector(BaseDetector):
    """Detects location management intents."""

    def detect(self, message: str, msg_lower: str, context: Dict) -> List[ToolIntent]:
        save_signals = ['save location', 'save this place', 'remember this location', 'add location']
        list_signals = ['my locations', 'saved locations', 'list locations']

        if any(s in msg_lower for s in save_signals):
            return [ToolIntent(
                tool_name='save_location',
                confidence=0.90,
                priority=ToolPriority.MEDIUM,
                reason="save location keywords",
                extracted_params={}
            )]
        elif any(s in msg_lower for s in list_signals):
            return [ToolIntent(
                tool_name='list_locations',
                confidence=0.90,
                priority=ToolPriority.MEDIUM,
                reason="list locations keywords",
                extracted_params={}
            )]
        return []
