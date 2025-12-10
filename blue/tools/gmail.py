"""
Blue Robot Gmail Tools - Enhanced Version
==========================================
Gmail email reading, sending, and replying with advanced features.

Features:
- Read emails with filtering (sender, date, labels, attachments)
- Send emails with HTML support and attachments
- Reply to emails (single or batch)
- Label management (add/remove labels, archive, star)
- Attachment downloading
- Email search with natural language
- Draft creation and management
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import pickle
import re
from datetime import datetime, timedelta
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email import encoders
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

# ================================================================================
# CONFIGURATION
# ================================================================================

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
]

GMAIL_TOKEN_FILE = "gmail_token.pickle"
GMAIL_CREDENTIALS_FILE = "gmail_credentials.json"
GMAIL_USER_EMAIL = os.environ.get("GMAIL_USER_EMAIL", "")

# Check if Gmail libraries are available
GMAIL_AVAILABLE = False
try:
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    GMAIL_AVAILABLE = True
except ImportError:
    pass

_gmail_service = None

# Download folder for attachments
ATTACHMENT_DOWNLOAD_FOLDER = Path(os.environ.get("ATTACHMENT_FOLDER", "downloads/attachments"))


# ================================================================================
# HELPER FUNCTIONS
# ================================================================================

def parse_natural_date_filter(query: str) -> str:
    """
    Convert natural language date filters to Gmail query syntax.

    Examples:
        "from last week" -> "after:2024/01/01"
        "today" -> "after:2024/01/08"
        "yesterday" -> "after:2024/01/07 before:2024/01/08"
    """
    query_lower = query.lower()
    today = datetime.now()

    if 'today' in query_lower:
        return f"after:{today.strftime('%Y/%m/%d')}"
    elif 'yesterday' in query_lower:
        yesterday = today - timedelta(days=1)
        return f"after:{yesterday.strftime('%Y/%m/%d')} before:{today.strftime('%Y/%m/%d')}"
    elif 'last week' in query_lower or 'past week' in query_lower:
        week_ago = today - timedelta(days=7)
        return f"after:{week_ago.strftime('%Y/%m/%d')}"
    elif 'last month' in query_lower or 'past month' in query_lower:
        month_ago = today - timedelta(days=30)
        return f"after:{month_ago.strftime('%Y/%m/%d')}"
    elif 'this week' in query_lower:
        # Start of this week (Monday)
        start_of_week = today - timedelta(days=today.weekday())
        return f"after:{start_of_week.strftime('%Y/%m/%d')}"
    elif 'this month' in query_lower:
        start_of_month = today.replace(day=1)
        return f"after:{start_of_month.strftime('%Y/%m/%d')}"

    return ""


def build_gmail_query(args: Dict[str, Any]) -> str:
    """
    Build a Gmail search query from structured arguments.

    Supports:
        - from: sender email or name
        - to: recipient
        - subject: subject keywords
        - has_attachment: bool
        - label: label name
        - is_unread: bool
        - is_starred: bool
        - date_filter: natural language or Gmail syntax
        - keywords: general search terms
    """
    query_parts = []

    # Direct query string
    if args.get("query"):
        query_parts.append(args["query"])

    # Sender filter
    if args.get("from"):
        query_parts.append(f"from:{args['from']}")

    # Recipient filter
    if args.get("to"):
        query_parts.append(f"to:{args['to']}")

    # Subject filter
    if args.get("subject"):
        query_parts.append(f"subject:{args['subject']}")

    # Attachment filter
    if args.get("has_attachment"):
        query_parts.append("has:attachment")

    # Label filter
    if args.get("label"):
        label = args["label"].lower().replace(" ", "-")
        query_parts.append(f"label:{label}")

    # Unread filter
    if args.get("is_unread"):
        query_parts.append("is:unread")

    # Starred filter
    if args.get("is_starred"):
        query_parts.append("is:starred")

    # Important filter
    if args.get("is_important"):
        query_parts.append("is:important")

    # Date filter
    if args.get("date_filter"):
        date_query = parse_natural_date_filter(args["date_filter"])
        if date_query:
            query_parts.append(date_query)

    # After date
    if args.get("after"):
        query_parts.append(f"after:{args['after']}")

    # Before date
    if args.get("before"):
        query_parts.append(f"before:{args['before']}")

    # General keywords
    if args.get("keywords"):
        query_parts.append(args["keywords"])

    return " ".join(query_parts)


def extract_email_body(payload: Dict, prefer_html: bool = False) -> Tuple[str, str]:
    """
    Extract email body from Gmail message payload.

    Returns:
        Tuple of (body_text, content_type)
    """
    body_text = ""
    body_html = ""

    def _extract_from_parts(parts):
        nonlocal body_text, body_html
        for part in parts:
            mime_type = part.get('mimeType', '')
            if mime_type == 'text/plain' and 'data' in part.get('body', {}):
                body_text = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
            elif mime_type == 'text/html' and 'data' in part.get('body', {}):
                body_html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
            elif 'parts' in part:
                _extract_from_parts(part['parts'])

    if 'parts' in payload:
        _extract_from_parts(payload['parts'])
    elif 'body' in payload and 'data' in payload['body']:
        data = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='replace')
        if payload.get('mimeType') == 'text/html':
            body_html = data
        else:
            body_text = data

    if prefer_html and body_html:
        return body_html, 'text/html'
    return body_text or body_html, 'text/plain' if body_text else 'text/html'


def extract_attachments_info(payload: Dict) -> List[Dict]:
    """Extract attachment information from email payload."""
    attachments = []

    def _extract_from_parts(parts, msg_id: str = ""):
        for part in parts:
            filename = part.get('filename', '')
            if filename:
                body = part.get('body', {})
                attachments.append({
                    'filename': filename,
                    'mime_type': part.get('mimeType', 'application/octet-stream'),
                    'size': body.get('size', 0),
                    'attachment_id': body.get('attachmentId', ''),
                    'part_id': part.get('partId', '')
                })
            if 'parts' in part:
                _extract_from_parts(part['parts'], msg_id)

    if 'parts' in payload:
        _extract_from_parts(payload['parts'])

    return attachments


def format_email_size(size_bytes: int) -> str:
    """Format byte size to human readable."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


