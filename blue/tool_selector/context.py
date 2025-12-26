"""
Context extraction from conversation history.

Extracts contextual information from recent messages to improve
intent detection accuracy.
"""

from typing import Dict, List
from .constants import MAX_CONTEXT_MESSAGES


def extract_context(conversation_history: List[Dict]) -> Dict:
    """
    Extract context from conversation history.

    Args:
        conversation_history: List of conversation messages with structure:
            [{'role': 'user'/'assistant', 'content': '...', 'tool_used': '...'}, ...]

    Returns:
        Context dictionary with flags and recency information:
        {
            'has_music_in_history': bool,
            'music_recency': int,  # How many messages ago
            'has_email_in_history': bool,
            'email_recency': int,
            # ... etc for each domain
            'recent_tools': List[str],  # Recently used tools
        }
    """
    context = {
        'recent_tools': [],
    }

    if not conversation_history:
        return context

    # Get recent messages (last N)
    recent = conversation_history[-MAX_CONTEXT_MESSAGES:]

    # Track tool usage and keywords
    tool_domains = {
        'music': ['play_music', 'control_music', 'music', 'song', 'artist'],
        'email': ['read_gmail', 'send_gmail', 'reply_gmail', 'email', 'inbox'],
        'lights': ['control_lights', 'light', 'lights', 'mood', 'brightness'],
        'camera': ['capture_camera_image', 'view_image', 'camera', 'picture'],
        'document': ['search_documents', 'create_document', 'document', 'file'],
        'weather': ['get_weather', 'weather', 'forecast'],
    }

    # Check for each domain
    for domain, keywords in tool_domains.items():
        has_flag = f'has_{domain}_in_history'
        recency_flag = f'{domain}_recency'

        context[has_flag] = False
        context[recency_flag] = 0

        # Search from most recent to oldest
        for i, msg in enumerate(reversed(recent)):
            content = msg.get('content', '').lower()
            tool_used = msg.get('tool_used', '')

            # Check if any keyword or tool matches this domain
            if any(kw in content or kw == tool_used for kw in keywords):
                context[has_flag] = True
                context[recency_flag] = i  # 0 = most recent
                break

    # Track recently used tools
    for msg in reversed(recent):
        tool_used = msg.get('tool_used')
        if tool_used and tool_used not in context['recent_tools']:
            context['recent_tools'].append(tool_used)
            if len(context['recent_tools']) >= 5:
                break

    return context


def _is_greeting(message: str) -> bool:
    """Check if message is a greeting."""
    from .constants import GREETING_PATTERNS, CASUAL_PATTERNS

    msg_lower = message.lower().strip()

    # Exact greetings
    if msg_lower in ['hi', 'hello', 'hey', 'yo']:
        return True

    # Greeting patterns
    if any(pattern in msg_lower for pattern in GREETING_PATTERNS):
        return True

    # Casual patterns (thanks, bye, etc.)
    if any(pattern in msg_lower for pattern in CASUAL_PATTERNS):
        return True

    return False


def should_skip_tool_selection(message: str) -> bool:
    """
    Determine if tool selection should be skipped for this message.

    Returns True for greetings, casual chat, acknowledgments, etc.
    """
    if not message or len(message.strip()) < 2:
        return True

    return _is_greeting(message)
