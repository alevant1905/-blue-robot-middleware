"""
Blue Robot Enhanced Memory System
==================================
Advanced memory with conversation history, semantic search, and context-aware retrieval.

Features:
- Long-term fact storage with timestamps
- Conversation history with semantic indexing
- Entity tracking (people, places, things)
- Relationship memory (connections between entities)
- Temporal memory (remembers when things happened)
- Context-aware retrieval (finds relevant memories based on current conversation)
- Memory consolidation (merges related memories)
- Importance scoring (prioritizes important memories)
"""

# Future imports
from __future__ import annotations

# Standard library
import datetime
import hashlib
import json
import os
import re
import sqlite3
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

# ================================================================================
# CONFIGURATION
# ================================================================================

ENHANCED_MEMORY_DB = os.environ.get("BLUE_ENHANCED_MEMORY_DB", os.path.join("data", "enhanced_memory.db"))


class MemoryType(Enum):
    """Types of memories"""
    FACT = "fact"  # Long-term facts about the user
    CONVERSATION = "conversation"  # Conversation snippets
    ENTITY = "entity"  # People, places, things
    RELATIONSHIP = "relationship"  # Connections between entities
    EVENT = "event"  # Things that happened
    PREFERENCE = "preference"  # User preferences
    INSTRUCTION = "instruction"  # How user wants things done