# ================================================================================
# SERVICE
# ================================================================================

def get_gmail_service():
    """Get or create Gmail API service."""
    global _gmail_service
    if _gmail_service:
        return _gmail_service

    if not GMAIL_AVAILABLE:
        raise Exception("Gmail libraries not installed")

    creds = None
    if os.path.exists(GMAIL_TOKEN_FILE):
        with open(GMAIL_TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(GMAIL_CREDENTIALS_FILE):
                raise Exception(f"Gmail credentials file not found: {GMAIL_CREDENTIALS_FILE}")
            flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_FILE, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)

        with open(GMAIL_TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    _gmail_service = build('gmail', 'v1', credentials=creds)
    return _gmail_service


# ================================================================================
# READ EMAIL - ENHANCED
# ================================================================================

def execute_read_gmail(args: Dict[str, Any]) -> str:
    """
    Read and search Gmail messages with enhanced filtering.

    Args (all optional):
        query: Direct Gmail query string
        from: Filter by sender
        to: Filter by recipient
        subject: Filter by subject keywords
        has_attachment: Only emails with attachments
        label: Filter by label (inbox, sent, starred, etc.)
        is_unread: Only unread emails
        is_starred: Only starred emails
        is_important: Only important emails
        date_filter: Natural language date ("today", "last week", "this month")
        after: After date (YYYY/MM/DD)
        before: Before date (YYYY/MM/DD)
        keywords: General search keywords
        max_results: Max emails to return (default 10, max 50)
        include_body: Include email body (default True)
        include_attachments: Include attachment info (default True)
        body_format: "text" or "html" (default "text")
    """
    if not GMAIL_AVAILABLE:
        return json.dumps({
            "error": "Gmail libraries not installed. Install with: pip install google-auth google-auth-oauthlib google-api-python-client",
            "success": False
        })

    try:
        service = get_gmail_service()

        # Build query from structured args
        query = build_gmail_query(args)
        max_results = min(args.get("max_results", 10), 50)
        include_body = args.get("include_body", True)
        include_attachments = args.get("include_attachments", True)
        body_format = args.get("body_format", "text")

        print(f"   [GMAIL] Query: {query or 'all recent'}")

        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            return json.dumps({
                "emails": [],
                "count": 0,
                "message": "No emails found matching the criteria",
                "query_used": query or "recent emails",
                "success": True,
                "note": "EMAIL ACCESS SUCCESSFUL! The inbox was checked but no emails matched your search."
            })

        email_list = []
        for msg in messages:
            msg_data = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='full'
            ).execute()

            headers = msg_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
            to = next((h['value'] for h in headers if h['name'].lower() == 'to'), '')
            cc = next((h['value'] for h in headers if h['name'].lower() == 'cc'), '')
            reply_to = next((h['value'] for h in headers if h['name'].lower() == 'reply-to'), '')
            message_id = next((h['value'] for h in headers if h['name'].lower() == 'message-id'), '')

            # Get labels
            labels = msg_data.get('labelIds', [])
            is_unread = 'UNREAD' in labels
            is_starred = 'STARRED' in labels
            is_important = 'IMPORTANT' in labels

            email_info = {
                "id": msg['id'],
                "thread_id": msg_data.get('threadId', ''),
                "subject": subject,
                "from": sender,
                "to": to,
                "date": date,
                "snippet": msg_data.get('snippet', ''),
                "is_unread": is_unread,
                "is_starred": is_starred,
                "is_important": is_important,
                "labels": [l for l in labels if not l.startswith('CATEGORY_')]
            }

            if cc:
                email_info['cc'] = cc
            if reply_to:
                email_info['reply_to'] = reply_to

            # Include body
            if include_body:
                body, content_type = extract_email_body(
                    msg_data['payload'],
                    prefer_html=(body_format == "html")
                )
                email_info['body'] = body
                email_info['body_type'] = content_type

            # Include attachments info
            if include_attachments:
                attachments = extract_attachments_info(msg_data['payload'])
                if attachments:
                    email_info['attachments'] = [
                        {
                            'filename': a['filename'],
                            'type': a['mime_type'],
                            'size': format_email_size(a['size'])
                        }
                        for a in attachments
                    ]
                    email_info['attachment_count'] = len(attachments)

            email_list.append(email_info)

        # Summary stats
        unread_count = sum(1 for e in email_list if e.get('is_unread'))
        with_attachments = sum(1 for e in email_list if e.get('attachments'))

        return json.dumps({
            "emails": email_list,
            "count": len(email_list),
            "unread_count": unread_count,
            "with_attachments": with_attachments,
            "query_used": query if query else "recent emails",
            "success": True,
            "note": "EMAIL ACCESS SUCCESSFUL! The emails above are REAL data from the Gmail inbox."
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"Failed to read Gmail: {str(e)}",
            "success": False
        })


