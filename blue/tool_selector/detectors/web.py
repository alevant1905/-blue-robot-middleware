"""Web search and browsing intent detector."""

import re
from typing import Dict, List, Optional
from .base import BaseDetector
from ..models import ToolIntent
from ..constants import ToolPriority


class WebDetector(BaseDetector):
    """Detects web search and browsing intents."""

    def detect(self, message: str, msg_lower: str, context: Dict) -> List[ToolIntent]:
        intents = []

        search_intent = self._detect_search_intent(msg_lower)
        if search_intent:
            intents.append(search_intent)

        browse_intent = self._detect_browse_intent(msg_lower)
        if browse_intent:
            intents.append(browse_intent)

        return intents

    def _detect_search_intent(self, msg_lower: str) -> Optional[ToolIntent]:
        strong_signals = [
            'search the web', 'search online', 'google', 'search google',
            'look up online', 'search the internet', 'find on the web'
        ]
        medium_signals = ['search for', 'look up', 'find out about']
        temporal = ['latest', 'recent', 'current', 'today', 'this week']

        confidence = 0.0
        reasons = []

        if any(s in msg_lower for s in strong_signals):
            confidence = 0.95
            reasons.append("explicit web search")
        elif any(s in msg_lower for s in medium_signals):
            confidence = 0.75
            reasons.append("generic search")
        elif any(t in msg_lower for t in temporal):
            if any(topic in msg_lower for topic in ['news', 'price', 'score', 'weather']):
                confidence = 0.85
                reasons.append("temporal + news/price")

        # Reduce for document search
        doc_signals = ['my document', 'my file', 'my contract', 'my pdf']
        if any(s in msg_lower for s in doc_signals):
            confidence = max(0, confidence - 0.6)

        if confidence <= 0:
            return None

        return ToolIntent(
            tool_name='web_search',
            confidence=confidence,
            priority=ToolPriority.LOW,
            reason=' | '.join(reasons),
            extracted_params={'query': msg_lower}
        )

    def _detect_browse_intent(self, msg_lower: str) -> Optional[ToolIntent]:
        browse_verbs = ['browse', 'open', 'visit', 'go to', 'navigate to', 'load', 'fetch']

        has_email = bool(re.search(r'\b[\w.-]+@[\w.-]+\.\w+\b', msg_lower))
        has_url = bool(re.search(r'https?://|www\.', msg_lower)) or \
                  (bool(re.search(r'\.(com|org|net)\b', msg_lower)) and not has_email)
        has_verb = any(v in msg_lower for v in browse_verbs)

        confidence = 0.0
        reasons = []

        if has_url:
            if has_verb:
                confidence = 0.95
                reasons.append("URL + browse verb")
            else:
                confidence = 0.85
                reasons.append("URL detected")
        elif has_verb and 'website' in msg_lower:
            confidence = 0.75
            reasons.append("browse + website")

        if confidence <= 0:
            return None

        url_match = re.search(r'https?://\S+|www\.\S+|\b\w+\.(com|org|net)\b', msg_lower)
        url = url_match.group(0) if url_match else None

        return ToolIntent(
            tool_name='browse_website',
            confidence=confidence,
            priority=ToolPriority.MEDIUM,
            reason=' | '.join(reasons),
            extracted_params={'url': url, 'extract': 'text'}
        )
