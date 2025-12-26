# Tool Selector Refactoring Plan

## Overview

Refactoring the monolithic `blue/tool_selector.py` (3,028 lines) into a modular package structure.

## Current State

**Before:**
```
blue/
└── tool_selector.py (3,028 lines)
    ├── Helper functions (fuzzy_match, normalize_artist_name)
    ├── Data classes (ToolIntent, ToolSelectionResult)
    ├── ImprovedToolSelector class (2,800+ lines)
    │   ├── 16 _detect_*_intents() methods
    │   ├── 6 _extract_*_params() methods
    │   ├── Hardcoded data (200+ artists, 60+ genres, etc.)
    │   └── Orchestration logic
    └── Integration function
```

## New Structure

**After:**
```
blue/
└── tool_selector/
    ├── __init__.py                 # Package exports
    ├── models.py                   # Data classes (ToolIntent, ToolSelectionResult)
    ├── constants.py                # Thresholds, priorities, patterns
    ├── utils.py                    # Utility functions (fuzzy_match, etc.)
    │
    ├── data/                       # Hardcoded reference data
    │   ├── __init__.py
    │   ├── music_data.py           # Artists, genres, music keywords
    │   ├── light_moods.py          # Mood presets (imported from lights module)
    │   └── patterns.py             # Common regex patterns
    │
    ├── detectors/                  # Intent detection by domain
    │   ├── __init__.py
    │   ├── base.py                 # Base detector class
    │   ├── music.py                # Music-related intents
    │   ├── gmail.py                # Email operations
    │   ├── lights.py               # Smart home lighting
    │   ├── documents.py            # Document operations
    │   ├── web.py                  # Web search
    │   ├── vision.py               # Camera/image operations
    │   ├── calendar.py             # Calendar/events
    │   ├── weather.py              # Weather queries
    │   ├── automation.py           # Routines/automation
    │   ├── contacts.py             # Contact management
    │   ├── habits.py               # Habit tracking
    │   ├── notes.py                # Notes and tasks
    │   ├── timers.py               # Timers and reminders
    │   ├── system.py               # System control
    │   └── utilities.py            # Misc utilities
    │
    ├── extractors.py               # Parameter extraction functions
    ├── context.py                  # Context extraction from history
    ├── selector.py                 # Main ImprovedToolSelector orchestrator
    └── integration.py              # integrate_with_existing_system()
```

## File Size Breakdown

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | ~50 | Package exports and documentation |
| `models.py` | ~50 | Data classes |
| `constants.py` | ~60 | Configuration constants |
| `utils.py` | ~150 | Utility functions |
| `data/music_data.py` | ~300 | Music reference data |
| `detectors/base.py` | ~100 | Base detector interface |
| `detectors/music.py` | ~250 | Music intent detection |
| `detectors/gmail.py` | ~200 | Email intent detection |
| `detectors/*.py` (12 more) | ~100-200 each | Domain-specific detectors |
| `extractors.py` | ~300 | Parameter extraction |
| `context.py` | ~100 | Context management |
| `selector.py` | ~200 | Main orchestrator |
| `integration.py` | ~50 | Legacy integration |

**Total:** ~2,500 lines (split across 25+ files, avg ~100 lines/file)

## Benefits

### 1. **Maintainability**
- Each file under 300 lines (vs single 3,028-line file)
- Clear separation of concerns
- Easy to locate and modify specific functionality

### 2. **Testability**
- Each detector can be tested independently
- Mock data easily injected
- Isolated unit tests per domain

### 3. **Extensibility**
- New intent detectors: just add a new file in `detectors/`
- No need to modify massive monolithic class
- Plugin architecture ready

### 4. **Readability**
- Self-documenting file structure
- Related code grouped together
- Reduced cognitive load

### 5. **Performance**
- Lazy loading of detectors (optional)
- Parallel detection possible
- Easier to profile and optimize

## Migration Strategy

### Phase 1: Create New Structure (Current)
1. ✅ Create package directories
2. ✅ Extract models and constants
3. ✅ Extract utility functions
4. ✅ Create music data file
5. 🔄 Create detector modules

