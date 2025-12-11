"""
Blue Robot Facebook Integration
================================
Direct integration with Facebook Graph API for posting, engagement tracking, and page management.

Features:
- OAuth 2.0 authentication
- Post to Facebook Pages and personal timeline
- Upload photos and videos
- Track engagement (likes, comments, shares)
- Read comments and messages
- Schedule posts
- Manage page insights

Requirements:
- Facebook App (created at developers.facebook.com)
- App ID and App Secret
- Access Token with proper permissions
"""

import datetime
import json
import os
import requests
import sqlite3
import time
import webbrowser
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

# ================================================================================
# CONFIGURATION
# ================================================================================

FACEBOOK_CONFIG_FILE = os.path.join("data", "facebook_config.json")
FACEBOOK_OAUTH_DB = os.path.join("data", "facebook_oauth.db")

# Facebook Graph API endpoint
GRAPH_API_URL = "https://graph.facebook.com/v18.0"

# OAuth URLs
OAUTH_DIALOG_URL = "https://www.facebook.com/v18.0/dialog/oauth"
OAUTH_TOKEN_URL = f"{GRAPH_API_URL}/oauth/access_token"

# Required permissions for posting and engagement
REQUIRED_PERMISSIONS = [
    "pages_manage_posts",        # Post to pages
    "pages_read_engagement",     # Read page engagement
    "pages_read_user_content",   # Read page content
    "pages_manage_engagement",   # Respond to comments/messages
    "public_profile",            # Basic profile info
    "email"                      # User email
]


# ================================================================================
# FACEBOOK OAUTH MANAGER
# ================================================================================

class FacebookOAuthManager:
    """Manages Facebook OAuth authentication and tokens"""

    def __init__(self, app_id: str = None, app_secret: str = None):
        self.app_id = app_id
        self.app_secret = app_secret
        self.redirect_uri = "http://localhost:5000/facebook/callback"
        self._init_database()
        self._load_config()

    def _init_database(self):
        """Initialize OAuth database"""
        os.makedirs(os.path.dirname(FACEBOOK_OAUTH_DB), exist_ok=True)
        conn = sqlite3.connect(FACEBOOK_OAUTH_DB)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_tokens (
                id INTEGER PRIMARY KEY,
                access_token TEXT NOT NULL,
                token_type TEXT DEFAULT 'user',
                expires_at REAL,
                page_id TEXT,
                page_name TEXT,
                created_at REAL NOT NULL,
                last_refreshed REAL
            )
        """)

        conn.commit()
        conn.close()

    def _load_config(self):
        """Load Facebook app configuration"""
        if os.path.exists(FACEBOOK_CONFIG_FILE):
            with open(FACEBOOK_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                self.app_id = self.app_id or config.get('app_id')
                self.app_secret = self.app_secret or config.get('app_secret')

    def save_config(self):
        """Save Facebook app configuration"""
        os.makedirs(os.path.dirname(FACEBOOK_CONFIG_FILE), exist_ok=True)
        config = {
            'app_id': self.app_id,
            'app_secret': self.app_secret,
            'redirect_uri': self.redirect_uri
        }
        with open(FACEBOOK_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)

    def get_authorization_url(self, state: str = None) -> str:
        """Generate Facebook OAuth authorization URL"""
        if not self.app_id:
            raise ValueError("Facebook App ID not configured")

        params = {
            'client_id': self.app_id,
            'redirect_uri': self.redirect_uri,
            'scope': ','.join(REQUIRED_PERMISSIONS),
            'response_type': 'code',
            'state': state or 'blue_robot_auth'
        }

        return f"{OAUTH_DIALOG_URL}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        if not self.app_id or not self.app_secret:
            raise ValueError("Facebook App ID and Secret required")

        params = {
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'redirect_uri': self.redirect_uri,
            'code': code
        }

        response = requests.get(OAUTH_TOKEN_URL, params=params)
        response.raise_for_status()

        data = response.json()
        access_token = data.get('access_token')

        # Get long-lived token
        long_lived_token = self._exchange_for_long_lived_token(access_token)

        # Save token
        self._save_token(long_lived_token)

        return {
            'access_token': long_lived_token,
            'token_type': 'user'
        }

    def _exchange_for_long_lived_token(self, short_lived_token: str) -> str:
        """Exchange short-lived token for long-lived token (60 days)"""
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'fb_exchange_token': short_lived_token
        }

        response = requests.get(OAUTH_TOKEN_URL, params=params)
        response.raise_for_status()

        data = response.json()
        return data.get('access_token')

    def _save_token(self, access_token: str, token_type: str = 'user',
                    page_id: str = None, page_name: str = None):
        """Save access token to database"""
        conn = sqlite3.connect(FACEBOOK_OAUTH_DB)
        cursor = conn.cursor()

        now = datetime.datetime.now().timestamp()
        # Long-lived tokens expire in 60 days
        expires_at = now + (60 * 24 * 60 * 60)

        cursor.execute("""
            INSERT INTO oauth_tokens (access_token, token_type, expires_at, page_id, page_name, created_at, last_refreshed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (access_token, token_type, expires_at, page_id, page_name, now, now))

        conn.commit()
        conn.close()

    def get_access_token(self, token_type: str = 'user') -> Optional[str]:
        """Get valid access token from database"""
        conn = sqlite3.connect(FACEBOOK_OAUTH_DB)
        cursor = conn.cursor()

        now = datetime.datetime.now().timestamp()

        cursor.execute("""
            SELECT access_token, expires_at FROM oauth_tokens
            WHERE token_type = ? AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at DESC LIMIT 1
        """, (token_type, now))

        row = cursor.fetchone()
        conn.close()

        if row:
            return row[0]
        return None


