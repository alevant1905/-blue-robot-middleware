"""
Blue Robot Recognition System
==============================
Face recognition and place recognition for Blue's visual memory.

Uses:
- face_recognition library for facial recognition
- OpenCV for image processing and feature matching
- SQLite for persistent storage of encodings
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import json
import os
import pickle
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# ================================================================================
# CONFIGURATION
# ================================================================================

RECOGNITION_DB = os.environ.get("BLUE_RECOGNITION_DB", "data/recognition.db")
FACE_ENCODINGS_DIR = os.environ.get("BLUE_FACE_ENCODINGS_DIR", "data/face_encodings")
PLACE_FEATURES_DIR = os.environ.get("BLUE_PLACE_FEATURES_DIR", "data/place_features")

# Recognition thresholds
FACE_MATCH_THRESHOLD = 0.6  # Lower = stricter matching
PLACE_MATCH_THRESHOLD = 0.7  # Higher = more matches needed


# ================================================================================
# DATA CLASSES
# ================================================================================

@dataclass
class FaceMatch:
    """Result of a face recognition match."""
    name: str
    confidence: float
    distance: float
    location: Tuple[int, int, int, int]  # top, right, bottom, left
    relationship: Optional[str] = None
    last_seen: Optional[str] = None
    times_seen: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "confidence": round(self.confidence, 2),
            "distance": round(self.distance, 3),
            "location": self.location,
            "relationship": self.relationship,
            "last_seen": self.last_seen,
            "times_seen": self.times_seen
        }


@dataclass
class PlaceMatch:
    """Result of a place recognition match."""
    name: str
    confidence: float
    match_count: int
    description: Optional[str] = None
    typical_contents: Optional[str] = None
    last_seen: Optional[str] = None
    times_seen: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "confidence": round(self.confidence, 2),
            "match_count": self.match_count,
            "description": self.description,
            "typical_contents": self.typical_contents,
            "last_seen": self.last_seen,
            "times_seen": self.times_seen
        }


@dataclass
class RecognitionResult:
    """Complete recognition result for an image."""
    faces: List[FaceMatch] = field(default_factory=list)
    place: Optional[PlaceMatch] = None
    unknown_faces: int = 0
    processing_time: float = 0.0
    image_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "faces": [f.to_dict() for f in self.faces],
            "place": self.place.to_dict() if self.place else None,
            "unknown_faces": self.unknown_faces,
            "processing_time": round(self.processing_time, 3),
            "image_hash": self.image_hash,
            "summary": self.get_summary()
        }

    def get_summary(self) -> str:
        """Get human-readable summary."""
        parts = []

        if self.faces:
            names = [f.name for f in self.faces]
            if len(names) == 1:
                parts.append(f"I see {names[0]}")
            elif len(names) == 2:
                parts.append(f"I see {names[0]} and {names[1]}")
            else:
                parts.append(f"I see {', '.join(names[:-1])}, and {names[-1]}")

        if self.unknown_faces > 0:
            if self.unknown_faces == 1:
                parts.append("There's someone I don't recognize")
            else:
                parts.append(f"There are {self.unknown_faces} people I don't recognize")

        if self.place:
            parts.append(f"This looks like {self.place.name}")

        if not parts:
            return "I don't recognize anyone or the location in this image"

        return ". ".join(parts)


# ================================================================================
# FACE RECOGNITION ENGINE
# ================================================================================

class FaceRecognitionEngine:
    """
    Handles face detection, encoding, and recognition.

    Features:
    - Store face encodings for known people
    - Match new faces against stored encodings
    - Learn new faces with multiple samples
    - Track confidence and viewing history
    """

    def __init__(self, db_path: str = RECOGNITION_DB,
                 encodings_dir: str = FACE_ENCODINGS_DIR):
        self.db_path = db_path
        self.encodings_dir = encodings_dir
        self._face_recognition = None
        self._cv2 = None

        self._known_encodings: Dict[str, List[np.ndarray]] = {}
        self._known_metadata: Dict[str, Dict] = {}

        self._init_directories()
        self._init_db()
        self._load_encodings()

    def _init_directories(self):
        """Create necessary directories."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.encodings_dir, exist_ok=True)

    def _init_db(self):
        """Initialize the recognition database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS known_faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                relationship TEXT,
                description TEXT,
                num_encodings INTEGER DEFAULT 0,
                last_seen TIMESTAMP,
                times_seen INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS face_sightings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                confidence REAL,
                image_hash TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (name) REFERENCES known_faces(name)
            )
        """)

        conn.commit()
        conn.close()

    def _load_encodings(self):
        """Load face encodings from disk."""
        self._known_encodings = {}
        self._known_metadata = {}

        # Load from database
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        rows = cursor.execute("SELECT * FROM known_faces").fetchall()
        conn.close()

        for row in rows:
            name = row['name']
            self._known_metadata[name] = {
                'relationship': row['relationship'],
                'description': row['description'],
                'last_seen': row['last_seen'],
                'times_seen': row['times_seen']
            }

            # Load encodings from file
            encoding_file = os.path.join(self.encodings_dir, f"{name}.pkl")
            if os.path.exists(encoding_file):
                try:
                    with open(encoding_file, 'rb') as f:
                        self._known_encodings[name] = pickle.load(f)
                except Exception as e:
                    print(f"[FACE] Error loading encodings for {name}: {e}")
                    self._known_encodings[name] = []
            else:
                self._known_encodings[name] = []

    def _save_encodings(self, name: str):
        """Save face encodings to disk."""
        if name not in self._known_encodings:
            return

        encoding_file = os.path.join(self.encodings_dir, f"{name}.pkl")
        try:
            with open(encoding_file, 'wb') as f:
                pickle.dump(self._known_encodings[name], f)
        except Exception as e:
            print(f"[FACE] Error saving encodings for {name}: {e}")

    def _get_face_recognition(self):
        """Lazy load face_recognition library."""
        if self._face_recognition is None:
            try:
                import face_recognition
                self._face_recognition = face_recognition
            except ImportError:
                raise ImportError(
                    "Face recognition requires face_recognition library. "
                    "Install with: pip install face_recognition\n"
                    "Note: Also requires dlib and cmake"
                )
        return self._face_recognition

    def _get_cv2(self):
        """Lazy load OpenCV."""
        if self._cv2 is None:
            try:
                import cv2
                self._cv2 = cv2
            except ImportError:
                raise ImportError(
                    "Face recognition requires OpenCV. "
                    "Install with: pip install opencv-python"
                )
        return self._cv2

    def enroll_face(self, name: str, image_path: str,
                    relationship: str = None,
                    description: str = None) -> Dict[str, Any]:
        """
        Enroll a new face or add samples to existing face.

        Args:
            name: Person's name
            image_path: Path to image containing their face
            relationship: Optional relationship description
            description: Optional description of the person

        Returns:
            Result dict with success status and encoding count
        """
        fr = self._get_face_recognition()

        try:
            # Load and process image
            image = fr.load_image_file(image_path)
            face_locations = fr.face_locations(image)

            if not face_locations:
                return {
                    "success": False,
                    "error": "No face detected in the image",
                    "name": name
                }

            if len(face_locations) > 1:
                return {
                    "success": False,
                    "error": f"Multiple faces ({len(face_locations)}) detected. Please use an image with only one face.",
                    "name": name
                }

            # Get face encoding
            face_encodings = fr.face_encodings(image, face_locations)
            if not face_encodings:
                return {
                    "success": False,
                    "error": "Could not encode face. Try a different image.",
                    "name": name
                }

            encoding = face_encodings[0]

            # Store encoding
            if name not in self._known_encodings:
                self._known_encodings[name] = []
                self._known_metadata[name] = {
                    'relationship': relationship,
                    'description': description,
                    'last_seen': None,
                    'times_seen': 0
                }

            self._known_encodings[name].append(encoding)
            self._save_encodings(name)

            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO known_faces
                (name, relationship, description, num_encodings, times_seen)
                VALUES (?, ?, ?, ?,
                    COALESCE((SELECT times_seen FROM known_faces WHERE name = ?), 0))
            """, (name, relationship, description,
                  len(self._known_encodings[name]), name))

            conn.commit()
            conn.close()

            # Update metadata
            if relationship:
                self._known_metadata[name]['relationship'] = relationship
            if description:
                self._known_metadata[name]['description'] = description

            return {
                "success": True,
                "name": name,
                "num_encodings": len(self._known_encodings[name]),
                "message": f"Enrolled {name} with {len(self._known_encodings[name])} face sample(s)"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "name": name
            }

    def recognize_faces(self, image_path: str,
                        update_seen: bool = True) -> List[FaceMatch]:
        """
        Recognize faces in an image.

        Args:
            image_path: Path to image to analyze
            update_seen: Whether to update last_seen timestamps

        Returns:
            List of FaceMatch objects for recognized faces
        """
        fr = self._get_face_recognition()
        matches = []

        try:
            # Load and process image
            image = fr.load_image_file(image_path)
            face_locations = fr.face_locations(image)

            if not face_locations:
                return []

            face_encodings = fr.face_encodings(image, face_locations)

            for i, encoding in enumerate(face_encodings):
                location = face_locations[i]
                best_match = None
                best_distance = float('inf')

                # Compare against known faces
                for name, known_encodings in self._known_encodings.items():
                    if not known_encodings:
                        continue

                    # Calculate distances to all encodings for this person
                    distances = fr.face_distance(known_encodings, encoding)
                    min_distance = np.min(distances)

                    if min_distance < best_distance and min_distance < FACE_MATCH_THRESHOLD:
                        best_distance = min_distance
                        best_match = name

                if best_match:
                    metadata = self._known_metadata.get(best_match, {})
                    confidence = 1.0 - best_distance  # Convert distance to confidence

                    match = FaceMatch(
                        name=best_match,
                        confidence=confidence,
                        distance=best_distance,
                        location=location,
                        relationship=metadata.get('relationship'),
                        last_seen=metadata.get('last_seen'),
                        times_seen=metadata.get('times_seen', 0) + 1
                    )
                    matches.append(match)

                    if update_seen:
                        self._update_seen(best_match, image_path)

            return matches

        except Exception as e:
            print(f"[FACE] Recognition error: {e}")
            return []

    def _update_seen(self, name: str, image_path: str):
        """Update last seen timestamp for a person."""
        now = datetime.datetime.now().isoformat()

        # Update metadata
        if name in self._known_metadata:
            self._known_metadata[name]['last_seen'] = now
            self._known_metadata[name]['times_seen'] = \
                self._known_metadata[name].get('times_seen', 0) + 1

        # Update database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE known_faces
            SET last_seen = ?, times_seen = times_seen + 1
            WHERE name = ?
        """, (now, name))

        # Log sighting
        image_hash = hashlib.md5(image_path.encode()).hexdigest()[:16]
        cursor.execute("""
            INSERT INTO face_sightings (name, confidence, image_hash)
            VALUES (?, ?, ?)
        """, (name, 1.0, image_hash))

        conn.commit()
        conn.close()

    def get_known_faces(self) -> List[Dict[str, Any]]:
        """Get list of all known faces."""
        faces = []
        for name, metadata in self._known_metadata.items():
            faces.append({
                "name": name,
                "relationship": metadata.get('relationship'),
                "description": metadata.get('description'),
                "num_encodings": len(self._known_encodings.get(name, [])),
                "last_seen": metadata.get('last_seen'),
                "times_seen": metadata.get('times_seen', 0)
            })
        return sorted(faces, key=lambda x: x['name'])

    def remove_face(self, name: str) -> bool:
        """Remove a known face."""
        if name not in self._known_encodings:
            return False

        # Remove from memory
        del self._known_encodings[name]
        if name in self._known_metadata:
            del self._known_metadata[name]

        # Remove encoding file
        encoding_file = os.path.join(self.encodings_dir, f"{name}.pkl")
        if os.path.exists(encoding_file):
            os.remove(encoding_file)

        # Remove from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM known_faces WHERE name = ?", (name,))
        cursor.execute("DELETE FROM face_sightings WHERE name = ?", (name,))
        conn.commit()
        conn.close()

        return True


