"""
Blue Robot Location & Places Tool
==================================
Manage favorite locations, saved places, and location-based features.

Features:
- Save favorite locations with custom names
- Store addresses and coordinates
- Location categories (home, work, favorite restaurants, etc.)
- Quick access to frequently used locations
- Distance calculations
- Location-based reminders
- Integration with maps and navigation
"""

from __future__ import annotations

import datetime
import json
import math
import os
import re
import sqlite3
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import requests

# ================================================================================
# CONFIGURATION
# ================================================================================

LOCATIONS_DB = os.environ.get("BLUE_LOCATIONS_DB", "data/locations.db")


class LocationCategory(Enum):
    HOME = "home"
    WORK = "work"
    RESTAURANT = "restaurant"
    SHOP = "shop"
    GYM = "gym"
    SCHOOL = "school"
    HOSPITAL = "hospital"
    PARK = "park"
    FRIEND = "friend"
    FAMILY = "family"
    ENTERTAINMENT = "entertainment"
    OTHER = "other"


@dataclass
class Location:
    """Represents a saved location."""
    id: str
    name: str
    address: str
    latitude: float
    longitude: float
    category: LocationCategory
    notes: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    visit_count: int = 0
    last_visited: Optional[float] = None
    favorite: bool = False
    created_at: float = field(default_factory=lambda: datetime.datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.datetime.now().timestamp())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "category": self.category.value,
            "notes": self.notes,
            "phone": self.phone,
            "website": self.website,
            "tags": self.tags,
            "visit_count": self.visit_count,
            "last_visited": self.last_visited,
            "favorite": self.favorite,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def distance_to(self, other: Location) -> float:
        """Calculate distance to another location in kilometers using Haversine formula."""
        R = 6371  # Earth's radius in kilometers

        lat1 = math.radians(self.latitude)
        lat2 = math.radians(other.latitude)
        dlat = math.radians(other.latitude - self.latitude)
        dlon = math.radians(other.longitude - self.longitude)

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))

        return R * c


# ================================================================================
# LOCATION MANAGER
# ================================================================================

