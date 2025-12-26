"""
Music intent detector.

Detects:
- play_music: Play songs, artists, genres, playlists
- control_music: Pause, stop, skip, volume, etc.
- music_visualizer: Sync lights with music

ENHANCED v7: Better false positive filtering for non-music "play" contexts
"""

from typing import Dict, List, Optional

from .base import BaseDetector
from ..models import ToolIntent
from ..constants import ToolPriority
from ..utils import fuzzy_match
from ..data.music_data import (
    NON_MUSIC_PLAY_PHRASES,
    PLAY_SIGNALS,
    MUSIC_NOUNS,
    GENRES,
    ARTISTS,
    CONTROL_SIGNALS,
    VISUALIZER_SIGNALS,
    INFO_REQUEST_WORDS,
    NON_MUSIC_CONTEXT_WORDS,
)


class MusicDetector(BaseDetector):
    """Detects music playback and control intents."""

    def detect(
        self,
        message: str,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """Detect music-related intents."""
        intents = []

        # Early exit: non-music "play" contexts
        if self._is_non_music_context(msg_lower):
            return intents

        # Detect play music intent
        play_intent = self._detect_play_intent(msg_lower, context)
        if play_intent:
            intents.append(play_intent)

        # Detect control music intent
        control_intent = self._detect_control_intent(msg_lower, context)
        if control_intent:
            intents.append(control_intent)

        # Detect visualizer intent
        visualizer_intent = self._detect_visualizer_intent(msg_lower)
        if visualizer_intent:
            intents.append(visualizer_intent)

        return intents

    def _is_non_music_context(self, msg_lower: str) -> bool:
        """Check if message contains non-music 'play' context."""
        return any(phrase in msg_lower for phrase in NON_MUSIC_PLAY_PHRASES)

    def _detect_play_intent(
        self,
        msg_lower: str,
        context: Dict
    ) -> Optional[ToolIntent]:
        """Detect play music intent."""

        # Check for artists and genres
        has_artist = any(artist in msg_lower for artist in ARTISTS)
        has_genre = any(genre in msg_lower for genre in GENRES)

        # Fuzzy match for artist names (handles typos)
        matched_artist = None
        if not has_artist and any(signal in msg_lower for signal in PLAY_SIGNALS):
            matched_artist = self._fuzzy_match_artist(msg_lower)
            if matched_artist:
                has_artist = True

        # Detect play signals and music nouns
        has_play = any(signal in msg_lower for signal in PLAY_SIGNALS)
        has_music = any(noun in msg_lower for noun in MUSIC_NOUNS)

        # Calculate confidence
        confidence, reasons = self._calculate_play_confidence(
            msg_lower, has_play, has_artist, has_genre, has_music,
            matched_artist, context
        )

        if confidence <= 0:
            return None

        # Extract query
        query = self._extract_music_query(msg_lower, matched_artist)

        return ToolIntent(
            tool_name='play_music',
            confidence=confidence,
            priority=ToolPriority.HIGH,
            reason=' | '.join(reasons),
            extracted_params={'query': query if query else msg_lower}
        )

    def _fuzzy_match_artist(self, msg_lower: str) -> Optional[str]:
        """Fuzzy match artist names to handle typos."""
        # Remove play signals
        msg_without_signals = msg_lower
        for signal in PLAY_SIGNALS:
            msg_without_signals = msg_without_signals.replace(signal, ' ')

        words = msg_without_signals.split()
        words = [w for w in words if len(w) > 2]  # Skip short words

        # Try single words and pairs
        for i in range(len(words)):
            for length in [1, 2, 3]:
                if i + length <= len(words):
                    phrase = ' '.join(words[i:i+length])
                    if len(phrase) >= 4:  # At least 4 characters
                        match = fuzzy_match(phrase, ARTISTS, threshold=0.85)
                        if match:
                            return match
        return None

    def _calculate_play_confidence(
        self,
        msg_lower: str,
        has_play: bool,
        has_artist: bool,
        has_genre: bool,
        has_music: bool,
        matched_artist: Optional[str],
        context: Dict
    ) -> tuple[float, List[str]]:
        """Calculate confidence score for play intent."""
        confidence = 0.0
        reasons = []

        # Direct "play [artist]" or "play [genre]"
        if has_play and (has_artist or has_genre):
            confidence = 0.98
            if matched_artist:
                reasons.append(f"play + fuzzy matched artist: {matched_artist}")
            else:
                reasons.append("play + artist/genre detected")

        # "play music"
        elif has_play and has_music:
            # Check if it's about searching for info
            if any(word in msg_lower for word in INFO_REQUEST_WORDS):
                confidence = 0.2
                reasons.append("play+music but info request detected")
            elif any(word in msg_lower for word in NON_MUSIC_CONTEXT_WORDS):
                confidence = 0.25
                reasons.append("play detected but non-music context")
            else:
                confidence = 0.95
                reasons.append("clear play + music intent")

        # "play" with music context from history
        elif has_play and context.get('has_music_in_history'):
            recency = context.get('music_recency', 0)
            if recency >= 3:
                confidence = 0.50
                reasons.append("play verb with RECENT music context")
            else:
                confidence = 0.30
                reasons.append("play verb but music context too old")

        # Music noun with play indicators
        elif has_music and any(word in msg_lower for word in ['play', 'start', 'queue']):
            if context.get('has_music_in_history') or any(g in msg_lower for g in GENRES[:20]):
                confidence = 0.60
                reasons.append("music noun with play indicators + context")
            else:
                confidence = 0.35
                reasons.append("music noun + play but no context")

        # "put on some [genre/artist/music]"
        elif 'put on' in msg_lower and (has_artist or has_genre or has_music):
            confidence = 0.92
            reasons.append("put on + music/artist/genre")

        # Artist mention with quantity words
        elif has_artist and any(w in msg_lower for w in ['some', 'little', 'bit of']):
            confidence = 0.85
            reasons.append("artist + quantity word suggests play intent")

        # Just artist name (might be info request)
        elif has_artist and not has_play:
            if any(w in msg_lower for w in ['who', 'what', 'when', 'where', 'how', 'tell me']):
                confidence = 0.2
                reasons.append("artist mentioned but seems like info request")
            elif context.get('has_music_in_history'):
                confidence = 0.7
                reasons.append("artist mentioned with music context")

        return confidence, reasons

    def _extract_music_query(
        self,
        msg_lower: str,
        matched_artist: Optional[str]
    ) -> str:
        """Extract clean music query."""
        if matched_artist:
            return matched_artist

        query = msg_lower
        for signal in PLAY_SIGNALS:
            query = query.replace(signal, '').strip()

        return query

    def _detect_control_intent(
        self,
        msg_lower: str,
        context: Dict
    ) -> Optional[ToolIntent]:
        """Detect music control intent (pause, skip, etc.)."""

        if not any(signal in msg_lower for signal in CONTROL_SIGNALS):
            return None

        confidence = 0.95
        reasons = ["explicit control keyword"]

        # Reduce confidence if no music context
        if (not context.get('has_music_in_history') and
            context.get('music_recency', 0) < 3):
            confidence = 0.75
            reasons.append("reduced: no recent music context")

        # Map control signals to actions
        action = self._extract_control_action(msg_lower)

        return ToolIntent(
            tool_name='control_music',
            confidence=confidence,
            priority=ToolPriority.HIGH,
            reason=' | '.join(reasons),
            extracted_params={'action': action}
        )

    def _extract_control_action(self, msg_lower: str) -> str:
        """Extract control action from message."""
        if 'skip' in msg_lower or 'next' in msg_lower:
            return 'next'
        elif 'previous' in msg_lower or 'back' in msg_lower:
            return 'previous'
        elif 'resume' in msg_lower:
            return 'resume'
        elif 'stop' in msg_lower:
            return 'pause'
        elif 'volume up' in msg_lower or 'louder' in msg_lower or 'turn it up' in msg_lower:
            return 'volume_up'
        elif 'volume down' in msg_lower or 'quieter' in msg_lower or 'softer' in msg_lower or 'turn it down' in msg_lower:
            return 'volume_down'
        elif 'mute' in msg_lower:
            return 'mute'
        else:
            return 'pause'

    def _detect_visualizer_intent(self, msg_lower: str) -> Optional[ToolIntent]:
        """Detect music visualizer intent."""
        if not any(signal in msg_lower for signal in VISUALIZER_SIGNALS):
            return None

        return ToolIntent(
            tool_name='music_visualizer',
            confidence=0.95,
            priority=ToolPriority.HIGH,
            reason="explicit visualizer keywords",
            extracted_params={
                'action': 'start',
                'duration': 300,
                'style': 'party'
            }
        )
