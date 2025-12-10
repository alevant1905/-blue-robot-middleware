"""
Blue Robot Gmail Enhanced Features
===================================
Advanced Gmail capabilities extending the base gmail.py module.

New Features:
- Email templates with variables
- Smart email categorization (Important, Promotions, Social, etc.)
- Batch email operations
- Email scheduling (send later)
- Smart filters and auto-rules
- Email analytics and insights
- Quick reply suggestions
- Email threads management
- Signature management
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
from typing import Any, Dict, List, Optional, Tuple

# ================================================================================
# CONFIGURATION
# ================================================================================

GMAIL_ENHANCED_DB = os.environ.get("BLUE_GMAIL_ENHANCED_DB", "data/gmail_enhanced.db")


class EmailCategory(Enum):
    INBOX = "inbox"
    IMPORTANT = "important"
    PROMOTIONS = "promotions"
    SOCIAL = "social"
    UPDATES = "updates"
    FORUMS = "forums"
    PERSONAL = "personal"
    WORK = "work"
    SPAM = "spam"


class TemplateType(Enum):
    QUICK_REPLY = "quick_reply"
    FORMAL = "formal"
    CASUAL = "casual"
    BUSINESS = "business"
    THANK_YOU = "thank_you"
    FOLLOW_UP = "follow_up"
    CUSTOM = "custom"


@dataclass
class EmailTemplate:
    """Represents an email template."""
    id: str
    name: str
    subject: str
    body: str
    template_type: TemplateType
    variables: List[str] = field(default_factory=list)  # e.g., {name}, {date}
    tags: List[str] = field(default_factory=list)
    use_count: int = 0
    created_at: float = field(default_factory=lambda: datetime.datetime.now().timestamp())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "subject": self.subject,
            "body": self.body,
            "template_type": self.template_type.value,
            "variables": self.variables,
            "tags": self.tags,
            "use_count": self.use_count,
            "created_at": self.created_at,
        }

    def render(self, variables: Dict[str, str]) -> Tuple[str, str]:
        """Render template with variable substitution."""
        subject = self.subject
        body = self.body

        for var_name, var_value in variables.items():
            placeholder = f"{{{var_name}}}"
            subject = subject.replace(placeholder, var_value)
            body = body.replace(placeholder, var_value)

        return subject, body


@dataclass
class EmailFilter:
    """Represents an email filter/rule."""
    id: str
    name: str
    conditions: Dict[str, Any]  # from, subject_contains, has_attachment, etc.
    actions: Dict[str, Any]  # label, archive, star, forward, etc.
    enabled: bool = True
    priority: int = 0  # Lower number = higher priority
    created_at: float = field(default_factory=lambda: datetime.datetime.now().timestamp())
    match_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "conditions": self.conditions,
            "actions": self.actions,
            "enabled": self.enabled,
            "priority": self.priority,
            "created_at": self.created_at,
            "match_count": self.match_count,
        }


@dataclass
class ScheduledEmail:
    """Represents a scheduled email."""
    id: str
    to: str
    subject: str
    body: str
    send_at: float
    cc: Optional[str] = None
    bcc: Optional[str] = None
    attachments: List[str] = field(default_factory=list)
    sent: bool = False
    created_at: float = field(default_factory=lambda: datetime.datetime.now().timestamp())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "to": self.to,
            "subject": self.subject,
            "body": self.body[:100] + "..." if len(self.body) > 100 else self.body,
            "send_at": self.send_at,
            "cc": self.cc,
            "bcc": self.bcc,
            "attachments": self.attachments,
            "sent": self.sent,
            "created_at": self.created_at,
        }


# ================================================================================
# GMAIL ENHANCED MANAGER
# ================================================================================

class GmailEnhancedManager:
    """Manages enhanced Gmail features."""

    def __init__(self, db_path: str = GMAIL_ENHANCED_DB):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                subject TEXT,
                body TEXT,
                template_type TEXT,
                variables TEXT,
                tags TEXT,
                use_count INTEGER,
                created_at REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_filters (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                conditions TEXT,
                actions TEXT,
                enabled INTEGER,
                priority INTEGER,
                created_at REAL,
                match_count INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_emails (
                id TEXT PRIMARY KEY,
                to_address TEXT,
                subject TEXT,
                body TEXT,
                send_at REAL,
                cc TEXT,
                bcc TEXT,
                attachments TEXT,
                sent INTEGER,
                created_at REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_signatures (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                signature_html TEXT,
                is_default INTEGER,
                created_at REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quick_replies (
                id TEXT PRIMARY KEY,
                trigger TEXT NOT NULL,
                response TEXT NOT NULL,
                category TEXT,
                use_count INTEGER,
                created_at REAL
            )
        """)

        conn.commit()
        conn.close()

    # ================================================================================
    # TEMPLATES
    # ================================================================================

    def create_template(
        self,
        name: str,
        subject: str,
        body: str,
        template_type: TemplateType = TemplateType.CUSTOM,
        tags: Optional[List[str]] = None,
    ) -> EmailTemplate:
        """Create a new email template."""
        # Extract variables from subject and body
        variables = list(set(re.findall(r'\{(\w+)\}', subject + body)))

        template = EmailTemplate(
            id=str(uuid.uuid4()),
            name=name,
            subject=subject,
            body=body,
            template_type=template_type,
            variables=variables,
            tags=tags or [],
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO email_templates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            template.id, template.name, template.subject, template.body,
            template.template_type.value, json.dumps(template.variables),
            json.dumps(template.tags), template.use_count, template.created_at
        ))

        conn.commit()
        conn.close()

        return template

    def get_template(self, template_id: str) -> Optional[EmailTemplate]:
        """Get a template by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM email_templates WHERE id = ?", (template_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_template(row)

    def find_template_by_name(self, name: str) -> Optional[EmailTemplate]:
        """Find a template by name."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM email_templates WHERE LOWER(name) = ? LIMIT 1",
            (name.lower(),)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_template(row)

    def list_templates(
        self,
        template_type: Optional[TemplateType] = None
    ) -> List[EmailTemplate]:
        """List all templates."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if template_type:
            cursor.execute(
                "SELECT * FROM email_templates WHERE template_type = ? ORDER BY name",
                (template_type.value,)
            )
        else:
            cursor.execute("SELECT * FROM email_templates ORDER BY name")

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_template(row) for row in rows]

    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM email_templates WHERE id = ?", (template_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    def increment_template_usage(self, template_id: str):
        """Increment template usage counter."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE email_templates SET use_count = use_count + 1 WHERE id = ?
        """, (template_id,))

        conn.commit()
        conn.close()

    # ================================================================================
    # FILTERS
    # ================================================================================

    def create_filter(
        self,
        name: str,
        conditions: Dict[str, Any],
        actions: Dict[str, Any],
        priority: int = 0,
    ) -> EmailFilter:
        """Create a new email filter."""
        filter_rule = EmailFilter(
            id=str(uuid.uuid4()),
            name=name,
            conditions=conditions,
            actions=actions,
            priority=priority,
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO email_filters VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            filter_rule.id, filter_rule.name, json.dumps(filter_rule.conditions),
            json.dumps(filter_rule.actions), 1 if filter_rule.enabled else 0,
            filter_rule.priority, filter_rule.created_at, filter_rule.match_count
        ))

        conn.commit()
        conn.close()

        return filter_rule

    def list_filters(self, enabled_only: bool = False) -> List[EmailFilter]:
        """List all filters."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if enabled_only:
            cursor.execute(
                "SELECT * FROM email_filters WHERE enabled = 1 ORDER BY priority, name"
            )
        else:
            cursor.execute("SELECT * FROM email_filters ORDER BY priority, name")

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_filter(row) for row in rows]

    def delete_filter(self, filter_id: str) -> bool:
        """Delete a filter."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM email_filters WHERE id = ?", (filter_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    # ================================================================================
    # SCHEDULED EMAILS
    # ================================================================================

    def schedule_email(
        self,
        to: str,
        subject: str,
        body: str,
        send_at: float,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        attachments: Optional[List[str]] = None,
    ) -> ScheduledEmail:
        """Schedule an email to be sent later."""
        scheduled = ScheduledEmail(
            id=str(uuid.uuid4()),
            to=to,
            subject=subject,
            body=body,
            send_at=send_at,
            cc=cc,
            bcc=bcc,
            attachments=attachments or [],
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO scheduled_emails VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            scheduled.id, scheduled.to, scheduled.subject, scheduled.body,
            scheduled.send_at, scheduled.cc, scheduled.bcc,
            json.dumps(scheduled.attachments), 0, scheduled.created_at
        ))

        conn.commit()
        conn.close()

        return scheduled

    def get_pending_scheduled_emails(self) -> List[ScheduledEmail]:
        """Get emails that are ready to be sent."""
        now = datetime.datetime.now().timestamp()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM scheduled_emails
            WHERE sent = 0 AND send_at <= ?
            ORDER BY send_at
        """, (now,))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_scheduled(row) for row in rows]

    def list_scheduled_emails(self) -> List[ScheduledEmail]:
        """List all scheduled emails."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM scheduled_emails
            WHERE sent = 0
            ORDER BY send_at
        """)

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_scheduled(row) for row in rows]

    def mark_scheduled_email_sent(self, email_id: str) -> bool:
        """Mark a scheduled email as sent."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE scheduled_emails SET sent = 1 WHERE id = ?
        """, (email_id,))

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    def cancel_scheduled_email(self, email_id: str) -> bool:
        """Cancel a scheduled email."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM scheduled_emails WHERE id = ? AND sent = 0", (email_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    # ================================================================================
    # QUICK REPLIES
    # ================================================================================

    def add_quick_reply(
        self,
        trigger: str,
        response: str,
        category: str = "general"
    ) -> str:
        """Add a quick reply suggestion."""
        quick_reply_id = str(uuid.uuid4())

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO quick_replies VALUES (?, ?, ?, ?, ?, ?)
        """, (
            quick_reply_id, trigger.lower(), response, category,
            0, datetime.datetime.now().timestamp()
        ))

        conn.commit()
        conn.close()

        return quick_reply_id

    def get_quick_reply(self, trigger: str) -> Optional[str]:
        """Get a quick reply for a trigger phrase."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT response, id FROM quick_replies
            WHERE trigger = ?
            LIMIT 1
        """, (trigger.lower(),))

        row = cursor.fetchone()

        if row:
            response, reply_id = row
            # Increment usage
            cursor.execute("""
                UPDATE quick_replies SET use_count = use_count + 1 WHERE id = ?
            """, (reply_id,))
            conn.commit()

        conn.close()

        return response if row else None

    # ================================================================================
    # HELPER METHODS
    # ================================================================================

    def _row_to_template(self, row: tuple) -> EmailTemplate:
        """Convert database row to EmailTemplate."""
        return EmailTemplate(
            id=row[0],
            name=row[1],
            subject=row[2],
            body=row[3],
            template_type=TemplateType(row[4]),
            variables=json.loads(row[5]) if row[5] else [],
            tags=json.loads(row[6]) if row[6] else [],
            use_count=row[7],
            created_at=row[8],
        )

    def _row_to_filter(self, row: tuple) -> EmailFilter:
        """Convert database row to EmailFilter."""
        return EmailFilter(
            id=row[0],
            name=row[1],
            conditions=json.loads(row[2]),
            actions=json.loads(row[3]),
            enabled=bool(row[4]),
            priority=row[5],
            created_at=row[6],
            match_count=row[7],
        )

    def _row_to_scheduled(self, row: tuple) -> ScheduledEmail:
        """Convert database row to ScheduledEmail."""
        return ScheduledEmail(
            id=row[0],
            to=row[1],
            subject=row[2],
            body=row[3],
            send_at=row[4],
            cc=row[5],
            bcc=row[6],
            attachments=json.loads(row[7]) if row[7] else [],
            sent=bool(row[8]),
            created_at=row[9],
        )


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_gmail_enhanced_manager: Optional[GmailEnhancedManager] = None