# ================================================================================
# SEND EMAIL - ENHANCED
# ================================================================================

def execute_send_gmail(args: Dict[str, Any], upload_folder: str = "uploads", documents_folder: str = "uploaded_documents") -> str:
    """
    Send an email via Gmail with HTML support and attachments.

    Args:
        to: Recipient email (required)
        subject: Email subject (required)
        body: Email body text
        html_body: HTML email body (if provided, creates multipart alternative)
        cc: CC recipients (comma separated)
        bcc: BCC recipients (comma separated)
        attachments: List of file paths to attach
        reply_to: Custom reply-to address
        priority: "high", "normal", or "low"
        save_draft: If True, saves as draft instead of sending
    """
    if not GMAIL_AVAILABLE:
        return json.dumps({
            "error": "Gmail libraries not installed. Install with: pip install google-auth google-auth-oauthlib google-api-python-client",
            "success": False
        })

    try:
        service = get_gmail_service()

        to = args.get("to", "")
        subject = args.get("subject", "")
        body = args.get("body", "")
        html_body = args.get("html_body", "")
        cc = args.get("cc", "")
        bcc = args.get("bcc", "")
        attachments = args.get("attachments", [])
        reply_to = args.get("reply_to", "")
        priority = args.get("priority", "normal")
        save_draft = args.get("save_draft", False)

        if not to or not subject:
            return json.dumps({
                "error": "Missing required email information. Need: recipient email address and subject.",
                "missing_to": not to,
                "missing_subject": not subject,
                "success": False
            })

        # Create message structure
        if html_body or attachments:
            message = MIMEMultipart('mixed')

            # Add body as multipart/alternative if both plain and HTML
            if html_body and body:
                body_part = MIMEMultipart('alternative')
                body_part.attach(MIMEText(body, 'plain', 'utf-8'))
                body_part.attach(MIMEText(html_body, 'html', 'utf-8'))
                message.attach(body_part)
            elif html_body:
                message.attach(MIMEText(html_body, 'html', 'utf-8'))
            else:
                message.attach(MIMEText(body, 'plain', 'utf-8'))
        else:
            message = MIMEMultipart()
            message.attach(MIMEText(body, 'plain', 'utf-8'))

        # Set headers
        message['To'] = to
        message['Subject'] = subject
        if cc:
            message['Cc'] = cc
        if bcc:
            message['Bcc'] = bcc
        if reply_to:
            message['Reply-To'] = reply_to

        # Priority headers
        if priority == "high":
            message['X-Priority'] = '1'
            message['X-MSMail-Priority'] = 'High'
            message['Importance'] = 'High'
        elif priority == "low":
            message['X-Priority'] = '5'
            message['X-MSMail-Priority'] = 'Low'
            message['Importance'] = 'Low'

        attached_files = []
        attachment_errors = []

        if attachments:
            print(f"   [ATTACH] Processing {len(attachments)} attachment(s)")

            for file_path in attachments:
                try:
                    file_path = str(file_path).strip()

                    # Try to find the file
                    if not os.path.exists(file_path):
                        # Try uploads folder
                        doc_path = os.path.join(upload_folder, file_path)
                        if os.path.exists(doc_path):
                            file_path = doc_path
                        else:
                            # Try documents folder
                            doc_path2 = os.path.join(documents_folder, file_path)
                            if os.path.exists(doc_path2):
                                file_path = doc_path2
                            else:
                                # Try just filename in uploads
                                basename = os.path.basename(file_path)
                                doc_path3 = os.path.join(upload_folder, basename)
                                if os.path.exists(doc_path3):
                                    file_path = doc_path3
                                else:
                                    attachment_errors.append(f"File not found: {file_path}")
                                    continue

                    file_size = os.path.getsize(file_path)
                    max_size = 25 * 1024 * 1024  # 25MB Gmail limit

                    if file_size > max_size:
                        attachment_errors.append(f"File too large (>{format_email_size(max_size)}): {os.path.basename(file_path)}")
                        continue

                    filename = os.path.basename(file_path)
                    mime_type, _ = mimetypes.guess_type(file_path)
                    if mime_type is None:
                        mime_type = 'application/octet-stream'
                    main_type, sub_type = mime_type.split('/', 1)

                    with open(file_path, 'rb') as f:
                        file_data = f.read()

                    # Handle images specially for potential inline display
                    if main_type == 'image':
                        attachment = MIMEImage(file_data, _subtype=sub_type)
                    else:
                        attachment = MIMEBase(main_type, sub_type)
                        attachment.set_payload(file_data)
                        encoders.encode_base64(attachment)

                    attachment.add_header('Content-Disposition', 'attachment', filename=filename)
                    message.attach(attachment)

                    attached_files.append({
                        'filename': filename,
                        'size': format_email_size(file_size),
                        'type': mime_type
                    })
                    print(f"   [ATTACH-OK] Attached: {filename} ({format_email_size(file_size)})")

                except Exception as e:
                    attachment_errors.append(f"Error attaching {os.path.basename(str(file_path))}: {str(e)}")

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        if save_draft:
            # Save as draft instead of sending
            draft = service.users().drafts().create(
                userId='me',
                body={'message': {'raw': raw_message}}
            ).execute()

            return json.dumps({
                "draft_id": draft['id'],
                "to": to,
                "subject": subject,
                "success": True,
                "message": f"Draft saved successfully",
                "note": "DRAFT CREATED! You can send it from Gmail."
            }, indent=2)

        # Send the email
        sent_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()

        result = {
            "message_id": sent_message['id'],
            "to": to,
            "subject": subject,
            "has_html": bool(html_body),
            "priority": priority,
            "success": True,
            "message": f"Email sent successfully to {to}",
            "confirmation": f"Email delivered to {to} with subject '{subject}'",
            "note": "EMAIL SENT SUCCESSFULLY!"
        }

        if cc:
            result['cc'] = cc
        if bcc:
            result['bcc'] = bcc
        if attached_files:
            result['attachments'] = attached_files
            result['attachments_count'] = len(attached_files)
        if attachment_errors:
            result['attachment_errors'] = attachment_errors

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"Failed to send email: {str(e)}",
            "success": False
        })


