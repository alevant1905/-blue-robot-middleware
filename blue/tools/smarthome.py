"""
Blue Robot Smart Home Tools
============================
Unified smart home control with device discovery, status, and automation.

Supports:
- Philips Hue lights (extended from lights.py)
- Generic device discovery (SSDP/UPnP)
- Device status monitoring
- Scene and routine management
- Energy monitoring
"""

from __future__ import annotations

import datetime
import json
import os
import re
import socket
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import requests

# ================================================================================
# CONFIGURATION
# ================================================================================

SMARTHOME_DB = os.environ.get("BLUE_SMARTHOME_DB", "data/smarthome.db")
DEVICE_SCAN_TIMEOUT = 3  # seconds


class DeviceType(Enum):
    LIGHT = "light"
    SWITCH = "switch"
    THERMOSTAT = "thermostat"
    SENSOR = "sensor"
    CAMERA = "camera"
    SPEAKER = "speaker"
    TV = "tv"
    PLUG = "plug"
    OTHER = "other"


class DeviceStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


# ================================================================================
# DATA CLASSES
# ================================================================================

@dataclass
class SmartDevice:
    """Represents a smart home device."""
    id: str
    name: str
    device_type: DeviceType
    manufacturer: str
    model: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    status: DeviceStatus = DeviceStatus.UNKNOWN
    room: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)
    last_seen: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.device_type.value,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "ip_address": self.ip_address,
            "status": self.status.value,
            "room": self.room,
            "capabilities": self.capabilities,
            "state": self.state,
            "last_seen": self.last_seen
        }


@dataclass
class Scene:
    """A scene that controls multiple devices."""
    id: str
    name: str
    description: Optional[str]
    actions: List[Dict[str, Any]]  # List of {device_id, action, params}
    created_at: str
    last_used: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "actions": self.actions,
            "created_at": self.created_at,
            "last_used": self.last_used
        }


@dataclass
class Routine:
    """An automated routine with triggers and actions."""
    id: str
    name: str
    description: Optional[str]
    trigger_type: str  # "time", "sunrise", "sunset", "device_state", "voice"
    trigger_config: Dict[str, Any]
    actions: List[Dict[str, Any]]
    enabled: bool = True
    last_triggered: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trigger_type": self.trigger_type,
            "trigger_config": self.trigger_config,
            "actions": self.actions,
            "enabled": self.enabled,
            "last_triggered": self.last_triggered
        }


# ================================================================================
# SMART HOME MANAGER
# ================================================================================

