"""
Blue Robot Tool Selector - Modular Architecture
================================================

Refactored tool selector with clean separation of concerns.

Package Structure:
    models.py           - Data classes and type definitions
    constants.py        - Configuration and thresholds
    utils.py            - Utility functions (fuzzy matching, etc.)
    detectors/          - Intent detection by domain
        music.py        - Music playback detection
        gmail.py        - Email operations detection
        lights.py       - Smart home lighting detection
        documents.py    - Document operations detection
        web.py          - Web search detection
        vision.py       - Camera and image detection
        ...
    extractors.py       - Parameter extraction functions
    selector.py         - Main orchestrator class

This refactor reduces complexity from a single 3,028-line file to
multiple focused modules under 300 lines each.
"""

from .models import ToolIntent, ToolSelectionResult
from .constants import ToolPriority, ConfidenceThreshold
from .utils import fuzzy_match, normalize_artist_name
from .selector import ImprovedToolSelector
from .integration import integrate_with_existing_system

__all__ = [
    # Data models
    'ToolIntent',
    'ToolSelectionResult',

    # Constants
    'ToolPriority',
    'ConfidenceThreshold',

    # Utilities
    'fuzzy_match',
    'normalize_artist_name',

    # Main selector
    'ImprovedToolSelector',

    # Integration
    'integrate_with_existing_system',
]

__version__ = '2.0.0'
