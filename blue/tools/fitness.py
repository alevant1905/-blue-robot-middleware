"""
Blue Robot Workout & Fitness Tracker
=====================================
Track workouts, exercises, nutrition, and fitness progress with comprehensive analytics.
"""

# Future imports
from __future__ import annotations

# Standard library
import datetime
import json
import os
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ================================================================================
# CONFIGURATION
# ================================================================================

FITNESS_DB = os.environ.get("BLUE_FITNESS_DB", os.path.join("data", "fitness.db"))


class WorkoutType(Enum):
    """Types of workouts"""
    STRENGTH = "strength"
    CARDIO = "cardio"
    FLEXIBILITY = "flexibility"
    SPORTS = "sports"
    HIIT = "hiit"
    YOGA = "yoga"
    PILATES = "pilates"
    SWIMMING = "swimming"
    CYCLING = "cycling"
    RUNNING = "running"
    WALKING = "walking"
    OTHER = "other"


class ExerciseCategory(Enum):
    """Exercise categories"""
    CHEST = "chest"
    BACK = "back"
    LEGS = "legs"
    SHOULDERS = "shoulders"
    ARMS = "arms"
    CORE = "core"
    CARDIO = "cardio"
    FULL_BODY = "full_body"


class IntensityLevel(Enum):
    """Intensity levels"""
    LOW = 1
    MODERATE = 2
    HIGH = 3
    VERY_HIGH = 4


@dataclass
class Workout:
    """Represents a workout session"""
    id: str
    date: float
    workout_type: WorkoutType
    title: str
    duration_minutes: int
    intensity: IntensityLevel
    calories_burned: Optional[int]
    notes: str
    created_at: float
    exercises: List[str]  # List of exercise IDs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "date": datetime.datetime.fromtimestamp(self.date).isoformat(),
            "date_human": datetime.datetime.fromtimestamp(self.date).strftime("%b %d, %Y"),
            "workout_type": self.workout_type.value,
            "title": self.title,
            "duration_minutes": self.duration_minutes,
            "intensity": self.intensity.value,
            "intensity_name": self.intensity.name.replace('_', ' ').title(),
            "calories_burned": self.calories_burned,
            "notes": self.notes,
            "exercise_count": len(self.exercises),
            "created_at": datetime.datetime.fromtimestamp(self.created_at).isoformat()
        }


@dataclass
class Exercise:
    """Represents an exercise within a workout"""
    id: str
    workout_id: str
    name: str
    category: ExerciseCategory
    sets: int
    reps: int
    weight: Optional[float]  # in kg or lbs
    duration_seconds: Optional[int]
    distance: Optional[float]  # in km or miles
    notes: str
    created_at: float

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "workout_id": self.workout_id,
            "name": self.name,
            "category": self.category.value,
            "sets": self.sets,
            "reps": self.reps,
            "notes": self.notes,
            "created_at": datetime.datetime.fromtimestamp(self.created_at).isoformat()
        }
        if self.weight:
            result["weight"] = self.weight
        if self.duration_seconds:
            result["duration_seconds"] = self.duration_seconds
            result["duration_minutes"] = round(self.duration_seconds / 60, 2)
        if self.distance:
            result["distance"] = self.distance
        return result


@dataclass
class BodyMeasurement:
    """Represents body measurements"""
    id: str
    date: float
    weight: Optional[float]
    body_fat_percent: Optional[float]
    muscle_mass: Optional[float]
    measurements: Dict[str, float]  # e.g., chest, waist, arms, etc.
    notes: str
    created_at: float

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "date": datetime.datetime.fromtimestamp(self.date).isoformat(),
            "date_human": datetime.datetime.fromtimestamp(self.date).strftime("%b %d, %Y"),
            "measurements": self.measurements,
            "notes": self.notes,
            "created_at": datetime.datetime.fromtimestamp(self.created_at).isoformat()
        }
        if self.weight:
            result["weight"] = self.weight
        if self.body_fat_percent:
            result["body_fat_percent"] = self.body_fat_percent
        if self.muscle_mass:
            result["muscle_mass"] = self.muscle_mass
        return result


@dataclass
class WorkoutPlan:
    """Represents a workout plan template"""
    id: str
    name: str
    description: str
    workout_type: WorkoutType
    duration_weeks: int
    days_per_week: int
    created_at: float
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "workout_type": self.workout_type.value,
            "duration_weeks": self.duration_weeks,
            "days_per_week": self.days_per_week,
            "active": self.active,
            "created_at": datetime.datetime.fromtimestamp(self.created_at).isoformat()
        }


