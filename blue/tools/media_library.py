"""
Blue Robot Media Library Tool
==============================
Manage and organize your media content including podcasts, audiobooks, and playlists.

Features:
- Subscribe to podcasts
- Track listening progress
- Organize media into collections
- Smart recommendations
- Download management
- Playback history
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

# ================================================================================
# CONFIGURATION
# ================================================================================

MEDIA_LIBRARY_DB = os.environ.get("BLUE_MEDIA_LIBRARY_DB", "data/media_library.db")


class MediaType(Enum):
    PODCAST = "podcast"
    AUDIOBOOK = "audiobook"
    MUSIC_PLAYLIST = "music_playlist"
    VIDEO_PLAYLIST = "video_playlist"
    OTHER = "other"


class MediaStatus(Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


@dataclass
class MediaItem:
    """Represents a media item (episode, chapter, track)."""
    id: str
    parent_id: str  # ID of the podcast/audiobook/playlist
    title: str
    description: str
    duration_seconds: int
    media_url: Optional[str] = None
    published_date: Optional[float] = None
    episode_number: Optional[int] = None
    season_number: Optional[int] = None
    progress_seconds: int = 0
    status: MediaStatus = MediaStatus.NEW
    created_at: float = field(default_factory=lambda: datetime.datetime.now().timestamp())
    last_played: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "title": self.title,
            "description": self.description,
            "duration_seconds": self.duration_seconds,
            "duration_formatted": self.format_duration(self.duration_seconds),
            "media_url": self.media_url,
            "published_date": self.published_date,
            "episode_number": self.episode_number,
            "season_number": self.season_number,
            "progress_seconds": self.progress_seconds,
            "progress_percent": self.get_progress_percent(),
            "status": self.status.value,
            "created_at": self.created_at,
            "last_played": self.last_played,
        }

    def get_progress_percent(self) -> int:
        """Get progress as percentage."""
        if self.duration_seconds <= 0:
            return 0
        return min(100, int((self.progress_seconds / self.duration_seconds) * 100))

    @staticmethod
    def format_duration(seconds: int) -> str:
        """Format duration in human-readable form."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"


@dataclass
class MediaCollection:
    """Represents a media collection (podcast, audiobook series, playlist)."""
    id: str
    title: str
    description: str
    media_type: MediaType
    author: Optional[str] = None
    feed_url: Optional[str] = None
    image_url: Optional[str] = None
    subscribed: bool = True
    auto_download: bool = False
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: datetime.datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.datetime.now().timestamp())
    last_checked: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "media_type": self.media_type.value,
            "author": self.author,
            "feed_url": self.feed_url,
            "image_url": self.image_url,
            "subscribed": self.subscribed,
            "auto_download": self.auto_download,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_checked": self.last_checked,
        }


# ================================================================================
# MEDIA LIBRARY MANAGER
# ================================================================================

