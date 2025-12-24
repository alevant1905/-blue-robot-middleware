"""
Blue Robot Middleware Package
=============================
A modular home assistant with music, lights, email, vision, and more.

Usage:
    from blue import utils, memory, llm
    from blue.utils import ConversationState, fuzzy_match
    from blue.memory import load_blue_facts, save_blue_facts
    from blue.llm import call_llm, LMStudioClient
"""

# Future imports
from __future__ import annotations

__version__ = "11.1.0"  # Enhanced tool selector v2.0

# Local imports
from .llm import (  # Client; Settings; URLs
    LM_STUDIO_MODEL,
    LM_STUDIO_RAG_URL,
    LM_STUDIO_URL,
    LMStudioClient,
    Settings,
    call_llm,
    get_lm_client,
    settings,
)
from .memory import (  # Facts; Memory system availability
    BLUE_FACTS,
    BLUE_FACTS_DB,
    ENHANCED_MEMORY_AVAILABLE,
    build_system_preamble,
    extract_and_save_facts,
    load_blue_facts,
    save_blue_facts,
)

# Tool Selector - Now using Enhanced v2.0 as primary
# (tool_selector.py includes backward compatibility for v1.0 names)
from .tool_selector import (
    TOOL_PROFILES,
    EnhancedToolSelector,
    ImprovedToolSelector,
    ParsedIntent,
    SelectionResult,
    ToolIntent,
    ToolMatch,
    ToolProfile,
    ToolSelectionResult,
)
from .tool_selector import (
    fuzzy_match as tool_fuzzy_match,  # Primary v2.0 classes; Backward compatibility aliases (v1.0); Utilities
)
from .tool_selector import integrate_enhanced_selector, integrate_with_existing_system
from .tool_selector import normalize_artist_name as tool_normalize_artist
from .tool_selector import normalize_verb

# Re-export commonly used items for convenience
from .utils import (  # Logging; Compound request parsing; Caching; Query analysis; String utilities; Conversation state
    ConversationState,
    cache_response,
    clean_response_text,
    detect_follow_up_correction,
    estimate_query_complexity,
    extract_action_from_query,
    extract_entities,
    extract_quoted_text,
    fuzzy_match,
    get_cached_response,
    get_conversation_state,
    get_time_ago,
    log,
    normalize_artist_name,
    parse_compound_request,
    safe_json_parse,
    setup_logger,
    smart_cache_key,
    truncate_text,
    validate_response_quality,
)

__all__ = [
    # Version
    '__version__',
    # Utils
    'setup_logger', 'log',
    'parse_compound_request', 'detect_follow_up_correction',
    'smart_cache_key', 'get_cached_response', 'cache_response',
    'estimate_query_complexity', 'extract_entities', 'extract_action_from_query',
    'fuzzy_match', 'normalize_artist_name', 'safe_json_parse',
    'truncate_text', 'extract_quoted_text', 'get_time_ago', 'clean_response_text',
    'ConversationState', 'get_conversation_state', 'validate_response_quality',
    # Memory
    'BLUE_FACTS', 'BLUE_FACTS_DB',
    'load_blue_facts', 'save_blue_facts', 'extract_and_save_facts',
    'build_system_preamble', 'ENHANCED_MEMORY_AVAILABLE',
    # LLM
    'LMStudioClient', 'get_lm_client', 'call_llm',
    'Settings', 'settings',
    'LM_STUDIO_URL', 'LM_STUDIO_MODEL', 'LM_STUDIO_RAG_URL',
    # Tool Selector v2.0 (Primary)
    'EnhancedToolSelector', 'ToolProfile', 'ParsedIntent', 'ToolMatch', 'SelectionResult',
    'integrate_enhanced_selector', 'TOOL_PROFILES', 'normalize_verb',
    # Tool Selector v1.0 (Backward Compatibility Aliases)
    'ImprovedToolSelector', 'ToolIntent', 'ToolSelectionResult', 'integrate_with_existing_system',
    'tool_fuzzy_match', 'tool_normalize_artist',
]
