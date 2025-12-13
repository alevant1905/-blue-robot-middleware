"""
Blue Robot Enhanced Tool Selection - v2.0
==========================================

MAJOR IMPROVEMENTS over v1:
1. Semantic Tool Profiles - Each tool has a rich description of capabilities
2. Example-Based Matching - Learn from example phrases for each tool
3. Verb-Object Intent Parsing - Understand what action on what target
4. Capability Scoring - Match user intent to tool capabilities
5. Smarter Disambiguation - Ask targeted questions when uncertain
6. Negative Examples - Know when NOT to use a tool
7. Slot Extraction - Better parameter extraction

Architecture:
- ToolProfile: Comprehensive definition of what a tool can do
- IntentParser: Extract verb, object, modifiers from user message
- CapabilityMatcher: Score tools against parsed intent
- DisambiguationEngine: Generate helpful clarifying questions
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import Counter


# ================================================================================
# DATA CLASSES
# ================================================================================

@dataclass
class ToolProfile:
    """Rich profile of a tool's capabilities for better matching."""
    name: str
    category: str  # email, music, lights, search, etc.
    description: str  # Human-readable description
    capabilities: List[str]  # What this tool can do
    example_phrases: List[str]  # Example user inputs
    negative_examples: List[str]  # When NOT to use this tool
    required_entities: List[str]  # What info is needed (email, time, etc.)
    verbs: List[str]  # Action verbs associated with this tool
    objects: List[str]  # Objects/nouns associated with this tool
    priority: int = 3  # Lower = higher priority


@dataclass
class ParsedIntent:
    """Structured representation of user intent."""
    original_message: str
    verb: Optional[str]  # play, send, check, turn on, etc.
    verb_normalized: Optional[str]  # Canonical form of verb
    object: Optional[str]  # music, email, lights, etc.
    target: Optional[str]  # Recipient, song name, etc.
    modifiers: List[str]  # Adjectives, adverbs
    entities: Dict[str, Any]  # Extracted entities (emails, times, etc.)
    question_type: Optional[str]  # what, how, when, where, etc.
    is_command: bool  # Is this a command or a question?
    is_follow_up: bool  # Is this continuing a conversation?


@dataclass
class ToolMatch:
    """Result of matching a tool to an intent."""
    tool_name: str
    confidence: float
    match_reasons: List[str]
    negative_reasons: List[str]
    extracted_params: Dict[str, Any]
    capability_scores: Dict[str, float]  # Which capabilities matched


@dataclass
class SelectionResult:
    """Final result of tool selection."""
    primary_tool: Optional[ToolMatch]
    alternatives: List[ToolMatch]
    needs_disambiguation: bool
    disambiguation_question: Optional[str]
    disambiguation_options: List[str]
    is_compound: bool
    parsed_intent: ParsedIntent


# ================================================================================
# TOOL PROFILES - The heart of semantic matching
# ================================================================================