class MediaLibraryManager:
    """Manages media library with persistent storage."""

    def __init__(self, db_path: str = MEDIA_LIBRARY_DB):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                media_type TEXT,
                author TEXT,
                feed_url TEXT,
                image_url TEXT,
                subscribed INTEGER,
                auto_download INTEGER,
                tags TEXT,
                created_at REAL,
                updated_at REAL,
                last_checked REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS media_items (
                id TEXT PRIMARY KEY,
                parent_id TEXT,
                title TEXT NOT NULL,
                description TEXT,
                duration_seconds INTEGER,
                media_url TEXT,
                published_date REAL,
                episode_number INTEGER,
                season_number INTEGER,
                progress_seconds INTEGER,
                status TEXT,
                created_at REAL,
                last_played REAL,
                FOREIGN KEY (parent_id) REFERENCES collections (id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playback_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_item_id TEXT,
                played_at REAL,
                duration_seconds INTEGER,
                FOREIGN KEY (media_item_id) REFERENCES media_items (id)
            )
        """)

        conn.commit()
        conn.close()

    def create_collection(
        self,
        title: str,
        description: str,
        media_type: MediaType,
        author: Optional[str] = None,
        feed_url: Optional[str] = None,
        image_url: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> MediaCollection:
        """Create a new media collection."""
        collection = MediaCollection(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            media_type=media_type,
            author=author,
            feed_url=feed_url,
            image_url=image_url,
            tags=tags or [],
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO collections VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            collection.id, collection.title, collection.description,
            collection.media_type.value, collection.author, collection.feed_url,
            collection.image_url, 1 if collection.subscribed else 0,
            1 if collection.auto_download else 0, json.dumps(collection.tags),
            collection.created_at, collection.updated_at, collection.last_checked
        ))

        conn.commit()
        conn.close()

        return collection

    def add_media_item(
        self,
        parent_id: str,
        title: str,
        description: str,
        duration_seconds: int,
        media_url: Optional[str] = None,
        episode_number: Optional[int] = None,
        season_number: Optional[int] = None,
        published_date: Optional[float] = None,
    ) -> MediaItem:
        """Add a media item to a collection."""
        item = MediaItem(
            id=str(uuid.uuid4()),
            parent_id=parent_id,
            title=title,
            description=description,
            duration_seconds=duration_seconds,
            media_url=media_url,
            episode_number=episode_number,
            season_number=season_number,
            published_date=published_date,
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO media_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.id, item.parent_id, item.title, item.description,
            item.duration_seconds, item.media_url, item.published_date,
            item.episode_number, item.season_number, item.progress_seconds,
            item.status.value, item.created_at, item.last_played
        ))

        conn.commit()
        conn.close()

        return item

    def get_collection(self, collection_id: str) -> Optional[MediaCollection]:
        """Get a collection by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM collections WHERE id = ?", (collection_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_collection(row)

    def list_collections(
        self,
        media_type: Optional[MediaType] = None,
        subscribed_only: bool = False
    ) -> List[MediaCollection]:
        """List all collections."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM collections WHERE 1=1"
        params = []

        if media_type:
            query += " AND media_type = ?"
            params.append(media_type.value)

        if subscribed_only:
            query += " AND subscribed = 1"

        query += " ORDER BY title"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_collection(row) for row in rows]

    def get_media_items(
        self,
        parent_id: str,
        status: Optional[MediaStatus] = None
    ) -> List[MediaItem]:
        """Get media items from a collection."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM media_items WHERE parent_id = ?"
        params = [parent_id]

        if status:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY episode_number DESC, published_date DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_media_item(row) for row in rows]

    def update_progress(
        self,
        media_item_id: str,
        progress_seconds: int,
        mark_complete: bool = False
    ) -> bool:
        """Update playback progress for a media item."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        status = MediaStatus.COMPLETED.value if mark_complete else MediaStatus.IN_PROGRESS.value

        cursor.execute("""
            UPDATE media_items SET
                progress_seconds = ?,
                status = ?,
                last_played = ?
            WHERE id = ?
        """, (progress_seconds, status, time.time(), media_item_id))

        success = cursor.rowcount > 0

        # Log playback
        if success:
            cursor.execute("""
                INSERT INTO playback_history (media_item_id, played_at, duration_seconds)
                VALUES (?, ?, ?)
            """, (media_item_id, time.time(), progress_seconds))

        conn.commit()
        conn.close()

        return success

    def search_media(self, query: str) -> Dict[str, List]:
        """Search for media items and collections."""
        query_lower = query.lower()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Search collections
        cursor.execute("""
            SELECT * FROM collections
            WHERE LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(author) LIKE ?
            ORDER BY title
        """, (f"%{query_lower}%", f"%{query_lower}%", f"%{query_lower}%"))

        collection_rows = cursor.fetchall()

        # Search media items
        cursor.execute("""
            SELECT * FROM media_items
            WHERE LOWER(title) LIKE ? OR LOWER(description) LIKE ?
            ORDER BY published_date DESC
        """, (f"%{query_lower}%", f"%{query_lower}%"))

        item_rows = cursor.fetchall()
        conn.close()

        return {
            "collections": [self._row_to_collection(row) for row in collection_rows],
            "items": [self._row_to_media_item(row) for row in item_rows],
        }

    def get_recently_played(self, limit: int = 10) -> List[MediaItem]:
        """Get recently played media items."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM media_items
            WHERE last_played IS NOT NULL
            ORDER BY last_played DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_media_item(row) for row in rows]

    def get_in_progress(self) -> List[MediaItem]:
        """Get media items currently in progress."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM media_items
            WHERE status = ?
            ORDER BY last_played DESC
        """, (MediaStatus.IN_PROGRESS.value,))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_media_item(row) for row in rows]

    def _row_to_collection(self, row: tuple) -> MediaCollection:
        """Convert database row to MediaCollection."""
        return MediaCollection(
            id=row[0],
            title=row[1],
            description=row[2] or "",
            media_type=MediaType(row[3]),
            author=row[4],
            feed_url=row[5],
            image_url=row[6],
            subscribed=bool(row[7]),
            auto_download=bool(row[8]),
            tags=json.loads(row[9]) if row[9] else [],
            created_at=row[10],
            updated_at=row[11],
            last_checked=row[12],
        )

    def _row_to_media_item(self, row: tuple) -> MediaItem:
        """Convert database row to MediaItem."""
        return MediaItem(
            id=row[0],
            parent_id=row[1],
            title=row[2],
            description=row[3] or "",
            duration_seconds=row[4],
            media_url=row[5],
            published_date=row[6],
            episode_number=row[7],
            season_number=row[8],
            progress_seconds=row[9],
            status=MediaStatus(row[10]),
            created_at=row[11],
            last_played=row[12],
        )


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_media_library_manager: Optional[MediaLibraryManager] = None


