"""
Blue Robot Vision Tools
=======================
Camera capture, image viewing, music visualizer, and recognition.

v9.0 ENHANCEMENTS:
- Face recognition integration
- Place recognition integration
- Automatic recognition on camera capture
- Recognition context for vision model
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# ================================================================================
# CONFIGURATION
# ================================================================================

UPLOAD_FOLDER = Path(os.environ.get("UPLOAD_FOLDER", "uploads"))


# ================================================================================
# VISION IMAGE QUEUE SYSTEM
# ================================================================================

@dataclass
class ImageInfo:
    """Information about an image to be shown to the vision model."""
    filename: str
    filepath: str
    hash: str
    is_camera_capture: bool
    added_at: str


class VisionImageQueue:
    """
    Manages the queue of images to be shown to the vision model.

    Features:
    - Separates NEW images from OLD images
    - Tracks which images have been viewed
    - Prevents showing the same image multiple times
    - Purges old camera captures from conversation context
    """

    def __init__(self):
        self.pending_images: List[ImageInfo] = []
        self.viewed_images: Set[str] = set()

    def clear(self):
        """Clear all pending images."""
        print(f"   [VISION-QUEUE] Clearing {len(self.pending_images)} pending images")
        self.pending_images = []

    def add_image(self, filepath: str, filename: str, is_camera: bool = False):
        """Add an image to the queue to be shown."""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        img_hash = hash_md5.hexdigest()

        if is_camera:
            self.pending_images = [img for img in self.pending_images
                                  if not img.is_camera_capture]
            print(f"   [VISION-QUEUE] New camera image, cleared old camera images")

        if img_hash not in self.viewed_images:
            self.pending_images.append(ImageInfo(
                filename=filename,
                filepath=filepath,
                hash=img_hash,
                is_camera_capture=is_camera,
                added_at=datetime.datetime.now().isoformat()
            ))
            print(f"   [VISION-QUEUE] Added {filename} (hash: {img_hash[:8]})")
        else:
            print(f"   [VISION-QUEUE] Skipped {filename} - already viewed")

    def mark_as_viewed(self):
        """Mark all current pending images as viewed."""
        for img in self.pending_images:
            self.viewed_images.add(img.hash)
        print(f"   [VISION-QUEUE] Marked {len(self.pending_images)} images as viewed")

    def has_images(self) -> bool:
        """Check if there are pending images."""
        return len(self.pending_images) > 0

    def get_pending(self) -> List[ImageInfo]:
        """Get list of pending images."""
        return self.pending_images.copy()


# Global vision queue
_vision_queue = VisionImageQueue()


def get_vision_queue() -> VisionImageQueue:
    """Get the global vision queue."""
    return _vision_queue


# ================================================================================
# VIEW IMAGE
# ================================================================================

def view_image(filename: str = None, query: str = None,
               load_index_fn=None, vision_queue: VisionImageQueue = None) -> str:
    """
    View an image file for the vision model to analyze.

    Args:
        filename: Specific image filename to view
        query: Search query if filename not provided
        load_index_fn: Function to load document index
        vision_queue: Vision queue instance (uses global if not provided)

    Returns:
        JSON string with image information for vision model injection
    """
    if vision_queue is None:
        vision_queue = _vision_queue

    print(f"   [VIEW] Request to view image - filename: {filename}, query: {query}")

    # Load document index
    if load_index_fn:
        index = load_index_fn()
    else:
        from .documents import load_document_index
        index = load_document_index()

    documents = index.get("documents", [])

    # Filter to only image files
    image_docs = [
        doc for doc in documents
        if doc['filename'].lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'))
    ]

    if not image_docs:
        return json.dumps({
            "success": False,
            "message": "No images found in uploaded documents. Upload images at http://127.0.0.1:5000/documents/upload"
        })

    print(f"   [DATA] Found {len(image_docs)} total image(s) in documents")

    found_images = []

    if filename:
        filename_lower = filename.lower()
        for doc in image_docs:
            doc_filename_lower = doc['filename'].lower()
            if doc_filename_lower == filename_lower or filename_lower in doc_filename_lower:
                found_images.append(doc)
                print(f"   [MATCH] Found by filename: {doc['filename']}")

    elif query:
        query_lower = query.lower()
        for doc in image_docs:
            if query_lower in doc['filename'].lower():
                found_images.append(doc)
                print(f"   [MATCH] Found by query: {doc['filename']}")

    else:
        found_images = image_docs[:3]
        print(f"   [LIST] Showing {len(found_images)} recent image(s)")

    if not found_images:
        available = ", ".join([doc['filename'] for doc in image_docs[:10]])
        return json.dumps({
            "success": False,
            "message": f"No images found matching '{filename or query}'. Available images: {available}"
        })

    # Queue images for vision model
    image_results = []
    for doc in found_images[:3]:
        filepath = doc.get('filepath', '')
        if os.path.exists(filepath):
            image_results.append({
                'filename': doc['filename'],
                'filepath': filepath,
                'score': 1.0
            })
            vision_queue.add_image(
                filepath=filepath,
                filename=doc['filename'],
                is_camera=False
            )
            print(f"   [QUEUE] Queued image for viewing: {doc['filename']}")

    image_names = [img['filename'] for img in image_results]

    return json.dumps({
        "success": True,
        "message": f"Viewing {len(image_results)} image(s): {', '.join(image_names)}",
        "images": image_names,
        "_instruction": "The images will be shown to you in the next message. Analyze them and respond to the user's question."
    })


# ================================================================================
# CAMERA CAPTURE
# ================================================================================

def capture_camera_image(vision_queue: VisionImageQueue = None,
                         upload_folder: Path = None) -> str:
    """
    Capture a BRAND NEW image from the camera.

    Features:
    - Unique timestamp with milliseconds
    - Longer warmup for better quality
    - Discards first frames
    - High quality JPEG
    - Clears vision queue and adds only THIS new image
    """
    if vision_queue is None:
        vision_queue = _vision_queue
    if upload_folder is None:
        upload_folder = UPLOAD_FOLDER

    print(f"   [CAMERA] Capturing brand new image...")

    try:
        import cv2

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        camera = cv2.VideoCapture(0)

        if not camera.isOpened():
            print(f"   [ERROR] Could not open camera")
            return json.dumps({
                "success": False,
                "error": "Could not access camera. Make sure a camera is connected and not in use by another application."
            })

        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)

        time.sleep(1.2)

        for _ in range(3):
            camera.read()
            time.sleep(0.1)

        ret, frame = camera.read()
        camera.release()

        if not ret or frame is None:
            print(f"   [ERROR] Could not capture frame")
            return json.dumps({
                "success": False,
                "error": "Could not capture image from camera. Try again."
            })

        # Save the image
        upload_folder.mkdir(parents=True, exist_ok=True)
        filename = f"camera_capture_{timestamp}.jpg"
        filepath = str(upload_folder / filename)

        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 95]
        cv2.imwrite(filepath, frame, encode_params)

        # Calculate hash for uniqueness
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            hash_md5.update(f.read())
        image_hash = hash_md5.hexdigest()

        height, width = frame.shape[:2]

        print(f"   [OK] Captured image: {filename} ({width}x{height})")

        # Clear old images and add new one
        vision_queue.clear()
        vision_queue.add_image(filepath, filename, is_camera=True)

        return json.dumps({
            "success": True,
            "message": f"Captured new image: {filename}",
            "filename": filename,
            "filepath": filepath,
            "dimensions": f"{width}x{height}",
            "hash": image_hash[:16],
            "timestamp": timestamp,
            "_instruction": "FRESH camera capture! Analyze this new image and tell the user what you see."
        })

    except ImportError:
        return json.dumps({
            "success": False,
            "error": "Camera capture requires OpenCV. Install with: pip install opencv-python"
        })
    except Exception as e:
        print(f"   [ERROR] Camera error: {e}")
        return json.dumps({
            "success": False,
            "error": f"Camera error: {str(e)}"
        })


# ================================================================================
# MUSIC VISUALIZER
# ================================================================================

_visualizer_active = False
_visualizer_thread = None


def start_music_visualizer(duration_seconds: int = 300, style: str = "party",
                           get_lights_fn=None, control_light_fn=None,
                           bridge_ip: str = None, hue_username: str = None) -> str:
    """
    Start a dynamic light show that changes colors rhythmically.

    Args:
        duration_seconds: How long to run (default 5 minutes)
        style: "party" (fast colorful), "chill" (slow smooth), "pulse" (rhythmic)
        get_lights_fn: Function to get Hue lights
        control_light_fn: Function to control a light
        bridge_ip: Hue bridge IP
        hue_username: Hue username
    """
    global _visualizer_active, _visualizer_thread

    if not bridge_ip or not hue_username:
        return "Hue lights not configured. Can't start visualizer."

    if _visualizer_active:
        return "Music visualizer is already running! Say 'stop visualizer' to turn it off first."

    print(f"   [SYNC] Starting {style} music visualizer for {duration_seconds} seconds")

    def visualizer_loop():
        global _visualizer_active

        if get_lights_fn is None:
            from .lights import get_hue_lights, control_hue_light
            lights = get_hue_lights()
            ctrl_fn = control_hue_light
        else:
            lights = get_lights_fn()
            ctrl_fn = control_light_fn

        if not lights:
            _visualizer_active = False
            return

        light_ids = list(lights.keys())
        start_time = time.time()

        if style == "party":
            color_options = [
                {"hue": 0, "sat": 254, "bri": 254},
                {"hue": 46920, "sat": 254, "bri": 254},
                {"hue": 25500, "sat": 254, "bri": 254},
                {"hue": 12750, "sat": 254, "bri": 254},
                {"hue": 50000, "sat": 254, "bri": 254},
                {"hue": 56100, "sat": 254, "bri": 254},
                {"hue": 30000, "sat": 254, "bri": 254},
                {"hue": 5000, "sat": 254, "bri": 254},
            ]
            transition_time = 5
            change_interval = 1.5
        elif style == "chill":
            color_options = [
                {"hue": 46920, "sat": 200, "bri": 150},
                {"hue": 50000, "sat": 180, "bri": 130},
                {"hue": 30000, "sat": 190, "bri": 140},
                {"hue": 25500, "sat": 160, "bri": 120},
            ]
            transition_time = 20
            change_interval = 4.0
        elif style == "pulse":
            color_options = [
                {"hue": 0, "sat": 254, "bri": 254},
                {"hue": 0, "sat": 254, "bri": 100},
                {"hue": 46920, "sat": 254, "bri": 254},
                {"hue": 46920, "sat": 254, "bri": 100},
            ]
            transition_time = 3
            change_interval = 0.8
        else:
            color_options = [
                {"hue": 0, "sat": 254, "bri": 254},
                {"hue": 46920, "sat": 254, "bri": 254},
            ]
            transition_time = 5
            change_interval = 2.0

        try:
            while _visualizer_active and (time.time() - start_time) < duration_seconds:
                for light_id in light_ids:
                    color = random.choice(color_options).copy()
                    color["on"] = True
                    color["transitiontime"] = transition_time
                    ctrl_fn(light_id, color)

                time.sleep(change_interval)
        finally:
            _visualizer_active = False
            print("   [SYNC] Music visualizer ended")

    _visualizer_active = True
    _visualizer_thread = threading.Thread(target=visualizer_loop, daemon=True)
    _visualizer_thread.start()

    style_descriptions = {
        "party": "fast, vibrant colors",
        "chill": "slow, smooth transitions",
        "pulse": "rhythmic pulsing"
    }

    return f"🎨 Music visualizer started ({style_descriptions.get(style, 'dynamic')})! Lights will dance for {duration_seconds//60} minutes."


def stop_music_visualizer() -> str:
    """Stop the music visualizer."""
    global _visualizer_active

    if not _visualizer_active:
        return "No visualizer is currently running."

    _visualizer_active = False
    print("   [SYNC] Stopping music visualizer...")

    time.sleep(1)

    return "🎨 Music visualizer stopped."


def is_visualizer_active() -> bool:
    """Check if visualizer is running."""
    return _visualizer_active


# ================================================================================
# RECOGNITION INTEGRATION
# ================================================================================

def capture_and_recognize(vision_queue: VisionImageQueue = None,
                          upload_folder: Path = None,
                          run_recognition: bool = True) -> str:
    """
    Capture a camera image AND run face/place recognition.

    This is the enhanced camera capture that automatically
    identifies people and places in the image.

    Args:
        vision_queue: Vision queue instance
        upload_folder: Folder to save captures
        run_recognition: Whether to run face/place recognition

    Returns:
        JSON result with capture info and recognition results
    """
    if vision_queue is None:
        vision_queue = _vision_queue
    if upload_folder is None:
        upload_folder = UPLOAD_FOLDER

    print(f"   [CAMERA+] Capturing with recognition...")

    try:
        import cv2

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        camera = cv2.VideoCapture(0)

        if not camera.isOpened():
            return json.dumps({
                "success": False,
                "error": "Could not access camera."
            })

        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)

        time.sleep(1.2)

        for _ in range(3):
            camera.read()
            time.sleep(0.1)

        ret, frame = camera.read()
        camera.release()

        if not ret or frame is None:
            return json.dumps({
                "success": False,
                "error": "Could not capture image from camera."
            })

        # Save the image
        upload_folder.mkdir(parents=True, exist_ok=True)
        filename = f"camera_capture_{timestamp}.jpg"
        filepath = str(upload_folder / filename)

        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 95]
        cv2.imwrite(filepath, frame, encode_params)

        height, width = frame.shape[:2]

        print(f"   [OK] Captured: {filename} ({width}x{height})")

        # Clear old images and add new one
        vision_queue.clear()
        vision_queue.add_image(filepath, filename, is_camera=True)

        result = {
            "success": True,
            "message": f"Captured: {filename}",
            "filename": filename,
            "filepath": filepath,
            "dimensions": f"{width}x{height}",
            "timestamp": timestamp
        }

        # Run recognition if requested
        if run_recognition:
            try:
                from .recognition import get_recognition_manager

                manager = get_recognition_manager()
                recognition_result = manager.analyze_image(filepath)

                result["recognition"] = recognition_result.to_dict()
                result["recognition_summary"] = recognition_result.get_summary()

                # Add recognition context to message
                if recognition_result.faces or recognition_result.place:
                    result["message"] += f" - {recognition_result.get_summary()}"

                print(f"   [RECOGNITION] {recognition_result.get_summary()}")

            except ImportError as e:
                print(f"   [RECOGNITION] Not available: {e}")
                result["recognition_note"] = "Face recognition not available. Install face_recognition package."
            except Exception as e:
                print(f"   [RECOGNITION] Error: {e}")
                result["recognition_error"] = str(e)

        result["_instruction"] = "Analyze this image. " + result.get("recognition_summary", "Describe what you see.")

        return json.dumps(result)

    except ImportError:
        return json.dumps({
            "success": False,
            "error": "Camera capture requires OpenCV. Install with: pip install opencv-python"
        })
    except Exception as e:
        print(f"   [ERROR] Camera error: {e}")
        return json.dumps({
            "success": False,
            "error": f"Camera error: {str(e)}"
        })


def recognize_uploaded_image(filepath: str) -> str:
    """
    Run face and place recognition on an existing image.

    Args:
        filepath: Path to the image file

    Returns:
        JSON result with recognition info
    """
    if not os.path.exists(filepath):
        return json.dumps({
            "success": False,
            "error": f"Image not found: {filepath}"
        })

    try:
        from .recognition import get_recognition_manager

        manager = get_recognition_manager()
        result = manager.analyze_image(filepath)

        return json.dumps({
            "success": True,
            **result.to_dict()
        })

    except ImportError as e:
        return json.dumps({
            "success": False,
            "error": f"Recognition not available: {e}. Install face_recognition and opencv-python."
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Recognition error: {str(e)}"
        })


def get_recognition_context() -> str:
    """
    Get context about known people and places for the vision model.

    Returns formatted string with recognition info.
    """
    context_parts = []

    try:
        from .recognition import get_recognition_manager

        manager = get_recognition_manager()

        # Get known people
        people = manager.get_known_people()
        if people:
            context_parts.append("=== PEOPLE I CAN RECOGNIZE ===")
            for person in people:
                line = f"• {person['name']}"
                if person.get('relationship'):
                    line += f" ({person['relationship']})"
                if person.get('last_seen'):
                    line += f" - last seen: {person['last_seen'][:10]}"
                context_parts.append(line)

        # Get known places
        places = manager.get_known_places()
        if places:
            context_parts.append("\n=== PLACES I CAN RECOGNIZE ===")
            for place in places:
                line = f"• {place['name']}"
                if place.get('description'):
                    line += f" - {place['description']}"
                context_parts.append(line)

    except ImportError:
        context_parts.append("(Face/place recognition not installed)")
    except Exception as e:
        context_parts.append(f"(Recognition error: {e})")

    return "\n".join(context_parts)


def teach_person(name: str, image_path: str,
                 relationship: str = None,
                 description: str = None) -> str:
    """
    Teach Blue to recognize a person.

    Args:
        name: Person's name
        image_path: Path to image with their face
        relationship: Optional relationship (e.g., "family", "friend")
        description: Optional description

    Returns:
        JSON result
    """
    try:
        from .recognition import get_recognition_manager

        manager = get_recognition_manager()
        result = manager.enroll_person(name, image_path, relationship, description)

        return json.dumps(result)

    except ImportError as e:
        return json.dumps({
            "success": False,
            "error": f"Recognition not available: {e}"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


def teach_place(name: str, image_path: str,
                description: str = None,
                typical_contents: str = None) -> str:
    """
    Teach Blue to recognize a place.

    Args:
        name: Place name
        image_path: Path to reference image
        description: Optional description
        typical_contents: What's typically in this place

    Returns:
        JSON result
    """
    try:
        from .recognition import get_recognition_manager

        manager = get_recognition_manager()
        result = manager.enroll_place(name, image_path, description, typical_contents)

        return json.dumps(result)

    except ImportError as e:
        return json.dumps({
            "success": False,
            "error": f"Recognition not available: {e}"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


def who_do_i_know() -> str:
    """
    List all people Blue can recognize.

    Returns:
        JSON result with list of known people
    """
    try:
        from .recognition import get_recognition_manager

        manager = get_recognition_manager()
        people = manager.get_known_people()

        if not people:
            return json.dumps({
                "success": True,
                "message": "I don't know anyone yet. You can teach me to recognize people!",
                "count": 0,
                "people": []
            })

        # Format for display
        lines = ["People I can recognize:"]
        for person in people:
            line = f"• {person['name']}"
            if person.get('relationship'):
                line += f" ({person['relationship']})"
            if person.get('times_seen', 0) > 0:
                line += f" - seen {person['times_seen']} time(s)"
            lines.append(line)

        return json.dumps({
            "success": True,
            "count": len(people),
            "people": people,
            "formatted": "\n".join(lines)
        })

    except ImportError as e:
        return json.dumps({
            "success": False,
            "error": f"Recognition not available: {e}"
        })


def where_do_i_know() -> str:
    """
    List all places Blue can recognize.

    Returns:
        JSON result with list of known places
    """
    try:
        from .recognition import get_recognition_manager

        manager = get_recognition_manager()
        places = manager.get_known_places()

        if not places:
            return json.dumps({
                "success": True,
                "message": "I don't recognize any places yet. You can teach me!",
                "count": 0,
                "places": []
            })

        # Format for display
        lines = ["Places I can recognize:"]
        for place in places:
            line = f"• {place['name']}"
            if place.get('description'):
                line += f" - {place['description']}"
            lines.append(line)

        return json.dumps({
            "success": True,
            "count": len(places),
            "places": places,
            "formatted": "\n".join(lines)
        })

    except ImportError as e:
        return json.dumps({
            "success": False,
            "error": f"Recognition not available: {e}"
        })


__all__ = [
    # Core vision
    'ImageInfo', 'VisionImageQueue', 'get_vision_queue',
    'view_image', 'capture_camera_image',
    'start_music_visualizer', 'stop_music_visualizer', 'is_visualizer_active',
    # Recognition integration
    'capture_and_recognize',
    'recognize_uploaded_image',
    'get_recognition_context',
    'teach_person',
    'teach_place',
    'who_do_i_know',
    'where_do_i_know',
]