class SmartHomeManager:
    """
    Central manager for all smart home devices and automation.
    """

    def __init__(self, db_path: str = SMARTHOME_DB):
        self.db_path = db_path
        self.devices: Dict[str, SmartDevice] = {}
        self.scenes: Dict[str, Scene] = {}
        self.routines: Dict[str, Routine] = {}
        self._hue_bridge_ip: Optional[str] = None
        self._hue_username: Optional[str] = None
        self._routine_thread: Optional[threading.Thread] = None
        self._running = False

        self._init_db()
        self._load_data()
        self._load_hue_config()

    def _init_db(self):
        """Initialize the database."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                device_type TEXT NOT NULL,
                manufacturer TEXT,
                model TEXT,
                ip_address TEXT,
                mac_address TEXT,
                room TEXT,
                capabilities TEXT,
                metadata TEXT,
                last_seen TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scenes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                actions TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS routines (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                trigger_type TEXT NOT NULL,
                trigger_config TEXT NOT NULL,
                actions TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                last_triggered TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                state TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def _load_data(self):
        """Load devices, scenes, and routines from database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Load devices
        for row in cursor.execute("SELECT * FROM devices").fetchall():
            device = SmartDevice(
                id=row['id'],
                name=row['name'],
                device_type=DeviceType(row['device_type']),
                manufacturer=row['manufacturer'] or "Unknown",
                model=row['model'],
                ip_address=row['ip_address'],
                mac_address=row['mac_address'],
                room=row['room'],
                capabilities=json.loads(row['capabilities'] or "[]"),
                metadata=json.loads(row['metadata'] or "{}"),
                last_seen=row['last_seen']
            )
            self.devices[device.id] = device

        # Load scenes
        for row in cursor.execute("SELECT * FROM scenes").fetchall():
            scene = Scene(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                actions=json.loads(row['actions']),
                created_at=row['created_at'],
                last_used=row['last_used']
            )
            self.scenes[scene.id] = scene

        # Load routines
        for row in cursor.execute("SELECT * FROM routines").fetchall():
            routine = Routine(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                trigger_type=row['trigger_type'],
                trigger_config=json.loads(row['trigger_config']),
                actions=json.loads(row['actions']),
                enabled=bool(row['enabled']),
                last_triggered=row['last_triggered']
            )
            self.routines[routine.id] = routine

        conn.close()

    def _load_hue_config(self):
        """Load Philips Hue configuration."""
        try:
            from .lights import BRIDGE_IP, HUE_USERNAME
            self._hue_bridge_ip = BRIDGE_IP
            self._hue_username = HUE_USERNAME
        except ImportError:
            pass

    def _save_device(self, device: SmartDevice):
        """Save a device to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO devices
            (id, name, device_type, manufacturer, model, ip_address, mac_address,
             room, capabilities, metadata, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            device.id, device.name, device.device_type.value,
            device.manufacturer, device.model, device.ip_address,
            device.mac_address, device.room,
            json.dumps(device.capabilities),
            json.dumps(device.metadata),
            device.last_seen
        ))

        conn.commit()
        conn.close()

    # ==================== DEVICE DISCOVERY ====================

    def discover_hue_lights(self) -> List[SmartDevice]:
        """Discover Philips Hue lights."""
        discovered = []

        if not self._hue_bridge_ip or not self._hue_username:
            return discovered

        try:
            url = f"http://{self._hue_bridge_ip}/api/{self._hue_username}/lights"
            response = requests.get(url, timeout=5)
            lights = response.json()

            for light_id, light_data in lights.items():
                device_id = f"hue_light_{light_id}"
                device = SmartDevice(
                    id=device_id,
                    name=light_data.get('name', f'Hue Light {light_id}'),
                    device_type=DeviceType.LIGHT,
                    manufacturer="Philips",
                    model=light_data.get('modelid'),
                    status=DeviceStatus.ONLINE if light_data.get('state', {}).get('reachable') else DeviceStatus.OFFLINE,
                    capabilities=['on_off', 'brightness', 'color'] if 'xy' in light_data.get('state', {}) else ['on_off', 'brightness'],
                    state=light_data.get('state', {}),
                    last_seen=datetime.datetime.now().isoformat(),
                    metadata={'hue_id': light_id, 'type': light_data.get('type')}
                )

                self.devices[device_id] = device
                self._save_device(device)
                discovered.append(device)

        except Exception as e:
            print(f"[SMARTHOME] Hue discovery error: {e}")

        return discovered

    def discover_devices_ssdp(self) -> List[SmartDevice]:
        """
        Discover devices using SSDP/UPnP protocol.
        This finds devices like smart TVs, speakers, etc.
        """
        discovered = []

        # SSDP M-SEARCH message
        ssdp_request = (
            'M-SEARCH * HTTP/1.1\r\n'
            'HOST: 239.255.255.250:1900\r\n'
            'MAN: "ssdp:discover"\r\n'
            'MX: 2\r\n'
            'ST: ssdp:all\r\n'
            '\r\n'
        )

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(DEVICE_SCAN_TIMEOUT)
            sock.sendto(ssdp_request.encode(), ('239.255.255.250', 1900))

            responses = []
            try:
                while True:
                    data, addr = sock.recvfrom(1024)
                    responses.append((data.decode(), addr))
            except socket.timeout:
                pass
            finally:
                sock.close()

            # Parse responses
            seen_ips = set()
            for response, addr in responses:
                ip = addr[0]
                if ip in seen_ips:
                    continue
                seen_ips.add(ip)

                # Parse response headers
                device_type = DeviceType.OTHER
                name = f"Device at {ip}"
                manufacturer = "Unknown"

                if 'samsung' in response.lower():
                    device_type = DeviceType.TV
                    manufacturer = "Samsung"
                elif 'roku' in response.lower():
                    device_type = DeviceType.TV
                    manufacturer = "Roku"
                elif 'sonos' in response.lower():
                    device_type = DeviceType.SPEAKER
                    manufacturer = "Sonos"
                elif 'philips-hue' in response.lower():
                    # Skip - we discover these separately
                    continue

                # Extract server/model info
                server_match = re.search(r'SERVER:\s*(.+)', response, re.I)
                if server_match:
                    name = server_match.group(1).strip()[:50]

                device_id = f"ssdp_{ip.replace('.', '_')}"
                device = SmartDevice(
                    id=device_id,
                    name=name,
                    device_type=device_type,
                    manufacturer=manufacturer,
                    ip_address=ip,
                    status=DeviceStatus.ONLINE,
                    last_seen=datetime.datetime.now().isoformat(),
                    metadata={'discovery': 'ssdp', 'raw_response': response[:500]}
                )

                self.devices[device_id] = device
                self._save_device(device)
                discovered.append(device)

        except Exception as e:
            print(f"[SMARTHOME] SSDP discovery error: {e}")

        return discovered

    def discover_all(self) -> Dict[str, List[SmartDevice]]:
        """Run all discovery methods."""
        results = {
            "hue_lights": self.discover_hue_lights(),
            "network_devices": self.discover_devices_ssdp()
        }
        return results

    # ==================== DEVICE CONTROL ====================

    def get_device(self, device_id: str) -> Optional[SmartDevice]:
        """Get a device by ID."""
        return self.devices.get(device_id)

    def get_device_by_name(self, name: str) -> Optional[SmartDevice]:
        """Find a device by name (fuzzy match)."""
        name_lower = name.lower()
        for device in self.devices.values():
            if name_lower in device.name.lower():
                return device
        return None

    def get_devices_by_room(self, room: str) -> List[SmartDevice]:
        """Get all devices in a room."""
        room_lower = room.lower()
        return [d for d in self.devices.values()
                if d.room and room_lower in d.room.lower()]

    def get_devices_by_type(self, device_type: DeviceType) -> List[SmartDevice]:
        """Get all devices of a type."""
        return [d for d in self.devices.values()
                if d.device_type == device_type]

    def set_device_room(self, device_id: str, room: str) -> bool:
        """Assign a device to a room."""
        device = self.devices.get(device_id)
        if device:
            device.room = room
            self._save_device(device)
            return True
        return False

    def control_device(self, device_id: str, action: str,
                       params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Control a device.

        Actions depend on device type:
        - Lights: on, off, brightness, color
        - Switches: on, off, toggle
        - Thermostats: set_temp, set_mode
        """
        device = self.devices.get(device_id)
        if not device:
            return {"success": False, "error": f"Device not found: {device_id}"}

        if params is None:
            params = {}

        # Handle Hue lights
        if device.manufacturer == "Philips" and device.device_type == DeviceType.LIGHT:
            return self._control_hue_light(device, action, params)

        # Generic device control placeholder
        return {
            "success": False,
            "error": f"Control not implemented for {device.manufacturer} {device.device_type.value}"
        }

    def _control_hue_light(self, device: SmartDevice, action: str,
                           params: Dict[str, Any]) -> Dict[str, Any]:
        """Control a Philips Hue light."""
        if not self._hue_bridge_ip or not self._hue_username:
            return {"success": False, "error": "Hue bridge not configured"}

        hue_id = device.metadata.get('hue_id')
        if not hue_id:
            return {"success": False, "error": "Invalid Hue device"}

        url = f"http://{self._hue_bridge_ip}/api/{self._hue_username}/lights/{hue_id}/state"

        # Build state update
        state = {}

        if action == 'on':
            state['on'] = True
        elif action == 'off':
            state['on'] = False
        elif action == 'toggle':
            current_on = device.state.get('on', False)
            state['on'] = not current_on
        elif action == 'brightness':
            bri = params.get('brightness', params.get('level', 100))
            state['on'] = True
            state['bri'] = int(min(254, max(1, bri * 2.54)))
        elif action == 'color':
            # Handle color by name or RGB
            color = params.get('color', '')
            from .lights import COLOR_MAP
            if color.lower() in COLOR_MAP:
                state.update(COLOR_MAP[color.lower()])
                state['on'] = True

        try:
            response = requests.put(url, json=state, timeout=5)
            result = response.json()

            # Update local state
            device.state.update(state)
            device.last_seen = datetime.datetime.now().isoformat()

            return {
                "success": True,
                "device": device.name,
                "action": action,
                "result": result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==================== SCENES ====================

    def create_scene(self, name: str, actions: List[Dict[str, Any]],
                     description: str = None) -> Scene:
        """Create a new scene."""
        import uuid
        scene_id = str(uuid.uuid4())[:8]

        scene = Scene(
            id=scene_id,
            name=name,
            description=description,
            actions=actions,
            created_at=datetime.datetime.now().isoformat()
        )

        self.scenes[scene_id] = scene

        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO scenes (id, name, description, actions, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (scene.id, scene.name, scene.description,
              json.dumps(scene.actions), scene.created_at))
        conn.commit()
        conn.close()

        return scene

    def activate_scene(self, scene_id: str) -> Dict[str, Any]:
        """Activate a scene."""
        scene = self.scenes.get(scene_id)
        if not scene:
            return {"success": False, "error": f"Scene not found: {scene_id}"}

        results = []
        for action in scene.actions:
            device_id = action.get('device_id')
            action_type = action.get('action')
            params = action.get('params', {})

            result = self.control_device(device_id, action_type, params)
            results.append({
                "device_id": device_id,
                "action": action_type,
                "result": result
            })

        # Update last used
        scene.last_used = datetime.datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE scenes SET last_used = ? WHERE id = ?",
                      (scene.last_used, scene.id))
        conn.commit()
        conn.close()

        return {
            "success": True,
            "scene": scene.name,
            "results": results
        }

    def get_scene_by_name(self, name: str) -> Optional[Scene]:
        """Find a scene by name."""
        name_lower = name.lower()
        for scene in self.scenes.values():
            if name_lower in scene.name.lower():
                return scene
        return None

    # ==================== STATUS & INFO ====================

    def get_all_devices(self) -> List[SmartDevice]:
        """Get all registered devices."""
        return list(self.devices.values())

    def get_home_status(self) -> Dict[str, Any]:
        """Get overall smart home status."""
        devices = self.get_all_devices()

        online = sum(1 for d in devices if d.status == DeviceStatus.ONLINE)
        offline = sum(1 for d in devices if d.status == DeviceStatus.OFFLINE)

        by_type = {}
        for d in devices:
            t = d.device_type.value
            by_type[t] = by_type.get(t, 0) + 1

        by_room = {}
        for d in devices:
            r = d.room or "Unassigned"
            by_room[r] = by_room.get(r, 0) + 1

        # Lights status
        lights = self.get_devices_by_type(DeviceType.LIGHT)
        lights_on = sum(1 for l in lights if l.state.get('on', False))

        return {
            "total_devices": len(devices),
            "online": online,
            "offline": offline,
            "by_type": by_type,
            "by_room": by_room,
            "lights": {
                "total": len(lights),
                "on": lights_on,
                "off": len(lights) - lights_on
            },
            "scenes": len(self.scenes),
            "routines": len(self.routines)
        }

    def refresh_device_status(self, device_id: str = None) -> bool:
        """Refresh status for one or all devices."""
        if device_id:
            devices = [self.devices.get(device_id)] if device_id in self.devices else []
        else:
            devices = list(self.devices.values())

        for device in devices:
            if device.manufacturer == "Philips" and device.device_type == DeviceType.LIGHT:
                # Refresh Hue light
                hue_id = device.metadata.get('hue_id')
                if hue_id and self._hue_bridge_ip and self._hue_username:
                    try:
                        url = f"http://{self._hue_bridge_ip}/api/{self._hue_username}/lights/{hue_id}"
                        response = requests.get(url, timeout=3)
                        data = response.json()
                        device.state = data.get('state', {})
                        device.status = DeviceStatus.ONLINE if data.get('state', {}).get('reachable') else DeviceStatus.OFFLINE
                        device.last_seen = datetime.datetime.now().isoformat()
                    except Exception:
                        device.status = DeviceStatus.OFFLINE

        return True


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_smarthome_manager: Optional[SmartHomeManager] = None


