"""
Blue Robot Light Tools
======================
Philips Hue light control.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import requests

# ================================================================================
# CONFIGURATION
# ================================================================================

# Load Hue config
HUE_CONFIG = {}
try:
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "hue_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            HUE_CONFIG = json.load(f)
        print(f"[OK] Hue config loaded: Bridge at {HUE_CONFIG.get('bridge_ip')}")
except Exception as e:
    print(f"[WARN] Error loading Hue config: {e}")

BRIDGE_IP = HUE_CONFIG.get("bridge_ip", "")
HUE_USERNAME = HUE_CONFIG.get("username", "")


# ================================================================================
# COLOR MAPPINGS
# ================================================================================

COLOR_MAP = {
    'red': {'hue': 0, 'sat': 254},
    'orange': {'hue': 5000, 'sat': 254},
    'yellow': {'hue': 10000, 'sat': 254},
    'lime': {'hue': 18000, 'sat': 254},
    'green': {'hue': 25500, 'sat': 254},
    'teal': {'hue': 30000, 'sat': 254},
    'cyan': {'hue': 35000, 'sat': 254},
    'blue': {'hue': 46920, 'sat': 254},
    'purple': {'hue': 50000, 'sat': 254},
    'violet': {'hue': 52000, 'sat': 254},
    'magenta': {'hue': 54000, 'sat': 254},
    'pink': {'hue': 56100, 'sat': 200},
    'white': {'ct': 250},
    'warm white': {'ct': 400},
    'cool white': {'ct': 200},
    'daylight': {'ct': 250},
    'amber': {'hue': 6000, 'sat': 254},
    'gold': {'hue': 8000, 'sat': 200},
}


# ================================================================================
# MOOD PRESETS
# ================================================================================

MOOD_PRESETS = {
    # Nature moods
    'moonlight': {'description': 'Cool blue moonlight', 'settings': [{'ct': 200, 'bri': 80}]},
    'sunset': {'description': 'Warm orange sunset', 'settings': [{'hue': 6000, 'sat': 200, 'bri': 180}]},
    'sunrise': {'description': 'Gentle morning light', 'settings': [{'hue': 8000, 'sat': 150, 'bri': 150}]},
    'ocean': {'description': 'Deep blue ocean', 'settings': [{'hue': 46920, 'sat': 200, 'bri': 120}]},
    'forest': {'description': 'Green forest', 'settings': [{'hue': 25500, 'sat': 180, 'bri': 100}]},
    'tropical': {'description': 'Tropical vibes', 'settings': [{'hue': 30000, 'sat': 200, 'bri': 180}]},
    'arctic': {'description': 'Cool arctic', 'settings': [{'ct': 153, 'bri': 200}]},
    'galaxy': {'description': 'Purple galaxy', 'settings': [{'hue': 50000, 'sat': 200, 'bri': 100}]},
    'aurora': {'description': 'Northern lights', 'settings': [{'hue': 35000, 'sat': 254, 'bri': 150}]},

    # Activity moods
    'focus': {'description': 'Cool white for focus', 'settings': [{'ct': 250, 'bri': 254}]},
    'relax': {'description': 'Warm relaxing light', 'settings': [{'ct': 400, 'bri': 120}]},
    'energize': {'description': 'Bright energizing', 'settings': [{'ct': 200, 'bri': 254}]},
    'reading': {'description': 'Comfortable reading', 'settings': [{'ct': 300, 'bri': 200}]},
    'movie': {'description': 'Dim movie mode', 'settings': [{'ct': 400, 'bri': 50}]},
    'gaming': {'description': 'Dynamic gaming', 'settings': [{'hue': 46920, 'sat': 254, 'bri': 200}]},
    'workout': {'description': 'High energy workout', 'settings': [{'hue': 0, 'sat': 254, 'bri': 254}]},

    # Mood settings
    'romance': {'description': 'Romantic ambiance', 'settings': [{'hue': 56100, 'sat': 200, 'bri': 80}]},
    'party': {'description': 'Party mode', 'settings': [{'hue': 50000, 'sat': 254, 'bri': 254}]},
    'cozy': {'description': 'Cozy warm', 'settings': [{'ct': 450, 'bri': 100}]},
    'fireplace': {'description': 'Fireplace glow', 'settings': [{'hue': 5000, 'sat': 220, 'bri': 120}]},
    'zen': {'description': 'Peaceful zen', 'settings': [{'ct': 350, 'bri': 80}]},

    # Colors
    'red': {'description': 'Red', 'settings': [{'hue': 0, 'sat': 254, 'bri': 200}]},
    'blue': {'description': 'Blue', 'settings': [{'hue': 46920, 'sat': 254, 'bri': 200}]},
    'green': {'description': 'Green', 'settings': [{'hue': 25500, 'sat': 254, 'bri': 200}]},
    'purple': {'description': 'Purple', 'settings': [{'hue': 50000, 'sat': 254, 'bri': 200}]},
    'pink': {'description': 'Pink', 'settings': [{'hue': 56100, 'sat': 200, 'bri': 200}]},
    'orange': {'description': 'Orange', 'settings': [{'hue': 5000, 'sat': 254, 'bri': 200}]},
    'yellow': {'description': 'Yellow', 'settings': [{'hue': 10000, 'sat': 254, 'bri': 200}]},
    'cyan': {'description': 'Cyan', 'settings': [{'hue': 35000, 'sat': 254, 'bri': 200}]},
    'white': {'description': 'White', 'settings': [{'ct': 250, 'bri': 254}]},

    # Special
    'bright': {'description': 'Maximum brightness', 'settings': [{'ct': 250, 'bri': 254}]},
    'dim': {'description': 'Dim lighting', 'settings': [{'ct': 350, 'bri': 50}]},
    'night': {'description': 'Night light', 'settings': [{'ct': 450, 'bri': 20}]},
    'natural': {'description': 'Natural daylight', 'settings': [{'ct': 250, 'bri': 200}]},
}


# ================================================================================
# FUNCTIONS
# ================================================================================

def get_hue_lights() -> Dict:
    """Get all lights from Hue Bridge."""
    if not BRIDGE_IP or not HUE_USERNAME:
        return {}
    try:
        response = requests.get(f"http://{BRIDGE_IP}/api/{HUE_USERNAME}/lights", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"   [ERROR] Error getting lights: {e}")
    return {}


def find_light_by_name(light_name: str) -> Optional[str]:
    """Find light ID by name."""
    lights = get_hue_lights()
    light_name_lower = light_name.lower()

    for light_id, data in lights.items():
        if data.get('name', '').lower() == light_name_lower:
            return light_id

    for light_id, data in lights.items():
        if light_name_lower in data.get('name', '').lower():
            return light_id

    return None


def control_hue_light(light_id: str, state: Dict) -> bool:
    """Send state change to a specific light."""
    if not BRIDGE_IP or not HUE_USERNAME:
        return False
    try:
        response = requests.put(
            f"http://{BRIDGE_IP}/api/{HUE_USERNAME}/lights/{light_id}/state",
            json=state,
            timeout=5
        )
        return response.status_code == 200
    except Exception as e:
        print(f"   [ERROR] Error controlling light: {e}")
        return False


def apply_mood_to_lights(mood: str) -> str:
    """Apply a mood/scene to all lights."""
    print(f"   [MOOD] Applying mood: {mood}")

    if not BRIDGE_IP or not HUE_USERNAME:
        return "Hue not configured. Run setup_hue.py first!"

    mood_lower = mood.lower()
    if mood_lower not in MOOD_PRESETS:
        available = ", ".join(MOOD_PRESETS.keys())
        return f"Unknown mood '{mood}'. Available moods: {available}"

    lights = get_hue_lights()
    if not lights:
        return "Could not connect to Hue Bridge."

    mood_data = MOOD_PRESETS[mood_lower]
    settings_list = mood_data["settings"]
    light_ids = list(lights.keys())

    success_count = 0
    assignments = []

    for i, light_id in enumerate(light_ids):
        setting = settings_list[i % len(settings_list)].copy()
        setting["on"] = True
        setting["transitiontime"] = 10

        if control_hue_light(light_id, setting):
            success_count += 1
            light_name = lights[light_id]['name']
            assignments.append(light_name)

    if success_count > 0:
        description = mood_data["description"]
        return f"Applied '{mood}' mood ({description}) to {success_count} light(s): {', '.join(assignments[:3])}{'...' if len(assignments) > 3 else ''}"
    else:
        return f"Failed to apply mood '{mood}'"


def execute_light_control(action: str, light_name: str = None, brightness: int = None,
                         color: str = None, mood: str = None) -> str:
    """Execute light control commands."""
    print(f"   [LIGHT] Light control: action={action}, light={light_name}, brightness={brightness}, color={color}, mood={mood}")

    if not BRIDGE_IP or not HUE_USERNAME:
        return "Philips Hue not configured. Run setup_hue.py first!"

    lights = get_hue_lights()
    if not lights:
        return "Could not connect to Hue Bridge."

    if action == "mood":
        if mood:
            return apply_mood_to_lights(mood)
        else:
            available = ", ".join(MOOD_PRESETS.keys())
            return f"Please specify a mood. Available: {available}"

    target_lights = []
    if light_name:
        light_id = find_light_by_name(light_name)
        if light_id:
            target_lights = [(light_id, lights[light_id]['name'])]
        else:
            available = ", ".join([lights[lid]['name'] for lid in lights])
            return f"Couldn't find '{light_name}'. Available: {available}"
    else:
        target_lights = [(lid, data['name']) for lid, data in lights.items()]

    if not target_lights:
        return "No lights found."

    if action == "status":
        status_lines = []
        for light_id, name in target_lights:
            state = lights[light_id].get('state', {})
            on_status = "ON" if state.get('on', False) else "OFF"
            bri = state.get('bri', 0)
            bri_percent = int((bri / 254) * 100) if bri else 0
            status_lines.append(f"{name}: {on_status}" + (f", {bri_percent}%" if on_status == "ON" else ""))
        return "Light Status:\n" + "\n".join(status_lines)

    elif action == "on":
        success_count = sum(1 for lid, _ in target_lights if control_hue_light(lid, {"on": True}))
        names = ", ".join([n for _, n in target_lights])
        return f"Turned on: {names}" if success_count == len(target_lights) else f"Turned on {success_count}/{len(target_lights)}"

    elif action == "off":
        success_count = sum(1 for lid, _ in target_lights if control_hue_light(lid, {"on": False}))
        names = ", ".join([n for _, n in target_lights])
        return f"Turned off: {names}" if success_count == len(target_lights) else f"Turned off {success_count}/{len(target_lights)}"

    elif action == "brightness":
        if brightness is None:
            return "Please specify brightness level (0-100)"
        bri_value = max(0, min(254, int((brightness / 100) * 254)))
        success_count = sum(1 for lid, _ in target_lights if control_hue_light(lid, {"on": True, "bri": bri_value}))
        names = ", ".join([n for _, n in target_lights])
        return f"Set {names} to {brightness}%" if success_count == len(target_lights) else f"Adjusted {success_count}/{len(target_lights)}"

    elif action == "color":
        if color is None:
            return "Please specify a color"
        color_lower = color.lower()
        if color_lower not in COLOR_MAP:
            available = ", ".join(COLOR_MAP.keys())
            return f"Unknown color '{color}'. Available: {available}"
        color_settings = COLOR_MAP[color_lower].copy()
        color_settings["on"] = True
        success_count = sum(1 for lid, _ in target_lights if control_hue_light(lid, color_settings))
        names = ", ".join([n for _, n in target_lights])
        return f"Set {names} to {color}" if success_count == len(target_lights) else f"Changed {success_count}/{len(target_lights)}"

    return "Unknown action"


__all__ = [
    'HUE_CONFIG', 'BRIDGE_IP', 'HUE_USERNAME',
    'COLOR_MAP', 'MOOD_PRESETS',
    'get_hue_lights', 'find_light_by_name', 'control_hue_light',
    'apply_mood_to_lights', 'execute_light_control',
]