TOOL_PROFILES: Dict[str, ToolProfile] = {
    # ==================== EMAIL TOOLS ====================
    "read_gmail": ToolProfile(
        name="read_gmail",
        category="email",
        description="Read, check, and view emails from Gmail inbox",
        capabilities=[
            "check inbox for new emails",
            "read unread messages",
            "show recent emails",
            "find emails from specific senders",
            "search emails by subject or content",
            "count unread messages",
            "list emails by date"
        ],
        example_phrases=[
            "check my email",
            "any new emails?",
            "show me my inbox",
            "what emails do I have?",
            "read my messages",
            "check my inbox",
            "do I have any unread emails?",
            "show emails from John",
            "find emails about the project",
            "what did Sarah send me?"
        ],
        negative_examples=[
            "send an email",
            "write to someone",
            "reply to that",
            "compose a message",
            "email John about the meeting"
        ],
        required_entities=[],
        verbs=["check", "read", "show", "see", "view", "look at", "open", "get", "find", "search"],
        objects=["email", "emails", "inbox", "messages", "mail", "gmail"],
        priority=1
    ),

    "send_gmail": ToolProfile(
        name="send_gmail",
        category="email",
        description="Compose and send new emails",
        capabilities=[
            "send new emails",
            "compose messages",
            "email someone",
            "write and send messages",
            "contact someone via email",
            "need to email someone"
        ],
        example_phrases=[
            "send an email to john@example.com",
            "email Sarah about the meeting",
            "write to my boss",
            "compose an email",
            "send a message to the team",
            "email John saying I'll be late",
            "shoot an email to marketing",
            "I need to email someone",
            "I want to send an email",
            "help me write an email",
            "draft an email"
        ],
        negative_examples=[
            "check my email",
            "read my inbox",
            "reply to that email",
            "what emails do I have?",
            "respond to that",
            "answer that email"
        ],
        required_entities=["recipient"],
        verbs=["send", "email", "write", "compose", "message", "contact", "shoot", "draft", "need to email"],
        objects=["email", "message", "mail", "someone"],
        priority=1
    ),

    "reply_gmail": ToolProfile(
        name="reply_gmail",
        category="email",
        description="Reply to existing emails",
        capabilities=[
            "reply to emails",
            "respond to messages",
            "answer emails",
            "reply all",
            "send responses"
        ],
        example_phrases=[
            "reply to that email",
            "respond to John's message",
            "answer that",
            "reply saying thanks",
            "send a reply",
            "respond to the last email"
        ],
        negative_examples=[
            "check my email",
            "send a new email",
            "compose a message"
        ],
        required_entities=["email_to_reply_to"],
        verbs=["reply", "respond", "answer"],
        objects=["email", "message", "that"],
        priority=1
    ),

    # ==================== MUSIC TOOLS ====================
    "play_music": ToolProfile(
        name="play_music",
        category="music",
        description="Play music, songs, artists, genres, or playlists",
        capabilities=[
            "play songs and music",
            "play specific artists",
            "play genres like jazz, rock, pop",
            "play playlists",
            "queue up music",
            "start playing tracks",
            "shuffle music",
            "play albums"
        ],
        example_phrases=[
            "play some jazz",
            "put on the Beatles",
            "play relaxing music",
            "play my workout playlist",
            "play something upbeat",
            "put on some rock",
            "play Taylor Swift",
            "play lo-fi beats",
            "put on some background music",
            "play the new Drake album",
            "shuffle my favorites"
        ],
        negative_examples=[
            "stop the music",
            "pause",
            "skip this song",
            "turn up the volume",
            "what song is this?",
            "next track"
        ],
        required_entities=[],
        verbs=["play", "put on", "start", "queue", "shuffle", "blast", "spin", "throw on", "crank"],
        objects=["music", "song", "songs", "artist", "band", "genre", "playlist", "album", "track", "tunes", "beats"],
        priority=2
    ),

    "control_music": ToolProfile(
        name="control_music",
        category="music",
        description="Control music playback: pause, resume, skip, volume",
        capabilities=[
            "pause music",
            "resume playback",
            "skip tracks",
            "go to previous track",
            "adjust volume",
            "stop music",
            "mute/unmute"
        ],
        example_phrases=[
            "pause the music",
            "stop",
            "skip this song",
            "next track",
            "previous song",
            "turn up the volume",
            "make it louder",
            "mute",
            "resume playing",
            "go back a song"
        ],
        negative_examples=[
            "play jazz",
            "put on some music",
            "play Taylor Swift"
        ],
        required_entities=[],
        verbs=["pause", "stop", "skip", "next", "previous", "resume", "mute", "unmute", "louder", "quieter", "turn up", "turn down"],
        objects=["music", "song", "track", "volume", "it", "this"],
        priority=2
    ),

    "music_visualizer": ToolProfile(
        name="music_visualizer",
        category="music",
        description="Start music visualizer with synchronized lights",
        capabilities=[
            "sync lights to music",
            "create light show",
            "music visualization",
            "disco mode",
            "party lights"
        ],
        example_phrases=[
            "start the visualizer",
            "sync lights to music",
            "do a light show",
            "disco mode",
            "party lights",
            "make the lights dance",
            "music visualization"
        ],
        negative_examples=[
            "play music",
            "turn on the lights",
            "set lights to blue"
        ],
        required_entities=[],
        verbs=["start", "sync", "visualize", "dance"],
        objects=["visualizer", "light show", "disco", "lights with music"],
        priority=2
    ),

    # ==================== LIGHT TOOLS ====================
    "control_lights": ToolProfile(
        name="control_lights",
        category="lights",
        description="Control smart lights: on/off, colors, brightness, moods",
        capabilities=[
            "turn lights on/off",
            "change light color",
            "adjust brightness",
            "set light moods/scenes",
            "dim lights",
            "set specific room lights"
        ],
        example_phrases=[
            "turn on the lights",
            "set lights to blue",
            "dim the lights",
            "set romantic lighting",
            "turn off bedroom lights",
            "make it brighter",
            "set sunset mood",
            "lights to 50%",
            "cozy lighting please",
            "turn the lights red"
        ],
        negative_examples=[
            "sync lights to music",
            "light show",
            "disco mode"
        ],
        required_entities=[],
        verbs=["turn on", "turn off", "set", "dim", "brighten", "change", "make"],
        objects=["lights", "light", "lamp", "lamps", "lighting", "brightness"],
        priority=3
    ),

    # ==================== SEARCH TOOLS ====================
    "web_search": ToolProfile(
        name="web_search",
        category="search",
        description="Search the web for information, news, facts",
        capabilities=[
            "search the internet",
            "find information online",
            "look up facts",
            "search for news",
            "find websites",
            "research topics"
        ],
        example_phrases=[
            "search for AI news",
            "look up the weather in Paris",
            "find information about quantum computing",
            "search for recipes",
            "what's the latest news?",
            "google how to make pasta",
            "search the web for Python tutorials"
        ],
        negative_examples=[
            "search my documents",
            "find that contract",
            "look in my files"
        ],
        required_entities=["query"],
        verbs=["search", "google", "look up", "find", "research"],
        objects=["web", "internet", "online", "news", "information"],
        priority=4
    ),

    "search_documents": ToolProfile(
        name="search_documents",
        category="search",
        description="Search personal documents and files",
        capabilities=[
            "search documents",
            "find files",
            "look up contracts",
            "search notes",
            "find PDFs",
            "search personal files"
        ],
        example_phrases=[
            "search my documents for contract",
            "find the project proposal",
            "look for that PDF",
            "search my files",
            "find the agreement document",
            "where's my resume?",
            "find documents about taxes"
        ],
        negative_examples=[
            "search the web",
            "google something",
            "look up news"
        ],
        required_entities=["query"],
        verbs=["search", "find", "look for", "locate", "get"],
        objects=["document", "documents", "file", "files", "PDF", "contract", "agreement", "notes"],
        priority=4
    ),

    # ==================== WEATHER TOOLS ====================
    "get_weather": ToolProfile(
        name="get_weather",
        category="weather",
        description="Get weather information and forecasts",
        capabilities=[
            "get current weather",
            "weather forecast",
            "check temperature",
            "rain prediction",
            "weather by location",
            "temperature outside",
            "how hot or cold it is"
        ],
        example_phrases=[
            "what's the weather?",
            "will it rain today?",
            "temperature outside",
            "weather forecast",
            "weather in New York",
            "is it going to snow?",
            "how hot is it?",
            "how hot is it outside?",
            "how cold is it outside?",
            "what's the weather like tomorrow?",
            "what's it like outside?",
            "is it cold out?",
            "is it warm today?"
        ],
        negative_examples=[
            "turn up the heat",
            "make it warmer",
            "too hot in here"
        ],
        required_entities=[],
        verbs=["check", "get", "what's", "how", "will", "is"],
        objects=["weather", "temperature", "rain", "snow", "forecast", "outside", "out", "hot", "cold", "warm"],
        priority=3
    ),

    # ==================== TIMER/REMINDER TOOLS ====================
    "set_timer": ToolProfile(
        name="set_timer",
        category="timer",
        description="Set timers for specific durations",
        capabilities=[
            "set countdown timers",
            "create timers",
            "alarm after duration"
        ],
        example_phrases=[
            "set a timer for 10 minutes",
            "timer for 1 hour",
            "5 minute timer",
            "set an alarm for 30 minutes",
            "countdown 15 minutes"
        ],
        negative_examples=[
            "remind me tomorrow",
            "set a reminder",
            "remember to call John"
        ],
        required_entities=["duration"],
        verbs=["set", "start", "create"],
        objects=["timer", "countdown", "alarm"],
        priority=1
    ),

    "create_reminder": ToolProfile(
        name="create_reminder",
        category="reminder",
        description="Set reminders for specific times or events",
        capabilities=[
            "set reminders",
            "remind at specific time",
            "remind about tasks",
            "schedule reminders"
        ],
        example_phrases=[
            "remind me to call John at 3pm",
            "set a reminder for the meeting",
            "remind me tomorrow to pay bills",
            "remind me in 2 hours",
            "don't let me forget to buy milk"
        ],
        negative_examples=[
            "set a 10 minute timer",
            "timer for cooking"
        ],
        required_entities=["reminder_text"],
        verbs=["remind", "remember", "don't forget", "alert"],
        objects=["reminder", "me", "about"],
        priority=1
    ),

    # ==================== CAMERA/VISION TOOLS ====================
    "capture_camera": ToolProfile(
        name="capture_camera",
        category="vision",
        description="Capture images from camera and describe what's seen",
        capabilities=[
            "take photos",
            "capture camera",
            "see surroundings",
            "describe what's visible",
            "look around"
        ],
        example_phrases=[
            "what do you see?",
            "take a picture",
            "look around",
            "what's in front of you?",
            "capture an image",
            "show me what you see",
            "what's happening?",
            "describe what you see"
        ],
        negative_examples=[
            "show me the photo I uploaded",
            "view that image",
            "analyze the screenshot"
        ],
        required_entities=[],
        verbs=["see", "look", "capture", "take", "show", "describe"],
        objects=["camera", "photo", "picture", "around", "surroundings"],
        priority=1
    ),

    "view_image": ToolProfile(
        name="view_image",
        category="vision",
        description="View and analyze uploaded or existing images",
        capabilities=[
            "view uploaded images",
            "analyze photos",
            "describe screenshots",
            "examine pictures"
        ],
        example_phrases=[
            "show me the uploaded image",
            "view that photo",
            "analyze this screenshot",
            "what's in this picture?",
            "describe the image I sent"
        ],
        negative_examples=[
            "what do you see around?",
            "take a picture",
            "capture from camera"
        ],
        required_entities=["image_reference"],
        verbs=["view", "show", "analyze", "describe", "examine", "look at"],
        objects=["image", "photo", "picture", "screenshot", "uploaded"],
        priority=2
    ),

    # ==================== CALENDAR TOOLS ====================
    "create_event": ToolProfile(
        name="create_event",
        category="calendar",
        description="Create calendar events and appointments",
        capabilities=[
            "create events",
            "schedule appointments",
            "add to calendar",
            "book meetings"
        ],
        example_phrases=[
            "create an event for tomorrow",
            "schedule a meeting at 3pm",
            "add dentist appointment to calendar",
            "book lunch with John on Friday",
            "put meeting on my calendar"
        ],
        negative_examples=[
            "what's on my calendar?",
            "show my schedule",
            "when is the meeting?"
        ],
        required_entities=["event_title", "datetime"],
        verbs=["create", "schedule", "add", "book", "put"],
        objects=["event", "meeting", "appointment", "calendar"],
        priority=2
    ),

    "list_events": ToolProfile(
        name="list_events",
        category="calendar",
        description="Show calendar events and schedule",
        capabilities=[
            "show calendar",
            "list events",
            "view schedule",
            "check appointments"
        ],
        example_phrases=[
            "what's on my calendar?",
            "show my schedule",
            "any meetings today?",
            "what events do I have this week?",
            "am I free tomorrow?"
        ],
        negative_examples=[
            "create an event",
            "schedule a meeting",
            "add to calendar"
        ],
        required_entities=[],
        verbs=["show", "list", "view", "check", "what"],
        objects=["calendar", "schedule", "events", "meetings", "appointments"],
        priority=3
    ),

    # ==================== NOTES/TASKS TOOLS ====================
    "create_note": ToolProfile(
        name="create_note",
        category="notes",
        description="Create and save notes",
        capabilities=[
            "create notes",
            "save information",
            "jot down thoughts",
            "write notes"
        ],
        example_phrases=[
            "create a note about the meeting",
            "save this: project deadline is Friday",
            "note: call John tomorrow",
            "write a note about ideas",
            "jot this down"
        ],
        negative_examples=[
            "find my notes",
            "show notes about project"
        ],
        required_entities=["note_content"],
        verbs=["create", "make", "save", "note", "jot", "write"],
        objects=["note", "notes", "this", "down"],
        priority=3
    ),

    "search_notes": ToolProfile(
        name="search_notes",
        category="notes",
        description="Search and retrieve notes",
        capabilities=[
            "search notes",
            "find notes",
            "show saved notes",
            "retrieve information"
        ],
        example_phrases=[
            "find my notes about the project",
            "search notes for meeting summary",
            "show notes from yesterday",
            "what notes do I have about taxes?"
        ],
        negative_examples=[
            "create a note",
            "save this",
            "jot down"
        ],
        required_entities=["query"],
        verbs=["search", "find", "show", "get", "retrieve"],
        objects=["notes", "note", "my notes"],
        priority=3
    ),

    "create_task": ToolProfile(
        name="create_task",
        category="tasks",
        description="Create tasks and to-do items",
        capabilities=[
            "add tasks",
            "create to-dos",
            "add to task list",
            "create action items"
        ],
        example_phrases=[
            "add task: buy groceries",
            "create a to-do to call mom",
            "remind me to finish the report",
            "add to my task list",
            "I need to buy milk"
        ],
        negative_examples=[
            "show my tasks",
            "what tasks do I have?",
            "complete task"
        ],
        required_entities=["task_title"],
        verbs=["add", "create", "need to", "have to", "must"],
        objects=["task", "todo", "to-do", "item", "action"],
        priority=3
    ),

    "list_tasks": ToolProfile(
        name="list_tasks",
        category="tasks",
        description="Show tasks and to-do list",
        capabilities=[
            "show tasks",
            "list to-dos",
            "view task list",
            "check pending items"
        ],
        example_phrases=[
            "show my tasks",
            "what do I need to do?",
            "list my to-dos",
            "what's on my task list?",
            "pending tasks"
        ],
        negative_examples=[
            "add a task",
            "create to-do",
            "complete task"
        ],
        required_entities=[],
        verbs=["show", "list", "view", "what", "check"],
        objects=["tasks", "todos", "to-dos", "list", "pending"],
        priority=3
    ),

    # ==================== UTILITY TOOLS ====================
    "get_time": ToolProfile(
        name="get_time",
        category="utility",
        description="Get current time",
        capabilities=["tell time", "current time"],
        example_phrases=[
            "what time is it?",
            "current time",
            "tell me the time"
        ],
        negative_examples=[],
        required_entities=[],
        verbs=["what", "tell", "get"],
        objects=["time"],
        priority=1
    ),

    "get_date": ToolProfile(
        name="get_date",
        category="utility",
        description="Get current date",
        capabilities=["tell date", "current date", "what day"],
        example_phrases=[
            "what's the date?",
            "what day is it?",
            "today's date"
        ],
        negative_examples=[],
        required_entities=[],
        verbs=["what", "tell", "get"],
        objects=["date", "day", "today"],
        priority=1
    ),

    "calculate": ToolProfile(
        name="calculate",
        category="utility",
        description="Perform calculations",
        capabilities=["math", "calculate", "compute"],
        example_phrases=[
            "calculate 15% of 200",
            "what's 5 + 3?",
            "multiply 7 by 8",
            "square root of 144"
        ],
        negative_examples=[],
        required_entities=["expression"],
        verbs=["calculate", "compute", "what's", "multiply", "divide", "add", "subtract"],
        objects=["calculation", "math", "number"],
        priority=1
    ),

    "generate_random": ToolProfile(
        name="generate_random",
        category="utility",
        description="Generate random numbers, flip coins, roll dice",
        capabilities=[
            "flip coins",
            "roll dice",
            "random numbers",
            "pick randomly"
        ],
        example_phrases=[
            "flip a coin",
            "roll a die",
            "random number between 1 and 100",
            "pick a number",
            "roll d20"
        ],
        negative_examples=[],
        required_entities=[],
        verbs=["flip", "roll", "generate", "pick", "choose"],
        objects=["coin", "dice", "die", "number", "random"],
        priority=2
    ),

    "get_clipboard": ToolProfile(
        name="get_clipboard",
        category="system",
        description="Get clipboard contents",
        capabilities=["read clipboard", "show copied text"],
        example_phrases=[
            "what's in my clipboard?",
            "show clipboard",
            "what did I copy?"
        ],
        negative_examples=[
            "copy this to clipboard"
        ],
        required_entities=[],
        verbs=["show", "get", "what's", "read"],
        objects=["clipboard", "copied"],
        priority=2
    ),

    "take_screenshot": ToolProfile(
        name="take_screenshot",
        category="system",
        description="Take a screenshot",
        capabilities=["capture screen", "screenshot"],
        example_phrases=[
            "take a screenshot",
            "capture my screen",
            "screenshot this"
        ],
        negative_examples=[],
        required_entities=[],
        verbs=["take", "capture", "screenshot"],
        objects=["screenshot", "screen"],
        priority=2
    ),

    # ==================== CONTACTS TOOLS ====================
    "search_contacts": ToolProfile(
        name="search_contacts",
        category="contacts",
        description="Search and find contacts",
        capabilities=[
            "find contacts",
            "look up phone numbers",
            "find email addresses",
            "search address book"
        ],
        example_phrases=[
            "find John's number",
            "what's Sarah's email?",
            "look up my dentist's contact",
            "find contact for Dr. Smith"
        ],
        negative_examples=[
            "add a contact",
            "create new contact"
        ],
        required_entities=["name_or_query"],
        verbs=["find", "search", "look up", "get", "what's"],
        objects=["contact", "number", "email", "phone", "address"],
        priority=3
    ),

    # ==================== HABITS TOOLS ====================
    "log_habit": ToolProfile(
        name="log_habit",
        category="habits",
        description="Track and log habits",
        capabilities=[
            "track habits",
            "log activities",
            "mark habits done",
            "record routines"
        ],
        example_phrases=[
            "I exercised today",
            "log that I meditated",
            "mark workout done",
            "I drank 8 glasses of water"
        ],
        negative_examples=[
            "show my habits",
            "habit streak"
        ],
        required_entities=["habit_name"],
        verbs=["log", "track", "mark", "record", "did"],
        objects=["habit", "exercise", "workout", "meditation"],
        priority=3
    ),

    "get_habits": ToolProfile(
        name="get_habits",
        category="habits",
        description="View habit tracking and streaks",
        capabilities=[
            "show habits",
            "view streaks",
            "check habit progress"
        ],
        example_phrases=[
            "show my habits",
            "how's my streak?",
            "habit progress",
            "how many days have I worked out?"
        ],
        negative_examples=[
            "log workout",
            "mark habit done"
        ],
        required_entities=[],
        verbs=["show", "check", "how", "view"],
        objects=["habits", "streak", "progress"],
        priority=3
    ),
}


