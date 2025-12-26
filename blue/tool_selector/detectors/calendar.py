"""Calendar and events intent detector."""

from typing import Dict, List, Optional
from .base import BaseDetector
from ..models import ToolIntent
from ..constants import ToolPriority


class CalendarDetector(BaseDetector):
    """Detects calendar and event-related intents."""

    def detect(self, message: str, msg_lower: str, context: Dict) -> List[ToolIntent]:
        intents = []

        create_event = self._detect_create_event(msg_lower)
        if create_event:
            intents.append(create_event)

        list_events = self._detect_list_events(msg_lower)
        if list_events:
            intents.append(list_events)

        return intents

    def _detect_create_event(self, msg_lower: str) -> Optional[ToolIntent]:
        strong_signals = [
            'create event', 'add event', 'schedule event', 'create appointment',
            'schedule meeting', 'add to calendar', 'create reminder'
        ]
        time_indicators = [
            'at', 'tomorrow', 'today', 'next week', 'on monday', 'on tuesday'
        ]

        confidence = 0.0
        reasons = []

        if any(s in msg_lower for s in strong_signals):
            confidence = 0.90
            reasons.append("explicit event creation")
        elif any(t in msg_lower for t in time_indicators):
            if any(v in msg_lower for v in ['schedule', 'meet', 'appointment']):
                confidence = 0.75
                reasons.append("time + schedule keyword")

        if confidence <= 0:
            return None

        return ToolIntent(
            tool_name='create_event',
            confidence=confidence,
            priority=ToolPriority.MEDIUM,
            reason=' | '.join(reasons),
            extracted_params={}
        )

    def _detect_list_events(self, msg_lower: str) -> Optional[ToolIntent]:
        strong_signals = [
            'show my calendar', 'list events', 'what\'s on my calendar',
            'my schedule', 'show schedule', 'upcoming events'
        ]

        confidence = 0.0
        reasons = []

        if any(s in msg_lower for s in strong_signals):
            confidence = 0.90
            reasons.append("explicit calendar query")

        if confidence <= 0:
            return None

        return ToolIntent(
            tool_name='list_events',
            confidence=confidence,
            priority=ToolPriority.MEDIUM,
            reason=' | '.join(reasons),
            extracted_params={}
        )
