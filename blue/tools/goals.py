"""
Blue Robot Goals & Projects Management
=======================================
Manage long-term goals, projects, milestones, and track progress toward achievements.
"""

import datetime
import json
import os
import sqlite3
import uuid
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

# ================================================================================
# CONFIGURATION
# ================================================================================

GOALS_DB = os.environ.get("BLUE_GOALS_DB", os.path.join("data", "goals.db"))


class GoalStatus(Enum):
    """Status of a goal"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class GoalCategory(Enum):
    """Category of goals"""
    CAREER = "career"
    EDUCATION = "education"
    HEALTH = "health"
    FINANCE = "finance"
    RELATIONSHIPS = "relationships"
    PERSONAL = "personal"
    CREATIVE = "creative"
    BUSINESS = "business"
    OTHER = "other"


class ProjectStatus(Enum):
    """Status of a project"""
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class MilestoneStatus(Enum):
    """Status of a milestone"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class Goal:
    """Represents a long-term goal"""
    id: str
    title: str
    description: str
    category: GoalCategory
    status: GoalStatus
    target_date: Optional[float]
    progress_percent: int
    created_at: float
    updated_at: float
    completed_at: Optional[float] = None
    tags: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "status": self.status.value,
            "progress_percent": self.progress_percent,
            "created_at": datetime.datetime.fromtimestamp(self.created_at).isoformat(),
            "updated_at": datetime.datetime.fromtimestamp(self.updated_at).isoformat(),
            "tags": self.tags or []
        }
        if self.target_date:
            result["target_date"] = datetime.datetime.fromtimestamp(self.target_date).isoformat()
            result["target_date_human"] = datetime.datetime.fromtimestamp(self.target_date).strftime("%b %d, %Y")
        if self.completed_at:
            result["completed_at"] = datetime.datetime.fromtimestamp(self.completed_at).isoformat()
        return result


@dataclass
class Project:
    """Represents a project with multiple tasks/milestones"""
    id: str
    name: str
    description: str
    status: ProjectStatus
    start_date: float
    end_date: Optional[float]
    progress_percent: int
    created_at: float
    updated_at: float
    completed_at: Optional[float] = None
    goal_id: Optional[str] = None  # Link to parent goal

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "start_date": datetime.datetime.fromtimestamp(self.start_date).isoformat(),
            "progress_percent": self.progress_percent,
            "created_at": datetime.datetime.fromtimestamp(self.created_at).isoformat(),
            "updated_at": datetime.datetime.fromtimestamp(self.updated_at).isoformat(),
            "goal_id": self.goal_id
        }
        if self.end_date:
            result["end_date"] = datetime.datetime.fromtimestamp(self.end_date).isoformat()
            result["end_date_human"] = datetime.datetime.fromtimestamp(self.end_date).strftime("%b %d, %Y")
        if self.completed_at:
            result["completed_at"] = datetime.datetime.fromtimestamp(self.completed_at).isoformat()
        return result


@dataclass
class Milestone:
    """Represents a milestone in a project or goal"""
    id: str
    project_id: str
    title: str
    description: str
    status: MilestoneStatus
    due_date: Optional[float]
    created_at: float
    updated_at: float
    completed_at: Optional[float] = None
    order: int = 0

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "order": self.order,
            "created_at": datetime.datetime.fromtimestamp(self.created_at).isoformat(),
            "updated_at": datetime.datetime.fromtimestamp(self.updated_at).isoformat()
        }
        if self.due_date:
            result["due_date"] = datetime.datetime.fromtimestamp(self.due_date).isoformat()
            result["due_date_human"] = datetime.datetime.fromtimestamp(self.due_date).strftime("%b %d, %Y")
        if self.completed_at:
            result["completed_at"] = datetime.datetime.fromtimestamp(self.completed_at).isoformat()
        return result


# ================================================================================
# GOALS MANAGER
# ================================================================================

