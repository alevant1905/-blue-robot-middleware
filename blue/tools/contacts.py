"""
Blue Robot Contacts Tool
=========================
Comprehensive contact management with communication integration.

Features:
- Store and organize contacts
- Link contacts to recognition data
- Communication history tracking
- Birthday reminders
- Groups and tags
- Quick dial/message shortcuts
- Integration with email, phone, and messaging
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sqlite3
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# ================================================================================
# CONFIGURATION
# ================================================================================

CONTACTS_DB = os.environ.get("BLUE_CONTACTS_DB", "data/contacts.db")


class ContactType(Enum):
    PERSONAL = "personal"
    WORK = "work"
    FAMILY = "family"
    FRIEND = "friend"
    BUSINESS = "business"
    OTHER = "other"


class CommunicationType(Enum):
    EMAIL = "email"
    PHONE = "phone"
    SMS = "sms"
    VIDEO_CALL = "video_call"
    IN_PERSON = "in_person"
    OTHER = "other"


@dataclass
class Contact:
    """Represents a contact."""
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    birthday: Optional[str] = None  # YYYY-MM-DD format
    contact_type: ContactType = ContactType.OTHER
    company: Optional[str] = None
    job_title: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    favorite: bool = False
    recognition_id: Optional[str] = None  # Link to face recognition
    created_at: float = field(default_factory=lambda: datetime.datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.datetime.now().timestamp())
    last_contacted: Optional[float] = None
    contact_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "birthday": self.birthday,
            "contact_type": self.contact_type.value,
            "company": self.company,
            "job_title": self.job_title,
            "notes": self.notes,
            "tags": self.tags,
            "favorite": self.favorite,
            "recognition_id": self.recognition_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_contacted": self.last_contacted,
            "contact_count": self.contact_count,
        }

    def get_display_name(self) -> str:
        """Get formatted display name."""
        if self.company and self.job_title:
            return f"{self.name} ({self.job_title} at {self.company})"
        elif self.company:
            return f"{self.name} ({self.company})"
        elif self.job_title:
            return f"{self.name} ({self.job_title})"
        return self.name

    def has_birthday_soon(self, days: int = 7) -> bool:
        """Check if birthday is within specified days."""
        if not self.birthday:
            return False

        try:
            birth_date = datetime.datetime.strptime(self.birthday, "%Y-%m-%d").date()
            today = datetime.datetime.now().date()

            # Get this year's birthday
            this_year_birthday = birth_date.replace(year=today.year)

            # If already passed, check next year
            if this_year_birthday < today:
                this_year_birthday = birth_date.replace(year=today.year + 1)

            days_until = (this_year_birthday - today).days
            return 0 <= days_until <= days

        except ValueError:
            return False


@dataclass
class CommunicationLog:
    """Log entry for communication with a contact."""
    id: str
    contact_id: str
    communication_type: CommunicationType
    timestamp: float
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    successful: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "contact_id": self.contact_id,
            "communication_type": self.communication_type.value,
            "timestamp": self.timestamp,
            "duration_minutes": self.duration_minutes,
            "notes": self.notes,
            "successful": self.successful,
        }


# ================================================================================
# CONTACT MANAGER
# ================================================================================

class ContactManager:
    """Manages contacts with persistent storage."""

    def __init__(self, db_path: str = CONTACTS_DB):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                address TEXT,
                birthday TEXT,
                contact_type TEXT,
                company TEXT,
                job_title TEXT,
                notes TEXT,
                tags TEXT,
                favorite INTEGER,
                recognition_id TEXT,
                created_at REAL,
                updated_at REAL,
                last_contacted REAL,
                contact_count INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS communication_log (
                id TEXT PRIMARY KEY,
                contact_id TEXT,
                communication_type TEXT,
                timestamp REAL,
                duration_minutes INTEGER,
                notes TEXT,
                successful INTEGER,
                FOREIGN KEY (contact_id) REFERENCES contacts (id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contact_groups (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contact_group_members (
                group_id TEXT,
                contact_id TEXT,
                PRIMARY KEY (group_id, contact_id),
                FOREIGN KEY (group_id) REFERENCES contact_groups (id),
                FOREIGN KEY (contact_id) REFERENCES contacts (id)
            )
        """)

        conn.commit()
        conn.close()

    def add_contact(
        self,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        birthday: Optional[str] = None,
        contact_type: ContactType = ContactType.OTHER,
        company: Optional[str] = None,
        job_title: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
        favorite: bool = False,
        recognition_id: Optional[str] = None,
    ) -> Contact:
        """Add a new contact."""
        contact = Contact(
            id=str(uuid.uuid4()),
            name=name,
            email=email,
            phone=phone,
            address=address,
            birthday=birthday,
            contact_type=contact_type,
            company=company,
            job_title=job_title,
            notes=notes,
            tags=tags or [],
            favorite=favorite,
            recognition_id=recognition_id,
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO contacts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            contact.id, contact.name, contact.email, contact.phone,
            contact.address, contact.birthday, contact.contact_type.value,
            contact.company, contact.job_title, contact.notes,
            json.dumps(contact.tags), 1 if contact.favorite else 0,
            contact.recognition_id, contact.created_at, contact.updated_at,
            contact.last_contacted, contact.contact_count
        ))

        conn.commit()
        conn.close()

        return contact

    def get_contact(self, contact_id: str) -> Optional[Contact]:
        """Get a contact by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_contact(row)

    def find_contact_by_name(self, name: str) -> Optional[Contact]:
        """Find a contact by name (case-insensitive)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM contacts WHERE LOWER(name) = ? LIMIT 1",
            (name.lower(),)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_contact(row)

    def find_contact_by_email(self, email: str) -> Optional[Contact]:
        """Find a contact by email."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM contacts WHERE LOWER(email) = ? LIMIT 1",
            (email.lower(),)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_contact(row)

    def find_contact_by_phone(self, phone: str) -> Optional[Contact]:
        """Find a contact by phone number."""
        # Remove non-digits for comparison
        phone_digits = re.sub(r'\D', '', phone)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM contacts WHERE phone IS NOT NULL")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            row_phone = re.sub(r'\D', '', row[3] or "")
            if phone_digits and row_phone and phone_digits in row_phone:
                return self._row_to_contact(row)

        return None

    def list_contacts(
        self,
        contact_type: Optional[ContactType] = None,
        favorites_only: bool = False,
        has_birthday: bool = False,
    ) -> List[Contact]:
        """List contacts with optional filters."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM contacts WHERE 1=1"
        params = []

        if contact_type:
            query += " AND contact_type = ?"
            params.append(contact_type.value)

        if favorites_only:
            query += " AND favorite = 1"

        if has_birthday:
            query += " AND birthday IS NOT NULL"

        query += " ORDER BY name"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_contact(row) for row in rows]

    def search_contacts(self, query: str) -> List[Contact]:
        """Search contacts by name, email, phone, or company."""
        query_lower = query.lower()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM contacts
            WHERE LOWER(name) LIKE ?
               OR LOWER(email) LIKE ?
               OR LOWER(phone) LIKE ?
               OR LOWER(company) LIKE ?
               OR LOWER(notes) LIKE ?
            ORDER BY favorite DESC, name
        """, (
            f"%{query_lower}%", f"%{query_lower}%", f"%{query_lower}%",
            f"%{query_lower}%", f"%{query_lower}%"
        ))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_contact(row) for row in rows]

    def update_contact(self, contact_id: str, **updates) -> bool:
        """Update a contact."""
        contact = self.get_contact(contact_id)
        if not contact:
            return False

        # Update fields
        for key, value in updates.items():
            if hasattr(contact, key):
                setattr(contact, key, value)

        contact.updated_at = datetime.datetime.now().timestamp()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE contacts SET
                name = ?, email = ?, phone = ?, address = ?,
                birthday = ?, contact_type = ?, company = ?, job_title = ?,
                notes = ?, tags = ?, favorite = ?, recognition_id = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            contact.name, contact.email, contact.phone, contact.address,
            contact.birthday, contact.contact_type.value, contact.company,
            contact.job_title, contact.notes, json.dumps(contact.tags),
            1 if contact.favorite else 0, contact.recognition_id,
            contact.updated_at, contact.id
        ))

        conn.commit()
        conn.close()

        return True

    def delete_contact(self, contact_id: str) -> bool:
        """Delete a contact."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    def log_communication(
        self,
        contact_id: str,
        communication_type: CommunicationType,
        duration_minutes: Optional[int] = None,
        notes: Optional[str] = None,
        successful: bool = True,
    ) -> bool:
        """Log a communication with a contact."""
        contact = self.get_contact(contact_id)
        if not contact:
            return False

        now = datetime.datetime.now().timestamp()

        log_entry = CommunicationLog(
            id=str(uuid.uuid4()),
            contact_id=contact_id,
            communication_type=communication_type,
            timestamp=now,
            duration_minutes=duration_minutes,
            notes=notes,
            successful=successful,
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Add log entry
        cursor.execute("""
            INSERT INTO communication_log VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            log_entry.id, log_entry.contact_id, log_entry.communication_type.value,
            log_entry.timestamp, log_entry.duration_minutes, log_entry.notes,
            1 if log_entry.successful else 0
        ))

        # Update contact stats
        cursor.execute("""
            UPDATE contacts SET
                last_contacted = ?,
                contact_count = contact_count + 1
            WHERE id = ?
        """, (now, contact_id))

        conn.commit()
        conn.close()

        return True

    def get_upcoming_birthdays(self, days: int = 30) -> List[Contact]:
        """Get contacts with birthdays in the next N days."""
        contacts = self.list_contacts(has_birthday=True)
        return [c for c in contacts if c.has_birthday_soon(days)]

    def get_communication_history(
        self,
        contact_id: str,
        limit: int = 10
    ) -> List[CommunicationLog]:
        """Get communication history for a contact."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM communication_log
            WHERE contact_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (contact_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_log(row) for row in rows]

    def _row_to_contact(self, row: tuple) -> Contact:
        """Convert database row to Contact."""
        return Contact(
            id=row[0],
            name=row[1],
            email=row[2],
            phone=row[3],
            address=row[4],
            birthday=row[5],
            contact_type=ContactType(row[6]),
            company=row[7],
            job_title=row[8],
            notes=row[9],
            tags=json.loads(row[10]) if row[10] else [],
            favorite=bool(row[11]),
            recognition_id=row[12],
            created_at=row[13],
            updated_at=row[14],
            last_contacted=row[15],
            contact_count=row[16],
        )

    def _row_to_log(self, row: tuple) -> CommunicationLog:
        """Convert database row to CommunicationLog."""
        return CommunicationLog(
            id=row[0],
            contact_id=row[1],
            communication_type=CommunicationType(row[2]),
            timestamp=row[3],
            duration_minutes=row[4],
            notes=row[5],
            successful=bool(row[6]),
        )


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_contact_manager: Optional[ContactManager] = None


def get_contact_manager() -> ContactManager:
    """Get the global contact manager instance."""
    global _contact_manager
    if _contact_manager is None:
        _contact_manager = ContactManager()
    return _contact_manager


# ================================================================================
# COMMAND FUNCTIONS
# ================================================================================

def add_contact_cmd(
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    contact_type: str = "other",
    company: Optional[str] = None,
    notes: Optional[str] = None,
    favorite: bool = False,
) -> str:
    """Add a new contact."""
    try:
        manager = get_contact_manager()

        # Parse contact type
        try:
            ctype = ContactType(contact_type.lower())
        except ValueError:
            ctype = ContactType.OTHER

        contact = manager.add_contact(
            name=name,
            email=email,
            phone=phone,
            contact_type=ctype,
            company=company,
            notes=notes,
            favorite=favorite,
        )

        return json.dumps({
            "success": True,
            "contact_id": contact.id,
            "name": contact.name,
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to add contact: {str(e)}"
        })


def list_contacts_cmd(
    contact_type: Optional[str] = None,
    favorites_only: bool = False
) -> str:
    """List contacts."""
    try:
        manager = get_contact_manager()

        # Parse type filter
        type_filter = None
        if contact_type:
            try:
                type_filter = ContactType(contact_type.lower())
            except ValueError:
                pass

        contacts = manager.list_contacts(type_filter, favorites_only)

        return json.dumps({
            "success": True,
            "count": len(contacts),
            "contacts": [c.to_dict() for c in contacts]
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to list contacts: {str(e)}"
        })


def search_contacts_cmd(query: str) -> str:
    """Search contacts."""
    try:
        manager = get_contact_manager()
        contacts = manager.search_contacts(query)

        return json.dumps({
            "success": True,
            "count": len(contacts),
            "contacts": [c.to_dict() for c in contacts]
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to search contacts: {str(e)}"
        })


def get_contact_cmd(name: str) -> str:
    """Get a specific contact."""
    try:
        manager = get_contact_manager()
        contact = manager.find_contact_by_name(name)

        if not contact:
            return json.dumps({
                "success": False,
                "error": f"Contact not found: {name}"
            })

        return json.dumps({
            "success": True,
            "contact": contact.to_dict()
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to get contact: {str(e)}"
        })


def upcoming_birthdays_cmd(days: int = 30) -> str:
    """Get upcoming birthdays."""
    try:
        manager = get_contact_manager()
        contacts = manager.get_upcoming_birthdays(days)

        return json.dumps({
            "success": True,
            "count": len(contacts),
            "contacts": [
                {
                    "name": c.name,
                    "birthday": c.birthday,
                    "email": c.email,
                    "phone": c.phone,
                }
                for c in contacts
            ]
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to get birthdays: {str(e)}"
        })


def execute_contact_command(command: str, **params) -> str:
    """Execute a contact command."""
    commands = {
        "add": add_contact_cmd,
        "list": list_contacts_cmd,
        "search": search_contacts_cmd,
        "get": get_contact_cmd,
        "birthdays": upcoming_birthdays_cmd,
    }

    handler = commands.get(command)
    if not handler:
        return json.dumps({
            "success": False,
            "error": f"Unknown contact command: {command}"
        })

    return handler(**params)
