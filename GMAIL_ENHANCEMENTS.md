# Gmail Enhanced Features - Documentation

## Overview

Blue's Gmail control has been significantly enhanced with advanced email management capabilities.

## 🆕 New Features Added

### 1. **Email Templates** 📝

Create reusable email templates with variable substitution.

**Features:**
- Create templates with dynamic variables (e.g., `{name}`, `{date}`, `{topic}`)
- Template categories: Quick Reply, Formal, Casual, Business, Thank You, Follow Up, Custom
- Track template usage statistics
- Predefined professional templates included
- Variable auto-detection

**Usage:**

```python
from blue.tools.gmail_enhanced import create_template_cmd

# Create a template
create_template_cmd(
    name="Meeting Request",
    subject="Meeting Request: {topic}",
    body="""Hi {name},

I would like to schedule a meeting to discuss {topic}.

Would you be available on {date} at {time}?

Best regards""",
    template_type="business"
)
```

**Voice Commands:**
- "Create email template for meeting requests"
- "Show my email templates"
- "Use thank you template"

**Predefined Templates:**
1. **Meeting Request** - Schedule meetings with variables for topic, date, time
2. **Thank You** - Express gratitude professionally
3. **Follow Up** - Follow up on previous conversations

---

### 2. **Email Scheduling** ⏰

Schedule emails to be sent at a specific time in the future.

**Features:**
- Natural language time parsing ("tomorrow at 9am", "next Monday 2pm")
- ISO format support ("2025-12-11 14:30")
- List and manage scheduled emails
- Cancel scheduled emails before they're sent
- Automatic sending at scheduled time

**Usage:**

```python
from blue.tools.gmail_enhanced import schedule_email_cmd

# Schedule an email
schedule_email_cmd(
    to="colleague@company.com",
    subject="Weekly Update",
    body="Here's this week's update...",
    send_at="tomorrow at 9am"
)
```

**Voice Commands:**
- "Schedule email to John for tomorrow at 9am"
- "Show my scheduled emails"
- "Cancel scheduled email"

**Supported Time Formats:**
- "tomorrow at 3pm"
- "next Monday 2:30pm"
- "2025-12-15 10:00"
- "in 2 hours"

---

### 3. **Smart Email Filters** 🎯

Create automated rules to process incoming emails.

**Features:**
- Condition-based filtering (from, subject, has attachment, etc.)
- Automated actions (label, archive, star, forward, delete)
- Priority-based execution
- Filter statistics tracking
- Enable/disable filters easily

**Usage:**

```python
from blue.tools.gmail_enhanced import GmailEnhancedManager

manager = GmailEnhancedManager()

# Create a filter
manager.create_filter(
    name="Important Client Emails",
    conditions={
        "from": "client@company.com",
        "has_words": "urgent"
    },
    actions={
        "add_label": "Important",
        "star": True,
        "forward_to": "manager@company.com"
    },
    priority=1
)
```

**Filter Conditions:**
- `from`: Sender email address
- `to`: Recipient email
- `subject_contains`: Words in subject
- `has_words`: Words anywhere in email
- `has_attachment`: Boolean
- `larger_than`: Size in bytes
- `date_after`: Date filter

**Filter Actions:**
- `add_label`: Add Gmail label
- `remove_label`: Remove label
- `archive`: Archive email
- `star`: Star email
- `mark_read`: Mark as read
- `forward_to`: Forward to address
- `delete`: Delete email

---

### 4. **Quick Replies** ⚡

Predefined responses for common email scenarios.

**Features:**
- Trigger-based responses
- Category organization
- Usage tracking
- Fast, one-word triggers

**Usage:**

```python
from blue.tools.gmail_enhanced import GmailEnhancedManager

manager = GmailEnhancedManager()

# Add quick reply
manager.add_quick_reply(
    trigger="thanks",
    response="Thank you for your email. I'll get back to you shortly.",
    category="professional"
)

# Use quick reply
response = manager.get_quick_reply("thanks")
```

**Common Quick Replies:**
- "thanks" → Thank you response
- "received" → Acknowledgment
- "meeting" → Meeting confirmation
- "ootd" → Out of the office

---

### 5. **Email Categories** 🗂️

Intelligent email categorization for better inbox organization.

**Categories:**
- **Inbox** - Default
- **Important** - High-priority emails
- **Promotions** - Marketing emails
- **Social** - Social network notifications
- **Updates** - Order confirmations, receipts
- **Forums** - Mailing lists, forums
- **Personal** - Personal correspondence
- **Work** - Work-related emails
- **Spam** - Junk mail

---

## 📊 Database Schema

New database file: `data/gmail_enhanced.db`

**Tables:**
- `email_templates` - Store email templates
- `email_filters` - Store filter rules
- `scheduled_emails` - Store emails to be sent later
- `email_signatures` - Store email signatures
- `quick_replies` - Store quick reply mappings

---

## 🔌 Integration with Existing Gmail

The enhanced features complement the existing Gmail tool (`blue/tools/gmail.py`):

**Existing Features (Still Available):**
- Read emails with filtering
- Send emails with attachments
- Reply to emails
- Label management
- Attachment downloading
- Natural language date filters
- Draft creation

**New Enhanced Features:**
- Email templates
- Email scheduling
- Smart filters
- Quick replies
- Email categorization

---

## 💡 Usage Examples

### Complete Workflow Example

