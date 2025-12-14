"""
Blue Robot Improved Memory System
=================================
Provides intelligent memory management with:
- Semantic deduplication (recognizes similar facts even when worded differently)
- Contradiction detection (catches conflicting facts)
- Fact versioning (tracks history of changes)
- Automatic consolidation (merges related memories)
- Confidence scoring (prioritizes reliable facts)

This module is designed to replace/enhance the legacy memory system.
"""

import sqlite3
import os
import re
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from collections import defaultdict
import logging

logger = logging.getLogger("blue.memory.improved")

# Database path
IMPROVED_MEMORY_DB = os.environ.get("BLUE_IMPROVED_MEMORY_DB", "data/blue_memory.db")

# ================================================================================
# DATA CLASSES
# ================================================================================

@dataclass
class Fact:
    """Represents a single fact with metadata."""
    key: str
    value: str
    category: str
    confidence: float  # 0.0 to 1.0
    source: str  # 'extracted', 'user_stated', 'inferred'
    created_at: str
    updated_at: str
    version: int
    supersedes: Optional[str] = None  # Previous value this supersedes

@dataclass
class FactConflict:
    """Represents a detected conflict between facts."""
    fact_key: str
    existing_value: str
    new_value: str
    conflict_type: str  # 'contradiction', 'update', 'refinement'
    resolution: Optional[str] = None  # 'keep_existing', 'use_new', 'merge', 'ask_user'


# ================================================================================
# SEMANTIC SIMILARITY ENGINE
# ================================================================================

class SemanticMatcher:
    """
    Handles semantic similarity matching for facts.
    Uses multiple strategies to detect duplicates and contradictions.
    """

    # Categories that represent the same concept
    # Note: occupation (what you do) and workplace (where you work) are SEPARATE
    CATEGORY_SYNONYMS = {
        'location': {'city', 'town', 'home', 'residence', 'address', 'lives_in', 'based_in'},
        'occupation': {'job', 'profession', 'career', 'role', 'title'},  # What you do
        'workplace': {'employer', 'company', 'organization', 'work_at', 'employed_at'},  # Where you work
        'partner': {'wife', 'husband', 'spouse', 'girlfriend', 'boyfriend', 'significant_other'},
        'children': {'kids', 'daughters', 'sons', 'child', 'children_names'},
        'pet': {'dog', 'cat', 'pet_name', 'puppy', 'kitten', 'dog_name', 'cat_name'},
        'name': {'user_name', 'first_name', 'full_name'},
        'age': {'years_old', 'birth_year'},
        'education': {'school', 'university', 'college', 'degree', 'studied', 'graduated'},
    }

    # Values that are contradictory for the same category
    MUTUALLY_EXCLUSIVE = {
        'dietary': {'vegetarian', 'vegan', 'pescatarian', 'carnivore'},
        'relationship_status': {'single', 'married', 'divorced', 'widowed', 'engaged'},
    }

    # Numeric patterns that might conflict
    NUMERIC_CATEGORIES = {'age', 'birth_year', 'children_count', 'years_experience'}

    def __init__(self):
        # Build reverse lookup for synonyms
        self._synonym_lookup = {}
        for canonical, synonyms in self.CATEGORY_SYNONYMS.items():
            for syn in synonyms:
                self._synonym_lookup[syn] = canonical
            self._synonym_lookup[canonical] = canonical

    def normalize_key(self, key: str) -> str:
        """Normalize a fact key to its canonical form."""
        key_lower = key.lower().strip().replace(' ', '_').replace('-', '_')

        # Check for direct synonym match
        if key_lower in self._synonym_lookup:
            return self._synonym_lookup[key_lower]

        # Check if key contains a synonym
        for syn, canonical in self._synonym_lookup.items():
            if syn in key_lower:
                return canonical

        return key_lower

    def normalize_value(self, value: str) -> str:
        """Normalize a value for comparison."""
        if not value:
            return ""

        # Basic normalization
        normalized = value.lower().strip()

        # Remove common prefixes/suffixes
        prefixes = ['the ', 'a ', 'an ']
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]

        # Normalize whitespace
        normalized = ' '.join(normalized.split())

        return normalized

    def calculate_similarity(self, value1: str, value2: str) -> float:
        """
        Calculate similarity between two values.
        Returns a score from 0.0 (completely different) to 1.0 (identical).
        """
        if not value1 or not value2:
            return 0.0

        norm1 = self.normalize_value(value1)
        norm2 = self.normalize_value(value2)

        # Exact match after normalization
        if norm1 == norm2:
            return 1.0

        # One contains the other
        if norm1 in norm2 or norm2 in norm1:
            return 0.85

        # Sequence matching (handles typos, minor variations)
        seq_ratio = SequenceMatcher(None, norm1, norm2).ratio()

        # Word overlap
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        if words1 and words2:
            word_overlap = len(words1 & words2) / max(len(words1), len(words2))
            # Combine sequence and word overlap
            return max(seq_ratio, word_overlap)

        return seq_ratio

    def are_contradictory(self, key: str, value1: str, value2: str) -> Tuple[bool, str]:
        """
        Check if two values for the same key are contradictory.
        Returns (is_contradictory, reason).
        """
        norm_key = self.normalize_key(key)
        norm1 = self.normalize_value(value1)
        norm2 = self.normalize_value(value2)

        # Same value = not contradictory
        if norm1 == norm2:
            return False, "identical"

        # Check numeric contradictions (age, year, etc.)
        if norm_key in self.NUMERIC_CATEGORIES:
            num1 = self._extract_number(norm1)
            num2 = self._extract_number(norm2)
            if num1 is not None and num2 is not None and num1 != num2:
                # Allow small differences for age (could be birthday passed)
                if norm_key == 'age' and abs(num1 - num2) <= 1:
                    return False, "age_within_tolerance"
                return True, f"numeric_mismatch: {num1} vs {num2}"

        # Check mutually exclusive values
        for category, exclusives in self.MUTUALLY_EXCLUSIVE.items():
            if norm_key == category or category in norm_key:
                matches1 = {e for e in exclusives if e in norm1}
                matches2 = {e for e in exclusives if e in norm2}
                if matches1 and matches2 and matches1 != matches2:
                    return True, f"mutually_exclusive: {matches1} vs {matches2}"

        # Check for explicit negation
        if ('not ' in norm1 and 'not ' not in norm2) or ('not ' in norm2 and 'not ' not in norm1):
            return True, "explicit_negation"

        # High similarity = probably update, not contradiction
        similarity = self.calculate_similarity(value1, value2)
        if similarity > 0.7:
            return False, f"similar_values (similarity={similarity:.2f})"

        # Different names for same relationship type = contradiction
        if norm_key in {'partner', 'spouse', 'wife', 'husband'}:
            if norm1 != norm2 and similarity < 0.5:
                return True, "different_person_same_relationship"

        # Location changes are updates, not contradictions (people move)
        if norm_key == 'location':
            return False, "location_update"

        # Default: significantly different values for same key = potential contradiction
        if similarity < 0.3:
            return True, f"low_similarity ({similarity:.2f})"

        return False, f"acceptable_variation (similarity={similarity:.2f})"

    def _extract_number(self, value: str) -> Optional[int]:
        """Extract a number from a value string."""
        match = re.search(r'\d+', value)
        return int(match.group()) if match else None

    def find_related_keys(self, key: str) -> Set[str]:
        """Find all keys related to the given key."""
        norm_key = self.normalize_key(key)
        related = {key, norm_key}

        # Add all synonyms from the same category
        if norm_key in self.CATEGORY_SYNONYMS:
            related.update(self.CATEGORY_SYNONYMS[norm_key])

        # Check reverse lookup
        if norm_key in self._synonym_lookup:
            canonical = self._synonym_lookup[norm_key]
            related.add(canonical)
            if canonical in self.CATEGORY_SYNONYMS:
                related.update(self.CATEGORY_SYNONYMS[canonical])

        return related