# ================================================================================
# FITNESS MANAGER
# ================================================================================

class FitnessManager:
    """Manages workouts, exercises, and fitness tracking"""

    def __init__(self, db_path: str = FITNESS_DB):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database tables"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Workouts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workouts (
                id TEXT PRIMARY KEY,
                date REAL NOT NULL,
                workout_type TEXT NOT NULL,
                title TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                intensity INTEGER NOT NULL,
                calories_burned INTEGER,
                notes TEXT,
                created_at REAL NOT NULL
            )
        """)

        # Exercises table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exercises (
                id TEXT PRIMARY KEY,
                workout_id TEXT NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                sets INTEGER NOT NULL,
                reps INTEGER NOT NULL,
                weight REAL,
                duration_seconds INTEGER,
                distance REAL,
                notes TEXT,
                created_at REAL NOT NULL,
                FOREIGN KEY (workout_id) REFERENCES workouts (id)
            )
        """)

        # Body measurements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS body_measurements (
                id TEXT PRIMARY KEY,
                date REAL NOT NULL,
                weight REAL,
                body_fat_percent REAL,
                muscle_mass REAL,
                measurements TEXT,
                notes TEXT,
                created_at REAL NOT NULL
            )
        """)

        # Workout plans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workout_plans (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                workout_type TEXT NOT NULL,
                duration_weeks INTEGER NOT NULL,
                days_per_week INTEGER NOT NULL,
                created_at REAL NOT NULL,
                active INTEGER DEFAULT 1
            )
        """)

        # Personal records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personal_records (
                id TEXT PRIMARY KEY,
                exercise_name TEXT NOT NULL,
                record_type TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                achieved_date REAL NOT NULL,
                notes TEXT,
                created_at REAL NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    # ==================== WORKOUTS ====================

    def create_workout(self, title: str, workout_type: str, duration_minutes: int,
                      intensity: int, date: float = None, calories_burned: int = None,
                      notes: str = "") -> Workout:
        """Create a new workout"""
        workout_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().timestamp()
        workout_date = date if date else now

        try:
            type_enum = WorkoutType(workout_type.lower())
        except ValueError:
            type_enum = WorkoutType.OTHER

        workout = Workout(
            id=workout_id,
            date=workout_date,
            workout_type=type_enum,
            title=title,
            duration_minutes=duration_minutes,
            intensity=IntensityLevel(intensity),
            calories_burned=calories_burned,
            notes=notes,
            created_at=now,
            exercises=[]
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO workouts (id, date, workout_type, title, duration_minutes, intensity, calories_burned, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (workout.id, workout.date, workout.workout_type.value, workout.title,
              workout.duration_minutes, workout.intensity.value, workout.calories_burned,
              workout.notes, workout.created_at))
        conn.commit()
        conn.close()

        return workout

    def get_workout(self, workout_id: str) -> Optional[Workout]:
        """Get a workout by ID"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        # Get exercises for this workout
        cursor.execute("SELECT id FROM exercises WHERE workout_id = ?", (workout_id,))
        exercise_ids = [r[0] for r in cursor.fetchall()]
        conn.close()

        return Workout(
            id=row[0], date=row[1], workout_type=WorkoutType(row[2]),
            title=row[3], duration_minutes=row[4], intensity=IntensityLevel(row[5]),
            calories_burned=row[6], notes=row[7] or "", created_at=row[8],
            exercises=exercise_ids
        )

    def get_workouts(self, start_date: float = None, end_date: float = None,
                    workout_type: str = None, limit: int = 30) -> List[Workout]:
        """Get workouts with optional filtering"""
        conn = self._get_conn()
        cursor = conn.cursor()

        sql = "SELECT * FROM workouts WHERE 1=1"
        params = []

        if start_date:
            sql += " AND date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND date <= ?"
            params.append(end_date)
        if workout_type:
            sql += " AND workout_type = ?"
            params.append(workout_type.lower())

        sql += " ORDER BY date DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        workouts = []
        for row in rows:
            cursor.execute("SELECT id FROM exercises WHERE workout_id = ?", (row[0],))
            exercise_ids = [r[0] for r in cursor.fetchall()]

            workouts.append(Workout(
                id=row[0], date=row[1], workout_type=WorkoutType(row[2]),
                title=row[3], duration_minutes=row[4], intensity=IntensityLevel(row[5]),
                calories_burned=row[6], notes=row[7] or "", created_at=row[8],
                exercises=exercise_ids
            ))

        conn.close()
        return workouts

    def get_workout_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get workout statistics for period"""
        start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).timestamp()
        workouts = self.get_workouts(start_date=start_date, limit=1000)

        if not workouts:
            return {
                "total_workouts": 0,
                "total_duration_minutes": 0,
                "total_calories": 0,
                "average_duration": 0,
                "workouts_per_week": 0
            }

        total_duration = sum(w.duration_minutes for w in workouts)
        total_calories = sum(w.calories_burned or 0 for w in workouts)
        avg_duration = total_duration / len(workouts)
        workouts_per_week = len(workouts) / (days / 7)

        # Workout type distribution
        type_counts = {}
        for workout in workouts:
            type_name = workout.workout_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        return {
            "total_workouts": len(workouts),
            "total_duration_minutes": total_duration,
            "total_calories": total_calories,
            "average_duration": round(avg_duration, 2),
            "workouts_per_week": round(workouts_per_week, 2),
            "workout_type_distribution": type_counts,
            "period_days": days
        }

    # ==================== EXERCISES ====================

    def add_exercise(self, workout_id: str, name: str, category: str,
                    sets: int, reps: int, weight: float = None,
                    duration_seconds: int = None, distance: float = None,
                    notes: str = "") -> Exercise:
        """Add an exercise to a workout"""
        exercise_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().timestamp()

        try:
            category_enum = ExerciseCategory(category.lower())
        except ValueError:
            category_enum = ExerciseCategory.FULL_BODY

        exercise = Exercise(
            id=exercise_id,
            workout_id=workout_id,
            name=name,
            category=category_enum,
            sets=sets,
            reps=reps,
            weight=weight,
            duration_seconds=duration_seconds,
            distance=distance,
            notes=notes,
            created_at=now
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO exercises (id, workout_id, name, category, sets, reps, weight, duration_seconds, distance, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (exercise.id, exercise.workout_id, exercise.name, exercise.category.value,
              exercise.sets, exercise.reps, exercise.weight, exercise.duration_seconds,
              exercise.distance, exercise.notes, exercise.created_at))
        conn.commit()
        conn.close()

        return exercise

    def get_exercises(self, workout_id: str) -> List[Exercise]:
        """Get all exercises for a workout"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM exercises WHERE workout_id = ? ORDER BY created_at ASC", (workout_id,))
        rows = cursor.fetchall()
        conn.close()

        return [
            Exercise(
                id=row[0], workout_id=row[1], name=row[2],
                category=ExerciseCategory(row[3]), sets=row[4], reps=row[5],
                weight=row[6], duration_seconds=row[7], distance=row[8],
                notes=row[9] or "", created_at=row[10]
            )
            for row in rows
        ]

    def get_exercise_history(self, exercise_name: str, limit: int = 10) -> List[Exercise]:
        """Get history for a specific exercise"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.* FROM exercises e
            JOIN workouts w ON e.workout_id = w.id
            WHERE e.name LIKE ?
            ORDER BY w.date DESC
            LIMIT ?
        """, (f"%{exercise_name}%", limit))
        rows = cursor.fetchall()
        conn.close()

        return [
            Exercise(
                id=row[0], workout_id=row[1], name=row[2],
                category=ExerciseCategory(row[3]), sets=row[4], reps=row[5],
                weight=row[6], duration_seconds=row[7], distance=row[8],
                notes=row[9] or "", created_at=row[10]
            )
            for row in rows
        ]

    # ==================== BODY MEASUREMENTS ====================

    def add_measurement(self, weight: float = None, body_fat_percent: float = None,
                       muscle_mass: float = None, measurements: Dict[str, float] = None,
                       date: float = None, notes: str = "") -> BodyMeasurement:
        """Add body measurements"""
        measurement_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().timestamp()
        measurement_date = date if date else now

        measurement = BodyMeasurement(
            id=measurement_id,
            date=measurement_date,
            weight=weight,
            body_fat_percent=body_fat_percent,
            muscle_mass=muscle_mass,
            measurements=measurements or {},
            notes=notes,
            created_at=now
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO body_measurements (id, date, weight, body_fat_percent, muscle_mass, measurements, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (measurement.id, measurement.date, measurement.weight, measurement.body_fat_percent,
              measurement.muscle_mass, json.dumps(measurement.measurements),
              measurement.notes, measurement.created_at))
        conn.commit()
        conn.close()

        return measurement

    def get_measurements(self, limit: int = 30) -> List[BodyMeasurement]:
        """Get recent body measurements"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM body_measurements ORDER BY date DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()

        return [
            BodyMeasurement(
                id=row[0], date=row[1], weight=row[2],
                body_fat_percent=row[3], muscle_mass=row[4],
                measurements=json.loads(row[5] or "{}"),
                notes=row[6] or "", created_at=row[7]
            )
            for row in rows
        ]

    def get_weight_progress(self, days: int = 90) -> List[Tuple[float, float]]:
        """Get weight progress over time"""
        start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).timestamp()

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, weight FROM body_measurements
            WHERE date >= ? AND weight IS NOT NULL
            ORDER BY date ASC
        """, (start_date,))
        rows = cursor.fetchall()
        conn.close()

        return [(row[0], row[1]) for row in rows]


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_fitness_manager: Optional[FitnessManager] = None


def get_fitness_manager() -> FitnessManager:
    """Get or create singleton fitness manager instance"""
    global _fitness_manager
    if _fitness_manager is None:
        _fitness_manager = FitnessManager()
    return _fitness_manager


# ================================================================================
# COMMAND FUNCTIONS
# ================================================================================

def log_workout_cmd(title: str, workout_type: str, duration_minutes: int,
                   intensity: int, calories: int = None) -> str:
    """Log a workout"""
    manager = get_fitness_manager()

    workout = manager.create_workout(
        title=title,
        workout_type=workout_type,
        duration_minutes=duration_minutes,
        intensity=intensity,
        calories_burned=calories
    )

    return json.dumps({
        "status": "success",
        "message": f"Workout '{title}' logged ({duration_minutes} minutes)",
        "workout": workout.to_dict()
    })


def add_exercise_to_workout_cmd(workout_id: str, name: str, category: str,
                                sets: int, reps: int, weight: float = None) -> str:
    """Add an exercise to a workout"""
    manager = get_fitness_manager()

    exercise = manager.add_exercise(
        workout_id=workout_id,
        name=name,
        category=category,
        sets=sets,
        reps=reps,
        weight=weight
    )

    return json.dumps({
        "status": "success",
        "message": f"Exercise '{name}' added: {sets}x{reps}" + (f" @ {weight}kg" if weight else ""),
        "exercise": exercise.to_dict()
    })


def get_workout_history_cmd(days: int = 7) -> str:
    """Get recent workout history"""
    manager = get_fitness_manager()

    start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).timestamp()
    workouts = manager.get_workouts(start_date=start_date)

    return json.dumps({
        "status": "success",
        "count": len(workouts),
        "workouts": [w.to_dict() for w in workouts]
    })


def get_workout_stats_cmd(days: int = 30) -> str:
    """Get workout statistics"""
    manager = get_fitness_manager()

    stats = manager.get_workout_stats(days)

    return json.dumps({
        "status": "success",
        "stats": stats
    })


def log_body_measurement_cmd(weight: float = None, body_fat: float = None,
                            muscle_mass: float = None) -> str:
    """Log body measurements"""
    manager = get_fitness_manager()

    measurement = manager.add_measurement(
        weight=weight,
        body_fat_percent=body_fat,
        muscle_mass=muscle_mass
    )

    return json.dumps({
        "status": "success",
        "message": "Body measurements logged",
        "measurement": measurement.to_dict()
    })


def get_weight_progress_cmd(days: int = 90) -> str:
    """Get weight progress"""
    manager = get_fitness_manager()

    progress = manager.get_weight_progress(days)

    return json.dumps({
        "status": "success",
        "data_points": len(progress),
        "progress": [
            {
                "date": datetime.datetime.fromtimestamp(date).isoformat(),
                "weight": weight
            }
            for date, weight in progress
        ]
    })


def get_exercise_progress_cmd(exercise_name: str, limit: int = 10) -> str:
    """Get progress for a specific exercise"""
    manager = get_fitness_manager()

    history = manager.get_exercise_history(exercise_name, limit)

    return json.dumps({
        "status": "success",
        "exercise": exercise_name,
        "count": len(history),
        "history": [e.to_dict() for e in history]
    })


__all__ = [
    'FitnessManager',
    'Workout',
    'Exercise',
    'BodyMeasurement',
    'WorkoutPlan',
    'WorkoutType',
    'ExerciseCategory',
    'IntensityLevel',
    'get_fitness_manager',
    'log_workout_cmd',
    'add_exercise_to_workout_cmd',
    'get_workout_history_cmd',
    'get_workout_stats_cmd',
    'log_body_measurement_cmd',
    'get_weight_progress_cmd',
    'get_exercise_progress_cmd',
]
