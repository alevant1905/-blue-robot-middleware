"""
Blue Robot Gmail Bulk Operations
=================================
Efficient bulk email operations and management.

Features:
- Bulk label management (add/remove labels to multiple emails)
- Bulk archive/delete operations
- Smart cleanup (old promotions, social emails, etc.)
- Email deduplication
- Attachment management (find, download, organize)
- Bulk mark as read/unread
- Sender management (mute, block, unsubscribe)
"""

from __future__ import annotations

import datetime
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

# ================================================================================
# BULK OPERATIONS MANAGER
# ================================================================================

class GmailBulkManager:
    """Manages bulk email operations."""

    def __init__(self):
        self.stats = {
            "modified": 0,
            "archived": 0,
            "deleted": 0,
            "labeled": 0,
            "errors": 0
        }

    def bulk_label(self, service, query: str, add_labels: List[str] = None,
                   remove_labels: List[str] = None, max_emails: int = 100) -> Dict[str, Any]:
        """Apply label operations to multiple emails matching query."""
        add_labels = add_labels or []
        remove_labels = remove_labels or []

        if not add_labels and not remove_labels:
            return {"error": "No label operations specified", "success": False}

        try:
            # Get messages matching query
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_emails
            ).execute()

            messages = results.get('messages', [])
            if not messages:
                return {
                    "success": True,
                    "modified": 0,
                    "message": "No emails found matching query"
                }

            # Convert label names to IDs
            labels_list = service.users().labels().list(userId='me').execute()
            label_map = {label['name']: label['id'] for label in labels_list.get('labels', [])}

            add_label_ids = [label_map.get(name, name) for name in add_labels]
            remove_label_ids = [label_map.get(name, name) for name in remove_labels]

            # Apply labels in batches
            batch_size = 50
            modified = 0

            for i in range(0, len(messages), batch_size):
                batch = messages[i:i+batch_size]
                message_ids = [msg['id'] for msg in batch]

                body = {
                    'ids': message_ids,
                    'addLabelIds': add_label_ids if add_labels else [],
                    'removeLabelIds': remove_label_ids if remove_labels else []
                }

                service.users().messages().batchModify(
                    userId='me',
                    body=body
                ).execute()

                modified += len(message_ids)

            return {
                "success": True,
                "modified": modified,
                "query": query,
                "labels_added": add_labels,
                "labels_removed": remove_labels,
                "message": f"Successfully modified {modified} emails"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def bulk_archive(self, service, query: str, max_emails: int = 100) -> Dict[str, Any]:
        """Archive multiple emails matching query."""
        return self.bulk_label(
            service,
            query,
            add_labels=[],
            remove_labels=['INBOX'],
            max_emails=max_emails
        )

    def bulk_mark_read(self, service, query: str, mark_read: bool = True,
                       max_emails: int = 100) -> Dict[str, Any]:
        """Mark multiple emails as read or unread."""
        label_op = 'remove' if mark_read else 'add'

        return self.bulk_label(
            service,
            query,
            add_labels=[] if mark_read else ['UNREAD'],
            remove_labels=['UNREAD'] if mark_read else [],
            max_emails=max_emails
        )

    def smart_cleanup(self, service, older_than_days: int = 30,
                     categories: List[str] = None) -> Dict[str, Any]:
        """
        Smart cleanup of old emails from specific categories.

        Args:
            older_than_days: Archive emails older than this many days
            categories: List of categories to clean (promotions, social, updates, forums)
        """
        categories = categories or ['promotions', 'social']
        results = []

        for category in categories:
            query = f"category:{category} older_than:{older_than_days}d"

            result = self.bulk_archive(service, query, max_emails=500)
            results.append({
                "category": category,
                "archived": result.get('modified', 0)
            })

        total_archived = sum(r['archived'] for r in results)

        return {
            "success": True,
            "total_archived": total_archived,
            "by_category": results,
            "message": f"Archived {total_archived} old emails"
        }

    def find_large_emails(self, service, size_mb: int = 10,
                         max_results: int = 50) -> Dict[str, Any]:
        """Find emails with large attachments."""
        try:
            size_bytes = size_mb * 1024 * 1024
            query = f"size:{size_bytes} has:attachment"

            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            large_emails = []

            for msg in messages:
                msg_data = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['Subject', 'From', 'Date']
                ).execute()

                headers = msg_data['payload']['headers']
                size_estimate = msg_data.get('sizeEstimate', 0)

                large_emails.append({
                    "id": msg['id'],
                    "subject": next((h['value'] for h in headers if h['name'] == 'Subject'), ''),
                    "from": next((h['value'] for h in headers if h['name'] == 'From'), ''),
                    "size_mb": round(size_estimate / (1024 * 1024), 2)
                })

            total_size = sum(e['size_mb'] for e in large_emails)

            return {
                "success": True,
                "count": len(large_emails),
                "total_size_mb": round(total_size, 2),
                "emails": large_emails,
                "message": f"Found {len(large_emails)} large emails ({total_size:.1f} MB total)"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def unsubscribe_from_sender(self, service, sender_email: str,
                                archive_existing: bool = True) -> Dict[str, Any]:
        """
        Unsubscribe from sender and optionally archive existing emails.
        """
        try:
            # Create filter to automatically archive future emails
            filter_criteria = {
                "from": sender_email
            }

            filter_action = {
                "removeLabelIds": ["INBOX"],
                "addLabelIds": []
            }

            filter_body = {
                "criteria": filter_criteria,
                "action": filter_action
            }

            service.users().settings().filters().create(
                userId='me',
                body=filter_body
            ).execute()

            archived = 0
            if archive_existing:
                query = f"from:{sender_email}"
                result = self.bulk_archive(service, query, max_emails=500)
                archived = result.get('modified', 0)

            return {
                "success": True,
                "sender": sender_email,
                "filter_created": True,
                "existing_archived": archived,
                "message": f"Unsubscribed from {sender_email} and archived {archived} existing emails"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def deduplicate_emails(self, service, query: str = "",
                          max_emails: int = 200) -> Dict[str, Any]:
        """
        Find and optionally remove duplicate emails based on Message-ID.
        """
        try:
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_emails
            ).execute()

            messages = results.get('messages', [])
            seen_message_ids = {}
            duplicates = []

            for msg in messages:
                msg_data = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['Message-ID', 'Subject']
                ).execute()

                headers = msg_data['payload']['headers']
                message_id = next((h['value'] for h in headers if h['name'] == 'Message-ID'), None)

                if message_id:
                    if message_id in seen_message_ids:
                        duplicates.append({
                            "id": msg['id'],
                            "message_id": message_id,
                            "subject": next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                        })
                    else:
                        seen_message_ids[message_id] = msg['id']

            return {
                "success": True,
                "total_checked": len(messages),
                "duplicates_found": len(duplicates),
                "duplicates": duplicates,
                "message": f"Found {len(duplicates)} duplicate emails out of {len(messages)} checked"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# ================================================================================
# ATTACHMENT MANAGER
# ================================================================================

class AttachmentManager:
    """Manages email attachments."""

    def __init__(self, download_folder: str = "downloads/attachments"):
        self.download_folder = download_folder
        os.makedirs(download_folder, exist_ok=True)

    def find_attachments_by_type(self, service, file_type: str,
                                 max_emails: int = 50) -> Dict[str, Any]:
        """
        Find attachments by file type.

        Args:
            file_type: e.g., 'pdf', 'xlsx', 'jpg', 'zip'
        """
        try:
            query = f"has:attachment filename:{file_type}"

            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_emails
            ).execute()

            messages = results.get('messages', [])
            attachments = []

            for msg in messages:
                msg_data = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()

                headers = msg_data['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '')

                # Extract attachment info
                parts = msg_data['payload'].get('parts', [])
                for part in parts:
                    filename = part.get('filename', '')
                    if filename and file_type.lower() in filename.lower():
                        attachments.append({
                            "email_id": msg['id'],
                            "subject": subject,
                            "from": sender,
                            "filename": filename,
                            "mime_type": part.get('mimeType', ''),
                            "size": part['body'].get('size', 0),
                            "attachment_id": part['body'].get('attachmentId', '')
                        })

            return {
                "success": True,
                "count": len(attachments),
                "file_type": file_type,
                "attachments": attachments,
                "message": f"Found {len(attachments)} {file_type} attachments"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def download_attachment(self, service, email_id: str, attachment_id: str,
                           filename: str) -> Dict[str, Any]:
        """Download a specific attachment."""
        try:
            import base64

            attachment = service.users().messages().attachments().get(
                userId='me',
                messageId=email_id,
                id=attachment_id
            ).execute()

            file_data = base64.urlsafe_b64decode(attachment['data'])
            file_path = os.path.join(self.download_folder, filename)

            # Ensure unique filename
            counter = 1
            base, ext = os.path.splitext(filename)
            while os.path.exists(file_path):
                file_path = os.path.join(self.download_folder, f"{base}_{counter}{ext}")
                counter += 1

            with open(file_path, 'wb') as f:
                f.write(file_data)

            return {
                "success": True,
                "filename": filename,
                "path": file_path,
                "size": len(file_data),
                "message": f"Downloaded {filename} to {file_path}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# ================================================================================
# GLOBAL INSTANCES
# ================================================================================

_bulk_manager: Optional[GmailBulkManager] = None
_attachment_manager: Optional[AttachmentManager] = None


def get_bulk_manager() -> GmailBulkManager:
    """Get or create bulk manager instance."""
    global _bulk_manager
    if _bulk_manager is None:
        _bulk_manager = GmailBulkManager()
    return _bulk_manager


def get_attachment_manager() -> AttachmentManager:
    """Get or create attachment manager instance."""
    global _attachment_manager
    if _attachment_manager is None:
        _attachment_manager = AttachmentManager()
    return _attachment_manager


# ================================================================================
# COMMAND FUNCTIONS
# ================================================================================

def bulk_archive_cmd(query: str, max_emails: int = 100) -> str:
    """Archive emails matching query."""
    try:
        from blue.tools.gmail import get_gmail_service

        service = get_gmail_service()
        manager = get_bulk_manager()

        result = manager.bulk_archive(service, query, max_emails)

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


def smart_cleanup_cmd(older_than_days: int = 30,
                     categories: str = "promotions,social") -> str:
    """Clean up old emails from specific categories."""
    try:
        from blue.tools.gmail import get_gmail_service

        service = get_gmail_service()
        manager = get_bulk_manager()

        category_list = [c.strip() for c in categories.split(',')]
        result = manager.smart_cleanup(service, older_than_days, category_list)

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


def find_large_emails_cmd(size_mb: int = 10, max_results: int = 50) -> str:
    """Find emails with large attachments."""
    try:
        from blue.tools.gmail import get_gmail_service

        service = get_gmail_service()
        manager = get_bulk_manager()

        result = manager.find_large_emails(service, size_mb, max_results)

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


def unsubscribe_cmd(sender_email: str, archive_existing: bool = True) -> str:
    """Unsubscribe from sender."""
    try:
        from blue.tools.gmail import get_gmail_service

        service = get_gmail_service()
        manager = get_bulk_manager()

        result = manager.unsubscribe_from_sender(service, sender_email, archive_existing)

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


__all__ = [
    'GmailBulkManager',
    'AttachmentManager',
    'get_bulk_manager',
    'get_attachment_manager',
    'bulk_archive_cmd',
    'smart_cleanup_cmd',
    'find_large_emails_cmd',
    'unsubscribe_cmd',
]