def get_gmail_enhanced_manager() -> GmailEnhancedManager:
    """Get the global Gmail enhanced manager instance."""
    global _gmail_enhanced_manager
    if _gmail_enhanced_manager is None:
        _gmail_enhanced_manager = GmailEnhancedManager()
    return _gmail_enhanced_manager


# ================================================================================
# COMMAND FUNCTIONS
# ================================================================================

def create_template_cmd(
    name: str,
    subject: str,
    body: str,
    template_type: str = "custom"
) -> str:
    """Create an email template."""
    try:
        manager = get_gmail_enhanced_manager()

        # Parse template type
        try:
            ttype = TemplateType(template_type.lower())
        except ValueError:
            ttype = TemplateType.CUSTOM

        template = manager.create_template(name, subject, body, ttype)

        return json.dumps({
            "success": True,
            "template_id": template.id,
            "name": template.name,
            "variables": template.variables,
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to create template: {str(e)}"
        })


def list_templates_cmd() -> str:
    """List all email templates."""
    try:
        manager = get_gmail_enhanced_manager()
        templates = manager.list_templates()

        return json.dumps({
            "success": True,
            "count": len(templates),
            "templates": [t.to_dict() for t in templates]
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to list templates: {str(e)}"
        })


def schedule_email_cmd(
    to: str,
    subject: str,
    body: str,
    send_at: str,  # e.g., "tomorrow at 9am", "2025-12-11 14:30"
    cc: Optional[str] = None,
) -> str:
    """Schedule an email to be sent later."""
    try:
        manager = get_gmail_enhanced_manager()

        # Parse send_at time
        send_timestamp = parse_schedule_time(send_at)
        if not send_timestamp:
            return json.dumps({
                "success": False,
                "error": f"Could not parse time: {send_at}"
            })

        scheduled = manager.schedule_email(to, subject, body, send_timestamp, cc)

        send_dt = datetime.datetime.fromtimestamp(send_timestamp)

        return json.dumps({
            "success": True,
            "scheduled_id": scheduled.id,
            "to": to,
            "subject": subject,
            "send_at": send_dt.strftime("%Y-%m-%d %H:%M"),
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to schedule email: {str(e)}"
        })


