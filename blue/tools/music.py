"""
Blue Robot Music Tools
======================
Music playback and control using YouTube Music.
"""

from __future__ import annotations

import os
import webbrowser
from typing import Any, Dict, List, Optional

import requests

# Global YouTube Music browser instance
YOUTUBE_MUSIC_BROWSER = None

# Music service configuration
MUSIC_SERVICE = "youtube_music"


def init_youtube_music() -> bool:
    """Initialize YouTube Music API."""
    global YOUTUBE_MUSIC_BROWSER
    if YOUTUBE_MUSIC_BROWSER is None:
        try:
            from ytmusicapi import YTMusic
            YOUTUBE_MUSIC_BROWSER = YTMusic()
            print("[OK] YouTube Music initialized")
            return True
        except ImportError:
            print("[WARN] ytmusicapi not installed. Install with: pip install ytmusicapi")
            return False
        except Exception as e:
            print(f"[WARN] Error initializing YouTube Music: {e}")
            return False
    return True


def search_youtube_music(query: str, limit: int = 5) -> List[Dict]:
    """Search for songs on YouTube Music."""
    if not init_youtube_music():
        return []

    try:
        results = YOUTUBE_MUSIC_BROWSER.search(query, filter="songs", limit=limit)
        return results
    except Exception as e:
        print(f"   [ERROR] Error searching YouTube Music: {e}")
        return []


def get_music_mood(query: str, song_info: dict = None) -> str:
    """Determine appropriate light mood based on music query."""
    query_lower = query.lower()

    mood_mappings = [
        (['relax', 'calm', 'chill', 'ambient', 'peaceful', 'meditation', 'sleep', 'quiet'], 'relax'),
        (['party', 'dance', 'edm', 'club', 'rave', 'celebration', 'upbeat', 'fun'], 'party'),
        (['romantic', 'love', 'ballad', 'slow dance', 'valentine', 'intimate'], 'romance'),
        (['energize', 'workout', 'pump up', 'hype', 'rock', 'metal', 'hard', 'intense'], 'energize'),
        (['jazz', 'lounge', 'smooth', 'sophisticated', 'cool', 'mellow'], 'moonlight'),
        (['tropical', 'beach', 'island', 'reggae', 'caribbean', 'summer'], 'tropical'),
        (['blues', 'soul', 'moody', 'melancholy', 'sad'], 'ocean'),
        (['classical', 'orchestra', 'symphony', 'piano', 'study', 'concentrate'], 'focus'),
        (['sunset', 'golden hour', 'evening', 'dusk'], 'sunset'),
        (['fire', 'cozy', 'warm', 'acoustic', 'folk'], 'fireplace'),
        (['space', 'cosmic', 'stars', 'galaxy', 'electronic'], 'galaxy'),
        (['forest', 'nature', 'green', 'earth', 'natural'], 'forest'),
        (['arctic', 'ice', 'winter', 'frozen', 'cold'], 'arctic'),
        (['sunrise', 'morning', 'dawn', 'wake up'], 'sunrise'),
    ]

    for keywords, mood in mood_mappings:
        if any(word in query_lower for word in keywords):
            return mood

    return 'party'  # Default


