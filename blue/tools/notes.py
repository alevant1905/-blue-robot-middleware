"""
Blue Robot Notes and Tasks Tools
=================================
Manage notes, tasks, and lists with persistent storage.
"""

from __future__ import annotations

import datetime
import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

# ================================================================================
# CONFIGURATION
# ================================================================================

NOTES_DB = os.environ.get("BLUE_NOTES_DB", "data/notes.db")


class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Note:
    """Represents a note."""
    id: str
    title: str
    content: str
    tags: List[str]
    created_at: float
    updated_at: float
    pinned: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "created_at": datetime.datetime.fromtimestamp(self.created_at).isoformat(),
            "updated_at": datetime.datetime.fromtimestamp(self.updated_at).isoformat(),
            "pinned": self.pinned,
            "preview": self.content[:100] + "..." if len(self.content) > 100 else self.content
        }


@dataclass
class Task:
    """Represents a task."""
    id: str
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    due_date: Optional[float]
    tags: List[str]
    created_at: float
    updated_at: float
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "tags": self.tags,
            "created_at": datetime.datetime.fromtimestamp(self.created_at).isoformat(),
            "updated_at": datetime.datetime.fromtimestamp(self.updated_at).isoformat(),
        }
        if self.due_date:
            result["due_date"] = datetime.datetime.fromtimestamp(self.due_date).isoformat()
            result["due_date_human"] = datetime.datetime.fromtimestamp(self.due_date).strftime("%b %d, %Y")
        if self.completed_at:
            result["completed_at"] = datetime.datetime.fromtimestamp(self.completed_at).isoformat()
        return result


@dataclass
class ListItem:
    """Represents an item in a list (shopping, grocery, etc.)."""
    id: str
    list_name: str
    item: str
    quantity: Optional[str]
    checked: bool
    created_at: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "list_name": self.list_name,
            "item": self.item,
            "quantity": self.quantity,
            "checked": self.checked,
            "created_at": datetime.datetime.fromtimestamp(self.created_at).isoformat()
        }


# ================================================================================
# NOTES MANAGER
# ================================================================================

