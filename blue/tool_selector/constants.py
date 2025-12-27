"""
Constants and configuration for tool selection.

Centralizes all magic numbers, thresholds, and configuration values.
"""

from enum import IntEnum


class ToolPriority(IntEnum):
    """
    Tool priority levels.

    Lower values indicate higher priority in case of ambiguity.
    """
    CRITICAL = 1    # Must execute (email operations)
    HIGH = 2        # Very specific (music, visualizer)
    MEDIUM = 3      # Clear intent (lights, weather)
    LOW = 4         # Broader intent (search, documents)
    FALLBACK = 5    # Last resort


class ConfidenceThreshold:
    """
    Confidence score thresholds for tool selection.

    Raised to reduce false positives.
    """
    HIGH = 0.90      # Very confident match
    MEDIUM = 0.75    # Confident match
    LOW = 0.55       # Possible match
    MINIMUM = 0.50   # Below this, don't suggest tool (raised from 0.30)


# Compound request patterns
COMPOUND_CONJUNCTIONS = [
    ' and then ',
    ' and ',
    ' then ',
    ' after that ',
    ' also ',
    ' plus ',
    ' and also ',
]

# Common greetings and casual phrases (don't need tools)
GREETING_PATTERNS = [
    'hello', 'hi ', 'hey ', 'howdy', 'greetings', 'good morning',
    'good afternoon', 'good evening', 'good night', "what's up",
    'whats up', 'sup ', 'yo ', 'hiya',
]

CASUAL_PATTERNS = [
    'thanks', 'thank you', 'thx', 'ty', 'cool', 'nice', 'great',
    'awesome', 'perfect', 'ok ', 'okay', 'sure', 'yep', 'yeah',
    'alright', 'sounds good', 'got it', 'understood', 'no problem',
    'np', 'you\'re welcome', 'yw', 'bye', 'goodbye', 'see you',
    'see ya', 'later', 'cya',
]

# Context extraction configuration
MAX_CONTEXT_MESSAGES = 5  # How many recent messages to consider
CONTEXT_DECAY_FACTOR = 0.8  # How much to reduce confidence from context

# Disambiguation settings
MAX_DISAMBIGUATION_OPTIONS = 3  # Maximum alternatives to show user
MIN_CONFIDENCE_GAP = 0.15  # Minimum gap between primary and alternative

# Cache settings
RESPONSE_CACHE_TTL = 300  # Seconds (5 minutes)
TOOL_USAGE_HISTORY_SIZE = 100  # Number of recent tool uses to track