# ================================================================================
# FACEBOOK API CLIENT
# ================================================================================

class FacebookAPIClient:
    """Facebook Graph API client for posting and engagement"""

    def __init__(self, access_token: str = None):
        self.oauth_manager = FacebookOAuthManager()
        self.access_token = access_token or self.oauth_manager.get_access_token()

    def _make_request(self, method: str, endpoint: str, params: Dict = None,
                     data: Dict = None, files: Dict = None) -> Dict[str, Any]:
        """Make authenticated request to Facebook Graph API"""
        if not self.access_token:
            raise ValueError("No access token available. Please authenticate first.")

        url = f"{GRAPH_API_URL}/{endpoint}"

        if params is None:
            params = {}
        params['access_token'] = self.access_token

        if method.upper() == 'GET':
            response = requests.get(url, params=params)
        elif method.upper() == 'POST':
            if files:
                response = requests.post(url, params=params, data=data, files=files)
            else:
                response = requests.post(url, params=params, json=data)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, params=params)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()

    # ==================== USER INFO ====================

    def get_user_info(self) -> Dict[str, Any]:
        """Get authenticated user information"""
        return self._make_request('GET', 'me', params={'fields': 'id,name,email'})

    def get_user_pages(self) -> List[Dict[str, Any]]:
        """Get pages that user manages"""
        response = self._make_request('GET', 'me/accounts',
                                     params={'fields': 'id,name,access_token,category'})
        return response.get('data', [])

    # ==================== POSTING ====================

    def post_to_feed(self, message: str, link: str = None,
                    page_id: str = None) -> Dict[str, Any]:
        """Post a message to user feed or page"""
        target = page_id if page_id else 'me'
        endpoint = f"{target}/feed"

        data = {'message': message}
        if link:
            data['link'] = link

        return self._make_request('POST', endpoint, data=data)

    def post_photo(self, image_path: str, caption: str = None,
                  page_id: str = None) -> Dict[str, Any]:
        """Upload and post a photo"""
        target = page_id if page_id else 'me'
        endpoint = f"{target}/photos"

        data = {}
        if caption:
            data['caption'] = caption

        with open(image_path, 'rb') as image_file:
            files = {'source': image_file}
            return self._make_request('POST', endpoint, data=data, files=files)

    def post_video(self, video_path: str, description: str = None,
                  page_id: str = None) -> Dict[str, Any]:
        """Upload and post a video"""
        target = page_id if page_id else 'me'
        endpoint = f"{target}/videos"

        data = {}
        if description:
            data['description'] = description

        with open(video_path, 'rb') as video_file:
            files = {'source': video_file}
            return self._make_request('POST', endpoint, data=data, files=files)

    def schedule_post(self, message: str, scheduled_time: int,
                     link: str = None, page_id: str = None) -> Dict[str, Any]:
        """Schedule a post for future publishing"""
        if not page_id:
            raise ValueError("Scheduled posts require a page_id")

        endpoint = f"{page_id}/feed"

        data = {
            'message': message,
            'published': False,
            'scheduled_publish_time': scheduled_time
        }
        if link:
            data['link'] = link

        return self._make_request('POST', endpoint, data=data)

    # ==================== ENGAGEMENT ====================

    def get_post_engagement(self, post_id: str) -> Dict[str, Any]:
        """Get engagement metrics for a post"""
        fields = 'id,message,created_time,likes.summary(true),comments.summary(true),shares'
        return self._make_request('GET', post_id, params={'fields': fields})

    def get_post_comments(self, post_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Get comments on a post"""
        response = self._make_request('GET', f"{post_id}/comments",
                                     params={'limit': limit, 'fields': 'id,from,message,created_time'})
        return response.get('data', [])

    def reply_to_comment(self, comment_id: str, message: str) -> Dict[str, Any]:
        """Reply to a comment"""
        return self._make_request('POST', f"{comment_id}/comments", data={'message': message})

    def like_post(self, post_id: str) -> Dict[str, Any]:
        """Like a post"""
        return self._make_request('POST', f"{post_id}/likes")

    def delete_post(self, post_id: str) -> Dict[str, Any]:
        """Delete a post"""
        return self._make_request('DELETE', post_id)

    # ==================== PAGE INSIGHTS ====================

    def get_page_insights(self, page_id: str, metrics: List[str] = None,
                         period: str = 'day') -> Dict[str, Any]:
        """Get page insights/analytics"""
        if metrics is None:
            metrics = ['page_impressions', 'page_engaged_users', 'page_post_engagements']

        params = {
            'metric': ','.join(metrics),
            'period': period
        }

        return self._make_request('GET', f"{page_id}/insights", params=params)


# ================================================================================
# INTEGRATION WITH SOCIAL MEDIA MANAGER
# ================================================================================

class FacebookIntegration:
    """Integration layer between Facebook API and Social Media Manager"""

    def __init__(self):
        self.oauth_manager = FacebookOAuthManager()
        self.api_client = None

    def setup_app(self, app_id: str, app_secret: str):
        """Configure Facebook app credentials"""
        self.oauth_manager.app_id = app_id
        self.oauth_manager.app_secret = app_secret
        self.oauth_manager.save_config()
        return {"status": "success", "message": "Facebook app configured"}

    def start_authentication(self) -> str:
        """Start OAuth flow and return authorization URL"""
        auth_url = self.oauth_manager.get_authorization_url()
        print(f"\n{'='*60}")
        print("FACEBOOK AUTHENTICATION")
        print(f"{'='*60}")
        print("\nOpening Facebook authorization page in your browser...")
        print(f"\nIf browser doesn't open, visit this URL:")
        print(f"\n{auth_url}\n")
        print("After authorizing, you'll be redirected to a callback URL.")
        print("Copy the 'code' parameter from the URL and provide it to Blue.")
        print(f"{'='*60}\n")

        # Open browser
        webbrowser.open(auth_url)

        return auth_url

    def complete_authentication(self, code: str) -> Dict[str, Any]:
        """Complete OAuth flow with authorization code"""
        try:
            token_data = self.oauth_manager.exchange_code_for_token(code)
            self.api_client = FacebookAPIClient(token_data['access_token'])

            # Get user info
            user_info = self.api_client.get_user_info()

            # Get managed pages
            pages = self.api_client.get_user_pages()

            # Save page tokens
            for page in pages:
                self.oauth_manager._save_token(
                    access_token=page['access_token'],
                    token_type='page',
                    page_id=page['id'],
                    page_name=page['name']
                )

            return {
                "status": "success",
                "user": user_info,
                "pages": pages,
                "message": f"Authenticated as {user_info.get('name')}"
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def publish_post(self, post_id: str) -> Dict[str, Any]:
        """Publish an approved post from Social Media Manager to Facebook"""
        from blue.tools.social_media import get_social_media_manager

        manager = get_social_media_manager()
        post = manager.get_post(post_id)

        if not post:
            return {"status": "error", "error": "Post not found"}

        if post.approval_status.value != "approved":
            return {"status": "error", "error": "Post not approved"}

        if not self.api_client:
            token = self.oauth_manager.get_access_token()
            if not token:
                return {"status": "error", "error": "Not authenticated"}
            self.api_client = FacebookAPIClient(token)

        try:
            # Post to Facebook
            if post.scheduled_time and post.scheduled_time > datetime.datetime.now().timestamp():
                # Schedule post
                result = self.api_client.schedule_post(
                    message=post.content,
                    scheduled_time=int(post.scheduled_time)
                )
            else:
                # Post immediately
                result = self.api_client.post_to_feed(message=post.content)

            # Update post in database
            post.platform_post_id = result.get('id')
            post.status = "posted"
            post.posted_time = datetime.datetime.now().timestamp()

            # Update in database
            conn = sqlite3.connect("data/social_media.db")
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE posts SET status = ?, posted_time = ?, platform_post_id = ?
                WHERE id = ?
            """, (post.status.value, post.posted_time, post.platform_post_id, post.id))
            conn.commit()
            conn.close()

            return {
                "status": "success",
                "message": "Post published to Facebook",
                "facebook_post_id": result.get('id'),
                "post": post.to_dict()
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def sync_engagement(self, post_id: str) -> Dict[str, Any]:
        """Sync engagement data from Facebook for a post"""
        from blue.tools.social_media import get_social_media_manager

        manager = get_social_media_manager()
        post = manager.get_post(post_id)

        if not post or not post.platform_post_id:
            return {"status": "error", "error": "Post not found or not published"}

        if not self.api_client:
            token = self.oauth_manager.get_access_token()
            if not token:
                return {"status": "error", "error": "Not authenticated"}
            self.api_client = FacebookAPIClient(token)

        try:
            engagement = self.api_client.get_post_engagement(post.platform_post_id)

            likes = engagement.get('likes', {}).get('summary', {}).get('total_count', 0)
            comments = engagement.get('comments', {}).get('summary', {}).get('total_count', 0)
            shares = engagement.get('shares', {}).get('count', 0)

            # Update engagement in Social Media Manager
            manager.track_engagement(
                post_id=post_id,
                likes=likes,
                shares=shares,
                comments=comments
            )

            return {
                "status": "success",
                "engagement": {
                    "likes": likes,
                    "comments": comments,
                    "shares": shares
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


# ================================================================================
# COMMAND FUNCTIONS
# ================================================================================

_facebook_integration: Optional[FacebookIntegration] = None


def get_facebook_integration() -> FacebookIntegration:
    """Get or create Facebook integration instance"""
    global _facebook_integration
    if _facebook_integration is None:
        _facebook_integration = FacebookIntegration()
    return _facebook_integration


def setup_facebook_app_cmd(app_id: str, app_secret: str) -> str:
    """Configure Facebook app credentials"""
    integration = get_facebook_integration()
    result = integration.setup_app(app_id, app_secret)
    return json.dumps(result)


def connect_facebook_cmd() -> str:
    """Start Facebook OAuth authentication"""
    integration = get_facebook_integration()
    auth_url = integration.start_authentication()
    return json.dumps({
        "status": "success",
        "message": "Please authorize Blue in the browser window",
        "auth_url": auth_url
    })


def complete_facebook_auth_cmd(code: str) -> str:
    """Complete Facebook authentication with code"""
    integration = get_facebook_integration()
    result = integration.complete_authentication(code)
    return json.dumps(result)


def publish_to_facebook_cmd(post_id: str) -> str:
    """Publish an approved post to Facebook"""
    integration = get_facebook_integration()
    result = integration.publish_post(post_id)
    return json.dumps(result)


def sync_facebook_engagement_cmd(post_id: str) -> str:
    """Sync Facebook engagement data for a post"""
    integration = get_facebook_integration()
    result = integration.sync_engagement(post_id)
    return json.dumps(result)


__all__ = [
    'FacebookOAuthManager',
    'FacebookAPIClient',
    'FacebookIntegration',
    'get_facebook_integration',
    'setup_facebook_app_cmd',
    'connect_facebook_cmd',
    'complete_facebook_auth_cmd',
    'publish_to_facebook_cmd',
    'sync_facebook_engagement_cmd',
]