def get_smarthome_manager() -> SmartHomeManager:
    """Get or create the global smart home manager."""
    global _smarthome_manager
    if _smarthome_manager is None:
        _smarthome_manager = SmartHomeManager()
    return _smarthome_manager


# ================================================================================
# EXECUTOR FUNCTIONS
# ================================================================================

def discover_devices() -> str:
    """Discover all smart home devices."""
    manager = get_smarthome_manager()
    results = manager.discover_all()

    total = sum(len(v) for v in results.values())

    return json.dumps({
        "success": True,
        "message": f"Discovered {total} device(s)",
        "hue_lights": len(results.get('hue_lights', [])),
        "network_devices": len(results.get('network_devices', [])),
        "devices": [d.to_dict() for devices in results.values() for d in devices]
    })


def list_devices(device_type: str = None, room: str = None) -> str:
    """List smart home devices."""
    manager = get_smarthome_manager()

    if device_type:
        try:
            dt = DeviceType(device_type.lower())
            devices = manager.get_devices_by_type(dt)
        except ValueError:
            devices = manager.get_all_devices()
    elif room:
        devices = manager.get_devices_by_room(room)
    else:
        devices = manager.get_all_devices()

    # Format for display
    if not devices:
        message = "No devices found. Try running device discovery."
    else:
        lines = [f"Found {len(devices)} device(s):"]
        for d in devices:
            status_icon = "🟢" if d.status == DeviceStatus.ONLINE else "🔴"
            room_str = f" [{d.room}]" if d.room else ""
            lines.append(f"{status_icon} {d.name} ({d.device_type.value}){room_str}")
        message = "\n".join(lines)

    return json.dumps({
        "success": True,
        "count": len(devices),
        "devices": [d.to_dict() for d in devices],
        "formatted": message
    })


