"""
Blue Robot Visual Memory System
Allows Blue to recognize and remember people, places, and objects he sees.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# Visual memory database location
try:
    from config import VISUAL_MEMORY_DB_PATH
    VISUAL_MEMORY_DB = str(VISUAL_MEMORY_DB_PATH)
except ImportError:
    VISUAL_MEMORY_DB = os.environ.get("BLUE_VISUAL_MEMORY_DB", "data/visual_memory.db")

class VisualMemory:
    """Manages Blue's visual memory - what he knows about people, places, and things."""
    
    def __init__(self, db_path: str = VISUAL_MEMORY_DB):
        self.db_path = db_path
        self._ensure_database()
    
    def _ensure_database(self):
        """Create the visual memory database if it doesn't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # People Blue knows
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                typical_appearance TEXT,
                relationship TEXT,
                common_locations TEXT,
                notes TEXT,
                last_seen TIMESTAMP,
                times_seen INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Places Blue recognizes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS places (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                typical_contents TEXT,
                typical_lighting TEXT,
                notes TEXT,
                last_seen TIMESTAMP,
                times_seen INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Objects Blue knows about
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS objects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                description TEXT,
                typical_location TEXT,
                notes TEXT,
                last_seen TIMESTAMP,
                times_seen INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Observation log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scene_description TEXT,
                people_present TEXT,
                location TEXT,
                notable_objects TEXT,
                context TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def add_person(self, name: str, description: str = None, 
                   typical_appearance: str = None, relationship: str = None,
                   common_locations: str = None, notes: str = None) -> bool:
        """Add or update a person in visual memory."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO people 
                (name, description, typical_appearance, relationship, common_locations, notes, last_seen, times_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT times_seen FROM people WHERE name = ?), 0))
            """, (name, description, typical_appearance, relationship, common_locations, notes, 
                  datetime.now(), name))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[VISUAL-MEMORY] Error adding person: {e}")
            return False
    
    def add_place(self, name: str, description: str = None,
                  typical_contents: str = None, typical_lighting: str = None,
                  notes: str = None) -> bool:
        """Add or update a place in visual memory."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO places 
                (name, description, typical_contents, typical_lighting, notes, last_seen, times_seen)
                VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT times_seen FROM places WHERE name = ?), 0))
            """, (name, description, typical_contents, typical_lighting, notes, datetime.now(), name))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[VISUAL-MEMORY] Error adding place: {e}")
            return False
    
    def add_object(self, name: str, category: str = None, description: str = None,
                   typical_location: str = None, notes: str = None) -> bool:
        """Add or update an object in visual memory."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO objects 
                (name, category, description, typical_location, notes, last_seen, times_seen)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (name, category, description, typical_location, notes, datetime.now()))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[VISUAL-MEMORY] Error adding object: {e}")
            return False
    
    def update_seen(self, entity_type: str, name: str):
        """Update when an entity was last seen."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            table = f"{entity_type}s" if not entity_type.endswith('s') else entity_type
            cursor.execute(f"""
                UPDATE {table}
                SET last_seen = ?, times_seen = times_seen + 1
                WHERE name = ?
            """, (datetime.now(), name))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[VISUAL-MEMORY] Error updating seen status: {e}")
    
    def log_observation(self, scene_description: str, people_present: List[str] = None,
                       location: str = None, notable_objects: List[str] = None,
                       context: str = None):
        """Log what Blue observes."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO observations 
                (scene_description, people_present, location, notable_objects, context)
                VALUES (?, ?, ?, ?, ?)
            """, (
                scene_description,
                json.dumps(people_present) if people_present else None,
                location,
                json.dumps(notable_objects) if notable_objects else None,
                context
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[VISUAL-MEMORY] Error logging observation: {e}")
    
    def get_all_people(self) -> List[Dict[str, Any]]:
        """Get all people Blue knows."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        rows = cursor.execute("SELECT * FROM people ORDER BY name").fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_all_places(self) -> List[Dict[str, Any]]:
        """Get all places Blue recognizes."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        rows = cursor.execute("SELECT * FROM places ORDER BY name").fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_person(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific person."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        row = cursor.execute("SELECT * FROM people WHERE name = ?", (name,)).fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_place(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific place."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        row = cursor.execute("SELECT * FROM places WHERE name = ?", (name,)).fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_recognition_context(self) -> str:
        """Get formatted context for visual recognition."""
        people = self.get_all_people()
        places = self.get_all_places()
        
        context_parts = []
        
        if people:
            context_parts.append("=== PEOPLE YOU KNOW ===")
            for person in people:
                parts = [f"• {person['name']}"]
                if person['relationship']:
                    parts.append(f"({person['relationship']})")
                if person['typical_appearance']:
                    parts.append(f"- Appearance: {person['typical_appearance']}")
                if person['description']:
                    parts.append(f"- {person['description']}")
                if person['common_locations']:
                    parts.append(f"- Often found: {person['common_locations']}")
                context_parts.append(" ".join(parts))
        
        if places:
            context_parts.append("\n=== PLACES YOU RECOGNIZE ===")
            for place in places:
                parts = [f"• {place['name']}"]
                if place['description']:
                    parts.append(f"- {place['description']}")
                if place['typical_contents']:
                    parts.append(f"- Typically contains: {place['typical_contents']}")
                context_parts.append(" ".join(parts))
        
        return "\n".join(context_parts)
    
    def seed_family_data(self):
        """Seed the database with Alex's family information."""
        # Add family members
        self.add_person(
            name="Alex",
            relationship="Your creator and primary user",
            typical_appearance="Man with beard and glasses, often in casual clothing",
            description="Teaches at York University and Wilfrid Laurier University. Works on AI ethics and runs The Circumference Centre. Very knowledgeable about technology and philosophy.",
            common_locations="Office, living room, kitchen",
            notes="Built you with Stella. Cares deeply about privacy and local AI systems."
        )
        
        self.add_person(
            name="Stella",
            relationship="Alex's partner, artist and teacher",
            typical_appearance="Woman, artistic style",
            description="Creative and thoughtful. Works as an artist and teacher.",
            common_locations="Art studio, living room, kitchen",
            notes="Co-created your identity with Alex."
        )
        
        self.add_person(
            name="Emmy",
            relationship="Alex and Stella's daughter",
            typical_appearance="Young girl",
            description="One of the three daughters.",
            common_locations="Living room, playroom, throughout the house"
        )
        
        self.add_person(
            name="Athena",
            relationship="Alex and Stella's daughter",
            typical_appearance="Young girl",
            description="One of the three daughters.",
            common_locations="Living room, playroom, throughout the house"
        )
        
        self.add_person(
            name="Vilda",
            relationship="Alex and Stella's daughter",
            typical_appearance="Young girl",
            description="One of the three daughters.",
            common_locations="Living room, playroom, throughout the house"
        )
        
        # Add common places
        self.add_place(
            name="Alex's Office",
            description="Where Alex works on his computer, teaches, and develops AI projects",
            typical_contents="Desktop computer with high-end specs (Intel i9-13900K, RTX 5090), monitors, desk, books, papers",
            typical_lighting="Natural light during day, desk lamp at night"
        )
        
        self.add_place(
            name="Stella's Studio",
            description="Stella's creative workspace",
            typical_contents="Art supplies, canvases, projects in progress, creative materials",
            typical_lighting="Good natural light for artwork"
        )
        
        self.add_place(
            name="Living Room",
            description="Main family gathering space",
            typical_contents="Couch, chairs, often toys from the kids, comfortable seating",
            typical_lighting="Varies - bright during day, warm lamps in evening"
        )
        
        self.add_place(
            name="Kitchen",
            description="Where meals are prepared and family often gathers",
            typical_contents="Appliances, coffee maker, dining table, dishes",
            typical_lighting="Bright overhead lighting, natural light from windows"
        )
        
        print("[VISUAL-MEMORY] Seeded family and location data")


def initialize_visual_memory():
    """Initialize the visual memory system and seed with family data if needed."""
    vm = VisualMemory()
    
    # Check if we need to seed data
    if not vm.get_all_people():
        print("[VISUAL-MEMORY] No existing data, seeding family information...")
        vm.seed_family_data()
    
    return vm


# Global instance
_visual_memory_instance = None

def get_visual_memory() -> VisualMemory:
    """Get the global visual memory instance."""
    global _visual_memory_instance
    if _visual_memory_instance is None:
        _visual_memory_instance = initialize_visual_memory()
    return _visual_memory_instance