# ================================================================================
# IMPROVED MEMORY SYSTEM
# ================================================================================

class ImprovedMemorySystem:
    """
    Enhanced memory system with semantic deduplication and conflict detection.
    """

    def __init__(self, db_path: str = IMPROVED_MEMORY_DB):
        self.db_path = db_path
        self.matcher = SemanticMatcher()
        self._ensure_database()
        self._facts_cache: Dict[str, Fact] = {}
        self._load_facts_to_cache()

    def _ensure_database(self):
        """Create database schema if not exists."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main facts table with versioning
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_key TEXT NOT NULL,
                normalized_key TEXT NOT NULL,
                value TEXT NOT NULL,
                category TEXT,
                confidence REAL DEFAULT 0.7,
                source TEXT DEFAULT 'extracted',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                version INTEGER DEFAULT 1,
                is_current BOOLEAN DEFAULT TRUE,
                supersedes_id INTEGER,
                FOREIGN KEY (supersedes_id) REFERENCES facts(id)
            )
        """)

        # Index for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_key
            ON facts(normalized_key, is_current)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_category
            ON facts(category, is_current)
        """)

        # Conflict history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conflict_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_key TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                conflict_type TEXT,
                resolution TEXT,
                resolved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        """)

        # Fact relationships table (for linked facts)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fact_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_id_1 INTEGER NOT NULL,
                fact_id_2 INTEGER NOT NULL,
                relationship_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fact_id_1) REFERENCES facts(id),
                FOREIGN KEY (fact_id_2) REFERENCES facts(id)
            )
        """)

        # Legacy compatibility: facts_top table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts_top (
                fact_key TEXT PRIMARY KEY,
                values_concat TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()
        logger.info(f"[MEMORY] Database initialized at {self.db_path}")

    def _load_facts_to_cache(self):
        """Load current facts into memory cache."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM facts WHERE is_current = TRUE
        """)

        for row in cursor.fetchall():
            fact = Fact(
                key=row['fact_key'],
                value=row['value'],
                category=row['category'] or 'general',
                confidence=row['confidence'],
                source=row['source'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                version=row['version']
            )
            self._facts_cache[row['normalized_key']] = fact

        conn.close()
        logger.info(f"[MEMORY] Loaded {len(self._facts_cache)} facts to cache")

    def load_facts(self) -> Dict[str, str]:
        """
        Load facts in legacy format for compatibility.
        Returns dict of {fact_key: value}.
        """
        result = {}

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get current facts
        cursor.execute("""
            SELECT fact_key, value FROM facts
            WHERE is_current = TRUE
            ORDER BY confidence DESC
        """)

        for row in cursor.fetchall():
            result[row['fact_key']] = row['value']

        # Also sync to legacy facts_top table
        cursor.execute("SELECT fact_key, values_concat FROM facts_top")
        for row in cursor.fetchall():
            if row['fact_key'] not in result:
                result[row['fact_key']] = row['values_concat']

        conn.close()
        return result

    def save_facts(self, facts: Dict[str, str], source: str = 'extracted') -> bool:
        """
        Save multiple facts with deduplication and conflict detection.
        """
        if not facts:
            return True

        conflicts = []
        saved_count = 0

        for key, value in facts.items():
            result = self.save_fact(key, value, source=source)
            if result['status'] == 'saved':
                saved_count += 1
            elif result['status'] == 'conflict':
                conflicts.append(result['conflict'])

        if conflicts:
            logger.warning(f"[MEMORY] Detected {len(conflicts)} conflicts while saving facts")
            for conflict in conflicts:
                logger.warning(f"  - {conflict.fact_key}: '{conflict.existing_value}' vs '{conflict.new_value}'")

        logger.info(f"[MEMORY] Saved {saved_count}/{len(facts)} facts")
        return saved_count > 0

    def save_fact(self, key: str, value: str, category: str = None,
                  source: str = 'extracted', confidence: float = 0.7,
                  force: bool = False) -> Dict[str, Any]:
        """
        Save a single fact with full conflict detection.

        Returns:
            {
                'status': 'saved' | 'skipped' | 'conflict' | 'updated',
                'fact': Fact | None,
                'conflict': FactConflict | None,
                'message': str
            }
        """
        if not key or not value:
            return {'status': 'skipped', 'fact': None, 'conflict': None,
                    'message': 'Empty key or value'}

        normalized_key = self.matcher.normalize_key(key)
        normalized_value = self.matcher.normalize_value(value)

        # Auto-detect category if not provided
        if not category:
            category = self._detect_category(normalized_key)

        # Check for existing fact with same or related key
        existing = self._find_existing_fact(normalized_key)

        if existing:
            # Calculate similarity
            similarity = self.matcher.calculate_similarity(existing.value, value)

            # Check for contradiction
            is_contradiction, reason = self.matcher.are_contradictory(
                normalized_key, existing.value, value
            )

            if is_contradiction and not force:
                conflict = FactConflict(
                    fact_key=key,
                    existing_value=existing.value,
                    new_value=value,
                    conflict_type='contradiction',
                    resolution=None
                )

                # Log the conflict
                self._log_conflict(conflict, reason)

                return {
                    'status': 'conflict',
                    'fact': existing,
                    'conflict': conflict,
                    'message': f'Contradiction detected: {reason}'
                }

            # If very similar, skip (duplicate)
            if similarity > 0.95:
                return {
                    'status': 'skipped',
                    'fact': existing,
                    'conflict': None,
                    'message': f'Near-duplicate (similarity={similarity:.2f})'
                }

            # Otherwise, this is an update
            return self._update_fact(existing, key, value, category, source, confidence)

        # No existing fact - save new one
        return self._save_new_fact(key, normalized_key, value, category, source, confidence)

    def _find_existing_fact(self, normalized_key: str) -> Optional[Fact]:
        """Find an existing fact by normalized key or related keys."""
        # Check cache first
        if normalized_key in self._facts_cache:
            return self._facts_cache[normalized_key]

        # Check related keys
        related_keys = self.matcher.find_related_keys(normalized_key)
        for related in related_keys:
            if related in self._facts_cache:
                return self._facts_cache[related]

        # Check database for partial matches
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Try exact match first
        cursor.execute("""
            SELECT * FROM facts
            WHERE normalized_key = ? AND is_current = TRUE
        """, (normalized_key,))

        row = cursor.fetchone()
        if row:
            conn.close()
            return self._row_to_fact(row)

        # Try related keys
        placeholders = ','.join('?' * len(related_keys))
        cursor.execute(f"""
            SELECT * FROM facts
            WHERE normalized_key IN ({placeholders}) AND is_current = TRUE
        """, tuple(related_keys))

        row = cursor.fetchone()
        conn.close()

        return self._row_to_fact(row) if row else None

    def _save_new_fact(self, key: str, normalized_key: str, value: str,
                       category: str, source: str, confidence: float) -> Dict[str, Any]:
        """Save a completely new fact."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO facts
            (fact_key, normalized_key, value, category, confidence, source,
             created_at, updated_at, version, is_current)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, TRUE)
        """, (key, normalized_key, value, category, confidence, source, now, now))

        # Also update legacy facts_top table
        cursor.execute("""
            INSERT OR REPLACE INTO facts_top (fact_key, values_concat, last_updated)
            VALUES (?, ?, ?)
        """, (key, value, now))

        conn.commit()
        conn.close()

        # Update cache
        fact = Fact(
            key=key, value=value, category=category, confidence=confidence,
            source=source, created_at=now, updated_at=now, version=1
        )
        self._facts_cache[normalized_key] = fact

        logger.info(f"[MEMORY] Saved new fact: {key} = {value}")

        return {
            'status': 'saved',
            'fact': fact,
            'conflict': None,
            'message': 'New fact saved'
        }

    def _update_fact(self, existing: Fact, key: str, new_value: str,
                     category: str, source: str, confidence: float) -> Dict[str, Any]:
        """Update an existing fact with version history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        normalized_key = self.matcher.normalize_key(key)

        # Mark old fact as not current
        cursor.execute("""
            UPDATE facts SET is_current = FALSE
            WHERE normalized_key = ? AND is_current = TRUE
        """, (normalized_key,))

        # Get the old fact's ID for reference
        cursor.execute("""
            SELECT id FROM facts WHERE normalized_key = ? ORDER BY version DESC LIMIT 1
        """, (normalized_key,))
        old_row = cursor.fetchone()
        old_id = old_row[0] if old_row else None

        # Insert new version
        new_version = existing.version + 1
        cursor.execute("""
            INSERT INTO facts
            (fact_key, normalized_key, value, category, confidence, source,
             created_at, updated_at, version, is_current, supersedes_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE, ?)
        """, (key, normalized_key, new_value, category, confidence, source,
              existing.created_at, now, new_version, old_id))

        # Update legacy table
        cursor.execute("""
            INSERT OR REPLACE INTO facts_top (fact_key, values_concat, last_updated)
            VALUES (?, ?, ?)
        """, (key, new_value, now))

        # Log the update
        cursor.execute("""
            INSERT INTO conflict_history
            (fact_key, old_value, new_value, conflict_type, resolution, notes)
            VALUES (?, ?, ?, 'update', 'use_new', 'Automatic update')
        """, (key, existing.value, new_value))

        conn.commit()
        conn.close()

        # Update cache
        updated_fact = Fact(
            key=key, value=new_value, category=category, confidence=confidence,
            source=source, created_at=existing.created_at, updated_at=now,
            version=new_version, supersedes=existing.value
        )
        self._facts_cache[normalized_key] = updated_fact

        logger.info(f"[MEMORY] Updated fact: {key} = {existing.value} -> {new_value}")

        return {
            'status': 'updated',
            'fact': updated_fact,
            'conflict': None,
            'message': f'Updated from v{existing.version} to v{new_version}'
        }

    def _log_conflict(self, conflict: FactConflict, reason: str):
        """Log a detected conflict for review."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO conflict_history
            (fact_key, old_value, new_value, conflict_type, resolution, notes)
            VALUES (?, ?, ?, ?, 'pending', ?)
        """, (conflict.fact_key, conflict.existing_value, conflict.new_value,
              conflict.conflict_type, reason))

        conn.commit()
        conn.close()

        logger.warning(f"[MEMORY] Conflict logged: {conflict.fact_key} - {reason}")

    def _detect_category(self, normalized_key: str) -> str:
        """Auto-detect category from key name."""
        categories = {
            'personal': ['name', 'age', 'birthday', 'gender'],
            'location': ['location', 'city', 'home', 'address', 'country'],
            'family': ['partner', 'wife', 'husband', 'spouse', 'child', 'daughter',
                      'son', 'mother', 'father', 'sibling', 'brother', 'sister'],
            'work': ['occupation', 'job', 'workplace', 'company', 'business', 'career'],
            'education': ['education', 'school', 'university', 'degree'],
            'preferences': ['favorite', 'prefer', 'like', 'hobby', 'interest'],
            'health': ['allergy', 'dietary', 'medical', 'medication'],
            'pets': ['pet', 'dog', 'cat', 'puppy', 'kitten'],
            'contact': ['email', 'phone', 'address'],
        }

        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in normalized_key:
                    return category

        return 'general'

    def _row_to_fact(self, row: sqlite3.Row) -> Fact:
        """Convert a database row to a Fact object."""
        return Fact(
            key=row['fact_key'],
            value=row['value'],
            category=row['category'] or 'general',
            confidence=row['confidence'],
            source=row['source'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            version=row['version']
        )

    # ================================================================================
    # QUERYING AND RETRIEVAL
    # ================================================================================

    def get_fact(self, key: str) -> Optional[str]:
        """Get a fact value by key."""
        normalized_key = self.matcher.normalize_key(key)

        if normalized_key in self._facts_cache:
            return self._facts_cache[normalized_key].value

        # Check related keys
        related = self.matcher.find_related_keys(normalized_key)
        for related_key in related:
            if related_key in self._facts_cache:
                return self._facts_cache[related_key].value

        return None

    def get_fact_with_metadata(self, key: str) -> Optional[Fact]:
        """Get a fact with full metadata."""
        normalized_key = self.matcher.normalize_key(key)
        return self._facts_cache.get(normalized_key)

    def get_facts_by_category(self, category: str) -> Dict[str, str]:
        """Get all facts in a category."""
        result = {}
        for norm_key, fact in self._facts_cache.items():
            if fact.category == category:
                result[fact.key] = fact.value
        return result

    def get_all_facts(self) -> Dict[str, str]:
        """Get all current facts."""
        return {fact.key: fact.value for fact in self._facts_cache.values()}

    def search_facts(self, query: str) -> List[Fact]:
        """Search facts by key or value."""
        query_lower = query.lower()
        results = []

        for norm_key, fact in self._facts_cache.items():
            if (query_lower in fact.key.lower() or
                query_lower in fact.value.lower() or
                query_lower in norm_key):
                results.append(fact)

        # Sort by confidence
        results.sort(key=lambda f: f.confidence, reverse=True)
        return results

    def get_fact_history(self, key: str) -> List[Dict[str, Any]]:
        """Get the version history of a fact."""
        normalized_key = self.matcher.normalize_key(key)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM facts
            WHERE normalized_key = ?
            ORDER BY version DESC
        """, (normalized_key,))

        history = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return history

    def get_pending_conflicts(self) -> List[Dict[str, Any]]:
        """Get all unresolved conflicts."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM conflict_history
            WHERE resolution = 'pending'
            ORDER BY resolved_at DESC
        """)

        conflicts = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return conflicts

    def resolve_conflict(self, conflict_id: int, resolution: str,
                        resolved_value: str = None) -> bool:
        """
        Resolve a pending conflict.

        resolution: 'keep_existing', 'use_new', 'custom'
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get the conflict
        cursor.execute("SELECT * FROM conflict_history WHERE id = ?", (conflict_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False

        # Update conflict resolution
        cursor.execute("""
            UPDATE conflict_history
            SET resolution = ?, resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (resolution, conflict_id))

        # If using new value, save it
        if resolution == 'use_new' and row[3]:  # new_value
            self.save_fact(row[1], row[3], force=True)  # fact_key, new_value
        elif resolution == 'custom' and resolved_value:
            self.save_fact(row[1], resolved_value, force=True)

        conn.commit()
        conn.close()

        logger.info(f"[MEMORY] Resolved conflict {conflict_id} with '{resolution}'")
        return True

    # ================================================================================
    # CONSOLIDATION AND MAINTENANCE
    # ================================================================================

    def consolidate_facts(self) -> Dict[str, Any]:
        """
        Consolidate and clean up the fact database.
        - Merge related facts
        - Remove very low confidence facts
        - Update normalized keys
        """
        stats = {
            'merged': 0,
            'removed': 0,
            'normalized': 0
        }

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Find facts with same normalized key
        cursor.execute("""
            SELECT normalized_key, COUNT(*) as count
            FROM facts WHERE is_current = TRUE
            GROUP BY normalized_key
            HAVING count > 1
        """)

        duplicates = cursor.fetchall()

        for dup in duplicates:
            norm_key = dup['normalized_key']

            # Get all facts for this key
            cursor.execute("""
                SELECT * FROM facts
                WHERE normalized_key = ? AND is_current = TRUE
                ORDER BY confidence DESC, updated_at DESC
            """, (norm_key,))

            facts = cursor.fetchall()

            if len(facts) > 1:
                # Keep the highest confidence one
                keeper = facts[0]

                # Mark others as not current
                for fact in facts[1:]:
                    cursor.execute("""
                        UPDATE facts SET is_current = FALSE
                        WHERE id = ?
                    """, (fact['id'],))
                    stats['merged'] += 1

        # Remove very low confidence facts (< 0.3)
        cursor.execute("""
            UPDATE facts SET is_current = FALSE
            WHERE confidence < 0.3 AND is_current = TRUE
        """)
        stats['removed'] = cursor.rowcount

        conn.commit()
        conn.close()

        # Refresh cache
        self._facts_cache.clear()
        self._load_facts_to_cache()

        logger.info(f"[MEMORY] Consolidation complete: {stats}")
        return stats

    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {}

        # Total facts
        cursor.execute("SELECT COUNT(*) FROM facts WHERE is_current = TRUE")
        stats['total_facts'] = cursor.fetchone()[0]

        # Facts by category
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM facts WHERE is_current = TRUE
            GROUP BY category
        """)
        stats['by_category'] = {row[0]: row[1] for row in cursor.fetchall()}

        # Version counts
        cursor.execute("SELECT AVG(version), MAX(version) FROM facts WHERE is_current = TRUE")
        row = cursor.fetchone()
        stats['avg_version'] = round(row[0], 2) if row[0] else 0
        stats['max_version'] = row[1] or 0

        # Pending conflicts
        cursor.execute("SELECT COUNT(*) FROM conflict_history WHERE resolution = 'pending'")
        stats['pending_conflicts'] = cursor.fetchone()[0]

        # Confidence distribution
        cursor.execute("""
            SELECT
                CASE
                    WHEN confidence >= 0.8 THEN 'high'
                    WHEN confidence >= 0.5 THEN 'medium'
                    ELSE 'low'
                END as level,
                COUNT(*) as count
            FROM facts WHERE is_current = TRUE
            GROUP BY level
        """)
        stats['confidence_distribution'] = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()
        return stats

    # ================================================================================
    # FACT EXTRACTION
    # ================================================================================

    def extract_and_save_facts(self, messages: list) -> bool:
        """
        Extract facts from conversation messages and save with deduplication.
        This is the enhanced version of the legacy extract_and_save_facts.
        """
        if not messages:
            return False

        extracted_facts = {}

        for msg in messages:
            if msg.get('role') not in ['user', 'assistant']:
                continue

            content = msg.get('content', '')
            if not content or len(content) < 10:
                continue

            # Skip code/technical content
            if content.strip().startswith(('{', '[', '```', 'import ', 'def ', 'class ')):
                continue

            # Extract facts using patterns
            facts = self._extract_facts_from_text(content)

            # Merge with existing (later messages override earlier)
            extracted_facts.update(facts)

        if extracted_facts:
            return self.save_facts(extracted_facts, source='extracted')

        return False

    def _extract_facts_from_text(self, text: str) -> Dict[str, str]:
        """Extract facts from a text string using pattern matching."""
        facts = {}

        # All extraction patterns organized by category
        patterns = {
            # Personal info
            'user_name': [
                r"my name is ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                r"i'?m ([A-Z][a-z]+)(?:\s|,|\.|$)",
                r"call me ([A-Z][a-z]+)",
            ],
            'age': [
                r"i'?m (\d{1,2}) years old",
                r"i am (\d{1,2}) years old",
            ],
            'birthday': [
                r"my birthday is ([A-Za-z]+ \d{1,2})",
                r"i was born (?:on )?([A-Za-z]+ \d{1,2})",
            ],

            # Location
            'location': [
                r"i live in ([A-Z][a-zA-Z\s,]+?)(?:\.|,|$|\sand\s)",
                r"i'?m (?:from|in|based in) ([A-Z][a-zA-Z\s]+?)(?:\.|,|$)",
                r"we live in ([A-Z][a-zA-Z\s,]+?)(?:\.|,|$)",
            ],

            # Work/Education
            'workplace': [
                r"i (?:work|teach) at ([A-Z][a-zA-Z\s&.]+?)(?:\.|,|$)",
                r"i work for ([A-Z][a-zA-Z\s&]+?)(?:\.|,|$)",
            ],
            'occupation': [
                r"i'?m (?:a|an) ([a-z][a-z\s]+(?:teacher|professor|engineer|developer|doctor|scientist|artist|writer|designer|manager|director))",
            ],
            'education': [
                r"i studied at ([A-Z][a-zA-Z\s&]+?)(?:\.|,|$)",
                r"i graduated from ([A-Z][a-zA-Z\s&]+?)(?:\.|,|$)",
            ],

            # Family
            'partner_name': [
                r"my (?:partner|wife|husband|spouse)(?:'s name)? is ([A-Z][a-z]+)",
            ],
            'children_names': [
                r"my (?:daughters?|sons?|children|kids) (?:are|named) ([A-Z][a-zA-Z,\s&]+?)(?:\.|$)",
            ],

            # Health
            'allergy': [
                r"i'?m allergic to ([a-zA-Z\s,]+?)(?:\.|$)",
                r"i have (?:a |an )?([a-zA-Z\s]+) allergy",
            ],
            'dietary': [
                r"i'?m (?:a )?(vegetarian|vegan|pescatarian|gluten[- ]free|keto|paleo)",
            ],

            # Contact
            'email': [
                r"my email is ([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            ],
            'phone': [
                r"my (?:phone|number|cell) is ([0-9\-\(\)\s]{10,20})",
            ],

            # Languages
            'languages': [
                r"i speak ([A-Z][a-z]+(?:,? (?:and )?[A-Z][a-z]+)*)",
                r"i'?m fluent in ([A-Z][a-z]+(?:,? (?:and )?[A-Z][a-z]+)*)",
            ],
        }

        # Family relations - dynamically add patterns
        for relation in ['partner', 'wife', 'husband', 'spouse', 'daughter', 'son',
                        'mother', 'father', 'mom', 'dad', 'brother', 'sister']:
            key = f'{relation}_name'
            if key not in patterns:
                patterns[key] = [
                    rf"my {relation}(?:'s name)? is ([A-Z][a-z]+)",
                    rf"(?:this is |meet )?my {relation} ([A-Z][a-z]+)",
                ]

        # Pet patterns
        for pet in ['dog', 'cat', 'pet', 'puppy', 'kitten']:
            key = f'{pet}_name'
            patterns[key] = [
                rf"my {pet}(?:'s name)? is ([A-Z][a-z]+)",
                rf"i have a {pet} (?:named |called )?([A-Z][a-z]+)",
            ]

        # Apply patterns
        for fact_key, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip().rstrip('.,;')

                    # Validate
                    if self._validate_fact_value(fact_key, value):
                        facts[fact_key] = value
                        break  # Found a match, move to next fact type

        # Handle favorites
        if 'my favorite' in text.lower():
            match = re.search(r"my favorite ([a-z\s]+) is ([a-zA-Z0-9\s]+?)(?:\.|,|$)",
                            text.lower())
            if match:
                pref_type = match.group(1).strip().replace(' ', '_')
                pref_value = match.group(2).strip().title()
                if len(pref_type) <= 20 and len(pref_value) <= 50:
                    facts[f'favorite_{pref_type}'] = pref_value

        return facts

    def _validate_fact_value(self, key: str, value: str) -> bool:
        """Validate an extracted fact value."""
        if not value or len(value) < 2:
            return False

        # Length limits by type
        limits = {
            'name': (2, 30),
            'age': (1, 3),
            'location': (2, 100),
            'workplace': (2, 100),
            'email': (5, 100),
            'phone': (7, 20),
        }

        for limit_key, (min_len, max_len) in limits.items():
            if limit_key in key.lower():
                if not (min_len <= len(value) <= max_len):
                    return False

        # Age validation
        if 'age' in key.lower():
            try:
                age = int(value)
                if not (1 <= age <= 120):
                    return False
            except ValueError:
                return False

        # Name validation (should be alpha)
        if 'name' in key.lower():
            if not value.replace(' ', '').replace('-', '').replace("'", '').isalpha():
                return False

        return True


# ================================================================================
# GLOBAL INSTANCE AND FACTORY
# ================================================================================

_memory_system_instance: Optional[ImprovedMemorySystem] = None

def get_memory_system() -> ImprovedMemorySystem:
    """Get the global memory system instance."""
    global _memory_system_instance
    if _memory_system_instance is None:
        _memory_system_instance = ImprovedMemorySystem()
    return _memory_system_instance


def reset_memory_system():
    """Reset the global memory system (for testing)."""
    global _memory_system_instance
    _memory_system_instance = None


# ================================================================================
# MIGRATION AND UTILITIES
# ================================================================================

def migrate_legacy_facts(legacy_db_path: str = "data/blue.db") -> Dict[str, Any]:
    """
    Migrate facts from the legacy blue.db to the improved memory system.

    Returns migration statistics.
    """
    stats = {
        'migrated': 0,
        'skipped_duplicate': 0,
        'skipped_conflict': 0,
        'errors': 0
    }

    if not os.path.exists(legacy_db_path):
        logger.warning(f"[MIGRATION] Legacy database not found: {legacy_db_path}")
        return stats

    mem = get_memory_system()

    try:
        conn = sqlite3.connect(legacy_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all facts from legacy facts_top table
        cursor.execute("SELECT fact_key, values_concat FROM facts_top")
        rows = cursor.fetchall()

        for row in rows:
            key = row['fact_key']
            value = row['values_concat']

            if not key or not value:
                continue

            result = mem.save_fact(
                key=key,
                value=value,
                source='migrated',
                confidence=0.8  # Moderate confidence for migrated facts
            )

            if result['status'] == 'saved':
                stats['migrated'] += 1
            elif result['status'] == 'skipped':
                stats['skipped_duplicate'] += 1
            elif result['status'] == 'conflict':
                stats['skipped_conflict'] += 1
            else:
                stats['errors'] += 1

        conn.close()
        logger.info(f"[MIGRATION] Complete: {stats}")

    except Exception as e:
        logger.error(f"[MIGRATION] Error: {e}")
        stats['errors'] += 1

    return stats


def get_memory_health_report() -> Dict[str, Any]:
    """
    Generate a comprehensive memory health report.

    Returns a dict with:
    - stats: Basic statistics
    - issues: List of detected issues
    - recommendations: Suggested actions
    """
    mem = get_memory_system()
    stats = mem.get_stats()

    issues = []
    recommendations = []

    # Check for pending conflicts
    if stats['pending_conflicts'] > 0:
        issues.append(f"{stats['pending_conflicts']} unresolved fact conflicts")
        recommendations.append("Review and resolve conflicts using resolve_conflict()")

    # Check confidence distribution
    conf_dist = stats.get('confidence_distribution', {})
    low_confidence = conf_dist.get('low', 0)
    total = stats['total_facts']

    if total > 0 and low_confidence / total > 0.3:
        issues.append(f"{low_confidence} facts have low confidence ({low_confidence/total*100:.1f}%)")
        recommendations.append("Run consolidate_facts() to clean up low-confidence facts")

    # Check for high version numbers (lots of updates)
    if stats['max_version'] > 5:
        issues.append(f"Some facts have been updated {stats['max_version']} times")
        recommendations.append("Review frequently-updated facts for accuracy")

    return {
        'stats': stats,
        'issues': issues,
        'recommendations': recommendations,
        'health_score': max(0, 100 - len(issues) * 20)  # Simple health score
    }


def export_facts_to_json(output_path: str = "data/facts_export.json") -> bool:
    """Export all facts to a JSON file for backup."""
    mem = get_memory_system()

    try:
        facts = []
        for norm_key, fact in mem._facts_cache.items():
            facts.append({
                'key': fact.key,
                'normalized_key': norm_key,
                'value': fact.value,
                'category': fact.category,
                'confidence': fact.confidence,
                'source': fact.source,
                'version': fact.version,
                'created_at': fact.created_at,
                'updated_at': fact.updated_at
            })

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'exported_at': datetime.now().isoformat(),
                'fact_count': len(facts),
                'facts': facts
            }, f, indent=2)

        logger.info(f"[EXPORT] Exported {len(facts)} facts to {output_path}")
        return True

    except Exception as e:
        logger.error(f"[EXPORT] Error: {e}")
        return False


def import_facts_from_json(input_path: str) -> Dict[str, int]:
    """Import facts from a JSON backup file."""
    stats = {'imported': 0, 'skipped': 0, 'errors': 0}

    if not os.path.exists(input_path):
        logger.error(f"[IMPORT] File not found: {input_path}")
        return stats

    mem = get_memory_system()

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        facts = data.get('facts', [])

        for fact_data in facts:
            result = mem.save_fact(
                key=fact_data['key'],
                value=fact_data['value'],
                category=fact_data.get('category'),
                source='imported',
                confidence=fact_data.get('confidence', 0.7)
            )

            if result['status'] in ['saved', 'updated']:
                stats['imported'] += 1
            elif result['status'] == 'skipped':
                stats['skipped'] += 1
            else:
                stats['errors'] += 1

        logger.info(f"[IMPORT] Complete: {stats}")

    except Exception as e:
        logger.error(f"[IMPORT] Error: {e}")
        stats['errors'] += 1

    return stats


# ================================================================================
# BLUE MEMORY MANAGEMENT API
# ================================================================================

class MemoryManager:
    """
    High-level memory management interface for Blue.
    Provides user-friendly methods for memory operations.
    """

    def __init__(self):
        self.memory = get_memory_system()

    def remember(self, key: str, value: str, confidence: float = 0.9) -> str:
        """
        Explicitly remember a fact (user-stated).
        Returns a human-readable status message.
        """
        result = self.memory.save_fact(
            key=key,
            value=value,
            source='user_stated',
            confidence=confidence
        )

        if result['status'] == 'saved':
            return f"[OK] I'll remember that {key} is {value}"
        elif result['status'] == 'updated':
            old_val = result['fact'].supersedes if result['fact'] else 'unknown'
            return f"[OK] Updated: {key} changed from '{old_val}' to '{value}'"
        elif result['status'] == 'skipped':
            return f"I already know that {key} is {value}"
        elif result['status'] == 'conflict':
            conflict = result['conflict']
            return (f"[CONFLICT] I thought {key} was '{conflict.existing_value}' "
                   f"but you said '{conflict.new_value}'. Which is correct?")
        else:
            return f"Failed to save: {result['message']}"

    def recall(self, key: str) -> Optional[str]:
        """
        Recall a fact by key.
        Returns the value or None if not found.
        """
        return self.memory.get_fact(key)

    def forget(self, key: str) -> str:
        """
        Mark a fact as no longer current (doesn't delete history).
        """
        normalized_key = self.memory.matcher.normalize_key(key)

        conn = sqlite3.connect(self.memory.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE facts SET is_current = FALSE
            WHERE normalized_key = ? AND is_current = TRUE
        """, (normalized_key,))

        affected = cursor.rowcount
        conn.commit()
        conn.close()

        if affected > 0:
            # Remove from cache
            if normalized_key in self.memory._facts_cache:
                del self.memory._facts_cache[normalized_key]
            return f"[OK] Forgot {key}"
        else:
            return f"I don't have any record of {key}"

    def correct(self, key: str, new_value: str) -> str:
        """
        Correct a fact (force update even if contradictory).
        """
        result = self.memory.save_fact(
            key=key,
            value=new_value,
            source='user_corrected',
            confidence=0.95,
            force=True
        )

        if result['status'] in ['saved', 'updated']:
            return f"[OK] Corrected: {key} is now {new_value}"
        else:
            return f"Failed to correct: {result['message']}"

    def list_conflicts(self) -> List[Dict[str, Any]]:
        """Get all pending conflicts."""
        return self.memory.get_pending_conflicts()

    def resolve(self, conflict_id: int, keep_existing: bool = True,
                custom_value: str = None) -> str:
        """
        Resolve a pending conflict.
        """
        if custom_value:
            resolution = 'custom'
        elif keep_existing:
            resolution = 'keep_existing'
        else:
            resolution = 'use_new'

        success = self.memory.resolve_conflict(conflict_id, resolution, custom_value)

        if success:
            return f"[OK] Conflict {conflict_id} resolved with '{resolution}'"
        else:
            return f"Failed to resolve conflict {conflict_id}"

    def summarize(self) -> str:
        """Get a human-readable memory summary."""
        stats = self.memory.get_stats()
        facts = self.memory.get_all_facts()

        lines = [
            f"=== Memory Summary ===",
            f"   Total facts: {stats['total_facts']}",
            f"   Categories: {', '.join(f'{k}({v})' for k, v in stats['by_category'].items())}",
            f"   Pending conflicts: {stats['pending_conflicts']}",
            "",
            "--- Key Facts ---"
        ]

        # Show important facts
        priority_keys = ['user_name', 'name', 'location', 'occupation', 'partner_name',
                        'children_names', 'age', 'birthday']

        for key in priority_keys:
            if key in facts:
                lines.append(f"   - {key}: {facts[key]}")

        # Show some other facts
        other_facts = [(k, v) for k, v in facts.items() if k not in priority_keys]
        if other_facts:
            lines.append("")
            lines.append("--- Other Facts ---")
            for key, value in other_facts[:10]:  # Limit to 10
                lines.append(f"   - {key}: {value}")
            if len(other_facts) > 10:
                lines.append(f"   ... and {len(other_facts) - 10} more")

        return "\n".join(lines)

    def cleanup(self) -> str:
        """Run memory consolidation and cleanup."""
        stats = self.memory.consolidate_facts()
        return (f"[OK] Memory cleanup complete:\n"
               f"   Merged: {stats['merged']}\n"
               f"   Removed (low confidence): {stats['removed']}\n"
               f"   Normalized: {stats['normalized']}")


# Global manager instance
_manager_instance: Optional[MemoryManager] = None

def get_memory_manager() -> MemoryManager:
    """Get the global memory manager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = MemoryManager()
    return _manager_instance


# ================================================================================
# CLI TESTING
# ================================================================================

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("Blue Improved Memory System - Test Suite")
    print("=" * 60)

    # Create test instance
    mem = ImprovedMemorySystem("data/test_memory.db")

    # Test 1: Save new facts
    print("\n[TEST 1] Saving new facts...")
    result = mem.save_fact("user_name", "Alex", source="user_stated", confidence=0.9)
    print(f"  Result: {result['status']} - {result['message']}")

    result = mem.save_fact("location", "Kitchener, Ontario", source="user_stated", confidence=0.9)
    print(f"  Result: {result['status']} - {result['message']}")

    result = mem.save_fact("occupation", "professor", source="user_stated", confidence=0.8)
    print(f"  Result: {result['status']} - {result['message']}")

    # Test 2: Duplicate detection
    print("\n[TEST 2] Testing duplicate detection...")
    result = mem.save_fact("user_name", "Alex", source="extracted")
    print(f"  Result: {result['status']} - {result['message']}")

    # Test 3: Similar value detection
    print("\n[TEST 3] Testing similar value detection...")
    result = mem.save_fact("location", "Kitchener Ontario", source="extracted")
    print(f"  Result: {result['status']} - {result['message']}")

    # Test 4: Contradiction detection
    print("\n[TEST 4] Testing contradiction detection...")
    result = mem.save_fact("user_name", "John", source="extracted")
    print(f"  Result: {result['status']} - {result['message']}")
    if result['conflict']:
        print(f"  Conflict: {result['conflict'].existing_value} vs {result['conflict'].new_value}")

    # Test 5: Update detection
    print("\n[TEST 5] Testing update detection...")
    result = mem.save_fact("age", "35", source="user_stated")
    print(f"  Result: {result['status']} - {result['message']}")

    result = mem.save_fact("age", "36", source="user_stated")
    print(f"  Result: {result['status']} - {result['message']}")

    # Test 6: Get statistics
    print("\n[TEST 6] Memory Statistics...")
    stats = mem.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Test 7: Load facts (legacy compatibility)
    print("\n[TEST 7] Loading facts (legacy format)...")
    facts = mem.load_facts()
    for key, value in facts.items():
        print(f"  {key}: {value}")

    # Test 8: Fact extraction from text
    print("\n[TEST 8] Extracting facts from conversation...")
    messages = [
        {"role": "user", "content": "Hi, my name is Sarah and I live in Toronto."},
        {"role": "user", "content": "I'm 28 years old and I work at Google."},
        {"role": "user", "content": "My dog's name is Buddy."},
    ]
    mem.extract_and_save_facts(messages)

    facts = mem.load_facts()
    print("  Extracted facts:")
    for key, value in facts.items():
        print(f"    {key}: {value}")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
