"""
Blue Robot Social Media Management Tool
========================================
Manage social media presence across Facebook, Twitter/X, and Instagram.

Features:
- Draft and schedule posts
- Multi-platform posting
- Engagement tracking and analytics
- Content calendar management
- Auto-suggestions for hashtags and captions
- Respond to messages and comments (with approval)
- Track post performance
- Content ideas and recommendations
"""

import datetime
import hashlib
import json
import os
import re
import sqlite3
import uuid
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ================================================================================
# CONFIGURATION
# ================================================================================

SOCIAL_MEDIA_DB = os.environ.get("BLUE_SOCIAL_MEDIA_DB", os.path.join("data", "social_media.db"))


class Platform(Enum):
    """Social media platforms"""
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    THREADS = "threads"


class PostStatus(Enum):
    """Status of social media posts"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    POSTED = "posted"
    FAILED = "failed"
    ARCHIVED = "archived"


class ContentType(Enum):
    """Type of content"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    LINK = "link"
    POLL = "poll"
    STORY = "story"


class ApprovalStatus(Enum):
    """Approval status for posts"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


@dataclass
class SocialPost:
    """Represents a social media post"""
    id: str
    platform: Platform
    content: str
    content_type: ContentType
    status: PostStatus
    approval_status: ApprovalStatus
    scheduled_time: Optional[float]
    posted_time: Optional[float]
    media_urls: List[str]
    hashtags: List[str]
    mentions: List[str]
    created_at: float
    updated_at: float
    platform_post_id: Optional[str] = None
    engagement: Dict[str, int] = None  # likes, shares, comments

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "platform": self.platform.value,
            "content": self.content,
            "content_type": self.content_type.value,
            "status": self.status.value,
            "approval_status": self.approval_status.value,
            "media_urls": self.media_urls,
            "hashtags": self.hashtags,
            "mentions": self.mentions,
            "created_at": datetime.datetime.fromtimestamp(self.created_at).isoformat(),
            "updated_at": datetime.datetime.fromtimestamp(self.updated_at).isoformat(),
            "platform_post_id": self.platform_post_id,
            "engagement": self.engagement or {}
        }
        if self.scheduled_time:
            result["scheduled_time"] = datetime.datetime.fromtimestamp(self.scheduled_time).isoformat()
            result["scheduled_time_human"] = datetime.datetime.fromtimestamp(self.scheduled_time).strftime("%b %d, %Y %I:%M %p")
        if self.posted_time:
            result["posted_time"] = datetime.datetime.fromtimestamp(self.posted_time).isoformat()
        return result


@dataclass
class ContentIdea:
    """Represents a content idea/suggestion"""
    id: str
    topic: str
    description: str
    suggested_platforms: List[str]
    suggested_hashtags: List[str]
    priority: int  # 1-5
    created_at: float
    used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "description": self.description,
            "suggested_platforms": self.suggested_platforms,
            "suggested_hashtags": self.suggested_hashtags,
            "priority": self.priority,
            "created_at": datetime.datetime.fromtimestamp(self.created_at).isoformat(),
            "used": self.used
        }


@dataclass
class PlatformAccount:
    """Represents a connected social media account"""
    id: str
    platform: Platform
    username: str
    display_name: str
    is_active: bool
    access_token: Optional[str]  # Encrypted
    token_expires: Optional[float]
    last_synced: Optional[float]
    connected_at: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform.value,
            "username": self.username,
            "display_name": self.display_name,
            "is_active": self.is_active,
            "token_expires": datetime.datetime.fromtimestamp(self.token_expires).isoformat() if self.token_expires else None,
            "last_synced": datetime.datetime.fromtimestamp(self.last_synced).isoformat() if self.last_synced else None,
            "connected_at": datetime.datetime.fromtimestamp(self.connected_at).isoformat()
        }


# ================================================================================
# SOCIAL MEDIA MANAGER
# ================================================================================

class SocialMediaManager:
    """Manages social media posts, scheduling, and engagement"""

    def __init__(self, db_path: str = SOCIAL_MEDIA_DB):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database tables"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Posts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL,
                status TEXT NOT NULL,
                approval_status TEXT NOT NULL,
                scheduled_time REAL,
                posted_time REAL,
                media_urls TEXT,
                hashtags TEXT,
                mentions TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                platform_post_id TEXT,
                engagement TEXT
            )
        """)

        # Content ideas table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_ideas (
                id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                description TEXT NOT NULL,
                suggested_platforms TEXT,
                suggested_hashtags TEXT,
                priority INTEGER DEFAULT 3,
                created_at REAL NOT NULL,
                used INTEGER DEFAULT 0
            )
        """)

        # Platform accounts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS platform_accounts (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                username TEXT NOT NULL,
                display_name TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                access_token TEXT,
                token_expires REAL,
                last_synced REAL,
                connected_at REAL NOT NULL
            )
        """)

        # Engagement tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS engagement_history (
                id TEXT PRIMARY KEY,
                post_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                likes INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                impressions INTEGER DEFAULT 0,
                FOREIGN KEY (post_id) REFERENCES posts (id)
            )
        """)

        # Content calendar table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_calendar (
                id TEXT PRIMARY KEY,
                date REAL NOT NULL,
                theme TEXT,
                notes TEXT,
                posts_planned INTEGER DEFAULT 0,
                posts_completed INTEGER DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    # ==================== POST MANAGEMENT ====================

    def create_post(self, platform: str, content: str, content_type: str = "text",
                   scheduled_time: float = None, media_urls: List[str] = None,
                   hashtags: List[str] = None, mentions: List[str] = None) -> SocialPost:
        """Create a new post draft"""
        post_id = str(uuid.uuid4())[:12]
        now = datetime.datetime.now().timestamp()

        try:
            platform_enum = Platform(platform.lower())
        except ValueError:
            platform_enum = Platform.FACEBOOK

        try:
            type_enum = ContentType(content_type.lower())
        except ValueError:
            type_enum = ContentType.TEXT

        # Auto-suggest hashtags if none provided
        if not hashtags:
            hashtags = self._suggest_hashtags(content)

        post = SocialPost(
            id=post_id,
            platform=platform_enum,
            content=content,
            content_type=type_enum,
            status=PostStatus.DRAFT if not scheduled_time else PostStatus.SCHEDULED,
            approval_status=ApprovalStatus.PENDING,
            scheduled_time=scheduled_time,
            posted_time=None,
            media_urls=media_urls or [],
            hashtags=hashtags or [],
            mentions=mentions or [],
            created_at=now,
            updated_at=now
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO posts (id, platform, content, content_type, status, approval_status,
                             scheduled_time, posted_time, media_urls, hashtags, mentions,
                             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (post.id, post.platform.value, post.content, post.content_type.value,
              post.status.value, post.approval_status.value, post.scheduled_time,
              post.posted_time, json.dumps(post.media_urls), json.dumps(post.hashtags),
              json.dumps(post.mentions), post.created_at, post.updated_at))
        conn.commit()
        conn.close()

        return post

    def get_post(self, post_id: str) -> Optional[SocialPost]:
        """Get a post by ID"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return SocialPost(
                id=row[0], platform=Platform(row[1]), content=row[2],
                content_type=ContentType(row[3]), status=PostStatus(row[4]),
                approval_status=ApprovalStatus(row[5]), scheduled_time=row[6],
                posted_time=row[7], media_urls=json.loads(row[8] or "[]"),
                hashtags=json.loads(row[9] or "[]"), mentions=json.loads(row[10] or "[]"),
                created_at=row[11], updated_at=row[12], platform_post_id=row[13],
                engagement=json.loads(row[14] or "{}")
            )
        return None

    def update_post(self, post_id: str, content: str = None, scheduled_time: float = None,
                   approval_status: str = None, hashtags: List[str] = None) -> Optional[SocialPost]:
        """Update a post"""
        post = self.get_post(post_id)
        if not post:
            return None

        if content:
            post.content = content
        if scheduled_time is not None:
            post.scheduled_time = scheduled_time
            post.status = PostStatus.SCHEDULED
        if approval_status:
            try:
                post.approval_status = ApprovalStatus(approval_status.lower())
            except ValueError:
                pass
        if hashtags is not None:
            post.hashtags = hashtags

        post.updated_at = datetime.datetime.now().timestamp()

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE posts SET content=?, scheduled_time=?, approval_status=?,
                           hashtags=?, updated_at=?, status=?
            WHERE id=?
        """, (post.content, post.scheduled_time, post.approval_status.value,
              json.dumps(post.hashtags), post.updated_at, post.status.value, post.id))
        conn.commit()
        conn.close()

        return post

    def approve_post(self, post_id: str) -> Optional[SocialPost]:
        """Approve a post for publishing"""
        return self.update_post(post_id, approval_status="approved")

    def get_posts(self, platform: str = None, status: str = None,
                 approval_status: str = None, limit: int = 50) -> List[SocialPost]:
        """Get posts with filtering"""
        conn = self._get_conn()
        cursor = conn.cursor()

        sql = "SELECT * FROM posts WHERE 1=1"
        params = []

        if platform:
            sql += " AND platform = ?"
            params.append(platform.lower())
        if status:
            sql += " AND status = ?"
            params.append(status.lower())
        if approval_status:
            sql += " AND approval_status = ?"
            params.append(approval_status.lower())

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            SocialPost(
                id=row[0], platform=Platform(row[1]), content=row[2],
                content_type=ContentType(row[3]), status=PostStatus(row[4]),
                approval_status=ApprovalStatus(row[5]), scheduled_time=row[6],
                posted_time=row[7], media_urls=json.loads(row[8] or "[]"),
                hashtags=json.loads(row[9] or "[]"), mentions=json.loads(row[10] or "[]"),
                created_at=row[11], updated_at=row[12], platform_post_id=row[13],
                engagement=json.loads(row[14] or "{}")
            )
            for row in rows
        ]

    def get_scheduled_posts(self, upcoming_hours: int = 24) -> List[SocialPost]:
        """Get posts scheduled in the next N hours"""
        now = datetime.datetime.now().timestamp()
        cutoff = (datetime.datetime.now() + datetime.timedelta(hours=upcoming_hours)).timestamp()

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM posts
            WHERE status = 'scheduled' AND scheduled_time >= ? AND scheduled_time <= ?
            ORDER BY scheduled_time ASC
        """, (now, cutoff))
        rows = cursor.fetchall()
        conn.close()

        return [
            SocialPost(
                id=row[0], platform=Platform(row[1]), content=row[2],
                content_type=ContentType(row[3]), status=PostStatus(row[4]),
                approval_status=ApprovalStatus(row[5]), scheduled_time=row[6],
                posted_time=row[7], media_urls=json.loads(row[8] or "[]"),
                hashtags=json.loads(row[9] or "[]"), mentions=json.loads(row[10] or "[]"),
                created_at=row[11], updated_at=row[12], platform_post_id=row[13],
                engagement=json.loads(row[14] or "{}")
            )
            for row in rows
        ]

    # ==================== CONTENT GENERATION ====================

    def generate_post_variations(self, topic: str, count: int = 3) -> List[str]:
        """Generate multiple post variations for a topic"""
        # Placeholder - would integrate with LLM for actual generation
        variations = [
            f"Excited to share insights about {topic}! 🚀",
            f"Just learned something amazing about {topic}. Let me tell you...",
            f"Here's what you need to know about {topic} 💡"
        ]
        return variations[:count]

    def _suggest_hashtags(self, content: str, max_tags: int = 5) -> List[str]:
        """Auto-suggest relevant hashtags based on content"""
        # Extract keywords
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())

        # Common stop words to exclude
        stop_words = {'this', 'that', 'with', 'from', 'have', 'will', 'your', 'about',
                     'what', 'when', 'where', 'just', 'like', 'more', 'some', 'than'}

        keywords = [w for w in words if w not in stop_words]

        # Get unique keywords
        unique_keywords = []
        seen = set()
        for word in keywords:
            if word not in seen:
                unique_keywords.append(word)
                seen.add(word)

        # Return as hashtags
        hashtags = [f"#{word}" for word in unique_keywords[:max_tags]]
        return hashtags

    def suggest_posting_times(self, platform: str) -> List[str]:
        """Suggest optimal posting times for a platform"""
        # Based on general best practices
        optimal_times = {
            "facebook": ["9:00 AM", "1:00 PM", "3:00 PM"],
            "twitter": ["8:00 AM", "12:00 PM", "5:00 PM"],
            "instagram": ["11:00 AM", "2:00 PM", "7:00 PM"],
            "linkedin": ["7:30 AM", "12:00 PM", "5:00 PM"]
        }
        return optimal_times.get(platform.lower(), ["9:00 AM", "12:00 PM", "6:00 PM"])

    # ==================== CONTENT IDEAS ====================

    def add_content_idea(self, topic: str, description: str,
                        platforms: List[str] = None, hashtags: List[str] = None,
                        priority: int = 3) -> ContentIdea:
        """Add a content idea"""
        idea_id = str(uuid.uuid4())[:12]
        now = datetime.datetime.now().timestamp()

        idea = ContentIdea(
            id=idea_id,
            topic=topic,
            description=description,
            suggested_platforms=platforms or ["facebook", "twitter"],
            suggested_hashtags=hashtags or [],
            priority=priority,
            created_at=now,
            used=False
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO content_ideas (id, topic, description, suggested_platforms,
                                      suggested_hashtags, priority, created_at, used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (idea.id, idea.topic, idea.description, json.dumps(idea.suggested_platforms),
              json.dumps(idea.suggested_hashtags), idea.priority, idea.created_at, 0))
        conn.commit()
        conn.close()

        return idea

    def get_content_ideas(self, unused_only: bool = True, limit: int = 10) -> List[ContentIdea]:
        """Get content ideas"""
        conn = self._get_conn()
        cursor = conn.cursor()

        sql = "SELECT * FROM content_ideas"
        if unused_only:
            sql += " WHERE used = 0"
        sql += " ORDER BY priority DESC, created_at DESC LIMIT ?"

        cursor.execute(sql, (limit,))
        rows = cursor.fetchall()
        conn.close()

        return [
            ContentIdea(
                id=row[0], topic=row[1], description=row[2],
                suggested_platforms=json.loads(row[3] or "[]"),
                suggested_hashtags=json.loads(row[4] or "[]"),
                priority=row[5], created_at=row[6], used=bool(row[7])
            )
            for row in rows
        ]

    # ==================== ANALYTICS ====================

    def track_engagement(self, post_id: str, likes: int = 0, shares: int = 0,
                        comments: int = 0, impressions: int = 0):
        """Track engagement for a post"""
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.datetime.now().timestamp()

        # Add to history
        history_id = str(uuid.uuid4())[:12]
        cursor.execute("""
            INSERT INTO engagement_history (id, post_id, timestamp, likes, shares, comments, impressions)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (history_id, post_id, now, likes, shares, comments, impressions))

        # Update post engagement
        engagement = {"likes": likes, "shares": shares, "comments": comments, "impressions": impressions}
        cursor.execute("""
            UPDATE posts SET engagement = ? WHERE id = ?
        """, (json.dumps(engagement), post_id))

        conn.commit()
        conn.close()

    def get_engagement_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get engagement statistics"""
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).timestamp()

        conn = self._get_conn()
        cursor = conn.cursor()

        # Total engagement
        cursor.execute("""
            SELECT SUM(likes), SUM(shares), SUM(comments), SUM(impressions)
            FROM engagement_history
            WHERE timestamp >= ?
        """, (cutoff,))
        row = cursor.fetchone()

        stats = {
            "total_likes": row[0] or 0,
            "total_shares": row[1] or 0,
            "total_comments": row[2] or 0,
            "total_impressions": row[3] or 0,
            "period_days": days
        }

        # Posts by platform
        cursor.execute("""
            SELECT platform, COUNT(*) FROM posts
            WHERE posted_time >= ?
            GROUP BY platform
        """, (cutoff,))
        stats["posts_by_platform"] = dict(cursor.fetchall())

        conn.close()
        return stats

    # ==================== PLATFORM ACCOUNTS ====================

    def connect_account(self, platform: str, username: str, display_name: str,
                       access_token: str = None) -> PlatformAccount:
        """Connect a social media account"""
        account_id = str(uuid.uuid4())[:12]
        now = datetime.datetime.now().timestamp()

        try:
            platform_enum = Platform(platform.lower())
        except ValueError:
            platform_enum = Platform.FACEBOOK

        account = PlatformAccount(
            id=account_id,
            platform=platform_enum,
            username=username,
            display_name=display_name,
            is_active=True,
            access_token=access_token,  # Would be encrypted in production
            token_expires=None,
            last_synced=None,
            connected_at=now
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO platform_accounts (id, platform, username, display_name, is_active,
                                          access_token, connected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (account.id, account.platform.value, account.username, account.display_name,
              1, account.access_token, account.connected_at))
        conn.commit()
        conn.close()

        return account

    def get_connected_accounts(self) -> List[PlatformAccount]:
        """Get all connected accounts"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM platform_accounts WHERE is_active = 1")
        rows = cursor.fetchall()
        conn.close()

        return [
            PlatformAccount(
                id=row[0], platform=Platform(row[1]), username=row[2],
                display_name=row[3], is_active=bool(row[4]),
                access_token=row[5], token_expires=row[6],
                last_synced=row[7], connected_at=row[8]
            )
            for row in rows
        ]


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_social_media_manager: Optional[SocialMediaManager] = None


def get_social_media_manager() -> SocialMediaManager:
    """Get or create singleton social media manager instance"""
    global _social_media_manager
    if _social_media_manager is None:
        _social_media_manager = SocialMediaManager()
    return _social_media_manager


# ================================================================================
# COMMAND FUNCTIONS
# ================================================================================

def draft_post_cmd(platform: str, content: str, scheduled_time: str = None,
                  hashtags: str = None) -> str:
    """Draft a new social media post"""
    manager = get_social_media_manager()

    # Parse scheduled time if provided
    schedule_timestamp = None
    if scheduled_time:
        from blue.tools.calendar import parse_datetime
        dt = parse_datetime(scheduled_time)
        if dt:
            schedule_timestamp = dt.timestamp()

    # Parse hashtags
    hashtag_list = []
    if hashtags:
        hashtag_list = [h.strip() for h in hashtags.split(',')]

    post = manager.create_post(
        platform=platform,
        content=content,
        scheduled_time=schedule_timestamp,
        hashtags=hashtag_list
    )

    return json.dumps({
        "status": "success",
        "message": f"Post drafted for {platform}",
        "post": post.to_dict()
    })


def approve_post_cmd(post_id: str) -> str:
    """Approve a post for publishing"""
    manager = get_social_media_manager()
    post = manager.approve_post(post_id)

    if post:
        return json.dumps({
            "status": "success",
            "message": f"Post {post_id} approved",
            "post": post.to_dict()
        })
    else:
        return json.dumps({
            "status": "error",
            "error": f"Post not found: {post_id}"
        })


def list_posts_cmd(platform: str = None, status: str = None) -> str:
    """List social media posts"""
    manager = get_social_media_manager()
    posts = manager.get_posts(platform=platform, status=status)

    return json.dumps({
        "status": "success",
        "count": len(posts),
        "posts": [p.to_dict() for p in posts]
    })


def get_scheduled_posts_cmd(hours: int = 24) -> str:
    """Get upcoming scheduled posts"""
    manager = get_social_media_manager()
    posts = manager.get_scheduled_posts(upcoming_hours=hours)

    return json.dumps({
        "status": "success",
        "count": len(posts),
        "posts": [p.to_dict() for p in posts]
    })


def add_content_idea_cmd(topic: str, description: str, priority: int = 3) -> str:
    """Add a content idea"""
    manager = get_social_media_manager()
    idea = manager.add_content_idea(topic, description, priority=priority)

    return json.dumps({
        "status": "success",
        "message": f"Content idea added: {topic}",
        "idea": idea.to_dict()
    })


def get_content_ideas_cmd() -> str:
    """Get content ideas"""
    manager = get_social_media_manager()
    ideas = manager.get_content_ideas()

    return json.dumps({
        "status": "success",
        "count": len(ideas),
        "ideas": [i.to_dict() for i in ideas]
    })


def get_engagement_stats_cmd(days: int = 7) -> str:
    """Get engagement statistics"""
    manager = get_social_media_manager()
    stats = manager.get_engagement_stats(days=days)

    return json.dumps({
        "status": "success",
        "stats": stats
    })


def suggest_hashtags_cmd(content: str) -> str:
    """Suggest hashtags for content"""
    manager = get_social_media_manager()
    hashtags = manager._suggest_hashtags(content)

    return json.dumps({
        "status": "success",
        "hashtags": hashtags
    })


def connect_account_cmd(platform: str, username: str, display_name: str) -> str:
    """Connect a social media account"""
    manager = get_social_media_manager()
    account = manager.connect_account(platform, username, display_name)

    return json.dumps({
        "status": "success",
        "message": f"Connected {platform} account: @{username}",
        "account": account.to_dict()
    })


__all__ = [
    'SocialMediaManager',
    'SocialPost',
    'ContentIdea',
    'PlatformAccount',
    'Platform',
    'PostStatus',
    'ContentType',
    'ApprovalStatus',
    'get_social_media_manager',
    'draft_post_cmd',
    'approve_post_cmd',
    'list_posts_cmd',
    'get_scheduled_posts_cmd',
    'add_content_idea_cmd',
    'get_content_ideas_cmd',
    'get_engagement_stats_cmd',
    'suggest_hashtags_cmd',
    'connect_account_cmd',
]
