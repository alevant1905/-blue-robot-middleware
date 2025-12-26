"""
Blue Robot Middleware Proxy — ENHANCED VERSION v8
==================================================

v8 ENHANCEMENTS (November 2025):
- Compound request parsing ("play jazz and set romantic lights")
- Follow-up correction detection ("no, make it blue" / "louder")
- Smart response caching for repeated queries
- Query complexity estimation for adaptive processing
- Entity extraction (emails, times, numbers, URLs)
- Better action type identification
- Improved context-aware corrections

v7 ENHANCEMENTS:
- Fuzzy matching for artist names (handles typos)
- ConversationState class for better context tracking
- Enhanced error recovery with helpful suggestions
- Utility functions: truncate_text, get_time_ago, safe_json_parse
- Better tool execution wrapper with timing and state tracking

v6 ENHANCEMENTS:
- 200+ music artists, 60+ genres with improved matching
- 50+ light moods/scenes including seasonal, holiday, activity-based
- Enhanced fact extraction: vehicles, medical, languages, skills
- Robust error handling with auto-retry

v5: Cleanup and consolidation
v4: Smart email parameter extraction
v3: Enhanced fact extraction, topic decay
v2: Greeting detection, timer/reminder detection
v1: Camera detection, email/search disambiguation

FILE STRUCTURE:
1. Imports & Configuration (line ~70)
2. Utility Functions (line ~170) - Enhanced in v8
3. Database & Memory (line ~560)  
4. System Prompt (line ~950)
5. Tool Definitions (line ~960)
6. Tool Selector (line ~1050)
7. LLM Client (line ~2650)
8. Music Functions (line ~3050)
9. Vision & Camera (line ~3350)
10. Document Functions (line ~4350)
11. Light Functions (line ~5150)
12. Web Search (line ~5350)
13. Gmail Functions (line ~5650)
14. Main Tool Executor (line ~6000)
15. Legacy Detect Functions (line ~6450)
16. Process With Tools (line ~7200)
17. Flask Routes (line ~8450)
18. Gmail Upgrades (line ~9410)
19. Voice Email Interface (line ~9530)
"""

# ================================================================================
# IMPORTS
# ================================================================================
from __future__ import annotations

# Standard library
import json
import logging
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pickle
import webbrowser
import random
import hashlib
import base64
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Third-party
import requests
from flask import Flask, Response, jsonify, redirect, render_template_string, request, send_from_directory, url_for
from werkzeug.utils import secure_filename
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Visual Memory System (if available)
try:
    from blue_visual_memory import get_visual_memory, VisualMemory
    VISUAL_MEMORY_AVAILABLE = True
    print("[OK] Visual memory system loaded - Blue can now recognize people and places!")
except ImportError:
    VISUAL_MEMORY_AVAILABLE = False
    print("[WARN] Visual memory system not available")

# Enhanced Visual Understanding (if available)
try:
    from blue_visual_understanding import get_visual_understanding, get_enhanced_vision_context
    VISUAL_UNDERSTANDING_AVAILABLE = True
    print("[OK] Enhanced visual understanding loaded - Blue can understand activities and emotions!")
except ImportError:
    VISUAL_UNDERSTANDING_AVAILABLE = False
    print("[WARN] Enhanced visual understanding not available")

# Proactive Assistance (if available)
try:
    from blue_proactive_assistance import get_proactive_assistance, ProactiveSuggestion
    PROACTIVE_ASSISTANCE_AVAILABLE = True
    print("[OK] Proactive assistance loaded - Blue can offer helpful suggestions!")
except ImportError:
    PROACTIVE_ASSISTANCE_AVAILABLE = False
    print("[WARN] Proactive assistance not available")

# Academic Research Assistant (if available)
try:
    from blue_academic_assistant import (
        get_academic_assistant, analyze_with_chat, prepare_lecture,
        generate_discussion_questions, simulate_student_q_and_a,
        synthesize_research, circumference_content
    )
    ACADEMIC_ASSISTANT_AVAILABLE = True
    print("[OK] Academic assistant loaded - Teaching and research tools ready!")
except ImportError:
    ACADEMIC_ASSISTANT_AVAILABLE = False
    print("[WARN] Academic assistant not available")

# Multi-Person Context Awareness (if available)
try:
    from blue_context_awareness import (
        get_context_awareness, adapt_for_audience, get_audience_context,
        generate_contextual_greeting
    )
    CONTEXT_AWARENESS_AVAILABLE = True
    print("[OK] Context awareness loaded - Blue adapts to his audience!")
except ImportError:
    CONTEXT_AWARENESS_AVAILABLE = False
    print("[WARN] Context awareness not available")

# ================================================================================
# LOGGING (single source)
# ================================================================================


def setup_logger(name: str = "blue", level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger

log = setup_logger(level=os.environ.get("LOG_LEVEL", "INFO"))

# ================================================================================
# UTILITY FUNCTIONS - v8 ENHANCED
# ================================================================================

def parse_compound_request(message: str) -> List[Dict[str, Any]]:
    """
    Parse compound requests into individual actions.
    v8 ENHANCEMENT: Handle "play jazz and turn on relaxing lights" as two actions.
    
    Returns list of {action, query, priority} dicts.
    """
    msg_lower = message.lower().strip()
    actions = []
    
    # Compound connectors
    connectors = [' and ', ' then ', ' also ', ' plus ', ', and ', ' & ']
    
    # Check if this is a compound request
    has_connector = any(conn in msg_lower for conn in connectors)
    
    if not has_connector:
        return []  # Not a compound request
    
    # Split on connectors
    parts = [msg_lower]
    for conn in connectors:
        new_parts = []
        for part in parts:
            new_parts.extend(part.split(conn))
        parts = new_parts
    
    # Clean and analyze each part
    for i, part in enumerate(parts):
        part = part.strip()
        if len(part) < 3:
            continue
            
        action_type = _identify_action_type(part)
        if action_type:
            actions.append({
                'action': action_type,
                'query': part,
                'priority': i,
                'original': part
            })
    
    return actions if len(actions) > 1 else []


def _identify_action_type(text: str) -> Optional[str]:
    """Identify the action type from a text fragment."""
    text = text.lower()
    
    # Music
    if any(w in text for w in ['play', 'put on', 'listen to', 'queue']):
        if any(w in text for w in ['music', 'song', 'jazz', 'rock', 'pop', 'by ']):
            return 'play_music'
    
    # Lights
    if any(w in text for w in ['light', 'lamp', 'bright', 'dim']):
        if any(w in text for w in ['turn', 'set', 'make', 'switch']):
            return 'control_lights'
        if any(w in text for w in ['mood', 'scene', 'party', 'relax', 'romantic']):
            return 'control_lights'
    
    # Music control
    if any(w in text for w in ['pause', 'stop', 'skip', 'next', 'volume', 'louder', 'quieter']):
        return 'control_music'
    
    # Weather
    if 'weather' in text:
        return 'get_weather'
    
    # Email
    if 'email' in text or 'inbox' in text:
        if any(w in text for w in ['send', 'write', 'compose']):
            return 'send_gmail'
        if any(w in text for w in ['check', 'read', 'show']):
            return 'read_gmail'
        if any(w in text for w in ['reply', 'respond']):
            return 'reply_gmail'
    
    # Camera
    if any(w in text for w in ['see', 'look', 'photo', 'camera', 'picture']):
        return 'capture_camera'
    
    # Timer
    if any(w in text for w in ['timer', 'remind', 'alarm']):
        return 'set_timer'
    
    return None


def detect_follow_up_correction(message: str, context: Dict) -> Optional[Dict[str, Any]]:
    """
    Detect if user is correcting or refining a previous request.
    v8 ENHANCEMENT: Handle "no, the blue one" or "actually make it louder"
    
    Returns correction info or None.
    """
    msg_lower = message.lower().strip()
    
    # Correction indicators
    correction_starters = [
        'no ', 'not ', 'actually ', 'i meant ', 'i mean ', 'sorry ', 
        'wait ', 'change ', 'make it ', 'instead ', 'rather ', 'wrong '
    ]
    
    is_correction = any(msg_lower.startswith(s) for s in correction_starters)
    
    # Also check for short corrections
    if len(msg_lower.split()) <= 4:
        short_corrections = ['the other', 'different', 'louder', 'quieter', 'brighter', 
                           'dimmer', 'faster', 'slower', 'more', 'less']
        if any(c in msg_lower for c in short_corrections):
            is_correction = True
    
    if not is_correction:
        return None
    
    # Determine what's being corrected
    last_tool = context.get('last_tool_used')
    last_result = context.get('last_tool_result', '')
    
    correction = {
        'is_correction': True,
        'original_tool': last_tool,
        'correction_type': 'unknown',
        'new_value': None
    }
    
    # Light corrections
    if last_tool == 'control_lights' or any(w in msg_lower for w in ['light', 'bright', 'dim', 'color']):
        correction['correction_type'] = 'lights'
        # Extract new color/brightness
        colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'white', 'pink', 'warm', 'cool']
        for color in colors:
            if color in msg_lower:
                correction['new_value'] = color
                break
        if 'brighter' in msg_lower:
            correction['new_value'] = 'brighter'
        elif 'dimmer' in msg_lower or 'darker' in msg_lower:
            correction['new_value'] = 'dimmer'
    
    # Music corrections
    elif last_tool in ['play_music', 'control_music'] or any(w in msg_lower for w in ['music', 'song', 'volume']):
        correction['correction_type'] = 'music'
        if 'louder' in msg_lower:
            correction['new_value'] = 'volume_up'
        elif 'quieter' in msg_lower or 'softer' in msg_lower:
            correction['new_value'] = 'volume_down'
        elif 'different' in msg_lower or 'other' in msg_lower:
            correction['new_value'] = 'skip'
    
    return correction


def smart_cache_key(query: str, tool: str = "") -> str:
    """Generate a smart cache key for query deduplication."""
    import hashlib
    # Normalize the query
    normalized = query.lower().strip()
    # Remove filler words
    fillers = ['please', 'can you', 'could you', 'would you', 'hey', 'blue', 'hi', 'hello']
    for filler in fillers:
        normalized = normalized.replace(filler, '')
    normalized = ' '.join(normalized.split())  # Normalize whitespace
    
    key_input = f"{tool}:{normalized}"
    return hashlib.md5(key_input.encode()).hexdigest()[:16]


# Response cache for repeated queries (5 minute TTL)
_response_cache: Dict[str, Tuple[float, str]] = {}
_RESPONSE_CACHE_TTL = 300  # 5 minutes


def get_cached_response(cache_key: str) -> Optional[str]:
    """Get cached response if still valid."""
    import time
    if cache_key in _response_cache:
        timestamp, response = _response_cache[cache_key]
        if time.time() - timestamp < _RESPONSE_CACHE_TTL:
            return response
        else:
            del _response_cache[cache_key]
    return None


def cache_response(cache_key: str, response: str):
    """Cache a response."""
    import time
    _response_cache[cache_key] = (time.time(), response)
    # Prune old entries
    if len(_response_cache) > 100:
        cutoff = time.time() - _RESPONSE_CACHE_TTL
        keys_to_delete = [k for k, (t, _) in _response_cache.items() if t < cutoff]
        for k in keys_to_delete:
            del _response_cache[k]


def estimate_query_complexity(message: str) -> str:
    """
    Estimate query complexity to adjust processing.
    Returns: 'simple', 'medium', 'complex'
    """
    msg_lower = message.lower()
    word_count = len(message.split())
    
    # Simple: greetings, single commands
    if word_count <= 5:
        return 'simple'
    
    # Complex: multiple actions, detailed requests
    compound_signals = [' and ', ' then ', ' also ', ' after ', ' before ']
    if any(s in msg_lower for s in compound_signals):
        return 'complex'
    
    # Complex: questions requiring research
    research_signals = ['explain', 'compare', 'difference between', 'how does', 'why does', 'analysis']
    if any(s in msg_lower for s in research_signals):
        return 'complex'
    
    # Medium: typical requests
    if word_count <= 15:
        return 'medium'
    
    return 'complex'


def extract_entities(message: str) -> Dict[str, List[str]]:
    """
    Extract named entities from message.
    v8 ENHANCEMENT: Better entity extraction for personalization.
    """
    entities = {
        'people': [],
        'places': [],
        'times': [],
        'numbers': [],
        'emails': [],
        'urls': []
    }
    
    # Email addresses
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    entities['emails'] = re.findall(email_pattern, message)
    
    # URLs
    url_pattern = r'https?://[^\s]+'
    entities['urls'] = re.findall(url_pattern, message)
    
    # Times
    time_patterns = [
        r'\d{1,2}:\d{2}(?:\s*[ap]m)?',
        r'\d{1,2}\s*(?:am|pm)',
        r'(?:noon|midnight|morning|afternoon|evening|night)',
        r'(?:today|tomorrow|yesterday)',
        r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
    ]
    for pattern in time_patterns:
        matches = re.findall(pattern, message.lower())
        entities['times'].extend(matches)
    
    # Numbers
    number_pattern = r'\b\d+(?:\.\d+)?\b'
    entities['numbers'] = re.findall(number_pattern, message)
    
    return entities


def fuzzy_match(query: str, targets: List[str], threshold: float = 0.75) -> Optional[str]:
    """
    Find the best fuzzy match for a query in a list of targets.
    Uses simple similarity ratio - no external dependencies.
    
    Args:
        query: The search string
        targets: List of possible matches
        threshold: Minimum similarity (0.0 to 1.0)
    
    Returns:
        Best matching target or None if no good match
    """
    if not query or not targets:
        return None
    
    query_lower = query.lower().strip()
    
    # Exact match first
    for target in targets:
        if query_lower == target.lower():
            return target
    
    # Substring match
    for target in targets:
        if query_lower in target.lower() or target.lower() in query_lower:
            return target
    
    # Similarity matching
    best_match = None
    best_score = 0.0
    
    for target in targets:
        score = _string_similarity(query_lower, target.lower())
        if score > best_score and score >= threshold:
            best_score = score
            best_match = target
    
    return best_match


def _string_similarity(s1: str, s2: str) -> float:
    """Calculate string similarity using character-based comparison."""
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    
    # Simple Jaccard-like similarity on character bigrams
    def get_bigrams(s):
        return set(s[i:i+2] for i in range(len(s) - 1)) if len(s) > 1 else {s}
    
    b1 = get_bigrams(s1)
    b2 = get_bigrams(s2)
    
    intersection = len(b1 & b2)
    union = len(b1 | b2)
    
    return intersection / union if union > 0 else 0.0


def normalize_artist_name(name: str) -> str:
    """Normalize artist name for matching."""
    if not name:
        return ""
    
    # Common replacements
    replacements = {
        '&': 'and',
        '+': 'and',
        ' - ': ' ',
        "'s": 's',
        '"': '',
    }
    
    result = name.lower().strip()
    for old, new in replacements.items():
        result = result.replace(old, new)
    
    # Remove "the " prefix for matching
    if result.startswith('the '):
        result = result[4:]
    
    return result


def safe_json_parse(text: str, default: Any = None) -> Any:
    """Safely parse JSON with fallback."""
    if not text:
        return default
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to max length with suffix."""
    if not text or len(text) <= max_length:
        return text or ""
    return text[:max_length - len(suffix)] + suffix


def extract_quoted_text(text: str) -> List[str]:
    """Extract all quoted strings from text."""
    import re
    # Match double and single quotes
    patterns = [
        r'"([^"]+)"',
        r"'([^']+)'",
    ]
    results = []
    for pattern in patterns:
        results.extend(re.findall(pattern, text))
    return results


def get_time_ago(timestamp: float) -> str:
    """Convert timestamp to human-readable 'time ago' string."""
    import time
    diff = time.time() - timestamp
    
    if diff < 60:
        return "just now"
    elif diff < 3600:
        mins = int(diff / 60)
        return f"{mins} minute{'s' if mins != 1 else ''} ago"
    elif diff < 86400:
        hours = int(diff / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff < 604800:
        days = int(diff / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        weeks = int(diff / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"


class ConversationState:
    """
    Track conversation state for better context awareness.
    v8 ENHANCED: More tracking, pattern learning, and suggestions.
    """
    
    def __init__(self):
        self.last_tool_used: Optional[str] = None
        self.last_tool_result: Optional[str] = None
        self.last_tool_args: Optional[Dict] = None
        self.pending_confirmation: Optional[str] = None
        self.topic_stack: List[str] = []
        self.user_corrections: List[Dict] = []
        self.successful_patterns: Dict[str, int] = {}
        self.failed_patterns: Dict[str, int] = {}
        self.tool_sequence: List[str] = []  # Track tool order
        self.last_query: str = ""
        self.query_count: int = 0
        self.session_start: float = __import__('time').time()
    
    def record_tool_use(self, tool_name: str, success: bool, pattern: str = "", args: Dict = None):
        """Record tool usage for learning."""
        self.last_tool_used = tool_name
        self.last_tool_args = args or {}
        self.tool_sequence.append(tool_name)
        if len(self.tool_sequence) > 20:
            self.tool_sequence.pop(0)
        
        if pattern:
            if success:
                self.successful_patterns[pattern] = self.successful_patterns.get(pattern, 0) + 1
            else:
                self.failed_patterns[pattern] = self.failed_patterns.get(pattern, 0) + 1
    
    def push_topic(self, topic: str):
        """Add a topic to the stack."""
        if topic and (not self.topic_stack or self.topic_stack[-1] != topic):
            self.topic_stack.append(topic)
            if len(self.topic_stack) > 10:
                self.topic_stack.pop(0)
    
    def get_current_topic(self) -> Optional[str]:
        """Get the most recent topic."""
        return self.topic_stack[-1] if self.topic_stack else None
    
    def record_correction(self, original: str, corrected: str):
        """Record user corrections for learning."""
        self.user_corrections.append({
            'original': original,
            'corrected': corrected,
            'timestamp': __import__('time').time()
        })
        if len(self.user_corrections) > 50:
            self.user_corrections.pop(0)
    
    def record_query(self, query: str):
        """Record a new query."""
        self.last_query = query
        self.query_count += 1
    
    def get_common_tool_pairs(self) -> List[Tuple[str, str]]:
        """Get commonly used tool pairs (for compound request optimization)."""
        pairs = {}
        for i in range(len(self.tool_sequence) - 1):
            pair = (self.tool_sequence[i], self.tool_sequence[i+1])
            pairs[pair] = pairs.get(pair, 0) + 1
        
        # Return top 3 most common pairs
        sorted_pairs = sorted(pairs.items(), key=lambda x: x[1], reverse=True)
        return [pair for pair, count in sorted_pairs[:3] if count > 1]
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        import time
        return {
            'duration_minutes': (time.time() - self.session_start) / 60,
            'query_count': self.query_count,
            'tools_used': len(set(self.tool_sequence)),
            'most_used_tools': self._get_tool_frequency(),
            'corrections_made': len(self.user_corrections)
        }
    
    def _get_tool_frequency(self) -> Dict[str, int]:
        """Get tool usage frequency."""
        freq = {}
        for tool in self.tool_sequence:
            freq[tool] = freq.get(tool, 0) + 1
        return dict(sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5])
    
    def suggest_next_action(self) -> Optional[str]:
        """Suggest next action based on patterns."""
        if not self.last_tool_used:
            return None
        
        # Check common pairs
        pairs = self.get_common_tool_pairs()
        for first, second in pairs:
            if first == self.last_tool_used:
                return f"You often use {second} after {first}. Would you like me to do that?"
        
        return None


# Global conversation state
_conversation_state = ConversationState()


def get_conversation_state() -> ConversationState:
    """Get the global conversation state."""
    return _conversation_state


def validate_response_quality(response: str, query: str) -> Dict[str, Any]:
    """
    Validate response quality and provide improvement suggestions.
    v7 ENHANCEMENT: Better response quality checking.
    """
    issues = []
    score = 100
    
    # Check for empty or very short response
    if not response or len(response.strip()) < 10:
        issues.append("Response is too short")
        score -= 30
    
    # Check for error indicators
    error_phrases = ['error', 'failed', 'could not', 'unable to', 'something went wrong']
    if any(phrase in response.lower() for phrase in error_phrases):
        issues.append("Response contains error indicators")
        score -= 20
    
    # Check for hallucination indicators (claiming to have searched without using tools)
    hallucination_phrases = ['i searched', 'according to my search', 'i found that', 'my research shows']
    if any(phrase in response.lower() for phrase in hallucination_phrases):
        if 'web_search' not in str(get_conversation_state().last_tool_used):
            issues.append("Possible hallucination - claims search without tool use")
            score -= 25
    
    # Check for repetition
    sentences = response.split('.')
    unique_sentences = set(s.strip().lower() for s in sentences if s.strip())
    if len(sentences) > 3 and len(unique_sentences) < len(sentences) * 0.7:
        issues.append("Response contains repetitive content")
        score -= 15
    
    # Check if response addresses the query
    query_words = set(query.lower().split())
    response_words = set(response.lower().split())
    overlap = len(query_words & response_words) / len(query_words) if query_words else 0
    if overlap < 0.2 and len(query_words) > 2:
        issues.append("Response may not address the query directly")
        score -= 10
    
    return {
        'score': max(0, score),
        'issues': issues,
        'is_valid': score >= 50
    }


def clean_response_text(text: str) -> str:
    """Clean up response text for better presentation."""
    if not text:
        return ""
    
    # Remove excessive whitespace
    import re
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    
    # Remove common artifacts
    artifacts = ['```json', '```', '{"', '"}']
    for artifact in artifacts:
        if text.startswith(artifact) or text.endswith(artifact):
            text = text.strip(artifact)
    
    return text.strip()


def extract_action_from_query(query: str) -> Dict[str, Any]:
    """
    Extract the intended action and parameters from a user query.
    v7 ENHANCEMENT: Better query understanding.
    """
    query_lower = query.lower().strip()
    
    # Action patterns with their tool mappings
    action_patterns = {
        'play_music': [r'^play\s+(.+)', r'^put on\s+(.+)', r'^listen to\s+(.+)'],
        'control_lights': [r'^turn (on|off)\s+(.+)?lights?', r'^set lights? to\s+(.+)', r'^(\w+) mode for lights'],
        'web_search': [r'^search (?:for\s+)?(.+)', r'^google\s+(.+)', r'^look up\s+(.+)'],
        'read_gmail': [r'^check (?:my )?email', r'^read (?:my )?email', r'^show (?:my )?inbox'],
        'send_gmail': [r'^send (?:an )?email to\s+(.+)', r'^email\s+(\S+@\S+)'],
        'get_weather': [r'^weather (?:in\s+)?(.+)?', r'^what\'?s the weather'],
        'capture_camera': [r'^what do you see', r'^take a photo', r'^look around'],
    }
    
    for tool, patterns in action_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                return {
                    'action': tool,
                    'params': match.groups() if match.groups() else None,
                    'confidence': 0.9,
                    'raw_match': match.group(0)
                }
    
    return {
        'action': None,
        'params': None,
        'confidence': 0.0,
        'raw_match': None
    }


# ================================================================================

# --- Document storage configuration ---
DOCUMENTS_FOLDER = os.environ.get("DOCUMENTS_DIR", os.path.join(os.getcwd(), "uploaded_documents"))
os.makedirs(DOCUMENTS_FOLDER, exist_ok=True)

# CONFIG (single source)
# ================================================================================

# Core facts DB
BLUE_FACTS_DB = os.environ.get("BLUE_FACTS_DB", "data/blue.db")
BLUE_FACTS: Dict[str, str] = {}

# Model/API (left as env-driven to match your runtime)
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "4096"))

# Conversation context (resolved the previous inconsistencies; default 20)
MAX_CONTEXT_MESSAGES = int(os.environ.get("MAX_CONTEXT_MESSAGES", "20"))

# Files
UPLOAD_FOLDER = Path(os.environ.get("UPLOAD_FOLDER", "uploads"))
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'bmp', 'csv', 'doc', 'docx', 'gif', 'html', 'jpeg', 'jpg', 'json', 'md', 'pdf', 'png', 'pptx', 'rtf', 'tiff', 'txt', 'webp', 'xlsx', 'xml'}

# DB (conversations)
CONVERSATION_DB = os.environ.get("CONVERSATION_DB", "data/conversations.db")

# Address book
ADDRESS_BOOK_PATH = Path(os.environ.get("BLUE_ADDRESS_BOOK", "/mnt/data/blue_address_book.json"))

# Gmail scopes — unified so read/label/send/compose all work
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
]
# ================================================================================
# BLUE CORE MEMORY SYSTEM - IMPROVED VERSION
# ================================================================================

try:
    from blue_memory_improved import get_memory_system
    memory_system = get_memory_system()
    ENHANCED_MEMORY_AVAILABLE = True
    print("[OK] Enhanced memory system loaded - Blue will remember better!")
except ImportError as e:
    ENHANCED_MEMORY_AVAILABLE = False
    memory_system = None
    print(f"[WARN] Enhanced memory not available: {e}")
    print("[WARN] Using legacy memory system")


def load_blue_facts(db_path: str = BLUE_FACTS_DB) -> Dict[str, str]:
    """Load facts using improved memory system if available."""
    if ENHANCED_MEMORY_AVAILABLE and memory_system:
        return memory_system.load_facts()
    
    # Fallback to legacy system
    facts: Dict[str, str] = {}
    try:
        if not os.path.exists(db_path):
            log.warning(f"[MEM] facts DB not found: {db_path}")
            return facts
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT fact_key, values_concat FROM facts_top").fetchall()
        for r in rows:
            facts[r["fact_key"]] = r["values_concat"]
    except Exception as e:
        log.warning(f"[MEM] failed to load facts: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass
    if facts:
        log.info(f"[MEM] loaded {len(facts)} core facts from {db_path}")
    return facts

def _facts_block() -> str:
    items: List[str] = []
    # Get fresh facts if enhanced memory is available
    facts = load_blue_facts() if ENHANCED_MEMORY_AVAILABLE else BLUE_FACTS
    
    def add(label: str, key: str) -> None:
        v = facts.get(key)
        if v:
            items.append(f"{label}: {v}")
    for label, key in [
        ("Name", "name"),
        ("Identity", "identity"),
        ("Created by", "created_by"),
        ("Original form", "original_form"),
        ("Upgraded by", "upgraded_by"),
        ("Privacy", "privacy"),
        ("Physical features", "physical_features"),
        ("Tools", "tool"),
        ("Has memory", "has_memory"),
        ("Moods", "mood"),
    ]:
        add(label, key)
    return " | ".join(items)



def save_blue_facts(facts: Dict[str, str], db_path: str = None) -> bool:
    """Save facts using improved memory system if available."""
    global BLUE_FACTS
    BLUE_FACTS.update(facts)
    
    if ENHANCED_MEMORY_AVAILABLE and memory_system:
        return memory_system.save_facts(facts)
    
    # Fallback to legacy system
    if db_path is None:
        db_path = BLUE_FACTS_DB
    
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create table if needed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts_top (
                fact_key TEXT PRIMARY KEY,
                values_concat TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Save facts
        saved_count = 0
        for fact_key, values_concat in facts.items():
            cursor.execute("""
                INSERT INTO facts_top (fact_key, values_concat, last_updated)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(fact_key) DO UPDATE SET
                    values_concat = excluded.values_concat,
                    last_updated = CURRENT_TIMESTAMP
            """, (fact_key, values_concat))
            saved_count += 1
        
        conn.commit()
        conn.close()
        log.info(f"[MEM] Saved {saved_count} facts to database")
        return True
    except Exception as e:
        log.error(f"[MEM] Failed to save facts: {e}")
        return False


def extract_and_save_facts(messages: list) -> bool:
    """Extract facts from conversation and save to database."""
    # Try enhanced system first
    if ENHANCED_MEMORY_AVAILABLE and memory_system:
        try:
            return memory_system.extract_and_save_facts(messages)
        except Exception as e:
            log.warning(f"[MEM] Enhanced extraction failed, using legacy: {e}")
    
    # Fallback to legacy extraction
    if not messages:
        return False
    
    import re
    facts_to_save = {}
    
    for msg in messages:
        if msg.get('role') not in ['user', 'assistant']:
            continue
        
        content = msg.get('content', '')
        content_lower = content.lower()
        
        if len(content) < 10 or content.strip().startswith(('{', '[', '```', 'import ')):
            continue
        
        # === NAME EXTRACTION ===
        name_patterns = [
            r"my name is ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"i'?m ([A-Z][a-z]+)(?:\s|,|\.|$)",
            r"call me ([A-Z][a-z]+)",
            r"this is ([A-Z][a-z]+) speaking",
            r"it'?s ([A-Z][a-z]+) here"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, content)
            if match:
                name = match.group(1).strip()
                if 2 <= len(name) <= 30 and name.replace(' ', '').isalpha():
                    facts_to_save['user_name'] = name
                    log.info(f"[MEM] Learned name: {name}")
                    break
        
        # === LOCATION EXTRACTION ===
        location_patterns = [
            r"i live in ([A-Z][a-zA-Z\s,]+?)(?:\.|,|$|\sand\s|\swith\s)",
            r"i'?m (?:from|in|based in) ([A-Z][a-zA-Z\s]+?)(?:\.|,|$)",
            r"my (?:city|town|home) is ([A-Z][a-zA-Z\s]+)",
            r"we live in ([A-Z][a-zA-Z\s,]+?)(?:\.|,|$)"
        ]
        for pattern in location_patterns:
            match = re.search(pattern, content)
            if match:
                location = match.group(1).strip().rstrip('.,;')
                if 2 <= len(location) <= 50:
                    facts_to_save['location'] = location
                    log.info(f"[MEM] Learned location: {location}")
                    break
        
        # === WORK/EDUCATION ===
        work_patterns = [
            (r"i (?:work|teach) at ([A-Z][a-zA-Z\s&.]+?)(?:\.|,|$)", 'workplace'),
            (r"i work for ([A-Z][a-zA-Z\s&]+?)(?:\.|,|$)", 'workplace'),
            (r"i'?m (?:a|an) ([a-z][a-z\s]+(?:teacher|professor|engineer|developer|doctor|scientist|artist|writer|designer|manager|director))", 'occupation'),
            (r"i studied (?:at )?([A-Z][a-zA-Z\s&]+?)(?:\.|,|$)", 'education'),
            (r"i graduated from ([A-Z][a-zA-Z\s&]+?)(?:\.|,|$)", 'education'),
            (r"i run ([A-Z][a-zA-Z\s&]+?)(?:\.|,|$)", 'business'),
            (r"my company is ([A-Z][a-zA-Z\s&]+?)(?:\.|,|$)", 'business')
        ]
        for pattern, key in work_patterns:
            match = re.search(pattern, content)
            if match:
                value = match.group(1).strip().rstrip('.,;')
                if 2 <= len(value) <= 100:
                    facts_to_save[key] = value
                    log.info(f"[MEM] Learned {key}: {value}")
        
        # === FAMILY EXTRACTION ===
        family_relations = ['partner', 'wife', 'husband', 'spouse', 'daughter', 'son', 'child', 
                           'mother', 'father', 'mom', 'dad', 'brother', 'sister', 'girlfriend', 'boyfriend']
        for relation in family_relations:
            patterns = [
                rf"my {relation}(?:'s name)? is ([A-Z][a-z]+)",
                rf"my {relation},? ([A-Z][a-z]+)",
                rf"(?:this is |meet )?my {relation} ([A-Z][a-z]+)"
            ]
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    name = match.group(1).strip()
                    if 2 <= len(name) <= 30 and name.isalpha():
                        facts_to_save[f'{relation}_name'] = name
                        log.info(f"[MEM] Learned {relation}: {name}")
                        break
        
        # Multiple children (e.g., "my daughters are Emmy, Athena, and Vilda")
        if re.search(r"my (?:daughters?|sons?|children|kids) (?:are|named) ", content_lower):
            match = re.search(r"my (?:daughters?|sons?|children|kids) (?:are|named) ([A-Z][a-zA-Z,\s&]+?)(?:\.|$)", content)
            if match:
                names = match.group(1).strip()
                if 2 <= len(names) <= 100:
                    facts_to_save['children_names'] = names
                    log.info(f"[MEM] Learned children: {names}")
        
        # === PETS ===
        pet_types = ['dog', 'cat', 'pet', 'puppy', 'kitten', 'bird', 'fish', 'hamster', 'rabbit']
        for pet in pet_types:
            patterns = [
                rf"my {pet}(?:'s name)? is ([A-Z][a-z]+)",
                rf"my {pet},? ([A-Z][a-z]+)",
                rf"i have a {pet} (?:named |called )?([A-Z][a-z]+)",
                rf"(?:this is |meet )?my {pet} ([A-Z][a-z]+)"
            ]
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    name = match.group(1).strip()
                    if 2 <= len(name) <= 30 and name.isalpha():
                        facts_to_save[f'{pet}_name'] = name
                        log.info(f"[MEM] Learned {pet}: {name}")
                        break
        
        # === HOBBIES & INTERESTS ===
        hobby_patterns = [
            (r"i (?:love|enjoy|like) (?:to )?([a-z]+ing)", 'hobby'),
            (r"my hobbies? (?:is|are|include) ([a-zA-Z,\s&]+?)(?:\.|$)", 'hobbies'),
            (r"i'?m (?:really )?into ([a-zA-Z\s]+?)(?:\.|,|$)", 'interest'),
            (r"i collect ([a-zA-Z\s]+?)(?:\.|,|$)", 'collection')
        ]
        for pattern, key in hobby_patterns:
            match = re.search(pattern, content_lower)
            if match:
                value = match.group(1).strip().rstrip('.,;')
                if 3 <= len(value) <= 50:
                    facts_to_save[key] = value.title()
                    log.info(f"[MEM] Learned {key}: {value}")
        
        # === PREFERENCES ===
        if 'my favorite' in content_lower or 'i prefer' in content_lower:
            match = re.search(r"my favorite ([a-z\s]+) is ([a-zA-Z0-9\s]+?)(?:\.|,|$)", content_lower)
            if match:
                pref_type = match.group(1).strip().replace(' ', '_')
                pref_value = match.group(2).strip().title()
                if len(pref_type) <= 20 and len(pref_value) <= 50:
                    facts_to_save[f'favorite_{pref_type}'] = pref_value
                    log.info(f"[MEM] Learned {pref_type}: {pref_value}")
            
            match = re.search(r"i prefer ([a-zA-Z\s]+) (?:over|to) ([a-zA-Z\s]+)", content_lower)
            if match:
                preference = f"{match.group(1).strip()} over {match.group(2).strip()}"
                facts_to_save['preference'] = preference.title()
                log.info(f"[MEM] Learned preference: {preference}")
        
        # === BIRTHDAY/AGE ===
        if "i'm " in content_lower or "i am " in content_lower:
            match = re.search(r"i'?m (\d{1,2}) years old", content_lower)
            if match:
                age = match.group(1)
                if 5 <= int(age) <= 120:
                    facts_to_save['age'] = age
                    log.info(f"[MEM] Learned age: {age}")
        
        birthday_patterns = [
            r"my birthday is ([A-Za-z]+ \d{1,2})",
            r"i was born (?:on )?([A-Za-z]+ \d{1,2})",
            r"my birthday'?s? (?:on )?([A-Za-z]+ \d{1,2})"
        ]
        for pattern in birthday_patterns:
            match = re.search(pattern, content)
            if match:
                birthday = match.group(1).strip()
                facts_to_save['birthday'] = birthday
                log.info(f"[MEM] Learned birthday: {birthday}")
                break
        
        # === ALLERGIES/DIETARY ===
        allergy_patterns = [
            r"i'?m allergic to ([a-zA-Z\s,]+?)(?:\.|$)",
            r"i have (?:a |an )?([a-zA-Z\s]+) allergy",
            r"i can'?t eat ([a-zA-Z\s]+?)(?:\.|,|$)"
        ]
        for pattern in allergy_patterns:
            match = re.search(pattern, content_lower)
            if match:
                allergy = match.group(1).strip()
                if 2 <= len(allergy) <= 50:
                    facts_to_save['allergy'] = allergy.title()
                    log.info(f"[MEM] Learned allergy: {allergy}")
                    break
        
        dietary_patterns = [
            r"i'?m (?:a )?(vegetarian|vegan|pescatarian|gluten[- ]free|lactose[- ]intolerant|keto|paleo)",
            r"i (?:don'?t|do not) eat ([a-zA-Z\s]+?)(?:\.|,|$)"
        ]
        for pattern in dietary_patterns:
            match = re.search(pattern, content_lower)
            if match:
                diet = match.group(1).strip()
                facts_to_save['dietary'] = diet.title()
                log.info(f"[MEM] Learned dietary: {diet}")
                break
        
        # === VEHICLES (v6 enhancement) ===
        vehicle_patterns = [
            (r"i drive (?:a |an )?(\d{4} )?([A-Z][a-zA-Z]+ [A-Z]?[a-zA-Z]+)", 'vehicle'),
            (r"my car is (?:a |an )?(\d{4} )?([A-Z][a-zA-Z]+ [A-Z]?[a-zA-Z]+)", 'vehicle'),
            (r"i have (?:a |an )?(\d{4} )?([A-Z][a-zA-Z]+ [A-Z]?[a-zA-Z]+) (?:car|truck|suv|vehicle)", 'vehicle'),
        ]
        for pattern, key in vehicle_patterns:
            match = re.search(pattern, content)
            if match:
                year = match.group(1).strip() if match.group(1) else ""
                make_model = match.group(2).strip()
                vehicle = f"{year}{make_model}".strip()
                if 3 <= len(vehicle) <= 50:
                    facts_to_save['vehicle'] = vehicle
                    log.info(f"[MEM] Learned vehicle: {vehicle}")
                    break
        
        # === LANGUAGES (v6 enhancement) ===
        language_patterns = [
            r"i speak ([A-Z][a-z]+(?:,? (?:and )?[A-Z][a-z]+)*)",
            r"i'?m fluent in ([A-Z][a-z]+(?:,? (?:and )?[A-Z][a-z]+)*)",
            r"my (?:native|first) language is ([A-Z][a-z]+)",
            r"i'?m learning ([A-Z][a-z]+)"
        ]
        for pattern in language_patterns:
            match = re.search(pattern, content)
            if match:
                languages = match.group(1).strip()
                if 3 <= len(languages) <= 100:
                    facts_to_save['languages'] = languages
                    log.info(f"[MEM] Learned languages: {languages}")
                    break
        
        # === SKILLS/EXPERTISE (v6 enhancement) ===
        skill_patterns = [
            r"i'?m (?:good|great|skilled|experienced) at ([a-zA-Z\s,]+?)(?:\.|$)",
            r"i know (?:how to )?([a-zA-Z\s]+?)(?:\.|$)",
            r"i can ([a-zA-Z\s]+) (?:well|professionally|expertly)",
            r"my skills? (?:include|are|is) ([a-zA-Z\s,]+?)(?:\.|$)"
        ]
        for pattern in skill_patterns:
            match = re.search(pattern, content_lower)
            if match:
                skill = match.group(1).strip()
                if 3 <= len(skill) <= 100 and skill not in ['do', 'be', 'help']:
                    facts_to_save['skills'] = skill.title()
                    log.info(f"[MEM] Learned skill: {skill}")
                    break
        
        # === MEDICAL (v6 enhancement) ===
        medical_patterns = [
            r"i have ([a-zA-Z\s]+(?:diabetes|asthma|arthritis|condition|disease|disorder))",
            r"i'?m (?:on|taking) ([a-zA-Z\s]+) (?:medication|medicine|pills)",
            r"i wear ([a-zA-Z\s]+(?:glasses|contacts|hearing aid|braces))"
        ]
        for pattern in medical_patterns:
            match = re.search(pattern, content_lower)
            if match:
                medical = match.group(1).strip()
                if 3 <= len(medical) <= 50:
                    facts_to_save['medical'] = medical.title()
                    log.info(f"[MEM] Learned medical: {medical}")
                    break
        
        # === TIMEZONE/SCHEDULE (v6 enhancement) ===
        if 'timezone' in content_lower or 'time zone' in content_lower:
            match = re.search(r"(?:my )?time ?zone is ([A-Z]{2,4}|[A-Z][a-z]+/[A-Z][a-z]+)", content)
            if match:
                tz = match.group(1).strip()
                facts_to_save['timezone'] = tz
                log.info(f"[MEM] Learned timezone: {tz}")
        
        # === PHONE/CONTACT (v6 enhancement) ===
        phone_match = re.search(r"my (?:phone|number|cell) is ([0-9\-\(\)\s]{10,20})", content)
        if phone_match:
            phone = phone_match.group(1).strip()
            facts_to_save['phone'] = phone
            log.info(f"[MEM] Learned phone: {phone}")
        
        # === EMAIL (v6 enhancement) ===
        email_match = re.search(r"my email is ([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", content)
        if email_match:
            email = email_match.group(1).strip()
            facts_to_save['email'] = email
            log.info(f"[MEM] Learned email: {email}")
    
    if facts_to_save:
        global BLUE_FACTS
        BLUE_FACTS.update(facts_to_save)
        return save_blue_facts(BLUE_FACTS)
    
    return False


def build_system_preamble() -> str:
    core = _facts_block()
    return ("You are Blue. Use these ground-truth facts as identity context. "
            "Do not contradict them. " + core) if core else "You are Blue."

# Load facts at import time (only if enhanced memory not available)
try:
    if not ENHANCED_MEMORY_AVAILABLE:
        BLUE_FACTS = load_blue_facts()
    else:
        # With enhanced memory, facts are loaded fresh each conversation
        BLUE_FACTS = {}
except Exception:
    BLUE_FACTS = {}

# ===== Enhanced Tools Import =====
try:
    from blue_tools_enhanced import (
        CalendarManager,
        TaskManager,
        NoteManager,
        SystemController,
        FileOperations,
        TimerManager,
        StorytellingTools,
        LocationServices,
        SmartHomeController,
        MusicController
    )
    ENHANCED_TOOLS_AVAILABLE = True
    print("[OK] Enhanced tools loaded successfully!")
except ImportError as e:
    ENHANCED_TOOLS_AVAILABLE = False
    print(f"[WARN] Enhanced tools not available: {e}")

# ===== Conversation Persistence Setup =====
try:
    from blue_database import create_database
    db = create_database()
    CONVERSATION_DB_AVAILABLE = True
    print("[OK] Conversation database connected - long-term memory enabled!")
except Exception as e:
    CONVERSATION_DB_AVAILABLE = False
    db = None
    print(f"[WARN] Conversation database not available: {e}")
    print("[WARN] Blue will not remember conversations across sessions")

    print("[WARN] Place blue_tools_enhanced.py in the same directory to enable enhanced features")


# ================================================================================
# IMPROVED TOOL SELECTION SYSTEM (Integrated Version - October 2025)
# ================================================================================
# This section contains the confidence-based tool selection system.
# When enabled (USE_IMPROVED_SELECTOR=True), it provides:
# - Confidence scoring (0.0-1.0) for each tool
# - Priority-based conflict resolution
# - Context awareness from conversation history
# - Disambiguation when confidence is low
# - Negative signals to prevent false positives
# ================================================================================

"""
Blue Robot Tool Selection - ENHANCED VERSION
=============================================

Key improvements over original:
1. Clear positive AND negative signals for each tool
2. Better email disambiguation (read vs send vs reply)
3. Better search disambiguation (web vs documents)
4. Context awareness from conversation history
5. Specific disambiguation questions when uncertain
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
import re
from collections import defaultdict, Counter
import json


@dataclass
class ToolIntent:
    """Represents a detected intent to use a specific tool."""
    tool_name: str
    confidence: float  # 0.0 to 1.0
    priority: int  # Lower number = higher priority
    reason: str  # Why this tool was selected
    extracted_params: Dict = field(default_factory=dict)
    negative_signals: List[str] = field(default_factory=list)


@dataclass
class ToolSelectionResult:
    """Result of tool selection analysis."""
    primary_tool: Optional[ToolIntent]
    alternative_tools: List[ToolIntent]
    needs_disambiguation: bool
    disambiguation_prompt: Optional[str]
    compound_request: bool  # True if multiple tools needed


class ImprovedToolSelector:
    """
    Enhanced tool selection engine with confidence scoring and context awareness.
    """

    # Tool priority levels (lower = higher priority)
    PRIORITY_CRITICAL = 1  # Must execute (email operations)
    PRIORITY_HIGH = 2      # Very specific (music, visualizer)
    PRIORITY_MEDIUM = 3    # Clear intent (lights, weather)
    PRIORITY_LOW = 4       # Broader intent (search, documents)
    PRIORITY_FALLBACK = 5  # Last resort

    # Confidence thresholds
    CONFIDENCE_HIGH = 0.85
    CONFIDENCE_MEDIUM = 0.65
    CONFIDENCE_LOW = 0.45
    CONFIDENCE_MINIMUM = 0.30  # Below this, don't suggest tool

    def __init__(self):
        self.tool_usage_history = Counter()  # Track which tools are used frequently
        self.disambiguation_memory = {}  # Remember user's choices

    def select_tool(
        self,
        message: str,
        conversation_history: List[Dict] = None
    ) -> ToolSelectionResult:
        """
        Main entry point for tool selection.

        Args:
            message: Current user message
            conversation_history: Recent conversation messages for context

        Returns:
            ToolSelectionResult with primary tool and alternatives
        """
        if conversation_history is None:
            conversation_history = []

        # Check for compound request patterns first
        compound_patterns = self._detect_compound_patterns(message.lower())
        
        # Detect all possible tool intents with confidence scores
        all_intents = self._detect_all_intents(message, conversation_history)

        # Filter out low-confidence intents
        viable_intents = [
            intent for intent in all_intents
            if intent.confidence >= self.CONFIDENCE_MINIMUM
        ]

        if not viable_intents:
            # No clear tool needed
            return ToolSelectionResult(
                primary_tool=None,
                alternative_tools=[],
                needs_disambiguation=False,
                disambiguation_prompt=None,
                compound_request=False
            )

        # Sort by priority first, then confidence
        viable_intents.sort(key=lambda x: (x.priority, -x.confidence))

        # Check for compound requests (multiple high-confidence tools from different categories)
        high_confidence_tools = [
            intent for intent in viable_intents
            if intent.confidence >= self.CONFIDENCE_MEDIUM
        ]
        
        # True compound = different tool types with high confidence
        unique_tools = set(t.tool_name for t in high_confidence_tools)
        is_compound = len(unique_tools) > 1 or compound_patterns

        # Get primary tool
        primary = viable_intents[0]
        alternatives = viable_intents[1:4]  # Top 3 alternatives

        # Check if disambiguation is needed
        needs_disambig = False
        disambig_prompt = None

        # Don't disambiguate for compound requests - just execute primary first
        if not is_compound:
            if primary.confidence < self.CONFIDENCE_MEDIUM:
                # Low confidence - ask user
                needs_disambig = True
                disambig_prompt = self._create_disambiguation_prompt(
                    primary,
                    alternatives[:2]
                )
            elif len(alternatives) > 0 and alternatives[0].confidence >= self.CONFIDENCE_MEDIUM:
                # Check if they're really different intents or just variations
                if self._are_conflicting_intents(primary, alternatives[0]):
                    needs_disambig = True
                    disambig_prompt = self._create_disambiguation_prompt(
                        primary,
                        [alternatives[0]]
                    )

        return ToolSelectionResult(
            primary_tool=primary,
            alternative_tools=alternatives,
            needs_disambiguation=needs_disambig,
            disambiguation_prompt=disambig_prompt,
            compound_request=is_compound
        )

    def _detect_compound_patterns(self, msg_lower: str) -> bool:
        """
        Detect if message contains compound request patterns like:
        - "play music and turn on the lights"
        - "check email then search for..."
        - "first do X, then do Y"
        """
        compound_connectors = [
            ' and ', ' then ', ' after that ', ' also ', ' plus ',
            ', and ', ', then ', ' followed by ', ' and also ',
            ' first ', ' second ', ' next '
        ]
        
        # Check for connectors that suggest multiple actions
        has_connector = any(conn in msg_lower for conn in compound_connectors)
        
        # Check for explicit multi-action patterns
        multi_patterns = [
            r'(?:play|put on).*(?:and|then).*(?:light|turn)',
            r'(?:check|read).*(?:and|then).*(?:search|find)',
            r'(?:turn|set).*(?:and|then).*(?:play|music)',
            r'(?:send|email).*(?:and|then).*(?:remind|timer)',
        ]
        
        has_multi_pattern = any(re.search(pat, msg_lower) for pat in multi_patterns)
        
        return has_connector and has_multi_pattern
    
    def _are_conflicting_intents(self, intent1: ToolIntent, intent2: ToolIntent) -> bool:
        """
        Check if two intents are genuinely conflicting (need disambiguation)
        vs just being different aspects of the same request.
        """
        # Same tool = not conflicting
        if intent1.tool_name == intent2.tool_name:
            return False
        
        # Related tools that shouldn't conflict
        related_groups = [
            {'read_gmail', 'send_gmail', 'reply_gmail'},  # All email
            {'play_music', 'control_music', 'music_visualizer'},  # All music
            {'web_search', 'browse_website'},  # All web
            {'control_lights', 'music_visualizer'},  # Can coexist
            {'set_timer', 'create_reminder'},  # Both time-based
        ]
        
        for group in related_groups:
            if intent1.tool_name in group and intent2.tool_name in group:
                # Within same group - might still conflict
                # Email read vs send is a real conflict
                if {intent1.tool_name, intent2.tool_name} == {'read_gmail', 'send_gmail'}:
                    return True
                if {intent1.tool_name, intent2.tool_name} == {'read_gmail', 'reply_gmail'}:
                    return True
                # play_music vs control_music is a real conflict
                if {intent1.tool_name, intent2.tool_name} == {'play_music', 'control_music'}:
                    return True
                return False
        
        # Different categories - check confidence gap
        confidence_gap = abs(intent1.confidence - intent2.confidence)
        if confidence_gap > 0.2:
            return False  # Clear winner
        
        return True  # Genuinely ambiguous

    def _detect_all_intents(
        self,
        message: str,
        history: List[Dict]
    ) -> List[ToolIntent]:
        """
        Detect all possible tool intents with confidence scores.
        Returns empty list if greeting/casual chat detected (no tool needed).
        """
        intents = []
        msg_lower = message.lower().strip()

        # FIRST: Check if this is a greeting or casual chat (NO TOOL NEEDED)
        if self._is_greeting_or_casual(msg_lower):
            return []  # Return empty - let model respond naturally

        # Get context from history
        context = self._extract_context(history)

        # Check each tool type - ORDER MATTERS (priority)
        intents.extend(self._detect_camera_intents(msg_lower, context))
        intents.extend(self._detect_view_image_intents(msg_lower, context))
        intents.extend(self._detect_gmail_intents(msg_lower, context))
        intents.extend(self._detect_music_intents(msg_lower, context))
        intents.extend(self._detect_timer_reminder_intents(msg_lower, context))
        intents.extend(self._detect_document_intents(msg_lower, context))
        intents.extend(self._detect_web_intents(msg_lower, context))
        intents.extend(self._detect_light_intents(msg_lower, context))
        intents.extend(self._detect_utility_intents(msg_lower, context))

        return intents

    def _is_greeting_or_casual(self, msg_lower: str) -> bool:
        """
        Detect if message is a greeting or casual chat that needs no tool.
        v6 ENHANCED: More patterns, time-aware greetings
        """
        # Pure greetings
        greetings = [
            'hi', 'hello', 'hey', 'hi blue', 'hello blue', 'hey blue',
            'good morning', 'good afternoon', 'good evening', 'good night',
            'howdy', 'yo', 'sup', "what's up", 'whats up', 'hiya',
            'morning', 'afternoon', 'evening', 'greetings', 'salutations',
            'hey there', 'hi there', 'hello there', "what's good", 'whats good',
            'aloha', 'bonjour', 'hola', 'ciao', 'g\'day', 'ahoy'
        ]
        stripped = msg_lower.strip().rstrip('!.,?')
        if stripped in greetings:
            return True
        
        # Casual questions about Blue
        casual_about_blue = [
            'who are you', 'what are you', 'what can you do', 
            'how are you', "how's it going", 'how do you feel',
            'are you there', 'you there', 'blue are you there',
            'what is your name', "what's your name", 'can you hear me',
            'are you listening', 'you awake', 'are you awake',
            'what are you doing', 'how are you doing', "how's life",
            'how have you been', 'what have you been up to'
        ]
        if any(phrase in msg_lower for phrase in casual_about_blue):
            return True
        
        # Jokes, stories, opinions (no tool needed)
        casual_requests = [
            'tell me a joke', 'tell a joke', 'make me laugh',
            'tell me a story', 'sing a song', 'say something funny',
            'what do you think', 'your opinion', 'do you like',
            'thank you', 'thanks', 'great job', 'good job', 'nice',
            'never mind', 'nevermind', 'forget it', 'cancel',
            'you rock', 'awesome', 'cool', 'nice one', 'well done',
            'i love you', 'you are great', 'you are awesome',
            'good bot', 'bad bot', 'stupid bot', 'smart bot'
        ]
        if any(phrase in msg_lower for phrase in casual_requests):
            return True
        
        # Affirmations and confirmations
        affirmations = ['yes', 'no', 'ok', 'okay', 'sure', 'yep', 'nope', 
                        'yeah', 'nah', 'fine', 'alright', 'sounds good',
                        'got it', 'understood', 'i see', 'makes sense']
        if stripped in affirmations:
            return True
        
        # Very short messages that are likely casual
        if len(msg_lower) < 4 and msg_lower not in ['play', 'stop', 'next', 'skip', 'mute', 'off', 'on']:
            return True
        
        return False

    def _detect_view_image_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect intent to view an UPLOADED image (not camera capture).
        """
        intents = []
        
        # Strong signals for viewing uploaded images
        view_signals = [
            'show me the image', 'view the image', 'open the image',
            'show me the photo', 'view the photo', 'look at the photo',
            'show me the picture', 'view the picture', 'look at the picture',
            'show the screenshot', 'view the screenshot', 'look at the screenshot',
            'show the diagram', 'view the diagram', 'look at the diagram',
            'what is in the image', "what's in the image", 'analyze the image',
            'what does the image show', 'describe the image',
            'uploaded image', 'the image i uploaded', 'image i sent'
        ]
        
        # Check for specific image file extensions
        img_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff']
        has_img_file = any(ext in msg_lower for ext in img_extensions)
        
        # Check for view signals
        has_view_signal = any(sig in msg_lower for sig in view_signals)
        
        # "show me" + image-related word
        show_image = ('show me' in msg_lower or 'show the' in msg_lower) and \
                     any(w in msg_lower for w in ['image', 'photo', 'picture', 'screenshot', 'diagram'])
        
        if has_img_file:
            # Extract filename
            import re
            filename_match = re.search(r'[\w\-\.]+\.(jpg|jpeg|png|gif|webp|bmp|tiff)', msg_lower)
            filename = filename_match.group(0) if filename_match else None
            intents.append(ToolIntent(
                tool_name='view_image',
                confidence=0.95,
                priority=2,  # High priority
                reason='image filename detected',
                extracted_params={'filename': filename}
            ))
        elif has_view_signal or show_image:
            # Don't confuse with camera - check for "uploaded", "sent", specific file refs
            if any(w in msg_lower for w in ['uploaded', 'sent', 'attached', 'the image', 'this image']):
                intents.append(ToolIntent(
                    tool_name='view_image',
                    confidence=0.88,
                    priority=2,
                    reason='view uploaded image signal',
                    extracted_params={'query': msg_lower}
                ))
            elif context.get('has_image_in_history'):
                intents.append(ToolIntent(
                    tool_name='view_image',
                    confidence=0.75,
                    priority=2,
                    reason='view image + image in context',
                    extracted_params={'query': msg_lower}
                ))
        
        return intents

    def _detect_timer_reminder_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect timer and reminder intents.
        """
        intents = []
        
        # TIMER signals
        timer_signals = [
            'set a timer', 'set timer', 'start a timer', 'start timer',
            'timer for', 'countdown', 'count down',
            'minutes timer', 'minute timer', 'second timer'
        ]
        timer_patterns = [
            r'(\d+)\s*(minute|min|second|sec|hour)',
            r'timer\s+(?:for\s+)?(\d+)',
        ]
        
        has_timer_signal = any(sig in msg_lower for sig in timer_signals)
        has_timer_pattern = any(re.search(pat, msg_lower) for pat in timer_patterns)
        
        if has_timer_signal or has_timer_pattern:
            # Extract duration
            duration = 5  # default
            for pat in timer_patterns:
                match = re.search(pat, msg_lower)
                if match:
                    duration = int(match.group(1))
                    if 'hour' in msg_lower:
                        duration *= 60
                    break
            
            intents.append(ToolIntent(
                tool_name='set_timer',
                confidence=0.95,
                priority=3,
                reason='timer signal detected',
                extracted_params={'duration_minutes': duration}
            ))
        
        # REMINDER signals
        reminder_signals = [
            'remind me', 'set a reminder', 'set reminder', 'create a reminder',
            'reminder to', 'reminder for', "don't let me forget", 'dont let me forget'
        ]
        
        if any(sig in msg_lower for sig in reminder_signals):
            # Extract when and what
            when = 'in 1 hour'  # default
            title = msg_lower
            
            # Try to extract time
            time_patterns = [
                (r'in (\d+)\s*(minute|min|hour|day)', 'relative'),
                (r'at (\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', 'absolute'),
                (r'(tomorrow|tonight|this evening|this afternoon)', 'named')
            ]
            for pat, ptype in time_patterns:
                match = re.search(pat, msg_lower)
                if match:
                    when = match.group(0)
                    break
            
            intents.append(ToolIntent(
                tool_name='create_reminder',
                confidence=0.92,
                priority=3,
                reason='reminder signal detected',
                extracted_params={'title': title[:50], 'when': when, 'user_name': 'Alex'}
            ))
        
        # CHECK reminders
        check_reminder_signals = [
            'my reminders', 'what reminders', 'any reminders', 'upcoming reminders',
            'check reminders', 'show reminders', 'list reminders'
        ]
        if any(sig in msg_lower for sig in check_reminder_signals):
            intents.append(ToolIntent(
                tool_name='get_upcoming_reminders',
                confidence=0.90,
                priority=3,
                reason='check reminders signal',
                extracted_params={'user_name': 'Alex'}
            ))
        
        return intents

    def _extract_context(self, history: List[Dict]) -> Dict:
        """
        Extract relevant context from conversation history with topic decay.
        More recent mentions get higher weight.
        """
        context = {
            'recent_tools': [],
            'recent_topics': set(),
            'last_user_query': '',
            'has_email_in_history': False,
            'has_document_in_history': False,
            'has_music_in_history': False,
            'has_image_in_history': False,
            'has_lights_in_history': False,
            'has_weather_in_history': False,
            'email_recency': 0,      # 0 = not mentioned, higher = more recent
            'music_recency': 0,
            'document_recency': 0,
            'last_tool_used': None,
            'last_tool_success': None,
            'conversation_topic': None,
            'pending_action': None,   # For multi-step operations like fanmail
        }

        # Look at last 7 messages with recency weighting
        recent_msgs = history[-7:] if len(history) >= 7 else history
        
        for idx, msg in enumerate(recent_msgs):
            role = msg.get('role', '')
            content = msg.get('content', '').lower()
            recency = idx + 1  # 1 = oldest in window, 7 = most recent
            
            if role == 'tool':
                # Extract tool name if present
                tool_match = re.search(r'tool[:\s]+(\w+)', content)
                if tool_match:
                    tool_name = tool_match.group(1)
                    context['recent_tools'].append(tool_name)
                    context['last_tool_used'] = tool_name
                    
                    # Check for success/failure
                    if '"success": true' in content or 'success' in content.lower():
                        context['last_tool_success'] = True
                    elif '"success": false' in content or 'error' in content.lower():
                        context['last_tool_success'] = False

            # Track topics with recency weighting
            if 'email' in content or 'gmail' in content or 'inbox' in content:
                context['has_email_in_history'] = True
                context['email_recency'] = max(context['email_recency'], recency)
                
            if 'document' in content or 'file' in content or 'pdf' in content or 'contract' in content:
                context['has_document_in_history'] = True
                context['document_recency'] = max(context['document_recency'], recency)
                
            if 'music' in content or 'song' in content or 'play' in content or 'spotify' in content:
                context['has_music_in_history'] = True
                context['music_recency'] = max(context['music_recency'], recency)
            
            if 'image' in content or 'photo' in content or 'picture' in content or '.jpg' in content or '.png' in content:
                context['has_image_in_history'] = True
            
            if 'light' in content or 'lamp' in content or 'bright' in content or 'dim' in content:
                context['has_lights_in_history'] = True
            
            if 'weather' in content or 'temperature' in content or 'rain' in content or 'forecast' in content:
                context['has_weather_in_history'] = True

            if role == 'user':
                context['last_user_query'] = content
                
                # Detect pending multi-step operations
                if 'fanmail' in content and ('reply' in content or 'respond' in content):
                    context['pending_action'] = 'fanmail_reply'
                elif 'send' in content and 'email' in content:
                    context['pending_action'] = 'send_email'
            
            # Track conversation topic from assistant responses
            if role == 'assistant':
                if 'email' in content and ('sent' in content or 'inbox' in content):
                    context['conversation_topic'] = 'email'
                elif 'playing' in content or 'music' in content:
                    context['conversation_topic'] = 'music'
                elif 'document' in content or 'file' in content:
                    context['conversation_topic'] = 'documents'
                elif 'light' in content or 'mood' in content:
                    context['conversation_topic'] = 'lights'

        return context

    def _detect_camera_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect camera/vision intents - HIGHEST PRIORITY.
        Always triggers fresh capture, never uses cached images.
        """
        intents = []

        # Strong camera triggers
        camera_triggers = [
            'what do you see', 'what can you see', 'what are you looking at',
            "what's in front of you", "what is in front of you",
            'look around', 'take a photo', 'take a picture',
            'show me what you see', 'capture', 'what do you notice',
            "what's there", "what is there", "who do you see",
            "what's happening", "describe what you see"
        ]

        # Direct match - very high confidence
        if any(trigger in msg_lower for trigger in camera_triggers):
            intents.append(ToolIntent(
                tool_name='capture_camera',
                confidence=0.98,
                priority=1,  # Highest priority
                reason='Direct camera/vision request',
                extracted_params={}
            ))
        # "see" with question words
        elif 'see' in msg_lower and any(q in msg_lower for q in ['what', 'can you', 'do you']):
            intents.append(ToolIntent(
                tool_name='capture_camera',
                confidence=0.92,
                priority=1,
                reason='Vision query detected',
                extracted_params={}
            ))
        # "look" without other context
        elif 'look' in msg_lower and 'look up' not in msg_lower and 'look for' not in msg_lower:
            if any(w in msg_lower for w in ['around', 'here', 'there', 'at this']):
                intents.append(ToolIntent(
                    tool_name='capture_camera',
                    confidence=0.88,
                    priority=1,
                    reason='Look around request',
                    extracted_params={}
                ))

        return intents

    def _detect_gmail_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect Gmail-related intents with high precision.
        """
        intents = []

        # READ Gmail
        read_signals = {
            'strong': [
                'check my email', 'check email', 'check my inbox', 'read my email',
                'show my inbox', 'any new email', 'unread email', 'recent email'
            ],
            'medium': ['check', 'read', 'show', 'see'],
            'weak': ['email', 'inbox', 'message']
        }

        read_confidence = 0.0
        read_reason = []

        # Strong signals = high confidence
        if any(signal in msg_lower for signal in read_signals['strong']):
            read_confidence = 0.95
            read_reason.append("explicit read keywords")

        # Medium signals need email context
        elif any(verb in msg_lower for verb in read_signals['medium']):
            if any(noun in msg_lower for noun in read_signals['weak']):
                read_confidence = 0.80
                read_reason.append("read verb + email noun")
            elif context.get('has_email_in_history'):
                read_confidence = 0.70
                read_reason.append("read verb + email context")

        # Weak signals need strong context
        elif any(noun in msg_lower for noun in read_signals['weak']):
            if context.get('has_email_in_history'):
                read_confidence = 0.50
                read_reason.append("email noun + conversation context")

        # Exclude if sending or replying
        if 'send' in msg_lower or 'reply' in msg_lower or 'respond' in msg_lower:
            read_confidence = max(0, read_confidence - 0.4)
            read_reason.append("reduced: send/reply detected")

        if read_confidence > 0:
            intents.append(ToolIntent(
                tool_name='read_gmail',
                confidence=read_confidence,
                priority=self.PRIORITY_CRITICAL,
                reason=' | '.join(read_reason),
                extracted_params=self._extract_gmail_read_params(msg_lower)
            ))

        # SEND Gmail
        send_signals = {
            'strong': [
                'send email to', 'send an email', 'email to', 'compose email',
                'send to', 'write email to', 'send them an email'
            ],
            'medium': ['send', 'compose', 'draft']
        }

        send_confidence = 0.0
        send_reason = []

        if any(signal in msg_lower for signal in send_signals['strong']):
            send_confidence = 0.95
            send_reason.append("explicit send keywords")

            # Boost if email address detected
            if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', msg_lower):
                send_confidence = min(1.0, send_confidence + 0.05)
                send_reason.append("email address found")

        elif any(verb in msg_lower for verb in send_signals['medium']):
            if 'email' in msg_lower or 'message' in msg_lower:
                send_confidence = 0.75
                send_reason.append("send verb + email context")

        # Exclude if reading
        if any(word in msg_lower for word in ['check', 'read', 'show my']):
            send_confidence = max(0, send_confidence - 0.3)
            send_reason.append("reduced: read indicators")

        if send_confidence > 0:
            intents.append(ToolIntent(
                tool_name='send_gmail',
                confidence=send_confidence,
                priority=self.PRIORITY_CRITICAL,
                reason=' | '.join(send_reason),
                extracted_params=self._extract_gmail_send_params(msg_lower)
            ))

        # REPLY Gmail
        reply_signals = {
            'strong': [
                'reply to', 'respond to', 'reply to all', 'send a reply',
                'write a reply', 'answer the email', 'reply to email'
            ],
            'medium': ['reply', 'respond', 'answer']
        }

        reply_confidence = 0.0
        reply_reason = []

        if any(signal in msg_lower for signal in reply_signals['strong']):
            reply_confidence = 0.95
            reply_reason.append("explicit reply keywords")
        elif any(verb in msg_lower for verb in reply_signals['medium']):
            if any(noun in msg_lower for noun in ['email', 'message', 'inbox']):
                reply_confidence = 0.80
                reply_reason.append("reply verb + email context")

        if reply_confidence > 0:
            intents.append(ToolIntent(
                tool_name='reply_gmail',
                confidence=reply_confidence,
                priority=self.PRIORITY_CRITICAL,
                reason=' | '.join(reply_reason),
                extracted_params=self._extract_gmail_reply_params(msg_lower)
            ))

        return intents

    def _detect_music_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect music-related intents with comprehensive artist/genre recognition.
        ENHANCED v6: 200+ artists, 60+ genres, fuzzy matching
        """
        intents = []

        # PLAY music signals
        play_signals = ['play', 'put on', 'start playing', 'queue up', 'listen to', 'throw on', 
                       'blast', 'spin', 'crank up', 'hit me with']
        music_nouns = ['music', 'song', 'artist', 'album', 'track', 'playlist', 'tune', 'jam',
                      'tunes', 'jams', 'beats', 'banger', 'anthem']
        
        # Comprehensive genres (60+)
        genres = [
            # Main genres
            'jazz', 'rock', 'pop', 'classical', 'hip hop', 'hiphop', 'rap', 'country', 'r&b', 'rnb',
            'electronic', 'edm', 'house', 'techno', 'indie', 'alternative', 'alt', 'metal',
            'punk', 'blues', 'soul', 'funk', 'reggae', 'folk', 'ambient', 'lo-fi', 'lofi',
            'latin', 'salsa', 'k-pop', 'kpop', 'j-pop', 'jpop', 'disco', 'gospel', 'opera',
            'soundtrack', 'ost', 'instrumental', 'acoustic', 'chill', 'relaxing', 'upbeat',
            'workout', 'party', 'focus', 'sleep', 'study', 'meditation',
            # Subgenres
            'grunge', 'shoegaze', 'post-rock', 'prog rock', 'progressive', 'psychedelic',
            'death metal', 'black metal', 'thrash', 'hardcore', 'emo', 'screamo',
            'trap', 'drill', 'grime', 'dubstep', 'drum and bass', 'dnb', 'trance',
            'deep house', 'tropical house', 'future bass', 'synthwave', 'retrowave',
            'bossa nova', 'samba', 'flamenco', 'afrobeat', 'afrobeats', 'dancehall',
            'ska', 'dub', 'new wave', 'synth pop', 'synthpop', 'dream pop',
            'neo soul', 'motown', 'doo wop', 'swing', 'big band', 'bebop',
            'bluegrass', 'americana', 'outlaw country', 'honky tonk',
            'gregorian', 'baroque', 'romantic', 'contemporary classical',
            'chillhop', 'vaporwave', 'city pop'
        ]
        
        # Comprehensive artists (200+)
        artists = [
            # Classic Rock / Rock
            'beatles', 'the beatles', 'queen', 'led zeppelin', 'pink floyd', 'rolling stones',
            'the rolling stones', 'ac/dc', 'acdc', 'nirvana', 'foo fighters', 'u2', 'coldplay',
            'radiohead', 'oasis', 'green day', 'linkin park', 'red hot chili peppers', 'rhcp',
            'guns n roses', 'gnr', 'bon jovi', 'aerosmith', 'metallica', 'iron maiden',
            'black sabbath', 'deep purple', 'the who', 'the doors', 'cream', 'jethro tull',
            'rush', 'yes', 'genesis', 'king crimson', 'tool', 'system of a down', 'soad',
            'rage against the machine', 'ratm', 'pearl jam', 'soundgarden', 'alice in chains',
            'stone temple pilots', 'weezer', 'blink 182', 'blink-182', 'sum 41', 'the offspring',
            'muse', 'arctic monkeys', 'the strokes', 'kings of leon', 'imagine dragons',
            'twenty one pilots', 'panic at the disco', 'fall out boy', 'my chemical romance', 'mcr',
            'paramore', 'evanescence', 'three days grace', 'breaking benjamin', 'disturbed',
            'five finger death punch', 'ffdp', 'slipknot', 'korn', 'limp bizkit', 'deftones',
            
            # Pop
            'taylor swift', 'ed sheeran', 'adele', 'bruno mars', 'ariana grande', 'dua lipa',
            'billie eilish', 'the weeknd', 'harry styles', 'olivia rodrigo', 'doja cat',
            'lady gaga', 'beyonce', 'rihanna', 'katy perry', 'justin bieber', 'shawn mendes',
            'post malone', 'halsey', 'sia', 'charlie puth', 'maroon 5', 'one direction', '1d',
            'bts', 'blackpink', 'twice', 'stray kids', 'seventeen', 'exo', 'nct', 'red velvet',
            'newjeans', 'aespa', 'itzy', 'le sserafim', 'ive',
            'selena gomez', 'miley cyrus', 'demi lovato', 'nick jonas', 'jonas brothers',
            'camila cabello', 'fifth harmony', 'little mix', 'lizzo', 'meghan trainor',
            'lorde', 'troye sivan', 'conan gray', 'gracie abrams', 'sabrina carpenter',
            'tate mcrae', 'dove cameron', 'madison beer', 'ava max', 'bebe rexha',
            
            # Hip Hop / Rap
            'drake', 'kendrick lamar', 'kanye', 'kanye west', 'jay-z', 'jay z', 'eminem',
            'travis scott', 'j cole', 'j. cole', 'lil nas x', 'megan thee stallion',
            'cardi b', 'nicki minaj', 'tyler the creator', 'asap rocky', 'a$ap rocky',
            'future', '21 savage', 'juice wrld', 'xxxtentacion', 'xxx', 'mac miller',
            'logic', 'chance the rapper', 'childish gambino', 'donald glover',
            'lil uzi vert', 'lil baby', 'dababy', 'rod wave', 'polo g', 'lil durk',
            'young thug', 'gunna', 'lil wayne', '50 cent', 'snoop dogg', 'dr dre',
            'ice cube', 'nas', 'tupac', '2pac', 'biggie', 'notorious big', 'wu-tang',
            'outkast', 'andre 3000', 'missy elliott', 'lauryn hill', 'fugees',
            'a tribe called quest', 'atcq', 'de la soul', 'run dmc', 'beastie boys',
            'kid cudi', 'pharrell', 'pusha t', 'jack harlow', 'central cee', 'ice spice',
            
            # R&B / Soul
            'frank ocean', 'sza', 'daniel caesar', 'h.e.r.', 'jhene aiko', 'summer walker',
            'usher', 'chris brown', 'alicia keys', 'john legend', 'miguel', 'khalid',
            'the weeknd', 'bryson tiller', 'kehlani', 'ari lennox', 'giveon', 'brent faiyaz',
            'steve lacy', 'blood orange', 'anderson paak', 'silk sonic', 'victoria monet',
            'brandy', 'monica', 'mary j blige', 'erykah badu', 'dangelo', 'maxwell',
            'babyface', 'boyz ii men', 'jodeci', 'new edition', 'tlc', 'destiny\'s child',
            'jagged edge', 'dru hill', '112', 'ginuwine', 'aaliyah', 'ashanti', 'keyshia cole',
            
            # Electronic / EDM
            'daft punk', 'deadmau5', 'skrillex', 'marshmello', 'calvin harris', 'avicii',
            'kygo', 'zedd', 'martin garrix', 'tiesto', 'david guetta', 'diplo',
            'major lazer', 'the chainsmokers', 'flume', 'odesza', 'porter robinson',
            'madeon', 'illenium', 'seven lions', 'above and beyond', 'armin van buuren',
            'kaskade', 'steve aoki', 'hardwell', 'afrojack', 'nicky romero',
            'excision', 'subtronics', 'rezz', 'griz', 'big wild', 'rufus du sol',
            'disclosure', 'kaytranada', 'four tet', 'jamie xx', 'bonobo', 'tycho',
            'boards of canada', 'aphex twin', 'burial', 'flying lotus', 'amon tobin',
            
            # Country
            'luke combs', 'morgan wallen', 'chris stapleton', 'luke bryan', 'blake shelton',
            'carrie underwood', 'dolly parton', 'johnny cash', 'willie nelson', 'waylon jennings',
            'garth brooks', 'george strait', 'alan jackson', 'kenny chesney', 'tim mcgraw',
            'faith hill', 'shania twain', 'reba mcentire', 'miranda lambert', 'kacey musgraves',
            'maren morris', 'kelsea ballerini', 'carly pearce', 'lainey wilson', 'zach bryan',
            'tyler childers', 'sturgill simpson', 'jason isbell', 'colter wall', 'charley crockett',
            
            # Jazz / Blues
            'miles davis', 'john coltrane', 'louis armstrong', 'ella fitzgerald',
            'duke ellington', 'charlie parker', 'thelonious monk', 'dizzy gillespie',
            'billie holiday', 'nina simone', 'nat king cole', 'sarah vaughan',
            'chet baker', 'dave brubeck', 'herbie hancock', 'chick corea', 'pat metheny',
            'bb king', 'b.b. king', 'muddy waters', 'howlin wolf', 'john lee hooker',
            'robert johnson', 'stevie ray vaughan', 'srv', 'eric clapton', 'buddy guy',
            'joe bonamassa', 'gary clark jr', 'john mayer', 'kamasi washington',
            
            # Classical
            'beethoven', 'mozart', 'bach', 'chopin', 'vivaldi', 'tchaikovsky',
            'brahms', 'schubert', 'handel', 'haydn', 'liszt', 'mendelssohn',
            'debussy', 'ravel', 'stravinsky', 'rachmaninoff', 'mahler', 'wagner',
            'dvorak', 'sibelius', 'grieg', 'verdi', 'puccini', 'rossini',
            'yo-yo ma', 'itzhak perlman', 'lang lang', 'martha argerich', 'andras schiff',
            
            # Legends / Legacy
            'michael jackson', 'mj', 'prince', 'whitney houston', 'elton john', 'david bowie',
            'madonna', 'stevie wonder', 'fleetwood mac', 'abba', 'eagles', 'dire straits',
            'bob marley', 'bob dylan', 'jimi hendrix', 'eric clapton', 'santana',
            'james brown', 'aretha franklin', 'ray charles', 'marvin gaye', 'otis redding',
            'sam cooke', 'al green', 'barry white', 'diana ross', 'supremes', 'temptations',
            'four tops', 'smokey robinson', 'ike turner', 'tina turner', 'chuck berry',
            'little richard', 'fats domino', 'buddy holly', 'elvis', 'elvis presley',
            'frank sinatra', 'dean martin', 'sammy davis jr', 'tony bennett', 'bing crosby',
            'bee gees', 'earth wind fire', 'earth wind and fire', 'ewf', 'kool and the gang',
            'commodores', 'lionel richie', 'phil collins', 'peter gabriel', 'sting', 'police',
            'talking heads', 'blondie', 'duran duran', 'depeche mode', 'new order', 'the cure',
            'joy division', 'the smiths', 'morrissey', 'r.e.m.', 'rem', 'pixies', 'sonic youth',
            
            # Modern Indie / Alternative
            'tame impala', 'mgmt', 'vampire weekend', 'bon iver', 'fleet foxes', 'iron and wine',
            'the national', 'interpol', 'modest mouse', 'death cab for cutie', 'the shins',
            'the decemberists', 'arcade fire', 'lcd soundsystem', 'st vincent', 'phoebe bridgers',
            'japanese breakfast', 'snail mail', 'soccer mommy', 'boygenius', 'big thief',
            'beach house', 'grizzly bear', 'animal collective', 'of montreal', 'neutral milk hotel',
            'sufjan stevens', 'andrew bird', 'father john misty', 'the war on drugs', 'kurt vile',
            'mac demarco', 'rex orange county', 'boy pablo', 'cavetown', 'girl in red',
            'clairo', 'beabadoobee', 'wallows', 'dayglow', 'still woozy', 'dominic fike',
            
            # Latin
            'bad bunny', 'j balvin', 'daddy yankee', 'ozuna', 'maluma', 'anuel aa',
            'rauw alejandro', 'karol g', 'becky g', 'nicky jam', 'farruko', 'sech',
            'shakira', 'jennifer lopez', 'jlo', 'enrique iglesias', 'ricky martin',
            'luis fonsi', 'marc anthony', 'romeo santos', 'prince royce', 'juan luis guerra',
            'carlos vives', 'juanes', 'mana', 'soda stereo', 'cafe tacvba',
            'rosalia', 'c tangana', 'arca', 'peso pluma', 'fuerza regida', 'grupo frontera'
        ]
        
        # Check for direct artist/genre mention (exact match first)
        has_artist = any(artist in msg_lower for artist in artists)
        has_genre = any(genre in msg_lower for genre in genres)
        
        # v7 ENHANCEMENT: Fuzzy match for artist names (handles typos)
        matched_artist = None
        if not has_artist:
            # Try fuzzy matching on individual words
            words = msg_lower.split()
            for i in range(len(words)):
                # Try single words and pairs
                for length in [1, 2, 3]:
                    if i + length <= len(words):
                        phrase = ' '.join(words[i:i+length])
                        match = fuzzy_match(phrase, artists, threshold=0.8)
                        if match:
                            matched_artist = match
                            has_artist = True
                            break
                if has_artist:
                    break

        play_confidence = 0.0
        play_reason = []

        has_play = any(signal in msg_lower for signal in play_signals)
        has_music = any(noun in msg_lower for noun in music_nouns)

        # Direct "play [artist]" or "play [genre]"
        if has_play and (has_artist or has_genre):
            play_confidence = 0.98
            if matched_artist:
                play_reason.append(f"play + fuzzy matched artist: {matched_artist}")
            else:
                play_reason.append("play + artist/genre detected")
        elif has_play and has_music:
            # Check if it's about searching for info vs playing
            info_words = ['about', 'information', 'who is', 'what is', 'search for', 'tell me about', 'wiki']
            if any(word in msg_lower for word in info_words):
                play_confidence = 0.3
                play_reason.append("play+music but info request detected")
            else:
                play_confidence = 0.95
                play_reason.append("clear play + music intent")
        elif has_play and context.get('has_music_in_history'):
            play_confidence = 0.75
            play_reason.append("play verb with music context")
        elif has_music and any(word in msg_lower for word in ['play', 'start', 'queue']):
            play_confidence = 0.65
            play_reason.append("music noun with play indicators")
        # "put on some [genre]" or "put on [artist]"
        elif 'put on' in msg_lower and (has_artist or has_genre or has_music):
            play_confidence = 0.92
            play_reason.append("put on + music/artist/genre")
        # Direct artist mention without explicit play (e.g., "some Beatles")
        elif has_artist and any(w in msg_lower for w in ['some', 'little', 'bit of']):
            play_confidence = 0.85
            play_reason.append("artist + quantity word suggests play intent")
        # Just artist name with question context might be info request
        elif has_artist and not has_play:
            if any(w in msg_lower for w in ['who', 'what', 'when', 'where', 'how', 'tell me']):
                play_confidence = 0.2
                play_reason.append("artist mentioned but seems like info request")
            elif context.get('has_music_in_history'):
                play_confidence = 0.7
                play_reason.append("artist mentioned with music context")

        if play_confidence > 0:
            # Extract the query - remove play signals to get cleaner query
            query = msg_lower
            for sig in play_signals:
                query = query.replace(sig, '').strip()
            
            # Use the fuzzy-matched artist if found (more accurate)
            if matched_artist:
                query = matched_artist
            
            intents.append(ToolIntent(
                tool_name='play_music',
                confidence=play_confidence,
                priority=self.PRIORITY_HIGH,
                reason=' | '.join(play_reason),
                extracted_params={'query': query if query else msg_lower}
            ))

        # CONTROL music
        control_signals = [
            'pause', 'stop', 'resume', 'skip', 'next', 'previous', 'back',
            'volume up', 'volume down', 'mute', 'louder', 'quieter', 'softer',
            'turn it up', 'turn it down', 'next song', 'previous song',
            'skip this', 'play next', 'go back'
        ]

        control_confidence = 0.0
        control_reason = []

        if any(signal in msg_lower for signal in control_signals):
            # Very high confidence if music control word found
            control_confidence = 0.95
            control_reason.append("explicit control keyword")

            # Slightly lower if could be about other things
            if not has_music and not context.get('has_music_in_history') and context.get('music_recency', 0) < 3:
                control_confidence = 0.75
                control_reason.append("reduced: no recent music context")

        if control_confidence > 0:
            # Map control signals to actions
            action = 'pause'
            if 'skip' in msg_lower or 'next' in msg_lower:
                action = 'next'
            elif 'previous' in msg_lower or 'back' in msg_lower:
                action = 'previous'
            elif 'resume' in msg_lower:
                action = 'resume'
            elif 'stop' in msg_lower:
                action = 'pause'
            elif 'volume up' in msg_lower or 'louder' in msg_lower or 'turn it up' in msg_lower:
                action = 'volume_up'
            elif 'volume down' in msg_lower or 'quieter' in msg_lower or 'softer' in msg_lower or 'turn it down' in msg_lower:
                action = 'volume_down'
            elif 'mute' in msg_lower:
                action = 'mute'
            
            intents.append(ToolIntent(
                tool_name='control_music',
                confidence=control_confidence,
                priority=self.PRIORITY_HIGH,
                reason=' | '.join(control_reason),
                extracted_params={'action': action}
            ))

        # VISUALIZER
        visualizer_signals = [
            'light show', 'music visualizer', 'visualizer', 'dance with music',
            'sync lights', 'lights dance', 'party lights', 'make lights dance',
            'lights to the music', 'disco mode', 'rave mode', 'club lights'
        ]

        if any(signal in msg_lower for signal in visualizer_signals):
            intents.append(ToolIntent(
                tool_name='music_visualizer',
                confidence=0.95,
                priority=self.PRIORITY_HIGH,
                reason="explicit visualizer keywords",
                extracted_params={'action': 'start', 'duration': 300, 'style': 'party'}
            ))


        return intents

    def _detect_document_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect document-related intents with distinction between retrieval and search.
        """
        intents = []

        # SEARCH documents (RAG/semantic search)
        search_signals = {
            'strong': [
                'search my documents', 'search documents for', 'find in my documents',
                'what do my documents say', 'according to my documents',
                'in my documents about', 'search my files'
            ],
            'medium': ['search', 'find', 'look for']
        }

        doc_nouns = ['document', 'documents', 'file', 'files', 'pdf', 'contract']

        search_confidence = 0.0
        search_reason = []

        if any(signal in msg_lower for signal in search_signals['strong']):
            search_confidence = 0.95
            search_reason.append("explicit document search keywords")
        elif any(verb in msg_lower for verb in search_signals['medium']):
            if any(noun in msg_lower for noun in doc_nouns):
                if 'my' in msg_lower or 'our' in msg_lower:
                    search_confidence = 0.85
                    search_reason.append("search verb + possessive + document noun")
                else:
                    search_confidence = 0.70
                    search_reason.append("search verb + document noun")
            elif context.get('has_document_in_history'):
                search_confidence = 0.60
                search_reason.append("search verb + document context")

        # Questions about document content
        question_about_docs = (
            ('what' in msg_lower or 'how' in msg_lower) and
            any(noun in msg_lower for noun in doc_nouns)
        )
        if question_about_docs:
            search_confidence = max(search_confidence, 0.75)
            search_reason.append("question about document content")

        # Reduce if web search more likely
        if any(word in msg_lower for word in ['google', 'search online', 'search the web']):
            search_confidence = max(0, search_confidence - 0.4)
            search_reason.append("reduced: web search indicators")

        if search_confidence > 0:
            intents.append(ToolIntent(
                tool_name='search_documents',
                confidence=search_confidence,
                priority=self.PRIORITY_MEDIUM,
                reason=' | '.join(search_reason),
                extracted_params={'query': msg_lower[:100]}
            ))

        # CREATE document
        create_signals = {
            'strong': [
                'create a document', 'create a file', 'make a document',
                'write a document', 'save as a file', 'create a list',
                'make me a list', 'write me a list'
            ],
            'medium': ['create', 'make', 'write', 'save']
        }

        create_nouns = ['document', 'file', 'list', 'note', 'notes', 'recipe']

        create_confidence = 0.0
        create_reason = []

        if any(signal in msg_lower for signal in create_signals['strong']):
            create_confidence = 0.90
            create_reason.append("explicit creation keywords")
        elif any(verb in msg_lower for verb in create_signals['medium']):
            if any(noun in msg_lower for noun in create_nouns):
                create_confidence = 0.80
                create_reason.append("create verb + document noun")

        if create_confidence > 0:
            intents.append(ToolIntent(
                tool_name='create_document',
                confidence=create_confidence,
                priority=self.PRIORITY_MEDIUM,
                reason=' | '.join(create_reason),
                extracted_params=self._extract_document_create_params(msg_lower)
            ))

        return intents

    def _detect_web_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect web-related intents (search, browse).
        """
        intents = []

        # WEB SEARCH
        web_signals = {
            'strong': [
                'search the web', 'search online', 'google', 'search google',
                'look up online', 'search the internet', 'find on the web'
            ],
            'medium': ['search for', 'look up', 'find out about'],
            'temporal': ['latest', 'recent', 'current', 'today', 'this week']
        }

        search_confidence = 0.0
        search_reason = []

        if any(signal in msg_lower for signal in web_signals['strong']):
            search_confidence = 0.95
            search_reason.append("explicit web search keywords")
        elif any(phrase in msg_lower for phrase in web_signals['medium']):
            search_confidence = 0.75
            search_reason.append("generic search keywords")
        elif any(word in msg_lower for word in web_signals['temporal']):
            # Temporal words suggest current info needed
            if any(topic in msg_lower for topic in ['news', 'price', 'score', 'weather']):
                search_confidence = 0.85
                search_reason.append("temporal + news/price/etc")

        # Reduce if documents or JavaScript more likely
        doc_signals = ['my document', 'my file', 'my contract', 'my pdf', 
                       'our document', 'uploaded', 'my upload']
        if any(sig in msg_lower for sig in doc_signals):
            search_confidence = max(0, search_confidence - 0.6)
            search_reason.append("reduced: document reference")
        if 'run javascript' in msg_lower or 'execute code' in msg_lower:
            search_confidence = max(0, search_confidence - 0.8)
            search_reason.append("reduced: code execution intent")

        if search_confidence > 0:
            intents.append(ToolIntent(
                tool_name='web_search',
                confidence=search_confidence,
                priority=self.PRIORITY_LOW,
                reason=' | '.join(search_reason),
                extracted_params={'query': msg_lower}
            ))

        # BROWSE website
        browse_signals = [
            'browse', 'open', 'visit', 'go to', 'navigate to', 'load', 'fetch'
        ]

        # Check for URL but not email addresses
        has_email_addr = bool(re.search(r'\b[\w.-]+@[\w.-]+\.\w+\b', msg_lower))
        has_url = bool(re.search(r'https?://|www\.', msg_lower)) or \
                  (bool(re.search(r'\.(com|org|net)\b', msg_lower)) and not has_email_addr)
        has_browse_verb = any(verb in msg_lower for verb in browse_signals)

        browse_confidence = 0.0
        browse_reason = []

        if has_url:
            if has_browse_verb:
                browse_confidence = 0.95
                browse_reason.append("URL + browse verb")
            else:
                browse_confidence = 0.85
                browse_reason.append("URL detected")
        elif has_browse_verb and 'website' in msg_lower:
            browse_confidence = 0.75
            browse_reason.append("browse + website")

        if browse_confidence > 0:
            url_match = re.search(r'https?://\S+|www\.\S+|\b\w+\.(com|org|net)\b', msg_lower)
            url = url_match.group(0) if url_match else None

            intents.append(ToolIntent(
                tool_name='browse_website',
                confidence=browse_confidence,
                priority=self.PRIORITY_MEDIUM,
                reason=' | '.join(browse_reason),
                extracted_params={'url': url, 'extract': 'text'}
            ))

        return intents

    def _detect_light_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect light control intents with comprehensive mood/color support.
        """
        intents = []

        light_signals = {
            'nouns': ['light', 'lights', 'lamp', 'lamps', 'bulb', 'bulbs', 'hue'],
            'actions': ['turn on', 'turn off', 'switch on', 'switch off', 'set', 'change', 'dim', 'brighten', 'adjust'],
            'colors': [
                'red', 'blue', 'green', 'yellow', 'purple', 'orange', 'white', 'pink',
                'cyan', 'magenta', 'lime', 'teal', 'amber', 'violet', 'turquoise',
                'warm white', 'cool white', 'daylight', 'gold', 'coral', 'salmon'
            ],
            'moods': [
                'moonlight', 'sunset', 'ocean', 'forest', 'romance', 'party',
                'focus', 'relax', 'energize', 'movie', 'fireplace', 'arctic',
                'sunrise', 'galaxy', 'tropical', 'reading', 'dinner', 'night',
                'cozy', 'warm', 'cool', 'natural', 'romantic', 'chill', 'calm',
                'zen', 'meditation', 'spa', 'beach', 'campfire', 'candle', 'aurora',
                'rainbow', 'disco', 'club', 'concert', 'gaming', 'tv', 'sleep'
            ]
        }

        has_light = any(noun in msg_lower for noun in light_signals['nouns'])
        has_action = any(action in msg_lower for action in light_signals['actions'])
        has_color = any(color in msg_lower for color in light_signals['colors'])
        has_mood = any(mood in msg_lower for mood in light_signals['moods'])

        confidence = 0.0
        reason = []

        # Check for visualizer conflicts - "light show" should go to visualizer
        visualizer_phrases = ['light show', 'lights dance', 'sync lights', 'disco mode', 'party lights']
        if any(phrase in msg_lower for phrase in visualizer_phrases):
            # Let music visualizer handle this
            return intents

        if has_light and (has_action or has_color or has_mood):
            confidence = 0.95
            reason.append("light + action/color/mood")
        elif has_mood and not has_light:
            # Mood words alone suggest lights (e.g., "set it to sunset")
            # But check for music context
            if not context.get('has_music_in_history') and 'play' not in msg_lower:
                confidence = 0.85
                reason.append("mood keyword (implies lights)")
        elif has_color and ('set' in msg_lower or 'change' in msg_lower or 'make' in msg_lower):
            confidence = 0.88
            reason.append("color + set/change")
        elif has_light:
            confidence = 0.70
            reason.append("light noun mentioned")
            reason.append("light noun only")

        # Exclude visualizer intent
        if 'visualizer' in msg_lower or 'light show' in msg_lower:
            confidence = 0

        if confidence > 0:
            intents.append(ToolIntent(
                tool_name='control_lights',
                confidence=confidence,
                priority=self.PRIORITY_MEDIUM,
                reason=' | '.join(reason),
                extracted_params=self._extract_light_params(msg_lower)
            ))

        return intents

    def _detect_utility_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect utility tool intents (weather, JavaScript, etc).
        """
        intents = []

        # WEATHER
        weather_keywords = ['weather', 'forecast', 'temperature', 'rain', 'snow', 'sunny']
        if any(kw in msg_lower for kw in weather_keywords):
            # Extract location if present
            location_match = re.search(r'in ([A-Z][a-z]+)', msg_lower)
            location = location_match.group(1) if location_match else "Toronto"

            intents.append(ToolIntent(
                tool_name='get_weather',
                confidence=0.95,
                priority=self.PRIORITY_MEDIUM,
                reason="weather keyword detected",
                extracted_params={'location': location}
            ))

        # JAVASCRIPT
        js_signals = [
            'run javascript', 'execute javascript', 'run js', 'execute js',
            'run code', 'execute code', 'javascript tool'
        ]
        if any(signal in msg_lower for signal in js_signals):
            intents.append(ToolIntent(
                tool_name='run_javascript',
                confidence=0.95,
                priority=self.PRIORITY_HIGH,
                reason="explicit JavaScript keywords",
                extracted_params={'code': ''}  # To be filled by LLM
            ))

        return intents

    def _create_disambiguation_prompt(
        self,
        primary: ToolIntent,
        alternatives: List[ToolIntent]
    ) -> str:
        """
        Create a user-friendly disambiguation prompt with natural language.
        """
        # Map tool names to friendly descriptions
        tool_descriptions = {
            'read_gmail': 'check your inbox',
            'send_gmail': 'send a new email',
            'reply_gmail': 'reply to an existing email',
            'play_music': 'play some music',
            'control_music': 'control the current playback (pause/skip/volume)',
            'music_visualizer': 'start a light show',
            'web_search': 'search the internet',
            'search_documents': 'search your uploaded documents',
            'browse_website': 'open a website',
            'control_lights': 'adjust the lights',
            'capture_camera': 'look at what\'s in front of me',
            'view_image': 'look at an uploaded image',
            'create_document': 'create a new document',
            'get_weather': 'check the weather',
            'set_timer': 'set a timer',
            'create_reminder': 'create a reminder'
        }
        
        primary_desc = tool_descriptions.get(primary.tool_name, primary.tool_name)
        
        if alternatives:
            alt_descs = [tool_descriptions.get(alt.tool_name, alt.tool_name) for alt in alternatives]
            
            if len(alternatives) == 1:
                prompt = f"Just to make sure - would you like me to {primary_desc}, or {alt_descs[0]}?"
            else:
                alt_list = ', '.join(alt_descs[:-1]) + f', or {alt_descs[-1]}'
                prompt = f"I want to help! Did you mean for me to {primary_desc}, {alt_list}?"
        else:
            prompt = f"Just checking - would you like me to {primary_desc}?"
        
        return prompt

    # Parameter extraction helpers
    def _extract_gmail_read_params(self, msg_lower: str) -> Dict:
        params = {'query': '', 'max_results': 10, 'include_body': False}
        
        # Unread filter
        if 'unread' in msg_lower or 'new' in msg_lower:
            params['query'] = 'is:unread'
        
        # Sender filter
        from_match = re.search(r'from\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}|[A-Z][a-z]+)', msg_lower)
        if from_match:
            sender = from_match.group(1)
            if '@' in sender:
                params['query'] = f'from:{sender}'
            else:
                params['query'] = f'from:{sender}'
        
        # Subject filter
        subject_patterns = [
            r'(?:with |about |subject[: ]+)["\']?([^"\']+)["\']?',
            r'subject[:\s]+(\w+)',
            r'about\s+(\w+)'
        ]
        for pattern in subject_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                subject = match.group(1).strip()
                if len(subject) > 2:
                    if params['query']:
                        params['query'] += f' subject:{subject}'
                    else:
                        params['query'] = f'subject:{subject}'
                    break
        
        # Include body for detailed requests
        if any(w in msg_lower for w in ['full', 'body', 'content', 'detail', 'read', 'show']):
            params['include_body'] = True
        
        # Limit
        limit_match = re.search(r'(?:last|recent|top)\s+(\d+)', msg_lower)
        if limit_match:
            params['max_results'] = min(int(limit_match.group(1)), 50)
        
        return params

    def _extract_gmail_send_params(self, msg_lower: str) -> Dict:
        """
        Extract send email parameters from natural language.
        Handles patterns like:
        - "send email to bob@test.com about meeting saying see you tomorrow"
        - "email john@example.com tell him the project is done"
        - "send a message to alice@work.com subject: Update body: Here's the info"
        """
        params = {'to': '', 'subject': '', 'body': ''}
        
        # Extract email address
        email_match = re.search(r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b', msg_lower)
        if email_match:
            params['to'] = email_match.group(1)
        
        # Extract subject - look for "about X", "subject: X", "regarding X"
        subject_patterns = [
            r'(?:subject[:\s]+)["\']?([^"\']+?)["\']?(?:\s+(?:saying|body|message)|$)',
            r'(?:about|regarding)\s+([^,\.]+?)(?:\s+(?:saying|tell|body|message)|,|\.|\s+and\s+|$)',
            r'subject[:\s]+([^\n,\.]+)'
        ]
        for pattern in subject_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                subject = match.group(1).strip()
                # Clean up common trailing words
                subject = re.sub(r'\s+(saying|tell|and|body|message).*$', '', subject)
                if 2 < len(subject) < 100:
                    params['subject'] = subject.title()
                    break
        
        # Extract body - look for "saying X", "tell them X", "message: X", "body: X"
        body_patterns = [
            r'(?:saying|tell (?:them|him|her)|message[:\s]+|body[:\s]+)["\']?(.+?)["\']?$',
            r'(?:and (?:say|tell)[:\s]+)(.+?)$',
            r'(?:with (?:message|body)[:\s]+)(.+?)$'
        ]
        for pattern in body_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                body = match.group(1).strip()
                if len(body) > 2:
                    # Capitalize first letter
                    params['body'] = body[0].upper() + body[1:] if body else ''
                    break
        
        # If no explicit subject but have body, try to generate subject
        if not params['subject'] and params['body']:
            # Use first few words as subject
            words = params['body'].split()[:5]
            params['subject'] = ' '.join(words)
            if len(params['subject']) > 50:
                params['subject'] = params['subject'][:47] + '...'
        
        # Default subject if still empty
        if not params['subject'] and params['to']:
            params['subject'] = 'Message from Blue'
        
        return params

    def _extract_gmail_reply_params(self, msg_lower: str) -> Dict:
        params = {
            'query': '',
            'reply_body': '',
            'reply_all': 'reply to all' in msg_lower or 'reply all' in msg_lower
        }
        
        # Extract what to reply to
        if 'fanmail' in msg_lower:
            params['query'] = 'subject:Fanmail'
        elif 'unread' in msg_lower:
            params['query'] = 'is:unread'
        
        # From specific sender
        from_match = re.search(r'(?:from|to)\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', msg_lower)
        if from_match:
            params['query'] = f'from:{from_match.group(1)}'
        
        # Subject filter
        subject_match = re.search(r'(?:about|subject[:\s]+|with\s+)["\']?([^"\']+?)["\']?(?:\s+saying|$)', msg_lower)
        if subject_match and not params['query']:
            params['query'] = f'subject:{subject_match.group(1).strip()}'
        
        # Extract reply body
        body_patterns = [
            r'(?:saying|tell them|with message)[:\s]+["\']?(.+?)["\']?$',
            r'(?:and say)[:\s]+(.+?)$'
        ]
        for pattern in body_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                params['reply_body'] = match.group(1).strip()
                break
        
        return params

    def _extract_document_create_params(self, msg_lower: str) -> Dict:
        """Extract document creation parameters from natural language."""
        
        # Determine file type
        file_type = 'txt'
        if 'markdown' in msg_lower or '.md' in msg_lower:
            file_type = 'md'
        elif 'html' in msg_lower or 'webpage' in msg_lower:
            file_type = 'html'
        elif 'json' in msg_lower:
            file_type = 'json'
        elif 'csv' in msg_lower or 'spreadsheet' in msg_lower:
            file_type = 'csv'
        
        # Determine filename based on content type
        filename = 'document'
        doc_types = {
            'shopping': 'shopping_list',
            'grocery': 'grocery_list',
            'todo': 'todo_list',
            'to-do': 'todo_list',
            'task': 'task_list',
            'recipe': 'recipe',
            'note': 'notes',
            'notes': 'notes',
            'memo': 'memo',
            'letter': 'letter',
            'email draft': 'email_draft',
            'meeting': 'meeting_notes',
            'agenda': 'agenda',
            'summary': 'summary',
            'report': 'report',
            'outline': 'outline',
            'plan': 'plan',
            'schedule': 'schedule',
            'checklist': 'checklist',
            'packing': 'packing_list',
            'wishlist': 'wishlist',
            'wish list': 'wishlist',
            'bucket list': 'bucket_list',
            'reading list': 'reading_list',
            'movie list': 'movie_list',
            'playlist': 'playlist',
            'contact': 'contacts',
            'address': 'addresses',
            'inventory': 'inventory',
            'log': 'log',
            'journal': 'journal',
            'diary': 'diary'
        }
        
        for keyword, name in doc_types.items():
            if keyword in msg_lower:
                filename = name
                break
        
        # Try to extract custom filename
        filename_patterns = [
            r'(?:called|named|as)\s+["\']?([a-zA-Z0-9_\-\s]+)["\']?',
            r'save (?:it )?(?:as|to)\s+["\']?([a-zA-Z0-9_\-\s]+)["\']?',
            r'file[:\s]+["\']?([a-zA-Z0-9_\-\s]+)["\']?'
        ]
        for pattern in filename_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                custom_name = match.group(1).strip()
                if len(custom_name) > 1:
                    # Clean up the filename
                    filename = re.sub(r'[^\w\-]', '_', custom_name)
                    break
        
        # Add extension
        full_filename = f"{filename}.{file_type}"
        
        return {
            'filename': full_filename,
            'content': '',
            'file_type': file_type
        }

    def _extract_light_params(self, msg_lower: str) -> Dict:
        """Extract light control parameters from natural language. v6 ENHANCED."""
        params = {'action': 'status'}
        
        # All available moods/scenes (matches MOOD_PRESETS)
        moods = list(MOOD_PRESETS.keys()) if 'MOOD_PRESETS' in globals() else [
            # Nature
            'moonlight', 'sunset', 'sunrise', 'ocean', 'forest', 'tropical', 
            'arctic', 'galaxy', 'aurora', 'thunderstorm', 'beach', 'desert', 'rainforest',
            # Activities
            'focus', 'relax', 'energize', 'reading', 'movie', 'gaming', 'workout',
            'yoga', 'meditation', 'cooking', 'dinner', 'sleep', 'wakeup',
            # Moods
            'romance', 'party', 'cozy', 'fireplace', 'candle', 'zen', 'spa',
            'club', 'disco', 'concert', 'chill', 'warm', 'cool', 'bright', 'dim', 'night', 'natural',
            # Holidays
            'christmas', 'halloween', 'valentines', 'easter', 'july4', 'stpatricks', 'hanukkah', 'newyear',
            # Colors
            'red', 'blue', 'green', 'purple', 'orange', 'yellow', 'pink', 'cyan', 'white', 'rainbow'
        ]
        
        # Color mappings with hue values
        color_map = {
            'red': {'hue': 0, 'sat': 254},
            'orange': {'hue': 5000, 'sat': 254},
            'yellow': {'hue': 10000, 'sat': 254},
            'lime': {'hue': 18000, 'sat': 254},
            'green': {'hue': 25500, 'sat': 254},
            'teal': {'hue': 30000, 'sat': 254},
            'cyan': {'hue': 35000, 'sat': 254},
            'blue': {'hue': 46920, 'sat': 254},
            'purple': {'hue': 50000, 'sat': 254},
            'violet': {'hue': 52000, 'sat': 254},
            'magenta': {'hue': 54000, 'sat': 254},
            'pink': {'hue': 56100, 'sat': 200},
            'white': {'ct': 250},
            'warm white': {'ct': 400},
            'cool white': {'ct': 200},
            'daylight': {'ct': 250},
            'amber': {'hue': 6000, 'sat': 254},
            'gold': {'hue': 8000, 'sat': 200},
        }
        
        # Light name patterns
        light_names = ['bedroom', 'living room', 'kitchen', 'bathroom', 'office', 
                       'hallway', 'dining', 'garage', 'basement', 'attic', 'porch',
                       'den', 'study', 'nursery', 'guest', 'master', 'lamp', 'strip']
        
        # Check for on/off first
        if any(w in msg_lower for w in ['turn on', 'switch on', 'lights on', 'light on']):
            params['action'] = 'on'
        elif any(w in msg_lower for w in ['turn off', 'switch off', 'lights off', 'light off']):
            params['action'] = 'off'
        elif any(w in msg_lower for w in ['toggle', 'flip']):
            params['action'] = 'toggle'
        
        # Check for mood/scene
        for mood in moods:
            if mood in msg_lower:
                params['action'] = 'mood'
                params['mood'] = mood
                break
        
        # Check for specific color (if no mood found)
        if 'mood' not in params:
            for color, values in color_map.items():
                if color in msg_lower:
                    params['action'] = 'color'
                    params['color'] = color
                    params['color_values'] = values
                    break
        
        # Extract brightness (0-100 scale)
        brightness_patterns = [
            r'(\d{1,3})\s*%',
            r'brightness\s*(?:to\s*)?(\d{1,3})',
            r'(?:at|to)\s*(\d{1,3})\s*(?:percent|%)?',
            r'set\s*(?:to\s*)?(\d{1,3})',
        ]
        for pattern in brightness_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                bri = int(match.group(1))
                if 0 <= bri <= 100:
                    params['brightness'] = int(bri * 254 / 100)  # Convert to 0-254 scale
                    if params['action'] == 'status':
                        params['action'] = 'brightness'
                    break
        
        # Natural language brightness
        if 'dim' in msg_lower and 'brightness' not in params:
            params['brightness'] = 50
            if params['action'] == 'status':
                params['action'] = 'brightness'
        elif 'bright' in msg_lower and 'brightness' not in params:
            params['brightness'] = 254
            if params['action'] == 'status':
                params['action'] = 'brightness'
        elif 'half' in msg_lower and 'brightness' not in params:
            params['brightness'] = 127
            if params['action'] == 'status':
                params['action'] = 'brightness'
        
        # Extract specific light name
        for light in light_names:
            if light in msg_lower:
                params['light_name'] = light
                break
        
        # Extract transition time
        trans_match = re.search(r'(?:over|in)\s+(\d+)\s*(?:seconds?|secs?|s)', msg_lower)
        if trans_match:
            params['transition'] = int(trans_match.group(1)) * 10  # Hue uses deciseconds
        
        return params

    def record_tool_usage(self, tool_name: str, was_successful: bool):
        """
        Record tool usage for learning patterns.
        """
        self.tool_usage_history[tool_name] += 1 if was_successful else 0


def integrate_with_existing_system(
    message: str,
    conversation_messages: List[Dict],
    selector: ImprovedToolSelector
) -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
    """
    Integration function to use the improved selector with existing Blue code.

    Args:
        message: Current user message
        conversation_messages: Full conversation history
        selector: Instance of ImprovedToolSelector

    Returns:
        Tuple of (forced_tool_name, tool_args, user_feedback_message)
    """
    # Get recent history for context
    recent_history = conversation_messages[-5:] if len(conversation_messages) > 5 else conversation_messages

    # Run selection
    result = selector.select_tool(message, recent_history)

    if not result.primary_tool:
        # No tool needed
        return None, None, None

    if result.needs_disambiguation:
        # Ask user for clarification
        return None, None, result.disambiguation_prompt

    # Return the selected tool
    tool_name = result.primary_tool.tool_name
    tool_args = result.primary_tool.extracted_params

    # Add logging
    print(f"   [IMPROVED-SELECTOR] Selected: {tool_name}")
    print(f"   [IMPROVED-SELECTOR] Confidence: {result.primary_tool.confidence:.2f}")
    print(f"   [IMPROVED-SELECTOR] Reason: {result.primary_tool.reason}")

    if result.alternative_tools:
        alt_names = [t.tool_name for t in result.alternative_tools[:2]]
        print(f"   [IMPROVED-SELECTOR] Alternatives: {', '.join(alt_names)}")

    if result.compound_request:
        print(f"   [IMPROVED-SELECTOR] WARNING: Compound request detected - may need multiple tools")

    return tool_name, tool_args, None


# Example usage:
if __name__ == "__main__":
    selector = ImprovedToolSelector()

    # Test cases
    test_messages = [
        "check my email",
        "search my documents for contract details",
        "play some jazz music",
        "turn on the lights",
        "what's the weather like?",
        "send an email to john@example.com saying hello",
        "search for latest AI news",
    ]

    for msg in test_messages:
        print(f"\n{'='*60}")
        print(f"Message: {msg}")
        print(f"{'='*60}")

        result = selector.select_tool(msg, [])

        if result.primary_tool:
            print(f"Primary Tool: {result.primary_tool.tool_name}")
            print(f"Confidence: {result.primary_tool.confidence:.2f}")
            print(f"Priority: {result.primary_tool.priority}")
            print(f"Reason: {result.primary_tool.reason}")
            print(f"Params: {result.primary_tool.extracted_params}")

            if result.alternative_tools:
                print(f"\nAlternatives:")
                for alt in result.alternative_tools:
                    print(f"  - {alt.tool_name} (confidence: {alt.confidence:.2f})")

            if result.needs_disambiguation:
                print(f"\nDisambiguation needed:")
                print(f"  {result.disambiguation_prompt}")
        else:
            print("No tool needed")


# ================================================================================
# END OF IMPROVED TOOL SELECTION SYSTEM
# ================================================================================

# Initialize the improved tool selector globally
try:
    IMPROVED_TOOL_SELECTOR = ImprovedToolSelector()
    print("[OK] Improved tool selector initialized - confidence-based selection enabled!")
    USE_IMPROVED_SELECTOR = True
except Exception as e:
    print(f"[WARN] Could not initialize improved selector: {e}")
    print("[INFO] Falling back to legacy detection")
    USE_IMPROVED_SELECTOR = False


app = Flask(__name__)

# Configuration
LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"
LM_STUDIO_RAG_URL = "http://127.0.0.1:1234/v1/rag"

# ============================
# LM Studio — single provider
# ============================
class LMStudioClient:
    """
    Enhanced client for local LM Studio (OpenAI-compatible) chat completions.
    v6 ENHANCEMENTS:
    - Auto-retry with exponential backoff
    - Connection health checks
    - Request/response logging
    - Timeout management
    """
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None, 
                 timeout: Optional[float] = None, max_retries: int = 3):
        self.base_url = (
            base_url
            or os.environ.get("LM_STUDIO_URL")
            or globals().get("LM_STUDIO_URL")
            or "http://127.0.0.1:1234/v1/chat/completions"
        )
        self.model = (
            model
            or os.environ.get("LM_STUDIO_MODEL")
            or globals().get("LM_STUDIO_MODEL")
            or "local-model"
        )
        self.timeout = float(timeout or os.environ.get("LM_STUDIO_TIMEOUT", "120"))
        self.max_retries = max_retries
        self._healthy = None
        self._last_health_check = 0
    
    def is_healthy(self, force_check: bool = False) -> bool:
        """Check if LM Studio is responding (cached for 60s)."""
        import time
        now = time.time()
        if not force_check and self._healthy is not None and (now - self._last_health_check) < 60:
            return self._healthy
        
        try:
            # Try to hit the models endpoint as a health check
            health_url = self.base_url.replace('/chat/completions', '/models')
            resp = requests.get(health_url, timeout=5)
            self._healthy = resp.status_code == 200
        except Exception:
            self._healthy = False
        
        self._last_health_check = now
        return self._healthy

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        extra: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if temperature is not None:
            payload["temperature"] = float(temperature)
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        if extra and isinstance(extra, dict):
            payload.update(extra)
        if kwargs:
            payload.update(kwargs)

        # Retry logic with exponential backoff
        import time
        last_error = None
        for attempt in range(self.max_retries):
            try:
                resp = requests.post(self.base_url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                result = resp.json()
                
                # Validate response structure
                if 'choices' not in result and 'error' not in result:
                    raise ValueError(f"Unexpected response structure: {list(result.keys())}")
                
                return result
                
            except requests.exceptions.Timeout as e:
                last_error = e
                wait_time = 2 ** attempt
                print(f"   [LLM] Timeout on attempt {attempt + 1}, retrying in {wait_time}s...")
                time.sleep(wait_time)
                
            except requests.exceptions.ConnectionError as e:
                last_error = e
                wait_time = 2 ** attempt
                print(f"   [LLM] Connection error on attempt {attempt + 1}, retrying in {wait_time}s...")
                time.sleep(wait_time)
                
            except requests.exceptions.HTTPError as e:
                # Don't retry on 4xx errors (client errors)
                if e.response.status_code < 500:
                    return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
                last_error = e
                wait_time = 2 ** attempt
                print(f"   [LLM] Server error on attempt {attempt + 1}, retrying in {wait_time}s...")
                time.sleep(wait_time)
                
            except Exception as e:
                last_error = e
                print(f"   [LLM] Unexpected error: {e}")
                break
        
        return {"error": f"LLM request failed after {self.max_retries} attempts: {last_error}"}

# Global LM Studio client
try:
    _LM = LMStudioClient()
except Exception as _e:
    print(f"[WARN] Failed to init LM Studio client: {_e}")
    _LM = None

def call_llm(
    messages: List[Dict[str, Any]],
    include_tools: bool = True,
    tool_choice: str = "auto",
    force_tool: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    """Unified LLM entrypoint: always uses local LM Studio."""
    # Nudge if a specific tool is required
    if force_tool:
        messages = list(messages)
        if messages and isinstance(messages[-1], dict) and messages[-1].get("role") == "user":
            messages[-1] = {**messages[-1]}
            messages[-1]["content"] = (
                (messages[-1].get("content") or "")
                + "\n\n[System note: Use the specified tool to satisfy this request.]"


            )
    tools_payload = None
    try:
        tools_payload = TOOLS if include_tools and "TOOLS" in globals() else None  # noqa: F821
    except Exception:
        tools_payload = None

    if _LM is None:
        return {"error": "LM Studio client not available"}
    try:
        return _LM.chat(
            messages,
            tools=tools_payload,
            tool_choice=tool_choice,
            max_tokens=max_tokens,
            temperature=temperature,
            extra=extra,
            **kwargs
        )
    except Exception as e:
        return {"error": f"LM Studio request failed: {e}"}

PROXY_PORT = 5000


# Document search behavior: "opt_in" (ask first) or "aggressive" (auto)
AUTO_DOCSEARCH_MODE = "opt_in"


# ===== Enhanced Settings & Logger =====
@dataclass
class Settings:
    LOG_LEVEL: str = "INFO"
    MAX_ITERATIONS: int = 10
    TOOL_TIMEOUT_SECS: float = 15.0
    TOOL_RETRIES: int = 2
    # Conversation trimming: retain only the most recent N messages (plus system) when
    # sending context to the language model. This helps prevent the model from
    # confusing long conversation history or previous tool responses with the
    # user’s current intent. A value of 0 disables trimming.
    MAX_CONTEXT_MESSAGES: int = 20  # Increased to preserve .ocf memories
    AUTO_DOCSEARCH_MODE: str = AUTO_DOCSEARCH_MODE if "AUTO_DOCSEARCH_MODE" in globals() else "opt_in"

_settings = Settings()
# Music configuration
MUSIC_SERVICE = "youtube_music"  # or "amazon_music"
YOUTUBE_MUSIC_BROWSER = None  # Will store ytmusicapi instance

# Document storage
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Document index (stores metadata)
DOCUMENT_INDEX_FILE = "document_index.json"

# Hue Configuration
HUE_CONFIG = {}
try:
    with open("hue_config.json", "r") as f:
        HUE_CONFIG = json.load(f)
    print(f"[OK] Hue config loaded: Bridge at {HUE_CONFIG.get('bridge_ip')}")
except FileNotFoundError:
    print("[WARN]  No hue_config.json found. Run setup_hue.py first!")
except Exception as e:
    print(f"[WARN]  Error loading Hue config: {e}")

BRIDGE_IP = HUE_CONFIG.get("bridge_ip", "")
HUE_USERNAME = HUE_CONFIG.get("username", "")

# Gmail Configuration

# Gmail library availability
try:
    from googleapiclient.discovery import build  # already imported above
    from google_auth_oauthlib.flow import InstalledAppFlow  # already imported above
    from google.auth.transport.requests import Request  # already imported above
    GMAIL_AVAILABLE = True
except Exception:
    GMAIL_AVAILABLE = False


GMAIL_TOKEN_FILE = "gmail_token.pickle"
GMAIL_CREDENTIALS_FILE = "gmail_credentials.json"
GMAIL_USER_EMAIL = "alevantresearch@gmail.com"
_gmail_service = None

def get_gmail_service():
    """Get or create Gmail API service"""
    global _gmail_service
    if _gmail_service:
        return _gmail_service

    if not GMAIL_AVAILABLE:
        raise Exception("Gmail libraries not installed")

    creds = None
    # Load existing token
    if os.path.exists(GMAIL_TOKEN_FILE):
        with open(GMAIL_TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(GMAIL_CREDENTIALS_FILE):
                raise Exception(f"Gmail credentials file not found: {GMAIL_CREDENTIALS_FILE}. " +
                              "Download from Google Cloud Console and save as gmail_credentials.json")
            flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_FILE, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials
        with open(GMAIL_TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    _gmail_service = build('gmail', 'v1', credentials=creds)
    return _gmail_service

# IMPROVED Keywords - More comprehensive and specific detection
SEARCH_KEYWORDS = [
    'search', 'look up', 'find out', 'google', 'check online', 'search for',
    'tell me about', 'information on', 'facts about', 'research',
    'check the internet', 'web search', 'online', 'latest', 'recent', 'current',
    'news about', 'who won', 'what happened', 'update on', 'check if'
]

WEATHER_KEYWORDS = [
    'weather', 'temperature', 'forecast', 'rain', 'raining', 'snow', 'snowing',
    'sunny', 'cloudy', 'storm', 'humidity', 'wind', 'windy', 'cold', 'hot',
    'warm', 'degrees', 'celsius', 'fahrenheit', 'climate'
]

LIGHT_KEYWORDS = [
    'light', 'lights', 'lamp', 'lamps', 'brightness', 'dim', 'bright',
    'turn on', 'turn off', 'switch on', 'switch off', 'color', 'colour',
    'mood', 'scene', 'atmosphere', 'illuminate', 'lighting', 'bulb',
    'darker', 'brighter', 'glow', 'hue', 'philips'
]

VISUALIZER_KEYWORDS = [
    'visualizer', 'light show', 'light dance', 'dancing lights', 'party lights',
    'disco', 'strobe', 'color changing', 'dynamic lights', 'animated lights'
]

DOCUMENT_KEYWORDS = [
    'document', 'doc', 'file', 'pdf', 'my documents', 'my files',
    'uploaded', 'contract', 'agreement', 'policy', 'deadline', 'due date',
    'syllabus', 'course', 'assignment', 'exam', 'schedule', 'paper', 'report',
    'memo', 'notes', 'guidelines', 'instructions', 'manual', 'handbook',
    'according to my', 'in my file', 'what does my', 'says in'
]

# ===== NEW: IMPROVED KEYWORD LISTS FOR BETTER TOOL DETECTION =====
# Keywords for RETRIEVING/READING a specific document
DOCUMENT_RETRIEVAL_KEYWORDS = [
    'read me', 'read to me', 'show me', 'display', 'view', 'open',
    'read the', 'show the', 'display the', 'view the', 'open the',
    'entire document', 'full document', 'whole document', 'complete document',
    'the document called', 'the file called', 'document named', 'file named',
    'in your documents folder', 'from your documents', 'from the documents folder'
]

# Keywords for SEARCHING within documents (semantic/RAG search)
DOCUMENT_SEARCH_KEYWORDS = [
    'search my documents', 'search documents', 'find in my documents',
    'what does my document say about', 'according to my documents',
    'in my documents about', 'search for', 'find information about',
    'what information', 'do my documents mention', 'do my files contain'
]

# Keywords for WEB SEARCH (internet search)
WEB_SEARCH_KEYWORDS = [
    'search the web', 'search online', 'google', 'search for online',
    'look up online', 'search the internet', 'find on the web',
    'current', 'latest', 'recent', 'today', 'this week', 'news about',
    'who won', 'what happened', 'check online', 'search google'
]

CREATE_DOCUMENT_KEYWORDS = [
    'create document', 'create file', 'write document', 'write file',
    'make document', 'make file', 'save document', 'save file',
    'create a', 'write a', 'make a', 'save as',
    'shopping list', 'todo list', 'to-do list', 'to do list',
    'notes', 'recipe', 'list for', 'write me', 'create me'
]

# Gmail keywords
GMAIL_READ_KEYWORDS = [
    'email', 'emails', 'gmail', 'inbox', 'messages', 'mail',
    'check my email', 'read email', 'show email', 'recent email',
    'unread', 'new messages', 'latest messages', 'my inbox',
    'email from', 'message from', 'email about'
]

GMAIL_SEND_KEYWORDS = [
    'send email', 'email to', 'write email', 'compose email',
    'send message', 'send a message', 'email', 'mail to',
    'send to', 'message to', 'draft email'
]

BROWSE_KEYWORDS = [
    'browse', 'open url', 'open website', 'visit website', 'visit url',
    'go to', 'navigate to', 'fetch', 'read this page', 'open this',
    'visit this', 'load this page', 'show me this website', 'http://', 'https://',
    'www.', '.com', '.org', '.net', 'summarize this page', 'what does this say'
]


MUSIC_PLAY_KEYWORDS = [
    'play', 'play music', 'play song', 'play some', 'put on', 'listen to',
    'start playing', 'i want to hear', 'can you play'
]

MUSIC_CONTROL_KEYWORDS = [
    'pause', 'stop music', 'skip', 'next song', 'previous song', 'volume',
    'resume', 'unpause', 'mute', 'unmute', 'louder', 'quieter',
    'next track', 'previous track', 'turn up', 'turn down', 'stop playing'
]

# Words that indicate this is NOT a tool request
NO_TOOL_KEYWORDS = [
    'hello', 'hi ', 'hey', 'good morning', 'good afternoon', 'good evening',
    'how are you', 'whats up', 'tell me a joke', 'who are you', 'what are you',
    'thank you', 'thanks', 'goodbye', 'bye', 'see you'
]

# Basic color presets
COLOR_MAP = {
    "red": {"hue": 0, "sat": 254},
    "orange": {"hue": 5000, "sat": 254},
    "yellow": {"hue": 12750, "sat": 254},
    "green": {"hue": 25500, "sat": 254},
    "cyan": {"hue": 30000, "sat": 254},
    "blue": {"hue": 46920, "sat": 254},
    "purple": {"hue": 50000, "sat": 254},
    "pink": {"hue": 56100, "sat": 254},
    "white": {"hue": 0, "sat": 0},
    "warm white": {"hue": 8000, "sat": 140, "ct": 400},
    "cool white": {"hue": 40000, "sat": 50, "ct": 200},
}

# MOOD/SCENE PRESETS [MOOD]
MOOD_PRESETS = {
    # === NATURE ===
    "moonlight": {
        "description": "Cool, dim blues and silvers like moonlight",
        "settings": [
            {"hue": 46920, "sat": 200, "bri": 80},
            {"hue": 46000, "sat": 150, "bri": 100},
            {"hue": 48000, "sat": 100, "bri": 60},
            {"ct": 200, "bri": 70},
        ]
    },
    "sunset": {
        "description": "Warm oranges, reds, and purples like a sunset",
        "settings": [
            {"hue": 5000, "sat": 254, "bri": 200},
            {"hue": 1000, "sat": 254, "bri": 180},
            {"hue": 50000, "sat": 200, "bri": 150},
            {"hue": 0, "sat": 254, "bri": 160},
        ]
    },
    "sunrise": {
        "description": "Gradual warm colors like sunrise",
        "settings": [
            {"hue": 8000, "sat": 200, "bri": 100},
            {"hue": 6000, "sat": 240, "bri": 150},
            {"hue": 5000, "sat": 254, "bri": 180},
            {"ct": 350, "bri": 200},
        ]
    },
    "ocean": {
        "description": "Deep blues and teals like the ocean",
        "settings": [
            {"hue": 46920, "sat": 254, "bri": 180},
            {"hue": 44000, "sat": 220, "bri": 200},
            {"hue": 35000, "sat": 240, "bri": 190},
            {"hue": 30000, "sat": 200, "bri": 170},
        ]
    },
    "forest": {
        "description": "Various greens like a forest",
        "settings": [
            {"hue": 25500, "sat": 254, "bri": 180},
            {"hue": 27000, "sat": 230, "bri": 160},
            {"hue": 24000, "sat": 200, "bri": 170},
            {"hue": 26000, "sat": 180, "bri": 150},
        ]
    },
    "tropical": {
        "description": "Vibrant greens and blues like a tropical paradise",
        "settings": [
            {"hue": 30000, "sat": 254, "bri": 200},
            {"hue": 25500, "sat": 254, "bri": 210},
            {"hue": 35000, "sat": 240, "bri": 190},
            {"hue": 28000, "sat": 230, "bri": 200},
        ]
    },
    "arctic": {
        "description": "Icy blues and whites like the arctic",
        "settings": [
            {"hue": 46920, "sat": 180, "bri": 200},
            {"ct": 150, "bri": 220},
            {"hue": 48000, "sat": 120, "bri": 210},
            {"ct": 180, "bri": 200},
        ]
    },
    "galaxy": {
        "description": "Deep purples and blues like outer space",
        "settings": [
            {"hue": 50000, "sat": 254, "bri": 150},
            {"hue": 48000, "sat": 230, "bri": 130},
            {"hue": 46920, "sat": 254, "bri": 120},
            {"hue": 52000, "sat": 240, "bri": 140},
        ]
    },
    "aurora": {
        "description": "Northern lights - greens and purples dancing",
        "settings": [
            {"hue": 25500, "sat": 254, "bri": 180},
            {"hue": 50000, "sat": 254, "bri": 160},
            {"hue": 35000, "sat": 240, "bri": 170},
            {"hue": 46920, "sat": 200, "bri": 150},
        ]
    },
    "thunderstorm": {
        "description": "Dark blues with flashes of white",
        "settings": [
            {"hue": 46920, "sat": 254, "bri": 40},
            {"hue": 48000, "sat": 200, "bri": 30},
            {"hue": 44000, "sat": 220, "bri": 35},
        ]
    },
    "beach": {
        "description": "Sandy yellows and ocean blues",
        "settings": [
            {"hue": 10000, "sat": 180, "bri": 200},
            {"hue": 35000, "sat": 200, "bri": 180},
            {"hue": 8000, "sat": 160, "bri": 210},
            {"hue": 40000, "sat": 180, "bri": 190},
        ]
    },
    "desert": {
        "description": "Warm sandy oranges and dusty browns",
        "settings": [
            {"hue": 6000, "sat": 200, "bri": 200},
            {"hue": 5000, "sat": 220, "bri": 180},
            {"hue": 8000, "sat": 180, "bri": 190},
            {"hue": 4000, "sat": 240, "bri": 170},
        ]
    },
    "rainforest": {
        "description": "Lush deep greens with hints of mist",
        "settings": [
            {"hue": 25500, "sat": 254, "bri": 140},
            {"hue": 27000, "sat": 230, "bri": 130},
            {"hue": 23000, "sat": 210, "bri": 150},
            {"hue": 30000, "sat": 180, "bri": 160},
        ]
    },
    
    # === ACTIVITIES ===
    "focus": {
        "description": "Bright, cool white for concentration",
        "settings": [
            {"ct": 200, "bri": 254},
            {"ct": 210, "bri": 240},
            {"ct": 220, "bri": 250},
        ]
    },
    "relax": {
        "description": "Warm, dim lighting for relaxation",
        "settings": [
            {"ct": 400, "bri": 120},
            {"ct": 420, "bri": 110},
            {"ct": 390, "bri": 130},
            {"ct": 410, "bri": 115},
        ]
    },
    "energize": {
        "description": "Very bright white to wake you up",
        "settings": [
            {"ct": 250, "bri": 254},
            {"ct": 240, "bri": 254},
            {"ct": 260, "bri": 254},
        ]
    },
    "reading": {
        "description": "Warm but bright for comfortable reading",
        "settings": [
            {"ct": 350, "bri": 254},
            {"ct": 340, "bri": 245},
            {"ct": 360, "bri": 250},
        ]
    },
    "movie": {
        "description": "Very dim for watching movies",
        "settings": [
            {"hue": 46920, "sat": 200, "bri": 30},
            {"hue": 0, "sat": 0, "bri": 20},
            {"hue": 0, "sat": 0, "bri": 25},
        ]
    },
    "gaming": {
        "description": "Vibrant colors for immersive gaming",
        "settings": [
            {"hue": 50000, "sat": 254, "bri": 180},
            {"hue": 0, "sat": 254, "bri": 160},
            {"hue": 25500, "sat": 254, "bri": 170},
            {"hue": 46920, "sat": 254, "bri": 175},
        ]
    },
    "workout": {
        "description": "High energy reds and oranges",
        "settings": [
            {"hue": 0, "sat": 254, "bri": 254},
            {"hue": 5000, "sat": 254, "bri": 240},
            {"hue": 2000, "sat": 254, "bri": 250},
        ]
    },
    "yoga": {
        "description": "Calm purples and soft blues for meditation",
        "settings": [
            {"hue": 50000, "sat": 150, "bri": 100},
            {"hue": 46920, "sat": 120, "bri": 90},
            {"hue": 48000, "sat": 140, "bri": 95},
        ]
    },
    "meditation": {
        "description": "Very dim, peaceful lighting",
        "settings": [
            {"hue": 46920, "sat": 100, "bri": 40},
            {"hue": 50000, "sat": 80, "bri": 35},
            {"ct": 450, "bri": 30},
        ]
    },
    "cooking": {
        "description": "Bright warm white for the kitchen",
        "settings": [
            {"ct": 300, "bri": 254},
            {"ct": 310, "bri": 250},
            {"ct": 290, "bri": 254},
        ]
    },
    "dinner": {
        "description": "Warm candlelight ambiance for dining",
        "settings": [
            {"hue": 6000, "sat": 200, "bri": 140},
            {"hue": 5500, "sat": 220, "bri": 130},
            {"hue": 6500, "sat": 180, "bri": 150},
        ]
    },
    "sleep": {
        "description": "Very dim red to help you fall asleep",
        "settings": [
            {"hue": 0, "sat": 254, "bri": 20},
            {"hue": 1000, "sat": 254, "bri": 15},
            {"hue": 500, "sat": 254, "bri": 18},
        ]
    },
    "wakeup": {
        "description": "Gradually brightening warm light",
        "settings": [
            {"ct": 400, "bri": 150},
            {"ct": 350, "bri": 200},
            {"ct": 300, "bri": 254},
        ]
    },
    
    # === MOODS ===
    "romance": {
        "description": "Soft reds and pinks, dim and intimate",
        "settings": [
            {"hue": 56100, "sat": 220, "bri": 100},
            {"hue": 0, "sat": 200, "bri": 80},
            {"hue": 1000, "sat": 180, "bri": 90},
            {"hue": 56500, "sat": 200, "bri": 85},
        ]
    },
    "party": {
        "description": "Bright, vibrant colors for celebration",
        "settings": [
            {"hue": 0, "sat": 254, "bri": 254},
            {"hue": 46920, "sat": 254, "bri": 254},
            {"hue": 25500, "sat": 254, "bri": 254},
            {"hue": 12750, "sat": 254, "bri": 254},
            {"hue": 50000, "sat": 254, "bri": 254},
        ]
    },
    "cozy": {
        "description": "Warm amber glow like firelight",
        "settings": [
            {"ct": 450, "bri": 140},
            {"ct": 470, "bri": 130},
            {"hue": 6000, "sat": 200, "bri": 150},
        ]
    },
    "fireplace": {
        "description": "Flickering oranges and reds like a fire",
        "settings": [
            {"hue": 5000, "sat": 254, "bri": 180},
            {"hue": 3000, "sat": 254, "bri": 160},
            {"hue": 1000, "sat": 254, "bri": 170},
            {"hue": 6000, "sat": 240, "bri": 190},
        ]
    },
    "candle": {
        "description": "Soft flickering candlelight",
        "settings": [
            {"hue": 6000, "sat": 254, "bri": 100},
            {"hue": 5500, "sat": 254, "bri": 90},
            {"hue": 6500, "sat": 240, "bri": 95},
        ]
    },
    "zen": {
        "description": "Minimalist calm with soft whites",
        "settings": [
            {"ct": 350, "bri": 100},
            {"ct": 360, "bri": 95},
            {"ct": 340, "bri": 105},
        ]
    },
    "spa": {
        "description": "Relaxing blues and soft greens",
        "settings": [
            {"hue": 35000, "sat": 150, "bri": 130},
            {"hue": 46920, "sat": 120, "bri": 140},
            {"hue": 38000, "sat": 140, "bri": 135},
        ]
    },
    "club": {
        "description": "Intense dance club vibes",
        "settings": [
            {"hue": 50000, "sat": 254, "bri": 254},
            {"hue": 0, "sat": 254, "bri": 254},
            {"hue": 46920, "sat": 254, "bri": 254},
        ]
    },
    "disco": {
        "description": "Retro disco colors",
        "settings": [
            {"hue": 50000, "sat": 254, "bri": 220},
            {"hue": 10000, "sat": 254, "bri": 230},
            {"hue": 35000, "sat": 254, "bri": 210},
            {"hue": 0, "sat": 254, "bri": 225},
        ]
    },
    "concert": {
        "description": "Stage lighting intensity",
        "settings": [
            {"hue": 0, "sat": 254, "bri": 254},
            {"hue": 46920, "sat": 254, "bri": 254},
            {"hue": 25500, "sat": 254, "bri": 254},
        ]
    },
    "chill": {
        "description": "Laid back cool tones",
        "settings": [
            {"hue": 46920, "sat": 150, "bri": 150},
            {"hue": 48000, "sat": 130, "bri": 140},
            {"ct": 300, "bri": 160},
        ]
    },
    "warm": {
        "description": "Comfortable warm white",
        "settings": [
            {"ct": 400, "bri": 200},
            {"ct": 420, "bri": 190},
            {"ct": 380, "bri": 210},
        ]
    },
    "cool": {
        "description": "Crisp cool white",
        "settings": [
            {"ct": 200, "bri": 220},
            {"ct": 180, "bri": 230},
            {"ct": 220, "bri": 210},
        ]
    },
    "bright": {
        "description": "Maximum brightness",
        "settings": [
            {"ct": 250, "bri": 254},
            {"ct": 250, "bri": 254},
            {"ct": 250, "bri": 254},
        ]
    },
    "dim": {
        "description": "Very low light",
        "settings": [
            {"ct": 400, "bri": 50},
            {"ct": 400, "bri": 45},
            {"ct": 400, "bri": 55},
        ]
    },
    "night": {
        "description": "Minimal nightlight",
        "settings": [
            {"hue": 0, "sat": 254, "bri": 10},
            {"hue": 5000, "sat": 200, "bri": 15},
        ]
    },
    "natural": {
        "description": "Daylight simulation",
        "settings": [
            {"ct": 250, "bri": 254},
            {"ct": 260, "bri": 250},
            {"ct": 240, "bri": 254},
        ]
    },
    
    # === HOLIDAYS ===
    "christmas": {
        "description": "Red and green holiday cheer",
        "settings": [
            {"hue": 0, "sat": 254, "bri": 200},
            {"hue": 25500, "sat": 254, "bri": 200},
            {"hue": 0, "sat": 254, "bri": 200},
            {"hue": 25500, "sat": 254, "bri": 200},
        ]
    },
    "halloween": {
        "description": "Spooky oranges and purples",
        "settings": [
            {"hue": 5000, "sat": 254, "bri": 180},
            {"hue": 50000, "sat": 254, "bri": 140},
            {"hue": 5500, "sat": 254, "bri": 170},
        ]
    },
    "valentines": {
        "description": "Romantic reds and pinks",
        "settings": [
            {"hue": 0, "sat": 254, "bri": 160},
            {"hue": 56100, "sat": 220, "bri": 150},
            {"hue": 1000, "sat": 254, "bri": 155},
        ]
    },
    "easter": {
        "description": "Soft pastels",
        "settings": [
            {"hue": 56100, "sat": 100, "bri": 200},
            {"hue": 35000, "sat": 80, "bri": 210},
            {"hue": 10000, "sat": 90, "bri": 205},
            {"hue": 50000, "sat": 85, "bri": 195},
        ]
    },
    "july4": {
        "description": "Red, white, and blue patriotic",
        "settings": [
            {"hue": 0, "sat": 254, "bri": 200},
            {"ct": 200, "bri": 254},
            {"hue": 46920, "sat": 254, "bri": 200},
        ]
    },
    "stpatricks": {
        "description": "Irish green",
        "settings": [
            {"hue": 25500, "sat": 254, "bri": 200},
            {"hue": 26000, "sat": 240, "bri": 210},
            {"hue": 24500, "sat": 254, "bri": 195},
        ]
    },
    "hanukkah": {
        "description": "Blue and white celebration",
        "settings": [
            {"hue": 46920, "sat": 254, "bri": 200},
            {"ct": 200, "bri": 220},
            {"hue": 46920, "sat": 254, "bri": 200},
        ]
    },
    "newyear": {
        "description": "Sparkling gold and silver",
        "settings": [
            {"hue": 8000, "sat": 200, "bri": 220},
            {"ct": 180, "bri": 230},
            {"hue": 9000, "sat": 180, "bri": 210},
        ]
    },
    
    # === COLORS ===
    "red": {
        "description": "Pure red",
        "settings": [{"hue": 0, "sat": 254, "bri": 200}]
    },
    "blue": {
        "description": "Pure blue",
        "settings": [{"hue": 46920, "sat": 254, "bri": 200}]
    },
    "green": {
        "description": "Pure green",
        "settings": [{"hue": 25500, "sat": 254, "bri": 200}]
    },
    "purple": {
        "description": "Pure purple",
        "settings": [{"hue": 50000, "sat": 254, "bri": 200}]
    },
    "orange": {
        "description": "Pure orange",
        "settings": [{"hue": 5000, "sat": 254, "bri": 200}]
    },
    "yellow": {
        "description": "Pure yellow",
        "settings": [{"hue": 10000, "sat": 254, "bri": 200}]
    },
    "pink": {
        "description": "Soft pink",
        "settings": [{"hue": 56100, "sat": 200, "bri": 200}]
    },
    "cyan": {
        "description": "Cyan/Teal",
        "settings": [{"hue": 35000, "sat": 254, "bri": 200}]
    },
    "white": {
        "description": "Pure white",
        "settings": [{"ct": 250, "bri": 254}]
    },
    "rainbow": {
        "description": "Full spectrum colors",
        "settings": [
            {"hue": 0, "sat": 254, "bri": 200},
            {"hue": 10000, "sat": 254, "bri": 200},
            {"hue": 25500, "sat": 254, "bri": 200},
            {"hue": 35000, "sat": 254, "bri": 200},
            {"hue": 46920, "sat": 254, "bri": 200},
            {"hue": 50000, "sat": 254, "bri": 200},
        ]
    },
}


# ===== MUSIC FUNCTIONS =====

def init_youtube_music():
    """Initialize YouTube Music API."""
    global YOUTUBE_MUSIC_BROWSER
    if YOUTUBE_MUSIC_BROWSER is None:
        try:
            from ytmusicapi import YTMusic
            YOUTUBE_MUSIC_BROWSER = YTMusic()
            print("[OK] YouTube Music initialized")
            return True
        except ImportError:
            print("[WARN]  ytmusicapi not installed. Install with: pip install ytmusicapi")
            return False
        except Exception as e:
            print(f"[WARN]  Error initializing YouTube Music: {e}")
            return False
    return True


def search_youtube_music(query: str, limit: int = 5) -> List[Dict]:
    """Search for songs on YouTube Music."""
    if not init_youtube_music():
        return []

    try:
        results = YOUTUBE_MUSIC_BROWSER.search(query, filter="songs", limit=limit)
        return results
    except Exception as e:
        print(f"   [ERROR] Error searching YouTube Music: {e}")
        return []


def get_music_mood(query: str, song_info: dict = None) -> str:
    """Determine appropriate light mood based on music query."""
    query_lower = query.lower()

    # Genre/vibe detection
    if any(word in query_lower for word in ['relax', 'calm', 'chill', 'ambient', 'peaceful', 'meditation', 'sleep', 'quiet']):
        return 'relax'
    elif any(word in query_lower for word in ['party', 'dance', 'edm', 'club', 'rave', 'celebration', 'upbeat', 'fun']):
        return 'party'
    elif any(word in query_lower for word in ['romantic', 'love', 'ballad', 'slow dance', 'valentine', 'intimate']):
        return 'romance'
    elif any(word in query_lower for word in ['energize', 'workout', 'pump up', 'hype', 'rock', 'metal', 'hard', 'intense']):
        return 'energize'
    elif any(word in query_lower for word in ['jazz', 'lounge', 'smooth', 'sophisticated', 'cool', 'mellow']):
        return 'moonlight'
    elif any(word in query_lower for word in ['tropical', 'beach', 'island', 'reggae', 'caribbean', 'summer']):
        return 'tropical'
    elif any(word in query_lower for word in ['blues', 'soul', 'moody', 'melancholy', 'sad']):
        return 'ocean'
    elif any(word in query_lower for word in ['classical', 'orchestra', 'symphony', 'piano', 'study', 'concentrate']):
        return 'focus'
    elif any(word in query_lower for word in ['sunset', 'golden hour', 'evening', 'dusk']):
        return 'sunset'
    elif any(word in query_lower for word in ['fire', 'cozy', 'warm', 'acoustic', 'folk']):
        return 'fireplace'
    elif any(word in query_lower for word in ['space', 'cosmic', 'stars', 'galaxy', 'ambient', 'electronic']):
        return 'galaxy'
    elif any(word in query_lower for word in ['forest', 'nature', 'green', 'earth', 'natural']):
        return 'forest'
    elif any(word in query_lower for word in ['arctic', 'ice', 'winter', 'frozen', 'cold']):
        return 'arctic'
    elif any(word in query_lower for word in ['sunrise', 'morning', 'dawn', 'wake up']):
        return 'sunrise'
    else:
        # Default party mood for general music
        return 'party'


def play_music(query: str, service: str = "youtube_music") -> str:
    """
    Play music based on query and automatically sync lights.

    Args:
        query: Song name, artist, or search query
        service: "youtube_music" or "amazon_music"
    """
    print(f"   [MUSIC] Playing music: '{query}' on {service}")

    if service == "youtube_music":
        # Search for the song
        results = search_youtube_music(query, limit=1)

        if not results:
            return f"Couldn't find any songs matching '{query}' on YouTube Music"

        # Get the first result
        song = results[0]
        song_title = song.get('title', 'Unknown')
        artists = song.get('artists', [])
        artist_names = ", ".join([a.get('name', '') for a in artists]) if artists else "Unknown Artist"
        video_id = song.get('videoId', '')

        if not video_id:
            return f"Found '{song_title}' by {artist_names}, but couldn't get playback URL"

        # Construct YouTube Music URL
        url = f"https://music.youtube.com/watch?v={video_id}"

        # **NEW: Sync lights with music vibe**
        light_sync_msg = ""
        if BRIDGE_IP and HUE_USERNAME:
            try:
                mood = get_music_mood(query, song)
                print(f"   [SYNC] Syncing lights to '{mood}' mood for this music")
                light_result = apply_mood_to_lights(mood)
                print(f"   [LIGHT] {light_result}")
                light_sync_msg = f"\n💡 Lights set to '{mood}' mood"
            except Exception as e:
                print(f"   [WARN] Couldn't sync lights: {e}")

        # Open in browser
        try:
            webbrowser.open(url)
            return f"🎵 Now playing: '{song_title}' by {artist_names}{light_sync_msg}"
        except Exception as e:
            return f"Found '{song_title}' by {artist_names}, but couldn't open browser: {str(e)}\nURL: {url}"

    elif service == "amazon_music":
        # Amazon Music web search URL
        search_url = f"https://music.amazon.com/search/{requests.utils.quote(query)}"

        # Sync lights for Amazon Music too
        light_sync_msg = ""
        if BRIDGE_IP and HUE_USERNAME:
            try:
                mood = get_music_mood(query)
                apply_mood_to_lights(mood)
                light_sync_msg = f"\n💡 Lights synced to '{mood}' mood"
            except Exception:
                pass

        try:
            webbrowser.open(search_url)
            return f"🎵 Opening Amazon Music search for '{query}'{light_sync_msg}"
        except Exception as e:
            return f"Couldn't open Amazon Music: {str(e)}"

    else:
        return f"Unknown music service: {service}"


def search_music_info(query: str) -> str:
    """Search for music and return info without playing."""
    print(f"   [SEARCH] Searching for music info: '{query}'")

    results = search_youtube_music(query, limit=5)

    if not results:
        return f"Couldn't find any songs matching '{query}'"

    # Format results
    formatted_results = []
    for i, song in enumerate(results, 1):
        title = song.get('title', 'Unknown')
        artists = song.get('artists', [])
        artist_names = ", ".join([a.get('name', '') for a in artists]) if artists else "Unknown"
        album = song.get('album', {}).get('name', '') if song.get('album') else ''
        duration = song.get('duration', '')

        result_str = f"{i}. '{title}' by {artist_names}"
        if album:
            result_str += f" (Album: {album})"
        if duration:
            result_str += f" - {duration}"

        formatted_results.append(result_str)

    return "[MUSIC] Found these songs:\n\n" + "\n".join(formatted_results)


def control_music(action: str) -> str:
    """
    Control music playback using SYSTEM-WIDE media keys.
    Works from ANY window - no need to focus YouTube Music!

    Args:
        action: Control action - "pause", "resume", "next", "previous", "volume_up", "volume_down"
    """
    print(f"   [MUSIC] Controlling music: {action}")

    try:
        import pyautogui
    except ImportError:
        return "Music control requires pyautogui. Install with: pip install pyautogui"

    action_lower = action.lower()

    # FIXED: Use system-wide media keys instead of application-specific shortcuts
    # These work regardless of which window has focus!

    if action_lower in ["pause", "resume", "play_pause"]:
        # Use the system media play/pause key
        try:
            pyautogui.press('playpause')
            return "🎵 Toggled play/pause"
        except Exception:
            # Fallback for systems that don't recognize 'playpause'
            try:
                pyautogui.press('play')
                return "🎵 Toggled play/pause"
            except Exception:
                return "⚠️ Media key not supported on this system"

    elif action_lower == "next":
        # Use the system next track media key
        try:
            pyautogui.press('nexttrack')
            return "🎵 Skipped to next track"
        except Exception:
            return "⚠️ Next track key not supported on this system"

    elif action_lower == "previous":
        # Use the system previous track media key
        try:
            pyautogui.press('prevtrack')
            return "🎵 Went to previous track"
        except Exception:
            return "⚠️ Previous track key not supported on this system"

    elif action_lower == "volume_up":
        # Use system volume up key
        try:
            pyautogui.press('volumeup')
            return "🎵 Volume increased"
        except Exception:
            return "⚠️ Volume key not supported on this system"

    elif action_lower == "volume_down":
        # Use system volume down key
        try:
            pyautogui.press('volumedown')
            return "🎵 Volume decreased"
        except Exception:
            return "⚠️ Volume key not supported on this system"

    elif action_lower == "mute":
        # Use system mute key
        try:
            pyautogui.press('volumemute')
            return "🎵 Toggled mute"
        except Exception:
            return "⚠️ Mute key not supported on this system"

    else:
        return f"Unknown music control action: {action}. Available: pause, resume, next, previous, volume_up, volume_down, mute"


# ===== MUSIC VISUALIZER (ADVANCED FEATURE) =====

# Global variable to track visualizer state
_visualizer_active = False
_visualizer_thread = None

# Global variable to store images that need to be shown to vision model
# ================================================================================
# VISION IMAGE QUEUE SYSTEM (Improved)
# ================================================================================
from dataclasses import dataclass
from typing import Set

@dataclass
class ImageInfo:
    """Information about an image to be shown to the vision model."""
    filename: str
    filepath: str
    hash: str
    is_camera_capture: bool
    added_at: str

class VisionImageQueue:
    """
    Manages the queue of images to be shown to the vision model.

    IMPROVEMENTS:
    - Separates NEW images from OLD images
    - Tracks which images have been viewed
    - Prevents showing the same image multiple times
    - Purges old camera captures from conversation context
    """

    def __init__(self):
        self.pending_images: List[ImageInfo] = []
        self.viewed_images: Set[str] = set()

    def clear(self):
        """Clear all pending images."""
        print(f"   [VISION-QUEUE] Clearing {len(self.pending_images)} pending images")
        self.pending_images = []

    def add_image(self, filepath: str, filename: str, is_camera: bool = False):
        """Add an image to the queue to be shown."""
        import hashlib
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        img_hash = hash_md5.hexdigest()

        if is_camera:
            # Clear old camera images
            self.pending_images = [img for img in self.pending_images
                                  if not img.is_camera_capture]
            print(f"   [VISION-QUEUE] New camera image, cleared old camera images")

        if img_hash not in self.viewed_images:
            import datetime
            self.pending_images.append(ImageInfo(
                filename=filename,
                filepath=filepath,
                hash=img_hash,
                is_camera_capture=is_camera,
                added_at=datetime.datetime.now().isoformat()
            ))
            print(f"   [VISION-QUEUE] Added {filename} (hash: {img_hash[:8]})")
        else:
            print(f"   [VISION-QUEUE] Skipped {filename} - already viewed")

    def mark_as_viewed(self):
        """Mark all current pending images as viewed."""
        for img in self.pending_images:
            self.viewed_images.add(img.hash)
        print(f"   [VISION-QUEUE] Marked {len(self.pending_images)} images as viewed")

    def has_images(self) -> bool:
        """Check if there are pending images."""
        return len(self.pending_images) > 0

_vision_queue = VisionImageQueue()


def start_music_visualizer(duration_seconds: int = 300, style: str = "party") -> str:
    """
    Start a dynamic light show that changes colors rhythmically.
    Creates an atmospheric visualizer effect for music.

    Args:
        duration_seconds: How long to run (default 5 minutes)
        style: "party" (fast colorful), "chill" (slow smooth), "pulse" (rhythmic)
    """
    global _visualizer_active, _visualizer_thread

    if not BRIDGE_IP or not HUE_USERNAME:
        return "Hue lights not configured. Can't start visualizer."

    if _visualizer_active:
        return "Music visualizer is already running! Say 'stop visualizer' to turn it off first."

    print(f"   [SYNC] Starting {style} music visualizer for {duration_seconds} seconds")

    def visualizer_loop():
        global _visualizer_active
        lights = get_hue_lights()
        if not lights:
            _visualizer_active = False
            return

        light_ids = list(lights.keys())
        start_time = time.time()

        # Different color schemes based on style
        if style == "party":
            color_options = [
                {"hue": 0, "sat": 254, "bri": 254},      # Red
                {"hue": 46920, "sat": 254, "bri": 254},  # Blue
                {"hue": 25500, "sat": 254, "bri": 254},  # Green
                {"hue": 12750, "sat": 254, "bri": 254},  # Yellow
                {"hue": 50000, "sat": 254, "bri": 254},  # Purple
                {"hue": 56100, "sat": 254, "bri": 254},  # Pink
                {"hue": 30000, "sat": 254, "bri": 254},  # Cyan
                {"hue": 5000, "sat": 254, "bri": 254},   # Orange
            ]
            transition_time = 5
            change_interval = 1.5
        elif style == "chill":
            color_options = [
                {"hue": 46920, "sat": 200, "bri": 150},  # Soft blue
                {"hue": 50000, "sat": 180, "bri": 130},  # Soft purple
                {"hue": 30000, "sat": 190, "bri": 140},  # Soft cyan
                {"hue": 25500, "sat": 160, "bri": 120},  # Soft green
            ]
            transition_time = 20
            change_interval = 4.0
        elif style == "pulse":
            color_options = [
                {"hue": 0, "sat": 254, "bri": 254},      # Bright red
                {"hue": 0, "sat": 254, "bri": 100},      # Dim red
                {"hue": 46920, "sat": 254, "bri": 254},  # Bright blue
                {"hue": 46920, "sat": 254, "bri": 100},  # Dim blue
            ]
            transition_time = 3
            change_interval = 0.8
        else:
            color_options = [
                {"hue": 0, "sat": 254, "bri": 254},
                {"hue": 46920, "sat": 254, "bri": 254},
            ]
            transition_time = 5
            change_interval = 2.0

        try:
            while _visualizer_active and (time.time() - start_time) < duration_seconds:
                for light_id in light_ids:
                    # Random color for each light
                    color = random.choice(color_options).copy()
                    color["on"] = True
                    color["transitiontime"] = transition_time
                    control_hue_light(light_id, color)

                time.sleep(change_interval)
        finally:
            _visualizer_active = False
            print("   [SYNC] Music visualizer ended")

    # Start visualizer
    _visualizer_active = True
    _visualizer_thread = threading.Thread(target=visualizer_loop, daemon=True)
    _visualizer_thread.start()

    style_descriptions = {
        "party": "fast, vibrant colors",
        "chill": "slow, smooth transitions",
        "pulse": "rhythmic pulsing"
    }

    return f"🎨 Music visualizer started ({style_descriptions.get(style, 'dynamic')})! Lights will dance for {duration_seconds//60} minutes."


def stop_music_visualizer() -> str:
    """Stop the music visualizer."""
    global _visualizer_active

    if not _visualizer_active:
        return "No visualizer is currently running."

    _visualizer_active = False
    print("   [SYNC] Stopping music visualizer...")

    # Wait a moment for thread to finish
    time.sleep(1)

    return "🎨 Music visualizer stopped."


# Tool definitions with MOOD, DOCUMENT, MUSIC, and VISUALIZER support!
TOOLS = [
    # ===== Enhanced Tools - Calendar & Reminders =====
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": "Create a reminder for a user with natural language time parsing (e.g., 'tomorrow at 3pm', 'in 2 hours', 'next Monday')",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_name": {"type": "string", "description": "Who the reminder is for (Alex, Stella, Emmy, Athena, or Vilda)"},
                    "title": {"type": "string", "description": "Short reminder title"},
                    "when": {"type": "string", "description": "When to remind - supports natural language like 'tomorrow at 3pm', 'in 2 hours', 'next Monday at 9am', 'tonight'"},
                    "description": {"type": "string", "description": "Optional detailed description"}
                },
                "required": ["user_name", "title", "when"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_upcoming_reminders",
            "description": "Get upcoming reminders for a user",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_name": {"type": "string"},
                    "hours_ahead": {"type": "integer", "description": "Look ahead this many hours (default 24)"}
                },
                "required": ["user_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete_reminder",
            "description": "Mark a reminder as completed",
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder_id": {"type": "integer", "description": "ID of the reminder to complete"}
                },
                "required": ["reminder_id"]
            }
        }
    },

    # ===== Enhanced Tools - Task Management =====
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a task or to-do item",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_name": {"type": "string"},
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Optional detailed description"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"], "description": "Task priority"},
                    "due_date": {"type": "string", "description": "Due date in natural language or ISO format"},
                    "category": {"type": "string", "description": "Task category (work, personal, shopping, etc.)"}
                },
                "required": ["user_name", "title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_tasks",
            "description": "Get tasks for a user",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_name": {"type": "string"},
                    "status": {"type": "string", "enum": ["pending", "completed"], "description": "Filter by status"}
                },
                "required": ["user_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": "Mark a task as completed",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer"}
                },
                "required": ["task_id"]
            }
        }
    },

    # ===== Enhanced Tools - Notes =====
    {
        "type": "function",
        "function": {
            "name": "create_note",
            "description": "Save a note or memo",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_name": {"type": "string"},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "category": {"type": "string", "description": "Note category"}
                },
                "required": ["user_name", "title", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_notes",
            "description": "Search through saved notes",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_name": {"type": "string"},
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["user_name", "query"]
            }
        }
    },

    # ===== Enhanced Tools - Timers =====
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": "Set a countdown timer",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_minutes": {"type": "integer", "description": "Timer duration in minutes"},
                    "label": {"type": "string", "description": "Timer name/label"}
                },
                "required": ["duration_minutes"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_timers",
            "description": "Check status of all active timers",
            "parameters": {"type": "object", "properties": {}}
        }
    },

    # ===== Enhanced Tools - System Control =====
    {
        "type": "function",
        "function": {
            "name": "get_system_info",
            "description": "Get computer system information (CPU, memory, disk usage)",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Capture a screenshot of the screen",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Optional filename for the screenshot"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "launch_application",
            "description": "Launch an application (browser, calculator, notepad, terminal, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Application name (chrome, firefox, calculator, notepad, terminal, vscode, spotify)"}
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Set system volume level",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {"type": "integer", "description": "Volume level 0-100"}
                },
                "required": ["level"]
            }
        }
    },

    # ===== Enhanced Tools - File Operations =====
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Directory path"},
                    "pattern": {"type": "string", "description": "File pattern like *.pdf or *.txt"},
                    "recursive": {"type": "boolean", "description": "Search subdirectories"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a text file",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the file"}
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["filepath", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_info",
            "description": "Get detailed information about a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string"}
                },
                "required": ["filepath"]
            }
        }
    },

    # ===== Enhanced Tools - Educational & Storytelling =====
    {
        "type": "function",
        "function": {
            "name": "story_prompt",
            "description": "Generate an age-appropriate story prompt for a child (Emmy age 10, Athena age 8, or Vilda age 5)",
            "parameters": {
                "type": "object",
                "properties": {
                    "child_name": {"type": "string", "enum": ["Emmy", "Athena", "Vilda"], "description": "Child's name"},
                    "theme": {"type": "string", "description": "Story theme (animals, adventure, magic, etc.)"},
                    "moral": {"type": "string", "description": "Moral or lesson to teach"},
                    "length": {"type": "string", "enum": ["short", "medium", "long"]}
                },
                "required": ["child_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "educational_activity",
            "description": "Suggest an age-appropriate educational activity",
            "parameters": {
                "type": "object",
                "properties": {
                    "child_name": {"type": "string", "enum": ["Emmy", "Athena", "Vilda"]},
                    "subject": {"type": "string", "enum": ["math", "science", "reading", "art", "writing"]}
                },
                "required": ["child_name", "subject"]
            }
        }
    },

    # ===== Enhanced Tools - Location & Time =====
    {
        "type": "function",
        "function": {
            "name": "get_local_time",
            "description": "Get current local time and date",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sunrise_sunset",
            "description": "Get sunrise and sunset times for today",
            "parameters": {"type": "object", "properties": {}}
        }
    },

    {
        "type": "function",
        "function": {
            "name": "play_music",
            "description": "START playing new music. USE THIS when user wants to: play a song, play an artist, 'put on some music'. DO NOT USE for: pausing, skipping, or volume control (use control_music for those).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Song name, artist, or search query (e.g., 'Bohemian Rhapsody', 'Taylor Swift Shake It Off', 'relaxing jazz')"
                    },
                    "action": {
                        "type": "string",
                        "enum": ["play", "search"],
                        "description": "'play' to play the song, 'search' to just find information without playing",
                        "default": "play"
                    },
                    "service": {
                        "type": "string",
                        "enum": ["youtube_music", "amazon_music"],
                        "description": "Music service to use",
                        "default": "youtube_music"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_music",
            "description": "CONTROL current playback. USE THIS for: pause, resume, skip, next, previous, volume up/down, mute. Works system-wide. DO NOT USE for: playing new music (use play_music to start playing something).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["pause", "resume", "play_pause", "next", "previous", "volume_up", "volume_down", "mute"],
                        "description": "Control action: 'pause' or 'resume' (toggle play/pause), 'next' (skip forward), 'previous' (skip back), 'volume_up', 'volume_down', 'mute'"
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "music_visualizer",
            "description": "Start LIGHT SHOW synced to music. USE THIS when user wants: light show, lights to dance, party lights, sync lights with music. DO NOT USE for: regular light control like turning on/off or setting color (use control_lights for those).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["start", "stop"],
                        "description": "'start' to begin visualizer, 'stop' to end it"
                    },
                    "duration": {
                        "type": "integer",
                        "description": "How long to run the visualizer in seconds (default: 300 = 5 minutes)",
                        "default": 300
                    },
                    "style": {
                        "type": "string",
                        "enum": ["party", "chill", "pulse"],
                        "description": "Visualizer style: 'party' (fast colorful), 'chill' (slow smooth), 'pulse' (rhythmic)",
                        "default": "party"
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search USER'S UPLOADED documents (PDFs, Word docs, text files). USE THIS when user asks about: 'my documents', 'my files', 'my contract', 'what does my document say', 'search my files'. DO NOT USE for: internet searches or general knowledge (use web_search for those).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant information in documents"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 3)",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_lights",
            "description": "Control Philips Hue lights. USE THIS for: turn on/off, change brightness, set color, set mood/scene (sunset, relax, etc). DO NOT USE for: music-synced light shows (use music_visualizer for 'light show' or 'lights dance').",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["on", "off", "brightness", "color", "mood", "status"],
                        "description": "Action: 'on', 'off', 'brightness', 'color', 'mood' (apply atmospheric scene), 'status'"
                    },
                    "light_name": {
                        "type": "string",
                        "description": "Specific light name (optional, controls all if empty)"
                    },
                    "brightness": {
                        "type": "integer",
                        "description": "Brightness 0-100 (for brightness action)"
                    },
                    "color": {
                        "type": "string",
                        "description": "Color name: red, blue, green, yellow, orange, purple, pink, white, warm white, cool white"
                    },
                    "mood": {
                        "type": "string",
                        "description": "Mood/scene name: moonlight, sunset, ocean, forest, romance, party, focus, relax, energize, movie, fireplace, arctic, sunrise, galaxy, tropical"
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather and forecast",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"}
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the INTERNET for external information. USE THIS for: current events, news, general knowledge queries, 'search for X', 'google X', 'latest news about X'. DO NOT USE for: user's personal documents (use search_documents for 'my documents', 'my files', 'my contract').",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_javascript",
            "description": "Execute JavaScript code",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "JavaScript code"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_document",
            "description": "Create and save a new document (text, markdown, or code file) to the documents folder. The user can then download it from the web interface at http://127.0.0.1:5000/documents",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file to create (e.g., 'report.txt', 'notes.md', 'recipe.txt')"
                    },
                    "content": {
                        "type": "string",
                        "description": "The text content to write to the file"
                    },
                    "file_type": {
                        "type": "string",
                        "enum": ["txt", "md", "json", "csv", "html"],
                        "description": "File type (default: txt). Options: txt (plain text), md (markdown), json, csv, html",
                        "default": "txt"
                    }
                },
                "required": ["filename", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_gmail",
            "description": "CHECK/READ emails from inbox. USE THIS when user wants to: check email, read inbox, show messages, see unread emails, find specific emails. DO NOT USE for: sending new emails (use send_gmail) or replying to emails (use reply_gmail).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Optional search query (e.g., 'from:john@example.com', 'subject:meeting', 'is:unread'). Leave empty to get recent emails."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of emails to return (default: 10)",
                        "default": 10
                    },
                    "include_body": {
                        "type": "boolean",
                        "description": "Whether to include full email body (default: true)",
                        "default": True
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_gmail",
            "description": "SEND/COMPOSE a NEW email. USE THIS when user wants to: send email to someone, compose new message, email an address. REQUIRES: recipient email address (extract from user message - look for name@domain.com format). DO NOT USE for: checking inbox (use read_gmail) or replying to existing emails (use reply_gmail).",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject line"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body text"
                    },
                    "cc": {
                        "type": "string",
                        "description": "Optional CC email addresses (comma-separated)"
                    },
                    "bcc": {
                        "type": "string",
                        "description": "Optional BCC email addresses (comma-separated)"
                    },
                    "attachments": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Optional list of filenames to attach from documents folder. Example: ['report.pdf', 'data.xlsx']"
                    }
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reply_gmail",
            "description": "REPLY to an EXISTING email. USE THIS when user wants to: reply to, respond to, or answer existing emails. IMPORTANT: For fanmail replies, FIRST use read_gmail to see the email content, THEN use this to reply with a contextual response. DO NOT USE for: checking inbox (use read_gmail) or sending new emails (use send_gmail).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find emails to reply to (e.g., 'subject:Fanmail', 'from:john@example.com is:unread'). Required to find which emails to reply to."
                    },
                    "reply_body": {
                        "type": "string",
                        "description": "The reply message body text. Should be contextual and personalized based on the original email content."
                    },
                    "reply_all": {
                        "type": "boolean",
                        "description": "If true, reply to all emails matching the query. If false, only reply to the first match. Default: false",
                        "default": False
                    },
                    "max_replies": {
                        "type": "integer",
                        "description": "Maximum number of emails to reply to (default: 10, max: 50)",
                        "default": 10
                    }
                },
                "required": ["query", "reply_body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "view_image",
            "description": "View and analyze image files from the uploaded documents. Use this when user asks about a specific image, wants to see an image, or references an uploaded photo/screenshot/diagram. This allows you (the vision model) to see the actual image content. You can view images by filename or search for them. Use this for: 'show me the image', 'what's in photo.jpg', 'look at the screenshot', 'analyze the diagram I uploaded', 'view the picture'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the image file to view (e.g., 'photo.jpg', 'screenshot.png'). If not provided, will search for images by query."
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query to find images if filename not provided (e.g., 'family photo', 'diagram', 'screenshot')"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "capture_camera",
            "description": "Look at what's in front of you right now by capturing a camera view. Use this when the user asks what you see, what's in front of you, or any question about your physical surroundings. After capturing, you'll see your current environment and can naturally discuss what's there - just like looking around a room and talking about it. Always capture a fresh view when asked about your surroundings.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remember_person",
            "description": "Learn and remember information about a person you see. Use this when the user tells you who someone is or provides information about a person. This helps you recognize them in the future.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The person's name"
                    },
                    "appearance": {
                        "type": "string",
                        "description": "Description of how they typically look (e.g., 'woman with long brown hair', 'man with beard and glasses')"
                    },
                    "relationship": {
                        "type": "string",
                        "description": "Their relationship to the household (e.g., 'family member', 'friend', 'neighbor')"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Any additional context or information about this person"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remember_place",
            "description": "Learn and remember information about a location or room you see. Use this when the user tells you about a place or provides context about a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the place (e.g., 'Alex's Office', 'Living Room', 'Kitchen')"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of this place and its purpose"
                    },
                    "typical_contents": {
                        "type": "string",
                        "description": "What is typically found in this location"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Any additional context about this place"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "who_do_i_know",
            "description": "List all the people you know and can recognize. Use this when asked who you know or to see your visual memory of people.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_with_chat_theory",
            "description": "Analyze a topic through Cultural-Historical Activity Theory (CHAT) lens. Use this when Alex asks to apply CHAT framework to something, or for academic analysis of technology/education topics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic to analyze"
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context about the situation"
                    }
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "prepare_lecture",
            "description": "Generate a lecture outline for teaching. Use when Alex needs to prepare for class or wants help structuring a lecture.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The lecture topic"
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Lecture duration in minutes (default 50)"
                    },
                    "course": {
                        "type": "string",
                        "description": "Course name or context"
                    },
                    "level": {
                        "type": "string",
                        "description": "Student level: undergraduate, graduate, etc."
                    }
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "discussion_questions",
            "description": "Generate discussion questions for a reading or topic. Use when Alex is preparing for class discussion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reading": {
                        "type": "string",
                        "description": "The reading or text to generate questions about"
                    },
                    "topic": {
                        "type": "string",
                        "description": "The topic or theme"
                    }
                },
                "required": ["reading", "topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "simulate_student_questions",
            "description": "Simulate likely student questions and provide teaching strategies. Use when Alex is preparing to teach a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic being taught"
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context about the lesson"
                    }
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_proactive_suggestions",
            "description": "Check if there are any helpful proactive suggestions based on patterns and context. Use when checking in or when appropriate time has passed.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


# ===== DOCUMENT MANAGEMENT FUNCTIONS =====

def load_document_index() -> Dict:
    """Load the document index from disk."""
    if os.path.exists(DOCUMENT_INDEX_FILE):
        try:
            with open(DOCUMENT_INDEX_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"documents": []}


def save_document_index(index: Dict):
    """Save the document index to disk."""
    with open(DOCUMENT_INDEX_FILE, 'w') as f:
        json.dump(index, f, indent=2)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def ensure_unique_path(directory: str, filename: str) -> str:
    """Ensure a unique file path by adding numbers if file already exists.

    Args:
        directory: Directory where file will be saved
        filename: Original filename

    Returns:
        Unique file path
    """
    base_path = os.path.join(directory, secure_filename(filename))

    # If file doesn't exist, return as-is
    if not os.path.exists(base_path):
        return base_path

    # File exists, add number suffix
    name, ext = os.path.splitext(filename)
    counter = 1

    while True:
        new_filename = f"{name}_{counter}{ext}"
        new_path = os.path.join(directory, secure_filename(new_filename))

        if not os.path.exists(new_path):
            return new_path

        counter += 1

        # Safety check to prevent infinite loop
        if counter > 9999:
            # Use timestamp as last resort
            import time
            timestamp = int(time.time())
            new_filename = f"{name}_{timestamp}{ext}"
            return os.path.join(directory, secure_filename(new_filename))


def get_file_hash(filepath):
    """Get MD5 hash of file for deduplication."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def encode_image_to_base64(filepath: str) -> Optional[Dict[str, Any]]:
    """Encode an image file to base64 for vision model viewing.

    Returns a dict with image data suitable for vision models, or None if error.
    Format: {
        "type": "image_url",
        "image_url": {
            "url": "data:image/jpeg;base64,..."
        }
    }
    """
    ext = filepath.rsplit('.', 1)[1].lower()
    if ext not in ['png', 'jpg', 'jpeg', 'tiff', 'bmp', 'gif', 'webp']:
        return None

    try:
        import base64
        with open(filepath, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        # Map extensions to MIME types
        mime_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'bmp': 'image/bmp',
            'tiff': 'image/tiff'
        }

        mime_type = mime_types.get(ext, 'image/jpeg')

        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{image_data}"
            }
        }
    except Exception as e:
        print(f"   [ERROR] Failed to encode image {filepath}: {e}")
        return None


def extract_text_from_file(filepath: str) -> str:
    """Extract text from various file types. For images, returns metadata since vision model will view them directly."""
    ext = filepath.rsplit('.', 1)[1].lower()

    if ext == 'txt' or ext == 'md':
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    elif ext == 'pdf':
        try:
            import PyPDF2
            text = []
            with open(filepath, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text.append(page.extract_text())
            return '\n'.join(text)
        except ImportError:
            return "Error: PyPDF2 not installed. Install with: pip install PyPDF2"
        except Exception as e:
            return f"Error extracting PDF: {str(e)}"

    elif ext in ['doc', 'docx']:
        try:
            import docx
            doc = docx.Document(filepath)
            return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        except ImportError:
            return "Error: python-docx not installed. Install with: pip install python-docx"
        except Exception as e:
            return f"Error extracting Word doc: {str(e)}"

    elif ext in ['png', 'jpg', 'jpeg', 'tiff', 'bmp', 'gif', 'webp']:
        # Image file - store metadata for vision model to view directly
        try:
            from PIL import Image
            image = Image.open(filepath)
            width, height = image.size
            mode = image.mode
            file_size = os.path.getsize(filepath)

            return (f"[IMAGE FILE - Vision model will view directly]\n"
                    f"Dimensions: {width}x{height}\n"
                    f"Color mode: {mode}\n"
                    f"File size: {file_size} bytes\n"
                    f"Format: {ext.upper()}")
        except ImportError:
            return f"[IMAGE FILE] {os.path.basename(filepath)} - PIL required to read metadata"
        except Exception as e:
            return f"[IMAGE FILE] {os.path.basename(filepath)} - Error reading: {str(e)}"

    return "Unsupported file type"


def add_document_to_rag(filepath: str, filename: str) -> bool:
    """Add a document to LM Studio's RAG system."""
    try:
        # Extract text from the file
        text_content = extract_text_from_file(filepath)

        if text_content.startswith("Error"):
            print(f"   [ERROR] {text_content}")
            return False

        # Send to LM Studio RAG endpoint
        payload = {
            "file_path": str(filepath),
            "content": text_content,
            "metadata": {
                "filename": filename,
                "source": "blue_middleware"
            }
        }

        response = requests.post(
            f"{LM_STUDIO_RAG_URL}/documents",
            json=payload,
            timeout=30
        )

        if response.status_code in [200, 201]:
            print(f"   [OK] Document indexed in RAG system")
            return True
        else:
            print(f"   [WARN]  RAG indexing returned: {response.status_code}")
            # Still return True to allow local indexing
            return True

    except requests.exceptions.RequestException as e:
        print(f"   [WARN]  RAG system not available: {e}")
        # Continue anyway - we'll store locally
        return True
    except Exception as e:
        print(f"   [ERROR] Error adding to RAG: {e}")
        return False


def search_documents_rag(query: str, max_results: int = 3) -> str:
    """Search documents using LM Studio's RAG system."""
    print(f"   [FIND] Searching documents for: '{query}'")
    print(f"   [NET] RAG endpoint: {LM_STUDIO_RAG_URL}/search")

    try:
        # Try to use LM Studio's RAG search
        payload = {
            "query": query,
            "max_results": max_results
        }

        print(f"   [OUT] Sending request to RAG...")
        response = requests.post(
            f"{LM_STUDIO_RAG_URL}/search",
            json=payload,
            timeout=10
        )

        print(f"   [IN] RAG response status: {response.status_code}")

        if response.status_code == 200:
            try:
                results = response.json()
                print(f"   [DATA] RAG response type: {type(results)}")
                print(f"   [DATA] RAG response preview: {str(results)[:200]}")

                # Handle different possible response structures
                # Case 1: Response is a dict with 'results' key
                if isinstance(results, dict):
                    if 'results' in results:
                        results = results['results']
                    elif 'data' in results:
                        results = results['data']
                    elif 'documents' in results:
                        results = results['documents']

                # Case 2: Response is already a list
                if isinstance(results, list) and len(results) > 0:
                    print(f"   [DATA] RAG returned {len(results)} result(s)")
                    formatted_results = []

                    for i, result in enumerate(results[:max_results], 1):
                        # Handle different result structures
                        if isinstance(result, dict):
                            filename = result.get('metadata', {}).get('filename', 'Unknown')
                            if not filename or filename == 'Unknown':
                                filename = result.get('filename', result.get('source', 'Unknown'))

                            content = result.get('content', result.get('text', result.get('body', '')))
                            score = result.get('score', result.get('relevance', result.get('similarity', 0)))

                            # Safely truncate content
                            if content:
                                content_preview = str(content)[:500] if len(str(content)) > 500 else str(content)
                            else:
                                content_preview = "No content available"

                            formatted_results.append(
                                f"[{i}] From: {filename} (relevance: {score:.2f})\n{content_preview}"
                            )
                        elif isinstance(result, str):
                            # Result is just a string
                            formatted_results.append(f"[{i}] {result[:500]}")
                        else:
                            formatted_results.append(f"[{i}] {str(result)[:500]}")

                    if formatted_results:
                        print(f"   [OK] Formatted {len(formatted_results)} document results")
                        return "Here's what I found in your documents:\n\n" + "\n\n".join(formatted_results)

                # No valid results found
                print(f"   [WARN]  No valid results from RAG, trying local search...")
                return search_documents_local(query, max_results)

            except (ValueError, KeyError, TypeError) as e:
                print(f"   [WARN]  Error parsing RAG response: {e}")
                print(f"   [ITER] Falling back to local search...")
                return search_documents_local(query, max_results)
        else:
            print(f"   [WARN]  RAG returned non-200 status, trying local search...")
            return search_documents_local(query, max_results)

    except requests.exceptions.RequestException as e:
        print(f"   [WARN]  RAG connection error: {e}")
        print(f"   [ITER] Falling back to local search...")
        return search_documents_local(query, max_results)
    except Exception as e:
        print(f"   [ERROR] Unexpected error: {e}")
        print(f"   [ITER] Falling back to local search...")
        return search_documents_local(query, max_results)


def search_documents_local(query: str, max_results: int = 3) -> str:
    """Fallback: Simple local search through document index. Returns JSON for images."""
    print(f"   [FOLDER] Using local document search...")
    index = load_document_index()
    documents = index.get("documents", [])

    print(f"   [DATA] Found {len(documents)} documents in local index")

    if not documents:
        print(f"   [WARN]  No documents uploaded yet!")
        return (
            "I don't have any documents to search through yet! "
            "You can upload documents at http://127.0.0.1:5000/documents - "
            "I can read PDFs, Word docs, text files, markdown, and images. "
            "Once you upload some documents, I'll be able to answer questions about them!"
        )

    query_lower = query.lower()
    matches = []

    # Special handling for "all documents" or "summarize all" queries
    if "all" in query_lower and ("document" in query_lower or "summarize" in query_lower or "image" in query_lower):
        print(f"   [LIST] Query asks for ALL documents, listing them...")
        doc_list = []
        for i, doc in enumerate(documents[:10], 1):
            preview = doc.get('text_preview', 'No preview available')[:200]
            doc_list.append(f"{i}. {doc['filename']}\n   Preview: {preview}...")

        summary = "\n\n".join(doc_list)
        if len(documents) > 10:
            summary += f"\n\n...and {len(documents) - 10} more documents."

        return f"I have {len(documents)} document(s) uploaded:\n\n{summary}"

    # Search through documents
    for doc in documents:
        relevance = 0
        filename_lower = doc['filename'].lower()

        # Check filename
        if query_lower in filename_lower:
            relevance += 3

        # Check cached text content
        text_content = doc.get('text_preview', '').lower()
        if query_lower in text_content:
            relevance += 5

        # Check individual query words
        for word in query_lower.split():
            if len(word) > 3:
                if word in filename_lower:
                    relevance += 1
                if word in text_content:
                    relevance += 2

        if relevance > 0:
            matches.append((doc, relevance))

    print(f"   [TARGET] Found {len(matches)} matching documents")

    if not matches:
        return (
            f"I couldn't find any documents matching '{query}'. "
            f"I have {len(documents)} document(s) uploaded. "
            "Try using different keywords, or ask me to list all documents."
        )

    # Sort by relevance
    matches.sort(key=lambda x: x[1], reverse=True)

    # Check if results include images - if so, return special format
    has_images = False
    image_results = []
    text_results = []

    for doc, score in matches[:max_results]:
        filepath = doc.get('filepath', '')
        filename = doc['filename']
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

        if ext in ['png', 'jpg', 'jpeg', 'tiff', 'bmp', 'gif', 'webp']:
            has_images = True
            if os.path.exists(filepath):
                image_results.append({
                    'filename': filename,
                    'filepath': filepath,
                    'score': score
                })
                print(f"   [IMAGE] Found image: {filename}")
        else:
            # Text document - extract content
            print(f"   [FILE] Extracting full text from: {filename}")

            if os.path.exists(filepath):
                try:
                    full_text = extract_text_from_file(filepath)

                    # If the file is very long, try to find relevant sections
                    if len(full_text) > 3000:
                        # Split into paragraphs/sections
                        sections = full_text.split('\n\n')
                        relevant_sections = []

                        for section in sections:
                            section_lower = section.lower()
                            # Check if this section contains query terms
                            if any(word in section_lower for word in query_lower.split() if len(word) > 3):
                                relevant_sections.append(section)

                        if relevant_sections:
                            # Return most relevant sections (up to 2000 chars)
                            combined = '\n\n'.join(relevant_sections[:5])
                            content = combined[:2000] if len(combined) > 2000 else combined
                        else:
                            # No specific sections found, return first part
                            content = full_text[:2000]
                    else:
                        # File is short enough, return it all
                        content = full_text

                    text_results.append(f"[FILE] **{filename}** (relevance: {score})\n\n{content}\n")

                except Exception as e:
                    print(f"   [WARN]  Error reading {filename}: {e}")
                    # Fall back to preview
                    preview = doc.get('text_preview', 'No preview available')[:500]
                    text_results.append(f"[FILE] **{filename}** (relevance: {score})\n\n{preview}...\n")
            else:
                # File not found, use preview
                preview = doc.get('text_preview', 'No preview available')[:500]
                text_results.append(f"[FILE] **{filename}** (relevance: {score})\n\n{preview}...\n")

    # If we found images, return special JSON format
    if has_images:
        result = {
            "_type": "document_search_with_images",
            "images": image_results,
            "text_documents": text_results
        }
        print(f"   [OK] Returning {len(image_results)} image(s) and {len(text_results)} text document(s)")
        return json.dumps(result)

    # No images, return text results as before
    print(f"   [OK] Returning {len(text_results)} document(s) with full content")
    return "Here's what I found in your documents:\n\n" + "\n---\n\n".join(text_results)


def view_image(filename: str = None, query: str = None) -> str:
    """View an image file for the vision model to analyze.

    Args:
        filename: Specific image filename to view
        query: Search query if filename not provided

    Returns:
        JSON string with image information for vision model injection
    """
    global _vision_queue

    print(f"   [VIEW] Request to view image - filename: {filename}, query: {query}")

    # Load document index
    index = load_document_index()
    documents = index.get("documents", [])

    # Filter to only image files
    image_docs = [
        doc for doc in documents
        if doc['filename'].lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'))
    ]

    if not image_docs:
        return json.dumps({
            "success": False,
            "message": "No images found in uploaded documents. Upload images at http://127.0.0.1:5000/documents/upload"
        })

    print(f"   [DATA] Found {len(image_docs)} total image(s) in documents")

    # Find the requested image
    found_images = []

    if filename:
        # Search by exact or partial filename match
        filename_lower = filename.lower()
        for doc in image_docs:
            doc_filename_lower = doc['filename'].lower()
            if doc_filename_lower == filename_lower or filename_lower in doc_filename_lower:
                found_images.append(doc)
                print(f"   [MATCH] Found by filename: {doc['filename']}")

    elif query:
        # Search by query in filename
        query_lower = query.lower()
        for doc in image_docs:
            if query_lower in doc['filename'].lower():
                found_images.append(doc)
                print(f"   [MATCH] Found by query: {doc['filename']}")

    else:
        # No filename or query - show all images
        found_images = image_docs[:3]  # Limit to 3 images at once
        print(f"   [LIST] Showing {len(found_images)} recent image(s)")

    if not found_images:
        available = ", ".join([doc['filename'] for doc in image_docs[:10]])
        return json.dumps({
            "success": False,
            "message": f"No images found matching '{filename or query}'. Available images: {available}"
        })

    # Queue images for vision model
    image_results = []
    for doc in found_images[:3]:  # Limit to 3 images at once
        filepath = doc.get('filepath', '')
        if os.path.exists(filepath):
            image_results.append({
                'filename': doc['filename'],
                'filepath': filepath,
                'score': 1.0
            })
            print(f"   [QUEUE] Queued image for viewing: {doc['filename']}")

    # Store in global pending images
    # Add images to vision queue
    global _vision_queue
    for img in image_results:
        _vision_queue.add_image(
            filepath=img['filepath'],
            filename=img['filename'],
            is_camera=False
        )
    print(f"   [VISION] Stored {len(image_results)} image(s) for vision model injection")

    # Build response
    image_names = [img['filename'] for img in image_results]

    return json.dumps({
        "success": True,
        "message": f"Viewing {len(image_results)} image(s): {', '.join(image_names)}",
        "images": image_names,
        "_instruction": "The images will be shown to you in the next message. Analyze them and respond to the user's question."
    })


def capture_camera_image() -> str:
    """
    Capture a BRAND NEW image from the camera - IMPROVED VERSION.

    CRITICAL IMPROVEMENTS:
    - Unique timestamp with milliseconds
    - Longer warmup for better quality
    - Discards first frames
    - High quality JPEG
    - Clears vision queue and adds only THIS new image
    - Returns hash for uniqueness verification
    """
    global _vision_queue

    print(f"   [CAMERA] ⚡ CAPTURING BRAND NEW IMAGE RIGHT NOW...")

    try:
        import cv2
        import datetime
        import time

        # CRITICAL: Unique timestamp with MILLISECONDS
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        # Open the camera
        camera = cv2.VideoCapture(0)

        if not camera.isOpened():
            print(f"   [ERROR] Could not open camera")
            return json.dumps({
                "success": False,
                "error": "Could not access camera. Make sure a camera is connected and not in use by another application."
            })

        # Set high quality
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)

        # Give camera MORE time to warm up and adjust (CRITICAL for quality)
        time.sleep(1.2)  # Increased from 0.8s

        # Discard first few frames (often lower quality)
        for _ in range(3):
            camera.read()
            time.sleep(0.1)

        # NOW capture the actual frame we'll use
        ret, frame = camera.read()
        camera.release()

        if not ret or frame is None:
            print(f"   [ERROR] Failed to capture frame")
            return json.dumps({
                "success": False,
                "error": "Failed to capture image from camera."
            })

        # Generate UNIQUE filename with timestamp
        filename = f"camera_NEW_{timestamp}.jpg"
        filepath = os.path.join(DOCUMENTS_FOLDER, filename)

        # Save with HIGH quality
        os.makedirs(DOCUMENTS_FOLDER, exist_ok=True)
        success = cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

        if not success:
            print(f"   [ERROR] Failed to save image")
            return json.dumps({
                "success": False,
                "error": "Failed to save captured image."
            })

        print(f"   [SAVE] ✅ NEW image saved to: {filepath}")

        # Get file info
        file_size = os.path.getsize(filepath)
        file_hash = get_file_hash(filepath)

        # Get image dimensions
        height, width = frame.shape[:2]

        # Add to document index
        index = load_document_index()
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        index['documents'].append({
            'filename': filename,
            'filepath': str(filepath),
            'size': file_size,
            'hash': file_hash,
            'uploaded_at': current_time,
            'text_preview': f"[🎥 LIVE CAMERA - {width}x{height} - Captured at {datetime.datetime.now().strftime('%I:%M:%S %p')}]",
            'indexed_in_rag': False,
            'camera_capture': True,
            'capture_timestamp': timestamp,
            'is_current_view': True
        })
        save_document_index(index)

        print(f"   [INDEX] Added NEW camera capture to document index")

        # CRITICAL: Clear queue and add ONLY this new image
        _vision_queue.clear()
        _vision_queue.add_image(filepath, filename, is_camera=True)

        print(f"   [VISION] Queued NEW camera image: {filename}")

        return json.dumps({
            "success": True,
            "message": f"📷 ✨ BRAND NEW CAMERA IMAGE captured at {datetime.datetime.now().strftime('%I:%M:%S %p')}",
            "filename": filename,
            "filepath": filepath,
            "dimensions": f"{width}x{height}",
            "timestamp": timestamp,
            "file_hash": file_hash,
            "_instruction": (
                f"Camera view captured at {datetime.datetime.now().strftime('%I:%M:%S %p')}. "
                "You'll see what's in front of you in the next message. "
                "Respond naturally about your surroundings."
            )
        })

    except ImportError:
        return json.dumps({
            "success": False,
            "error": "OpenCV (cv2) not installed. Install with: pip install opencv-python"
        })
    except Exception as e:
        print(f"   [ERROR] Camera capture failed: {e}")
        import traceback
        traceback.print_exc()
        return json.dumps({
            "success": False,
            "error": f"Camera capture failed: {str(e)}"
        })

def create_document_file(filename: str, content: str, file_type: str = "txt") -> str:
    """Create a new document and save it to the documents folder."""
    print(f"   [CREATE] Creating document: {filename}")

    try:
        # Sanitize filename
        filename = secure_filename(filename)

        # Ensure filename has correct extension
        if '.' not in filename:
            filename = f"{filename}.{file_type}"
        else:
            # Check if extension matches file_type
            ext = filename.rsplit('.', 1)[1].lower()
            if ext != file_type:
                filename = f"{filename.rsplit('.', 1)[0]}.{file_type}"

        # Create full path
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Check if file already exists
        if os.path.exists(filepath):
            # Add timestamp to make it unique
            timestamp = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')
            name_part = filename.rsplit('.', 1)[0]
            ext_part = filename.rsplit('.', 1)[1]
            filename = f"{name_part}_{timestamp}.{ext_part}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Write content to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"   [SAVE] Saved to: {filepath}")

        # Get file info
        file_size = os.path.getsize(filepath)
        file_hash = get_file_hash(filepath)

        # Add to document index
        index = load_document_index()

        # Add text file extensions to allowed extensions if not already there
        allowed_create_extensions = {'txt', 'md', 'json', 'csv', 'html'}

        index['documents'].append({
            'filename': filename,
            'filepath': str(filepath),
            'size': file_size,
            'hash': file_hash,
            'uploaded_at': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M'),
            'text_preview': content[:500] if len(content) > 500 else content,
            'indexed_in_rag': False,  # Created files are not automatically indexed in RAG
            'created_by_blue': True  # Mark as created by Blue
        })

        save_document_index(index)

        print(f"   [INDEX] Added to document index")

        download_url = f"http://127.0.0.1:5000/documents/download/{filename}"

        return (
            f"✅ Document created successfully!\n\n"
            f"📄 Filename: {filename}\n"
            f"📏 Size: {file_size} bytes\n"
            f"🔗 Download: {download_url}\n"
            f"📂 View all documents: http://127.0.0.1:5000/documents"
        )

    except Exception as e:
        print(f"   [ERROR] Error creating document: {e}")
        return f"❌ Error creating document: {str(e)}"


# ===== HUE LIGHT FUNCTIONS =====

def get_hue_lights() -> Dict:
    """Get all lights from Hue Bridge."""
    if not BRIDGE_IP or not HUE_USERNAME:
        return {}
    try:
        response = requests.get(f"http://{BRIDGE_IP}/api/{HUE_USERNAME}/lights", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"   [ERROR] Error getting lights: {e}")
    return {}


def find_light_by_name(light_name: str) -> Optional[str]:
    """Find light ID by name."""
    lights = get_hue_lights()
    light_name_lower = light_name.lower()

    for light_id, data in lights.items():
        if data.get('name', '').lower() == light_name_lower:
            return light_id

    for light_id, data in lights.items():
        if light_name_lower in data.get('name', '').lower():
            return light_id

    return None


def control_hue_light(light_id: str, state: Dict) -> bool:
    """Send state change to a specific light."""
    if not BRIDGE_IP or not HUE_USERNAME:
        return False
    try:
        response = requests.put(
            f"http://{BRIDGE_IP}/api/{HUE_USERNAME}/lights/{light_id}/state",
            json=state,
            timeout=5
        )
        return response.status_code == 200
    except Exception as e:
        print(f"   [ERROR] Error controlling light: {e}")
        return False


def apply_mood_to_lights(mood: str) -> str:
    """Apply a mood/scene to all lights."""
    print(f"   [MOOD] Applying mood: {mood}")

    if not BRIDGE_IP or not HUE_USERNAME:
        return "Hue not configured. Run setup_hue.py first!"

    mood_lower = mood.lower()
    if mood_lower not in MOOD_PRESETS:
        available = ", ".join(MOOD_PRESETS.keys())
        return f"Unknown mood '{mood}'. Available moods: {available}"

    lights = get_hue_lights()
    if not lights:
        return "Could not connect to Hue Bridge."

    mood_data = MOOD_PRESETS[mood_lower]
    settings_list = mood_data["settings"]
    light_ids = list(lights.keys())

    success_count = 0
    assignments = []

    for i, light_id in enumerate(light_ids):
        setting = settings_list[i % len(settings_list)].copy()
        setting["on"] = True
        setting["transitiontime"] = 10

        if control_hue_light(light_id, setting):
            success_count += 1
            light_name = lights[light_id]['name']
            assignments.append(light_name)

    if success_count > 0:
        description = mood_data["description"]
        return f"Applied '{mood}' mood ({description}) to {success_count} light(s): {', '.join(assignments[:3])}{'...' if len(assignments) > 3 else ''}"
    else:
        return f"Failed to apply mood '{mood}'"


def execute_light_control(action: str, light_name: str = None, brightness: int = None,
                         color: str = None, mood: str = None) -> str:
    """Execute light control commands."""
    print(f"   [LIGHT] Light control: action={action}, light={light_name}, brightness={brightness}, color={color}, mood={mood}")

    if not BRIDGE_IP or not HUE_USERNAME:
        return "Philips Hue not configured. Run setup_hue.py first!"

    lights = get_hue_lights()
    if not lights:
        return "Could not connect to Hue Bridge."

    if action == "mood":
        if mood:
            return apply_mood_to_lights(mood)
        else:
            available = ", ".join(MOOD_PRESETS.keys())
            return f"Please specify a mood. Available: {available}"

    target_lights = []
    if light_name:
        light_id = find_light_by_name(light_name)
        if light_id:
            target_lights = [(light_id, lights[light_id]['name'])]
        else:
            available = ", ".join([lights[lid]['name'] for lid in lights])
            return f"Couldn't find '{light_name}'. Available: {available}"
    else:
        target_lights = [(lid, data['name']) for lid, data in lights.items()]

    if not target_lights:
        return "No lights found."

    if action == "status":
        status_lines = []
        for light_id, name in target_lights:
            state = lights[light_id].get('state', {})
            on_status = "ON" if state.get('on', False) else "OFF"
            bri = state.get('bri', 0)
            bri_percent = int((bri / 254) * 100) if bri else 0
            status_lines.append(f"{name}: {on_status}" + (f", {bri_percent}%" if on_status == "ON" else ""))
        return "Light Status:\n" + "\n".join(status_lines)

    elif action == "on":
        success_count = sum(1 for lid, _ in target_lights if control_hue_light(lid, {"on": True}))
        names = ", ".join([n for _, n in target_lights])
        return f"Turned on: {names}" if success_count == len(target_lights) else f"Turned on {success_count}/{len(target_lights)}"

    elif action == "off":
        success_count = sum(1 for lid, _ in target_lights if control_hue_light(lid, {"on": False}))
        names = ", ".join([n for _, n in target_lights])
        return f"Turned off: {names}" if success_count == len(target_lights) else f"Turned off {success_count}/{len(target_lights)}"

    elif action == "brightness":
        if brightness is None:
            return "Please specify brightness level (0-100)"
        bri_value = max(0, min(254, int((brightness / 100) * 254)))
        success_count = sum(1 for lid, _ in target_lights if control_hue_light(lid, {"on": True, "bri": bri_value}))
        names = ", ".join([n for _, n in target_lights])
        return f"Set {names} to {brightness}%" if success_count == len(target_lights) else f"Adjusted {success_count}/{len(target_lights)}"

    elif action == "color":
        if color is None:
            return "Please specify a color"
        color_lower = color.lower()
        if color_lower not in COLOR_MAP:
            available = ", ".join(COLOR_MAP.keys())
            return f"Unknown color '{color}'. Available: {available}"
        color_settings = COLOR_MAP[color_lower].copy()
        color_settings["on"] = True
        success_count = sum(1 for lid, _ in target_lights if control_hue_light(lid, color_settings))
        names = ", ".join([n for _, n in target_lights])
        return f"Set {names} to {color}" if success_count == len(target_lights) else f"Changed {success_count}/{len(target_lights)}"

    return "Unknown action"


# ===== OTHER TOOL FUNCTIONS =====

def get_weather_data(location: str) -> str:
    """Get weather data."""
    try:
        url = f"https://wttr.in/{location}?format=j1"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            current = data['current_condition'][0]
            temp_c = current['temp_C']
            temp_f = current['temp_F']
            weather_desc = current['weatherDesc'][0]['value']
            humidity = current['humidity']
            wind_speed = current['windspeedKmph']
            location_name = data['nearest_area'][0]['areaName'][0]['value']
            return f"Weather in {location_name}: {weather_desc}, {temp_c}°C ({temp_f}°F), Humidity: {humidity}%, Wind: {wind_speed} km/h"
        return f"Could not get weather for '{location}'"
    except Exception as e:
        return f"Weather error: {str(e)}"


# ===== SEARCH LIMITS, CACHE, AND WEB SEARCH (patched) =====
try:
    SEARCH_MAX_PER_MINUTE
except NameError:
    import threading, time, os
    from collections import deque
    SEARCH_MAX_PER_MINUTE = int(os.getenv("SEARCH_MAX_PER_MINUTE", "8"))
    SEARCH_CACHE_TTL_SEC = int(os.getenv("SEARCH_CACHE_TTL_SEC", "21600"))
    SEARCH_RESULTS_PER_QUERY = int(os.getenv("SEARCH_RESULTS_PER_QUERY", "5"))
    _SEARCH_TIMESTAMPS = deque(maxlen=64)
    _SEARCH_CACHE = {}
    _SEARCH_LOCK = threading.Lock()

def _search_budget_ok():
    now = time.time()
    while _SEARCH_TIMESTAMPS and (now - _SEARCH_TIMESTAMPS[0]) > 60:
        _SEARCH_TIMESTAMPS.popleft()
    return len(_SEARCH_TIMESTAMPS) < SEARCH_MAX_PER_MINUTE

def _record_search():
    _SEARCH_TIMESTAMPS.append(time.time())

def _get_cached(query):
    q = query.strip().lower()
    item = _SEARCH_CACHE.get(q)
    if not item:
        return None
    exp, value = item
    if time.time() < exp:
        return value
    _SEARCH_CACHE.pop(q, None)
    return None

def _set_cached(query, value):
    _SEARCH_CACHE[query.strip().lower()] = (time.time() + SEARCH_CACHE_TTL_SEC, value)

def execute_web_search(query: str) -> str:
    """Execute a web search with caching + rate limiting and graceful provider backoff. Returns JSON."""
    import time
    from urllib.parse import quote_plus

    if not query or not query.strip():
        return json.dumps({
            "success": False,
            "error": "Please provide a search query."
        })

    q = query.strip()

    with _SEARCH_LOCK:
        cached = _get_cached(q)
        if cached is not None:
            return cached
        if not _search_budget_ok():
            if cached is not None:
                return cached
            return json.dumps({
                "success": False,
                "error": "[RATE LIMIT] You've run out of web searches for the moment. Please wait ~60 seconds and try again. Tip: identical queries are cached for 6 hours."
            })
        _record_search()

    results = []
    used_provider = None

    # Preferred library path
    try:
        from ddgs import DDGS  # UPDATED: Changed from duckduckgo_search to ddgs
        used_provider = "ddgs.DDGS"
        with DDGS() as ddgs:
            for i, r in enumerate(ddgs.text(q, region="ca-en", max_results=SEARCH_RESULTS_PER_QUERY)):
                title = (r.get("title") or "").strip() or "Untitled"
                href = (r.get("href") or r.get("link") or "").strip()
                snippet = (r.get("body") or r.get("description") or "").strip()
                if href:
                    results.append({
                        "position": i + 1,
                        "title": title,
                        "url": href,
                        "snippet": snippet
                    })
        if not results:
            used_provider = None
    except Exception:
        used_provider = None

    # Fallback HTML endpoint (no JS)
    if not results:
        try:
            import requests
            from bs4 import BeautifulSoup  # type: ignore
            used_provider = "duckduckgo html"
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(q)}"
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (compatible; BlueBot/1.0)"})
            if resp.status_code == 429:
                cached = _get_cached(q)
                if cached is not None:
                    return cached
                return json.dumps({
                    "success": False,
                    "error": "[PROVIDER LIMIT] The search provider is rate-limiting right now. Please retry in a minute."
                })
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select(".result__body")
            for i, item in enumerate(items[:SEARCH_RESULTS_PER_QUERY]):
                a = item.select_one("a.result__a")
                if not a:
                    continue
                title = a.get_text(strip=True) or "Untitled"
                href = a.get("href", "")
                snippet_el = item.select_one(".result__snippet")
                snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""
                if href:
                    results.append({
                        "position": i + 1,
                        "title": title,
                        "url": href,
                        "snippet": snippet
                    })
        except Exception as e:
            msg = json.dumps({
                "success": False,
                "error": f"Web search failed: {e.__class__.__name__}: {e}"
            })
            _set_cached(q, msg)
            return msg

    if not results:
        msg = json.dumps({
            "success": False,
            "query": q,
            "error": "No results found."
        })
        _set_cached(q, msg)
        return msg

    # Return proper JSON with success field
    payload = json.dumps({
        "success": True,
        "query": q,
        "provider": used_provider or "unknown",
        "results": results,
        "result_count": len(results)
    }, ensure_ascii=False)

    _set_cached(q, payload)
    return payload
# ===== END patched web search =====


# ===== BROWSE WEBSITE TOOL (moved here so it's available to execute_tool) =====
import re as _re
import html as _html
import json as _json
from typing import Optional

# HTML cleaning patterns
_SCRIPT_STYLE = _re.compile(r"(?is)<(script|style)\b.*?>.*?</\1>")
_TAGS = _re.compile(r"(?s)<[^>]+>")
_MULTI_WS = _re.compile(r"[ \t\r\f\v]+")
_MULTI_NL = _re.compile(r"\n{3,}")
_TITLE_RE = _re.compile(r"(?is)<title[^>]*>(.*?)</title>")
_LINK_RE = _re.compile(r'(?i)href=["\'](.*?)["\']')

def _clean_html_to_text(html_str: str, max_chars: int = 8000) -> str:
    """Clean HTML and convert to readable text."""
    if not isinstance(html_str, str):
        html_str = str(html_str or "")
    # remove script/style
    s = _SCRIPT_STYLE.sub(" ", html_str)
    # extract title separately if needed
    title = None
    mt = _TITLE_RE.search(s)
    if mt:
        title = _html.unescape(mt.group(1).strip())
    # remove tags
    s = _TAGS.sub("\n", s)
    s = _html.unescape(s)
    # collapse whitespace
    s = _MULTI_WS.sub(" ", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = _MULTI_NL.sub("\n\n", s)
    s = s.strip()
    if max_chars and len(s) > max_chars:
        s = s[:max_chars].rstrip() + "…"
    if title and title not in s[:500]:
        s = f"{title}\n\n{s}"
    return s

def _extract_links(html_str: str, base_url: str, max_links: int = 40) -> list:
    """Extract links from HTML."""
    import urllib.parse as _urlparse2
    out = []
    seen = set()
    for m in _LINK_RE.finditer(html_str or ""):
        href = m.group(1).strip()
        if not href:
            continue
        href_abs = _urlparse2.urljoin(base_url, href)
        if not href_abs.startswith(("http://","https://")):
            continue
        if href_abs in seen:
            continue
        seen.add(href_abs)
        out.append(href_abs)
        if len(out) >= max_links:
            break
    return out

def _safe_fetch_url(url: str, headers: Optional[dict] = None, timeout: int = 15, max_bytes: int = 1_500_000):
    """Safely fetch a URL with size limits."""
    import requests as _requests
    import urllib.parse as _urlparse3
    if not isinstance(url, str):
        raise ValueError("url must be a string")
    u = url.strip()
    if not u.startswith(("http://","https://")):
        raise ValueError("Only http/https URLs are allowed")
    parts = _urlparse3.urlsplit(u)
    if not parts.netloc:
        raise ValueError("URL must be absolute")
    req_headers = {
        "User-Agent": "BlueBot/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    if isinstance(headers, dict):
        req_headers.update({str(k): str(v) for k,v in headers.items()})
    resp = _requests.get(u, headers=req_headers, timeout=timeout, stream=True, allow_redirects=True)
    resp.raise_for_status()
    content = b""
    for chunk in resp.iter_content(chunk_size=16384):
        if chunk:
            content += chunk
            if len(content) > max_bytes:
                break
    return resp.headers.get("content-type",""), content

def _execute_browse_website(args: dict) -> str:
    """Execute the browse_website tool."""
    import requests

    url = (args or {}).get("url", "")
    extract = (args or {}).get("extract", "text") or "text"
    max_chars = int((args or {}).get("max_chars", 8000) or 8000)
    include_links = bool((args or {}).get("include_links", True))
    headers = (args or {}).get("headers", None)

    try:
        print(f"   [BROWSE] Fetching URL: {url}")
        ctype, content = _safe_fetch_url(url, headers=headers)
        html_raw = content.decode("utf-8", errors="ignore")

        if extract == "html":
            body = html_raw[: max_chars] + ("…" if len(html_raw) > max_chars else "")
        else:
            body = _clean_html_to_text(html_raw, max_chars=max_chars)

        result = {
            "url": url,
            "content_type": ctype,
            "extract": extract,
            "text": body,
            "success": True
        }
        if include_links:
            result["links"] = _extract_links(html_raw, url, max_links=40)

        print(f"   [BROWSE] Successfully fetched {len(body)} characters from {url}")
        return _json.dumps(result, ensure_ascii=False)

    except requests.exceptions.Timeout:
        error_msg = f"Timeout: The website {url} took too long to respond (>15 seconds)."
        print(f"   [ERROR] {error_msg}")
        return _json.dumps({"error": error_msg, "url": url, "success": False})

    except requests.exceptions.ConnectionError:
        error_msg = f"Connection Error: Could not connect to {url}. The website may be down or unreachable."
        print(f"   [ERROR] {error_msg}")
        return _json.dumps({"error": error_msg, "url": url, "success": False})

    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP Error {e.response.status_code}: {url} returned an error. The page may not exist or access may be denied."
        print(f"   [ERROR] {error_msg}")
        return _json.dumps({"error": error_msg, "url": url, "success": False})

    except ValueError as e:
        error_msg = f"Invalid URL: {str(e)}"
        print(f"   [ERROR] {error_msg}")
        return _json.dumps({"error": error_msg, "url": url, "success": False})

    except Exception as e:
        error_msg = f"Unexpected error while browsing {url}: {str(e)}"
        print(f"   [ERROR] {error_msg}")
        return _json.dumps({"error": error_msg, "url": url, "success": False})
# ===== END BROWSE WEBSITE TOOL =====


# ===== GMAIL TOOLS =====


def _execute_read_gmail(args: Dict[str, Any]) -> str:
    """Read and search Gmail messages"""
    if not GMAIL_AVAILABLE:
        return json.dumps({
            "error": "Gmail libraries not installed. Install with: pip install google-auth google-auth-oauthlib google-api-python-client",
            "success": False
        })

    try:
        service = get_gmail_service()
        query = args.get("query", "")
        max_results = args.get("max_results", 10)
        include_body = args.get("include_body", True)

        # Search for messages
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            return json.dumps({
                "emails": [],
                "count": 0,
                "message": "No emails found matching the criteria",
                "success": True,
                "note": "EMAIL ACCESS SUCCESSFUL! The inbox was checked but no emails matched your search. This is REAL data."
            })

        email_list = []
        for msg in messages:
            msg_data = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()

            # Extract headers
            headers = msg_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
            to = next((h['value'] for h in headers if h['name'].lower() == 'to'), '')

            email_info = {
                "id": msg['id'],
                "subject": subject,
                "from": sender,
                "to": to,
                "date": date,
                "snippet": msg_data.get('snippet', '')
            }

            # Extract body if requested
            if include_body:
                body = ""
                if 'parts' in msg_data['payload']:
                    for part in msg_data['payload']['parts']:
                        if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                            body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                            break
                elif 'body' in msg_data['payload'] and 'data' in msg_data['payload']['body']:
                    body = base64.urlsafe_b64decode(msg_data['payload']['body']['data']).decode('utf-8')

                email_info['body'] = body

            email_list.append(email_info)

        return json.dumps({
            "emails": email_list,
            "count": len(email_list),
            "query": query if query else "recent emails",
            "success": True,
            "note": "EMAIL ACCESS SUCCESSFUL! The emails above are REAL data from the Gmail inbox. Present this information to the user."
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"Failed to read Gmail: {str(e)}",
            "success": False
        })


def _execute_send_gmail(args: Dict[str, Any]) -> str:
    """Send an email via Gmail with optional attachments"""
    if not GMAIL_AVAILABLE:
        return json.dumps({
            "error": "Gmail libraries not installed. Install with: pip install google-auth google-auth-oauthlib google-api-python-client",
            "success": False
        })

    try:
        service = get_gmail_service()

        to = args.get("to", "")
        subject = args.get("subject", "")
        body = args.get("body", "")
        cc = args.get("cc", "")
        bcc = args.get("bcc", "")
        attachments = args.get("attachments", [])  # NEW: List of file paths

        if not to or not subject:
            return json.dumps({
                "error": "Missing required email information. Need: recipient email address (name@domain.com) and subject. Please ask user to provide both.",
                "missing_to": not to,
                "missing_subject": not subject,
                "success": False,
                "instruction": "Tell the user you need their email address or subject line. Example: 'I need the recipient's email address to send this message.'"
            })

        # Create message
        message = MIMEMultipart()
        message['To'] = to
        message['Subject'] = subject

        if cc:
            message['Cc'] = cc
        if bcc:
            message['Bcc'] = bcc

        # Add body
        message.attach(MIMEText(body, 'plain'))

        # Process attachments
        attached_files = []
        attachment_errors = []

        if attachments:
            print(f"   [ATTACH] Processing {len(attachments)} attachment(s)")

            for file_path in attachments:
                try:
                    # Normalize path
                    file_path = file_path.strip()

                    # Check if file exists
                    if not os.path.exists(file_path):
                        # Try in documents folder
                        doc_path = os.path.join(str(UPLOAD_FOLDER), file_path)
                        if os.path.exists(doc_path):
                            file_path = doc_path
                        else:
                            # Also try DOCUMENTS_FOLDER
                            doc_path2 = os.path.join(DOCUMENTS_FOLDER, file_path)
                            if os.path.exists(doc_path2):
                                file_path = doc_path2
                            else:
                                attachment_errors.append(f"File not found: {file_path}")
                                print(f"   [ATTACH-ERROR] File not found: {file_path}")
                                continue

                    # Check file size (limit to 25MB - Gmail limit)
                    file_size = os.path.getsize(file_path)
                    max_size = 25 * 1024 * 1024  # 25MB in bytes

                    if file_size > max_size:
                        attachment_errors.append(f"File too large: {os.path.basename(file_path)} ({file_size / (1024*1024):.1f}MB > 25MB)")
                        print(f"   [ATTACH-ERROR] File too large: {file_path}")
                        continue

                    # Get filename
                    filename = os.path.basename(file_path)

                    # Guess MIME type
                    mime_type, _ = mimetypes.guess_type(file_path)
                    if mime_type is None:
                        mime_type = 'application/octet-stream'

                    # Split MIME type
                    main_type, sub_type = mime_type.split('/', 1)

                    # Read file and attach
                    with open(file_path, 'rb') as f:
                        file_data = f.read()

                    # Create attachment
                    attachment = MIMEBase(main_type, sub_type)
                    attachment.set_payload(file_data)
                    encoders.encode_base64(attachment)
                    attachment.add_header('Content-Disposition', f'attachment; filename={filename}')

                    # Attach to message
                    message.attach(attachment)

                    attached_files.append({
                        'filename': filename,
                        'size': file_size,
                        'type': mime_type
                    })
                    print(f"   [ATTACH-OK] Attached: {filename} ({file_size / 1024:.1f}KB)")

                except Exception as e:
                    error_msg = f"Error attaching {os.path.basename(file_path) if file_path else 'file'}: {str(e)}"
                    attachment_errors.append(error_msg)
                    print(f"   [ATTACH-ERROR] {error_msg}")

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        # Send message
        sent_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()

        # Build result
        result = {
            "message_id": sent_message['id'],
            "to": to,
            "subject": subject,
            "success": True,
            "message": f"✅ Email sent successfully to {to}",
            "confirmation": f"Email delivered to {to} with subject '{subject}'",
            "note": "EMAIL SENT SUCCESSFULLY! You MUST confirm this to the user by saying 'I sent the email to [address]' or similar."
        }

        # Add attachment info
        if attached_files:
            result['attachments'] = attached_files
            result['attachments_count'] = len(attached_files)
            result['message'] += f" with {len(attached_files)} attachment(s)"
            result['note'] += f" ATTACHMENTS: {', '.join([f['filename'] for f in attached_files])}"

        if attachment_errors:
            result['attachment_errors'] = attachment_errors
            result['warning'] = f"Email sent but {len(attachment_errors)} attachment(s) failed"

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"Failed to send email: {str(e)}",
            "success": False
        })


def _execute_reply_gmail(args: Dict[str, Any]) -> str:
    """Reply to Gmail messages"""
    if not GMAIL_AVAILABLE:
        return json.dumps({
            "error": "Gmail libraries not installed. Install with: pip install google-auth google-auth-oauthlib google-api-python-client",
            "success": False
        })

    try:
        service = get_gmail_service()

        query = args.get("query", "")
        reply_body = args.get("reply_body", "")
        reply_all = args.get("reply_all", False)
        max_replies = min(args.get("max_replies", 10), 50)  # Cap at 50

        if not query or not reply_body:
            return json.dumps({
                "error": "Missing required fields: 'query' and 'reply_body' are required",
                "success": False
            })

        # Search for messages to reply to
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_replies if reply_all else 1
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            return json.dumps({
                "success": True,
                "replies_sent": 0,
                "message": f"No emails found matching query: {query}",
                "query": query
            })

        replies_sent = []
        errors = []

        # Reply to each message
        for msg in messages:
            try:
                # Get the original message details
                msg_data = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()

                # Extract headers
                headers = msg_data['payload']['headers']
                original_subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                original_from = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
                original_to = next((h['value'] for h in headers if h['name'].lower() == 'to'), '')
                message_id_header = next((h['value'] for h in headers if h['name'].lower() == 'message-id'), '')

                # Extract email body content
                email_body = ""
                if 'parts' in msg_data['payload']:
                    for part in msg_data['payload']['parts']:
                        if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                            email_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                            break
                elif 'body' in msg_data['payload'] and 'data' in msg_data['payload']['body']:
                    email_body = base64.urlsafe_b64decode(msg_data['payload']['body']['data']).decode('utf-8')

                # Extract email address from "Name <email@domain.com>" format
                import re
                email_match = re.search(r'<(.+?)>', original_from)
                reply_to = email_match.group(1) if email_match else original_from

                # Create reply subject (add Re: if not already there)
                reply_subject = original_subject if original_subject.startswith('Re:') else f"Re: {original_subject}"

                # Create reply message
                reply_message = MIMEMultipart()
                reply_message['To'] = reply_to
                reply_message['Subject'] = reply_subject
                reply_message['In-Reply-To'] = message_id_header
                reply_message['References'] = message_id_header

                # Add reply body
                reply_message.attach(MIMEText(reply_body, 'plain'))

                # Encode and send
                raw_message = base64.urlsafe_b64encode(reply_message.as_bytes()).decode('utf-8')

                sent_message = service.users().messages().send(
                    userId='me',
                    body={
                        'raw': raw_message,
                        'threadId': msg_data.get('threadId')  # Keep in same thread
                    }
                ).execute()

                replies_sent.append({
                    "original_subject": original_subject,
                    "original_body": email_body[:500] + "..." if len(email_body) > 500 else email_body,  # Include truncated body
                    "replied_to": reply_to,
                    "reply_id": sent_message['id'],
                    "reply_sent": reply_body
                })

                print(f"   [OK] Replied to: {original_subject} (from {reply_to})")

            except Exception as e:
                errors.append({
                    "message_id": msg['id'],
                    "error": str(e)
                })
                print(f"   [ERROR] Failed to reply to message {msg['id']}: {e}")

        return json.dumps({
            "success": True,
            "replies_sent": len(replies_sent),
            "query": query,
            "replies": replies_sent,
            "errors": errors if errors else None,
            "message": f"Successfully replied to {len(replies_sent)} email(s) matching '{query}'",
            "note": "REPLIES SENT SUCCESSFULLY! The replies have been delivered and threaded correctly."
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"Failed to reply to emails: {str(e)}",
            "success": False
        })
# ===== END GMAIL TOOLS =====


def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> str:
    """
    Execute requested tool with enhanced error handling and state tracking.
    v8 ENHANCED: Better state tracking, timing, retry on transient failures.
    """
    import time
    start_time = time.time()
    state = get_conversation_state()
    
    print(f"[TOOL] Executing tool: {tool_name}")
    print(f"   Arguments: {json.dumps(tool_args, indent=2)}")
    
    # v8: Track execution attempt
    max_retries = 2 if tool_name in ['web_search', 'read_gmail', 'browse_website'] else 1
    last_error = None
    
    for attempt in range(max_retries):
        try:
            result = _execute_tool_internal(tool_name, tool_args)
            elapsed = time.time() - start_time
            
            # Record successful execution with args
            state.record_tool_use(
                tool_name, 
                success=True, 
                pattern=f"{tool_name}:{list(tool_args.keys())}",
                args=tool_args
            )
            state.last_tool_result = truncate_text(result, 500)
            
            # v8: Update topic based on tool
            if tool_name == 'play_music':
                state.push_topic('music')
            elif tool_name in ['control_lights', 'music_visualizer']:
                state.push_topic('lights')
            elif tool_name in ['read_gmail', 'send_gmail', 'reply_gmail']:
                state.push_topic('email')
            
            print(f"   [OK] {tool_name} completed in {elapsed:.2f}s")
            return result
            
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 1 * (attempt + 1)
                print(f"   [RETRY] {tool_name} failed, retrying in {wait_time}s...")
                time.sleep(wait_time)
            continue
    
    # All retries failed
    elapsed = time.time() - start_time
    error_msg = str(last_error)
    
    # Record failed execution
    state.record_tool_use(tool_name, success=False, pattern=f"{tool_name}:error", args=tool_args)
    
    print(f"   [ERROR] {tool_name} failed after {elapsed:.2f}s: {error_msg}")
    
    # Provide helpful error message
    error_response = {
        "success": False,
        "error": error_msg,
        "tool": tool_name,
        "suggestion": _get_error_suggestion(tool_name, error_msg)
    }
    
    return json.dumps(error_response)


def _get_error_suggestion(tool_name: str, error: str) -> str:
    """Get a helpful suggestion for common errors."""
    error_lower = error.lower()
    
    if "timeout" in error_lower or "timed out" in error_lower:
        return "The service took too long to respond. Try again in a moment."
    elif "connection" in error_lower or "network" in error_lower:
        return "Network connection issue. Check your internet connection."
    elif "not found" in error_lower:
        return "The requested resource wasn't found. Check the name or path."
    elif "permission" in error_lower or "unauthorized" in error_lower:
        return "Permission denied. You may need to re-authenticate."
    elif "rate limit" in error_lower:
        return "Too many requests. Please wait a moment before trying again."
    elif tool_name == "play_music":
        return "Try a different artist name or check if YouTube Music is running."
    elif tool_name == "control_lights":
        return "Check if the Philips Hue bridge is connected and accessible."
    elif tool_name in ["read_gmail", "send_gmail", "reply_gmail"]:
        return "Gmail authentication may have expired. Check credentials."
    else:
        return "Try rephrasing your request or provide more details."


def _execute_tool_internal(tool_name: str, tool_args: Dict[str, Any]) -> str:
    """Internal tool execution - called by execute_tool wrapper."""
    
    if tool_name == "play_music":
        query = tool_args.get("query", "")
        action = tool_args.get("action", "play")
        service = tool_args.get("service", "youtube_music")

        if action == "search":
            result = search_music_info(query)
        else:
            result = play_music(query, service)
        print(f"   [OK] Music action completed")
        return result

    elif tool_name == "control_music":
        action = tool_args.get("action", "")
        result = control_music(action)
        print(f"   [OK] Music control executed")
        return result

    elif tool_name == "music_visualizer":
        action = tool_args.get("action", "start")

        if action == "start":
            duration = tool_args.get("duration", 300)
            style = tool_args.get("style", "party")
            result = start_music_visualizer(duration, style)
        elif action == "stop":
            result = stop_music_visualizer()
        else:
            result = f"Unknown visualizer action: {action}"

        print(f"   [OK] Visualizer action completed")
        return result

    elif tool_name == "control_lights":
        result = execute_light_control(
            tool_args.get("action"),
            tool_args.get("light_name"),
            tool_args.get("brightness"),
            tool_args.get("color"),
            tool_args.get("mood")
        )
        print(f"   [OK] Light control executed")
        return result

    elif tool_name == "search_documents":
        global _vision_queue
        query = tool_args.get("query", "")
        max_results = tool_args.get("max_results", 3)
        result = search_documents_rag(query, max_results)
        print(f"   [OK] Document search completed")

        # Check if result contains images (special JSON format)
        try:
            result_data = json.loads(result)
            if isinstance(result_data, dict) and result_data.get("_type") == "document_search_with_images":
                images = result_data.get("images", [])
                text_docs = result_data.get("text_documents", [])

                # Store images globally so they can be injected into next LLM call
                for img in images:
                    _vision_queue.add_image(
                        filepath=img['filepath'],
                        filename=img['filename'],
                        is_camera=False
                    )
                print(f"   [VISION] Stored {len(images)} image(s) for vision model")

                # Build text response
                response_parts = []
                if images:
                    image_names = [img['filename'] for img in images]
                    response_parts.append(f"Found {len(images)} image(s): {', '.join(image_names)}")
                    response_parts.append("(Images will be shown to vision model in next response)")

                if text_docs:
                    response_parts.append("\n\nText documents found:\n\n" + "\n---\n\n".join(text_docs))

                return "\n".join(response_parts) if response_parts else "Found documents."
        except (json.JSONDecodeError, TypeError):
            # Not JSON or not our special format - return as-is
            pass

        return result

    elif tool_name == "view_image":
        filename = tool_args.get("filename")
        query = tool_args.get("query")
        result = view_image(filename=filename, query=query)
        print(f"   [OK] Image view requested")
        return result

    elif tool_name == "capture_camera":
        result = capture_camera_image()
        print(f"   [OK] Camera capture completed")
        return result

    elif tool_name == "get_weather":
        result = get_weather_data(tool_args.get("location", ""))
        print(f"   [OK] Weather retrieved")
        return result

    elif tool_name == "web_search":
        result = execute_web_search(tool_args.get("query", ""))
        print(f"   [OK] Search completed")
        return result

    elif tool_name == "run_javascript":
        try:
            import js2py
            result = js2py.eval_js(tool_args.get("code", ""))
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {str(e)}"

    elif tool_name == "create_document":
        filename = tool_args.get("filename", "")
        content = tool_args.get("content", "")
        file_type = tool_args.get("file_type", "txt")
        result = create_document_file(filename, content, file_type)
        print(f"   [OK] Document created")
        return result

    elif tool_name == "browse_website":
        print(f"   [DEBUG] Calling _execute_browse_website...")
        result = _execute_browse_website(tool_args)
        print(f"   [DEBUG] Got result, length: {len(result)} chars")
        # Parse the result to check success
        try:
            result_obj = json.loads(result)
            if result_obj.get("success"):
                print(f"   [OK] Browse completed - fetched {len(result_obj.get('text', ''))} chars")
            else:
                print(f"   [ERROR] Browse failed: {result_obj.get('error', 'Unknown error')}")
        except Exception:
            pass
        return result

    elif tool_name == "read_gmail":
        result = _execute_read_gmail(tool_args)
        # Add operation type to help Blue understand what just happened
        try:
            result_obj = json.loads(result)
            result_obj["_operation_type"] = "READ_EMAIL"
            result_obj["_instruction"] = "You just READ emails. User asked to check/read, NOT to reply or send."
            result = json.dumps(result_obj)
        except Exception:
            pass
        print(f"   [OK] Gmail READ completed")
        return result

    elif tool_name == "send_gmail":
        result = _execute_send_gmail(tool_args)
        # Add operation type to help Blue understand what just happened
        try:
            result_obj = json.loads(result)
            result_obj["_operation_type"] = "SEND_EMAIL"
            result_obj["_instruction"] = "You just SENT a new email. User asked to send, NOT to read or reply."
            result = json.dumps(result_obj)
        except Exception:
            pass
        print(f"   [OK] Gmail SEND completed")
        return result

    elif tool_name == "reply_gmail":
        result = _execute_reply_gmail(tool_args)
        # Add operation type to help Blue understand what just happened
        try:
            result_obj = json.loads(result)
            result_obj["_operation_type"] = "REPLY_EMAIL"
            result_obj["_instruction"] = "You just REPLIED to emails. User asked to reply/respond, NOT to just read."
            result = json.dumps(result_obj)
        except Exception:
            pass
        print(f"   [OK] Gmail REPLY completed")
        return result


    # ===== Enhanced Tools Handlers =====
    elif tool_name == "create_reminder" and ENHANCED_TOOLS_AVAILABLE:
        result = CalendarManager.create_reminder(**tool_args)
        print(f"   [OK] Reminder created")
        return json.dumps(result)

    elif tool_name == "get_upcoming_reminders" and ENHANCED_TOOLS_AVAILABLE:
        result = CalendarManager.get_upcoming_reminders(**tool_args)
        print(f"   [OK] Retrieved reminders")
        return json.dumps(result)

    elif tool_name == "complete_reminder" and ENHANCED_TOOLS_AVAILABLE:
        result = CalendarManager.complete_reminder(**tool_args)
        print(f"   [OK] Reminder completed")
        return json.dumps(result)

    elif tool_name == "create_task" and ENHANCED_TOOLS_AVAILABLE:
        result = TaskManager.create_task(**tool_args)
        print(f"   [OK] Task created")
        return json.dumps(result)

    elif tool_name == "get_tasks" and ENHANCED_TOOLS_AVAILABLE:
        result = TaskManager.get_tasks(**tool_args)
        print(f"   [OK] Retrieved tasks")
        return json.dumps(result)

    elif tool_name == "complete_task" and ENHANCED_TOOLS_AVAILABLE:
        result = TaskManager.complete_task(**tool_args)
        print(f"   [OK] Task completed")
        return json.dumps(result)

    elif tool_name == "create_note" and ENHANCED_TOOLS_AVAILABLE:
        result = NoteManager.create_note(**tool_args)
        print(f"   [OK] Note saved")
        return json.dumps(result)

    elif tool_name == "search_notes" and ENHANCED_TOOLS_AVAILABLE:
        result = NoteManager.search_notes(**tool_args)
        print(f"   [OK] Note search completed")
        return json.dumps(result)

    elif tool_name == "set_timer" and ENHANCED_TOOLS_AVAILABLE:
        result = TimerManager.set_timer(**tool_args)
        print(f"   [OK] Timer set")
        return json.dumps(result)

    elif tool_name == "check_timers" and ENHANCED_TOOLS_AVAILABLE:
        result = TimerManager.check_timers()
        print(f"   [OK] Timer status checked")
        return json.dumps(result)

    elif tool_name == "get_system_info" and ENHANCED_TOOLS_AVAILABLE:
        result = SystemController.get_system_info()
        print(f"   [OK] System info retrieved")
        return json.dumps(result)

    elif tool_name == "take_screenshot" and ENHANCED_TOOLS_AVAILABLE:
        result = SystemController.take_screenshot(**tool_args)
        print(f"   [OK] Screenshot captured")
        return json.dumps(result)

    elif tool_name == "launch_application" and ENHANCED_TOOLS_AVAILABLE:
        result = SystemController.launch_application(**tool_args)
        print(f"   [OK] Application launched")
        return json.dumps(result)

    elif tool_name == "set_volume" and ENHANCED_TOOLS_AVAILABLE:
        result = SystemController.set_volume(**tool_args)
        print(f"   [OK] Volume set")
        return json.dumps(result)

    elif tool_name == "list_files" and ENHANCED_TOOLS_AVAILABLE:
        result = FileOperations.list_files(**tool_args)
        print(f"   [OK] Files listed")
        return json.dumps(result)

    elif tool_name == "read_file" and ENHANCED_TOOLS_AVAILABLE:
        result = FileOperations.read_file(**tool_args)
        print(f"   [OK] File read")
        return json.dumps(result)

    elif tool_name == "write_file" and ENHANCED_TOOLS_AVAILABLE:
        result = FileOperations.write_file(**tool_args)
        print(f"   [OK] File written")
        return json.dumps(result)

    elif tool_name == "get_file_info" and ENHANCED_TOOLS_AVAILABLE:
        result = FileOperations.get_file_info(**tool_args)
        print(f"   [OK] File info retrieved")
        return json.dumps(result)

    elif tool_name == "story_prompt" and ENHANCED_TOOLS_AVAILABLE:
        result = StorytellingTools.story_prompt(**tool_args)
        print(f"   [OK] Story prompt generated")
        return json.dumps(result)

    elif tool_name == "educational_activity" and ENHANCED_TOOLS_AVAILABLE:
        result = StorytellingTools.educational_activity(**tool_args)
        print(f"   [OK] Activity suggested")
        return json.dumps(result)

    elif tool_name == "get_local_time" and ENHANCED_TOOLS_AVAILABLE:
        result = LocationServices.get_local_time()
        print(f"   [OK] Local time retrieved")
        return json.dumps(result)

    elif tool_name == "get_sunrise_sunset" and ENHANCED_TOOLS_AVAILABLE:
        result = LocationServices.get_sunrise_sunset()
        print(f"   [OK] Sunrise/sunset times retrieved")
        return json.dumps(result)

    elif tool_name == "remember_person" and VISUAL_MEMORY_AVAILABLE:
        name = tool_args.get("name", "")
        appearance = tool_args.get("appearance", "")
        relationship = tool_args.get("relationship", "")
        notes = tool_args.get("notes", "")

        try:
            vm = get_visual_memory()
            vm.add_person(
                name=name,
                typical_appearance=appearance,
                relationship=relationship,
                notes=notes
            )
            print(f"   [OK] Remembered person: {name}")
            return json.dumps({
                "success": True,
                "message": f"I'll remember {name}. Next time I see them through my camera, I'll recognize them."
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Failed to remember person: {str(e)}"
            })

    elif tool_name == "remember_place" and VISUAL_MEMORY_AVAILABLE:
        name = tool_args.get("name", "")
        description = tool_args.get("description", "")
        typical_contents = tool_args.get("typical_contents", "")
        notes = tool_args.get("notes", "")

        try:
            vm = get_visual_memory()
            vm.add_place(
                name=name,
                description=description,
                typical_contents=typical_contents,
                notes=notes
            )
            print(f"   [OK] Remembered place: {name}")
            return json.dumps({
                "success": True,
                "message": f"I'll remember {name}. Next time I see this location, I'll recognize it."
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Failed to remember place: {str(e)}"
            })

    elif tool_name == "who_do_i_know" and VISUAL_MEMORY_AVAILABLE:
        try:
            vm = get_visual_memory()
            people = vm.get_all_people()
            places = vm.get_all_places()

            result = {"people": [], "places": []}

            for person in people:
                result["people"].append({
                    "name": person['name'],
                    "relationship": person['relationship'],
                    "appearance": person['typical_appearance'],
                    "times_seen": person['times_seen']
                })

            for place in places:
                result["places"].append({
                    "name": place['name'],
                    "description": place['description'],
                    "times_seen": place['times_seen']
                })

            print(f"   [OK] Retrieved visual memory: {len(people)} people, {len(places)} places")
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Failed to retrieve visual memory: {str(e)}"
            })

    elif tool_name == "analyze_with_chat_theory" and ACADEMIC_ASSISTANT_AVAILABLE:
        topic = tool_args.get("topic", "")
        context = tool_args.get("context", "")

        result = analyze_with_chat(topic, context)
        print(f"   [OK] Generated CHAT analysis for: {topic}")
        return result

    elif tool_name == "prepare_lecture" and ACADEMIC_ASSISTANT_AVAILABLE:
        topic = tool_args.get("topic", "")
        duration = tool_args.get("duration", 50)
        course = tool_args.get("course", "")
        level = tool_args.get("level", "undergraduate")

        result = prepare_lecture(topic, duration, course, level)
        print(f"   [OK] Generated lecture outline for: {topic}")
        return result

    elif tool_name == "discussion_questions" and ACADEMIC_ASSISTANT_AVAILABLE:
        reading = tool_args.get("reading", "")
        topic = tool_args.get("topic", "")

        result = generate_discussion_questions(reading, topic)
        print(f"   [OK] Generated discussion questions for: {topic}")
        return result

    elif tool_name == "simulate_student_questions" and ACADEMIC_ASSISTANT_AVAILABLE:
        topic = tool_args.get("topic", "")
        context = tool_args.get("context", "")

        result = simulate_student_q_and_a(topic, context)
        print(f"   [OK] Simulated student questions for: {topic}")
        return result

    elif tool_name == "check_proactive_suggestions" and PROACTIVE_ASSISTANCE_AVAILABLE:
        try:
            pa = get_proactive_assistance()
            # Get current person from context (default to Alex)
            person = "Alex"  # Could be enhanced to detect from visual memory

            suggestions = pa.check_for_suggestions(person)

            if suggestions:
                result = {
                    "has_suggestions": True,
                    "suggestions": [
                        {
                            "type": suggestion.suggestion_type,
                            "priority": suggestion.priority,
                            "message": suggestion.message,
                            "action_available": suggestion.action_available
                        }
                        for suggestion in suggestions
                    ]
                }
                print(f"   [OK] Found {len(suggestions)} proactive suggestions")
            else:
                result = {
                    "has_suggestions": False,
                    "message": "No suggestions at this time"
                }
                print(f"   [OK] No proactive suggestions at this time")

            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Failed to check suggestions: {str(e)}"
            })

    return f"Unknown tool: {tool_name}"


# IMPROVED Intent Detection Functions


def detect_no_tool_intent(message: str) -> bool:
    """Detect if this is a greeting or casual chat that needs no tools."""
    msg_lower = message.lower().strip()
    # Check if it's very short and matches no-tool patterns
    if len(msg_lower) < 50:  # Short messages are often greetings
        return any(kw in msg_lower for kw in NO_TOOL_KEYWORDS)
    return False

def detect_search_intent(message: str) -> bool:
    """Detect if user wants a web search."""
    msg_lower = message.lower()

    # EXCLUDE: If explicitly asking for another tool, don't treat as search
    explicit_tool_mentions = [
        'use the', 'run javascript', 'execute javascript', 'run the javascript',
        'use javascript', 'call the', 'javascript tool', 'js tool',
        'run code', 'execute code'
    ]
    if any(mention in msg_lower for mention in explicit_tool_mentions):
        return False

    # Explicit search requests
    if any(kw in msg_lower for kw in ['search for', 'google', 'look up', 'find out about']):
        return True
    # Questions about current/recent things (but not if asking for code execution)
    if any(word in msg_lower for word in ['latest', 'recent', 'current', 'today', 'yesterday', 'this week']):
        return True
    # Questions about specific events/results
    if any(phrase in msg_lower for phrase in ['who won', 'what happened', 'news about']):
        return True
    return False

def detect_javascript_intent(message: str) -> bool:
    """Detect if user wants to run JavaScript code."""
    msg_lower = message.lower()
    javascript_keywords = [
        'run javascript', 'execute javascript', 'use javascript', 'javascript tool',
        'run js', 'execute js', 'js tool', 'run code', 'execute code',
        'use the javascript', 'use the js', 'run the javascript'
    ]
    return any(kw in msg_lower for kw in javascript_keywords)

def detect_weather_intent(message: str) -> bool:
    """Detect weather requests."""
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in WEATHER_KEYWORDS)

def detect_light_intent(message: str) -> bool:
    """
    Detect light control requests with improved false positive filtering.
    Must have BOTH a light noun AND an action OR color to trigger.
    """
    msg_lower = message.lower()

    # Exclude visualizer requests from regular light control
    if detect_visualizer_intent(message):
        return False

    # Filter out "light" used as adjective (NOT about lighting)
    light_adjective_phrases = [
        'light snack', 'light meal', 'light reading', 'light exercise',
        'light work', 'light duty', 'light touch', 'light breeze',
        'light rain', 'light traffic', 'light weight', 'light load',
        'light blue', 'light green', 'light pink', 'light grey', 'light gray',
        'bring to light', 'see the light', 'light of day', 'in light of'
    ]
    if any(phrase in msg_lower for phrase in light_adjective_phrases):
        return False

    # Light nouns - must have one of these
    light_nouns = ['light', 'lights', 'lamp', 'lamps', 'bulb', 'bulbs', 'hue', 'lighting']
    has_light_noun = any(noun in msg_lower for noun in light_nouns)

    # Actions that indicate light control
    light_actions = ['turn on', 'turn off', 'switch on', 'switch off', 'dim', 'brighten',
                     'set to', 'change to', 'make it', 'adjust', 'lights on', 'lights off']
    has_action = any(action in msg_lower for action in light_actions)

    # Colors that suggest light control (when combined with light noun)
    light_colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'white', 'pink',
                    'cyan', 'warm', 'cool', 'bright', 'dim']
    has_color = any(color in msg_lower for color in light_colors)

    # Must have light noun AND (action OR color)
    return has_light_noun and (has_action or has_color)

def detect_visualizer_intent(message: str) -> bool:
    """Detect light visualizer/show requests."""
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in VISUALIZER_KEYWORDS)


def detect_document_intent(message: str) -> bool:
    """Detect *explicit* requests to check user-uploaded documents."""
    msg_lower = message.lower()
    explicit_phrases = [
        "search my documents", "search my docs", "check my documents",
        "check my docs", "look in my documents", "look in my docs",
        "search my files", "check my files", "look in my files",
        "look in my uploads", "check my uploads", "search my uploads",
        "from my documents", "from my files", "in my documents", "in my files",
        "use the documents tool", "use documents tool", "use search_documents",
        "open my document", "open my file"
    ]
    if any(p in msg_lower for p in explicit_phrases):
        return True
    if ("according to my" in msg_lower or "in my file" in msg_lower or "in my document" in msg_lower):
        return True
    return False


def detect_create_document_intent(message: str) -> bool:
    """Detect requests to create/write/save a new document."""
    msg_lower = message.lower()

    # Check for explicit document creation keywords
    if any(kw in msg_lower for kw in CREATE_DOCUMENT_KEYWORDS):
        return True

    # Check for "create/write/make/save" followed by list/notes/file/doc
    creation_verbs = ['create', 'write', 'make', 'save', 'generate']
    doc_nouns = ['list', 'document', 'file', 'notes', 'note', 'recipe', 'doc']

    for verb in creation_verbs:
        for noun in doc_nouns:
            if f"{verb} a {noun}" in msg_lower or f"{verb} {noun}" in msg_lower:
                return True
            if f"{verb} me a {noun}" in msg_lower:
                return True

    return False


def detect_browse_intent(message: str) -> bool:
    """Detect requests to browse/open/visit a website or URL."""
    msg_lower = message.lower()

    # EXCLUDE document/file browsing - those should use search_documents
    document_phrases = [
        'browse documents', 'browse files', 'browse my documents', 'browse my files',
        'browse the documents', 'browse the files', 'browse document', 'browse file'
    ]
    if any(phrase in msg_lower for phrase in document_phrases):
        return False

    # Check for URLs in the message (http://, https://, www.)
    import re
    url_pattern = r'https?://\S+|www\.\S+'
    if re.search(url_pattern, msg_lower):
        return True

    # Check for explicit website browse keywords (but not just "browse")
    website_keywords = [
        'open url', 'open website', 'visit website', 'visit url',
        'go to', 'navigate to', 'read this page', 'open this',
        'visit this', 'load this page', 'show me this website', 'summarize this page'
    ]
    if any(kw in msg_lower for kw in website_keywords):
        return True

    # Check for "browse" + website/url/page
    if 'browse' in msg_lower:
        if any(word in msg_lower for word in ['website', 'site', 'url', 'page', 'web']):
            return True
        # Also check for domain patterns after "browse"
        if re.search(r'browse\s+\S+\.(com|org|net|edu|gov|io|co)', msg_lower):
            return True

    # Check for domain patterns (.com, .org, .net, etc)
    domain_pattern = r'\b\w+\.(com|org|net|edu|gov|io|co|uk|ca)\b'
    if re.search(domain_pattern, msg_lower):
        # Make sure it's not just a casual mention
        browse_verbs = ['open', 'visit', 'go to', 'navigate', 'check', 'read', 'fetch', 'load', 'show me']
        if any(verb in msg_lower for verb in browse_verbs):
            return True

    return False


def detect_music_play_intent(message: str) -> bool:
    """
    Detect requests to play music with improved false positive filtering.

    Key improvements:
    - Filters out "play" in non-music contexts (games, videos, sports, etc.)
    - Requires explicit music context or artist/genre mention
    - Excludes information-seeking queries
    """
    msg_lower = message.lower()

    # Non-music "play" contexts that should NOT trigger music
    non_music_play_contexts = [
        'play a game', 'play game', 'play games', 'play video game', 'play the game',
        'play a video', 'play video', 'play this video', 'play the video',
        'play a role', 'play the role', 'play a part', 'play the part',
        'play sports', 'play a sport', 'play basketball', 'play football', 'play soccer',
        'play tennis', 'play golf', 'play baseball', 'play hockey',
        'play cards', 'play poker', 'play chess', 'play checkers',
        'play with', 'play around', 'let\'s play', 'wanna play', 'want to play',
        'play a match', 'play the match', 'play a round',
        'play a trick', 'play tricks', 'play a joke', 'play pranks',
        'role play', 'roleplay', 'word play', 'wordplay', 'fair play',
        'at play', 'child\'s play', 'foul play', 'power play'
    ]
    if any(phrase in msg_lower for phrase in non_music_play_contexts):
        return False

    # Must have "play" or similar
    play_keywords = ['play', 'put on', 'listen to', 'start playing', 'i want to hear', 'can you play']
    has_play = any(kw in msg_lower for kw in play_keywords)

    if not has_play:
        return False

    # Music context signals
    music_nouns = ['music', 'song', 'songs', 'artist', 'album', 'track', 'playlist', 'tune', 'tunes']
    has_music_noun = any(noun in msg_lower for noun in music_nouns)

    # Common genres
    genres = ['jazz', 'rock', 'pop', 'classical', 'hip hop', 'country', 'r&b', 'electronic',
              'metal', 'punk', 'blues', 'soul', 'funk', 'reggae', 'folk', 'indie', 'edm', 'rap']
    has_genre = any(genre in msg_lower for genre in genres)

    # Some very common artists (not exhaustive - improved selector has the full list)
    common_artists = ['beatles', 'taylor swift', 'drake', 'queen', 'coldplay', 'ed sheeran',
                      'adele', 'beyonce', 'kanye', 'eminem', 'michael jackson', 'elvis',
                      'bruno mars', 'ariana grande', 'billie eilish', 'the weeknd']
    has_artist = any(artist in msg_lower for artist in common_artists)

    # Exclude information-seeking queries
    info_terms = ['search', 'find', 'information', 'info', 'who is', 'what is', 'tell me about',
                  'wikipedia', 'wiki', 'how old', 'when did', 'where is']
    if any(term in msg_lower for term in info_terms):
        return False

    # Must have play AND (music noun OR genre OR artist)
    return has_play and (has_music_noun or has_genre or has_artist)

def detect_music_control_intent(message: str) -> bool:
    """Detect requests to control currently playing music."""
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in MUSIC_CONTROL_KEYWORDS)

# ===== NEW: IMPROVED DETECTION FUNCTIONS =====


def detect_document_retrieval_intent(message: str) -> bool:
    """Detect if user wants to RETRIEVE/READ a specific document."""
    msg_lower = message.lower()

    # Strong signals for document retrieval
    retrieval_signals = [
        'read me', 'read to me', 'show me the', 'display the', 'view the',
        'open the', 'entire document', 'full document', 'whole document',
        'complete document', 'the document called', 'the file called',
        'document named', 'file named', 'in your documents folder',
        'from your documents'
    ]

    # Check if asking to read/retrieve
    has_retrieval_keyword = any(signal in msg_lower for signal in retrieval_signals)

    # Check if mentions a specific document name
    has_specific_document = any(keyword in msg_lower for keyword in [
        'document', 'file', 'pdf', '.txt', '.doc', '.md'
    ])

    return has_retrieval_keyword and has_specific_document


def detect_document_search_intent(message: str) -> bool:
    """Detect if user wants to SEARCH WITHIN document content (RAG/semantic search)."""
    msg_lower = message.lower()

    # Signals for searching within documents
    search_signals = [
        'what does my document say',
        'what do my documents say',
        'search my documents',
        'search documents for',
        'find in my documents',
        'according to my documents',
        'in my documents about',
        'do my documents mention',
        'information in my documents',
        'what information',
        'find information about'
    ]

    has_search_signal = any(signal in msg_lower for signal in search_signals)

    # Has document reference AND search intent
    has_document_ref = any(word in msg_lower for word in ['document', 'file', 'pdf', 'contract', 'policy'])

    return has_search_signal or (has_document_ref and 'about' in msg_lower)


def detect_camera_capture_intent(message: str) -> bool:
    """Detect if user wants to capture a camera image (what do you see?)."""
    msg_lower = message.lower()

    # Primary camera capture triggers
    camera_triggers = [
        'what do you see',
        'what can you see',
        'what are you seeing',
        "what's in front of you",
        'what is in front of you',
        'take a photo',
        'take a picture',
        'capture image',
        'capture photo',
        'show me what you see',
        'look around',
        'what are you looking at',
        'describe what you see',
        "what's happening right now",
        'what is happening right now',
        'show me your view',
        'use the camera',
        'use your camera',
        'camera photo',
        'camera picture'
    ]

    # Check for any trigger phrases
    return any(trigger in msg_lower for trigger in camera_triggers)


def detect_web_search_intent_improved(message: str) -> bool:
    """Detect if user wants to search the WEB/INTERNET (improved version)."""
    msg_lower = message.lower()

    # EXCLUDE: If explicitly asking for JavaScript/code execution, it's NOT a web search
    javascript_phrases = [
        'run javascript', 'execute javascript', 'use javascript', 'javascript code',
        'run js', 'execute js', 'run code', 'execute code', 'run the code'
    ]
    if any(phrase in msg_lower for phrase in javascript_phrases):
        return False

    # EXCLUDE: If asking for "current date/time" it's NOT a web search
    datetime_phrases = [
        'current date', 'current time', 'current datetime', 'today\'s date',
        'what time is it', 'what\'s the time', 'what is the time',
        'tell me the date', 'tell me the time', 'get the date', 'get the time'
    ]
    if any(phrase in msg_lower for phrase in datetime_phrases):
        return False

    # EXCLUDE: If the user is clearly asking to play music ("play music", "play song")
    if ('play' in msg_lower and any(term in msg_lower for term in ['music', 'song', 'artist', 'album'])):
        return False

    # Explicit web search signals
    explicit_web = [
        'search the web', 'search online', 'google', 'search for online',
        'look up online', 'search the internet', 'find on the web',
        'check online', 'search google', 'web search'
    ]

    # Implicit signals (current events, etc.) - but with more context
    implicit_web_phrases = [
        'current news', 'latest news', 'recent news',
        'current price', 'latest price', 'current events',
        'latest information', 'recent information',
        'news about', 'who won', 'what happened', 'update on', 'breaking news',
        'today\'s weather', 'current weather forecast'
    ]

    # Single word triggers that need more context
    temporal_words = ['current', 'latest', 'recent', 'today', 'this week', 'this month']

    has_explicit = any(signal in msg_lower for signal in explicit_web)
    has_implicit_phrase = any(phrase in msg_lower for phrase in implicit_web_phrases)

    # For single temporal words, check if they're used in a web search context
    has_temporal_with_context = False
    if any(word in msg_lower for word in temporal_words):
        # Check if paired with search/info/news context words
        search_context = ['news', 'information', 'search', 'find', 'look up', 'price', 'score', 'result', 'winner']
        if any(context in msg_lower for context in search_context):
            has_temporal_with_context = True

    # If mentions documents folder, it's NOT web search
    if 'documents folder' in msg_lower or 'my documents' in msg_lower or 'my files' in msg_lower:
        return False

    return has_explicit or has_implicit_phrase or has_temporal_with_context

def detect_hallucinated_search(response: str) -> bool:
    patterns = [r'i searched', r'according to (?:my|the) search', r'i found (?:that|the following)']
    return any(re.search(pattern, response.lower()) for pattern in patterns)


def detect_gmail_read_intent(message: str) -> bool:
    """Detect if user wants to read/check their Gmail."""
    msg_lower = message.lower()

    # Strong read/check signals
    read_signals = [
        'check my email', 'check email', 'read my email', 'read email',
        'show my email', 'show email', 'check my inbox', 'check inbox',
        'show my inbox', 'my inbox', 'read my inbox',
        'unread email', 'unread message', 'new email', 'new message',
        'recent email', 'latest email', 'my messages',
        'email from', 'message from', 'emails about',
        'do i have any email', 'any new email', 'check if i have'
    ]

    # Check for read signals
    has_read_signal = any(signal in msg_lower for signal in read_signals)

    # Additional check: mentions "email" or "message" with check/read/show
    has_email_word = 'email' in msg_lower or 'message' in msg_lower or 'inbox' in msg_lower or 'gmail' in msg_lower
    has_read_verb = any(verb in msg_lower for verb in ['check', 'read', 'show', 'see', 'get', 'find', 'look'])

    return has_read_signal or (has_email_word and has_read_verb)


def detect_gmail_send_intent(message: str) -> bool:
    """Detect if user wants to send an email."""
    msg_lower = message.lower()

    # Strong send signals
    send_signals = [
        'send email', 'send an email', 'send a message',
        'email to', 'email someone', 'write email', 'compose email',
        'send to', 'message to', 'mail to',
        'draft email', 'draft an email', 'draft a message'
    ]

    # Check for send signals
    has_send_signal = any(signal in msg_lower for signal in send_signals)

    # Additional check: "send" + "email"/"message"
    has_send = 'send' in msg_lower
    has_email_word = 'email' in msg_lower or 'message' in msg_lower or 'mail' in msg_lower

    return has_send_signal or (has_send and has_email_word)


def detect_gmail_reply_intent(message: str) -> bool:
    """Detect if user wants to reply to emails."""
    msg_lower = message.lower()

    # Strong reply signals
    reply_signals = [
        'reply to', 'reply to all', 'respond to', 'answer',
        'reply to email', 'reply to message', 'respond to email',
        'reply to the email', 'send a reply', 'write a reply',
        'reply to emails with', 'reply to all emails', 'respond to all'
    ]

    # Check for reply signals
    has_reply_signal = any(signal in msg_lower for signal in reply_signals)

    # Additional check: "reply" + email/message context
    has_reply = 'reply' in msg_lower or 'respond' in msg_lower or 'answer' in msg_lower
    has_email_context = any(word in msg_lower for word in ['email', 'message', 'inbox', 'fanmail', 'subject'])

    return has_reply_signal or (has_reply and has_email_context)


def detect_fanmail_reply_intent(message: str) -> bool:
    """Detect if user specifically wants to reply to fanmail."""
    msg_lower = message.lower()
    return ('fanmail' in msg_lower and
            any(word in msg_lower for word in ['reply', 'respond', 'answer']))


def detect_gmail_operation_intent(message: str) -> str | None:
    """
    CRITICAL: Explicitly determine if user wants to READ, SEND, or REPLY to email.
    Returns 'read_gmail', 'send_gmail', 'reply_gmail', or None.
    Priority: REPLY > SEND > READ
    """
    try:
        msg_lower = (message or "").lower().strip().replace("e-mail", "email")
    except Exception:
        return None
    
    # PRIORITY 1: REPLY indicators (most specific)
    reply_indicators = [
        "reply to", "reply to all", "respond to", "send a reply", "write a reply",
        "answer the email", "respond to email", "respond to message",
        "shoot a reply", "write back", "get back to", "respond back"
    ]
    if any(ind in msg_lower for ind in reply_indicators):
        return "reply_gmail"
    
    # PRIORITY 2: SEND indicators
    send_indicators = [
        "send email to", "send an email to", "send a message to",
        "email to", "compose email", "write email to", "draft email",
        "draft an email", "email them", "send them an email",
        "send her an email", "send him an email",
        "drop an email to", "ping via email", "shoot an email to"
    ]
    if any(ind in msg_lower for ind in send_indicators):
        return "send_gmail"
    if "send" in msg_lower and "email" in msg_lower and all(k not in msg_lower for k in ["reply", "respond"]):
        return "send_gmail"
    
    # PRIORITY 3: READ indicators
    read_indicators = [
        "check email", "check my email", "read email", "read my email", "read out",
        "read out only", "show email", "show my email", "check inbox", "my inbox",
        "unread email", "new email", "recent email", "latest email", "email from",
        "emails about", "do i have", "any new email", "look for email", "find email",
        "get email", "see my email", "what emails", "list email", "show inbox",
        "what emails do i have", "any new emails", "what's in my inbox",
        "check gmail", "open my inbox"
    ]
    if any(ind in msg_lower for ind in read_indicators):
        return "read_gmail"
    if "email" in msg_lower and any(v in msg_lower for v in ["check", "read", "show", "see", "get", "find", "look", "list", "tell"]):
        if all(k not in msg_lower for k in ["reply", "respond", "send"]):
            return "read_gmail"
    if "email" in msg_lower or "inbox" in msg_lower:
        return "read_gmail"
    
    return None


def extract_email_address(message: str) -> str | None:
    """Extract email address from message."""
    import re
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", message or "")
    return m.group(0) if m else None


def extract_email_subject_and_body(message: str) -> tuple:
    """Extract subject and body from natural language email request."""
    import re
    subject = ""
    body = ""
    
    subject_match = re.search(r'(?:subject|about)[:\s]+([^,.;]+)', message or "", re.IGNORECASE)
    if subject_match:
        subject = subject_match.group(1).strip()
        subject = re.sub(r'\b(right away|immediately|now|asap|urgent)\b', '', subject, flags=re.IGNORECASE).strip()
    
    for pattern in [
        r'(?:message|body|saying|tell (?:them|him|her))[:\s]+["\']?(.+?)["\']?(?:\s+(?:right away|immediately|now|asap))?$',
        r'(?:that says|saying)[:\s]+["\']?(.+?)["\']?(?:\s+(?:right away|immediately|now|asap))?$',
    ]:
        m = re.search(pattern, message or "", re.IGNORECASE)
        if m:
            body = m.group(1).strip().strip('\"\'')
            body = re.sub(r'\b(right away|immediately|now|asap|urgent)\b', '', body, flags=re.IGNORECASE).strip()
            break
    
    if not subject:
        if body:
            words = body.split()
            subject = ' '.join(words[:5]) + ('...' if len(words) > 5 else '')
        else:
            subject = "Message from Blue"
    if not body:
        body = "Hello! This is a message sent via Blue."
    
    return subject, body


def call_lm_studio(messages: List[Dict], include_tools: bool = True, force_tool: str = None) -> Dict:
    global _vision_queue

    if force_tool:
        messages = messages.copy()
        last_msg = messages[-1]
        if last_msg.get("role") == "user":
            original = last_msg["content"]
            instructions = {
                "web_search": "[You MUST use the web_search tool to answer this.]",
                "get_weather": "[You MUST use the get_weather tool to answer this.]",
                "control_lights": "[You MUST use the control_lights tool to do this.]",
                "search_documents": "[You MUST use the search_documents tool to answer this.]",
                "view_image": "[Use the view_image tool now to see the image. You can view and analyze images - the image will be shown to you after calling this tool.]",
                "capture_camera": "[Use the capture_camera tool now to look at what's in front of you. Your camera allows you to see your physical surroundings, so you can naturally discuss what's there.]",
                "play_music": "[You MUST use the play_music tool to do this.]",
                "control_music": "[You MUST use the control_music tool to do this.]",
                "music_visualizer": "[You MUST use the music_visualizer tool to do this.]",
                "create_document": "[You MUST use the create_document tool to create and save this file.]",
                "browse_website": "[You MUST use the browse_website tool to fetch and read this URL.]",
                "read_gmail": "[CRITICAL: You MUST use the read_gmail tool RIGHT NOW to check the email inbox. DO NOT say you can't access email - you CAN and you MUST use the tool! Call read_gmail immediately!]",
                "send_gmail": "[CRITICAL: You MUST use the send_gmail tool RIGHT NOW to send this email. Extract the recipient email address and message content from the user's request. After sending, CONFIRM to the user: 'I sent the email to [address]'. DO NOT say you can't send email - you CAN and you MUST use the tool! Call send_gmail immediately!]",
                "reply_gmail": "[CRITICAL: You MUST use the reply_gmail tool RIGHT NOW to reply to these emails. DO NOT say you can't reply - you CAN and you MUST use the tool! Call reply_gmail immediately!]"
            }

            # Special handling for fanmail read-first workflow
            if force_tool == "read_gmail" and 'fanmail' in original.lower() and 'reply' in original.lower():
                instructions["read_gmail"] = "[CRITICAL FANMAIL WORKFLOW: You MUST use the read_gmail tool FIRST to see what the fanmail says before you can write a reply! Use query 'subject:Fanmail' with include_body=true. After you READ the email content, THEN you can reply with specific details from their message. DO NOT reply without reading first!]"

            if force_tool in instructions:
                messages[-1] = {"role": "user", "content": f"{original}\n\n{instructions[force_tool]}"}

    # INJECT PENDING IMAGES as a NEW USER MESSAGE (CRITICAL FIX!)
    global _vision_queue
    if _vision_queue.has_images():
        print(f"   [VISION] Injecting {len(_vision_queue.pending_images)} image(s)")

        # Build image message
        image_parts = []

        # Add header
        if any(img.is_camera_capture for img in _vision_queue.pending_images):
            # Get visual memory context if available
            recognition_context = ""
            if VISUAL_MEMORY_AVAILABLE:
                try:
                    vm = get_visual_memory()
                    recognition_context = "\n\n" + vm.get_recognition_context()

                    # Get list of known people for enhanced understanding
                    people = vm.get_all_people()
                    known_people = [p['name'] for p in people]
                except Exception as e:
                    print(f"[VISUAL-MEMORY] Error loading context: {e}")
                    known_people = []

            # Build comprehensive vision prompt
            vision_prompt_parts = [
                "[You're now looking at your current surroundings through your camera. "
                "Respond naturally about what you observe, as if you're in the space looking around.]",
                "",
                "Observe comprehensively:",
                "• WHO is present and WHAT are they doing? (activities, body language)",
                "• HOW are people interacting? (collaborating, conversing, working alone)",
                "• EMOTIONAL context: What moods or emotions are visible?",
                "• OBJECTS in use: What are people actively using or engaged with?",
                "• NARRATIVE: What's the story of this moment?",
                ""
            ]

            # Add recognition context
            if recognition_context:
                vision_prompt_parts.append(recognition_context)

            # Add context awareness if available
            if CONTEXT_AWARENESS_AVAILABLE and known_people:
                try:
                    # Infer who might be present (this is simplified - real detection would be more sophisticated)
                    audience_prompt = adapt_for_audience("", known_people[:1])  # Default to Alex
                    vision_prompt_parts.append(audience_prompt)
                except Exception as e:
                    print(f"[CONTEXT-AWARE] Error: {e}")

            vision_prompt_parts.append(
                "\nRespond conversationally about your surroundings - not like describing a photograph."
            )

            image_parts.append({
                "type": "text",
                "text": "\n".join(vision_prompt_parts)
            })
        else:
            image_parts.append({"type": "text", "text": "[Images to analyze:]"})

        # Add each image
        for img_info in _vision_queue.pending_images:
            is_camera = img_info.is_camera_capture
            label = "[Your current view:]" if is_camera else f"Image: {img_info.filename}"

            image_parts.append({"type": "text", "text": f"\n{label}"})

            image_data = encode_image_to_base64(img_info.filepath)
            if image_data:
                image_parts.append(image_data)
                print(f"   [VISION] Added {img_info.filename}")

        # Add natural prompt for camera
        if any(img.is_camera_capture for img in _vision_queue.pending_images):
            image_parts.append({
                "type": "text",
                "text": "\n[Now respond naturally about what's in your environment. Talk about it conversationally, not like you're describing a picture.]"
            })

        # CRITICAL: Inject as USER message (not assistant)
        messages.append({"role": "user", "content": image_parts})

        print(f"   [VISION] Images injected as user message")
        _vision_queue.mark_as_viewed()
        _vision_queue.clear()

    payload = {
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": -1,
        "stream": False
    }

    if include_tools:
        payload["tools"] = TOOLS
        payload["tool_choice"] = "required" if force_tool else "auto"

    try:
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=360)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Error calling LM Studio: {e}")
        return None


def purge_old_camera_images(messages: List[Dict]) -> List[Dict]:
    """
    Remove old camera images from conversation to prevent confusion.

    Only keeps the most recent camera image reference.
    This prevents the model from seeing multiple camera captures and
    getting confused about which one is current.
    """
    print(f"   [VISION-CLEANUP] Checking conversation for old camera images...")

    # Find all messages with camera images
    camera_indices = []
    for i, msg in enumerate(messages):
        content = msg.get('content', '')
        if isinstance(content, str):
            if 'CAMERA' in content or 'camera_capture_' in content or 'camera_NEW_' in content:
                camera_indices.append(i)
        elif isinstance(content, list):
            # Check for camera-related text in multimodal content
            for part in content:
                if part.get('type') == 'text':
                    text = part.get('text', '')
                    if 'CAMERA' in text or 'camera_capture_' in text or 'camera_NEW_' in text:
                        camera_indices.append(i)
                        break

    if len(camera_indices) > 1:
        # Keep only the LAST camera message, remove older ones
        indices_to_remove = camera_indices[:-1]
        print(f"   [VISION-CLEANUP] Removing {len(indices_to_remove)} old camera image(s)")

        # Remove from back to front to maintain indices
        for idx in reversed(indices_to_remove):
            messages.pop(idx)
    else:
        print(f"   [VISION-CLEANUP] Found {len(camera_indices)} camera image(s), no cleanup needed")

    return messages


def process_with_tools(messages: List[Dict]) -> Dict:
    """Process conversation with tool support."""
    conversation_messages = messages.copy()

    # BUILD SYSTEM MESSAGE WITH MEMORY FACTS
    # Extract facts from .ocf conversations first
    ocf_facts = extract_ocf_facts(conversation_messages)
    facts_preamble = build_system_preamble()
    if ocf_facts:
        facts_preamble += ocf_facts
        log.info("[MEMORY] Injected extracted .ocf facts into system message")

    # IMPROVED SYSTEM PROMPT - Streamlined and clear
    system_msg = {
        "role": "system",
        "content": (
            f"{facts_preamble}\n\n"
            "You are Blue, a friendly home assistant. Keep responses brief and natural.\n\n"
            "=== TOOL SELECTION RULES ===\n\n"
            "CAMERA (highest priority):\n"
            "• 'What do you see?' → capture_camera\n"
            "• 'Look around' → capture_camera\n\n"
            "EMAIL (match carefully):\n"
            "• Check/read/show inbox → read_gmail\n"
            "• Send to [email address] → send_gmail (extract address!)\n"
            "• Reply/respond to email → reply_gmail\n"
            "• FANMAIL: First read_gmail, THEN reply_gmail\n\n"
            "MUSIC:\n"
            "• 'Play [song]' → play_music\n"
            "• Pause/skip/volume → control_music\n"
            "• 'Light show' → music_visualizer\n\n"
            "SEARCH (critical distinction!):\n"
            "• MY documents/files/contract → search_documents\n"
            "• Internet/news/google → web_search\n\n"
            "LIGHTS:\n"
            "• Turn on/off, color, mood → control_lights\n"
            "• Light show/dance → music_visualizer\n\n"
            "OTHER:\n"
            "• Weather → get_weather\n"
            "• Create file/list → create_document\n"
            "• Visit URL → browse_website\n"
            "• Run code → run_javascript\n\n"
            "NO TOOL NEEDED:\n"
            "• Greetings, jokes, general knowledge\n\n"
            "=== AFTER TOOL RUNS ===\n"
            "• Tool results are REAL - use them immediately\n"
            "• Don't say 'working on it' - it's already done\n"
            "• Don't claim you can't access - the tool worked\n\n"
            "Moods: moonlight, sunset, ocean, forest, romance, party, focus, relax, energize, movie, fireplace"
        )
    }

    if not conversation_messages or conversation_messages[0].get("role") != "system":
        conversation_messages.insert(0, system_msg)
    else:
        conversation_messages[0] = system_msg

    # ===== CONTEXT TRIMMING =====
    # To reduce confusion from very long conversations or previous tool results, we
    # limit the number of messages sent to the language model. We always keep
    # the system message at index 0 and the most recent (MAX_CONTEXT_MESSAGES-1)
    # messages following it. This helps the assistant focus on the current query.
    try:
        max_ctx = int(getattr(_settings, "MAX_CONTEXT_MESSAGES", 0))
        if max_ctx and len(conversation_messages) > max_ctx:
            # Preserve the system message at position 0, then keep the last (max_ctx-1) messages
            # Keep system message and trim context
            conversation_messages = [conversation_messages[0]] + conversation_messages[-(max_ctx - 1):]
    except Exception:
        # If any error occurs while trimming, proceed without trimming
        pass


    # Purge old camera images from conversation to prevent confusion
    conversation_messages = purge_old_camera_images(conversation_messages)

    max_iterations = _settings.MAX_ITERATIONS
    iteration = 0
    last_user_message = messages[-1].get("content", "") if messages else ""

    # ================================================================================
    # v8 ENHANCEMENT: Check for compound requests and follow-up corrections
    # ================================================================================
    
    # Check for compound requests ("play jazz and turn on romantic lights")
    compound_actions = parse_compound_request(last_user_message)
    if compound_actions:
        print(f"   [COMPOUND] Detected {len(compound_actions)} actions in request:")
        for action in compound_actions:
            print(f"      → {action['action']}: {action['query'][:50]}")
    
    # Check for follow-up corrections ("no, make it blue")
    state = get_conversation_state()
    correction = detect_follow_up_correction(last_user_message, {
        'last_tool_used': state.last_tool_used,
        'last_tool_result': state.last_tool_result
    })
    if correction and correction['is_correction']:
        print(f"   [CORRECTION] Detected correction for {correction['correction_type']}: {correction['new_value']}")
    
    # Check query complexity
    complexity = estimate_query_complexity(last_user_message)
    print(f"   [COMPLEXITY] Query complexity: {complexity}")

    # IMPROVED INTENT DETECTION with specialized functions

    # ================================================================================
    # PRIORITY CHECK: Camera Capture (must take NEW photo every time)
    # ================================================================================
    # This check happens BEFORE tool selector to ensure "what do you see?"
    # ALWAYS triggers a new camera capture, not a cached response
    if detect_camera_capture_intent(last_user_message):
        print(f"   [CAMERA-DETECT] ✅ Camera capture intent detected!")
        print(f"   [CAMERA-DETECT] Forcing NEW photo capture - bypassing tool selector")
        # Force the capture_camera tool to be called
        # This ensures a brand new photo is taken, not reusing old context
        improved_force_tool = "capture_camera"
        improved_tool_args = {}

        # Skip tool selector and go straight to execution
        # Set flags for compatibility
        is_greeting = False
        wants_music_play = False
        wants_music_control = False
        wants_visualizer = False
        wants_javascript = False
        wants_weather = False
        wants_lights = False
        wants_create_document = False
        wants_browse = False
        wants_gmail_read = False
        wants_gmail_send = False
        wants_gmail_reply = False
        wants_fanmail_reply = False
        wants_document_retrieval = False
        wants_document_search = False
        wants_web_search = False

        print(f"   [CAMERA-DETECT] Tool forced: capture_camera (will execute in iteration 1)")
    else:
        # Normal tool selection flow
        improved_force_tool = None
        improved_tool_args = None

    # ================================================================================
    # TOOL SELECTION: Improved (confidence-based) or Legacy (keyword-based)
    # ================================================================================

    # v8: Handle corrections first
    if correction and correction['is_correction'] and correction['new_value']:
        print(f"   [CORRECTION] Handling correction before tool selection")
        if correction['correction_type'] == 'lights':
            improved_force_tool = 'control_lights'
            if correction['new_value'] in ['brighter', 'dimmer']:
                improved_tool_args = {'action': 'brightness', 'brightness': 80 if correction['new_value'] == 'brighter' else 30}
            else:
                improved_tool_args = {'action': 'color', 'color': correction['new_value']}
        elif correction['correction_type'] == 'music':
            improved_force_tool = 'control_music'
            improved_tool_args = {'action': correction['new_value']}
        
        if improved_force_tool:
            print(f"   [CORRECTION] Forcing tool: {improved_force_tool} with {improved_tool_args}")

    if USE_IMPROVED_SELECTOR and not improved_force_tool:
        # ===== USE IMPROVED CONFIDENCE-BASED SELECTOR =====
        print(f"   [SELECTOR-V2] Using improved confidence-based tool selection")

        # Get recent history for context (last 5 messages)
        recent_history = conversation_messages[-5:] if len(conversation_messages) > 5 else conversation_messages

        # Run the improved selector
        selection_result = IMPROVED_TOOL_SELECTOR.select_tool(last_user_message, recent_history)

        # Check if disambiguation is needed
        if selection_result.needs_disambiguation:
            print(f"   [SELECTOR-V2] Low confidence - asking user for clarification")
            # Return disambiguation prompt to user
            conversation_messages.append({
                'role': 'assistant',
                'content': selection_result.disambiguation_prompt
            })
            return {
                'response': selection_result.disambiguation_prompt,
                'needs_clarification': True
            }

        # Set variables for compatibility with rest of code
        if selection_result.primary_tool:
            selected_tool = selection_result.primary_tool

            # Don't overwrite if priority detection (camera) already set a tool
            if not improved_force_tool:
                # Set tool name and args from selector
                improved_force_tool = selected_tool.tool_name
                improved_tool_args = selected_tool.extracted_params

                # Log selection details
                print(f"   [SELECTOR-V2] Selected: {improved_force_tool}")
                print(f"   [SELECTOR-V2] Confidence: {selected_tool.confidence:.2f}")
                print(f"   [SELECTOR-V2] Priority: {selected_tool.priority}")
                print(f"   [SELECTOR-V2] Reason: {selected_tool.reason}")
            else:
                print(f"   [SELECTOR-V2] Skipping selector - priority tool already set: {improved_force_tool}")

            if selection_result.alternative_tools:
                alt_names = [t.tool_name for t in selection_result.alternative_tools[:2]]
                print(f"   [SELECTOR-V2] Alternatives: {', '.join(alt_names)}")

            if selection_result.compound_request:
                print(f"   [SELECTOR-V2] WARNING: Compound request (multiple tools needed)")

            # Initialize legacy detection variables to False (not used with improved selector)
            is_greeting = False
            wants_music_play = False
            wants_music_control = False
            wants_visualizer = False
            wants_javascript = False
            wants_weather = False
            wants_lights = False
            wants_create_document = False
            wants_browse = False
            wants_gmail_read = False
            wants_gmail_send = False
            wants_gmail_reply = False
            wants_fanmail_reply = False
            wants_document_retrieval = False
            wants_document_search = False
            wants_web_search = False
        else:
            # No tool needed - conversational response (but only if no priority tool set)
            if not improved_force_tool:
                improved_force_tool = None
                improved_tool_args = None
                print(f"   [SELECTOR-V2] No tool needed - conversational response")
            else:
                print(f"   [SELECTOR-V2] Keeping priority tool: {improved_force_tool}")

            # Initialize detection variables
            is_greeting = True  # Treat as greeting if no tool
            wants_music_play = False
            wants_music_control = False
            wants_visualizer = False
            wants_javascript = False
            wants_weather = False
            wants_lights = False
            wants_create_document = False
            wants_browse = False
            wants_gmail_read = False
            wants_gmail_send = False
            wants_gmail_reply = False
            wants_fanmail_reply = False
            wants_document_retrieval = False
            wants_document_search = False
            wants_web_search = False
    else:
        # ===== USE LEGACY KEYWORD-BASED DETECTION =====
        print(f"   [SELECTOR-LEGACY] Using legacy keyword-based detection")
        # Don't overwrite improved_force_tool if it was set by priority detection (camera, etc.)
        if not improved_force_tool:
            improved_force_tool = None
            improved_tool_args = None
        else:
            print(f"   [SELECTOR-LEGACY] Keeping priority tool: {improved_force_tool}")

        # LEGACY DETECTION - Only run when NOT using improved selector
        is_greeting = detect_no_tool_intent(last_user_message)
        wants_music_play = detect_music_play_intent(last_user_message)
        wants_music_control = detect_music_control_intent(last_user_message)
        wants_visualizer = detect_visualizer_intent(last_user_message)
        wants_javascript = detect_javascript_intent(last_user_message)
        wants_weather = detect_weather_intent(last_user_message)
        wants_lights = detect_light_intent(last_user_message)
        wants_create_document = detect_create_document_intent(last_user_message)
        wants_browse = detect_browse_intent(last_user_message)

        # CRITICAL FIX (Oct 2024): Use unified Gmail operation detector to prevent READ/REPLY confusion
        gmail_operation = detect_gmail_operation_intent(last_user_message)
        wants_gmail_read = (gmail_operation == 'read_gmail')
        wants_gmail_send = (gmail_operation == 'send_gmail')
        wants_gmail_reply = (gmail_operation == 'reply_gmail')
        wants_fanmail_reply = detect_fanmail_reply_intent(last_user_message)

        # NEW: Distinguish between document operations
        wants_document_retrieval = detect_document_retrieval_intent(last_user_message)
        wants_document_search = detect_document_search_intent(last_user_message)

        # NEW: Better web search detection
        wants_web_search = detect_web_search_intent_improved(last_user_message)

        # LOGGING - Show all detected intents with clear categorization
        print(f"   [DETECT-LEGACY] Intent analysis:")
        if is_greeting:
            print(f"      → Greeting/casual chat (NO TOOL NEEDED)")
        if wants_music_play:
            print(f"      → Play music request")
        if wants_music_control:
            print(f"      → Music control request")
        if wants_visualizer:
            print(f"      → Light visualizer request")
        if wants_javascript:
            print(f"      → JavaScript/code execution request")
        if wants_document_retrieval:
            print(f"      → Document RETRIEVAL request (read specific document)")
        if wants_document_search:
            print(f"      → Document SEARCH request (search within documents)")
        if wants_web_search:
            print(f"      → WEB SEARCH request (search internet)")
        if wants_weather:
            print(f"      → Weather request")
        if wants_lights:
            print(f"      → Light control request")
        if wants_create_document:
            print(f"      → Document creation request")
        if wants_browse:
            print(f"      → Website browse request")
        if wants_gmail_read:
            print(f"      → Gmail READ request (check inbox)")
        if wants_gmail_send:
            print(f"      → Gmail SEND request (send email)")
        if wants_gmail_reply:
            print(f"      → Gmail REPLY request (reply to emails)")
            if wants_fanmail_reply:
                print(f"      → FANMAIL REPLY detected!")

    # Track if fanmail has been read in this conversation (always needed)
    fanmail_has_been_read = False
    for msg in conversation_messages:
        if msg.get("role") == "tool" and "Fanmail" in msg.get("content", ""):
            fanmail_has_been_read = True
            break

    # Check for questions that need information
    question_words = ['what', 'when', 'where', 'who', 'why', 'how', 'which', 'tell me', 'explain', 'show me']
    is_question = any(word in last_user_message.lower() for word in question_words)

    while iteration < max_iterations:
        iteration += 1
        print(f"\n[ITER] Iteration {iteration}")

        force_tool = None

        # ITERATION 1: Force correct tool based on clear intent
        if iteration == 1:
            # Check if priority detection (camera, etc.) already set a tool
            # This works regardless of which selector is being used
            if improved_force_tool:
                force_tool = improved_force_tool
                print(f"   [FORCE] Using tool from priority detection: {force_tool}")
                # Skip to tool execution
            elif is_greeting:
                print("   [SKIP] Greeting detected - no tool needed")
                force_tool = None  # Let model respond naturally

            # PRIORITY 1: Music and visualizer (very specific keywords)
            elif wants_visualizer:
                force_tool = "music_visualizer"
                print("   [FORCE] Forcing music_visualizer")
            elif wants_music_play:
                force_tool = "play_music"
                print("   [FORCE] Forcing play_music")
            elif wants_music_control:
                force_tool = "control_music"
                print("   [FORCE] Forcing control_music")

            # PRIORITY 2: JavaScript/code execution (explicit tool mention)
            elif wants_javascript:
                force_tool = "run_javascript"
                print("   [FORCE] Forcing run_javascript")

            # PRIORITY 3A: Document RETRIEVAL (reading a specific document)
            elif wants_document_retrieval:
                force_tool = "search_documents"
                print("   [FORCE] Forcing search_documents (retrieval mode - user wants to read specific document)")

            # PRIORITY 3B: Document SEARCH (searching within documents)
            elif wants_document_search:
                force_tool = "search_documents"
                print("   [FORCE] Forcing search_documents (search mode - user wants to find info in documents)")

            # PRIORITY 3C: Document creation (user wants to create/save files)
            elif wants_create_document:
                force_tool = "create_document"
                print("   [FORCE] Forcing create_document")

            # PRIORITY 3D: Gmail READ (user wants to check/read email)
            elif wants_gmail_read:
                force_tool = "read_gmail"
                print("   [FORCE] Forcing read_gmail (check email inbox)")

            # PRIORITY 3E: Gmail SEND (user wants to send email)
            elif wants_gmail_send:
                force_tool = "send_gmail"
                print("   [FORCE] Forcing send_gmail (send email)")

            # PRIORITY 3F: Gmail REPLY (user wants to reply to emails)
            elif wants_gmail_reply:
                # SPECIAL FANMAIL WORKFLOW: Force read first if this is a fanmail reply and they haven't read it yet
                if wants_fanmail_reply and not fanmail_has_been_read:
                    force_tool = "read_gmail"
                    print("   [FORCE] Forcing read_gmail FIRST (must read fanmail before replying!)")
                    print("   [INFO] Fanmail reply detected - enforcing two-step workflow")
                else:
                    force_tool = "reply_gmail"
                    print("   [FORCE] Forcing reply_gmail (reply to emails)")

            # PRIORITY 4: Browse website (explicit URL navigation) - AFTER documents
            elif wants_browse:
                force_tool = "browse_website"
                print("   [FORCE] Forcing browse_website")

            # PRIORITY 5: Light control
            elif wants_lights:
                force_tool = "control_lights"
                print("   [FORCE] Forcing control_lights")

            # PRIORITY 6: Weather (specific and clear)
            elif wants_weather and not wants_web_search:
                force_tool = "get_weather"
                print("   [FORCE] Forcing get_weather")

            # PRIORITY 7: Web search (explicit search requests, but not if other tools requested)
            elif wants_web_search and not wants_document_search and not wants_document_retrieval and not wants_javascript:
                force_tool = "web_search"
                print("   [FORCE] Forcing web_search")

            # PRIORITY 8: Questions that likely need current info
            elif is_question and not is_greeting:
                # Check if it's about user's documents (must be specific, not just "my friend" etc)
                doc_phrases = [
                    'my document', 'my file', 'my contract', 'my pdf', 'my upload',
                    'our document', 'our file', 'our contract',
                    'in the document', 'in my document', 'in the file',
                    'according to my', 'what does my contract', 'what does my file'
                ]
                if any(phrase in last_user_message.lower() for phrase in doc_phrases):
                    force_tool = "search_documents"  # Force when asking about user content
                    print("   [FORCE] Question about user content - forcing search_documents")
                # Check if it's asking about current events, recent info, or unknowns
                elif any(word in last_user_message.lower() for word in ['latest', 'recent', 'current', 'today', 'who won', 'what happened']):
                    force_tool = "web_search"
                    print("   [FORCE] Current info question - forcing web_search")
                # General knowledge questions don't need tools
                else:
                    print("   [ALLOW] General knowledge question - no tool forced")
            else:
                print("   [ALLOW] No clear tool intent - letting model decide")

        response = call_lm_studio(conversation_messages, include_tools=True, force_tool=force_tool)

        if not response:
            return {"choices": [{"message": {"role": "assistant", "content": "I'm having trouble connecting."}}]}

        assistant_message = response["choices"][0]["message"]
        tool_calls = assistant_message.get("tool_calls", [])

        if not tool_calls:
            content = assistant_message.get("content", "")

            # Check if model should have used a tool but didn't
            if iteration == 1:
                should_have_used_tool = False
                correct_tool = None

                # Music requests should ALWAYS use tools
                if wants_music_play and 'play_music' not in content.lower():
                    should_have_used_tool = True
                    correct_tool = "play_music"
                    print(f"   [ERROR] Model answered music request without play_music tool!")

                elif wants_music_control and 'control_music' not in content.lower():
                    should_have_used_tool = True
                    correct_tool = "control_music"
                    print(f"   [ERROR] Model answered music control without control_music tool!")

                # Visualizer requests should ALWAYS use tools
                elif wants_visualizer:
                    should_have_used_tool = True
                    correct_tool = "music_visualizer"
                    print(f"   [ERROR] Model answered visualizer request without music_visualizer tool!")

                # Explicit search requests should ALWAYS search
                elif 'search for' in last_user_message.lower() or 'google' in last_user_message.lower():
                    should_have_used_tool = True
                    correct_tool = "web_search"
                    print(f"   [ERROR] Model answered explicit search without web_search tool!")

                # Document questions: force tool when explicitly asked
                elif wants_document_retrieval or wants_document_search:
                    should_have_used_tool = True
                    correct_tool = "search_documents"
                    if wants_document_retrieval:
                        print(f"   [INFO] Document retrieval request -> forcing search_documents")
                    else:
                        print(f"   [INFO] Document search request -> forcing search_documents")
                # Weather requests should use weather tool
                elif wants_weather and not wants_web_search:
                    should_have_used_tool = True
                    correct_tool = "get_weather"
                    print(f"   [ERROR] Model answered weather without get_weather tool!")

                # Light control should use light tool
                elif wants_lights and not wants_visualizer:
                    should_have_used_tool = True
                    correct_tool = "control_lights"
                    print(f"   [ERROR] Model answered light control without control_lights tool!")

                # Document creation requests should use create_document tool
                elif wants_create_document:
                    should_have_used_tool = True
                    correct_tool = "create_document"
                    print(f"   [ERROR] Model answered document creation without create_document tool!")

                # Gmail READ requests should ALWAYS use read_gmail
                elif wants_gmail_read:
                    should_have_used_tool = True
                    correct_tool = "read_gmail"
                    print(f"   [ERROR] Model answered email check without read_gmail tool!")

                # Gmail SEND requests should ALWAYS use send_gmail
                elif wants_gmail_send:
                    should_have_used_tool = True
                    correct_tool = "send_gmail"
                    print(f"   [ERROR] Model answered email send without send_gmail tool!")

                # Gmail REPLY requests should ALWAYS use reply_gmail
                elif wants_gmail_reply:
                    should_have_used_tool = True
                    correct_tool = "reply_gmail"
                    print(f"   [ERROR] Model answered email reply without reply_gmail tool!")

                # Browse requests should use browse_website tool
                elif wants_browse:
                    should_have_used_tool = True
                    correct_tool = "browse_website"
                    print(f"   [ERROR] Model answered browse request without browse_website tool!")

                # Force the correct tool if model skipped it
                if should_have_used_tool and correct_tool:
                    print(f"   [RETRY] Forcing {correct_tool} and retrying...")
                    # Create a tool call manually
                    tool_args = {}
                    if correct_tool == "play_music":
                        # Extract what to play from the message
                        tool_args = {"query": last_user_message.replace("play", "").strip()[:100]}
                    elif correct_tool == "control_music":
                        # Detect the action
                        msg_lower = last_user_message.lower()
                        if 'pause' in msg_lower or 'stop' in msg_lower:
                            tool_args = {"action": "pause"}
                        elif 'resume' in msg_lower or 'unpause' in msg_lower:
                            tool_args = {"action": "resume"}
                        elif 'next' in msg_lower or 'skip' in msg_lower:
                            tool_args = {"action": "next"}
                        elif 'previous' in msg_lower or 'back' in msg_lower:
                            tool_args = {"action": "previous"}
                        elif 'volume up' in msg_lower or 'louder' in msg_lower or 'turn up' in msg_lower:
                            tool_args = {"action": "volume_up"}
                        elif 'volume down' in msg_lower or 'quieter' in msg_lower or 'turn down' in msg_lower:
                            tool_args = {"action": "volume_down"}
                        elif 'mute' in msg_lower:
                            tool_args = {"action": "mute"}
                        else:
                            tool_args = {"action": "pause"}  # default
                    elif correct_tool == "music_visualizer":
                        tool_args = {"action": "start", "duration": 300, "style": "party"}
                    elif correct_tool == "web_search":
                        query = last_user_message.replace("search for", "").replace("google", "").strip()
                        tool_args = {"query": query[:100]}
                    elif correct_tool == "search_documents":
                        if AUTO_DOCSEARCH_MODE == "aggressive":
                            tool_args = {"query": last_user_message[:100]}
                        else:
                            tool_args = None  # do not auto-search in opt-in mode
                    elif correct_tool == "get_weather":
                        # Extract location
                        words = last_user_message.split()
                        location = next((w for w in words if w[0].isupper() and len(w) > 2), "Toronto")
                        tool_args = {"location": location}
                    elif correct_tool == "control_lights":
                        # Try to detect action
                        msg_lower = last_user_message.lower()
                        if 'on' in msg_lower and 'turn' in msg_lower:
                            tool_args = {"action": "on"}
                        elif 'off' in msg_lower and 'turn' in msg_lower:
                            tool_args = {"action": "off"}
                        elif any(mood in msg_lower for mood in MOOD_PRESETS.keys()):
                            mood = next(m for m in MOOD_PRESETS.keys() if m in msg_lower)
                            tool_args = {"action": "mood", "mood": mood}
                        else:
                            tool_args = {"action": "status"}
                    elif correct_tool == "create_document":
                        # Create filename and placeholder content
                        msg_lower = last_user_message.lower()
                        # Try to extract a filename or type
                        if 'shopping' in msg_lower:
                            filename = "shopping_list.txt"
                            content = "Shopping List:\n\n[Items will be added here]"
                        elif 'todo' in msg_lower or 'to-do' in msg_lower or 'to do' in msg_lower:
                            filename = "todo_list.txt"
                            content = "To-Do List:\n\n[Tasks will be added here]"
                        elif 'recipe' in msg_lower:
                            filename = "recipe.txt"
                            content = "Recipe:\n\n[Recipe details will be added here]"
                        elif 'notes' in msg_lower or 'note' in msg_lower:
                            filename = "notes.txt"
                            content = "Notes:\n\n[Content will be added here]"
                        else:
                            filename = "document.txt"
                            content = "[Document content]"

                        file_type = "txt"
                        if '.md' in msg_lower or 'markdown' in msg_lower:
                            file_type = "md"
                            filename = filename.replace('.txt', '.md')

                        tool_args = {"filename": filename, "content": content, "file_type": file_type}
                    elif correct_tool == "browse_website":
                        # Extract URL from message
                        import re
                        url_match = re.search(r'https?://\S+', last_user_message)
                        if url_match:
                            url = url_match.group(0)
                        else:
                            # Look for www.domain.com pattern
                            www_match = re.search(r'www\.\S+', last_user_message)
                            if www_match:
                                url = "https://" + www_match.group(0)
                            else:
                                # Look for domain.com pattern
                                domain_match = re.search(r'\b(\w+\.(com|org|net|edu|gov|io|co))\b', last_user_message.lower())
                                if domain_match:
                                    url = "https://" + domain_match.group(0)
                                else:
                                    url = "https://example.com"  # fallback

                        tool_args = {"url": url, "extract": "text", "include_links": True}

                    elif correct_tool == "read_gmail":
                        # Extract query parameters from message
                        query = ""
                        max_results = 10
                        include_body = False

                        msg_lower = last_user_message.lower()

                        # Check for specific search terms
                        if "unread" in msg_lower:
                            query = "is:unread"
                        elif "from" in msg_lower:
                            # Try to extract sender
                            import re
                            from_match = re.search(r'from\s+([^\s,]+)', msg_lower)
                            if from_match:
                                query = f"from:{from_match.group(1)}"
                        elif "about" in msg_lower or "subject" in msg_lower:
                            # Try to extract subject
                            subject_match = re.search(r'(?:about|subject)\s+([^\s,]+)', msg_lower)
                            if subject_match:
                                query = f"subject:{subject_match.group(1)}"

                        # Check if they want full content
                        if any(word in msg_lower for word in ["full", "entire", "complete", "content", "body"]):
                            include_body = True

                        tool_args = {"query": query, "max_results": max_results, "include_body": include_body}

                    elif correct_tool == "send_gmail":
                        # Extract email components from message
                        to_address = extract_email_address(last_user_message)
                        subject, body = extract_email_subject_and_body(last_user_message)

                        if not to_address:
                            # If no email found, try to get it from the message context
                            # Default to a placeholder that will show error
                            to_address = "MISSING_ADDRESS@example.com"

                        tool_args = {
                            "to": to_address,
                            "subject": subject,
                            "body": body
                        }
                        print(f"   [EMAIL] Extracted: to={to_address}, subject={subject}")

                    elif correct_tool == "reply_gmail":
                        # Extract query and reply body
                        query = ""
                        reply_body = ""

                        msg_lower = last_user_message.lower()

                        # Look for what to reply to
                        if "fanmail" in msg_lower:
                            query = "subject:Fanmail"
                        elif "unread" in msg_lower:
                            query = "is:unread"
                        elif "from" in msg_lower:
                            import re
                            from_match = re.search(r'from\s+([^\s,]+)', msg_lower)
                            if from_match:
                                query = f"from:{from_match.group(1)}"

                        # Extract reply message
                        reply_patterns = [
                            r'(?:reply|respond|say|write|tell them)[:\s]+(.+)',
                            r'(?:saying|message)[:\s]+(.+)',
                        ]
                        import re
                        for pattern in reply_patterns:
                            reply_match = re.search(pattern, last_user_message, re.IGNORECASE)
                            if reply_match:
                                reply_body = reply_match.group(1).strip().strip('"\'')
                                break

                        if not reply_body:
                            reply_body = "Thank you for your message!"

                        tool_args = {
                            "query": query,
                            "reply_body": reply_body,
                            "reply_all": False
                        }
                        print(f"   [EMAIL] Reply: query={query}, body={reply_body[:50]}...")

                    if tool_args is not None:
                        # Execute the tool
                        tool_result = execute_tool(correct_tool, tool_args)
                        conversation_messages.append({
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [{"id": "forced", "type": "function", "function": {"name": correct_tool, "arguments": json.dumps(tool_args)}}]
                        })
                        conversation_messages.append({
                            "role": "tool",
                            "tool_call_id": "forced",
                            "name": correct_tool,
                            "content": tool_result
                        })
                        continue
                    conversation_messages.append({
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [{"id": "forced", "type": "function", "function": {"name": correct_tool, "arguments": json.dumps(tool_args)}}]
                    })
                    conversation_messages.append({
                        "role": "tool",
                        "tool_call_id": "forced",
                        "name": correct_tool,
                        "content": tool_result
                    })
                    continue

            # Check if model is hallucinating search results
            if detect_hallucinated_search(content):
                print("   [WARN]  AI IS HALLUCINATING - forcing search")
                search_query = last_user_message.replace("search for", "").strip()[:100]
                search_result = execute_tool("web_search", {"query": search_query})
                conversation_messages.append({
                    "role": "assistant",
                    "content": "Let me search for that.",
                    "tool_calls": [{"id": "forced", "type": "function", "function": {"name": "web_search", "arguments": json.dumps({"query": search_query})}}]
                })
                conversation_messages.append({"role": "tool", "tool_call_id": "forced", "name": "web_search", "content": search_result})
                continue

            # CRITICAL FIX: Detect if model is denying tool capabilities after successfully using them
            if iteration > 1:  # Only check after first iteration (after tools have been used)
                denial_phrases = [
                    "can't access", "cannot access", "don't have access", "no access to",
                    "unable to access", "not able to access", "can't browse", "cannot browse",
                    "can't visit", "cannot visit", "no links", "no pages", "can't reach",
                    "unable to browse", "unable to visit", "don't have the ability to",
                    "i'm here with you", "just us"
                ]

                # ADDED: Filler phrases - model acknowledges tool but doesn't use results
                filler_phrases = [
                    "working on", "just a moment", "let me", "i'll", "i will",
                    "give me a moment", "one moment", "accessing now", "trying to",
                    "attempting to", "in progress", "loading"
                ]

                # ADDED: Hallucinated error phrases - model claims failure when tool succeeded
                hallucinated_error_phrases = [
                    "browser initialization failed", "initialization failed", "could not be accessed",
                    "access failed", "connection failed", "unable to reach", "failed to connect",
                    "error accessing", "error connecting", "access denied", "request failed"
                ]

                content_lower = content.lower()
                is_denial = any(phrase in content_lower for phrase in denial_phrases)
                is_filler = any(phrase in content_lower for phrase in filler_phrases)
                is_hallucinated_error = any(phrase in content_lower for phrase in hallucinated_error_phrases)

                # Check if response is too short to contain actual results
                is_too_short = len(content.strip()) < 100

                # Check if the tool actually succeeded by looking at the last tool result
                tool_actually_succeeded = False
                if is_hallucinated_error:
                    # Check the last tool result to see if it actually succeeded
                    for msg in reversed(conversation_messages):
                        if msg.get("role") == "tool":
                            try:
                                result_obj = json.loads(msg.get("content", "{}"))
                                tool_actually_succeeded = result_obj.get("success", False)
                            except Exception:
                                pass
                            break

                if is_denial or (is_filler and is_too_short) or (is_hallucinated_error and tool_actually_succeeded):
                    if is_hallucinated_error and tool_actually_succeeded:
                        reason = "hallucinating an error when the tool actually succeeded"
                    elif is_denial:
                        reason = "denying tool capabilities"
                    else:
                        reason = "giving filler response instead of using tool results"
                    print(f"   [FIX] Model is {reason} - FORCING ACKNOWLEDGMENT")

                    # Find the most recent tool result
                    last_tool_result = None
                    last_tool_name = None
                    for msg in reversed(conversation_messages):
                        if msg.get("role") == "tool":
                            last_tool_result = msg.get("content", "")
                            last_tool_name = msg.get("name", "")
                            break

                    if last_tool_result and last_tool_name:
                        # Parse the tool result to give better feedback
                        tool_succeeded = False
                        tool_summary = ""

                        try:
                            result_obj = json.loads(last_tool_result)
                            # FIXED: Default to True if success field is missing (backwards compatible)
                            tool_succeeded = result_obj.get("success", True)

                            # FIXED: Even if success is False, check if there's actual content
                            # This handles tools that don't set success field properly
                            if not tool_succeeded and (result_obj.get("text") or result_obj.get("results")):
                                tool_succeeded = True

                            if tool_succeeded:
                                if last_tool_name == "browse_website":
                                    text_content = result_obj.get("text", "")[:500]
                                    url = result_obj.get("url", "")
                                    tool_summary = f"Successfully fetched {url}. Content preview:\n{text_content}"
                                elif last_tool_name == "web_search":
                                    # FIXED: Handle new JSON format properly
                                    results = result_obj.get("results", [])
                                    if results:
                                        tool_summary = f"Search completed. Found {len(results)} results:\n"
                                        for i, res in enumerate(results[:3], 1):
                                            tool_summary += f"{i}. {res.get('title', 'Untitled')}\n   {res.get('snippet', '')[:100]}\n"
                                    else:
                                        tool_summary = last_tool_result[:500]
                                else:
                                    tool_summary = last_tool_result[:500]
                            else:
                                error_msg = result_obj.get("error", "Unknown error")
                                tool_summary = f"Tool failed with error: {error_msg}"
                        except json.JSONDecodeError:
                            # FIXED: If it's not JSON, assume it's successful text output
                            tool_succeeded = True if last_tool_result.strip() else False
                            tool_summary = last_tool_result[:500]

                        # Add a STRONG instruction message forcing the model to use the results
                        if tool_succeeded:
                            correction_msg = (
                                f"STOP. The {last_tool_name} tool ALREADY FINISHED executing and was SUCCESSFUL. "
                                f"DO NOT say 'I'm working on it' or 'just a moment' - the tool ALREADY completed!\n\n"
                                f"Here are the actual results:\n\n{tool_summary}\n\n"
                                f"Now, IMMEDIATELY use this information to answer the question. "
                                f"Do NOT say you're 'trying to access' or 'working on accessing' - you ALREADY accessed it successfully! "
                                f"Just tell me what you found in the results above."
                            )
                        else:
                            correction_msg = (
                                f"The {last_tool_name} tool executed but encountered an error:\n\n{tool_summary}\n\n"
                                f"Tell the user about this error clearly and honestly. "
                                f"Do NOT make up fake error messages like 'browser initialization failed' - use the ACTUAL error message above."
                            )

                        conversation_messages.append({
                            "role": "user",
                            "content": correction_msg
                        })
                        print(f"   [RETRY] Added correction message to force model to use {last_tool_name} results")
                        continue  # Loop back to get a new response

            print("[OK] Response complete (no tool calls)")
            return response

        print(f"[TOOL] Model requested {len(tool_calls)} tool call(s)")

        # Check if model is using tools when it shouldn't
        if is_greeting and not force_tool:
            print(f"   [WARN] Model called tool for greeting/casual chat - this is unnecessary!")
            # Let it proceed but warn in logs

        conversation_messages.append(assistant_message)

        for tool_call in tool_calls:
            function_name = tool_call["function"]["name"]
            function_args = json.loads(tool_call["function"]["arguments"])
            tool_result = execute_tool(function_name, function_args)
            conversation_messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": function_name,
                "content": tool_result
            })

            # CRITICAL FIX (Oct 2024): Add operation-specific reminders for Gmail operations
            # This prevents Blue from confusing READ with REPLY operations
            if function_name == "read_gmail":
                try:
                    result_data = json.loads(tool_result)
                    if result_data.get("success"):
                        reminder = (
                            "[OPERATION COMPLETE: You just READ/CHECKED emails. "
                            "The user asked you to READ or CHECK their inbox, NOT to reply or send. "
                            "Now summarize what emails you found. "
                            "Do NOT say you 'replied' or 'sent' anything - you only READ the emails!]"
                        )
                        conversation_messages.append({
                            "role": "user",
                            "content": reminder
                        })
                        print("   [INFO] Added READ operation reminder to prevent confusion")
                except Exception:
                    pass

            elif function_name == "reply_gmail":
                try:
                    result_data = json.loads(tool_result)
                    if result_data.get("success"):
                        reminder = (
                            "[OPERATION COMPLETE: You just REPLIED to emails. "
                            "The user asked you to REPLY or RESPOND, and you successfully did so. "
                            "Now confirm what you did. "
                            "Do NOT say you only 'read' or 'checked' - you actually REPLIED to the emails!]"
                        )
                        conversation_messages.append({
                            "role": "user",
                            "content": reminder
                        })
                        print("   [INFO] Added REPLY operation reminder")
                except Exception:
                    pass

            elif function_name == "send_gmail":
                try:
                    result_data = json.loads(tool_result)
                    if result_data.get("success"):
                        reminder = (
                            "[OPERATION COMPLETE: You just SENT a new email. "
                            "The user asked you to SEND an email, and you successfully did so. "
                            "Now confirm what you did.]"
                        )
                        conversation_messages.append({
                            "role": "user",
                            "content": reminder
                        })
                        print("   [INFO] Added SEND operation reminder")
                except Exception:
                    pass

            # Special handling: If this was read_gmail for fanmail, add a reminder to reply with specific content
            if function_name == "read_gmail" and "fanmail" in str(function_args).lower():
                try:
                    result_data = json.loads(tool_result)
                    if result_data.get("success") and result_data.get("emails"):
                        # Add a system reminder about replying to the specific content
                        conversation_messages.append({
                            "role": "user",
                            "content": "[SYSTEM REMINDER: You just read the fanmail content above. Now compose a personalized reply that SPECIFICALLY addresses what the sender wrote. Reference details from their message in your reply. Do NOT send a generic 'thank you' - make it personal and contextual!]"
                        })
                        print("   [INFO] Added fanmail reply reminder to conversation")
                except Exception:
                    pass

    return {"choices": [{"message": {"role": "assistant", "content": "I couldn't complete your request."}}]}


# ===== WEB INTERFACE FOR DOCUMENT MANAGEMENT =====

DOCUMENT_MANAGER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Blue Document Manager [DOC]</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }
        .header p {
            opacity: 0.9;
            font-size: 1.1em;
        }
        .content {
            padding: 40px;
        }
        .upload-section {
            background: #f8f9fa;
            border: 3px dashed #667eea;
            border-radius: 15px;
            padding: 40px;
            text-align: center;
            margin-bottom: 40px;
            transition: all 0.3s;
        }
        .upload-section:hover {
            border-color: #764ba2;
            background: #f0f1f5;
        }
        .upload-section h2 {
            color: #667eea;
            margin-bottom: 20px;
        }
        .file-input-wrapper {
            position: relative;
            overflow: hidden;
            display: inline-block;
        }
        .file-input-wrapper input[type=file] {
            position: absolute;
            left: -9999px;
        }
        .file-input-label {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 40px;
            border-radius: 50px;
            cursor: pointer;
            font-size: 1.1em;
            font-weight: 600;
            transition: transform 0.2s;
            display: inline-block;
        }
        .file-input-label:hover {
            transform: scale(1.05);
        }
        .file-name {
            margin-top: 20px;
            color: #666;
            font-style: italic;
        }
        .upload-btn {
            background: #28a745;
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 50px;
            font-size: 1.1em;
            font-weight: 600;
            cursor: pointer;
            margin-top: 20px;
            transition: transform 0.2s;
        }
        .upload-btn:hover:not(:disabled) {
            transform: scale(1.05);
        }
        .upload-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .documents-list {
            margin-top: 40px;
        }
        .documents-list h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5em;
        }
        .document-item {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: transform 0.2s;
        }
        .document-item:hover {
            transform: translateX(5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .document-info {
            flex: 1;
        }
        .document-name {
            font-weight: 600;
            color: #667eea;
            font-size: 1.1em;
            margin-bottom: 5px;
        }
        .document-meta {
            color: #666;
            font-size: 0.9em;
        }
        .delete-btn {
            background: #dc3545;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            transition: transform 0.2s;
            text-decoration: none;
            font-size: 14px;
        }
        .delete-btn:hover {
            transform: scale(1.05);
        }
        .download-btn {
            background: #28a745;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            transition: transform 0.2s;
            text-decoration: none;
            font-size: 14px;
            display: inline-block;
        }
        .download-btn:hover {
            transform: scale(1.05);
            background: #218838;
        }
        .message {
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            font-weight: 500;
        }
        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
        }
        .stat-number {
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 5px;
        }
        .stat-label {
            font-size: 1em;
            opacity: 0.9;
        }
        .back-link {
            display: inline-block;
            margin-top: 20px;
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }
        .back-link:hover {
            text-decoration: underline;
        }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }
        .empty-state-icon {
            font-size: 4em;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎵💡 Blue Document Manager</h1>
            <p>Upload documents to teach Blue about your files</p>
        </div>

        <div class="content">
            {% if message %}
            <div class="message {{ message_type }}">
                {{ message }}
            </div>
            {% endif %}

            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{{ document_count }}</div>
                    <div class="stat-label">Documents</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ total_size }}</div>
                    <div class="stat-label">Total Size</div>
                </div>
            </div>

            <div class="upload-section">
                <h2>📤 Upload New Document</h2>
                <p style="color: #666; margin-bottom: 20px;">
                    Supported: PDF, Word (.doc, .docx), Text (.txt, .md)
                </p>
                <form method="POST" enctype="multipart/form-data" id="uploadForm">
                    <div class="file-input-wrapper">
                        <input type="file" name="file" id="fileInput" accept=".pdf,.doc,.docx,.txt,.md" required>
                        <label for="fileInput" class="file-input-label">
                            Choose File
                        </label>
                    </div>
                    <div class="file-name" id="fileName">No file chosen</div>
                    <br>
                    <button type="submit" class="upload-btn" id="uploadBtn">
                        Upload & Index
                    </button>
                </form>
            </div>

            <div class="documents-list">
                <h2>📚 Your Documents</h2>
                {% if documents %}
                    {% for doc in documents %}
                    <div class="document-item">
                        <div class="document-info">
                            <div class="document-name">{{ doc.filename }}</div>
                            <div class="document-meta">
                                Uploaded: {{ doc.uploaded_at }} | Size: {{ doc.size }}
                                {% if doc.created_by_blue %}
                                <span style="color: #667eea; font-weight: 600;"> • Created by Blue</span>
                                {% endif %}
                            </div>
                        </div>
                        <div style="display: flex; gap: 10px;">
                            <a href="/documents/download/{{ doc.filename }}" class="download-btn">
                                Download
                            </a>
                            <form method="POST" action="/documents/delete/{{ doc.filename }}" style="display: inline; margin: 0;">
                                <button type="submit" class="delete-btn" onclick="return confirm('Delete this document?')">
                                    Delete
                                </button>
                            </form>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="empty-state">
                        <div class="empty-state-icon">🔭</div>
                        <h3>No documents yet</h3>
                        <p>Upload your first document to get started!</p>
                    </div>
                {% endif %}
            </div>

            <a href="/" class="back-link">← Back to main page</a>
        </div>
    </div>

    <script>
        document.getElementById('fileInput').addEventListener('change', function(e) {
            const fileName = e.target.files[0] ? e.target.files[0].name : 'No file chosen';
            document.getElementById('fileName').textContent = fileName;
        });

        document.getElementById('uploadForm').addEventListener('submit', function() {
            document.getElementById('uploadBtn').disabled = true;
            document.getElementById('uploadBtn').textContent = 'Uploading...';
        });
    </script>
</body>
</html>
"""

@app.route('/documents', methods=['GET', 'POST'])


def manage_documents():
    """Web interface for document management."""
    message = None
    message_type = None

    if request.method == 'POST':
        if 'file' not in request.files:
            message = "No file provided"
            message_type = "error"
        else:
            file = request.files['file']

            if file.filename == '':
                message = "No file selected"
                message_type = "error"
            elif not allowed_file(file.filename):
                message = f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
                message_type = "error"
            else:
                try:
                    # Secure the filename
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                    # Save the file
                    file.save(filepath)

                    # Get file info
                    file_size = os.path.getsize(filepath)
                    file_hash = get_file_hash(filepath)

                    # Extract text preview
                    text_content = extract_text_from_file(filepath)
                    text_preview = text_content[:500] if not text_content.startswith("Error") else ""

                    # Add to RAG system
                    rag_success = add_document_to_rag(filepath, filename)

                    # Update index
                    index = load_document_index()

                    # Check for duplicates
                    duplicate = False
                    for doc in index['documents']:
                        if doc.get('hash') == file_hash:
                            duplicate = True
                            message = f"Document '{filename}' already exists (duplicate detected)"
                            message_type = "error"
                            os.remove(filepath)
                            break

                    if not duplicate:
                        index['documents'].append({
                            'filename': filename,
                            'filepath': str(filepath),
                            'size': file_size,
                            'hash': file_hash,
                            'uploaded_at': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'text_preview': text_preview,
                            'indexed_in_rag': rag_success
                        })
                        save_document_index(index)

                        message = f"✅ Successfully uploaded and indexed '{filename}'!"
                        message_type = "success"

                except Exception as e:
                    message = f"Error uploading file: {str(e)}"
                    message_type = "error"

    # Load documents for display
    index = load_document_index()
    documents = index.get('documents', [])

    # Calculate stats
    total_size_bytes = sum(doc.get('size', 0) for doc in documents)
    total_size = f"{total_size_bytes / 1024 / 1024:.1f} MB" if total_size_bytes > 0 else "0 MB"

    # Format document sizes
    for doc in documents:
        size_bytes = doc.get('size', 0)
        if size_bytes > 1024 * 1024:
            doc['size'] = f"{size_bytes / 1024 / 1024:.1f} MB"
        else:
            doc['size'] = f"{size_bytes / 1024:.1f} KB"

    return render_template_string(
        DOCUMENT_MANAGER_HTML,
        documents=documents,
        document_count=len(documents),
        total_size=total_size,
        message=message,
        message_type=message_type
    )


@app.route('/documents/delete/<filename>', methods=['POST'])


def delete_document(filename):
    """Delete a document."""
    try:
        index = load_document_index()
        documents = index.get('documents', [])

        # Find and remove document
        updated_documents = []
        deleted = False

        for doc in documents:
            if doc['filename'] == filename:
                # Delete file
                filepath = doc['filepath']
                if os.path.exists(filepath):
                    os.remove(filepath)
                deleted = True
            else:
                updated_documents.append(doc)

        if deleted:
            index['documents'] = updated_documents
            save_document_index(index)

        return redirect(url_for('manage_documents'))

    except Exception as e:
        print(f"Error deleting document: {e}")
        return redirect(url_for('manage_documents'))


@app.route('/documents/download/<filename>', methods=['GET'])


def download_document(filename):
    """Download a document."""
    try:
        from flask import send_file

        # Security: Make sure filename is safe
        filename = secure_filename(filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        if not os.path.exists(filepath):
            return "File not found", 404

        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"Error downloading document: {e}")
        return f"Error: {str(e)}", 500


# ===== Conversation Persistence Functions =====

def save_conversation_to_db(user_name: str, role: str, content: str,
                            session_id: str = None, tool_used: str = None):
    """Save a conversation message to the database for long-term memory"""
    if not CONVERSATION_DB_AVAILABLE or not db:
        return

    try:
        # Determine importance based on length and content
        importance = 5  # Default
        if len(content) > 500:
            importance = 7  # Longer messages are more important
        if any(keyword in content.lower() for keyword in ['remember', 'important', 'don\'t forget']):
            importance = 8  # User explicitly wants to remember

        db.save_conversation(
            user_name=user_name,
            role=role,
            content=content,
            session_id=session_id,
            tool_used=tool_used,
            importance=importance
        )
        log.debug(f"Saved {role} message to database (importance: {importance})")
    except Exception as e:
        log.warning(f"Failed to save conversation: {e}")


def load_recent_context(user_name: str = "Alex", limit: int = 10):
    """Load recent conversations from database for context"""
    if not CONVERSATION_DB_AVAILABLE or not db:
        return []

    try:
        conversations = db.get_recent_conversations(user_name=user_name, limit=limit)

        # Format for LLM context
        context_messages = []
        for conv in conversations:
            context_messages.append({
                "role": conv.get("role", "user"),
                "content": conv.get("content", "")
            })

        log.debug(f"Loaded {len(context_messages)} messages from database history")
        return context_messages
    except Exception as e:
        log.warning(f"Failed to load conversation context: {e}")
        return []


def extract_ocf_facts(messages: list) -> str:
    """Extract key facts from .ocf conversations for permanent memory."""
    if not messages:
        return ""

    facts = {'identity': [], 'family': [], 'capabilities': [], 'location': []}

    for msg in messages:
        if msg.get('role') not in ['user', 'assistant']:
            continue
        content = msg.get('content', '')
        content_lower = content.lower()
        if len(content) < 20 or content.startswith('{'):
            continue

        if any(term in content_lower for term in ['your name is blue', 'you are blue', 'created by', 'you are our family robot', 'what makes you different']):
            if content not in facts['identity'] and len(facts['identity']) < 3:
                facts['identity'].append(content[:300])
        elif any(term in content_lower for term in ['alex is', 'stella is', 'our family', 'your daughters', 'extended family', 'daughters are', 'family includes', 'felix', 'felix and svetlana']):
            if content not in facts['family'] and len(facts['family']) < 5:
                facts['family'].append(content[:500])
        elif any(term in content_lower for term in ['your tools', 'you can control', 'you have access to', 'tell me about your origin']):
            if content not in facts['capabilities'] and len(facts['capabilities']) < 2:
                facts['capabilities'].append(content[:300])
        elif any(term in content_lower for term in ['live on mansion', 'live in kitchener', 'waterloo', 'mansion st']):
            if content not in facts['location'] and len(facts['location']) < 2:
                facts['location'].append(content[:200])

    fact_parts = []
    if facts['identity']:
        identity = max(facts['identity'], key=len)
        fact_parts.append(f"IDENTITY: {identity.strip()}")
    if facts['family']:
        family_info = " | ".join(facts['family'])
        fact_parts.append(f"FAMILY: {family_info.strip()}")
    if facts['capabilities']:
        capabilities = facts['capabilities'][0]
        fact_parts.append(f"CAPABILITIES: {capabilities.strip()}")
    if facts['location']:
        location = facts['location'][0]
        fact_parts.append(f"LOCATION: {location.strip()}")

    if not fact_parts:
        return ""

    return "\n\n=== LONG-TERM MEMORY (from .ocf) ===\n" + "\n\n".join(fact_parts)


def should_include_history(messages) -> bool:
    """Determine if we should inject historical context"""
    # Don't inject if already have a lot of context
    if len(messages) > 10:
        return False

    # Inject if this is a new conversation (only 1-2 messages)
    if len(messages) <= 2:
        return True

    # Check if user is asking about past conversations
    if messages:
        last_msg = messages[-1].get('content', '').lower()
        past_indicators = [
            'remember', 'recall', 'what did', 'we discussed', 'talked about',
            'mentioned', 'said before', 'last time', 'previously', 'earlier'
        ]
        if any(indicator in last_msg for indicator in past_indicators):
            return True

    return False


# ===== MAIN API ENDPOINTS =====

@app.route('/v1/chat/completions', methods=['POST'])


def chat_completions():
    """Main endpoint with conversation persistence"""
    try:
        data = request.json
        messages = data.get("messages", [])

        print(f"")
        print(f"{'='*60}")
        print(f"[MSG] Received request from Ohbot")

        # Extract user name from messages if available (default to Alex)
        user_name = "Alex"

        # Find the last actual USER message
        user_messages = [m for m in messages if m.get('role') == 'user']
        if user_messages:
            last_user_msg = user_messages[-1].get('content', '')

            # If it's too long (probably includes system prompt), show shorter version
            if len(last_user_msg) > 200:
                if "You are Blue" in last_user_msg:
                    if len(user_messages) > 1:
                        last_user_msg = user_messages[-2].get('content', last_user_msg)

            print(f"   [SPEAK]  User asked: {last_user_msg[:150]}..." if len(last_user_msg) > 150 else f"   [SPEAK]  User asked: {last_user_msg}")

            # SAVE USER MESSAGE TO DATABASE
            save_conversation_to_db(
                user_name=user_name,
                role="user",
                content=last_user_msg,
                session_id=None
            )

        # INJECT HISTORICAL CONTEXT IF NEEDED (IMPROVED)
        if CONVERSATION_DB_AVAILABLE:
            # Use enhanced memory system if available
            if ENHANCED_MEMORY_AVAILABLE and memory_system:
                should_inject = memory_system.should_inject_context(messages)
                if should_inject:
                    historical_context = memory_system.build_context(messages, user_name=user_name)
                    if historical_context:
                        print(f"   [MEMORY] ✓ Injecting {len(historical_context)} messages (semantic + recent)")
                        messages = messages[:-1] + historical_context + [messages[-1]]
            # Fallback to legacy system
            elif should_include_history(messages):
                historical_context = load_recent_context(user_name=user_name, limit=6)
                if historical_context:
                    print(f"   [MEMORY] Injecting {len(historical_context)} messages from history")
                    messages = messages[:-1] + historical_context[-6:] + [messages[-1]]

        # INJECT SYSTEM MESSAGE WITH FACTS (ALWAYS FRESH)
        # Load fresh facts from database (critical for memory persistence!)
        fresh_facts = load_blue_facts()  # ← This is the key fix!
        
        if fresh_facts:
            fact_summary = []
            for key, value in fresh_facts.items():
                fact_summary.append(f"{key.replace('_', ' ').title()}: {value}")
            
            if fact_summary:
                memory_text = "\\n".join(fact_summary[:20])  # Increased from 15 to 20
                system_with_memory = build_system_preamble() + f"\\n\\n<known_facts>\\n{memory_text}\\n</known_facts>"
                
                # Insert system message at the beginning
                messages.insert(0, {"role": "system", "content": system_with_memory})
                log.info(f"[MEM] ✓ Injected {len(fact_summary)} FRESH facts into system message")

        # Process with tools
        response = process_with_tools(messages)

        # SAVE ASSISTANT RESPONSE TO DATABASE
        if response:
            final_content = response["choices"][0]["message"].get("content", "")
            if final_content:
                print(f"[OUT] Sending response: {final_content[:100]}..." if len(final_content) > 100 else f"[OUT] Sending response: {final_content}")

                save_conversation_to_db(
                    user_name=user_name,
                    role="assistant",
                    content=final_content,
                    session_id=None
                )
                
                # AUTO-SAVE LEARNED FACTS & CONSOLIDATE
                try:
                    # Add assistant response to messages for fact extraction
                    full_conversation = messages + [{"role": "assistant", "content": final_content}]
                    if extract_and_save_facts(full_conversation):
                        log.info("[MEM] ✓ Auto-saved learned facts")
                    
                    # Run memory consolidation if needed
                    if ENHANCED_MEMORY_AVAILABLE and memory_system:
                        memory_system.consolidate_if_needed(user_name=user_name)
                        
                except Exception as e:
                    log.warning(f"[MEM] Auto-save failed: {e}")

        return jsonify(response)
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"choices": [{"message": {"role": "assistant", "content": f"Error: {str(e)}"}}]}), 500


# ===== Memory Management Endpoints =====

@app.route('/memory/stats', methods=['GET'])


def memory_stats():
    """Get statistics about stored conversations"""
    if not CONVERSATION_DB_AVAILABLE or not db:
        return jsonify({"error": "Database not available"}), 503

    try:
        stats = db.get_database_stats()

        return jsonify({
            "status": "success",
            "total_conversations": stats.get('conversations', 0),
            "total_memories": stats.get('memories', 0),
            "db_size_mb": stats.get('db_size_mb', 0),
            "message": "Long-term memory is active"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/memory/recent', methods=['GET'])


def get_recent_memory():
    """Get recent conversation history"""
    if not CONVERSATION_DB_AVAILABLE or not db:
        return jsonify({"error": "Database not available"}), 503

    user_name = request.args.get('user', 'Alex')
    limit = int(request.args.get('limit', 20))

    try:
        conversations = db.get_recent_conversations(user_name=user_name, limit=limit)

        return jsonify({
            "status": "success",
            "user": user_name,
            "count": len(conversations),
            "conversations": [
                {
                    "role": c.get("role"),
                    "content": c.get("content")[:200],  # First 200 chars
                    "timestamp": c.get("timestamp"),
                    "importance": c.get("importance")
                }
                for c in conversations
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/memory/summary', methods=['GET'])
def memory_summary():
    """Get comprehensive memory summary with enhanced details."""
    if ENHANCED_MEMORY_AVAILABLE and memory_system:
        try:
            summary = memory_system.get_memory_summary()
            return jsonify({
                "status": "success",
                "enhanced": True,
                "summary": summary,
                "message": "Using enhanced memory system"
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        # Fallback to basic stats
        if not CONVERSATION_DB_AVAILABLE or not db:
            return jsonify({"error": "Database not available"}), 503
        
        try:
            stats = db.get_database_stats()
            facts = load_blue_facts()
            
            return jsonify({
                "status": "success",
                "enhanced": False,
                "summary": {
                    "facts_count": len(facts),
                    "conversations_stored": stats.get('conversations', 0),
                    "database_size_mb": stats.get('db_size_mb', 0)
                },
                "message": "Using legacy memory system"
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])


def health():
    """Enhanced health check with comprehensive system status."""
    import time
    
    # Core services
    hue_status = "configured" if BRIDGE_IP and HUE_USERNAME else "not configured"
    index = load_document_index()
    doc_count = len(index.get('documents', []))
    music_status = "ready" if YOUTUBE_MUSIC_BROWSER else "not initialized"
    visualizer_status = "active" if _visualizer_active else "inactive"
    
    # LLM status
    llm_status = "unknown"
    llm_model = "unknown"
    if _LM:
        try:
            if _LM.is_healthy():
                llm_status = "healthy"
                llm_model = _LM.model
            else:
                llm_status = "unreachable"
        except Exception:
            llm_status = "error"
    
    # Gmail status
    gmail_status = "not configured"
    if GMAIL_AVAILABLE:
        try:
            service = get_gmail_service()
            if service:
                gmail_status = "configured"
        except Exception:
            gmail_status = "auth error"
    
    # Memory stats
    fact_count = len(BLUE_FACTS) if BLUE_FACTS else 0
    
    # Search stats
    search_remaining = SEARCH_MAX_PER_MINUTE - len(_SEARCH_TIMESTAMPS) if _SEARCH_TIMESTAMPS else SEARCH_MAX_PER_MINUTE
    cache_size = len(_SEARCH_CACHE)
    
    # Mood count
    mood_count = len(MOOD_PRESETS)

    return jsonify({
        "status": "healthy",
        "version": "v8-enhanced",
        "service": "Blue Robot Middleware",
        "uptime_note": "Flask app running",
        "components": {
            "llm": {
                "status": llm_status,
                "model": llm_model,
                "endpoint": _LM.base_url if _LM else None
            },
            "hue": {
                "status": hue_status,
                "bridge_ip": BRIDGE_IP if BRIDGE_IP else None,
                "mood_presets": mood_count
            },
            "gmail": {
                "status": gmail_status
            },
            "music": {
                "status": music_status,
                "visualizer": visualizer_status
            },
            "documents": {
                "count": doc_count,
                "folder": str(DOCUMENTS_FOLDER)
            },
            "memory": {
                "facts_stored": fact_count
            },
            "search": {
                "remaining_this_minute": search_remaining,
                "cache_entries": cache_size
            }
        }
    })


@app.route('/stats', methods=['GET'])
def session_stats():
    """v8: Get session statistics for debugging and optimization."""
    state = get_conversation_state()
    stats = state.get_session_stats()
    
    # Add additional stats
    stats['response_cache_size'] = len(_response_cache)
    stats['current_topic'] = state.get_current_topic()
    stats['last_tool'] = state.last_tool_used
    stats['common_tool_pairs'] = state.get_common_tool_pairs()
    stats['corrections_count'] = len(state.user_corrections)
    
    # Suggest next action if available
    suggestion = state.suggest_next_action()
    if suggestion:
        stats['suggestion'] = suggestion
    
    return jsonify(stats)


@app.route('/')


def index():
    """Home page with links."""
    index_data = load_document_index()
    doc_count = len(index_data.get('documents', []))
    music_status = "✅ Ready" if YOUTUBE_MUSIC_BROWSER else "⚠️ Not initialized"
    visualizer_status = "🎨 Active" if _visualizer_active else "⚪ Inactive"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Blue Middleware - Music + Light Sync [FIXED]</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                margin: 0;
                padding: 20px;
            }}
            .card {{
                background: white;
                border-radius: 20px;
                padding: 50px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
                max-width: 600px;
            }}
            h1 {{
                color: #667eea;
                font-size: 2.5em;
                margin-bottom: 10px;
            }}
            .subtitle {{
                color: #666;
                font-size: 1.2em;
                margin-bottom: 40px;
            }}
            .status {{
                background: #f8f9fa;
                border-radius: 15px;
                padding: 30px;
                margin-bottom: 30px;
            }}
            .status-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                padding: 15px;
                background: white;
                border-radius: 10px;
            }}
            .status-label {{
                font-weight: 600;
                color: #333;
            }}
            .status-value {{
                color: #667eea;
                font-weight: 600;
            }}
            .btn {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                padding: 20px 40px;
                border-radius: 50px;
                font-size: 1.2em;
                font-weight: 600;
                transition: transform 0.2s;
                margin: 10px;
            }}
            .btn:hover {{
                transform: scale(1.05);
            }}
            .feature-highlight {{
                background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                color: white;
                padding: 20px;
                border-radius: 15px;
                margin-bottom: 30px;
                font-weight: 600;
            }}
            .fix-badge {{
                background: #ff4757;
                color: white;
                padding: 10px 20px;
                border-radius: 25px;
                display: inline-block;
                margin-bottom: 20px;
                font-weight: 700;
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0%, 100% {{ transform: scale(1); }}
                50% {{ transform: scale(1.05); }}
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="fix-badge">🔧 FIXED: Music Controls Now Work!</div>
            <h1>🎵💡 Blue Middleware</h1>
            <p class="subtitle">Your AI assistant with music-light sync!</p>

            <div class="feature-highlight">
                ✨ NEW: Music controls work from ANY window!<br>
                🎵 Uses system-wide media keys<br>
                💡 Lights automatically sync with music!<br>
                🎨 Dynamic light visualizer!
            </div>

            <div class="status">
                <div class="status-item">
                    <span class="status-label">Service</span>
                    <span class="status-value">✅ Running</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Music Controls</span>
                    <span class="status-value">✅ FIXED - Works from any window!</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Music</span>
                    <span class="status-value">{music_status}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Visualizer</span>
                    <span class="status-value">{visualizer_status}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Hue Lights</span>
                    <span class="status-value">{'✅ Connected' if BRIDGE_IP else '⚠️ Not configured'}</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Documents</span>
                    <span class="status-value">{doc_count} indexed</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Moods Available</span>
                    <span class="status-value">{len(MOOD_PRESETS)}</span>
                </div>
            </div>

            <a href="/documents" class="btn">📚 Manage Documents</a>
        </div>
    </body>
    </html>
    """
    return html


if __name__ == "__main__":
    print("=" * 60)
    print("🎵💡 Blue Robot Middleware - WITH MUSIC-LIGHT SYNC!")
    print("🔧 FIXED: Music controls now work from ANY window!")
    print("=" * 60)
    print(f"[NET] Listening on: http://127.0.0.1:{PROXY_PORT}")
    print(f"[TARGET] Forwarding to LM Studio: {LM_STUDIO_URL}")
    print(f"[DOC] RAG endpoint: {LM_STUDIO_RAG_URL}")
    print(f"[TOOL] Tools: {len(TOOLS)}")
    print("   • play_music (YouTube Music & Amazon Music) 🎵")
    print("     → AUTOMATICALLY syncs lights to match music vibe! 💡")
    print("   • control_music (pause, skip, volume) 🎵")
    print("     → FIXED: Now uses system-wide media keys!")
    print("     → Works from ANY window - no need to focus YouTube Music!")
    print("   • music_visualizer (dynamic light shows!) 🎨")
    print("   • control_lights (with 15 moods!) 💡")
    print("   • search_documents (RAG-powered) 📄")
    print("   • get_weather ⛅")
    print("   • web_search 🔍")
    print("   • run_javascript 💻")
    print("   • create_document (save files) 📝")
    print("   • browse_website (fetch URLs) 🌐")
    print("   • read_gmail (check emails) 📧")
    print("   • send_gmail (send emails) 📧")
    print("=" * 60)

    # Try to initialize YouTube Music
    if init_youtube_music():
        print("\n🎵 YouTube Music Status: ✅ Ready!")
        print("   Note: Music controls use system media keys (no pyautogui needed)")
    else:
        print("\n🎵 YouTube Music Status: ⚠️ Not available")
        print("   To enable music: pip install ytmusicapi")

    if BRIDGE_IP and HUE_USERNAME:
        print(f"\n💡 Hue configured: Bridge at {BRIDGE_IP}")
        lights = get_hue_lights()
        if lights:
            print(f"✅ Found {len(lights)} light(s)")
    else:
        print("\n⚠️ Hue not configured. Run setup_hue.py!")

    # Check document status
    index = load_document_index()
    doc_count = len(index.get('documents', []))
    print(f"\n📄 Document Manager:")
    print(f"   • {doc_count} document(s) indexed")
    print(f"   • Web interface: http://127.0.0.1:{PROXY_PORT}/documents")
    print(f"   • Storage: {UPLOAD_FOLDER}/")

    # Check Gmail status
    if globals().get("GMAIL_AVAILABLE", False):

        print(f"\n📧 Gmail Integration:")
        print(f"   • Account: {GMAIL_USER_EMAIL}")
        if os.path.exists(GMAIL_TOKEN_FILE):
            print(f"   • Status: ✅ Authenticated")
        else:
            print(f"   • Status: ⚠️ Not authenticated yet")
            print(f"   • Run bluetools.py and use Gmail commands to authenticate")
    else:
        print(f"\n⚠️ Gmail not available. Install with:")
        print(f"   pip install google-auth google-auth-oauthlib google-api-python-client")

    print("\n✨ Example commands:")
    print("   🎵 'Play Bohemian Rhapsody by Queen' (lights auto-sync!)")
    print("   🎵 'Play some relaxing jazz music' (sets moonlight mood)")
    print("   🎵 'Play party music' (bright colorful lights!)")
    print("   🎵 'Pause the music' - NOW WORKS FROM OHBOT APP! ✅")
    print("   🎵 'Skip to next song' - Works from any window! ✅")
    print("   🎨 'Start a light show' / 'lights dance with music'")
    print("   💡 'Set the lights to sunset mood'")
    print("   📄 'What does my contract say about termination?'")
    print("   🔍 'Search for information about AI'")
    print("   📝 'Create a shopping list document for me'")
    print("   🌐 'Browse https://example.com and summarize it'")
    print("   📧 'Check my email' / 'Read my recent emails'")
    print("   📧 'Send an email to john@example.com about the meeting'")

    print("\n⭐ Music-Light Sync Features:")
    print("   • Auto mood detection: Jazz → moonlight, Party → colorful")
    print("   • Romantic music → soft romance lighting")
    print("   • Workout music → energizing bright whites")
    print("   • Dynamic visualizer with party/chill/pulse modes")
    print("   • Background thread for continuous light shows")

    print("\n🔧 FIX DETAILS:")
    print("   • Changed from application-specific shortcuts to system media keys")
    print("   • Uses pyautogui.press('playpause'), 'nexttrack', 'prevtrack'")
    print("   • These keys work globally regardless of window focus")
    print("   • No longer requires YouTube Music window to be active!")
    print("   • You can control music while using Ohbot app! ✅\n")


# --- Image Upload Endpoints ---
@app.route("/upload", methods=["GET", "POST"])


def upload_page():
    # If POST, handle files directly and then redirect to /documents (if present) or return a simple page.
    if request.method == "POST":
        if "file" not in request.files and "files" not in request.files:
            return Response("No file part in the request.", status=400)
        files = request.files.getlist("file") or request.files.getlist("files")
        saved = []
        for f in files:
            if not f or f.filename == "":
                continue
            if not allowed_file(f.filename):
                continue
            target_path = ensure_unique_path(UPLOAD_FOLDER, f.filename)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            f.save(target_path)
            saved.append(os.path.basename(target_path))
        if not saved:
            return Response("No valid image files were uploaded.", status=400)
        # Prefer redirect to a document manager if available
        try:
            return redirect(url_for("documents"))
        except Exception:
            # Fallback simple success page
            body = "<h3>Uploaded:</h3><ul>" + "".join(f"<li>{x}</li>" for x in saved) + "</ul>"
            return Response(body, mimetype="text/html")

    # GET -> simple HTML upload form
    html = """
<!doctype html>
<title>Upload Images</title>
<h2>Upload images to Blue's uploads folder</h2>
<form method="post" enctype="multipart/form-data">
  <input type="file" name="file" multiple accept="image/*">
  <button type="submit">Upload</button>
</form>
<p>Files will be saved under: <code>{folder}</code></p>
""".format(folder=UPLOAD_FOLDER)
    return Response(html, mimetype="text/html")


@app.route("/api/upload", methods=["POST"])


def api_upload():
    if "file" not in request.files and "files" not in request.files:
        return jsonify({"error": "No file(s) in request. Use 'file' or 'files' field."}), 400
    files = request.files.getlist("file") or request.files.getlist("files")
    saved = []
    rejected = []
    for f in files:
        if not f or f.filename == "":
            rejected.append({"filename": "", "reason": "empty filename"})
            continue
        if not allowed_file(f.filename):
            rejected.append({"filename": f.filename, "reason": "unsupported extension"})
            continue
        target_path = ensure_unique_path(UPLOAD_FOLDER, f.filename)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        f.save(target_path)
        saved.append({"filename": os.path.basename(target_path), "path": target_path})
    return jsonify({"saved": saved, "rejected": rejected, "upload_folder": UPLOAD_FOLDER})


# --- Document Upload Endpoints (images + texts, saved into uploaded_documents) ---
@app.route("/documents/upload", methods=["GET", "POST"])


def documents_upload():
    if request.method == "POST":
        if "file" not in request.files and "files" not in request.files:
            return Response("No file part in the request.", status=400)
        files = request.files.getlist("file") or request.files.getlist("files")
        saved = []
        for f in files:
            if not f or f.filename == "":
                continue
            if not allowed_file(f.filename):
                continue
            path = ensure_unique_path(DOCUMENTS_FOLDER, f.filename)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            f.save(path)
            saved.append(os.path.basename(path))
        if not saved:
            return Response("No valid files were uploaded.", status=400)
        try:
            return redirect(url_for("documents"))
        except Exception:
            body = "<h3>Uploaded:</h3><ul>" + "".join(f"<li>{x}</li>" for x in saved) + "</ul>"
            return Response(body, mimetype="text/html")

    # GET -> HTML form
    html = f"""
<!doctype html>
<title>Upload Documents</title>
<h2>Upload documents/images</h2>
<form method="post" enctype="multipart/form-data">
  <input type="file" name="file" multiple>
  <button type="submit">Upload</button>
</form>
<p>Saved under: <code>{DOCUMENTS_FOLDER}</code></p>
<p>Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}</p>
"""
    return Response(html, mimetype="text/html")


@app.route("/api/documents/upload", methods=["POST"])


def api_documents_upload():
    if "file" not in request.files and "files" not in request.files:
        return jsonify({"error": "No file(s) in request. Use 'file' or 'files' field."}), 400
    files = request.files.getlist("file") or request.files.getlist("files")
    saved, rejected = [], []
    for f in files:
        if not f or f.filename == "":
            rejected.append({"filename": "", "reason": "empty filename"})
            continue
        if not allowed_file(f.filename):
            rejected.append({"filename": f.filename, "reason": "unsupported extension"})
            continue
        path = ensure_unique_path(DOCUMENTS_FOLDER, f.filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        f.save(path)
        saved.append({"filename": os.path.basename(path), "path": path})
    return jsonify({"saved": saved, "rejected": rejected, "documents_folder": DOCUMENTS_FOLDER})


@app.route("/documents/file/<path:filename>")
def serve_document_file(filename):
    return send_from_directory(DOCUMENTS_FOLDER, filename, as_attachment=False)


# ===== Facebook OAuth Callback =====
@app.route("/facebook/callback")
def facebook_callback():
    """Handle Facebook OAuth callback"""
    code = request.args.get('code')
    error = request.args.get('error')

    if error:
        return f"""
        <html>
        <head><title>Facebook Authentication Failed</title></head>
        <body style="font-family: Arial, sans-serif; padding: 40px;">
            <h1 style="color: #e74c3c;">Authentication Failed</h1>
            <p>Error: {error}</p>
            <p>Description: {request.args.get('error_description', 'Unknown error')}</p>
            <p><a href="/">Return to Home</a></p>
        </body>
        </html>
        """

    if not code:
        return """
        <html>
        <head><title>Facebook Authentication</title></head>
        <body style="font-family: Arial, sans-serif; padding: 40px;">
            <h1 style="color: #f39c12;">Missing Authorization Code</h1>
            <p>No authorization code received from Facebook.</p>
            <p><a href="/">Return to Home</a></p>
        </body>
        </html>
        """

    try:
        from blue.tools import get_facebook_integration
        integration = get_facebook_integration()
        result = integration.complete_authentication(code)

        if result.get('status') == 'success':
            user_info = result.get('user', {})
            pages = result.get('pages', [])

            pages_html = ""
            if pages:
                pages_html = "<h3>Connected Pages:</h3><ul>"
                for page in pages:
                    pages_html += f"<li>{page.get('name')} (ID: {page.get('id')})</li>"
                pages_html += "</ul>"

            return f"""
            <html>
            <head><title>Facebook Connected</title></head>
            <body style="font-family: Arial, sans-serif; padding: 40px;">
                <h1 style="color: #27ae60;">✓ Successfully Connected to Facebook</h1>
                <p>Authenticated as: <strong>{user_info.get('name')}</strong></p>
                <p>Email: {user_info.get('email')}</p>
                {pages_html}
                <p style="margin-top: 20px;">You can now use Blue to post to Facebook!</p>
                <p><a href="/">Return to Home</a></p>
            </body>
            </html>
            """
        else:
            error_msg = result.get('error', 'Unknown error')
            return f"""
            <html>
            <head><title>Authentication Error</title></head>
            <body style="font-family: Arial, sans-serif; padding: 40px;">
                <h1 style="color: #e74c3c;">Authentication Error</h1>
                <p>Error: {error_msg}</p>
                <p><a href="/">Return to Home</a></p>
            </body>
            </html>
            """

    except Exception as e:
        return f"""
        <html>
        <head><title>Error</title></head>
        <body style="font-family: Arial, sans-serif; padding: 40px;">
            <h1 style="color: #e74c3c;">Unexpected Error</h1>
            <p>Error: {str(e)}</p>
            <p><a href="/">Return to Home</a></p>
        </body>
        </html>
        """


app.run(host='127.0.0.1', port=PROXY_PORT, debug=False)

# ===== Tool Executor with timeouts, retries, and small cache =====
class ToolExecutor:
    def __init__(self, settings: Settings):
        self.settings = settings

    @lru_cache(maxsize=128)
    def _cached_call(self, tool_name: str, args_key: str) -> str:
        args = json.loads(args_key)
        return self._raw_call(tool_name, args)

    def _raw_call(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        try:
            return execute_tool(tool_name, tool_args)
        except Exception as e:
            log.exception("Tool '%s' crashed: %s", tool_name, e)
            return json.dumps({"error": str(e), "tool": tool_name})

    def execute(self, tool_name: str, tool_args: Dict[str, Any], use_cache: bool = False) -> str:
        tries = max(1, int(self.settings.TOOL_RETRIES) + 1)
        last_err = None
        for attempt in range(1, tries + 1):
            try:
                if use_cache:
                    args_key = json.dumps(tool_args, sort_keys=True)[:2048]
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        fut = pool.submit(self._cached_call, tool_name, args_key)
                        return fut.result(timeout=self.settings.TOOL_TIMEOUT_SECS)
                else:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        fut = pool.submit(self._raw_call, tool_name, tool_args)
                        return fut.result(timeout=self.settings.TOOL_TIMEOUT_SECS)
            except concurrent.futures.TimeoutError:
                last_err = f"timeout after {self.settings.TOOL_TIMEOUT_SECS}s"
                log.warning("Tool '%s' timed out (attempt %d/%d)", tool_name, attempt, tries)
            except Exception as e:
                last_err = str(e)
                log.warning("Tool '%s' failed (attempt %d/%d): %s", tool_name, attempt, tries, e)
            time.sleep(0.2 * attempt)
        return json.dumps({"error": last_err or "unknown", "tool": tool_name, "attempts": tries})

# ===== Ephemeral Session State =====
SESSION_STATE: Dict[str, Any] = {}


def session_get(key: str, default=None):
    return SESSION_STATE.get(key, default)


def session_set(key: str, value: Any) -> None:
    SESSION_STATE[key] = value

def clear_gmail_context():
    """
    Clear email-related session state to prevent confusion between operations.
    Call this after completing email operations to ensure old results don't interfere.
    ADDED: October 2024 - Fix for Blue confusing READ with REPLY operations
    """
    SESSION_STATE.pop('last_gmail_operation', None)
    SESSION_STATE.pop('last_gmail_result', None)
    SESSION_STATE.pop('last_gmail_query', None)
    log.info("Cleared Gmail session context to prevent operation confusion")


# ================== BEGIN: Browse Website Tool + PRIORITY-EXPLICIT (with browse) ==================
"""
Adds a safe 'browse_website' tool and updates the middleware to understand and prioritize it.
- Explicit commands ALWAYS win.
- Smart auto-use (optional) may trigger for obvious "open/read this URL" cases.
- Web search cannot override an explicit browse request.
- Safe fetch: http/https only; timeouts; size limits; basic HTML->text extraction; link harvesting.

USAGE examples:
  use browse_website: {"url":"https://example.com"}
  /browse_website https://example.com
  use browse: https://example.com
"""

from typing import List, Dict, Optional, Tuple, Any
import re as _re, json as _json, html as _html, urllib.parse as _urlparse
import requests

# ---- Ensure TOOLS contains browse_website schema ----
try:
    TOOLS
except NameError:
    TOOLS = []

def _has_tool_named(name: str) -> bool:
    try:
        for t in TOOLS:
            fn = t.get("function",{})
            if fn.get("name") == name:
                return True
    except Exception:
        pass
    return False

_BROWSE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "browse_website",
        "description": "Fetch a web page over HTTPS and return cleaned text, title, and links. For direct browsing of a specific URL.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type":"string", "description":"The absolute URL to fetch (http or https)."},
                "extract": {"type":"string", "enum":["text","html"], "description":"Return cleaned text or raw HTML (default text)."},
                "max_chars": {"type":"integer", "description":"Max length of text to return (default 8000)."},
                "include_links": {"type":"boolean", "description":"Include a compact list of outgoing links (default true)."},
                "headers": {"type":"object", "description":"Optional request headers to include."}
            },
            "required": ["url"]
        }
    }
}

if not _has_tool_named("browse_website"):
    try:
        TOOLS.append(_BROWSE_SCHEMA)
        print("[TOD] Registered tool: browse_website", flush=True)
    except Exception as e:
        print(f"[TOD] Could not register browse_website: {e}", flush=True)

# ---- DUPLICATE CODE REMOVED ----
# The browse_website implementation has been moved to before execute_tool (around line 1600)
# to fix the NameError: name '_execute_browse_website' is not defined
# Keeping only the TOOLS registration above and the alias/scoring below.

# ---- Hook into execute_tool without breaking existing tools ----
# REMOVED: Duplicate execute_tool override - browse_website is now handled in main execute_tool

# ---- Extend existing middleware alias+scoring with browse ----
try:
    KNOWN_TOOL_ALIASES
except NameError:
    KNOWN_TOOL_ALIASES = {}
KNOWN_TOOL_ALIASES.setdefault("browse_website", [])
for alias in ["browse","open_url","open website","visit","go to","navigate","read url"]:
    if alias not in KNOWN_TOOL_ALIASES["browse_website"]:
        KNOWN_TOOL_ALIASES["browse_website"].append(alias)

_URL_IN_TEXT = _re.compile(r'https?://\S+', _re.I)


def _score_browse(text: str) -> float:
    t = (text or "").strip().lower()
    if _URL_IN_TEXT.search(t): return 0.98
    cues = ["open ", "go to ", "navigate to ", "read this page", "summarize this page", "visit "]
    if any(c in t for c in cues): return 0.85
    return 0.0

try:
    _SCORERS
    _SCORERS["browse_website"] = _score_browse
except NameError:
    _SCORERS = {"browse_website": _score_browse}

# ---- Add Gmail tool aliases ----
KNOWN_TOOL_ALIASES.setdefault("read_gmail", [])
for alias in ["check email", "read email", "show email", "get email", "inbox", "my emails", "check messages", "read messages"]:
    if alias not in KNOWN_TOOL_ALIASES["read_gmail"]:
        KNOWN_TOOL_ALIASES["read_gmail"].append(alias)

KNOWN_TOOL_ALIASES.setdefault("send_gmail", [])
for alias in ["send email", "email to", "compose email", "write email", "send message", "email"]:
    if alias not in KNOWN_TOOL_ALIASES["send_gmail"]:
        KNOWN_TOOL_ALIASES["send_gmail"].append(alias)

def _score_read_gmail(text: str) -> float:
    t = (text or "").strip().lower()
    gmail_read_terms = ["check email", "read email", "show email", "my inbox", "unread", "new messages", "email from"]
    if any(term in t for term in gmail_read_terms): return 0.95
    if "email" in t and any(word in t for word in ["check", "read", "show", "get", "see"]): return 0.85
    return 0.0

def _score_send_gmail(text: str) -> float:
    t = (text or "").strip().lower()
    if "send email" in t or "email to" in t: return 0.95
    if "send" in t and "email" in t: return 0.85
    if "compose" in t and "email" in t: return 0.85
    return 0.0

_SCORERS["read_gmail"] = _score_read_gmail
_SCORERS["send_gmail"] = _score_send_gmail

print("[TOD] Browse tool ready", flush=True)
print("[TOD] Gmail tools ready", flush=True)
# ================== END: Browse Website Tool + PRIORITY-EXPLICIT (with browse) ==================


# ================================================================================
#                           BLUETOOLS GMAIL UPGRADES                          #
#                    (Appended October 2025 — safe block)                    #
# ================================================================================

# Per-tool context limits to prevent cross-tool bleed in email operations
try:
    PER_TOOL_CONTEXT_LIMITS  # type: ignore
except NameError:
    PER_TOOL_CONTEXT_LIMITS = {
        "read_gmail": 6,
        "send_gmail": 6,
        "reply_gmail": 6,
    }

def get_context_limit_for(tool_name: str, default_limit: int = 20) -> int:
    try:
        return int(PER_TOOL_CONTEXT_LIMITS.get(tool_name, default_limit))
    except Exception:
        return default_limit

# NOTE: detect_gmail_operation_intent, extract_email_address, extract_email_subject_and_body
# are defined earlier in the file (around line 7116) to ensure they're available when needed.

# Operation receipt


def _record_gmail_operation(op_type: str, query: str = "", extra: dict | None = None):
    import time as _t, json as _json
    meta = {"tool": op_type, "query": query or "", "ts": _t.time()}
    if extra and isinstance(extra, dict):
        meta.update(extra)
    try:
        print("[GMAIL-META] " + _json.dumps(meta))
    except Exception:
        pass
    return meta

# NOTE: To wire these into your existing flow:
#  - Before invoking the model/tool for Gmail, call detect_gmail_operation_intent(last_user_text)
#    and route strictly to 'read_gmail' / 'send_gmail' / 'reply_gmail' if returned.
#  - When building the context for that tool call, cap messages using get_context_limit_for(tool, default_limit).
#  - In your Gmail tool implementations, call _record_gmail_operation(...) after success.
#  - Use extract_email_subject_and_body() in your send path to infer subject/body from natural phrasing.
# ================================================================================


# ================================================================================
#                    VOICE EMAIL INTERFACE (CONSOLIDATED)                     #
#             AddressBook + NLU + Controller + Lazy Wiring Helpers            #
#                    Appended: 1761490066                                        #
# ================================================================================
import re, os, json, difflib, time, typing, dataclasses
from dataclasses import dataclass

@dataclass
class _Contact:
    name: str
    email: str
    aliases: list[str] | None = None
    def all_names(self) -> list[str]:
        names = [self.name]
        if self.aliases: names.extend(self.aliases)
        return [_normalize_text(n) for n in names if n]

def _normalize_text(s: str) -> str:
    s = s or ""
    s = s.strip().lower()
    s = _re.sub(r"[^a-z0-9@.\s+-]", "", s)
    s = _re.sub(r"\s+", " ", s)
    return s

class AddressBook:
    def __init__(self, path: str):
        self.path = path
        self.contacts: list[_Contact] = []
        if _os.path.exists(path): self._load()
        else: self._save()
    def add_or_update(self, name: str, email: str, aliases: list[str] | None = None) -> _Contact:
        name_n = _normalize_text(name)
        for c in self.contacts:
            if _normalize_text(c.name) == name_n or _normalize_text(c.email) == _normalize_text(email):
                c.name = name; c.email = email; c.aliases = aliases or c.aliases; self._save(); return c
        c = _Contact(name=name, email=email, aliases=aliases or [])
        self.contacts.append(c); self._save(); return c
    def remove(self, name_or_email: str) -> bool:
        key = _normalize_text(name_or_email); before = len(self.contacts)
        self.contacts = [c for c in self.contacts if _normalize_text(c.name)!=key and _normalize_text(c.email)!=key]
        if len(self.contacts)!=before: self._save(); return True
        return False
    def find_best(self, query: str) -> tuple[_Contact | None, float, list[_Contact]]:
        q = _normalize_text(query)
        if not q: return None, 0.0, []
        for c in self.contacts:
            if _normalize_text(c.email) == q: return c, 1.0, [c]
        candidates: list[tuple[_Contact,float]] = []
        for c in self.contacts:
            for nm in c.all_names():
                score = _difflib.SequenceMatcher(a=q, b=nm).ratio()
                candidates.append((c, score))
        candidates.sort(key=lambda x: x[1], reverse=True)
        if not candidates: return None, 0.0, []
        best, score = candidates[0]
        top = [c for c,_ in candidates[:3]]
        return best, score, top
    def as_dict(self) -> dict:
        return {"contacts":[_dataclasses.asdict(c) for c in self.contacts], "last_updated": int(_time.time())}
    def _load(self):
        with open(self.path, "r", encoding="utf-8") as f: data = _json.load(f)
        self.contacts = [_Contact(**c) for c in data.get("contacts", [])]
    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f: _json.dump(self.as_dict(), f, indent=2)

@dataclass
class ParseResult:
    intent: str | None
    contact_query: str | None = None
    subject: str | None = None
    body: str | None = None
    constraints: dict | None = None

class VoiceEmailNLU:
    def __init__(self, address_book: AddressBook | None = None):
        self.address_book = address_book
        self._pat_reply_from = _re.compile(r"(answer|reply)\s+(?:to\s+)?(?:emails?\s+)?(?:from\s+)?(?P<name>.+)$", _re.I)
        self._pat_reply_to   = _re.compile(r"(reply|respond)\s+(?:to\s+)(?P<name>.+)$", _re.I)
        self._pat_read_from  = _re.compile(r"(show|read|list|check)\s+(?:my\s+)?emails?\s+(?:from\s+)(?P<name>.+)$", _re.I)
        self._pat_send_to    = _re.compile(r"(send|email|compose)\s+(?:an?\s+email\s+)?(?:to\s+)?(?P<name>[^,]+?)(?:\s+about\s+(?P<subject>[^,]+?))?(?:\s+(?:that\s+says|saying)\s+(?P<body>.+))?$", _re.I)
    def parse(self, text: str) -> ParseResult:
        t = (text or "").strip()
        m = self._pat_reply_from.search(t) or self._pat_reply_to.search(t)
        if m: return ParseResult(intent="reply_contact", contact_query=m.group("name").strip())
        m = self._pat_read_from.search(t)
        if m: return ParseResult(intent="read_contact", contact_query=m.group("name").strip())
        m = self._pat_send_to.search(t)
        if m: return ParseResult(intent="send_contact", contact_query=(m.group("name") or "").strip(), subject=(m.group("subject") or "").strip() or None, body=(m.group("body") or "").strip() or None)
        if "email" in t.lower() or "inbox" in t.lower(): return ParseResult(intent="read_generic")
        return ParseResult(intent=None)

class VoiceEmailController:
    def __init__(self, execute_tool_fn, address_book: AddressBook, nlu: VoiceEmailNLU, confidence_threshold: float = 0.72):
        self.execute_tool = execute_tool_fn
        self.address_book = address_book
        self.nlu = nlu
        self.confidence_threshold = confidence_threshold
    def handle_voice_command(self, utterance: str, dry_run: bool = True) -> dict:
        parse = self.nlu.parse(utterance)
        if parse.intent in ("reply_contact","read_contact","send_contact"):
            contact, conf, top = self.address_book.find_best(parse.contact_query or "")
            if not contact or conf < self.confidence_threshold:
                suggestion = ", ".join([c.name for c in top]) or "no matches"
                return {"success": False, "needs_disambiguation": True, "spoken_confirmation": f"I found multiple or low-confidence matches for '{parse.contact_query}'. Did you mean {suggestion}?", "candidates": [_dataclasses.asdict(c) for c in top], "confidence": conf}
        if parse.intent == "reply_contact": return self._reply_latest_from(contact, dry_run=dry_run)
        if parse.intent == "read_contact":  return self._read_from(contact, dry_run=dry_run)
        if parse.intent == "send_contact":  return self._send_to(contact, subject=parse.subject, body=parse.body, dry_run=dry_run)
        if parse.intent == "read_generic":  return self._read_generic(dry_run=dry_run)
        return {"success": False, "spoken_confirmation": "I didn't catch that. Try 'reply to Sam', 'show emails from Jordan', or 'email Pat about timelines saying move ahead'."}
    def _read_generic(self, dry_run: bool) -> dict:
        args = {"query": "in:inbox newer_than:7d"}
        if dry_run: return {"success": True, "plan": {"tool": "read_gmail", "args": args}, "spoken_confirmation": "I'll read your recent inbox."}
        out = self.execute_tool("read_gmail", args); return self._norm(out, "I'll read your recent inbox.")
    def _read_from(self, contact: _Contact, dry_run: bool) -> dict:
        args = {"query": f'in:inbox from:{contact.email}'}
        if dry_run: return {"success": True, "plan": {"tool": "read_gmail", "args": args}, "spoken_confirmation": f"I'll read your recent emails from {contact.name}."}
        out = self.execute_tool("read_gmail", args); return self._norm(out, f"I'll read your emails from {contact.name}.")
    def _reply_latest_from(self, contact: _Contact, dry_run: bool) -> dict:
        args = {"query": f'in:inbox from:{contact.email}', "mode": "latest_only"}
        if dry_run: return {"success": True, "plan": {"tool": "reply_gmail", "args": args}, "spoken_confirmation": f"I'll reply to the latest email from {contact.name}."}
        out = self.execute_tool("reply_gmail", args); return self._norm(out, f"I replied to the latest email from {contact.name}.")
    def _send_to(self, contact: _Contact, subject: str | None, body: str | None, dry_run: bool) -> dict:
        text = f"send email to {contact.email}"
        if subject: text += f" about {subject}"
        if body: text += f" saying {body}"
        args = {"to": contact.email, "subject": subject, "body": body, "text": text}
        if dry_run: return {"success": True, "plan": {"tool": "send_gmail", "args": args}, "spoken_confirmation": f"I'll send {contact.name} an email" + (f" about {subject}" if subject else "") + (" with your message." if body else ".")}
        out = self.execute_tool("send_gmail", args); return self._norm(out, f"I sent an email to {contact.name}.")
    def _norm(self, out, confirmation: str) -> dict:
        if isinstance(out, str):
            try: obj = _json.loads(out)
            except Exception: obj = {"raw": out}
        else: obj = out or {}
        obj.setdefault("success", True); obj.setdefault("spoken_confirmation", confirmation); return obj

_VOICE_ADDRBOOK_PATH = _os.environ.get("BLUE_ADDRESS_BOOK", "/mnt/data/blue_address_book.json")
__voice_singletons = {"ab": None, "nlu": None, "controller": None}

def get_voice_email_controller(execute_tool_fn):
    ab = __voice_singletons.get("ab")
    if ab is None:
        if not _os.path.exists(_VOICE_ADDRBOOK_PATH):
            seed = {"contacts":[
                {"name":"Sam Carter","email":"sam.carter@example.com","aliases":["Sam","Samuel Carter"]},
                {"name":"Jordan Lee","email":"jordan.lee@example.com","aliases":["Jordy","J Lee"]},
                {"name":"Pat Morgan","email":"pat.morgan@example.com","aliases":["Patrick Morgan","Patricia Morgan","Pat"]}
            ], "last_updated": int(_time.time())}
            with open(_VOICE_ADDRBOOK_PATH, "w", encoding="utf-8") as f: _json.dump(seed, f, indent=2)
        ab = AddressBook(_VOICE_ADDRBOOK_PATH); __voice_singletons["ab"] = ab
    nlu = __voice_singletons.get("nlu") or VoiceEmailNLU(address_book=ab); __voice_singletons["nlu"] = nlu
    ctl = __voice_singletons.get("controller") or VoiceEmailController(execute_tool_fn=execute_tool_fn, address_book=ab, nlu=nlu); __voice_singletons["controller"] = ctl
    return ctl

def voice_email_handle_command(utterance: str, *, execute_tool_fn, dry_run: bool = True) -> dict:
    ctl = get_voice_email_controller(execute_tool_fn)
    return ctl.handle_voice_command(utterance, dry_run=dry_run)

# End Voice Email Interface
###############################################################################