class LocationManager:
    """Manages saved locations with persistent storage."""

    def __init__(self, db_path: str = LOCATIONS_DB):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                address TEXT,
                latitude REAL,
                longitude REAL,
                category TEXT,
                notes TEXT,
                phone TEXT,
                website TEXT,
                tags TEXT,
                visit_count INTEGER,
                last_visited REAL,
                favorite INTEGER,
                created_at REAL,
                updated_at REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS location_visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_id TEXT,
                visited_at REAL,
                duration_minutes INTEGER,
                notes TEXT,
                FOREIGN KEY (location_id) REFERENCES locations (id)
            )
        """)

        conn.commit()
        conn.close()

    def add_location(
        self,
        name: str,
        address: str,
        category: LocationCategory = LocationCategory.OTHER,
        notes: Optional[str] = None,
        phone: Optional[str] = None,
        website: Optional[str] = None,
        tags: Optional[List[str]] = None,
        favorite: bool = False,
    ) -> Optional[Location]:
        """Add a new location."""
        # Geocode the address
        coords = self._geocode(address)
        if not coords:
            return None

        lat, lon = coords

        location = Location(
            id=str(uuid.uuid4()),
            name=name,
            address=address,
            latitude=lat,
            longitude=lon,
            category=category,
            notes=notes,
            phone=phone,
            website=website,
            tags=tags or [],
            favorite=favorite,
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO locations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            location.id, location.name, location.address,
            location.latitude, location.longitude, location.category.value,
            location.notes, location.phone, location.website,
            json.dumps(location.tags), location.visit_count,
            location.last_visited, 1 if location.favorite else 0,
            location.created_at, location.updated_at
        ))

        conn.commit()
        conn.close()

        return location

    def get_location(self, location_id: str) -> Optional[Location]:
        """Get a location by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM locations WHERE id = ?", (location_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_location(row)

    def find_location_by_name(self, name: str) -> Optional[Location]:
        """Find a location by name (case-insensitive)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM locations WHERE LOWER(name) = ? LIMIT 1",
            (name.lower(),)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_location(row)

    def list_locations(
        self,
        category: Optional[LocationCategory] = None,
        favorites_only: bool = False
    ) -> List[Location]:
        """List all locations."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM locations WHERE 1=1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category.value)

        if favorites_only:
            query += " AND favorite = 1"

        query += " ORDER BY name"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_location(row) for row in rows]

    def search_locations(self, query: str) -> List[Location]:
        """Search locations by name, address, or notes."""
        query_lower = query.lower()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM locations
            WHERE LOWER(name) LIKE ? OR LOWER(address) LIKE ? OR LOWER(notes) LIKE ?
            ORDER BY favorite DESC, name
        """, (f"%{query_lower}%", f"%{query_lower}%", f"%{query_lower}%"))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_location(row) for row in rows]

    def update_location(self, location_id: str, **updates) -> bool:
        """Update a location."""
        location = self.get_location(location_id)
        if not location:
            return False

        # Update fields
        for key, value in updates.items():
            if hasattr(location, key):
                setattr(location, key, value)

        # If address changed, re-geocode
        if "address" in updates:
            coords = self._geocode(updates["address"])
            if coords:
                location.latitude, location.longitude = coords

        location.updated_at = datetime.datetime.now().timestamp()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE locations SET
                name = ?, address = ?, latitude = ?, longitude = ?,
                category = ?, notes = ?, phone = ?, website = ?,
                tags = ?, favorite = ?, updated_at = ?
            WHERE id = ?
        """, (
            location.name, location.address, location.latitude, location.longitude,
            location.category.value, location.notes, location.phone, location.website,
            json.dumps(location.tags), 1 if location.favorite else 0,
            location.updated_at, location.id
        ))

        conn.commit()
        conn.close()

        return True

    def delete_location(self, location_id: str) -> bool:
        """Delete a location."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM locations WHERE id = ?", (location_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    def log_visit(
        self,
        location_id: str,
        duration_minutes: int = 0,
        notes: Optional[str] = None
    ) -> bool:
        """Log a visit to a location."""
        location = self.get_location(location_id)
        if not location:
            return False

        now = datetime.datetime.now().timestamp()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Log the visit
        cursor.execute("""
            INSERT INTO location_visits (location_id, visited_at, duration_minutes, notes)
            VALUES (?, ?, ?, ?)
        """, (location_id, now, duration_minutes, notes))

        # Update location stats
        cursor.execute("""
            UPDATE locations SET
                visit_count = visit_count + 1,
                last_visited = ?
            WHERE id = ?
        """, (now, location_id))

        conn.commit()
        conn.close()

        return True

    def get_nearby_locations(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 10.0
    ) -> List[Tuple[Location, float]]:
        """Get locations within a radius, sorted by distance."""
        all_locations = self.list_locations()
        reference = Location(
            id="", name="", address="",
            latitude=latitude, longitude=longitude,
            category=LocationCategory.OTHER
        )

        nearby = []
        for loc in all_locations:
            distance = reference.distance_to(loc)
            if distance <= radius_km:
                nearby.append((loc, distance))

        # Sort by distance
        nearby.sort(key=lambda x: x[1])
        return nearby

    def _geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """Convert address to coordinates."""
        try:
            url = "https://geocoding-api.open-meteo.com/v1/search"
            params = {"name": address, "count": 1, "language": "en", "format": "json"}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if not results:
                return None

            result = results[0]
            return result["latitude"], result["longitude"]

        except Exception as e:
            print(f"Error geocoding address: {e}")
            return None

    def _row_to_location(self, row: tuple) -> Location:
        """Convert database row to Location."""
        return Location(
            id=row[0],
            name=row[1],
            address=row[2] or "",
            latitude=row[3],
            longitude=row[4],
            category=LocationCategory(row[5]),
            notes=row[6],
            phone=row[7],
            website=row[8],
            tags=json.loads(row[9]) if row[9] else [],
            visit_count=row[10],
            last_visited=row[11],
            favorite=bool(row[12]),
            created_at=row[13],
            updated_at=row[14],
        )


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_location_manager: Optional[LocationManager] = None


def get_location_manager() -> LocationManager:
    """Get the global location manager instance."""
    global _location_manager
    if _location_manager is None:
        _location_manager = LocationManager()
    return _location_manager


# ================================================================================
# COMMAND FUNCTIONS
# ================================================================================

def add_location_cmd(
    name: str,
    address: str,
    category: str = "other",
    notes: Optional[str] = None,
    phone: Optional[str] = None,
    favorite: bool = False,
) -> str:
    """
    Add a new location.

    Args:
        name: Location name
        address: Full address
        category: Location category
        notes: Additional notes
        phone: Phone number
        favorite: Mark as favorite

    Returns:
        JSON result
    """
    try:
        manager = get_location_manager()

        # Parse category
        try:
            cat = LocationCategory(category.lower())
        except ValueError:
            cat = LocationCategory.OTHER

        location = manager.add_location(
            name=name,
            address=address,
            category=cat,
            notes=notes,
            phone=phone,
            favorite=favorite,
        )

        if not location:
            return json.dumps({
                "success": False,
                "error": "Could not geocode address"
            })

        return json.dumps({
            "success": True,
            "location_id": location.id,
            "name": location.name,
            "address": location.address,
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to add location: {str(e)}"
        })


def list_locations_cmd(category: Optional[str] = None, favorites_only: bool = False) -> str:
    """
    List saved locations.

    Args:
        category: Filter by category
        favorites_only: Show only favorites

    Returns:
        JSON result with locations
    """
    try:
        manager = get_location_manager()

        # Parse category filter
        cat_filter = None
        if category:
            try:
                cat_filter = LocationCategory(category.lower())
            except ValueError:
                pass

        locations = manager.list_locations(cat_filter, favorites_only)

        return json.dumps({
            "success": True,
            "count": len(locations),
            "locations": [loc.to_dict() for loc in locations]
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to list locations: {str(e)}"
        })


def search_locations_cmd(query: str) -> str:
    """
    Search for locations.

    Args:
        query: Search query

    Returns:
        JSON result with matching locations
    """
    try:
        manager = get_location_manager()
        locations = manager.search_locations(query)

        return json.dumps({
            "success": True,
            "count": len(locations),
            "locations": [loc.to_dict() for loc in locations]
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to search locations: {str(e)}"
        })


def get_location_cmd(location_name: str) -> str:
    """
    Get a specific location by name.

    Args:
        location_name: Name of the location

    Returns:
        JSON result with location details
    """
    try:
        manager = get_location_manager()
        location = manager.find_location_by_name(location_name)

        if not location:
            return json.dumps({
                "success": False,
                "error": f"Location not found: {location_name}"
            })

        return json.dumps({
            "success": True,
            "location": location.to_dict()
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to get location: {str(e)}"
        })


def delete_location_cmd(location_name: str) -> str:
    """
    Delete a location.

    Args:
        location_name: Name of the location to delete

    Returns:
        JSON result
    """
    try:
        manager = get_location_manager()
        location = manager.find_location_by_name(location_name)

        if not location:
            return json.dumps({
                "success": False,
                "error": f"Location not found: {location_name}"
            })

        success = manager.delete_location(location.id)

        return json.dumps({
            "success": success,
            "deleted_name": location.name if success else None
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to delete location: {str(e)}"
        })


def log_visit_cmd(location_name: str, duration_minutes: int = 0) -> str:
    """
    Log a visit to a location.

    Args:
        location_name: Name of the location
        duration_minutes: Duration of visit in minutes

    Returns:
        JSON result
    """
    try:
        manager = get_location_manager()
        location = manager.find_location_by_name(location_name)

        if not location:
            return json.dumps({
                "success": False,
                "error": f"Location not found: {location_name}"
            })

        success = manager.log_visit(location.id, duration_minutes)

        return json.dumps({
            "success": success,
            "location": location.name,
            "total_visits": location.visit_count + 1 if success else location.visit_count
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to log visit: {str(e)}"
        })


def execute_location_command(command: str, **params) -> str:
    """
    Execute a location command.

    Args:
        command: Command name
        **params: Command parameters

    Returns:
        JSON result
    """
    commands = {
        "add": add_location_cmd,
        "list": list_locations_cmd,
        "search": search_locations_cmd,
        "get": get_location_cmd,
        "delete": delete_location_cmd,
        "visit": log_visit_cmd,
    }

    handler = commands.get(command)
    if not handler:
        return json.dumps({
            "success": False,
            "error": f"Unknown location command: {command}"
        })

    return handler(**params)