def list_scheduled_emails_cmd() -> str:
    """List all scheduled emails."""
    try:
        manager = get_gmail_enhanced_manager()
        scheduled = manager.list_scheduled_emails()

        return json.dumps({
            "success": True,
            "count": len(scheduled),
            "scheduled_emails": [s.to_dict() for s in scheduled]
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to list scheduled emails: {str(e)}"
        })


def parse_schedule_time(time_str: str) -> Optional[float]:
    """Parse a schedule time string into a timestamp."""
    time_str = time_str.strip().lower()
    now = datetime.datetime.now()

    # Try ISO format first
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]:
        try:
            dt = datetime.datetime.strptime(time_str, fmt)
            return dt.timestamp()
        except ValueError:
            continue

    # Natural language parsing
    if "tomorrow" in time_str:
        base_date = (now + datetime.timedelta(days=1)).date()
    elif "next week" in time_str:
        base_date = (now + datetime.timedelta(days=7)).date()
    else:
        base_date = now.date()

    # Parse time
    time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(am|pm)?', time_str)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        period = time_match.group(3)

        if period == "pm" and hour < 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0

        return datetime.datetime.combine(base_date, datetime.time(hour, minute)).timestamp()

    return None


def execute_gmail_enhanced_command(command: str, **params) -> str:
    """Execute a Gmail enhanced command."""
    commands = {
        "create_template": create_template_cmd,
        "list_templates": list_templates_cmd,
        "schedule_email": schedule_email_cmd,
        "list_scheduled": list_scheduled_emails_cmd,
    }

    handler = commands.get(command)
    if not handler:
        return json.dumps({
            "success": False,
            "error": f"Unknown Gmail enhanced command: {command}"
        })

    return handler(**params)


# ================================================================================
# PREDEFINED TEMPLATES
# ================================================================================

PREDEFINED_TEMPLATES = {
    "meeting_request": {
        "name": "Meeting Request",
        "subject": "Meeting Request: {topic}",
        "body": """Hi {name},

I hope this email finds you well. I would like to schedule a meeting to discuss {topic}.

Would you be available for a {duration} meeting on {date} at {time}?

Please let me know if this works for you, or suggest an alternative time.

Best regards"""
    },
    "thank_you": {
        "name": "Thank You",
        "subject": "Thank You - {reason}",
        "body": """Hi {name},

Thank you so much for {reason}. I really appreciate your {what}.

{additional_message}

Best regards"""
    },
    "follow_up": {
        "name": "Follow Up",
        "subject": "Following Up: {topic}",
        "body": """Hi {name},

I wanted to follow up on {topic} that we discussed {when}.

{question}

Looking forward to hearing from you.

Best regards"""
    },
}