class NotesManager:
    """Manages notes, tasks, and lists."""

    def __init__(self, db_path: str = NOTES_DB):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the database."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Notes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                pinned INTEGER DEFAULT 0
            )
        """)

        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                due_date REAL,
                tags TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                completed_at REAL
            )
        """)

        # Lists table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lists (
                id TEXT PRIMARY KEY,
                list_name TEXT NOT NULL,
                item TEXT NOT NULL,
                quantity TEXT,
                checked INTEGER DEFAULT 0,
                created_at REAL NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    # ==================== NOTES ====================

    def create_note(self, title: str, content: str, tags: List[str] = None,
                   pinned: bool = False) -> Note:
        """Create a new note."""
        note_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().timestamp()

        note = Note(
            id=note_id,
            title=title,
            content=content,
            tags=tags or [],
            created_at=now,
            updated_at=now,
            pinned=pinned
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO notes (id, title, content, tags, created_at, updated_at, pinned)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (note.id, note.title, note.content, json.dumps(note.tags),
              note.created_at, note.updated_at, 1 if note.pinned else 0))
        conn.commit()
        conn.close()

        return note

    def get_note(self, note_id: str) -> Optional[Note]:
        """Get a note by ID."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return Note(
                id=row[0], title=row[1], content=row[2],
                tags=json.loads(row[3] or "[]"),
                created_at=row[4], updated_at=row[5],
                pinned=bool(row[6])
            )
        return None

    def update_note(self, note_id: str, title: str = None, content: str = None,
                   tags: List[str] = None, pinned: bool = None) -> Optional[Note]:
        """Update a note."""
        note = self.get_note(note_id)
        if not note:
            return None

        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        if tags is not None:
            note.tags = tags
        if pinned is not None:
            note.pinned = pinned

        note.updated_at = datetime.datetime.now().timestamp()

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE notes SET title=?, content=?, tags=?, updated_at=?, pinned=?
            WHERE id=?
        """, (note.title, note.content, json.dumps(note.tags),
              note.updated_at, 1 if note.pinned else 0, note.id))
        conn.commit()
        conn.close()

        return note

    def delete_note(self, note_id: str) -> bool:
        """Delete a note."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def search_notes(self, query: str = None, tags: List[str] = None,
                    limit: int = 20) -> List[Note]:
        """Search notes by text or tags."""
        conn = self._get_conn()
        cursor = conn.cursor()

        sql = "SELECT * FROM notes WHERE 1=1"
        params = []

        if query:
            sql += " AND (title LIKE ? OR content LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])

        if tags:
            for tag in tags:
                sql += " AND tags LIKE ?"
                params.append(f"%{tag}%")

        sql += " ORDER BY pinned DESC, updated_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            Note(
                id=row[0], title=row[1], content=row[2],
                tags=json.loads(row[3] or "[]"),
                created_at=row[4], updated_at=row[5],
                pinned=bool(row[6])
            )
            for row in rows
        ]

    def list_notes(self, limit: int = 20) -> List[Note]:
        """List all notes."""
        return self.search_notes(limit=limit)

    # ==================== TASKS ====================

    def create_task(self, title: str, description: str = "",
                   priority: str = "medium", due_date: float = None,
                   tags: List[str] = None) -> Task:
        """Create a new task."""
        task_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().timestamp()

        try:
            priority_enum = TaskPriority(priority.lower())
        except ValueError:
            priority_enum = TaskPriority.MEDIUM

        task = Task(
            id=task_id,
            title=title,
            description=description,
            priority=priority_enum,
            status=TaskStatus.PENDING,
            due_date=due_date,
            tags=tags or [],
            created_at=now,
            updated_at=now
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (id, title, description, priority, status, due_date, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (task.id, task.title, task.description, task.priority.value,
              task.status.value, task.due_date, json.dumps(task.tags),
              task.created_at, task.updated_at))
        conn.commit()
        conn.close()

        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return Task(
                id=row[0], title=row[1], description=row[2],
                priority=TaskPriority(row[3]),
                status=TaskStatus(row[4]),
                due_date=row[5],
                tags=json.loads(row[6] or "[]"),
                created_at=row[7], updated_at=row[8],
                completed_at=row[9]
            )
        return None

    def update_task(self, task_id: str, title: str = None, description: str = None,
                   priority: str = None, status: str = None,
                   due_date: float = None, tags: List[str] = None) -> Optional[Task]:
        """Update a task."""
        task = self.get_task(task_id)
        if not task:
            return None

        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if priority is not None:
            try:
                task.priority = TaskPriority(priority.lower())
            except ValueError:
                pass
        if status is not None:
            try:
                task.status = TaskStatus(status.lower())
                if task.status == TaskStatus.COMPLETED:
                    task.completed_at = datetime.datetime.now().timestamp()
            except ValueError:
                pass
        if due_date is not None:
            task.due_date = due_date
        if tags is not None:
            task.tags = tags

        task.updated_at = datetime.datetime.now().timestamp()

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tasks SET title=?, description=?, priority=?, status=?,
            due_date=?, tags=?, updated_at=?, completed_at=?
            WHERE id=?
        """, (task.title, task.description, task.priority.value,
              task.status.value, task.due_date, json.dumps(task.tags),
              task.updated_at, task.completed_at, task.id))
        conn.commit()
        conn.close()

        return task

    def complete_task(self, task_id: str) -> Optional[Task]:
        """Mark a task as completed."""
        return self.update_task(task_id, status="completed")

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def list_tasks(self, status: str = None, priority: str = None,
                  include_completed: bool = False, limit: int = 20) -> List[Task]:
        """List tasks with optional filtering."""
        conn = self._get_conn()
        cursor = conn.cursor()

        sql = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if not include_completed:
            sql += " AND status != 'completed'"

        if status:
            sql += " AND status = ?"
            params.append(status.lower())

        if priority:
            sql += " AND priority = ?"
            params.append(priority.lower())

        # Order by: urgent first, then due date, then created
        sql += " ORDER BY CASE priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END, due_date ASC NULLS LAST, created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            Task(
                id=row[0], title=row[1], description=row[2],
                priority=TaskPriority(row[3]),
                status=TaskStatus(row[4]),
                due_date=row[5],
                tags=json.loads(row[6] or "[]"),
                created_at=row[7], updated_at=row[8],
                completed_at=row[9]
            )
            for row in rows
        ]

    # ==================== LISTS ====================

    def add_to_list(self, list_name: str, item: str,
                   quantity: str = None) -> ListItem:
        """Add an item to a list."""
        item_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().timestamp()

        list_item = ListItem(
            id=item_id,
            list_name=list_name.lower(),
            item=item,
            quantity=quantity,
            checked=False,
            created_at=now
        )

        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO lists (id, list_name, item, quantity, checked, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (list_item.id, list_item.list_name, list_item.item,
              list_item.quantity, 0, list_item.created_at))
        conn.commit()
        conn.close()

        return list_item

    def check_item(self, item_id: str, checked: bool = True) -> bool:
        """Check/uncheck a list item."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE lists SET checked = ? WHERE id = ?",
                      (1 if checked else 0, item_id))
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def remove_from_list(self, item_id: str = None, list_name: str = None,
                        item: str = None) -> int:
        """Remove item(s) from a list."""
        conn = self._get_conn()
        cursor = conn.cursor()

        if item_id:
            cursor.execute("DELETE FROM lists WHERE id = ?", (item_id,))
        elif list_name and item:
            cursor.execute("DELETE FROM lists WHERE list_name = ? AND item LIKE ?",
                          (list_name.lower(), f"%{item}%"))
        elif list_name:
            # Clear entire list
            cursor.execute("DELETE FROM lists WHERE list_name = ?", (list_name.lower(),))
        else:
            conn.close()
            return 0

        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted

    def get_list(self, list_name: str, include_checked: bool = True) -> List[ListItem]:
        """Get all items in a list."""
        conn = self._get_conn()
        cursor = conn.cursor()

        sql = "SELECT * FROM lists WHERE list_name = ?"
        params = [list_name.lower()]

        if not include_checked:
            sql += " AND checked = 0"

        sql += " ORDER BY checked ASC, created_at DESC"

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            ListItem(
                id=row[0], list_name=row[1], item=row[2],
                quantity=row[3], checked=bool(row[4]),
                created_at=row[5]
            )
            for row in rows
        ]

    def get_all_lists(self) -> Dict[str, List[ListItem]]:
        """Get all lists."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT list_name FROM lists")
        list_names = [row[0] for row in cursor.fetchall()]
        conn.close()

        result = {}
        for name in list_names:
            result[name] = self.get_list(name)

        return result

    def clear_checked(self, list_name: str) -> int:
        """Clear checked items from a list."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM lists WHERE list_name = ? AND checked = 1",
                      (list_name.lower(),))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_notes_manager: Optional[NotesManager] = None


def get_notes_manager() -> NotesManager:
    """Get or create the global notes manager."""
    global _notes_manager
    if _notes_manager is None:
        _notes_manager = NotesManager()
    return _notes_manager


# ================================================================================
# HELPER FUNCTIONS
# ================================================================================

def format_notes_list(notes: List[Note]) -> str:
    """Format notes for display."""
    if not notes:
        return "No notes found."

    lines = []
    for note in notes:
        pin = "📌 " if note.pinned else ""
        tags = f" [{', '.join(note.tags)}]" if note.tags else ""
        preview = note.content[:50].replace('\n', ' ')
        if len(note.content) > 50:
            preview += "..."
        lines.append(f"{pin}[{note.id}] {note.title}{tags}\n   {preview}")

    return "\n".join(lines)


def format_tasks_list(tasks: List[Task]) -> str:
    """Format tasks for display."""
    if not tasks:
        return "No tasks found."

    priority_icons = {
        "low": "🟢",
        "medium": "🟡",
        "high": "🟠",
        "urgent": "🔴"
    }

    status_icons = {
        "pending": "⬜",
        "in_progress": "🔄",
        "completed": "✅",
        "cancelled": "❌"
    }

    lines = []
    for task in tasks:
        p_icon = priority_icons.get(task.priority.value, "⬜")
        s_icon = status_icons.get(task.status.value, "⬜")
        due = ""
        if task.due_date:
            due_dt = datetime.datetime.fromtimestamp(task.due_date)
            due = f" (due: {due_dt.strftime('%b %d')})"
        lines.append(f"{s_icon} {p_icon} [{task.id}] {task.title}{due}")

    return "\n".join(lines)


def format_list_items(items: List[ListItem], list_name: str) -> str:
    """Format list items for display."""
    if not items:
        return f"The {list_name} list is empty."

    lines = [f"📝 {list_name.title()} List:"]
    for item in items:
        check = "☑️" if item.checked else "⬜"
        qty = f" ({item.quantity})" if item.quantity else ""
        lines.append(f"  {check} [{item.id}] {item.item}{qty}")

    return "\n".join(lines)


def parse_due_date(text: str) -> Optional[float]:
    """Parse due date from text."""
    import re
    text = text.lower().strip()
    now = datetime.datetime.now()

    # Relative dates
    if text in ['today', 'tonight']:
        return now.replace(hour=23, minute=59).timestamp()
    if text == 'tomorrow':
        return (now + datetime.timedelta(days=1)).replace(hour=23, minute=59).timestamp()
    if text == 'next week':
        return (now + datetime.timedelta(weeks=1)).timestamp()

    # "in X days/weeks"
    match = re.match(r'in\s+(\d+)\s+(day|days|week|weeks)', text)
    if match:
        num = int(match.group(1))
        unit = match.group(2)
        if 'week' in unit:
            return (now + datetime.timedelta(weeks=num)).timestamp()
        else:
            return (now + datetime.timedelta(days=num)).timestamp()

    # Day names
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    for i, day in enumerate(days):
        if day in text:
            current_weekday = now.weekday()
            days_ahead = i - current_weekday
            if days_ahead <= 0:
                days_ahead += 7
            return (now + datetime.timedelta(days=days_ahead)).timestamp()

    return None


# ================================================================================
# EXECUTOR FUNCTIONS
# ================================================================================

def create_note_cmd(title: str, content: str, tags: str = None) -> str:
    """Create a new note."""
    manager = get_notes_manager()

    tag_list = []
    if tags:
        tag_list = [t.strip() for t in tags.split(',')]

    note = manager.create_note(title, content, tag_list)

    return json.dumps({
        "success": True,
        "message": f"Note '{title}' created",
        "note": note.to_dict()
    })


def get_note_cmd(note_id: str) -> str:
    """Get a note by ID."""
    manager = get_notes_manager()
    note = manager.get_note(note_id)

    if note:
        return json.dumps({
            "success": True,
            "note": note.to_dict()
        })
    else:
        return json.dumps({
            "success": False,
            "error": f"Note not found: {note_id}"
        })


def search_notes_cmd(query: str = None, tags: str = None) -> str:
    """Search notes."""
    manager = get_notes_manager()

    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(',')]

    notes = manager.search_notes(query, tag_list)

    return json.dumps({
        "success": True,
        "count": len(notes),
        "notes": [n.to_dict() for n in notes],
        "formatted": format_notes_list(notes)
    })


def delete_note_cmd(note_id: str) -> str:
    """Delete a note."""
    manager = get_notes_manager()

    if manager.delete_note(note_id):
        return json.dumps({
            "success": True,
            "message": f"Note {note_id} deleted"
        })
    else:
        return json.dumps({
            "success": False,
            "error": f"Note not found: {note_id}"
        })


def create_task_cmd(title: str, description: str = "", priority: str = "medium",
                   due: str = None) -> str:
    """Create a new task."""
    manager = get_notes_manager()

    due_date = None
    if due:
        due_date = parse_due_date(due)

    task = manager.create_task(title, description, priority, due_date)

    return json.dumps({
        "success": True,
        "message": f"Task '{title}' created",
        "task": task.to_dict()
    })


def complete_task_cmd(task_id: str) -> str:
    """Mark a task as completed."""
    manager = get_notes_manager()
    task = manager.complete_task(task_id)

    if task:
        return json.dumps({
            "success": True,
            "message": f"Task '{task.title}' completed!",
            "task": task.to_dict()
        })
    else:
        return json.dumps({
            "success": False,
            "error": f"Task not found: {task_id}"
        })


def list_tasks_cmd(status: str = None, priority: str = None,
                  show_completed: bool = False) -> str:
    """List tasks."""
    manager = get_notes_manager()
    tasks = manager.list_tasks(status, priority, show_completed)

    return json.dumps({
        "success": True,
        "count": len(tasks),
        "tasks": [t.to_dict() for t in tasks],
        "formatted": format_tasks_list(tasks)
    })


def add_to_list_cmd(list_name: str, item: str, quantity: str = None) -> str:
    """Add item to a list."""
    manager = get_notes_manager()
    list_item = manager.add_to_list(list_name, item, quantity)

    return json.dumps({
        "success": True,
        "message": f"Added '{item}' to {list_name} list",
        "item": list_item.to_dict()
    })


def get_list_cmd(list_name: str) -> str:
    """Get a list."""
    manager = get_notes_manager()
    items = manager.get_list(list_name)

    return json.dumps({
        "success": True,
        "list_name": list_name,
        "count": len(items),
        "items": [i.to_dict() for i in items],
        "formatted": format_list_items(items, list_name)
    })


def check_item_cmd(item_id: str) -> str:
    """Check/uncheck a list item."""
    manager = get_notes_manager()

    if manager.check_item(item_id):
        return json.dumps({
            "success": True,
            "message": f"Item {item_id} checked"
        })
    else:
        return json.dumps({
            "success": False,
            "error": f"Item not found: {item_id}"
        })


def remove_from_list_cmd(list_name: str, item: str = None) -> str:
    """Remove item(s) from a list."""
    manager = get_notes_manager()
    count = manager.remove_from_list(list_name=list_name, item=item)

    return json.dumps({
        "success": True,
        "message": f"Removed {count} item(s) from {list_name}",
        "removed_count": count
    })


def execute_notes_command(action: str, params: Dict[str, Any] = None) -> str:
    """Execute a notes/tasks/lists command."""
    if params is None:
        params = {}

    action_lower = action.lower().strip()

    # Notes
    if action_lower in ['create_note', 'new_note', 'add_note', 'note']:
        return create_note_cmd(
            title=params.get('title', 'Untitled'),
            content=params.get('content', ''),
            tags=params.get('tags')
        )
    elif action_lower in ['get_note', 'read_note', 'show_note']:
        return get_note_cmd(params.get('id', ''))
    elif action_lower in ['search_notes', 'find_notes', 'notes']:
        return search_notes_cmd(params.get('query'), params.get('tags'))
    elif action_lower in ['delete_note', 'remove_note']:
        return delete_note_cmd(params.get('id', ''))

    # Tasks
    elif action_lower in ['create_task', 'new_task', 'add_task', 'task', 'todo']:
        return create_task_cmd(
            title=params.get('title', ''),
            description=params.get('description', ''),
            priority=params.get('priority', 'medium'),
            due=params.get('due')
        )
    elif action_lower in ['complete_task', 'done', 'finish_task', 'check_task']:
        return complete_task_cmd(params.get('id', ''))
    elif action_lower in ['list_tasks', 'tasks', 'show_tasks', 'todos']:
        return list_tasks_cmd(
            status=params.get('status'),
            priority=params.get('priority'),
            show_completed=params.get('show_completed', False)
        )

    # Lists
    elif action_lower in ['add_to_list', 'add_item']:
        return add_to_list_cmd(
            list_name=params.get('list', 'shopping'),
            item=params.get('item', ''),
            quantity=params.get('quantity')
        )
    elif action_lower in ['get_list', 'show_list', 'list']:
        return get_list_cmd(params.get('list', 'shopping'))
    elif action_lower in ['check_item', 'mark_item']:
        return check_item_cmd(params.get('id', ''))
    elif action_lower in ['remove_from_list', 'remove_item', 'clear_list']:
        return remove_from_list_cmd(
            list_name=params.get('list', 'shopping'),
            item=params.get('item')
        )

    else:
        return json.dumps({
            "success": False,
            "error": f"Unknown notes action: {action}",
            "available_actions": [
                "create_note", "search_notes", "delete_note",
                "create_task", "complete_task", "list_tasks",
                "add_to_list", "get_list", "check_item", "remove_from_list"
            ]
        })


__all__ = [
    'NotesManager',
    'Note',
    'Task',
    'ListItem',
    'TaskPriority',
    'TaskStatus',
    'get_notes_manager',
    'create_note_cmd',
    'search_notes_cmd',
    'delete_note_cmd',
    'create_task_cmd',
    'complete_task_cmd',
    'list_tasks_cmd',
    'add_to_list_cmd',
    'get_list_cmd',
    'check_item_cmd',
    'remove_from_list_cmd',
    'execute_notes_command',
]
