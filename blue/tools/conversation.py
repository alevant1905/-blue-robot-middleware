"""
Blue Robot Conversation Memory
===============================
Enhanced conversation tracking with context awareness and memory.

Features:
- Short-term conversation context
- Long-term memory storage
- Topic tracking and summarization
- User preference learning
- Conversation analytics
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import sqlite3
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

# ================================================================================
# CONFIGURATION
# ================================================================================

CONVERSATION_DB = os.environ.get("BLUE_CONVERSATION_DB", "data/conversation.db")
MAX_SHORT_TERM_MESSAGES = 20
MAX_TOPIC_HISTORY = 10


class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationTopic(Enum):
    MUSIC = "music"
    WEATHER = "weather"
    EMAIL = "email"
    LIGHTS = "lights"
    TASKS = "tasks"
    REMINDERS = "reminders"
    GENERAL = "general"
    TECHNICAL = "technical"
    PERSONAL = "personal"
    CREATIVE = "creative"


# ================================================================================
# DATA CLASSES
# ================================================================================

@dataclass
class Message:
    """A single message in the conversation."""
    role: MessageRole
    content: str
    timestamp: str
    message_id: str = ""
    topics: List[str] = field(default_factory=list)
    entities: Dict[str, List[str]] = field(default_factory=dict)
    sentiment: Optional[str] = None
    tool_used: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
            "topics": self.topics,
            "entities": self.entities,
            "sentiment": self.sentiment,
            "tool_used": self.tool_used
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=data["timestamp"],
            message_id=data.get("message_id", ""),
            topics=data.get("topics", []),
            entities=data.get("entities", {}),
            sentiment=data.get("sentiment"),
            tool_used=data.get("tool_used")
        )


@dataclass
class ConversationSummary:
    """Summary of a conversation session."""
    session_id: str
    start_time: str
    end_time: str
    message_count: int
    topics: List[str]
    key_points: List[str]
    user_requests: List[str]
    tools_used: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "message_count": self.message_count,
            "topics": self.topics,
            "key_points": self.key_points,
            "user_requests": self.user_requests,
            "tools_used": self.tools_used
        }


@dataclass
class UserPreference:
    """Learned user preference."""
    category: str
    key: str
    value: str
    confidence: float
    source: str  # Where we learned this
    learned_at: str
    times_observed: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "key": self.key,
            "value": self.value,
            "confidence": self.confidence,
            "source": self.source,
            "learned_at": self.learned_at,
            "times_observed": self.times_observed
        }


@dataclass
class MemoryEntry:
    """A long-term memory entry."""
    memory_id: str
    memory_type: str  # "fact", "preference", "event", "person", "place"
    subject: str
    content: str
    importance: float  # 0.0 to 1.0
    created_at: str
    last_accessed: str
    access_count: int = 0
    related_memories: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "memory_type": self.memory_type,
            "subject": self.subject,
            "content": self.content,
            "importance": self.importance,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "related_memories": self.related_memories
        }


# ================================================================================
# CONVERSATION MEMORY MANAGER
# ================================================================================

class ConversationMemory:
    """
    Manages conversation history, context, and long-term memory.
    """

    def __init__(self, db_path: str = CONVERSATION_DB):
        self.db_path = db_path
        self.session_id = self._generate_session_id()
        self.short_term: Deque[Message] = deque(maxlen=MAX_SHORT_TERM_MESSAGES)
        self.current_topics: Deque[str] = deque(maxlen=MAX_TOPIC_HISTORY)
        self.active_entities: Dict[str, List[str]] = {}
        self.user_preferences: Dict[str, UserPreference] = {}

        self._init_db()
        self._load_preferences()

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = datetime.datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:12]

    def _init_db(self):
        """Initialize the conversation database."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                message_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                topics TEXT,
                entities TEXT,
                sentiment TEXT,
                tool_used TEXT
            )
        """)

        # Session summaries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                start_time TEXT NOT NULL,
                end_time TEXT,
                message_count INTEGER DEFAULT 0,
                topics TEXT,
                summary TEXT
            )
        """)

        # User preferences
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                source TEXT,
                learned_at TEXT,
                times_observed INTEGER DEFAULT 1,
                UNIQUE(category, key)
            )
        """)

        # Long-term memories
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY,
                memory_type TEXT NOT NULL,
                subject TEXT NOT NULL,
                content TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                created_at TEXT NOT NULL,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 0,
                related_memories TEXT
            )
        """)

        # Create session record
        cursor.execute("""
            INSERT OR IGNORE INTO sessions (session_id, start_time, message_count)
            VALUES (?, ?, 0)
        """, (self.session_id, datetime.datetime.now().isoformat()))

        conn.commit()
        conn.close()

    def _load_preferences(self):
        """Load user preferences from database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        for row in cursor.execute("SELECT * FROM preferences").fetchall():
            key = f"{row['category']}:{row['key']}"
            self.user_preferences[key] = UserPreference(
                category=row['category'],
                key=row['key'],
                value=row['value'],
                confidence=row['confidence'],
                source=row['source'] or "",
                learned_at=row['learned_at'] or "",
                times_observed=row['times_observed']
            )

        conn.close()

    # ==================== MESSAGE HANDLING ====================

    def add_message(self, role: str, content: str,
                    tool_used: str = None) -> Message:
        """Add a new message to the conversation."""
        message = Message(
            role=MessageRole(role),
            content=content,
            timestamp=datetime.datetime.now().isoformat(),
            message_id=hashlib.md5(f"{self.session_id}:{content}".encode()).hexdigest()[:8],
            tool_used=tool_used
        )

        # Analyze message
        message.topics = self._detect_topics(content)
        message.entities = self._extract_entities(content)
        message.sentiment = self._detect_sentiment(content)

        # Update tracking
        self.short_term.append(message)
        for topic in message.topics:
            if topic not in self.current_topics:
                self.current_topics.append(topic)

        # Update active entities
        for entity_type, entities in message.entities.items():
            if entity_type not in self.active_entities:
                self.active_entities[entity_type] = []
            self.active_entities[entity_type].extend(entities)
            # Keep only recent
            self.active_entities[entity_type] = self.active_entities[entity_type][-10:]

        # Save to database
        self._save_message(message)

        # Learn preferences from user messages
        if role == "user":
            self._learn_from_message(message)

        return message

    def _save_message(self, message: Message):
        """Save message to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO messages
            (session_id, message_id, role, content, timestamp, topics, entities, sentiment, tool_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.session_id,
            message.message_id,
            message.role.value,
            message.content,
            message.timestamp,
            json.dumps(message.topics),
            json.dumps(message.entities),
            message.sentiment,
            message.tool_used
        ))

        # Update session count
        cursor.execute("""
            UPDATE sessions SET message_count = message_count + 1, end_time = ?
            WHERE session_id = ?
        """, (message.timestamp, self.session_id))

        conn.commit()
        conn.close()

    # ==================== TOPIC DETECTION ====================

    def _detect_topics(self, content: str) -> List[str]:
        """Detect topics in the message."""
        topics = []
        content_lower = content.lower()

        topic_keywords = {
            "music": ["music", "song", "play", "artist", "album", "spotify", "playlist"],
            "weather": ["weather", "temperature", "rain", "sunny", "forecast", "cold", "hot"],
            "email": ["email", "inbox", "message", "send", "reply", "gmail"],
            "lights": ["lights", "lamp", "bright", "dim", "hue", "color"],
            "tasks": ["task", "todo", "reminder", "deadline", "schedule"],
            "reminders": ["remind", "reminder", "don't forget", "remember to"],
            "technical": ["code", "programming", "bug", "error", "function", "api"],
            "personal": ["family", "friend", "birthday", "anniversary", "feeling"],
            "creative": ["write", "story", "poem", "creative", "imagine", "idea"],
        }

        for topic, keywords in topic_keywords.items():
            if any(kw in content_lower for kw in keywords):
                topics.append(topic)

        if not topics:
            topics.append("general")

        return topics

    # ==================== ENTITY EXTRACTION ====================

    def _extract_entities(self, content: str) -> Dict[str, List[str]]:
        """Extract named entities from content."""
        entities = {
            "names": [],
            "times": [],
            "locations": [],
            "numbers": []
        }

        # Names (capitalized words)
        name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
        entities["names"] = re.findall(name_pattern, content)

        # Times
        time_patterns = [
            r'\b(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)\b',
            r'\b(tomorrow|today|yesterday|next week|this week)\b',
            r'\b(\d+\s*(?:minutes?|hours?|days?|weeks?))\b'
        ]
        for pattern in time_patterns:
            entities["times"].extend(re.findall(pattern, content, re.I))

        # Numbers
        entities["numbers"] = re.findall(r'\b(\d+(?:\.\d+)?)\b', content)

        # Filter out empty lists
        return {k: v for k, v in entities.items() if v}

    # ==================== SENTIMENT DETECTION ====================

    def _detect_sentiment(self, content: str) -> str:
        """Simple sentiment detection."""
        content_lower = content.lower()

        positive = ["thanks", "great", "awesome", "love", "perfect", "excellent",
                   "happy", "good", "nice", "wonderful", "amazing"]
        negative = ["hate", "bad", "terrible", "awful", "wrong", "error",
                   "frustrated", "annoyed", "angry", "upset"]
        question = ["?", "what", "how", "why", "when", "where", "who", "which"]

        pos_count = sum(1 for w in positive if w in content_lower)
        neg_count = sum(1 for w in negative if w in content_lower)
        is_question = any(q in content_lower for q in question)

        if is_question:
            return "questioning"
        elif pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        else:
            return "neutral"

    # ==================== PREFERENCE LEARNING ====================

    def _learn_from_message(self, message: Message):
        """Learn user preferences from messages."""
        content_lower = message.content.lower()

        # Music preferences
        if "music" in message.topics:
            # Genre preferences
            genres = ["jazz", "rock", "pop", "classical", "electronic", "hip hop", "country", "metal"]
            for genre in genres:
                if genre in content_lower:
                    if "love" in content_lower or "like" in content_lower or "favorite" in content_lower:
                        self._update_preference("music", f"preferred_genre", genre, 0.7, message.content)
                    elif "hate" in content_lower or "don't like" in content_lower:
                        self._update_preference("music", f"disliked_genre", genre, 0.7, message.content)

        # Time preferences
        if "morning" in content_lower and ("prefer" in content_lower or "like" in content_lower):
            self._update_preference("schedule", "active_time", "morning", 0.6, message.content)
        elif "night" in content_lower and ("prefer" in content_lower or "like" in content_lower):
            self._update_preference("schedule", "active_time", "night", 0.6, message.content)

        # Communication style
        if len(message.content) < 20:
            self._update_preference("communication", "brevity", "concise", 0.5, message.content)
        elif len(message.content) > 200:
            self._update_preference("communication", "brevity", "detailed", 0.5, message.content)

    def _update_preference(self, category: str, key: str, value: str,
                          confidence: float, source: str):
        """Update or create a preference."""
        pref_key = f"{category}:{key}"

        if pref_key in self.user_preferences:
            pref = self.user_preferences[pref_key]
            if pref.value == value:
                pref.times_observed += 1
                pref.confidence = min(1.0, pref.confidence + 0.1)
        else:
            pref = UserPreference(
                category=category,
                key=key,
                value=value,
                confidence=confidence,
                source=source[:100],
                learned_at=datetime.datetime.now().isoformat()
            )
            self.user_preferences[pref_key] = pref

        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO preferences
            (category, key, value, confidence, source, learned_at, times_observed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            pref.category, pref.key, pref.value,
            pref.confidence, pref.source, pref.learned_at,
            pref.times_observed
        ))
        conn.commit()
        conn.close()

    # ==================== CONTEXT RETRIEVAL ====================

    def get_context(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation context."""
        messages = list(self.short_term)[-max_messages:]
        return [m.to_dict() for m in messages]

    def get_context_summary(self) -> str:
        """Get a summary of current context."""
        parts = []

        # Topics
        if self.current_topics:
            topics = list(self.current_topics)[-5:]
            parts.append(f"Recent topics: {', '.join(topics)}")

        # Active entities
        if self.active_entities:
            for entity_type, entities in self.active_entities.items():
                if entities:
                    unique = list(set(entities[-5:]))
                    parts.append(f"{entity_type.title()}: {', '.join(unique)}")

        # Message count
        parts.append(f"Messages in session: {len(self.short_term)}")

        return "\n".join(parts)

    def get_relevant_preferences(self, topics: List[str] = None) -> List[UserPreference]:
        """Get preferences relevant to current context."""
        if topics is None:
            topics = list(self.current_topics)

        relevant = []
        for pref in self.user_preferences.values():
            if pref.category in topics or pref.confidence > 0.7:
                relevant.append(pref)

        return sorted(relevant, key=lambda p: p.confidence, reverse=True)

    # ==================== MEMORY OPERATIONS ====================

    def remember(self, memory_type: str, subject: str, content: str,
                importance: float = 0.5) -> MemoryEntry:
        """Create a long-term memory."""
        import uuid
        memory_id = str(uuid.uuid4())[:8]

        memory = MemoryEntry(
            memory_id=memory_id,
            memory_type=memory_type,
            subject=subject,
            content=content,
            importance=importance,
            created_at=datetime.datetime.now().isoformat(),
            last_accessed=datetime.datetime.now().isoformat()
        )

        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO memories
            (memory_id, memory_type, subject, content, importance, created_at, last_accessed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            memory.memory_id, memory.memory_type, memory.subject,
            memory.content, memory.importance,
            memory.created_at, memory.last_accessed
        ))
        conn.commit()
        conn.close()

        return memory

    def recall(self, query: str, memory_type: str = None,
               limit: int = 5) -> List[MemoryEntry]:
        """Recall memories matching a query."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        sql = """
            SELECT * FROM memories
            WHERE (subject LIKE ? OR content LIKE ?)
        """
        params = [f"%{query}%", f"%{query}%"]

        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type)

        sql += " ORDER BY importance DESC, last_accessed DESC LIMIT ?"
        params.append(limit)

        rows = cursor.execute(sql, params).fetchall()

        memories = []
        for row in rows:
            memory = MemoryEntry(
                memory_id=row['memory_id'],
                memory_type=row['memory_type'],
                subject=row['subject'],
                content=row['content'],
                importance=row['importance'],
                created_at=row['created_at'],
                last_accessed=row['last_accessed'],
                access_count=row['access_count'],
                related_memories=json.loads(row['related_memories'] or "[]")
            )
            memories.append(memory)

            # Update access
            cursor.execute("""
                UPDATE memories
                SET last_accessed = ?, access_count = access_count + 1
                WHERE memory_id = ?
            """, (datetime.datetime.now().isoformat(), memory.memory_id))

        conn.commit()
        conn.close()

        return memories

    def get_important_memories(self, limit: int = 10) -> List[MemoryEntry]:
        """Get the most important memories."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        rows = cursor.execute("""
            SELECT * FROM memories
            ORDER BY importance DESC, access_count DESC
            LIMIT ?
        """, (limit,)).fetchall()

        conn.close()

        return [
            MemoryEntry(
                memory_id=row['memory_id'],
                memory_type=row['memory_type'],
                subject=row['subject'],
                content=row['content'],
                importance=row['importance'],
                created_at=row['created_at'],
                last_accessed=row['last_accessed'],
                access_count=row['access_count'],
                related_memories=json.loads(row['related_memories'] or "[]")
            )
            for row in rows
        ]

    # ==================== SESSION MANAGEMENT ====================

    def end_session(self) -> ConversationSummary:
        """End the current session and create a summary."""
        messages = list(self.short_term)

        # Collect data
        all_topics = []
        tools_used = []
        user_requests = []

        for msg in messages:
            all_topics.extend(msg.topics)
            if msg.tool_used:
                tools_used.append(msg.tool_used)
            if msg.role == MessageRole.USER:
                user_requests.append(msg.content[:100])

        # Create summary
        summary = ConversationSummary(
            session_id=self.session_id,
            start_time=messages[0].timestamp if messages else "",
            end_time=messages[-1].timestamp if messages else "",
            message_count=len(messages),
            topics=list(set(all_topics)),
            key_points=[],  # Could be enhanced with LLM summarization
            user_requests=user_requests[:5],
            tools_used=list(set(tools_used))
        )

        # Save summary
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions
            SET end_time = ?, topics = ?, summary = ?
            WHERE session_id = ?
        """, (
            summary.end_time,
            json.dumps(summary.topics),
            json.dumps(summary.to_dict()),
            self.session_id
        ))
        conn.commit()
        conn.close()

        # Start new session
        self.session_id = self._generate_session_id()
        self.short_term.clear()
        self.current_topics.clear()

        return summary

    def get_session_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get past session summaries."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        rows = cursor.execute("""
            SELECT * FROM sessions
            WHERE summary IS NOT NULL
            ORDER BY start_time DESC
            LIMIT ?
        """, (limit,)).fetchall()

        conn.close()

        return [json.loads(row['summary']) for row in rows if row['summary']]


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_conversation_memory: Optional[ConversationMemory] = None


def get_conversation_memory() -> ConversationMemory:
    """Get or create the global conversation memory."""
    global _conversation_memory
    if _conversation_memory is None:
        _conversation_memory = ConversationMemory()
    return _conversation_memory


# ================================================================================
# EXECUTOR FUNCTIONS
# ================================================================================

def add_to_conversation(role: str, content: str, tool_used: str = None) -> str:
    """Add a message to the conversation."""
    memory = get_conversation_memory()
    message = memory.add_message(role, content, tool_used)

    return json.dumps({
        "success": True,
        "message_id": message.message_id,
        "topics": message.topics,
        "sentiment": message.sentiment
    })


def get_conversation_context(max_messages: int = 10) -> str:
    """Get recent conversation context."""
    memory = get_conversation_memory()
    context = memory.get_context(max_messages)

    return json.dumps({
        "success": True,
        "messages": context,
        "summary": memory.get_context_summary()
    })


def remember_this(subject: str, content: str, memory_type: str = "fact",
                  importance: float = 0.5) -> str:
    """Create a long-term memory."""
    memory = get_conversation_memory()
    entry = memory.remember(memory_type, subject, content, importance)

    return json.dumps({
        "success": True,
        "message": f"I'll remember that about {subject}",
        "memory": entry.to_dict()
    })


def recall_memory(query: str, memory_type: str = None) -> str:
    """Recall memories matching a query."""
    memory = get_conversation_memory()
    memories = memory.recall(query, memory_type)

    if not memories:
        return json.dumps({
            "success": True,
            "message": f"I don't have any memories about '{query}'",
            "count": 0,
            "memories": []
        })

    return json.dumps({
        "success": True,
        "count": len(memories),
        "memories": [m.to_dict() for m in memories]
    })


def get_user_preferences(category: str = None) -> str:
    """Get learned user preferences."""
    memory = get_conversation_memory()

    if category:
        prefs = [p for p in memory.user_preferences.values()
                 if p.category == category]
    else:
        prefs = list(memory.user_preferences.values())

    return json.dumps({
        "success": True,
        "count": len(prefs),
        "preferences": [p.to_dict() for p in prefs]
    })


def execute_conversation_command(action: str, params: Dict[str, Any] = None) -> str:
    """Execute a conversation memory command."""
    if params is None:
        params = {}

    action_lower = action.lower().strip()

    if action_lower in ['add_message', 'log']:
        return add_to_conversation(
            role=params.get('role', 'user'),
            content=params.get('content', ''),
            tool_used=params.get('tool_used')
        )

    elif action_lower in ['context', 'get_context']:
        return get_conversation_context(params.get('max_messages', 10))

    elif action_lower in ['remember', 'save_memory']:
        return remember_this(
            subject=params.get('subject', ''),
            content=params.get('content', ''),
            memory_type=params.get('type', 'fact'),
            importance=params.get('importance', 0.5)
        )

    elif action_lower in ['recall', 'search_memory']:
        return recall_memory(
            query=params.get('query', ''),
            memory_type=params.get('type')
        )

    elif action_lower in ['preferences', 'get_preferences']:
        return get_user_preferences(params.get('category'))

    else:
        return json.dumps({
            "success": False,
            "error": f"Unknown conversation action: {action}"
        })


__all__ = [
    'ConversationMemory',
    'Message',
    'MessageRole',
    'ConversationSummary',
    'UserPreference',
    'MemoryEntry',
    'get_conversation_memory',
    'add_to_conversation',
    'get_conversation_context',
    'remember_this',
    'recall_memory',
    'get_user_preferences',
    'execute_conversation_command',
]