def get_media_library_manager() -> MediaLibraryManager:
    """Get the global media library manager instance."""
    global _media_library_manager
    if _media_library_manager is None:
        _media_library_manager = MediaLibraryManager()
    return _media_library_manager


# ================================================================================
# COMMAND FUNCTIONS
# ================================================================================

def subscribe_podcast_cmd(
    title: str,
    feed_url: str,
    description: str = "",
    author: Optional[str] = None,
) -> str:
    """
    Subscribe to a podcast.

    Args:
        title: Podcast title
        feed_url: RSS feed URL
        description: Podcast description
        author: Podcast author

    Returns:
        JSON result
    """
    try:
        manager = get_media_library_manager()

        collection = manager.create_collection(
            title=title,
            description=description,
            media_type=MediaType.PODCAST,
            author=author,
            feed_url=feed_url,
        )

        return json.dumps({
            "success": True,
            "collection_id": collection.id,
            "title": collection.title,
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to subscribe: {str(e)}"
        })


def list_subscriptions_cmd(media_type: Optional[str] = None) -> str:
    """
    List all subscriptions.

    Args:
        media_type: Filter by media type

    Returns:
        JSON result with subscriptions
    """
    try:
        manager = get_media_library_manager()

        # Parse media type
        type_filter = None
        if media_type:
            try:
                type_filter = MediaType(media_type.lower())
            except ValueError:
                pass

        collections = manager.list_collections(
            media_type=type_filter,
            subscribed_only=True
        )

        return json.dumps({
            "success": True,
            "count": len(collections),
            "collections": [c.to_dict() for c in collections]
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to list subscriptions: {str(e)}"
        })


def list_episodes_cmd(collection_id: str, unplayed_only: bool = False) -> str:
    """
    List episodes from a collection.

    Args:
        collection_id: Collection ID
        unplayed_only: Only show unplayed episodes

    Returns:
        JSON result with episodes
    """
    try:
        manager = get_media_library_manager()

        status_filter = MediaStatus.NEW if unplayed_only else None
        items = manager.get_media_items(collection_id, status_filter)

        return json.dumps({
            "success": True,
            "count": len(items),
            "items": [item.to_dict() for item in items]
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to list episodes: {str(e)}"
        })


def update_progress_cmd(
    media_item_id: str,
    progress_seconds: int,
    mark_complete: bool = False
) -> str:
    """
    Update playback progress.

    Args:
        media_item_id: Media item ID
        progress_seconds: Current progress in seconds
        mark_complete: Mark as completed

    Returns:
        JSON result
    """
    try:
        manager = get_media_library_manager()
        success = manager.update_progress(media_item_id, progress_seconds, mark_complete)

        return json.dumps({
            "success": success,
            "message": "Progress updated" if success else "Item not found"
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to update progress: {str(e)}"
        })


def search_media_cmd(query: str) -> str:
    """
    Search media library.

    Args:
        query: Search query

    Returns:
        JSON result with search results
    """
    try:
        manager = get_media_library_manager()
        results = manager.search_media(query)

        return json.dumps({
            "success": True,
            "collections_found": len(results["collections"]),
            "items_found": len(results["items"]),
            "collections": [c.to_dict() for c in results["collections"]],
            "items": [item.to_dict() for item in results["items"]],
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to search: {str(e)}"
        })


def get_recently_played_cmd(limit: int = 10) -> str:
    """
    Get recently played items.

    Args:
        limit: Maximum number of items

    Returns:
        JSON result
    """
    try:
        manager = get_media_library_manager()
        items = manager.get_recently_played(limit)

        return json.dumps({
            "success": True,
            "count": len(items),
            "items": [item.to_dict() for item in items]
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to get recently played: {str(e)}"
        })


def get_in_progress_cmd() -> str:
    """Get items currently in progress."""
    try:
        manager = get_media_library_manager()
        items = manager.get_in_progress()

        return json.dumps({
            "success": True,
            "count": len(items),
            "items": [item.to_dict() for item in items]
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to get in progress items: {str(e)}"
        })


def execute_media_library_command(command: str, **params) -> str:
    """
    Execute a media library command.

    Args:
        command: Command name
        **params: Command parameters

    Returns:
        JSON result
    """
    commands = {
        "subscribe": subscribe_podcast_cmd,
        "list": list_subscriptions_cmd,
        "episodes": list_episodes_cmd,
        "progress": update_progress_cmd,
        "search": search_media_cmd,
        "recent": get_recently_played_cmd,
        "in_progress": get_in_progress_cmd,
    }

    handler = commands.get(command)
    if not handler:
        return json.dumps({
            "success": False,
            "error": f"Unknown media library command: {command}"
        })

    return handler(**params)