def control_device_cmd(device_name: str, action: str, **params) -> str:
    """Control a smart home device."""
    manager = get_smarthome_manager()

    device = manager.get_device_by_name(device_name)
    if not device:
        return json.dumps({
            "success": False,
            "error": f"Device not found: {device_name}"
        })

    result = manager.control_device(device.id, action, params)
    return json.dumps(result)


def get_home_status() -> str:
    """Get smart home status summary."""
    manager = get_smarthome_manager()
    status = manager.get_home_status()

    # Format message
    lines = ["Smart Home Status:"]
    lines.append(f"  Devices: {status['total_devices']} ({status['online']} online, {status['offline']} offline)")
    lines.append(f"  Lights: {status['lights']['on']}/{status['lights']['total']} on")
    if status['scenes'] > 0:
        lines.append(f"  Scenes: {status['scenes']}")

    return json.dumps({
        "success": True,
        **status,
        "formatted": "\n".join(lines)
    })


def create_scene_cmd(name: str, devices_actions: List[Dict[str, Any]],
                     description: str = None) -> str:
    """Create a scene."""
    manager = get_smarthome_manager()

    # Convert device names to IDs
    actions = []
    for da in devices_actions:
        device_name = da.get('device')
        device = manager.get_device_by_name(device_name)
        if device:
            actions.append({
                'device_id': device.id,
                'action': da.get('action'),
                'params': da.get('params', {})
            })

    scene = manager.create_scene(name, actions, description)

    return json.dumps({
        "success": True,
        "message": f"Created scene '{name}'",
        "scene": scene.to_dict()
    })