class GoalsManager:
    """Manages goals, projects, and milestones"""

    def __init__(self, db_path: str = GOALS_DB):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database tables"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Goals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                status TEXT NOT NULL,
                target_date REAL,
                progress_percent INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                completed_at REAL,
                tags TEXT
            )
        """)

        # Projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                start_date REAL NOT NULL,
                end_date REAL,
                progress_percent INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                completed_at REAL,
                goal_id TEXT,
                FOREIGN KEY (goal_id) REFERENCES goals (id)
            )
        """)

        # Milestones table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS milestones (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                due_date REAL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                completed_at REAL,
                order_num INTEGER DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        """)

        # Progress log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS progress_logs (
                id TEXT PRIMARY KEY,
                goal_id TEXT,
                project_id TEXT,
                note TEXT NOT NULL,
                logged_at REAL NOT NULL,
                FOREIGN KEY (goal_id) REFERENCES goals (id),
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        """)

        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    # ==================== GOALS ====================

    def create_goal(self, title: str, description: str, category: str,
                   target_date: float = None, tags: List[str] = None) -> Goal:
        """Create a new goal"""
        goal_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().timestamp()

        try:
            category_enum = GoalCategory(category.lower())
        except ValueError:
            category_enum = GoalCategory.OTHER

        goal = Goal(
            id=goal_id,
            title=title,
            description=description,
            category=category_enum,
            status=GoalStatus.NOT_STARTED,
            target_date=target_date,
            progress_percent=0,
            created_at=now,
            updated_at=now,
            tags=tags or []
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO goals (id, title, description, category, status, target_date, progress_percent, created_at, updated_at, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (goal.id, goal.title, goal.description, goal.category.value,
              goal.status.value, goal.target_date, goal.progress_percent,
              goal.created_at, goal.updated_at, json.dumps(goal.tags)))
        conn.commit()
        conn.close()

        return goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM goals WHERE id = ?", (goal_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return Goal(
                id=row[0], title=row[1], description=row[2],
                category=GoalCategory(row[3]), status=GoalStatus(row[4]),
                target_date=row[5], progress_percent=row[6],
                created_at=row[7], updated_at=row[8],
                completed_at=row[9], tags=json.loads(row[10] or "[]")
            )
        return None

    def update_goal(self, goal_id: str, title: str = None, description: str = None,
                   status: str = None, progress_percent: int = None) -> Optional[Goal]:
        """Update a goal"""
        goal = self.get_goal(goal_id)
        if not goal:
            return None

        if title:
            goal.title = title
        if description:
            goal.description = description
        if status:
            try:
                goal.status = GoalStatus(status.lower())
                if goal.status == GoalStatus.COMPLETED:
                    goal.completed_at = datetime.datetime.now().timestamp()
                    goal.progress_percent = 100
            except ValueError:
                pass
        if progress_percent is not None:
            goal.progress_percent = max(0, min(100, progress_percent))

        goal.updated_at = datetime.datetime.now().timestamp()

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE goals SET title=?, description=?, status=?, progress_percent=?, updated_at=?, completed_at=?
            WHERE id=?
        """, (goal.title, goal.description, goal.status.value,
              goal.progress_percent, goal.updated_at, goal.completed_at, goal.id))
        conn.commit()
        conn.close()

        return goal

    def get_goals(self, status: str = None, category: str = None, limit: int = 50) -> List[Goal]:
        """Get goals with optional filtering"""
        conn = self._get_conn()
        cursor = conn.cursor()

        sql = "SELECT * FROM goals WHERE 1=1"
        params = []

        if status:
            sql += " AND status = ?"
            params.append(status.lower())
        if category:
            sql += " AND category = ?"
            params.append(category.lower())

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            Goal(
                id=row[0], title=row[1], description=row[2],
                category=GoalCategory(row[3]), status=GoalStatus(row[4]),
                target_date=row[5], progress_percent=row[6],
                created_at=row[7], updated_at=row[8],
                completed_at=row[9], tags=json.loads(row[10] or "[]")
            )
            for row in rows
        ]

    # ==================== PROJECTS ====================

    def create_project(self, name: str, description: str, start_date: float = None,
                      end_date: float = None, goal_id: str = None) -> Project:
        """Create a new project"""
        project_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().timestamp()
        project_start = start_date if start_date else now

        project = Project(
            id=project_id,
            name=name,
            description=description,
            status=ProjectStatus.PLANNING,
            start_date=project_start,
            end_date=end_date,
            progress_percent=0,
            created_at=now,
            updated_at=now,
            goal_id=goal_id
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO projects (id, name, description, status, start_date, end_date, progress_percent, created_at, updated_at, goal_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (project.id, project.name, project.description, project.status.value,
              project.start_date, project.end_date, project.progress_percent,
              project.created_at, project.updated_at, project.goal_id))
        conn.commit()
        conn.close()

        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return Project(
                id=row[0], name=row[1], description=row[2],
                status=ProjectStatus(row[3]), start_date=row[4],
                end_date=row[5], progress_percent=row[6],
                created_at=row[7], updated_at=row[8],
                completed_at=row[9], goal_id=row[10]
            )
        return None

    def update_project(self, project_id: str, status: str = None,
                      progress_percent: int = None) -> Optional[Project]:
        """Update a project"""
        project = self.get_project(project_id)
        if not project:
            return None

        if status:
            try:
                project.status = ProjectStatus(status.lower())
                if project.status == ProjectStatus.COMPLETED:
                    project.completed_at = datetime.datetime.now().timestamp()
                    project.progress_percent = 100
            except ValueError:
                pass
        if progress_percent is not None:
            project.progress_percent = max(0, min(100, progress_percent))

        project.updated_at = datetime.datetime.now().timestamp()

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE projects SET status=?, progress_percent=?, updated_at=?, completed_at=?
            WHERE id=?
        """, (project.status.value, project.progress_percent,
              project.updated_at, project.completed_at, project.id))
        conn.commit()
        conn.close()

        # Update progress of linked goal if exists
        if project.goal_id:
            self._update_goal_from_projects(project.goal_id)

        return project

    def get_projects(self, status: str = None, goal_id: str = None, limit: int = 50) -> List[Project]:
        """Get projects with optional filtering"""
        conn = self._get_conn()
        cursor = conn.cursor()

        sql = "SELECT * FROM projects WHERE 1=1"
        params = []

        if status:
            sql += " AND status = ?"
            params.append(status.lower())
        if goal_id:
            sql += " AND goal_id = ?"
            params.append(goal_id)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            Project(
                id=row[0], name=row[1], description=row[2],
                status=ProjectStatus(row[3]), start_date=row[4],
                end_date=row[5], progress_percent=row[6],
                created_at=row[7], updated_at=row[8],
                completed_at=row[9], goal_id=row[10]
            )
            for row in rows
        ]

    # ==================== MILESTONES ====================

    def create_milestone(self, project_id: str, title: str, description: str = "",
                        due_date: float = None, order: int = 0) -> Milestone:
        """Create a new milestone"""
        milestone_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().timestamp()

        milestone = Milestone(
            id=milestone_id,
            project_id=project_id,
            title=title,
            description=description,
            status=MilestoneStatus.PENDING,
            due_date=due_date,
            created_at=now,
            updated_at=now,
            order=order
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO milestones (id, project_id, title, description, status, due_date, created_at, updated_at, order_num)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (milestone.id, milestone.project_id, milestone.title, milestone.description,
              milestone.status.value, milestone.due_date, milestone.created_at,
              milestone.updated_at, milestone.order))
        conn.commit()
        conn.close()

        return milestone

    def complete_milestone(self, milestone_id: str) -> Optional[Milestone]:
        """Mark a milestone as completed"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM milestones WHERE id = ?", (milestone_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        now = datetime.datetime.now().timestamp()
        cursor.execute("""
            UPDATE milestones SET status = ?, completed_at = ?, updated_at = ?
            WHERE id = ?
        """, (MilestoneStatus.COMPLETED.value, now, now, milestone_id))
        conn.commit()
        conn.close()

        # Update project progress
        self._update_project_from_milestones(row[1])

        return self.get_milestone(milestone_id)

    def get_milestone(self, milestone_id: str) -> Optional[Milestone]:
        """Get a milestone by ID"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM milestones WHERE id = ?", (milestone_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return Milestone(
                id=row[0], project_id=row[1], title=row[2],
                description=row[3], status=MilestoneStatus(row[4]),
                due_date=row[5], created_at=row[6], updated_at=row[7],
                completed_at=row[8], order=row[9]
            )
        return None

    def get_milestones(self, project_id: str) -> List[Milestone]:
        """Get all milestones for a project"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM milestones WHERE project_id = ? ORDER BY order_num ASC", (project_id,))
        rows = cursor.fetchall()
        conn.close()

        return [
            Milestone(
                id=row[0], project_id=row[1], title=row[2],
                description=row[3], status=MilestoneStatus(row[4]),
                due_date=row[5], created_at=row[6], updated_at=row[7],
                completed_at=row[8], order=row[9]
            )
            for row in rows
        ]

    # ==================== PROGRESS TRACKING ====================

    def log_progress(self, note: str, goal_id: str = None, project_id: str = None) -> str:
        """Log progress on a goal or project"""
        log_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().timestamp()

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO progress_logs (id, goal_id, project_id, note, logged_at)
            VALUES (?, ?, ?, ?, ?)
        """, (log_id, goal_id, project_id, note, now))
        conn.commit()
        conn.close()

        return log_id

    def _update_project_from_milestones(self, project_id: str):
        """Update project progress based on milestone completion"""
        milestones = self.get_milestones(project_id)
        if not milestones:
            return

        completed = sum(1 for m in milestones if m.status == MilestoneStatus.COMPLETED)
        progress = int((completed / len(milestones)) * 100)

        self.update_project(project_id, progress_percent=progress)

    def _update_goal_from_projects(self, goal_id: str):
        """Update goal progress based on linked projects"""
        projects = self.get_projects(goal_id=goal_id)
        if not projects:
            return

        avg_progress = sum(p.progress_percent for p in projects) // len(projects)
        self.update_goal(goal_id, progress_percent=avg_progress)


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_goals_manager: Optional[GoalsManager] = None