# ================================================================================
# REPLY EMAIL
# ================================================================================

def execute_reply_gmail(args: Dict[str, Any]) -> str:
    """Reply to Gmail messages."""
    if not GMAIL_AVAILABLE:
        return json.dumps({
            "error": "Gmail libraries not installed.",
            "success": False
        })

    try:
        service = get_gmail_service()

        query = args.get("query", "")
        reply_body = args.get("reply_body", "")
        reply_all = args.get("reply_all", False)
        max_replies = min(args.get("max_replies", 10), 50)

        if not query or not reply_body:
            return json.dumps({
                "error": "Missing required fields: 'query' and 'reply_body' are required",
                "success": False
            })

        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_replies if reply_all else 1
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            return json.dumps({
                "success": True,
                "replies_sent": 0,
                "message": f"No emails found matching query: {query}",
                "query": query
            })

        replies_sent = []
        errors = []

        for msg in messages:
            try:
                msg_data = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()

                headers = msg_data['payload']['headers']
                original_subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                original_from = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
                message_id_header = next((h['value'] for h in headers if h['name'].lower() == 'message-id'), '')

                email_body = ""
                if 'parts' in msg_data['payload']:
                    for part in msg_data['payload']['parts']:
                        if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                            email_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                            break
                elif 'body' in msg_data['payload'] and 'data' in msg_data['payload']['body']:
                    email_body = base64.urlsafe_b64decode(msg_data['payload']['body']['data']).decode('utf-8')

                email_match = re.search(r'<(.+?)>', original_from)
                reply_to = email_match.group(1) if email_match else original_from

                reply_subject = original_subject if original_subject.startswith('Re:') else f"Re: {original_subject}"

                reply_message = MIMEMultipart()
                reply_message['To'] = reply_to
                reply_message['Subject'] = reply_subject
                reply_message['In-Reply-To'] = message_id_header
                reply_message['References'] = message_id_header

                reply_message.attach(MIMEText(reply_body, 'plain'))

                raw_message = base64.urlsafe_b64encode(reply_message.as_bytes()).decode('utf-8')

                sent_message = service.users().messages().send(
                    userId='me',
                    body={
                        'raw': raw_message,
                        'threadId': msg_data.get('threadId')
                    }
                ).execute()

                replies_sent.append({
                    "original_subject": original_subject,
                    "replied_to": reply_to,
                    "reply_id": sent_message['id']
                })

            except Exception as e:
                errors.append({
                    "message_id": msg['id'],
                    "error": str(e)
                })

        return json.dumps({
            "success": True,
            "replies_sent": len(replies_sent),
            "query": query,
            "replies": replies_sent,
            "errors": errors if errors else None,
            "message": f"Successfully replied to {len(replies_sent)} email(s)",
            "note": "REPLIES SENT SUCCESSFULLY!"
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"Failed to reply to emails: {str(e)}",
            "success": False
        })


__all__ = [
    'GMAIL_AVAILABLE',
    'GMAIL_SCOPES',
    'get_gmail_service',
    'execute_read_gmail',
    'execute_send_gmail',
    'execute_reply_gmail',
]