def activate_scene_cmd(scene_name: str) -> str:
    """Activate a scene by name."""
    manager = get_smarthome_manager()

    scene = manager.get_scene_by_name(scene_name)
    if not scene:
        return json.dumps({
            "success": False,
            "error": f"Scene not found: {scene_name}"
        })

    result = manager.activate_scene(scene.id)
    return json.dumps(result)


def assign_room_cmd(device_name: str, room: str) -> str:
    """Assign a device to a room."""
    manager = get_smarthome_manager()

    device = manager.get_device_by_name(device_name)
    if not device:
        return json.dumps({
            "success": False,
            "error": f"Device not found: {device_name}"
        })

    manager.set_device_room(device.id, room)

    return json.dumps({
        "success": True,
        "message": f"Assigned {device.name} to {room}"
    })


def execute_smarthome_command(action: str, params: Dict[str, Any] = None) -> str:
    """Execute a smart home command."""
    if params is None:
        params = {}

    action_lower = action.lower().strip()

    if action_lower in ['discover', 'scan', 'find_devices']:
        return discover_devices()

    elif action_lower in ['list', 'list_devices', 'devices', 'show_devices']:
        return list_devices(
            device_type=params.get('type'),
            room=params.get('room')
        )

    elif action_lower in ['status', 'home_status', 'overview']:
        return get_home_status()

    elif action_lower in ['control', 'set', 'turn']:
        return control_device_cmd(
            device_name=params.get('device', ''),
            action=params.get('action', ''),
            **params.get('params', {})
        )

    elif action_lower in ['create_scene', 'new_scene']:
        return create_scene_cmd(
            name=params.get('name', ''),
            devices_actions=params.get('actions', []),
            description=params.get('description')
        )

    elif action_lower in ['activate_scene', 'scene', 'run_scene']:
        return activate_scene_cmd(params.get('name', ''))

    elif action_lower in ['assign_room', 'set_room']:
        return assign_room_cmd(
            device_name=params.get('device', ''),
            room=params.get('room', '')
        )

    else:
        return json.dumps({
            "success": False,
            "error": f"Unknown smart home action: {action}",
            "available_actions": [
                "discover", "list_devices", "status",
                "control", "create_scene", "activate_scene", "assign_room"
            ]
        })


__all__ = [
    'SmartHomeManager',
    'SmartDevice',
    'Scene',
    'Routine',
    'DeviceType',
    'DeviceStatus',
    'get_smarthome_manager',
    'discover_devices',
    'list_devices',
    'control_device_cmd',
    'get_home_status',
    'create_scene_cmd',
    'activate_scene_cmd',
    'assign_room_cmd',
    'execute_smarthome_command',
]
