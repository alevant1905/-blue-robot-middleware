"""
Blue Robot Gmail AI Features
=============================
AI-powered email intelligence and automation.

Features:
- Smart email summarization
- AI-powered reply generation
- Email priority and urgency detection
- Conversation thread intelligence
- Smart categorization beyond Gmail's defaults
- Action item extraction from emails
- Email sentiment analysis
- Smart search with semantic understanding
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# ================================================================================
# CONFIGURATION
# ================================================================================

GMAIL_AI_DB = os.environ.get("BLUE_GMAIL_AI_DB", "data/gmail_ai.db")


class EmailPriority(Enum):
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class EmailSentiment(Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


@dataclass
class EmailAnalysis:
    """Comprehensive email analysis."""
    email_id: str
    summary: str
    priority: EmailPriority
    sentiment: EmailSentiment
    action_items: List[str]
    key_points: List[str]
    suggested_reply: Optional[str] = None
    urgency_score: float = 0.5  # 0-1 scale
    requires_action: bool = False
    deadline: Optional[str] = None
    analyzed_at: float = field(default_factory=lambda: datetime.datetime.now().timestamp())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "email_id": self.email_id,
            "summary": self.summary,
            "priority": self.priority.value,
            "sentiment": self.sentiment.value,
            "action_items": self.action_items,
            "key_points": self.key_points,
            "suggested_reply": self.suggested_reply,
            "urgency_score": self.urgency_score,
            "requires_action": self.requires_action,
            "deadline": self.deadline,
            "analyzed_at": self.analyzed_at,
        }


# ================================================================================
# EMAIL AI MANAGER
# ================================================================================

class GmailAIManager:
    """Manages AI-powered email intelligence."""

    def __init__(self, db_path: str = GMAIL_AI_DB):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database for AI features."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Email analysis cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_analysis (
                email_id TEXT PRIMARY KEY,
                summary TEXT,
                priority TEXT,
                sentiment TEXT,
                action_items TEXT,
                key_points TEXT,
                suggested_reply TEXT,
                urgency_score REAL,
                requires_action INTEGER,
                deadline TEXT,
                analyzed_at REAL
            )
        """)

        # Conversation threads
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_threads (
                thread_id TEXT PRIMARY KEY,
                participants TEXT,
                subject TEXT,
                message_count INTEGER,
                last_message_at REAL,
                summary TEXT,
                status TEXT
            )
        """)

        # Smart labels/tags
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS smart_labels (
                email_id TEXT,
                label TEXT,
                confidence REAL,
                created_at REAL,
                PRIMARY KEY (email_id, label)
            )
        """)

        conn.commit()
        conn.close()

    def analyze_email(self, email: Dict[str, Any], use_llm: bool = True) -> EmailAnalysis:
        """
        Analyze an email for priority, sentiment, and actionability.

        Args:
            email: Email dict with 'subject', 'from', 'body', etc.
            use_llm: If True, use LLM for advanced analysis
        """
        # Check cache first
        cached = self._get_cached_analysis(email.get('id', ''))
        if cached:
            return cached

        subject = email.get('subject', '')
        body = email.get('body', email.get('snippet', ''))
        sender = email.get('from', '')

        # Rule-based analysis (fast fallback)
        priority = self._detect_priority(subject, body, sender)
        sentiment = self._detect_sentiment(body)
        action_items = self._extract_action_items(body)
        key_points = self._extract_key_points(subject, body)
        urgency_score = self._calculate_urgency(subject, body, sender)
        requires_action = bool(action_items) or self._requires_action(body)
        deadline = self._extract_deadline(body)

        summary = self._generate_summary(subject, body, key_points)

        # LLM-powered analysis (if available and requested)
        if use_llm:
            try:
                llm_analysis = self._llm_analyze(email)
                if llm_analysis:
                    summary = llm_analysis.get('summary', summary)
                    priority = EmailPriority(llm_analysis.get('priority', priority.value))
                    sentiment = EmailSentiment(llm_analysis.get('sentiment', sentiment.value))
                    if llm_analysis.get('action_items'):
                        action_items = llm_analysis['action_items']
                    if llm_analysis.get('key_points'):
                        key_points = llm_analysis['key_points']
                    if llm_analysis.get('suggested_reply'):
                        suggested_reply = llm_analysis['suggested_reply']
                    else:
                        suggested_reply = None
                else:
                    suggested_reply = None
            except Exception as e:
                print(f"   [GMAIL-AI] LLM analysis failed: {e}")
                suggested_reply = None
        else:
            suggested_reply = None

        analysis = EmailAnalysis(
            email_id=email.get('id', ''),
            summary=summary,
            priority=priority,
            sentiment=sentiment,
            action_items=action_items,
            key_points=key_points,
            suggested_reply=suggested_reply,
            urgency_score=urgency_score,
            requires_action=requires_action,
            deadline=deadline
        )

        # Cache the analysis
        self._cache_analysis(analysis)

        return analysis

    def _detect_priority(self, subject: str, body: str, sender: str) -> EmailPriority:
        """Detect email priority using heuristics."""
        text = (subject + " " + body).lower()

        urgent_keywords = [
            'urgent', 'asap', 'immediate', 'emergency', 'critical', 'deadline',
            'time-sensitive', 'right away', 'quickly', 'priority', 'important!'
        ]

        high_keywords = [
            'important', 'action required', 'response needed', 'attention',
            'approval needed', 'review', 'feedback needed', 'please respond'
        ]

        low_keywords = [
            'fyi', 'for your information', 'no action needed', 'just letting you know',
            'newsletter', 'update', 'announcement'
        ]

        if any(keyword in text for keyword in urgent_keywords):
            return EmailPriority.URGENT
        elif any(keyword in text for keyword in high_keywords):
            return EmailPriority.HIGH
        elif any(keyword in text for keyword in low_keywords):
            return EmailPriority.LOW

        return EmailPriority.NORMAL

    def _detect_sentiment(self, text: str) -> EmailSentiment:
        """Detect sentiment using keyword matching."""
        text_lower = text.lower()

        positive_keywords = [
            'thank', 'thanks', 'appreciate', 'great', 'excellent', 'wonderful',
            'happy', 'pleased', 'congratulations', 'success', 'good news'
        ]

        negative_keywords = [
            'unfortunately', 'sorry', 'apologize', 'issue', 'problem', 'concern',
            'disappointed', 'frustrated', 'bad news', 'failed', 'error'
        ]

        positive_count = sum(1 for kw in positive_keywords if kw in text_lower)
        negative_count = sum(1 for kw in negative_keywords if kw in text_lower)

        if positive_count > 0 and negative_count > 0:
            return EmailSentiment.MIXED
        elif positive_count > negative_count:
            return EmailSentiment.POSITIVE
        elif negative_count > positive_count:
            return EmailSentiment.NEGATIVE

        return EmailSentiment.NEUTRAL

    def _extract_action_items(self, text: str) -> List[str]:
        """Extract action items from email text."""
        action_items = []

        # Look for common action item patterns
        patterns = [
            r'(?:please|could you|can you|need you to)\s+([^.!?]+)[.!?]',
            r'(?:action item|to-do|todo):\s*([^.!?\n]+)',
            r'you (?:should|must|need to)\s+([^.!?]+)[.!?]',
            r'\[ \]\s*([^.!?\n]+)',  # Checkbox items
            r'^\s*[-*]\s+([^.!?\n]+)',  # Bullet points
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                action = match.group(1).strip()
                if len(action) > 10 and action not in action_items:
                    action_items.append(action)

        return action_items[:5]  # Limit to top 5

    def _extract_key_points(self, subject: str, body: str) -> List[str]:
        """Extract key points from email."""
        key_points = []

        # Add subject as first key point if meaningful
        if len(subject) > 5 and not subject.lower().startswith('re:'):
            key_points.append(subject)

        # Extract sentences that seem important
        sentences = re.split(r'[.!?]\s+', body)
        for sentence in sentences:
            sentence = sentence.strip()
            # Important indicators
            if any(keyword in sentence.lower() for keyword in [
                'important', 'please note', 'reminder', 'deadline', 'key', 'main'
            ]):
                if len(sentence) > 20 and sentence not in key_points:
                    key_points.append(sentence[:200])  # Limit length

        return key_points[:3]  # Top 3 key points

    def _calculate_urgency(self, subject: str, body: str, sender: str) -> float:
        """Calculate urgency score (0-1)."""
        score = 0.5  # Base score

        text = (subject + " " + body).lower()

        # Urgency indicators
        if 'urgent' in text or 'asap' in text:
            score += 0.3
        if 'deadline' in text or 'due' in text:
            score += 0.2
        if 'emergency' in text or 'critical' in text:
            score += 0.3
        if 'today' in text or 'now' in text:
            score += 0.1
        if '?' in subject:  # Question in subject = likely needs response
            score += 0.1

        return min(1.0, score)

    def _requires_action(self, text: str) -> bool:
        """Determine if email requires action."""
        action_phrases = [
            'please', 'action required', 'respond', 'reply', 'confirm',
            'approve', 'review', 'feedback', 'sign', 'complete', 'submit'
        ]

        text_lower = text.lower()
        return any(phrase in text_lower for phrase in action_phrases)

    def _extract_deadline(self, text: str) -> Optional[str]:
        """Extract deadline/due date from email."""
        # Look for date patterns
        date_patterns = [
            r'(?:due|deadline|by)\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?)',
            r'(?:due|deadline|by)\s+(\d{1,2}/\d{1,2}/\d{2,4})',
            r'(?:due|deadline|by)\s+(today|tomorrow|next week|end of week)',
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _generate_summary(self, subject: str, body: str, key_points: List[str]) -> str:
        """Generate a brief summary of the email."""
        if key_points:
            return f"{subject}: " + "; ".join(key_points[:2])

        # Fallback: first sentence of body
        sentences = re.split(r'[.!?]\s+', body)
        if sentences:
            first_sentence = sentences[0].strip()
            if len(first_sentence) > 10:
                return first_sentence[:150]

        return subject

    def _llm_analyze(self, email: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Use LLM to analyze email (if available)."""
        try:
            # Try to import LLM client
            try:
                from blue.llm import call_llm
            except ImportError:
                return None

            subject = email.get('subject', '')
            body = email.get('body', email.get('snippet', ''))
            sender = email.get('from', '')

            prompt = f"""Analyze this email and provide a structured response:

Subject: {subject}
From: {sender}
Body: {body[:1000]}

Provide analysis in JSON format:
{{
    "summary": "Brief 1-2 sentence summary",
    "priority": "urgent|high|normal|low",
    "sentiment": "positive|neutral|negative|mixed",
    "action_items": ["list", "of", "actions"],
    "key_points": ["important", "points"],
    "suggested_reply": "A brief, professional reply suggestion (or null if not needed)",
    "requires_action": true/false,
    "deadline": "extracted deadline or null"
}}

Focus on being concise and actionable."""

            response = call_llm(prompt, max_tokens=500, temperature=0.3)

            # Try to parse JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))

        except Exception as e:
            print(f"   [LLM] Analysis failed: {e}")

        return None

    def _cache_analysis(self, analysis: EmailAnalysis):
        """Cache email analysis."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO email_analysis
            (email_id, summary, priority, sentiment, action_items, key_points,
             suggested_reply, urgency_score, requires_action, deadline, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analysis.email_id,
            analysis.summary,
            analysis.priority.value,
            analysis.sentiment.value,
            json.dumps(analysis.action_items),
            json.dumps(analysis.key_points),
            analysis.suggested_reply,
            analysis.urgency_score,
            1 if analysis.requires_action else 0,
            analysis.deadline,
            analysis.analyzed_at
        ))

        conn.commit()
        conn.close()

    def _get_cached_analysis(self, email_id: str) -> Optional[EmailAnalysis]:
        """Get cached analysis if recent."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM email_analysis WHERE email_id = ?
        """, (email_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            # Check if cache is still fresh (24 hours)
            age = datetime.datetime.now().timestamp() - row[10]
            if age < 24 * 3600:
                return EmailAnalysis(
                    email_id=row[0],
                    summary=row[1],
                    priority=EmailPriority(row[2]),
                    sentiment=EmailSentiment(row[3]),
                    action_items=json.loads(row[4]),
                    key_points=json.loads(row[5]),
                    suggested_reply=row[6],
                    urgency_score=row[7],
                    requires_action=bool(row[8]),
                    deadline=row[9],
                    analyzed_at=row[10]
                )

        return None

    def smart_inbox_summary(self, emails: List[Dict[str, Any]], use_llm: bool = False) -> Dict[str, Any]:
        """Generate an intelligent inbox summary."""
        if not emails:
            return {
                "total": 0,
                "by_priority": {},
                "requires_action": 0,
                "summary": "No emails to analyze"
            }

        analyses = []
        for email in emails:
            analysis = self.analyze_email(email, use_llm=use_llm)
            analyses.append(analysis)

        # Aggregate statistics
        by_priority = {}
        by_sentiment = {}
        total_action_items = 0
        requires_action_count = 0
        urgent_emails = []

        for analysis in analyses:
            # Count by priority
            priority_key = analysis.priority.value
            by_priority[priority_key] = by_priority.get(priority_key, 0) + 1

            # Count by sentiment
            sentiment_key = analysis.sentiment.value
            by_sentiment[sentiment_key] = by_sentiment.get(sentiment_key, 0) + 1

            # Count action items
            total_action_items += len(analysis.action_items)

            if analysis.requires_action:
                requires_action_count += 1

            if analysis.priority == EmailPriority.URGENT:
                urgent_emails.append({
                    "subject": emails[analyses.index(analysis)].get('subject', ''),
                    "from": emails[analyses.index(analysis)].get('from', ''),
                    "summary": analysis.summary,
                    "deadline": analysis.deadline
                })

        return {
            "total": len(emails),
            "by_priority": by_priority,
            "by_sentiment": by_sentiment,
            "requires_action": requires_action_count,
            "total_action_items": total_action_items,
            "urgent_emails": urgent_emails,
            "summary": f"You have {len(emails)} emails: {requires_action_count} need action, {by_priority.get('urgent', 0)} are urgent."
        }


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_gmail_ai_manager: Optional[GmailAIManager] = None


def get_gmail_ai_manager() -> GmailAIManager:
    """Get or create Gmail AI manager instance."""
    global _gmail_ai_manager
    if _gmail_ai_manager is None:
        _gmail_ai_manager = GmailAIManager()
    return _gmail_ai_manager


# ================================================================================
# COMMAND FUNCTIONS
# ================================================================================

def analyze_inbox_cmd(max_emails: int = 20, use_llm: bool = False) -> str:
    """Analyze inbox and provide intelligent summary."""
    try:
        from blue.tools.gmail import get_gmail_service

        service = get_gmail_service()
        manager = get_gmail_ai_manager()

        # Get recent emails
        results = service.users().messages().list(
            userId='me',
            maxResults=max_emails,
            q='in:inbox'
        ).execute()

        messages = results.get('messages', [])
        emails = []

        for msg in messages:
            msg_data = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()

            headers = msg_data['payload']['headers']
            emails.append({
                'id': msg['id'],
                'subject': next((h['value'] for h in headers if h['name'].lower() == 'subject'), ''),
                'from': next((h['value'] for h in headers if h['name'].lower() == 'from'), ''),
                'body': msg_data.get('snippet', ''),
            })

        summary = manager.smart_inbox_summary(emails, use_llm=use_llm)

        return json.dumps({
            "success": True,
            "inbox_summary": summary,
            "message": summary['summary']
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


def suggest_reply_cmd(email_id: str, use_llm: bool = True) -> str:
    """Generate a suggested reply for an email."""
    try:
        from blue.tools.gmail import get_gmail_service

        service = get_gmail_service()
        manager = get_gmail_ai_manager()

        # Get email
        msg_data = service.users().messages().get(
            userId='me',
            id=email_id,
            format='full'
        ).execute()

        headers = msg_data['payload']['headers']
        email = {
            'id': email_id,
            'subject': next((h['value'] for h in headers if h['name'].lower() == 'subject'), ''),
            'from': next((h['value'] for h in headers if h['name'].lower() == 'from'), ''),
            'body': msg_data.get('snippet', ''),
        }

        analysis = manager.analyze_email(email, use_llm=use_llm)

        return json.dumps({
            "success": True,
            "email_id": email_id,
            "analysis": analysis.to_dict(),
            "suggested_reply": analysis.suggested_reply,
            "message": "Reply suggestion generated"
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


__all__ = [
    'EmailPriority',
    'EmailSentiment',
    'EmailAnalysis',
    'GmailAIManager',
    'get_gmail_ai_manager',
    'analyze_inbox_cmd',
    'suggest_reply_cmd',
]
