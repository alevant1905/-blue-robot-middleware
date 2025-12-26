"""
Base detector class and interfaces.

All intent detectors inherit from BaseDetector to ensure consistent API.
"""

from typing import Dict, List
from abc import ABC, abstractmethod

from ..models import ToolIntent


class BaseDetector(ABC):
    """
    Base class for all intent detectors.

    Each detector is responsible for identifying intents within a specific
    domain (music, email, lights, etc.) and returning confidence-scored
    ToolIntent objects.
    """

    @abstractmethod
    def detect(
        self,
        message: str,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect intents for this domain.

        Args:
            message: Original user message (preserves case)
            msg_lower: Lowercased message for pattern matching
            context: Conversation context dict with keys:
                - has_*_in_history: bool flags for context
                - *_recency: int, how many messages ago
                - recent_tools: list of recently used tools
                - etc.

        Returns:
            List of detected ToolIntent objects, sorted by confidence (highest first)

        Example:
            >>> detector = MusicDetector()
            >>> intents = detector.detect("play the beatles", "play the beatles", {})
            >>> intents[0].tool_name
            'play_music'
        """
        raise NotImplementedError


class DetectorRegistry:
    """
    Registry for managing detector instances.

    Allows dynamic registration and retrieval of detectors,
    enabling/disabling features at runtime.
    """

    def __init__(self):
        self._detectors: Dict[str, BaseDetector] = {}
        self._enabled: Dict[str, bool] = {}

    def register(self, name: str, detector: BaseDetector, enabled: bool = True):
        """Register a detector."""
        self._detectors[name] = detector
        self._enabled[name] = enabled

    def get(self, name: str) -> BaseDetector:
        """Get detector by name."""
        return self._detectors.get(name)

    def get_all_enabled(self) -> List[BaseDetector]:
        """Get all enabled detectors."""
        return [
            detector
            for name, detector in self._detectors.items()
            if self._enabled.get(name, False)
        ]

    def enable(self, name: str):
        """Enable a detector."""
        if name in self._detectors:
            self._enabled[name] = True

    def disable(self, name: str):
        """Disable a detector."""
        if name in self._detectors:
            self._enabled[name] = False

    def is_enabled(self, name: str) -> bool:
        """Check if detector is enabled."""
        return self._enabled.get(name, False)
