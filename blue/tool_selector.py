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

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Import MOOD_PRESETS from lights module for light intent detection
try:
    from .tools.lights import MOOD_PRESETS
except ImportError:
    MOOD_PRESETS = {}


# ================================================================================
# HELPER FUNCTIONS
# ================================================================================

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


# ================================================================================
# DATA CLASSES
# ================================================================================

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


# ================================================================================
# IMPROVED TOOL SELECTOR
# ================================================================================

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

    # Confidence thresholds - RAISED to reduce false positives
    CONFIDENCE_HIGH = 0.90
    CONFIDENCE_MEDIUM = 0.75
    CONFIDENCE_LOW = 0.55
    CONFIDENCE_MINIMUM = 0.50  # Below this, don't suggest tool (raised from 0.30)

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
        intents.extend(self._detect_recognition_intents(msg_lower, context))
        intents.extend(self._detect_gmail_intents(msg_lower, context))
        intents.extend(self._detect_music_intents(msg_lower, context))
        intents.extend(self._detect_timer_reminder_intents(msg_lower, context))
        intents.extend(self._detect_calendar_intents(msg_lower, context))
        intents.extend(self._detect_weather_intents(msg_lower, context))
        intents.extend(self._detect_automation_intents(msg_lower, context))
        intents.extend(self._detect_media_library_intents(msg_lower, context))
        intents.extend(self._detect_location_intents(msg_lower, context))
        intents.extend(self._detect_contact_intents(msg_lower, context))
        intents.extend(self._detect_habit_intents(msg_lower, context))
        intents.extend(self._detect_document_intents(msg_lower, context))
        intents.extend(self._detect_web_intents(msg_lower, context))
        intents.extend(self._detect_light_intents(msg_lower, context))
        intents.extend(self._detect_utility_intents(msg_lower, context))
        intents.extend(self._detect_notes_tasks_intents(msg_lower, context))
        intents.extend(self._detect_system_intents(msg_lower, context))

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

    # ================================================================================
    # INTENT DETECTORS
    # ================================================================================

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

    def _detect_recognition_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect face and place recognition intents.
        v9+ ENHANCEMENT: Person and place recognition
        """
        intents = []

        # ==================== WHO IS THIS / RECOGNIZE ====================
        recognize_signals = [
            'who is this', 'who is that', 'recognize', 'identify',
            'do you know who', 'can you tell who', 'who do you see',
            'who am i looking at', 'is that', 'is this'
        ]
        if any(sig in msg_lower for sig in recognize_signals):
            intents.append(ToolIntent(
                tool_name='capture_and_recognize',
                confidence=0.92,
                priority=self.PRIORITY_HIGH,
                reason="recognition request detected",
                extracted_params={}
            ))

        # ==================== WHERE IS THIS / WHAT PLACE ====================
        place_signals = [
            'where is this', 'what room', 'which room', 'what place',
            'where am i', 'recognize this place', 'what location',
            'do you know where', 'identify this location'
        ]
        if any(sig in msg_lower for sig in place_signals):
            intents.append(ToolIntent(
                tool_name='capture_and_recognize',
                confidence=0.90,
                priority=self.PRIORITY_MEDIUM,
                reason="place recognition request",
                extracted_params={}
            ))

        # ==================== TEACH / LEARN PERSON ====================
        teach_person_signals = [
            'learn my face', 'remember my face', 'this is me',
            "that's me", 'teach you my face', 'learn to recognize',
            'remember who i am', 'this is', "that's", 'learn who'
        ]
        # Check for teaching patterns like "this is Alex" or "that's my friend John"
        name_teach_pattern = r"(?:this is|that's|that is|learn|remember)\s+(\w+)"
        if any(sig in msg_lower for sig in teach_person_signals):
            # Try to extract name
            name_match = re.search(name_teach_pattern, msg_lower)
            name = name_match.group(1).title() if name_match else None

            intents.append(ToolIntent(
                tool_name='teach_person',
                confidence=0.88,
                priority=self.PRIORITY_MEDIUM,
                reason="teach person recognition",
                extracted_params={'name': name}
            ))

        # ==================== TEACH / LEARN PLACE ====================
        teach_place_signals = [
            'remember this place', 'learn this room', 'this is my',
            'remember this location', 'this room is', 'learn this place',
            'remember where we are'
        ]
        if any(sig in msg_lower for sig in teach_place_signals):
            # Try to extract place name
            place_pattern = r"(?:this is|this room is|this place is|remember as)\s+(?:my\s+)?(\w+(?:\s+\w+)?)"
            place_match = re.search(place_pattern, msg_lower)
            place_name = place_match.group(1).title() if place_match else None

            intents.append(ToolIntent(
                tool_name='teach_place',
                confidence=0.85,
                priority=self.PRIORITY_MEDIUM,
                reason="teach place recognition",
                extracted_params={'name': place_name}
            ))

        # ==================== WHO DO YOU KNOW ====================
        list_people_signals = [
            'who do you know', 'who can you recognize', 'list known people',
            'who have you learned', 'which faces', 'known faces',
            'people you recognize', 'who do i know'
        ]
        if any(sig in msg_lower for sig in list_people_signals):
            intents.append(ToolIntent(
                tool_name='who_do_i_know',
                confidence=0.95,
                priority=self.PRIORITY_MEDIUM,
                reason="list known people",
                extracted_params={}
            ))

        # ==================== WHAT PLACES DO YOU KNOW ====================
        list_places_signals = [
            'what places do you know', 'which places', 'known places',
            'places you recognize', 'rooms you know', 'locations you know',
            'where do you know', 'list known places'
        ]
        if any(sig in msg_lower for sig in list_places_signals):
            intents.append(ToolIntent(
                tool_name='where_do_i_know',
                confidence=0.95,
                priority=self.PRIORITY_MEDIUM,
                reason="list known places",
                extracted_params={}
            ))

        # ==================== FORGET PERSON ====================
        forget_signals = [
            'forget', 'remove', 'delete from memory', 'stop recognizing',
            'unlearn', 'remove from recognition'
        ]
        if any(sig in msg_lower for sig in forget_signals) and \
           any(w in msg_lower for w in ['face', 'person', 'recognize']):
            # Try to extract name
            name_match = re.search(r'(?:forget|remove|unlearn)\s+(\w+)', msg_lower)
            name = name_match.group(1).title() if name_match else None

            intents.append(ToolIntent(
                tool_name='forget_person',
                confidence=0.85,
                priority=self.PRIORITY_MEDIUM,
                reason="forget person request",
                extracted_params={'name': name}
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
        ENHANCED v7: Better false positive filtering for non-music "play" contexts
        """
        intents = []

        # EARLY EXIT: Non-music "play" contexts that should NEVER trigger music
        non_music_play_phrases = [
            'play a game', 'play game', 'play games', 'play video game', 'play the game',
            'play a video', 'play video', 'play this video', 'play the video',
            'play a role', 'play the role', 'play a part', 'play the part',
            'play sports', 'play a sport', 'play basketball', 'play football', 'play soccer',
            'play tennis', 'play golf', 'play baseball', 'play hockey',
            'play cards', 'play poker', 'play chess', 'play checkers',
            'play with', 'play around', "let's play", 'wanna play', 'want to play',
            'play a match', 'play the match', 'play a round',
            'play a trick', 'play tricks', 'play a joke', 'play pranks',
            'role play', 'roleplay', 'word play', 'wordplay', 'fair play',
            'at play', "child's play", 'foul play', 'power play'
        ]
        if any(phrase in msg_lower for phrase in non_music_play_phrases):
            return intents  # Return empty - no music intent

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

        # IMPORTANT: Exclude false positives where "blue" refers to the robot, not the genre "blues"
        # Check if "blues" genre was matched, but it's actually "blue" (robot name) in self-referential context
        if has_genre and 'blue' in msg_lower:
            # Check for self-referential context (talking about Blue the robot)
            if any(phrase in msg_lower for phrase in ['about you', 'your', 'yourself', 'you are', 'remember', 'learn', 'never forget']):
                has_genre = False  # Not a genre mention - it's about the robot

        # v7 ENHANCEMENT: Fuzzy match for artist names (handles typos)
        # BUT: Only do fuzzy matching if we have clear music context (play signal present)
        matched_artist = None
        if not has_artist and any(signal in msg_lower for signal in play_signals):
            # Try fuzzy matching on individual words AFTER removing play signals
            # This prevents "play" matching with "Coldplay"
            msg_without_signals = msg_lower
            for signal in play_signals:
                msg_without_signals = msg_without_signals.replace(signal, ' ')

            words = msg_without_signals.split()
            words = [w for w in words if len(w) > 2]  # Skip short words

            for i in range(len(words)):
                # Try single words and pairs
                for length in [1, 2, 3]:
                    if i + length <= len(words):
                        phrase = ' '.join(words[i:i+length])
                        # Stricter threshold and minimum length
                        if len(phrase) >= 4:  # At least 4 characters
                            match = fuzzy_match(phrase, artists, threshold=0.85)  # Raised from 0.8
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
            # Also check for non-music play context (games, videos, etc.)
            non_music_play = ['game', 'video', 'role', 'part', 'character', 'sport', 'match', 'quiz']

            if any(word in msg_lower for word in info_words):
                play_confidence = 0.2  # Lowered from 0.3
                play_reason.append("play+music but info request detected")
            elif any(word in msg_lower for word in non_music_play):
                play_confidence = 0.25  # NEW: Detect non-music play context
                play_reason.append("play detected but non-music context (game/video/etc)")
            else:
                play_confidence = 0.95
                play_reason.append("clear play + music intent")
        elif has_play and context.get('has_music_in_history'):
            # Only trigger if recent music context (within 3 messages)
            if context.get('music_recency', 0) >= 3:
                play_confidence = 0.50  # Lowered from 0.75 and requires stricter check
                play_reason.append("play verb with RECENT music context")
            else:
                play_confidence = 0.30  # Too old context, likely false positive
                play_reason.append("play verb but music context too old")
        elif has_music and any(word in msg_lower for word in ['play', 'start', 'queue']):
            # Check if it's really about music or just coincidental word overlap
            if context.get('has_music_in_history') or any(g in msg_lower for g in genres[:20]):  # Check for actual music context
                play_confidence = 0.60  # Slightly lowered from 0.65
                play_reason.append("music noun with play indicators + context")
            else:
                play_confidence = 0.35  # Too low to trigger (below minimum threshold)
                play_reason.append("music noun + play but no context")
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
            # Check for memory/learning context (not music)
            elif any(w in msg_lower for w in ['remember', 'learn', 'don\'t forget', 'never forget', 'memorize', 'keep in mind']):
                play_confidence = 0.15  # Too low to trigger
                play_reason.append("artist mentioned but memory context detected")
            # Check for self-referential context (talking about Blue the robot, not music)
            elif any(phrase in msg_lower for phrase in ['about yourself', 'about you', 'about blue', 'your name', 'you are', 'your identity']):
                play_confidence = 0.15  # Too low to trigger
                play_reason.append("artist mentioned but self-referential context")
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

        # LIST files/documents
        list_signals = {
            'strong': [
                'list files', 'list documents', 'show files', 'show documents',
                'list all files', 'show all documents', 'what files', 'what documents',
                'list my files', 'list my documents', 'show my files', 'show my documents',
                'files in', 'documents in'
            ],
            'medium': ['list', 'show me', 'what\'s in']
        }

        list_confidence = 0.0
        list_reason = []

        if any(signal in msg_lower for signal in list_signals['strong']):
            list_confidence = 0.92
            list_reason.append("explicit file/document listing keywords")
        elif any(verb in msg_lower for verb in list_signals['medium']):
            # Check if it's asking about files/documents in a folder
            if any(noun in msg_lower for noun in doc_nouns + ['folder', 'directory']):
                list_confidence = 0.85
                list_reason.append("list verb + file/folder noun")

        if list_confidence > 0:
            # Try to extract directory from message
            directory = None
            # Look for "in the X folder" or "in X"
            if 'document' in msg_lower and 'folder' in msg_lower:
                directory = 'uploaded_documents'
            elif 'upload' in msg_lower:
                directory = 'uploaded_documents'

            intents.append(ToolIntent(
                tool_name='list_files',
                confidence=list_confidence,
                priority=self.PRIORITY_MEDIUM,
                reason=' | '.join(list_reason),
                extracted_params={'directory': directory if directory else 'uploaded_documents'}
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
            'actions': ['turn on', 'turn off', 'switch on', 'switch off', 'set', 'change', 'dim', 'brighten', 'adjust', 'on', 'off'],
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

        # Check for common "light as adjective" phrases (NOT about lighting)
        light_adjective_phrases = [
            'light snack', 'light meal', 'light reading', 'light exercise',
            'light work', 'light duty', 'light touch', 'light breeze',
            'light rain', 'light traffic', 'light weight', 'light load',
            'light blue', 'light green', 'light pink', 'light grey', 'light gray',
            'light brown', 'light yellow', 'light purple', 'light orange',
            'bring to light', 'see the light', 'light of day', 'in light of',
            'light years', 'speed of light', 'light as a feather'
        ]
        if any(phrase in msg_lower for phrase in light_adjective_phrases):
            # "light" is being used as an adjective, not about lights
            return intents

        # Check for visualizer conflicts - "light show" should go to visualizer
        visualizer_phrases = ['light show', 'lights dance', 'sync lights', 'disco mode', 'party lights']
        if any(phrase in msg_lower for phrase in visualizer_phrases):
            # Let music visualizer handle this
            return intents

        if has_light and (has_action or has_color or has_mood):
            confidence = 0.95
            reason.append("light + action/color/mood")
        elif has_mood and not has_light:
            # Mood words alone are WEAK signals - many mood words are ambiguous (party, chill, focus, etc.)
            # Only trigger if there's a clear "set" context AND explicit light indicator nearby
            set_context = any(w in msg_lower for w in ['set', 'change', 'make', 'switch to', 'turn to'])
            explicit_light_ref = any(w in msg_lower for w in ['it', 'them', 'the lights', 'the light', 'lighting', 'brightness'])

            if set_context and explicit_light_ref and not context.get('has_music_in_history') and 'play' not in msg_lower:
                confidence = 0.70  # Lowered from 0.85 - still uncertain
                reason.append("mood keyword with set context + light reference")
            else:
                confidence = 0.40  # Too low to trigger - mood words are too ambiguous
                reason.append("mood keyword but no clear light context")
        elif has_color and ('set' in msg_lower or 'change' in msg_lower or 'make' in msg_lower):
            # Color alone is also ambiguous - could be clothing, design, etc.
            if has_light or context.get('has_lights_in_history') or 'light' in msg_lower:
                confidence = 0.88
                reason.append("color + set/change + light context")
            else:
                confidence = 0.45  # Too ambiguous without light context
                reason.append("color + set/change but no light context")
        elif has_light:
            # Just mentioning "light" is weak - could be "light snack", "light reading", etc.
            if has_action or context.get('has_lights_in_history'):
                confidence = 0.65  # Lowered from 0.70
                reason.append("light noun mentioned with action/context")
            else:
                confidence = 0.40  # Too low to trigger
                reason.append("light noun only - ambiguous")

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
        Detect utility tool intents (time, date, calculator, weather, etc).
        These are quick queries that can be answered without external services.
        """
        intents = []

        # ==================== TIME QUERIES ====================
        time_signals = [
            'what time', "what's the time", 'current time', 'time is it',
            'tell me the time', 'what time is it', 'time now', 'time right now',
            'do you know the time', 'got the time', 'have the time',
            'what is the time', 'the time please', 'time please'
        ]
        if any(signal in msg_lower for signal in time_signals):
            intents.append(ToolIntent(
                tool_name='get_time',
                confidence=0.98,
                priority=self.PRIORITY_CRITICAL,
                reason="time query detected",
                extracted_params={'action': 'time'}
            ))

        # ==================== DATE QUERIES ====================
        date_signals = [
            "what's today", 'what is today', "today's date", 'current date',
            'what day is it', 'what date is it', 'the date today', 'date today',
            'what day of the week', 'day of week', 'what month is it',
            'what year is it', 'what is the date', "what's the date"
        ]
        if any(signal in msg_lower for signal in date_signals):
            intents.append(ToolIntent(
                tool_name='get_date',
                confidence=0.98,
                priority=self.PRIORITY_CRITICAL,
                reason="date query detected",
                extracted_params={'action': 'date'}
            ))

        # Combined datetime query
        datetime_signals = [
            'date and time', 'time and date', 'current datetime',
            'what is the date and time', 'date time'
        ]
        if any(signal in msg_lower for signal in datetime_signals):
            intents.append(ToolIntent(
                tool_name='get_datetime',
                confidence=0.98,
                priority=self.PRIORITY_CRITICAL,
                reason="datetime query detected",
                extracted_params={'action': 'datetime'}
            ))

        # ==================== CALCULATOR ====================
        # Math expression patterns
        math_patterns = [
            r'\d+\s*[\+\-\*\/\^]\s*\d+',  # 5 + 3, 10 * 2
            r'\d+\s*(?:plus|minus|times|divided by|multiplied by)\s*\d+',  # 5 plus 3
            r'(?:calculate|compute|solve|evaluate)\s+.+',  # calculate 5+3
            r'what is \d+\s*[\+\-\*\/\^]\s*\d+',  # what is 5 + 3
            r'(\d+(?:\.\d+)?)\s*%\s*(?:of)\s*(\d+(?:\.\d+)?)',  # 15% of 200
            r'square root of \d+',  # square root of 16
            r'sqrt\s*\(?\s*\d+',  # sqrt(16) or sqrt 16
            r'\d+\s*(?:squared|cubed)',  # 5 squared
            r'(?:factorial|fact)\s*\(?\s*\d+',  # factorial 5
            r'\d+\s*(?:factorial|!)',  # 5!
            r'(?:sin|cos|tan|log|ln)\s*\(?\s*\d+',  # sin(45)
            r'power of \d+',  # to the power of
            r'\d+\s*to the\s*\d+',  # 2 to the 3
        ]

        for pattern in math_patterns:
            if re.search(pattern, msg_lower):
                # Extract the math expression
                expression = msg_lower
                for prefix in ['calculate', 'compute', 'solve', 'evaluate', 'what is', "what's"]:
                    expression = expression.replace(prefix, '').strip()

                intents.append(ToolIntent(
                    tool_name='calculate',
                    confidence=0.95,
                    priority=self.PRIORITY_CRITICAL,
                    reason="math expression detected",
                    extracted_params={'expression': expression}
                ))
                break

        # ==================== UNIT CONVERSION ====================
        conversion_patterns = [
            r'convert\s+(\d+(?:\.\d+)?)\s*(\w+)\s+to\s+(\w+)',  # convert 5 miles to km
            r'(\d+(?:\.\d+)?)\s*(\w+)\s+(?:in|to)\s+(\w+)',  # 5 miles in km
            r'how many (\w+) (?:in|are in)\s+(\d+(?:\.\d+)?)\s*(\w+)',  # how many km in 5 miles
            r'(\d+(?:\.\d+)?)\s*(celsius|fahrenheit|kelvin)\s+(?:to|in)\s+(celsius|fahrenheit|kelvin)',  # temp
            r'(\d+(?:\.\d+)?)\s*(c|f|k)\s+(?:to|in)\s+(c|f|k)',  # short temp
        ]

        conversion_signals = ['convert', 'conversion', 'how many', 'equals in', 'in km', 'in miles',
                              'in feet', 'in meters', 'in celsius', 'in fahrenheit', 'to kg', 'to pounds',
                              'to liters', 'to gallons', 'to inches', 'to centimeters']

        if any(signal in msg_lower for signal in conversion_signals):
            for pattern in conversion_patterns:
                match = re.search(pattern, msg_lower)
                if match:
                    intents.append(ToolIntent(
                        tool_name='convert_units',
                        confidence=0.95,
                        priority=self.PRIORITY_CRITICAL,
                        reason="unit conversion detected",
                        extracted_params={
                            'expression': msg_lower,
                            'groups': match.groups()
                        }
                    ))
                    break
            else:
                # General conversion request without specific match
                intents.append(ToolIntent(
                    tool_name='convert_units',
                    confidence=0.80,
                    priority=self.PRIORITY_MEDIUM,
                    reason="conversion keyword detected",
                    extracted_params={'expression': msg_lower}
                ))

        # ==================== RANDOM GENERATION ====================
        random_signals = [
            'flip a coin', 'coin flip', 'heads or tails', 'toss a coin',
            'roll a die', 'roll dice', 'roll a d6', 'roll d20', 'dice roll',
            'random number', 'pick a number', 'generate a number',
            'random between', 'random from', 'choose randomly',
            'pick one', 'choose one', 'random choice', 'random pick'
        ]

        # Also detect "roll a d20", "roll a d6", etc with pattern
        has_dice_roll = bool(re.search(r'roll\s+(?:a\s+)?d\d+', msg_lower))
        has_random_signal = any(signal in msg_lower for signal in random_signals)

        if has_random_signal or has_dice_roll:
            # Determine type and params
            random_type = 'number'
            sides = 6
            min_val = 1
            max_val = 100

            if 'coin' in msg_lower or 'heads' in msg_lower or 'tails' in msg_lower:
                random_type = 'coin'
            elif 'die' in msg_lower or 'dice' in msg_lower or re.search(r'd\d+', msg_lower):
                random_type = 'dice'
                # Extract dice type
                dice_match = re.search(r'd(\d+)', msg_lower)
                sides = int(dice_match.group(1)) if dice_match else 6
            else:
                # Try to extract range
                range_match = re.search(r'between\s+(\d+)\s+and\s+(\d+)', msg_lower)
                if range_match:
                    min_val, max_val = int(range_match.group(1)), int(range_match.group(2))

            intents.append(ToolIntent(
                tool_name='generate_random',
                confidence=0.95,
                priority=self.PRIORITY_CRITICAL,
                reason="random generation requested",
                extracted_params={
                    'type': random_type,
                    'sides': sides if random_type == 'dice' else None,
                    'min': min_val if random_type == 'number' else None,
                    'max': max_val if random_type == 'number' else None
                }
            ))

        # ==================== SYSTEM INFO ====================
        system_signals = [
            'system info', 'system information', 'computer info',
            'what os', 'operating system', 'what platform',
            'cpu info', 'memory info', 'disk space', 'free space',
            'system status', 'computer status', 'machine info'
        ]

        if any(signal in msg_lower for signal in system_signals):
            intents.append(ToolIntent(
                tool_name='get_system_info',
                confidence=0.90,
                priority=self.PRIORITY_MEDIUM,
                reason="system info query detected",
                extracted_params={}
            ))

        # ==================== TEXT UTILITIES ====================
        count_signals = [
            'count words', 'word count', 'how many words',
            'count characters', 'character count', 'how many characters',
            'count lines', 'line count', 'how many lines',
            'count sentences', 'sentence count', 'how many sentences'
        ]

        if any(signal in msg_lower for signal in count_signals):
            count_type = 'words'
            if 'character' in msg_lower:
                count_type = 'characters'
            elif 'line' in msg_lower:
                count_type = 'lines'
            elif 'sentence' in msg_lower:
                count_type = 'sentences'

            intents.append(ToolIntent(
                tool_name='count_text',
                confidence=0.90,
                priority=self.PRIORITY_MEDIUM,
                reason="text counting requested",
                extracted_params={'type': count_type}
            ))

        # ==================== WEATHER ====================
        weather_keywords = ['weather', 'forecast', 'temperature outside', 'rain today',
                           'snow today', 'sunny today', 'how hot', 'how cold',
                           'will it rain', 'is it raining', 'weather like']
        if any(kw in msg_lower for kw in weather_keywords):
            # Extract location if present
            location_patterns = [
                r'(?:weather|forecast|temperature)\s+(?:in|at|for)\s+([A-Za-z\s]+)',
                r'(?:in|at|for)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(?:weather|forecast)',
            ]
            location = None
            for pattern in location_patterns:
                match = re.search(pattern, msg_lower)
                if match:
                    location = match.group(1).strip().title()
                    break

            if not location:
                location = "Toronto"  # Default

            intents.append(ToolIntent(
                tool_name='get_weather',
                confidence=0.95,
                priority=self.PRIORITY_MEDIUM,
                reason="weather keyword detected",
                extracted_params={'location': location}
            ))

        # ==================== JAVASCRIPT (kept for compatibility) ====================
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

    def _detect_notes_tasks_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect notes, tasks, and list management intents.
        v8+ ENHANCEMENT: Full note-taking and task management
        """
        intents = []

        # ==================== NOTES ====================
        note_create_signals = [
            'create a note', 'make a note', 'new note', 'write a note',
            'take a note', 'save a note', 'add a note', 'jot down',
            'note this', 'remember this', 'save this'
        ]
        if any(sig in msg_lower for sig in note_create_signals):
            intents.append(ToolIntent(
                tool_name='create_note',
                confidence=0.95,
                priority=self.PRIORITY_MEDIUM,
                reason="note creation signal detected",
                extracted_params={'title': '', 'content': msg_lower}
            ))

        note_search_signals = [
            'search notes', 'find note', 'search my notes', 'look in notes',
            'find in my notes', 'my notes about', 'notes about', 'show my notes',
            'list my notes', 'what notes', 'any notes'
        ]
        if any(sig in msg_lower for sig in note_search_signals):
            intents.append(ToolIntent(
                tool_name='search_notes',
                confidence=0.92,
                priority=self.PRIORITY_MEDIUM,
                reason="note search signal detected",
                extracted_params={'query': msg_lower}
            ))

        # ==================== TASKS / TODOS ====================
        task_create_signals = [
            'add a task', 'create a task', 'new task', 'add to do',
            'add todo', 'add to-do', 'create todo', 'new todo',
            'i need to', 'i have to', 'remind me to do', 'task to',
            'add to my tasks', 'put on my list'
        ]
        if any(sig in msg_lower for sig in task_create_signals):
            # Extract priority
            priority = 'medium'
            if any(w in msg_lower for w in ['urgent', 'asap', 'immediately', 'right away']):
                priority = 'urgent'
            elif any(w in msg_lower for w in ['important', 'high priority']):
                priority = 'high'
            elif any(w in msg_lower for w in ['low priority', 'eventually', 'whenever']):
                priority = 'low'

            intents.append(ToolIntent(
                tool_name='create_task',
                confidence=0.94,
                priority=self.PRIORITY_MEDIUM,
                reason="task creation signal detected",
                extracted_params={'title': msg_lower, 'priority': priority}
            ))

        task_list_signals = [
            'show my tasks', 'list tasks', 'my tasks', 'my todos', 'my to-dos',
            'what tasks', 'pending tasks', 'upcoming tasks', 'show todos',
            'what do i need to do', 'what should i do', 'my to do list'
        ]
        if any(sig in msg_lower for sig in task_list_signals):
            intents.append(ToolIntent(
                tool_name='list_tasks',
                confidence=0.93,
                priority=self.PRIORITY_MEDIUM,
                reason="task listing signal detected",
                extracted_params={}
            ))

        task_complete_signals = [
            'complete task', 'mark done', 'task done', 'finished task',
            'completed task', 'check off', 'mark as done', 'task complete',
            'done with', 'finished with'
        ]
        if any(sig in msg_lower for sig in task_complete_signals):
            intents.append(ToolIntent(
                tool_name='complete_task',
                confidence=0.92,
                priority=self.PRIORITY_MEDIUM,
                reason="task completion signal detected",
                extracted_params={}
            ))

        # ==================== LISTS (Shopping, Grocery, etc) ====================
        list_add_signals = [
            'add to list', 'add to my list', 'put on list', 'add to shopping',
            'add to grocery', 'shopping list', 'grocery list', 'add to the list',
            'put on the list', 'put on shopping', 'put on grocery'
        ]
        if any(sig in msg_lower for sig in list_add_signals):
            # Detect list type
            list_name = 'shopping'
            if 'grocery' in msg_lower:
                list_name = 'grocery'
            elif 'todo' in msg_lower or 'to-do' in msg_lower or 'to do' in msg_lower:
                list_name = 'todo'
            elif 'wish' in msg_lower:
                list_name = 'wishlist'

            intents.append(ToolIntent(
                tool_name='add_to_list',
                confidence=0.93,
                priority=self.PRIORITY_MEDIUM,
                reason="list add signal detected",
                extracted_params={'list_name': list_name, 'item': msg_lower}
            ))

        list_show_signals = [
            'show my list', 'show the list', 'what on my list', "what's on the list",
            'show shopping list', 'show grocery list', 'my shopping list',
            'my grocery list', 'read the list', 'read my list'
        ]
        if any(sig in msg_lower for sig in list_show_signals):
            list_name = 'shopping'
            if 'grocery' in msg_lower:
                list_name = 'grocery'
            elif 'todo' in msg_lower or 'to-do' in msg_lower:
                list_name = 'todo'

            intents.append(ToolIntent(
                tool_name='get_list',
                confidence=0.92,
                priority=self.PRIORITY_MEDIUM,
                reason="list show signal detected",
                extracted_params={'list_name': list_name}
            ))

        return intents

    def _detect_system_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect system utility intents (clipboard, screenshot, apps, volume).
        v8+ ENHANCEMENT: System tools integration
        """
        intents = []

        # ==================== CLIPBOARD ====================
        clipboard_get_signals = [
            'clipboard', 'what did i copy', 'paste from clipboard',
            'show clipboard', 'read clipboard', "what's in clipboard",
            'what is in my clipboard', 'clipboard contents'
        ]
        if any(sig in msg_lower for sig in clipboard_get_signals):
            intents.append(ToolIntent(
                tool_name='get_clipboard',
                confidence=0.95,
                priority=self.PRIORITY_MEDIUM,
                reason="clipboard read signal detected",
                extracted_params={}
            ))

        clipboard_set_signals = [
            'copy to clipboard', 'copy this', 'put in clipboard',
            'save to clipboard', 'copy that'
        ]
        if any(sig in msg_lower for sig in clipboard_set_signals):
            intents.append(ToolIntent(
                tool_name='set_clipboard',
                confidence=0.94,
                priority=self.PRIORITY_MEDIUM,
                reason="clipboard write signal detected",
                extracted_params={'text': ''}
            ))

        # ==================== SCREENSHOT ====================
        screenshot_signals = [
            'take a screenshot', 'screenshot', 'capture screen',
            'grab screen', 'screen capture', 'save screen',
            'screenshot this', 'take screenshot'
        ]
        if any(sig in msg_lower for sig in screenshot_signals):
            region = 'full'
            if 'window' in msg_lower or 'active' in msg_lower:
                region = 'active'

            intents.append(ToolIntent(
                tool_name='take_screenshot',
                confidence=0.96,
                priority=self.PRIORITY_MEDIUM,
                reason="screenshot signal detected",
                extracted_params={'region': region}
            ))

        # ==================== VOLUME CONTROL ====================
        volume_signals = [
            'volume up', 'volume down', 'turn up volume', 'turn down volume',
            'increase volume', 'decrease volume', 'mute', 'unmute',
            'set volume', 'volume to', 'louder', 'quieter', 'softer'
        ]
        if any(sig in msg_lower for sig in volume_signals):
            action = 'get'
            level = None

            if 'up' in msg_lower or 'increase' in msg_lower or 'louder' in msg_lower:
                action = 'up'
            elif 'down' in msg_lower or 'decrease' in msg_lower or 'quieter' in msg_lower or 'softer' in msg_lower:
                action = 'down'
            elif 'mute' in msg_lower:
                action = 'mute' if 'unmute' not in msg_lower else 'unmute'

            # Try to extract level
            level_match = re.search(r'(?:volume\s+(?:to\s+)?|set\s+(?:to\s+)?)(\d+)', msg_lower)
            if level_match:
                level = int(level_match.group(1))
                action = 'set'

            intents.append(ToolIntent(
                tool_name='set_volume',
                confidence=0.94,
                priority=self.PRIORITY_MEDIUM,
                reason="volume control signal detected",
                extracted_params={'action': action, 'level': level}
            ))

        # ==================== LAUNCH APPLICATION ====================
        launch_signals = [
            'open', 'launch', 'start', 'run', 'open app', 'launch app'
        ]
        app_names = [
            'chrome', 'firefox', 'edge', 'notepad', 'calculator', 'explorer',
            'cmd', 'terminal', 'powershell', 'spotify', 'outlook', 'teams',
            'slack', 'discord', 'vscode', 'code', 'word', 'excel', 'powerpoint'
        ]

        has_launch = any(sig in msg_lower for sig in launch_signals)
        has_app = any(app in msg_lower for app in app_names)

        if has_launch and has_app:
            # Find which app
            app = None
            for a in app_names:
                if a in msg_lower:
                    app = a
                    break

            intents.append(ToolIntent(
                tool_name='launch_application',
                confidence=0.92,
                priority=self.PRIORITY_MEDIUM,
                reason="app launch signal detected",
                extracted_params={'app': app}
            ))

        # ==================== NOTIFICATIONS ====================
        notify_signals = [
            'send notification', 'notify me', 'show notification',
            'desktop notification', 'alert me', 'pop up'
        ]
        if any(sig in msg_lower for sig in notify_signals):
            intents.append(ToolIntent(
                tool_name='send_notification',
                confidence=0.90,
                priority=self.PRIORITY_LOW,
                reason="notification signal detected",
                extracted_params={'title': 'Blue', 'message': msg_lower}
            ))

        return intents

    def _detect_calendar_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect calendar and event intents.
        """
        intents = []

        # ==================== CREATE EVENT ====================
        create_signals = [
            'create event', 'add event', 'schedule', 'book',
            'add to calendar', 'calendar event', 'set up meeting',
            'schedule meeting', 'schedule appointment', 'make appointment',
            'remind me on', 'add reminder for'
        ]
        if any(sig in msg_lower for sig in create_signals):
            intents.append(ToolIntent(
                tool_name='create_event',
                confidence=0.94,
                priority=self.PRIORITY_MEDIUM,
                reason="calendar event creation signal detected",
                extracted_params={}
            ))

        # ==================== LIST EVENTS ====================
        list_signals = [
            'what events', 'show events', 'list events', 'my calendar',
            "what's on my calendar", "what is on my calendar",
            'upcoming events', 'schedule for', 'calendar for',
            'events today', 'events tomorrow', 'events this week',
            "what's scheduled", "what is scheduled"
        ]
        if any(sig in msg_lower for sig in list_signals):
            intents.append(ToolIntent(
                tool_name='list_events',
                confidence=0.93,
                priority=self.PRIORITY_MEDIUM,
                reason="calendar list signal detected",
                extracted_params={}
            ))

        # ==================== SEARCH EVENTS ====================
        if 'find event' in msg_lower or 'search calendar' in msg_lower or 'search events' in msg_lower:
            intents.append(ToolIntent(
                tool_name='search_events',
                confidence=0.92,
                priority=self.PRIORITY_MEDIUM,
                reason="calendar search signal detected",
                extracted_params={}
            ))

        return intents

    def _detect_weather_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect weather-related intents (enhanced version).
        """
        intents = []

        # ==================== CURRENT WEATHER ====================
        current_signals = [
            'weather', 'temperature', 'how hot', 'how cold',
            'is it raining', 'is it sunny', 'is it snowing',
            "what's the weather", "what is the weather",
            'weather like', 'weather today', 'current weather'
        ]
        if any(sig in msg_lower for sig in current_signals) and 'forecast' not in msg_lower:
            intents.append(ToolIntent(
                tool_name='get_weather',
                confidence=0.95,
                priority=self.PRIORITY_MEDIUM,
                reason="current weather signal detected",
                extracted_params={}
            ))

        # ==================== WEATHER FORECAST ====================
        forecast_signals = [
            'forecast', 'weather this week', 'weather tomorrow',
            'weather next', 'upcoming weather', 'weather for',
            'will it rain', 'going to rain', 'should i bring umbrella'
        ]
        if any(sig in msg_lower for sig in forecast_signals):
            intents.append(ToolIntent(
                tool_name='get_forecast',
                confidence=0.94,
                priority=self.PRIORITY_MEDIUM,
                reason="weather forecast signal detected",
                extracted_params={}
            ))

        return intents

    def _detect_automation_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect automation and routine intents.
        """
        intents = []

        # ==================== EXECUTE ROUTINE ====================
        routine_names = [
            'good morning', 'bedtime', 'focus mode', 'party mode',
            'work mode', 'relax', 'sleep', 'wake up'
        ]
        if any(routine in msg_lower for routine in routine_names):
            intents.append(ToolIntent(
                tool_name='execute_routine',
                confidence=0.93,
                priority=self.PRIORITY_MEDIUM,
                reason="routine execution signal detected",
                extracted_params={}
            ))

        # ==================== CREATE ROUTINE ====================
        create_routine_signals = [
            'create routine', 'new routine', 'add routine',
            'make routine', 'set up routine', 'automate'
        ]
        if any(sig in msg_lower for sig in create_routine_signals):
            intents.append(ToolIntent(
                tool_name='create_routine',
                confidence=0.91,
                priority=self.PRIORITY_LOW,
                reason="routine creation signal detected",
                extracted_params={}
            ))

        # ==================== LIST ROUTINES ====================
        if 'show routines' in msg_lower or 'list routines' in msg_lower or 'my routines' in msg_lower:
            intents.append(ToolIntent(
                tool_name='list_routines',
                confidence=0.90,
                priority=self.PRIORITY_LOW,
                reason="routine list signal detected",
                extracted_params={}
            ))

        return intents

    def _detect_media_library_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect media library intents (podcasts, audiobooks).
        """
        intents = []

        # ==================== SUBSCRIBE ====================
        subscribe_signals = [
            'subscribe to podcast', 'add podcast', 'follow podcast',
            'subscribe to', 'add to library', 'follow'
        ]
        if any(sig in msg_lower for sig in subscribe_signals) and 'podcast' in msg_lower:
            intents.append(ToolIntent(
                tool_name='subscribe_podcast',
                confidence=0.94,
                priority=self.PRIORITY_MEDIUM,
                reason="podcast subscription signal detected",
                extracted_params={}
            ))

        # ==================== LIST SUBSCRIPTIONS ====================
        list_sub_signals = [
            'my podcasts', 'show podcasts', 'list podcasts',
            'podcast library', 'subscriptions', 'subscribed to'
        ]
        if any(sig in msg_lower for sig in list_sub_signals):
            intents.append(ToolIntent(
                tool_name='list_subscriptions',
                confidence=0.92,
                priority=self.PRIORITY_MEDIUM,
                reason="podcast list signal detected",
                extracted_params={}
            ))

        # ==================== LIST EPISODES ====================
        if 'episodes' in msg_lower or 'new episodes' in msg_lower:
            intents.append(ToolIntent(
                tool_name='list_episodes',
                confidence=0.90,
                priority=self.PRIORITY_MEDIUM,
                reason="episode list signal detected",
                extracted_params={}
            ))

        # ==================== SEARCH MEDIA ====================
        if 'search podcast' in msg_lower or 'find podcast' in msg_lower or 'search episodes' in msg_lower:
            intents.append(ToolIntent(
                tool_name='search_media',
                confidence=0.91,
                priority=self.PRIORITY_MEDIUM,
                reason="media search signal detected",
                extracted_params={}
            ))

        return intents

    def _detect_location_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect location/places management intents.
        """
        intents = []

        # ==================== ADD LOCATION ====================
        add_signals = [
            'save location', 'add location', 'save place', 'add place',
            'remember this place', 'save this address', 'add address'
        ]
        if any(sig in msg_lower for sig in add_signals):
            intents.append(ToolIntent(
                tool_name='add_location',
                confidence=0.93,
                priority=self.PRIORITY_MEDIUM,
                reason="location save signal detected",
                extracted_params={}
            ))

        # ==================== LIST/SEARCH LOCATIONS ====================
        list_signals = [
            'my locations', 'my places', 'saved locations', 'saved places',
            'show locations', 'show places', 'list locations', 'list places'
        ]
        if any(sig in msg_lower for sig in list_signals):
            intents.append(ToolIntent(
                tool_name='list_locations',
                confidence=0.92,
                priority=self.PRIORITY_MEDIUM,
                reason="location list signal detected",
                extracted_params={}
            ))

        if 'find location' in msg_lower or 'search places' in msg_lower or 'search locations' in msg_lower:
            intents.append(ToolIntent(
                tool_name='search_locations',
                confidence=0.91,
                priority=self.PRIORITY_MEDIUM,
                reason="location search signal detected",
                extracted_params={}
            ))

        return intents

    def _detect_contact_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect contact management intents.
        """
        intents = []

        # ==================== ADD CONTACT ====================
        add_signals = [
            'add contact', 'new contact', 'save contact',
            'add person', 'save person', 'remember person'
        ]
        if any(sig in msg_lower for sig in add_signals):
            intents.append(ToolIntent(
                tool_name='add_contact',
                confidence=0.94,
                priority=self.PRIORITY_MEDIUM,
                reason="contact add signal detected",
                extracted_params={}
            ))

        # ==================== LIST/SEARCH CONTACTS ====================
        list_signals = [
            'my contacts', 'show contacts', 'list contacts',
            'contact list', 'address book'
        ]
        if any(sig in msg_lower for sig in list_signals):
            intents.append(ToolIntent(
                tool_name='list_contacts',
                confidence=0.92,
                priority=self.PRIORITY_MEDIUM,
                reason="contact list signal detected",
                extracted_params={}
            ))

        if 'find contact' in msg_lower or 'search contacts' in msg_lower:
            intents.append(ToolIntent(
                tool_name='search_contacts',
                confidence=0.91,
                priority=self.PRIORITY_MEDIUM,
                reason="contact search signal detected",
                extracted_params={}
            ))

        # ==================== BIRTHDAYS ====================
        birthday_signals = [
            'birthday', 'birthdays', 'upcoming birthdays', 'who has birthday'
        ]
        if any(sig in msg_lower for sig in birthday_signals):
            intents.append(ToolIntent(
                tool_name='upcoming_birthdays',
                confidence=0.93,
                priority=self.PRIORITY_MEDIUM,
                reason="birthday query detected",
                extracted_params={}
            ))

        return intents

    def _detect_habit_intents(
        self,
        msg_lower: str,
        context: Dict
    ) -> List[ToolIntent]:
        """
        Detect habit tracking intents.
        """
        intents = []

        # ==================== CREATE HABIT ====================
        create_signals = [
            'track habit', 'new habit', 'add habit', 'create habit',
            'start tracking', 'track daily'
        ]
        if any(sig in msg_lower for sig in create_signals):
            intents.append(ToolIntent(
                tool_name='create_habit',
                confidence=0.93,
                priority=self.PRIORITY_MEDIUM,
                reason="habit creation signal detected",
                extracted_params={}
            ))

        # ==================== COMPLETE HABIT ====================
        complete_signals = [
            'complete habit', 'done with', 'finished', 'mark done',
            'did my', 'completed'
        ]
        habit_words = ['habit', 'exercise', 'meditation', 'reading', 'workout']
        has_complete = any(sig in msg_lower for sig in complete_signals)
        has_habit_word = any(word in msg_lower for word in habit_words)

        if has_complete and has_habit_word:
            intents.append(ToolIntent(
                tool_name='complete_habit',
                confidence=0.92,
                priority=self.PRIORITY_MEDIUM,
                reason="habit completion signal detected",
                extracted_params={}
            ))

        # ==================== LIST/CHECK HABITS ====================
        list_signals = [
            'my habits', 'show habits', 'list habits', 'habit list',
            'what habits', 'habits today', 'check habits'
        ]
        if any(sig in msg_lower for sig in list_signals):
            intents.append(ToolIntent(
                tool_name='list_habits',
                confidence=0.91,
                priority=self.PRIORITY_MEDIUM,
                reason="habit list signal detected",
                extracted_params={}
            ))

        # ==================== HABIT STATS ====================
        if 'habit' in msg_lower and any(w in msg_lower for w in ['streak', 'progress', 'stats', 'statistics']):
            intents.append(ToolIntent(
                tool_name='habit_stats',
                confidence=0.90,
                priority=self.PRIORITY_LOW,
                reason="habit statistics signal detected",
                extracted_params={}
            ))

        return intents

    # ================================================================================
    # DISAMBIGUATION
    # ================================================================================

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
            'create_reminder': 'create a reminder',
            # Notes & Tasks
            'create_note': 'create a new note',
            'search_notes': 'search your notes',
            'create_task': 'add a task to your list',
            'list_tasks': 'show your tasks',
            'complete_task': 'mark a task as done',
            'add_to_list': 'add something to a list',
            'get_list': 'show a list',
            # System
            'get_clipboard': 'check your clipboard',
            'set_clipboard': 'copy something',
            'take_screenshot': 'take a screenshot',
            'set_volume': 'adjust the volume',
            'launch_application': 'open an application',
            'send_notification': 'send a notification',
            # Recognition
            'capture_and_recognize': 'look and recognize who\'s here',
            'recognize_image': 'identify people in an image',
            'teach_person': 'learn to recognize someone',
            'teach_place': 'learn to recognize a place',
            'who_do_i_know': 'show who I can recognize',
            'where_do_i_know': 'show places I recognize',
            'forget_person': 'forget how to recognize someone',
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

    # ================================================================================
    # PARAMETER EXTRACTION HELPERS
    # ================================================================================

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
        moods = list(MOOD_PRESETS.keys()) if MOOD_PRESETS else [
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


# ================================================================================
# INTEGRATION FUNCTION
# ================================================================================

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


# ================================================================================
# EXPORTS
# ================================================================================

__all__ = [
    'ToolIntent',
    'ToolSelectionResult',
    'ImprovedToolSelector',
    'integrate_with_existing_system',
    'fuzzy_match',
    'normalize_artist_name',
]