# ================================================================================
# PLACE RECOGNITION ENGINE
# ================================================================================

class PlaceRecognitionEngine:
    """
    Handles place/location recognition using feature matching.

    Features:
    - Store reference images for known places
    - Use ORB features for matching
    - Track confidence and viewing history
    """

    def __init__(self, db_path: str = RECOGNITION_DB,
                 features_dir: str = PLACE_FEATURES_DIR):
        self.db_path = db_path
        self.features_dir = features_dir
        self._cv2 = None
        self._orb = None
        self._bf = None

        self._known_places: Dict[str, Dict] = {}

        self._init_directories()
        self._init_db()
        self._load_places()

    def _init_directories(self):
        """Create necessary directories."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.features_dir, exist_ok=True)

    def _init_db(self):
        """Initialize the places database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS known_places (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                typical_contents TEXT,
                typical_lighting TEXT,
                num_samples INTEGER DEFAULT 0,
                last_seen TIMESTAMP,
                times_seen INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def _load_places(self):
        """Load known places from database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        rows = cursor.execute("SELECT * FROM known_places").fetchall()
        conn.close()

        for row in rows:
            name = row['name']
            self._known_places[name] = {
                'description': row['description'],
                'typical_contents': row['typical_contents'],
                'typical_lighting': row['typical_lighting'],
                'num_samples': row['num_samples'],
                'last_seen': row['last_seen'],
                'times_seen': row['times_seen'],
                'features': self._load_features(name)
            }

    def _load_features(self, name: str) -> List[Any]:
        """Load stored features for a place."""
        features_file = os.path.join(self.features_dir, f"{name}.pkl")
        if os.path.exists(features_file):
            try:
                with open(features_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"[PLACE] Error loading features for {name}: {e}")
        return []

    def _save_features(self, name: str, features: List[Any]):
        """Save features to disk."""
        features_file = os.path.join(self.features_dir, f"{name}.pkl")
        try:
            with open(features_file, 'wb') as f:
                pickle.dump(features, f)
        except Exception as e:
            print(f"[PLACE] Error saving features for {name}: {e}")

    def _get_cv2(self):
        """Lazy load OpenCV."""
        if self._cv2 is None:
            try:
                import cv2
                self._cv2 = cv2
                self._orb = cv2.ORB_create(nfeatures=1000)
                self._bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            except ImportError:
                raise ImportError(
                    "Place recognition requires OpenCV. "
                    "Install with: pip install opencv-python"
                )
        return self._cv2

    def enroll_place(self, name: str, image_path: str,
                     description: str = None,
                     typical_contents: str = None,
                     typical_lighting: str = None) -> Dict[str, Any]:
        """
        Enroll a new place or add samples.

        Args:
            name: Place name
            image_path: Path to reference image
            description: Optional description
            typical_contents: What's typically in this place
            typical_lighting: Typical lighting conditions

        Returns:
            Result dict
        """
        cv2 = self._get_cv2()

        try:
            # Load and process image
            image = cv2.imread(image_path)
            if image is None:
                return {
                    "success": False,
                    "error": "Could not load image",
                    "name": name
                }

            # Convert to grayscale and extract features
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            keypoints, descriptors = self._orb.detectAndCompute(gray, None)

            if descriptors is None or len(keypoints) < 10:
                return {
                    "success": False,
                    "error": "Not enough features detected. Try a more detailed image.",
                    "name": name
                }

            # Store features
            if name not in self._known_places:
                self._known_places[name] = {
                    'description': description,
                    'typical_contents': typical_contents,
                    'typical_lighting': typical_lighting,
                    'num_samples': 0,
                    'last_seen': None,
                    'times_seen': 0,
                    'features': []
                }

            # Add features (store descriptors as list)
            self._known_places[name]['features'].append(descriptors)
            self._known_places[name]['num_samples'] += 1

            if description:
                self._known_places[name]['description'] = description
            if typical_contents:
                self._known_places[name]['typical_contents'] = typical_contents
            if typical_lighting:
                self._known_places[name]['typical_lighting'] = typical_lighting

            # Save features
            self._save_features(name, self._known_places[name]['features'])

            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO known_places
                (name, description, typical_contents, typical_lighting, num_samples, times_seen)
                VALUES (?, ?, ?, ?, ?,
                    COALESCE((SELECT times_seen FROM known_places WHERE name = ?), 0))
            """, (name, description, typical_contents, typical_lighting,
                  self._known_places[name]['num_samples'], name))

            conn.commit()
            conn.close()

            return {
                "success": True,
                "name": name,
                "num_samples": self._known_places[name]['num_samples'],
                "features_detected": len(keypoints),
                "message": f"Enrolled {name} with {self._known_places[name]['num_samples']} sample(s)"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "name": name
            }

    def recognize_place(self, image_path: str,
                        update_seen: bool = True) -> Optional[PlaceMatch]:
        """
        Recognize a place in an image.

        Args:
            image_path: Path to image to analyze
            update_seen: Whether to update last_seen timestamps

        Returns:
            PlaceMatch if recognized, None otherwise
        """
        cv2 = self._get_cv2()

        try:
            # Load and process image
            image = cv2.imread(image_path)
            if image is None:
                return None

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            keypoints, descriptors = self._orb.detectAndCompute(gray, None)

            if descriptors is None:
                return None

            best_match = None
            best_score = 0.0
            best_count = 0

            # Compare against known places
            for name, place_data in self._known_places.items():
                features_list = place_data.get('features', [])
                if not features_list:
                    continue

                total_matches = 0
                samples_matched = 0

                for stored_descriptors in features_list:
                    try:
                        matches = self._bf.match(descriptors, stored_descriptors)
                        # Good matches (distance < 50)
                        good_matches = [m for m in matches if m.distance < 50]
                        total_matches += len(good_matches)
                        if len(good_matches) > 10:
                            samples_matched += 1
                    except Exception:
                        continue

                if samples_matched > 0:
                    # Calculate confidence based on matches
                    avg_matches = total_matches / len(features_list)
                    confidence = min(1.0, avg_matches / 100)

                    if confidence > best_score and confidence > PLACE_MATCH_THRESHOLD:
                        best_score = confidence
                        best_count = total_matches
                        best_match = name

            if best_match:
                place_data = self._known_places[best_match]

                match = PlaceMatch(
                    name=best_match,
                    confidence=best_score,
                    match_count=best_count,
                    description=place_data.get('description'),
                    typical_contents=place_data.get('typical_contents'),
                    last_seen=place_data.get('last_seen'),
                    times_seen=place_data.get('times_seen', 0) + 1
                )

                if update_seen:
                    self._update_seen(best_match)

                return match

            return None

        except Exception as e:
            print(f"[PLACE] Recognition error: {e}")
            return None

    def _update_seen(self, name: str):
        """Update last seen timestamp for a place."""
        now = datetime.datetime.now().isoformat()

        if name in self._known_places:
            self._known_places[name]['last_seen'] = now
            self._known_places[name]['times_seen'] = \
                self._known_places[name].get('times_seen', 0) + 1

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE known_places
            SET last_seen = ?, times_seen = times_seen + 1
            WHERE name = ?
        """, (now, name))

        conn.commit()
        conn.close()

    def get_known_places(self) -> List[Dict[str, Any]]:
        """Get list of all known places."""
        places = []
        for name, data in self._known_places.items():
            places.append({
                "name": name,
                "description": data.get('description'),
                "typical_contents": data.get('typical_contents'),
                "num_samples": data.get('num_samples', 0),
                "last_seen": data.get('last_seen'),
                "times_seen": data.get('times_seen', 0)
            })
        return sorted(places, key=lambda x: x['name'])


# ================================================================================
# UNIFIED RECOGNITION MANAGER
# ================================================================================

class RecognitionManager:
    """
    Unified manager for face and place recognition.

    Provides high-level API for all recognition tasks.
    """

    def __init__(self):
        self.face_engine = FaceRecognitionEngine()
        self.place_engine = PlaceRecognitionEngine()

    def analyze_image(self, image_path: str) -> RecognitionResult:
        """
        Perform complete recognition analysis on an image.

        Returns faces recognized, place recognized, and unknown face count.
        """
        import time
        start_time = time.time()

        result = RecognitionResult()

        # Calculate image hash
        try:
            with open(image_path, 'rb') as f:
                result.image_hash = hashlib.md5(f.read()).hexdigest()[:16]
        except Exception:
            pass

        # Recognize faces
        try:
            faces = self.face_engine.recognize_faces(image_path)
            result.faces = faces
        except ImportError as e:
            print(f"[RECOGNITION] Face recognition not available: {e}")
        except Exception as e:
            print(f"[RECOGNITION] Face recognition error: {e}")

        # Count unknown faces
        try:
            import face_recognition
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            result.unknown_faces = len(face_locations) - len(result.faces)
        except Exception:
            pass

        # Recognize place
        try:
            place = self.place_engine.recognize_place(image_path)
            result.place = place
        except ImportError as e:
            print(f"[RECOGNITION] Place recognition not available: {e}")
        except Exception as e:
            print(f"[RECOGNITION] Place recognition error: {e}")

        result.processing_time = time.time() - start_time

        return result

    def enroll_person(self, name: str, image_path: str,
                      relationship: str = None,
                      description: str = None) -> Dict[str, Any]:
        """Enroll a new person for face recognition."""
        return self.face_engine.enroll_face(
            name, image_path, relationship, description
        )

    def enroll_place(self, name: str, image_path: str,
                     description: str = None,
                     typical_contents: str = None) -> Dict[str, Any]:
        """Enroll a new place for recognition."""
        return self.place_engine.enroll_place(
            name, image_path, description, typical_contents
        )

    def get_known_people(self) -> List[Dict[str, Any]]:
        """Get list of all known people."""
        return self.face_engine.get_known_faces()

    def get_known_places(self) -> List[Dict[str, Any]]:
        """Get list of all known places."""
        return self.place_engine.get_known_places()

    def forget_person(self, name: str) -> bool:
        """Remove a person from recognition."""
        return self.face_engine.remove_face(name)


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_recognition_manager: Optional[RecognitionManager] = None


def get_recognition_manager() -> RecognitionManager:
    """Get or create the global recognition manager."""
    global _recognition_manager
    if _recognition_manager is None:
        _recognition_manager = RecognitionManager()
    return _recognition_manager


# ================================================================================
# EXECUTOR FUNCTIONS
# ================================================================================

def recognize_image(image_path: str) -> str:
    """
    Recognize faces and places in an image.

    Returns JSON result.
    """
    manager = get_recognition_manager()
    result = manager.analyze_image(image_path)

    return json.dumps({
        "success": True,
        **result.to_dict()
    })


def enroll_person(name: str, image_path: str,
                  relationship: str = None,
                  description: str = None) -> str:
    """Enroll a person for face recognition."""
    manager = get_recognition_manager()
    result = manager.enroll_person(name, image_path, relationship, description)
    return json.dumps(result)


def enroll_place(name: str, image_path: str,
                 description: str = None,
                 typical_contents: str = None) -> str:
    """Enroll a place for recognition."""
    manager = get_recognition_manager()
    result = manager.enroll_place(name, image_path, description, typical_contents)
    return json.dumps(result)


def list_known_people() -> str:
    """List all known people."""
    manager = get_recognition_manager()
    people = manager.get_known_people()
    return json.dumps({
        "success": True,
        "count": len(people),
        "people": people
    })


def list_known_places() -> str:
    """List all known places."""
    manager = get_recognition_manager()
    places = manager.get_known_places()
    return json.dumps({
        "success": True,
        "count": len(places),
        "places": places
    })


def forget_person(name: str) -> str:
    """Remove a person from recognition."""
    manager = get_recognition_manager()
    if manager.forget_person(name):
        return json.dumps({
            "success": True,
            "message": f"Removed {name} from face recognition"
        })
    else:
        return json.dumps({
            "success": False,
            "error": f"Person not found: {name}"
        })


def execute_recognition_command(action: str, params: Dict[str, Any] = None) -> str:
    """
    Execute a recognition command.

    Actions:
    - recognize: Analyze an image for faces and places
    - enroll_person: Add a person for recognition
    - enroll_place: Add a place for recognition
    - list_people: List known people
    - list_places: List known places
    - forget_person: Remove a person
    """
    if params is None:
        params = {}

    action_lower = action.lower().strip()

    if action_lower in ['recognize', 'analyze', 'identify']:
        return recognize_image(params.get('image_path', ''))

    elif action_lower in ['enroll_person', 'learn_person', 'add_person', 'remember_person']:
        return enroll_person(
            name=params.get('name', ''),
            image_path=params.get('image_path', ''),
            relationship=params.get('relationship'),
            description=params.get('description')
        )

    elif action_lower in ['enroll_place', 'learn_place', 'add_place', 'remember_place']:
        return enroll_place(
            name=params.get('name', ''),
            image_path=params.get('image_path', ''),
            description=params.get('description'),
            typical_contents=params.get('typical_contents')
        )

    elif action_lower in ['list_people', 'known_people', 'who_do_i_know']:
        return list_known_people()

    elif action_lower in ['list_places', 'known_places', 'where_do_i_know']:
        return list_known_places()

    elif action_lower in ['forget_person', 'remove_person', 'delete_person']:
        return forget_person(params.get('name', ''))

    else:
        return json.dumps({
            "success": False,
            "error": f"Unknown recognition action: {action}",
            "available_actions": [
                "recognize", "enroll_person", "enroll_place",
                "list_people", "list_places", "forget_person"
            ]
        })


__all__ = [
    'FaceRecognitionEngine',
    'PlaceRecognitionEngine',
    'RecognitionManager',
    'RecognitionResult',
    'FaceMatch',
    'PlaceMatch',
    'get_recognition_manager',
    'recognize_image',
    'enroll_person',
    'enroll_place',
    'list_known_people',
    'list_known_places',
    'forget_person',
    'execute_recognition_command',
]