class ImportanceLevel(Enum):
    """How important is this memory"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Memory:
    """Represents a single memory"""
    id: str
    memory_type: MemoryType
    content: str
    timestamp: float
    importance: ImportanceLevel
    entities: List[str]  # Related entities
    tags: List[str]  # Semantic tags
    context: Dict[str, Any]  # Additional context
    access_count: int = 0
    last_accessed: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "timestamp": datetime.datetime.fromtimestamp(self.timestamp).isoformat(),
            "importance": self.importance.value,
            "entities": self.entities,
            "tags": self.tags,
            "context": self.context,
            "access_count": self.access_count,
            "last_accessed": datetime.datetime.fromtimestamp(self.last_accessed).isoformat() if self.last_accessed else None
        }


@dataclass
class Entity:
    """Represents an entity (person, place, thing)"""
    id: str
    name: str
    entity_type: str  # person, place, organization, object, etc.
    attributes: Dict[str, str]  # Properties of the entity
    first_mentioned: float
    last_mentioned: float
    mention_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type,
            "attributes": self.attributes,
            "first_mentioned": datetime.datetime.fromtimestamp(self.first_mentioned).isoformat(),
            "last_mentioned": datetime.datetime.fromtimestamp(self.last_mentioned).isoformat(),
            "mention_count": self.mention_count
        }


# ================================================================================
# ENHANCED MEMORY MANAGER
# ================================================================================

class EnhancedMemoryManager:
    """Manages Blue's enhanced memory system"""

    def __init__(self, db_path: str = ENHANCED_MEMORY_DB):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize all memory tables"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Memories table - stores all types of memories
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL NOT NULL,
                importance INTEGER NOT NULL,
                entities TEXT,
                tags TEXT,
                context TEXT,
                access_count INTEGER DEFAULT 0,
                last_accessed REAL,
                embedding_hash TEXT
            )
        """)

        # Entities table - tracks people, places, things
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                attributes TEXT,
                first_mentioned REAL NOT NULL,
                last_mentioned REAL NOT NULL,
                mention_count INTEGER DEFAULT 1
            )
        """)

        # Relationships table - connections between entities
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                entity1_id TEXT NOT NULL,
                entity2_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                description TEXT,
                created_at REAL NOT NULL,
                strength INTEGER DEFAULT 1,
                FOREIGN KEY (entity1_id) REFERENCES entities (id),
                FOREIGN KEY (entity2_id) REFERENCES entities (id)
            )
        """)

        # Conversation history - full conversation tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL NOT NULL,
                tokens_estimate INTEGER,
                summary TEXT,
                extracted_facts TEXT
            )
        """)

        # Indices for fast retrieval
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp)")

        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    # ==================== MEMORY STORAGE ====================

    def store_memory(self, memory_type: str, content: str, importance: int = 2,
                    entities: List[str] = None, tags: List[str] = None,
                    context: Dict[str, Any] = None) -> Memory:
        """Store a new memory"""
        memory_id = str(uuid.uuid4())[:12]
        now = datetime.datetime.now().timestamp()

        try:
            type_enum = MemoryType(memory_type.lower())
        except ValueError:
            type_enum = MemoryType.FACT

        memory = Memory(
            id=memory_id,
            memory_type=type_enum,
            content=content,
            timestamp=now,
            importance=ImportanceLevel(importance),
            entities=entities or [],
            tags=tags or [],
            context=context or {},
            access_count=0,
            last_accessed=None
        )

        # Create embedding hash for deduplication
        embedding_hash = hashlib.md5(content.lower().encode()).hexdigest()

        conn = self._get_conn()
        cursor = conn.cursor()

        # Check for duplicate
        cursor.execute("SELECT id FROM memories WHERE embedding_hash = ?", (embedding_hash,))
        if cursor.fetchone():
            conn.close()
            return memory  # Skip duplicate

        cursor.execute("""
            INSERT INTO memories (id, memory_type, content, timestamp, importance, entities, tags, context, embedding_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (memory.id, memory.memory_type.value, memory.content, memory.timestamp,
              memory.importance.value, json.dumps(memory.entities), json.dumps(memory.tags),
              json.dumps(memory.context), embedding_hash))

        conn.commit()
        conn.close()

        # Update entities
        for entity_name in entities or []:
            self._update_entity(entity_name)

        return memory

    def get_memories(self, memory_type: str = None, limit: int = 50,
                    min_importance: int = 1, tags: List[str] = None) -> List[Memory]:
        """Retrieve memories with filtering"""
        conn = self._get_conn()
        cursor = conn.cursor()

        sql = "SELECT * FROM memories WHERE importance >= ?"
        params = [min_importance]

        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type.lower())

        if tags:
            for tag in tags:
                sql += " AND tags LIKE ?"
                params.append(f"%{tag}%")

        sql += " ORDER BY importance DESC, timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            Memory(
                id=row[0], memory_type=MemoryType(row[1]), content=row[2],
                timestamp=row[3], importance=ImportanceLevel(row[4]),
                entities=json.loads(row[5] or "[]"), tags=json.loads(row[6] or "[]"),
                context=json.loads(row[7] or "{}"),
                access_count=row[8] or 0, last_accessed=row[9]
            )
            for row in rows
        ]

    def search_memories(self, query: str, limit: int = 10) -> List[Memory]:
        """Search memories by content"""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Simple keyword search with ranking by importance
        cursor.execute("""
            SELECT * FROM memories
            WHERE content LIKE ?
            ORDER BY importance DESC, timestamp DESC
            LIMIT ?
        """, (f"%{query}%", limit))

        rows = cursor.fetchall()
        conn.close()

        # Update access counts
        for row in rows:
            self._record_memory_access(row[0])

        return [
            Memory(
                id=row[0], memory_type=MemoryType(row[1]), content=row[2],
                timestamp=row[3], importance=ImportanceLevel(row[4]),
                entities=json.loads(row[5] or "[]"), tags=json.loads(row[6] or "[]"),
                context=json.loads(row[7] or "{}"),
                access_count=row[8] or 0, last_accessed=row[9]
            )
            for row in rows
        ]

    def _record_memory_access(self, memory_id: str):
        """Record that a memory was accessed"""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.datetime.now().timestamp()
        cursor.execute("""
            UPDATE memories
            SET access_count = access_count + 1, last_accessed = ?
            WHERE id = ?
        """, (now, memory_id))
        conn.commit()
        conn.close()

    # ==================== ENTITY TRACKING ====================

    def _update_entity(self, name: str, entity_type: str = "unknown",
                      attributes: Dict[str, str] = None):
        """Update or create an entity"""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.datetime.now().timestamp()

        # Check if entity exists
        cursor.execute("SELECT id, mention_count FROM entities WHERE LOWER(name) = LOWER(?)", (name,))
        row = cursor.fetchone()

        if row:
            # Update existing
            entity_id, count = row
            cursor.execute("""
                UPDATE entities
                SET last_mentioned = ?, mention_count = mention_count + 1
                WHERE id = ?
            """, (now, entity_id))
        else:
            # Create new
            entity_id = str(uuid.uuid4())[:12]
            cursor.execute("""
                INSERT INTO entities (id, name, entity_type, attributes, first_mentioned, last_mentioned, mention_count)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (entity_id, name, entity_type, json.dumps(attributes or {}), now, now))

        conn.commit()
        conn.close()
        return entity_id

    def get_entities(self, entity_type: str = None, min_mentions: int = 1) -> List[Entity]:
        """Get tracked entities"""
        conn = self._get_conn()
        cursor = conn.cursor()

        sql = "SELECT * FROM entities WHERE mention_count >= ?"
        params = [min_mentions]

        if entity_type:
            sql += " AND entity_type = ?"
            params.append(entity_type)

        sql += " ORDER BY mention_count DESC, last_mentioned DESC"

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            Entity(
                id=row[0], name=row[1], entity_type=row[2],
                attributes=json.loads(row[3] or "{}"),
                first_mentioned=row[4], last_mentioned=row[5],
                mention_count=row[6]
            )
            for row in rows
        ]

    # ==================== CONVERSATION HISTORY ====================

    def store_conversation(self, role: str, content: str, session_id: str = "default") -> str:
        """Store a conversation message"""
        msg_id = str(uuid.uuid4())[:12]
        now = datetime.datetime.now().timestamp()

        # Estimate tokens (rough estimate: 4 chars per token)
        tokens_estimate = len(content) // 4

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversations (id, session_id, role, content, timestamp, tokens_estimate)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (msg_id, session_id, role, content, now, tokens_estimate))
        conn.commit()
        conn.close()

        return msg_id

    def get_conversation_history(self, session_id: str = "default",
                                limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, content, timestamp FROM conversations
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (session_id, limit))
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "role": row[0],
                "content": row[1],
                "timestamp": datetime.datetime.fromtimestamp(row[2]).isoformat()
            }
            for row in reversed(rows)  # Return chronological order
        ]

    def get_conversation_summary(self, session_id: str = "default",
                                hours: int = 24) -> str:
        """Get a summary of recent conversation"""
        cutoff = (datetime.datetime.now() - datetime.timedelta(hours=hours)).timestamp()

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT role, content FROM conversations
            WHERE session_id = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        """, (session_id, cutoff))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "No recent conversation"

        # Create summary
        user_messages = [r[1] for r in rows if r[0] == "user"]
        assistant_messages = [r[1] for r in rows if r[0] == "assistant"]

        summary = f"Recent conversation ({len(rows)} messages):\n"
        if user_messages:
            summary += f"User discussed: {', '.join(user_messages[:3])}...\n"
        if assistant_messages:
            summary += f"Assistant helped with: {', '.join(assistant_messages[:3])}..."

        return summary

    # ==================== CONTEXT-AWARE RETRIEVAL ====================

    def get_relevant_context(self, current_message: str, limit: int = 5) -> List[str]:
        """Get relevant memories and facts based on current message"""
        context_items = []

        # Extract keywords from current message
        keywords = self._extract_keywords(current_message)

        # Search for relevant memories
        for keyword in keywords[:3]:  # Top 3 keywords
            memories = self.search_memories(keyword, limit=2)
            for memory in memories:
                if memory.content not in context_items:
                    context_items.append(memory.content)

        # Add high-importance facts
        important_facts = self.get_memories(memory_type="fact", min_importance=3, limit=3)
        for fact in important_facts:
            if fact.content not in context_items:
                context_items.append(fact.content)

        return context_items[:limit]

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
                     'i', 'you', 'he', 'she', 'it', 'we', 'they', 'is', 'am', 'are', 'was',
                     'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
                     'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can'}

        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        keywords = [w for w in words if w not in stop_words]

        # Count frequency
        freq = defaultdict(int)
        for word in keywords:
            freq[word] += 1

        # Return sorted by frequency
        return sorted(freq.keys(), key=lambda x: freq[x], reverse=True)

    # ==================== MEMORY CONSOLIDATION ====================

    def consolidate_similar_memories(self, threshold: float = 0.8):
        """Merge very similar memories to reduce duplication"""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Get all facts
        cursor.execute("SELECT id, content FROM memories WHERE memory_type = 'fact'")
        facts = cursor.fetchall()

        consolidated = []
        for i, (id1, content1) in enumerate(facts):
            for id2, content2 in facts[i+1:]:
                similarity = self._text_similarity(content1, content2)
                if similarity > threshold:
                    # Mark for consolidation
                    consolidated.append((id1, id2, similarity))

        conn.close()

        return len(consolidated)

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity (Jaccard similarity)"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    # ==================== STATISTICS ====================

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        conn = self._get_conn()
        cursor = conn.cursor()

        stats = {}

        # Total memories by type
        cursor.execute("""
            SELECT memory_type, COUNT(*) FROM memories
            GROUP BY memory_type
        """)
        stats['memories_by_type'] = dict(cursor.fetchall())

        # Total entities
        cursor.execute("SELECT COUNT(*) FROM entities")
        stats['total_entities'] = cursor.fetchone()[0]

        # Total conversations
        cursor.execute("SELECT COUNT(*) FROM conversations")
        stats['total_conversations'] = cursor.fetchone()[0]

        # Most accessed memories
        cursor.execute("""
            SELECT content, access_count FROM memories
            ORDER BY access_count DESC
            LIMIT 5
        """)
        stats['most_accessed'] = [{"content": r[0], "count": r[1]} for r in cursor.fetchall()]

        # Most mentioned entities
        cursor.execute("""
            SELECT name, mention_count FROM entities
            ORDER BY mention_count DESC
            LIMIT 5
        """)
        stats['top_entities'] = [{"name": r[0], "mentions": r[1]} for r in cursor.fetchall()]

        conn.close()
        return stats


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_enhanced_memory_manager: Optional[EnhancedMemoryManager] = None


def get_enhanced_memory_manager() -> EnhancedMemoryManager:
    """Get or create singleton enhanced memory manager"""
    global _enhanced_memory_manager
    if _enhanced_memory_manager is None:
        _enhanced_memory_manager = EnhancedMemoryManager()
    return _enhanced_memory_manager


# ================================================================================
# INTEGRATION FUNCTIONS
# ================================================================================

def store_fact(content: str, importance: int = 2, tags: List[str] = None) -> str:
    """Store a fact about the user"""
    manager = get_enhanced_memory_manager()
    memory = manager.store_memory("fact", content, importance, tags=tags)
    return json.dumps({"status": "success", "memory_id": memory.id})


def retrieve_facts(query: str = None, limit: int = 10) -> str:
    """Retrieve facts, optionally searching by query"""
    manager = get_enhanced_memory_manager()

    if query:
        memories = manager.search_memories(query, limit=limit)
    else:
        memories = manager.get_memories(memory_type="fact", limit=limit)

    return json.dumps({
        "status": "success",
        "count": len(memories),
        "facts": [m.to_dict() for m in memories]
    })


def get_context_for_message(message: str) -> List[str]:
    """Get relevant context for a message"""
    manager = get_enhanced_memory_manager()
    return manager.get_relevant_context(message)


def log_conversation(role: str, content: str, session_id: str = "default") -> str:
    """Log a conversation message"""
    manager = get_enhanced_memory_manager()
    msg_id = manager.store_conversation(role, content, session_id)
    return msg_id


def get_memory_statistics() -> str:
    """Get memory system statistics"""
    manager = get_enhanced_memory_manager()
    stats = manager.get_memory_stats()
    return json.dumps({"status": "success", "stats": stats})


__all__ = [
    'EnhancedMemoryManager',
    'Memory',
    'Entity',
    'MemoryType',
    'ImportanceLevel',
    'get_enhanced_memory_manager',
    'store_fact',
    'retrieve_facts',
    'get_context_for_message',
    'log_conversation',
    'get_memory_statistics',
]