def play_music(query: str, service: str = "youtube_music",
               bridge_ip: str = None, hue_username: str = None,
               apply_mood_fn=None) -> str:
    """
    Play music based on query and automatically sync lights.

    Args:
        query: Song name, artist, or search query
        service: "youtube_music" or "amazon_music"
        bridge_ip: Hue bridge IP (optional, for light sync)
        hue_username: Hue username (optional, for light sync)
        apply_mood_fn: Function to apply mood to lights (optional)
    """
    print(f"   [MUSIC] Playing music: '{query}' on {service}")

    if service == "youtube_music":
        results = search_youtube_music(query, limit=1)

        if not results:
            return f"Couldn't find any songs matching '{query}' on YouTube Music"

        song = results[0]
        song_title = song.get('title', 'Unknown')
        artists = song.get('artists', [])
        artist_names = ", ".join([a.get('name', '') for a in artists]) if artists else "Unknown Artist"
        video_id = song.get('videoId', '')

        if not video_id:
            return f"Found '{song_title}' by {artist_names}, but couldn't get playback URL"

        url = f"https://music.youtube.com/watch?v={video_id}"

        # Sync lights with music vibe
        light_sync_msg = ""
        if bridge_ip and hue_username and apply_mood_fn:
            try:
                mood = get_music_mood(query, song)
                print(f"   [SYNC] Syncing lights to '{mood}' mood for this music")
                light_result = apply_mood_fn(mood)
                print(f"   [LIGHT] {light_result}")
                light_sync_msg = f"\n💡 Lights set to '{mood}' mood"
            except Exception as e:
                print(f"   [WARN] Couldn't sync lights: {e}")

        try:
            webbrowser.open(url)
            return f"🎵 Now playing: '{song_title}' by {artist_names}{light_sync_msg}"
        except Exception as e:
            return f"Found '{song_title}' by {artist_names}, but couldn't open browser: {str(e)}\nURL: {url}"

    elif service == "amazon_music":
        search_url = f"https://music.amazon.com/search/{requests.utils.quote(query)}"

        light_sync_msg = ""
        if bridge_ip and hue_username and apply_mood_fn:
            try:
                mood = get_music_mood(query)
                apply_mood_fn(mood)
                light_sync_msg = f"\n💡 Lights synced to '{mood}' mood"
            except Exception:
                pass

        try:
            webbrowser.open(search_url)
            return f"🎵 Opening Amazon Music search for '{query}'{light_sync_msg}"
        except Exception as e:
            return f"Couldn't open Amazon Music: {str(e)}"

    else:
        return f"Unknown music service: {service}"


def search_music_info(query: str) -> str:
    """Search for music and return info without playing."""
    print(f"   [SEARCH] Searching for music info: '{query}'")

    results = search_youtube_music(query, limit=5)

    if not results:
        return f"Couldn't find any songs matching '{query}'"

    formatted_results = []
    for i, song in enumerate(results, 1):
        title = song.get('title', 'Unknown')
        artists = song.get('artists', [])
        artist_names = ", ".join([a.get('name', '') for a in artists]) if artists else "Unknown"
        album = song.get('album', {}).get('name', '') if song.get('album') else ''
        duration = song.get('duration', '')

        result_str = f"{i}. '{title}' by {artist_names}"
        if album:
            result_str += f" (Album: {album})"
        if duration:
            result_str += f" - {duration}"

        formatted_results.append(result_str)

    return "[MUSIC] Found these songs:\n\n" + "\n".join(formatted_results)


def control_music(action: str) -> str:
    """
    Control music playback using SYSTEM-WIDE media keys.
    Works from ANY window - no need to focus YouTube Music!

    Args:
        action: Control action - "pause", "resume", "next", "previous", "volume_up", "volume_down"
    """
    print(f"   [MUSIC] Controlling music: {action}")

    try:
        import pyautogui
    except ImportError:
        return "Music control requires pyautogui. Install with: pip install pyautogui"

    action_lower = action.lower()

    action_map = {
        ('pause', 'resume', 'play_pause'): ('playpause', '🎵 Toggled play/pause'),
        ('next',): ('nexttrack', '🎵 Skipped to next track'),
        ('previous',): ('prevtrack', '🎵 Went to previous track'),
        ('volume_up',): ('volumeup', '🎵 Volume increased'),
        ('volume_down',): ('volumedown', '🎵 Volume decreased'),
        ('mute',): ('volumemute', '🎵 Toggled mute'),
    }

    for actions, (key, message) in action_map.items():
        if action_lower in actions:
            try:
                pyautogui.press(key)
                return message
            except Exception:
                return f"⚠️ {key} key not supported on this system"

    return f"Unknown music control action: {action}. Available: pause, resume, next, previous, volume_up, volume_down, mute"


__all__ = [
    'init_youtube_music',
    'search_youtube_music',
    'get_music_mood',
    'play_music',
    'search_music_info',
    'control_music',
    'YOUTUBE_MUSIC_BROWSER',
    'MUSIC_SERVICE',
]