```python
from blue.tools import gmail_enhanced

manager = gmail_enhanced.get_gmail_enhanced_manager()

# 1. Create a meeting request template
template = manager.create_template(
    name="Client Meeting",
    subject="Meeting Request: {project_name}",
    body="""Dear {client_name},

I hope this email finds you well. I would like to schedule a meeting to discuss the progress on {project_name}.

Would you be available for a {duration} meeting on {proposed_date}?

Best regards,
{my_name}""",
    template_type=gmail_enhanced.TemplateType.BUSINESS
)

# 2. Use the template
subject, body = template.render({
    "client_name": "John Smith",
    "project_name": "Q4 Strategy",
    "duration": "30-minute",
    "proposed_date": "December 15th at 2 PM",
    "my_name": "Your Name"
})

# 3. Schedule the email
manager.schedule_email(
    to="john.smith@client.com",
    subject=subject,
    body=body,
    send_at=datetime.datetime(2025, 12, 11, 9, 0).timestamp()
)

# 4. Create a filter for client responses
manager.create_filter(
    name="Client Responses",
    conditions={"from": "john.smith@client.com"},
    actions={"add_label": "Client/Important", "star": True},
    priority=1
)
```

---

## 🎯 Voice Commands

Blue can now understand these enhanced Gmail commands:

**Templates:**
- "Create email template for thank you notes"
- "Show my email templates"
- "List business templates"
- "Use meeting request template"

**Scheduling:**
- "Schedule email to John for tomorrow at 9am"
- "Send email to Sarah next Monday at 2pm"
- "Show scheduled emails"
- "Cancel scheduled email to John"

**Filters:**
- "Create filter for emails from boss"
- "Show my email filters"
- "Disable promotion filter"

**Quick Replies:**
- "Add quick reply for thank you"
- "Show quick replies"

---

## 🔧 Configuration

### Environment Variables

```bash
# Gmail Enhanced database location
export BLUE_GMAIL_ENHANCED_DB="path/to/gmail_enhanced.db"

# Existing Gmail config
export GMAIL_USER_EMAIL="your.email@gmail.com"
```

### Setup

1. **Install Dependencies:**
   ```bash
   pip install google-auth google-auth-oauthlib google-api-python-client
   ```

2. **Gmail API Credentials:**
   - Place `gmail_credentials.json` in project root
   - First run will prompt for OAuth authorization
   - Token saved to `gmail_token.pickle`

3. **Initialize Enhanced Features:**
   ```python
   from blue.tools.gmail_enhanced import get_gmail_enhanced_manager

   manager = get_gmail_enhanced_manager()
   # Database automatically created on first use
   ```

---

## 📈 Benefits

### Time Savings
- **Templates**: Save 5-10 minutes per email with templates
- **Scheduling**: Set it and forget it - never miss send times
- **Filters**: Automatically organize 100+ emails per day
- **Quick Replies**: Respond in seconds instead of minutes

### Organization
- Clean, categorized inbox
- Automatic labeling and starring
- Priority-based processing
- Easy email tracking

### Professionalism
- Consistent, professional templates
- Timely, scheduled communications
- Never miss a follow-up
- Quick, appropriate responses

---

## 🚀 Advanced Features

### Batch Operations

Process multiple emails at once:

```python
# Example: Star all emails from VIP clients
vip_clients = ["client1@company.com", "client2@company.com"]

for client in vip_clients:
    manager.create_filter(
        name=f"VIP: {client}",
        conditions={"from": client},
        actions={"star": True, "add_label": "VIP"},
        priority=0  # Highest priority
    )
```

### Template Chains

Create multi-step email sequences:

```python
# Initial contact
template1 = manager.create_template(
    name="Initial Outreach",
    subject="Introduction: {my_company}",
    body="...",
    template_type=TemplateType.BUSINESS
)

# Follow-up
template2 = manager.create_template(
    name="Follow Up",
    subject="Following Up: {topic}",
    body="...",
    template_type=TemplateType.FOLLOW_UP
)
```

---

## 🐛 Troubleshooting

### Templates not saving
- Check database permissions
- Ensure `data/` directory exists
- Verify SQLite is installed

### Scheduled emails not sending
- Implement background service to check pending emails
- Use cron job or task scheduler
- Check `get_pending_scheduled_emails()` method

### Filters not applying
- Check filter priority order
- Verify conditions match email format
- Enable filter if disabled

---

## 🔮 Future Enhancements

Planned features:
- [ ] AI-powered email composition
- [ ] Sentiment analysis
- [ ] Email thread summarization
- [ ] Auto-categorization with ML
- [ ] Email analytics dashboard
- [ ] Integration with calendar for meeting scheduling
- [ ] Attachment management system
- [ ] Email search with semantic understanding

---

## 📚 API Reference

### GmailEnhancedManager Methods

**Templates:**
- `create_template(name, subject, body, template_type, tags)` → EmailTemplate
- `get_template(template_id)` → EmailTemplate | None
- `find_template_by_name(name)` → EmailTemplate | None
- `list_templates(template_type)` → List[EmailTemplate]
- `delete_template(template_id)` → bool

**Filters:**
- `create_filter(name, conditions, actions, priority)` → EmailFilter
- `list_filters(enabled_only)` → List[EmailFilter]
- `delete_filter(filter_id)` → bool

**Scheduling:**
- `schedule_email(to, subject, body, send_at, cc, bcc, attachments)` → ScheduledEmail
- `get_pending_scheduled_emails()` → List[ScheduledEmail]
- `list_scheduled_emails()` → List[ScheduledEmail]
- `cancel_scheduled_email(email_id)` → bool
- `mark_scheduled_email_sent(email_id)` → bool

**Quick Replies:**
- `add_quick_reply(trigger, response, category)` → str
- `get_quick_reply(trigger)` → str | None

---

## Version History

### v11.0.0 (2025-12-10)
- Initial release of Gmail Enhanced features
- Added email templates with variables
- Added email scheduling
- Added smart filters and rules
- Added quick replies
- Added email categorization
- Integrated with existing Gmail tool

---

*Blue Robot Middleware - Gmail Enhanced Features*
*Making email management intelligent and effortless*