def get_goals_manager() -> GoalsManager:
    """Get or create singleton goals manager instance"""
    global _goals_manager
    if _goals_manager is None:
        _goals_manager = GoalsManager()
    return _goals_manager


# ================================================================================
# COMMAND FUNCTIONS
# ================================================================================

def create_goal_cmd(title: str, description: str, category: str = "personal",
                   target_date: str = None) -> str:
    """Create a new goal"""
    manager = get_goals_manager()

    target_timestamp = None
    if target_date:
        from blue.tools.calendar import parse_datetime
        dt = parse_datetime(target_date)
        if dt:
            target_timestamp = dt.timestamp()

    goal = manager.create_goal(title, description, category, target_timestamp)

    return json.dumps({
        "status": "success",
        "message": f"Goal '{title}' created",
        "goal": goal.to_dict()
    })


def update_goal_progress_cmd(goal_id: str, progress: int) -> str:
    """Update goal progress"""
    manager = get_goals_manager()

    goal = manager.update_goal(goal_id, progress_percent=progress)

    if goal:
        return json.dumps({
            "status": "success",
            "message": f"Goal progress updated to {progress}%",
            "goal": goal.to_dict()
        })
    else:
        return json.dumps({
            "status": "error",
            "error": f"Goal not found: {goal_id}"
        })