# ================================================================================
# VERB NORMALIZATION - Map variations to canonical forms
# ================================================================================

VERB_ALIASES = {
    # Play/Start
    "play": ["put on", "throw on", "blast", "spin", "crank", "queue", "start playing"],
    "start": ["begin", "launch", "initiate", "turn on", "activate"],
    "stop": ["pause", "halt", "end", "quit", "kill", "terminate"],

    # Check/Read
    "check": ["read", "view", "show", "see", "look at", "open", "get", "display"],
    "search": ["find", "look for", "look up", "locate", "search for", "google"],

    # Send/Write
    "send": ["email", "message", "contact", "write to", "shoot"],
    "reply": ["respond", "answer", "write back"],

    # Control
    "turn on": ["switch on", "enable", "activate", "light up"],
    "turn off": ["switch off", "disable", "deactivate", "shut off"],
    "set": ["change", "make", "adjust", "configure", "put"],

    # Create
    "create": ["make", "add", "new", "write", "compose"],
    "delete": ["remove", "erase", "clear", "cancel"],

    # Remember
    "remind": ["remember", "don't forget", "alert me"],
}

def normalize_verb(verb: str) -> str:
    """Convert verb variations to canonical form."""
    verb_lower = verb.lower().strip()

    for canonical, aliases in VERB_ALIASES.items():
        if verb_lower == canonical or verb_lower in aliases:
            return canonical
        # Check if verb starts with any alias
        for alias in aliases:
            if verb_lower.startswith(alias):
                return canonical

    return verb_lower