### Phase 2: Implement Detectors
For each detector module:
1. Extract detection logic from `_detect_*_intents()` methods
2. Extract parameter extraction from `_extract_*_params()` methods
3. Add tests for detector
4. Document API

### Phase 3: Orchestrator
1. Create main `selector.py` with simplified orchestration
2. Registry pattern for detector registration
3. Context extraction in separate module
4. Disambiguation logic

### Phase 4: Integration
1. Update `blue/__init__.py` to export from new package
2. Create backward-compatible imports in old `tool_selector.py`
3. Update dependent files
4. Deprecation warnings

### Phase 5: Cleanup
1. Mark old `tool_selector.py` as deprecated
2. Remove after verification period
3. Update documentation
4. Add migration guide

## Detector Interface

Each detector follows a consistent interface:

```python
from typing import Dict, List
from ..models import ToolIntent

class BaseDetector:
    """Base class for all intent detectors."""

    def detect(
        self,
        message: str,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect intents for this domain.

        Args:
            message: Original user message
            msg_lower: Lowercased message
            context: Conversation context

        Returns:
            List of detected ToolIntent objects
        """
        raise NotImplementedError

class MusicDetector(BaseDetector):
    """Detects music playback and control intents."""

    def detect(self, message: str, msg_lower: str, context: Dict) -> List[ToolIntent]:
        intents = []

        # Early exit: non-music play contexts
        if self._is_non_music_context(msg_lower):
            return intents

        # Detect play intents
        play_intent = self._detect_play_intent(msg_lower, context)
        if play_intent:
            intents.append(play_intent)

        # Detect control intents
        control_intent = self._detect_control_intent(msg_lower, context)
        if control_intent:
            intents.append(control_intent)

        return intents
```

## Testing Strategy

Each detector gets comprehensive unit tests:

```python
# tests/test_detectors/test_music.py

def test_play_music_with_artist():
    detector = MusicDetector()
    result = detector.detect("play the beatles", "play the beatles", {})

    assert len(result) == 1
    assert result[0].tool_name == 'play_music'
    assert result[0].confidence >= 0.95
    assert 'beatles' in result[0].extracted_params['query'].lower()


def test_no_music_intent_for_games():
    detector = MusicDetector()
    result = detector.detect("let's play a game", "let's play a game", {})

    assert len(result) == 0  # Should not trigger music


def test_fuzzy_artist_matching():
    detector = MusicDetector()
    result = detector.detect("play beatls", "play beatls", {})  # Typo

    assert len(result) == 1
    assert 'beatles' in result[0].extracted_params.get('query', '').lower()
```

## Backward Compatibility

Old imports continue to work:

```python
# Old way (still works)
from blue.tool_selector import ImprovedToolSelector, ToolIntent

# New way (preferred)
from blue.tool_selector import ImprovedToolSelector, ToolIntent
# (imports from new package location)
```

## Configuration

Detectors can be enabled/disabled via configuration:

```python
# config.py or settings
ENABLED_DETECTORS = [
    'music',
    'gmail',
    'lights',
    'documents',
    # ... etc
]

# Disable detectors for services not configured
if not GMAIL_AVAILABLE:
    ENABLED_DETECTORS.remove('gmail')
```

## Performance Considerations

- **Lazy loading:** Detectors only loaded when needed
- **Caching:** Compiled regex patterns cached
- **Parallel detection:** Multiple detectors can run concurrently
- **Early exits:** Non-matches exit quickly

## Next Steps

1. Complete implementation of all 16 detector modules
2. Write comprehensive tests (target: 80% coverage)
3. Add integration tests
4. Update documentation
5. Performance benchmarking
6. Gradual rollout with feature flag

## Success Metrics

- ✅ All files under 300 lines
- ✅ 80%+ test coverage
- ✅ No functionality regression
- ✅ Same or better performance
- ✅ Improved maintainability score
- ✅ Easier onboarding for new contributors