def complete_goal_cmd(goal_id: str) -> str:
    """Mark a goal as completed"""
    manager = get_goals_manager()

    goal = manager.update_goal(goal_id, status="completed")

    if goal:
        return json.dumps({
            "status": "success",
            "message": f"Goal '{goal.title}' completed! 🎉",
            "goal": goal.to_dict()
        })
    else:
        return json.dumps({
            "status": "error",
            "error": f"Goal not found: {goal_id}"
        })


def list_goals_cmd(status: str = None, category: str = None) -> str:
    """List goals with optional filtering"""
    manager = get_goals_manager()

    goals = manager.get_goals(status=status, category=category)

    return json.dumps({
        "status": "success",
        "count": len(goals),
        "goals": [g.to_dict() for g in goals]
    })


def create_project_cmd(name: str, description: str, goal_id: str = None,
                      end_date: str = None) -> str:
    """Create a new project"""
    manager = get_goals_manager()

    end_timestamp = None
    if end_date:
        from blue.tools.calendar import parse_datetime
        dt = parse_datetime(end_date)
        if dt:
            end_timestamp = dt.timestamp()

    project = manager.create_project(name, description, end_date=end_timestamp, goal_id=goal_id)

    return json.dumps({
        "status": "success",
        "message": f"Project '{name}' created",
        "project": project.to_dict()
    })


def add_milestone_cmd(project_id: str, title: str, description: str = "",
                     due_date: str = None) -> str:
    """Add a milestone to a project"""
    manager = get_goals_manager()

    due_timestamp = None
    if due_date:
        from blue.tools.calendar import parse_datetime
        dt = parse_datetime(due_date)
        if dt:
            due_timestamp = dt.timestamp()

    milestone = manager.create_milestone(project_id, title, description, due_timestamp)

    return json.dumps({
        "status": "success",
        "message": f"Milestone '{title}' added to project",
        "milestone": milestone.to_dict()
    })


def complete_milestone_cmd(milestone_id: str) -> str:
    """Mark a milestone as completed"""
    manager = get_goals_manager()

    milestone = manager.complete_milestone(milestone_id)

    if milestone:
        return json.dumps({
            "status": "success",
            "message": f"Milestone '{milestone.title}' completed!",
            "milestone": milestone.to_dict()
        })
    else:
        return json.dumps({
            "status": "error",
            "error": f"Milestone not found: {milestone_id}"
        })


def get_project_status_cmd(project_id: str) -> str:
    """Get project status with milestones"""
    manager = get_goals_manager()

    project = manager.get_project(project_id)
    if not project:
        return json.dumps({
            "status": "error",
            "error": f"Project not found: {project_id}"
        })

    milestones = manager.get_milestones(project_id)

    return json.dumps({
        "status": "success",
        "project": project.to_dict(),
        "milestones": [m.to_dict() for m in milestones],
        "milestone_count": len(milestones),
        "completed_milestones": sum(1 for m in milestones if m.status == MilestoneStatus.COMPLETED)
    })


__all__ = [
    'GoalsManager',
    'Goal',
    'Project',
    'Milestone',
    'GoalStatus',
    'GoalCategory',
    'ProjectStatus',
    'MilestoneStatus',
    'get_goals_manager',
    'create_goal_cmd',
    'update_goal_progress_cmd',
    'complete_goal_cmd',
    'list_goals_cmd',
    'create_project_cmd',
    'add_milestone_cmd',
    'complete_milestone_cmd',
    'get_project_status_cmd',
]