# ================================================================================
# INTENT PARSER - Extract structured intent from natural language
# ================================================================================

class IntentParser:
    """Parse user messages into structured intents."""

    # Question words
    QUESTION_WORDS = {'what', 'how', 'when', 'where', 'who', 'which', 'why', 'can', 'could', 'would', 'will', 'is', 'are', 'do', 'does', 'did'}

    # Compound connectors
    COMPOUND_CONNECTORS = [' and then ', ' then ', ' and also ', ' also ', ' and ', ' plus ', ' after that ']

    def parse(self, message: str, context: Optional[Dict] = None) -> ParsedIntent:
        """Parse message into structured intent."""
        msg_lower = message.lower().strip()

        # Check for question type
        question_type = self._detect_question_type(msg_lower)
        is_command = question_type is None and not msg_lower.endswith('?')

        # Extract verb and object
        verb, verb_normalized = self._extract_verb(msg_lower)
        obj = self._extract_object(msg_lower, verb)

        # Extract target (recipient, song name, etc.)
        target = self._extract_target(msg_lower)

        # Extract modifiers
        modifiers = self._extract_modifiers(msg_lower)

        # Extract entities
        entities = self._extract_entities(msg_lower)

        # Check if follow-up
        is_follow_up = self._is_follow_up(msg_lower, context)

        return ParsedIntent(
            original_message=message,
            verb=verb,
            verb_normalized=verb_normalized,
            object=obj,
            target=target,
            modifiers=modifiers,
            entities=entities,
            question_type=question_type,
            is_command=is_command,
            is_follow_up=is_follow_up
        )

    def _detect_question_type(self, msg: str) -> Optional[str]:
        """Detect if message is a question and what type."""
        words = msg.split()
        if not words:
            return None

        first_word = words[0].lower()
        if first_word in self.QUESTION_WORDS:
            return first_word
        if msg.endswith('?'):
            return 'yes_no'
        return None

    def _extract_verb(self, msg: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract the main verb and its normalized form."""
        # Common verb patterns
        verb_patterns = [
            # Multi-word verbs first
            r'^(turn on|turn off|put on|look up|look for|look at|set up|sign up|log in|check out)\b',
            r'\b(turn on|turn off|put on|look up|look for|look at)\b',
            # Single word verbs
            r'^(play|check|read|send|search|find|show|get|set|create|add|make|open|close|start|stop|pause|resume|skip|next|previous|mute|unmute|remind|remember|take|capture|view|analyze|describe|tell|give|list|schedule|book|cancel|delete|remove)\b',
            r'^(what|how|when|where|who|can|could|would|will|is|are|do|does|did)\b.+?\b(see|hear|tell|show|give|make|do|get|find|play|send|check)\b',
        ]

        for pattern in verb_patterns:
            match = re.search(pattern, msg, re.IGNORECASE)
            if match:
                verb = match.group(1).lower()
                return verb, normalize_verb(verb)

        # Try to find any verb-like word
        common_verbs = ['play', 'check', 'read', 'send', 'search', 'find', 'show', 'get', 'set',
                       'create', 'add', 'open', 'start', 'stop', 'remind', 'take', 'view']
        for verb in common_verbs:
            if verb in msg:
                return verb, normalize_verb(verb)

        return None, None

    def _extract_object(self, msg: str, verb: Optional[str]) -> Optional[str]:
        """Extract the main object/noun of the action."""
        # Object patterns based on common tool targets
        object_patterns = [
            r'\b(email|emails|inbox|mail|messages?)\b',
            r'\b(music|song|songs|playlist|album|track|tunes)\b',
            r'\b(lights?|lamps?|lighting|brightness)\b',
            r'\b(weather|temperature|forecast|rain|snow)\b',
            r'\b(timer|timers|countdown|alarm)\b',
            r'\b(reminder|reminders)\b',
            r'\b(calendar|schedule|events?|appointments?|meetings?)\b',
            r'\b(notes?|tasks?|todos?|to-dos?)\b',
            r'\b(documents?|files?|pdf|contract)\b',
            r'\b(clipboard)\b',
            r'\b(screenshot|screen)\b',
            r'\b(camera|photo|picture|image)\b',
            r'\b(contacts?|phone number|address book)\b',
            r'\b(habits?|streak|workout|exercise)\b',
            r'\b(time|date|day)\b',
            r'\b(coin|dice|die|random)\b',
        ]

        for pattern in object_patterns:
            match = re.search(pattern, msg, re.IGNORECASE)
            if match:
                return match.group(1).lower()

        return None

    def _extract_target(self, msg: str) -> Optional[str]:
        """Extract target like recipient, song name, etc."""
        # Email address
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', msg)
        if email_match:
            return email_match.group(0)

        # "to [name]" pattern
        to_match = re.search(r'\bto\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', msg)
        if to_match:
            return to_match.group(1)

        # Artist/genre after "play"
        play_match = re.search(r'\bplay\s+(?:some\s+)?(.+?)(?:\s+(?:music|and|then)|$)', msg, re.IGNORECASE)
        if play_match:
            return play_match.group(1).strip()

        return None

    def _extract_modifiers(self, msg: str) -> List[str]:
        """Extract adjectives and adverbs."""
        modifiers = []

        # Common modifiers
        modifier_patterns = [
            r'\b(relaxing|upbeat|calm|energetic|soft|loud|quiet|romantic|cozy|bright|dim)\b',
            r'\b(new|unread|recent|old|latest|urgent|important)\b',
            r'\b(tomorrow|today|tonight|morning|afternoon|evening|night)\b',
        ]

        for pattern in modifier_patterns:
            matches = re.findall(pattern, msg, re.IGNORECASE)
            modifiers.extend([m.lower() for m in matches])

        return modifiers

    def _extract_entities(self, msg: str) -> Dict[str, Any]:
        """Extract specific entities like times, durations, etc."""
        entities = {}

        # Email addresses
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', msg)
        if emails:
            entities['emails'] = emails

        # Times (3pm, 15:00, etc.)
        times = re.findall(r'\b(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b', msg, re.IGNORECASE)
        if times:
            entities['times'] = times

        # Durations (10 minutes, 1 hour, etc.)
        duration_match = re.search(r'(\d+)\s*(minutes?|mins?|hours?|hrs?|seconds?|secs?)', msg, re.IGNORECASE)
        if duration_match:
            entities['duration'] = {
                'value': int(duration_match.group(1)),
                'unit': duration_match.group(2).lower()
            }

        # Percentages
        percent_match = re.search(r'(\d+)\s*%', msg)
        if percent_match:
            entities['percentage'] = int(percent_match.group(1))

        # Numbers
        numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', msg)
        if numbers:
            entities['numbers'] = [float(n) for n in numbers]

        return entities

    def _is_follow_up(self, msg: str, context: Optional[Dict]) -> bool:
        """Detect if this is a follow-up to previous conversation."""
        follow_up_indicators = [
            'that', 'this', 'it', 'them', 'those',
            'the same', 'another', 'more', 'again',
            'no, ', 'yes, ', 'actually', 'instead',
            'also', 'too', 'as well'
        ]

        if any(msg.startswith(ind) or f' {ind} ' in f' {msg} ' for ind in follow_up_indicators):
            return True

        # Very short messages often are follow-ups
        if len(msg.split()) <= 3 and context:
            return True

        return False


# ================================================================================
# CAPABILITY MATCHER - Score tools against parsed intent
# ================================================================================

class CapabilityMatcher:
    """Match user intent to tool capabilities."""

    def __init__(self):
        self.intent_parser = IntentParser()

    def match(
        self,
        intent: ParsedIntent,
        conversation_context: Optional[Dict] = None
    ) -> List[ToolMatch]:
        """Match intent against all tools and return ranked matches."""
        matches = []

        for tool_name, profile in TOOL_PROFILES.items():
            match = self._score_tool(intent, profile, conversation_context)
            if match.confidence > 0.1:  # Minimum threshold
                matches.append(match)

        # Sort by confidence (descending)
        matches.sort(key=lambda x: (-x.confidence, profile.priority))

        return matches

    def _score_tool(
        self,
        intent: ParsedIntent,
        profile: ToolProfile,
        context: Optional[Dict]
    ) -> ToolMatch:
        """Score how well a tool matches the intent."""
        scores = {}
        match_reasons = []
        negative_reasons = []

        msg_lower = intent.original_message.lower()

        # 1. Verb matching (0-0.3)
        verb_score = self._score_verb_match(intent, profile)
        scores['verb'] = verb_score
        if verb_score > 0.5:
            match_reasons.append(f"verb '{intent.verb}' matches")

        # 2. Object matching (0-0.3)
        obj_score = self._score_object_match(intent, profile)
        scores['object'] = obj_score
        if obj_score > 0.5:
            match_reasons.append(f"object '{intent.object}' matches")

        # 3. Example phrase matching (0-0.4)
        example_score = self._score_example_match(msg_lower, profile)
        scores['example'] = example_score
        if example_score > 0.5:
            match_reasons.append("similar to example phrases")

        # 4. Capability matching (0-0.3)
        capability_score = self._score_capability_match(msg_lower, profile)
        scores['capability'] = capability_score
        if capability_score > 0.5:
            match_reasons.append("matches tool capabilities")

        # 5. Negative example matching (-0.5-0)
        negative_score = self._score_negative_match(msg_lower, profile)
        scores['negative'] = negative_score
        if negative_score < -0.2:
            negative_reasons.append("matches negative examples")

        # 6. Entity matching (0-0.2)
        entity_score = self._score_entity_match(intent, profile)
        scores['entity'] = entity_score
        if entity_score > 0.3:
            match_reasons.append("required entities present")

        # 7. Context boost (0-0.15)
        context_score = self._score_context_match(intent, profile, context)
        scores['context'] = context_score
        if context_score > 0.1:
            match_reasons.append("matches conversation context")

        # Calculate weighted total - weights tuned for higher confidence on good matches
        raw_score = (
            verb_score * 0.25 +          # Verb match is important
            obj_score * 0.30 +           # Object match is very important
            example_score * 0.30 +       # Example similarity is key
            capability_score * 0.10 +    # Capability match
            negative_score +             # Negative penalties (already weighted)
            entity_score * 0.05          # Entity bonus
        )

        # Add context bonus on top
        total_score = raw_score + context_score

        # Apply confidence boost for strong matches
        # If multiple signals match, boost confidence
        match_count = sum(1 for s in [verb_score, obj_score, example_score] if s > 0.5)
        if match_count >= 2:
            total_score = min(1.0, total_score * 1.15)  # 15% boost for multi-signal matches

        # Clamp to 0-1
        total_score = max(0.0, min(1.0, total_score))

        # Extract parameters
        extracted_params = self._extract_params(intent, profile)

        return ToolMatch(
            tool_name=profile.name,
            confidence=total_score,
            match_reasons=match_reasons,
            negative_reasons=negative_reasons,
            extracted_params=extracted_params,
            capability_scores=scores
        )

    def _score_verb_match(self, intent: ParsedIntent, profile: ToolProfile) -> float:
        """Score verb match."""
        if not intent.verb:
            return 0.0

        verb = intent.verb.lower()
        verb_norm = intent.verb_normalized or verb

        # Exact match
        if verb in profile.verbs or verb_norm in profile.verbs:
            return 1.0

        # Partial match (verb contained in profile verbs)
        for profile_verb in profile.verbs:
            if verb in profile_verb or profile_verb in verb:
                return 0.7

        return 0.0

    def _score_object_match(self, intent: ParsedIntent, profile: ToolProfile) -> float:
        """Score object/noun match."""
        if not intent.object:
            # Check if message contains any profile objects
            msg_lower = intent.original_message.lower()
            for obj in profile.objects:
                if obj in msg_lower:
                    return 0.8
            return 0.0

        obj = intent.object.lower()

        # Exact match
        if obj in profile.objects:
            return 1.0

        # Partial match
        for profile_obj in profile.objects:
            if obj in profile_obj or profile_obj in obj:
                return 0.7

        return 0.0

    def _score_example_match(self, msg: str, profile: ToolProfile) -> float:
        """Score similarity to example phrases."""
        best_score = 0.0

        for example in profile.example_phrases:
            example_lower = example.lower()

            # Exact match
            if msg == example_lower:
                return 1.0

            # Substring match
            if msg in example_lower or example_lower in msg:
                score = min(len(msg), len(example_lower)) / max(len(msg), len(example_lower))
                best_score = max(best_score, score * 0.9)
                continue

            # Word overlap
            msg_words = set(msg.split())
            example_words = set(example_lower.split())
            overlap = len(msg_words & example_words)
            if overlap > 0:
                score = overlap / max(len(msg_words), len(example_words))
                best_score = max(best_score, score * 0.8)

        return best_score

    def _score_capability_match(self, msg: str, profile: ToolProfile) -> float:
        """Score match against tool capabilities."""
        best_score = 0.0

        for capability in profile.capabilities:
            cap_lower = capability.lower()

            # Word overlap
            msg_words = set(msg.split())
            cap_words = set(cap_lower.split())
            overlap = len(msg_words & cap_words)

            if overlap > 0:
                score = overlap / len(cap_words)
                best_score = max(best_score, score)

        return best_score

    def _score_negative_match(self, msg: str, profile: ToolProfile) -> float:
        """Score against negative examples (returns negative value)."""
        for negative in profile.negative_examples:
            neg_lower = negative.lower()

            if msg == neg_lower:
                return -0.5

            if neg_lower in msg or msg in neg_lower:
                return -0.3

            # Word overlap check
            msg_words = set(msg.split())
            neg_words = set(neg_lower.split())
            overlap = len(msg_words & neg_words)
            if overlap >= 2:
                return -0.2

        return 0.0

    def _score_entity_match(self, intent: ParsedIntent, profile: ToolProfile) -> float:
        """Score based on required entities being present."""
        if not profile.required_entities:
            return 0.1  # Small bonus if no entities required

        found_count = 0
        for entity in profile.required_entities:
            if entity in intent.entities:
                found_count += 1
            # Check if entity can be inferred from target
            elif entity == 'recipient' and intent.target:
                found_count += 1
            elif entity == 'query' and (intent.target or intent.modifiers):
                found_count += 0.5

        return found_count / len(profile.required_entities)

    def _score_context_match(
        self,
        intent: ParsedIntent,
        profile: ToolProfile,
        context: Optional[Dict]
    ) -> float:
        """Score based on conversation context."""
        if not context:
            return 0.0

        score = 0.0

        # Check if tool was recently used (continuation)
        recent_tools = context.get('recent_tools', [])
        if profile.name in recent_tools:
            score += 0.1

        # Check category match with recent context
        recent_category = context.get('recent_category')
        if recent_category == profile.category:
            score += 0.05

        # Follow-up boost
        if intent.is_follow_up:
            if profile.name in recent_tools:
                score += 0.1

        return min(0.15, score)

    def _extract_params(self, intent: ParsedIntent, profile: ToolProfile) -> Dict[str, Any]:
        """Extract parameters for the tool from the intent."""
        params = {}

        # Copy relevant entities
        for entity_name in profile.required_entities:
            if entity_name in intent.entities:
                params[entity_name] = intent.entities[entity_name]

        # Add target if available
        if intent.target:
            if 'recipient' in profile.required_entities:
                params['recipient'] = intent.target
            elif 'query' in profile.required_entities:
                params['query'] = intent.target
            elif profile.category == 'music':
                params['query'] = intent.target

        # Add modifiers
        if intent.modifiers:
            params['modifiers'] = intent.modifiers

        # Tool-specific extraction
        if profile.name == 'set_timer' and 'duration' in intent.entities:
            params['duration'] = intent.entities['duration']

        if profile.name == 'get_weather':
            # Try to extract location
            loc_match = re.search(r'(?:in|at|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', intent.original_message)
            if loc_match:
                params['location'] = loc_match.group(1)

        return params


# ================================================================================
# DISAMBIGUATION ENGINE - Generate helpful clarifying questions
# ================================================================================

class DisambiguationEngine:
    """Generate smart disambiguation questions."""

    # Templates for disambiguation questions
    TEMPLATES = {
        'email': {
            'read_vs_send': "Would you like me to check your inbox or send a new email?",
            'read_vs_reply': "Should I show you recent emails or help you reply to one?",
            'send_vs_reply': "Do you want to compose a new email or reply to an existing one?",
        },
        'music': {
            'play_vs_control': "Would you like me to play something new or control what's currently playing?",
            'play_vs_visualizer': "Should I just play music or start the visualizer with synced lights?",
        },
        'search': {
            'web_vs_docs': "Should I search the web or look through your personal documents?",
        },
        'timer': {
            'timer_vs_reminder': "Do you need a countdown timer or a reminder at a specific time?",
        },
        'generic': {
            'low_confidence': "I'm not quite sure what you'd like me to do. Could you tell me more specifically?",
            'multiple_options': "I can help with a few things here. Which would you prefer: {options}?",
        }
    }

    def generate_disambiguation(
        self,
        matches: List[ToolMatch],
        intent: ParsedIntent
    ) -> Tuple[bool, Optional[str], List[str]]:
        """
        Determine if disambiguation is needed and generate question.

        Returns:
            (needs_disambiguation, question, options)
        """
        if not matches:
            return True, self.TEMPLATES['generic']['low_confidence'], []

        primary = matches[0]

        # If high confidence, no disambiguation needed
        if primary.confidence >= 0.75:
            return False, None, []

        # If only one match, ask for confirmation if confidence is low
        if len(matches) == 1:
            if primary.confidence < 0.4:
                return True, self.TEMPLATES['generic']['low_confidence'], []
            return False, None, []

        # Check for specific conflict patterns
        secondary = matches[1] if len(matches) > 1 else None

        if secondary and secondary.confidence > 0.4:
            # Check if they're in the same category
            primary_profile = TOOL_PROFILES.get(primary.tool_name)
            secondary_profile = TOOL_PROFILES.get(secondary.tool_name)

            if primary_profile and secondary_profile:
                if primary_profile.category == secondary_profile.category:
                    # Same category conflict
                    question = self._get_category_disambiguation(
                        primary_profile.category,
                        primary.tool_name,
                        secondary.tool_name
                    )
                    if question:
                        return True, question, [primary.tool_name, secondary.tool_name]

        # Generic multiple options
        if primary.confidence < 0.6:
            options = [m.tool_name.replace('_', ' ') for m in matches[:3]]
            question = self.TEMPLATES['generic']['multiple_options'].format(
                options=', '.join(options[:-1]) + f', or {options[-1]}' if len(options) > 1 else options[0]
            )
            return True, question, [m.tool_name for m in matches[:3]]

        return False, None, []

    def _get_category_disambiguation(
        self,
        category: str,
        tool1: str,
        tool2: str
    ) -> Optional[str]:
        """Get category-specific disambiguation question."""
        category_templates = self.TEMPLATES.get(category, {})

        # Try to find specific template
        key = f"{tool1.replace(category + '_', '').replace('_' + category, '')}_vs_{tool2.replace(category + '_', '').replace('_' + category, '')}"
        if key in category_templates:
            return category_templates[key]

        # Try reverse order
        key_reverse = f"{tool2.replace(category + '_', '').replace('_' + category, '')}_vs_{tool1.replace(category + '_', '').replace('_' + category, '')}"
        if key_reverse in category_templates:
            return category_templates[key_reverse]

        return None


# ================================================================================
# MAIN ENHANCED SELECTOR CLASS
# ================================================================================

class EnhancedToolSelector:
    """
    Enhanced tool selector with semantic understanding.

    Key improvements:
    1. Semantic matching via tool profiles
    2. Example-based learning
    3. Better disambiguation
    4. Context awareness
    """

    def __init__(self):
        self.intent_parser = IntentParser()
        self.capability_matcher = CapabilityMatcher()
        self.disambiguation_engine = DisambiguationEngine()
        self.usage_history = Counter()
        self.context = {}

    def select_tool(
        self,
        message: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> SelectionResult:
        """
        Main entry point for tool selection.

        Args:
            message: User's message
            conversation_history: Recent conversation for context

        Returns:
            SelectionResult with primary tool and alternatives
        """
        # Check for greeting/casual chat first
        if self._is_casual_chat(message):
            return SelectionResult(
                primary_tool=None,
                alternatives=[],
                needs_disambiguation=False,
                disambiguation_question=None,
                disambiguation_options=[],
                is_compound=False,
                parsed_intent=ParsedIntent(
                    original_message=message,
                    verb=None,
                    verb_normalized=None,
                    object=None,
                    target=None,
                    modifiers=[],
                    entities={},
                    question_type=None,
                    is_command=False,
                    is_follow_up=False
                )
            )

        # Build context from history
        context = self._build_context(conversation_history)

        # Parse intent
        intent = self.intent_parser.parse(message, context)

        # Check for compound request
        is_compound = self._is_compound_request(message)

        # Match against tool profiles
        matches = self.capability_matcher.match(intent, context)

        # Check for disambiguation
        needs_disambig, question, options = self.disambiguation_engine.generate_disambiguation(
            matches, intent
        )

        # Get primary and alternatives
        primary = matches[0] if matches else None
        alternatives = matches[1:4] if len(matches) > 1 else []

        # Update context
        if primary:
            self._update_context(primary.tool_name)

        return SelectionResult(
            primary_tool=primary,
            alternatives=alternatives,
            needs_disambiguation=needs_disambig,
            disambiguation_question=question,
            disambiguation_options=options,
            is_compound=is_compound,
            parsed_intent=intent
        )

    def _is_casual_chat(self, message: str) -> bool:
        """Detect greetings and casual chat."""
        msg_lower = message.lower().strip().rstrip('!.,?')

        # Pure greetings
        greetings = {
            'hi', 'hello', 'hey', 'howdy', 'yo', 'sup', 'hiya',
            'good morning', 'good afternoon', 'good evening', 'good night',
            'morning', 'afternoon', 'evening', 'greetings'
        }
        if msg_lower in greetings:
            return True

        # Casual about Blue
        casual_patterns = [
            r'^(hi|hello|hey)\s+blue',
            r'^how are you',
            r'^who are you',
            r'^what are you',
            r'^thanks?( you)?$',
            r'^(ok|okay|sure|yes|no|yep|nope|fine|alright)$',
            r'^(good|great|awesome|cool|nice)$',
            r'^tell me a joke',
            r'^never ?mind',
        ]

        for pattern in casual_patterns:
            if re.match(pattern, msg_lower):
                return True

        # Very short non-commands
        if len(msg_lower) < 4 and msg_lower not in {'play', 'stop', 'skip', 'next', 'mute', 'on', 'off'}:
            return True

        return False

    def _is_compound_request(self, message: str) -> bool:
        """Detect compound requests."""
        msg_lower = message.lower()

        connectors = [' and then ', ' then ', ' and also ', ' also ', ' and ', ' plus ']
        has_connector = any(conn in msg_lower for conn in connectors)

        if not has_connector:
            return False

        # Check for multi-action patterns
        multi_patterns = [
            r'(?:play|put on).*(?:and|then).*(?:light|turn)',
            r'(?:check|read).*(?:and|then).*(?:search|find)',
            r'(?:send|email).*(?:and|then).*(?:remind|timer)',
            r'(?:turn|set).*(?:and|then).*(?:play|music)',
        ]

        return any(re.search(pat, msg_lower) for pat in multi_patterns)

    def _build_context(self, history: Optional[List[Dict]]) -> Dict:
        """Build context from conversation history."""
        if not history:
            return self.context

        context = {
            'recent_tools': [],
            'recent_category': None,
            'topics': set(),
        }

        for msg in history[-5:]:
            content = msg.get('content', '').lower()

            # Track tool usage from assistant responses
            if msg.get('role') == 'tool':
                tool_match = re.search(r'tool[:\s]+(\w+)', content)
                if tool_match:
                    tool_name = tool_match.group(1)
                    context['recent_tools'].append(tool_name)
                    profile = TOOL_PROFILES.get(tool_name)
                    if profile:
                        context['recent_category'] = profile.category

            # Track topics
            for keyword in ['email', 'music', 'light', 'weather', 'calendar', 'timer']:
                if keyword in content:
                    context['topics'].add(keyword)

        self.context = context
        return context

    def _update_context(self, tool_name: str) -> None:
        """Update context after tool selection."""
        self.usage_history[tool_name] += 1
        self.context['recent_tools'] = self.context.get('recent_tools', [])[-4:] + [tool_name]

        profile = TOOL_PROFILES.get(tool_name)
        if profile:
            self.context['recent_category'] = profile.category


# ================================================================================
# INTEGRATION FUNCTION
# ================================================================================

def integrate_enhanced_selector(
    message: str,
    conversation_messages: List[Dict],
    selector: EnhancedToolSelector
) -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
    """
    Integration function for compatibility with existing Blue code.

    Args:
        message: Current user message
        conversation_messages: Full conversation history
        selector: Instance of EnhancedToolSelector

    Returns:
        Tuple of (tool_name, tool_args, disambiguation_prompt)
    """
    # Get recent history for context
    recent_history = conversation_messages[-5:] if len(conversation_messages) > 5 else conversation_messages

    # Run selection
    result = selector.select_tool(message, recent_history)

    if not result.primary_tool:
        return None, None, None

    if result.needs_disambiguation:
        return None, None, result.disambiguation_question

    # Return selected tool
    tool_name = result.primary_tool.tool_name
    tool_args = result.primary_tool.extracted_params

    # Logging
    print(f"   [ENHANCED-SELECTOR] Selected: {tool_name}")
    print(f"   [ENHANCED-SELECTOR] Confidence: {result.primary_tool.confidence:.2f}")
    print(f"   [ENHANCED-SELECTOR] Reasons: {', '.join(result.primary_tool.match_reasons)}")

    if result.alternatives:
        alt_names = [t.tool_name for t in result.alternatives[:2]]
        print(f"   [ENHANCED-SELECTOR] Alternatives: {', '.join(alt_names)}")

    if result.is_compound:
        print(f"   [ENHANCED-SELECTOR] WARNING: Compound request detected")

    return tool_name, tool_args, None


# ================================================================================
# STANDALONE TEST
# ================================================================================

if __name__ == "__main__":
    selector = EnhancedToolSelector()

    test_messages = [
        "check my email",
        "play some jazz",
        "what's the weather?",
        "set a timer for 10 minutes",
        "turn on the lights",
        "search for AI news",
        "send an email to john@example.com",
        "search my documents for the contract",
        "remind me to call mom at 3pm",
        "skip this song",
        "hello blue",
        "play relaxing music and dim the lights",
        "what time is it?",
        "flip a coin",
    ]

    for msg in test_messages:
        print(f"\n{'='*60}")
        print(f"Message: {msg}")
        print(f"{'='*60}")

        result = selector.select_tool(msg, [])

        if result.primary_tool:
            print(f"Primary: {result.primary_tool.tool_name} ({result.primary_tool.confidence:.2f})")
            print(f"Reasons: {', '.join(result.primary_tool.match_reasons)}")
            print(f"Params: {result.primary_tool.extracted_params}")

            if result.alternatives:
                print(f"Alternatives: {[f'{a.tool_name}({a.confidence:.2f})' for a in result.alternatives]}")

            if result.needs_disambiguation:
                print(f"DISAMBIGUATION: {result.disambiguation_question}")
        else:
            print("No tool needed (casual chat)")

        print(f"Parsed intent: verb={result.parsed_intent.verb}, object={result.parsed_intent.object}")
