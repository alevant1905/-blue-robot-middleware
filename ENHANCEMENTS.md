# Blue Robot Middleware - Recent Enhancements

## Overview
This document describes the latest enhancements made to the Blue Robot Middleware system.

## Latest Session - 7 New Tools Added! 🚀

This enhancement session added **7 comprehensive new tools** to dramatically expand Blue's capabilities:

## New Tools Added (Latest Session)

### 1. Calendar & Events Tool (`blue/tools/calendar.py`)
A comprehensive calendar management system with event scheduling and conflict detection.

**Features:**
- Create, edit, and delete calendar events
- Support for recurring events (daily, weekly, monthly, yearly)
- Event reminders and notifications
- Calendar views (day, week, month)
- Event search and filtering
- Automatic conflict detection
- All-day events support
- Multiple event types (appointment, meeting, reminder, birthday, holiday, task)

**Usage Examples:**
```python
from blue.tools.calendar import create_event_cmd, list_events_cmd

# Create an event
create_event_cmd(
    title="Team Meeting",
    start_time="tomorrow at 2pm",
    duration_minutes=60,
    description="Weekly team sync",
    event_type="meeting"
)

# List upcoming events
list_events_cmd(days_ahead=7)
```

**Voice Commands:**
- "Create an event for tomorrow at 3pm"
- "What events do I have this week?"
- "Schedule a meeting for next Monday"
- "What's on my calendar today?"

---

### 2. Enhanced Weather Tool (`blue/tools/weather.py`)
Advanced weather information with multi-day forecasting and intelligent suggestions.

**Features:**
- Current weather conditions with detailed metrics
- Multi-day weather forecasts (up to 16 days)
- Hourly forecasts
- Weather-based suggestions (e.g., "Bring an umbrella")
- Location caching for faster responses
- Support for any location worldwide
- UV index, wind speed, precipitation, and more
- Temperature in both Celsius and Fahrenheit

**Usage Examples:**
```python
from blue.tools.weather import get_current_weather_cmd, get_forecast_cmd

# Get current weather
get_current_weather_cmd(location="London")

# Get 7-day forecast
get_forecast_cmd(location="New York", days=7)
```

**Voice Commands:**
- "What's the weather like?"
- "Will it rain tomorrow?"
- "Show me the forecast for this week"
- "What's the temperature in Paris?"

---

### 3. Automation & Routines Tool (`blue/tools/automation.py`)
Create and manage automation routines by chaining multiple actions together.

**Features:**
- Create custom routines with multiple actions
- Chain actions from different tools (music, lights, notifications, etc.)
- Conditional execution based on time and day
- Predefined routines (Good Morning, Bedtime, Focus Mode, Party Mode)
- Routine execution tracking and statistics
- Manual and scheduled triggers
- Action types: music, lights, notifications, timers, weather, email, notes, tasks, system

**Predefined Routines:**
- **Good Morning:** Check weather, turn on lights, play upbeat music, show calendar
- **Bedtime:** Dim lights, play relaxing music, set sleep timer
- **Focus Mode:** Play focus music, adjust lights, set 25-minute timer
- **Party Mode:** Party lights, party music, send notification

**Usage Examples:**
```python
from blue.tools.automation import execute_routine_cmd, install_predefined_routine

# Install predefined routine
install_predefined_routine("good_morning")

# Execute a routine
execute_routine_cmd(routine_id="...")
```

**Voice Commands:**
- "Run my good morning routine"
- "Start bedtime routine"
- "Activate focus mode"
- "Show my routines"

---

### 4. Media Library Tool (`blue/tools/media_library.py`)
Manage and organize podcasts, audiobooks, and playlists with playback tracking.

**Features:**
- Subscribe to podcasts and manage subscriptions
- Track listening progress for each episode
- Organize media into collections
- Playback history tracking
- Search across all media
- Mark episodes as played/unplayed
- Recently played items
- In-progress tracking

**Usage Examples:**
```python
from blue.tools.media_library import subscribe_podcast_cmd, list_subscriptions_cmd

# Subscribe to a podcast
subscribe_podcast_cmd(
    title="Tech Talk Daily",
    feed_url="https://example.com/feed.xml",
    description="Daily tech news"
)

# List all subscriptions
list_subscriptions_cmd(media_type="podcast")
```

**Voice Commands:**
- "Subscribe to Tech Talk podcast"
- "Show me my podcasts"
- "What new episodes do I have?"
- "Search for episodes about AI"
- "What was I listening to?"

---

## Technical Implementation

### Database Schema
Each new tool uses SQLite databases for persistent storage:
- `data/calendar.db` - Calendar events
- `data/weather_cache.db` - Weather data cache
- `data/automation.db` - Automation routines and execution logs
- `data/media_library.db` - Media subscriptions and playback history

### Tool Selector Integration
The `ImprovedToolSelector` in `blue/tool_selector.py` has been updated with new intent detection methods:
- `_detect_calendar_intents()` - Recognizes calendar-related requests
- `_detect_weather_intents()` - Recognizes weather queries with forecast support
- `_detect_automation_intents()` - Recognizes routine execution and management
- `_detect_media_library_intents()` - Recognizes podcast and media queries

### Module Structure
All new tools follow the established pattern:
```
blue/tools/
├── calendar.py          # Calendar & events
├── weather.py           # Enhanced weather
├── automation.py        # Routines & automation
└── media_library.py     # Media library management
```

---

## API Integration

### Weather API
The weather tool uses the **Open-Meteo API** (https://open-meteo.com/):
- Free, no API key required
- Accurate weather data worldwide
- Up to 16-day forecasts
- Geocoding support for location search

### Geocoding
Location names are automatically converted to coordinates using Open-Meteo's geocoding API.

---

## Configuration

### Environment Variables
You can customize database locations:
```bash
export BLUE_CALENDAR_DB="path/to/calendar.db"
export BLUE_WEATHER_CACHE_DB="path/to/weather_cache.db"
export BLUE_AUTOMATION_DB="path/to/automation.db"
export BLUE_MEDIA_LIBRARY_DB="path/to/media_library.db"
```

### Cache Settings
Weather data is cached for 30 minutes by default to reduce API calls.

---

## Dependencies

### Required
- `requests` - For API calls (already included)
- `sqlite3` - Built-in with Python

### Optional
None - all new tools use standard library packages.

---

## Future Enhancements

### Calendar
- [ ] Google Calendar integration
- [ ] iCal import/export
- [ ] Smart scheduling suggestions
- [ ] Meeting link generation

### Weather
- [ ] Weather alerts and warnings
- [ ] Historical weather data
- [ ] Weather-based automation triggers
- [ ] Multiple location tracking

### Automation
- [ ] Location-based triggers
- [ ] Voice command triggers
- [ ] Complex conditional logic
- [ ] Routine templates marketplace

### Media Library
- [ ] Podcast RSS feed parsing
- [ ] Automatic episode downloads
- [ ] Smart recommendations
- [ ] Playback speed control
- [ ] Chapter markers

---

## Testing

To test the new tools:

```bash
# Test imports
python -c "from blue.tools import calendar, weather, automation, media_library"

# Test tool selector
python -c "
from blue.tool_selector import ImprovedToolSelector
selector = ImprovedToolSelector()
result = selector.select_tool('What events do I have today?', [])
print(result.primary_tool.tool_name if result.primary_tool else 'None')
"
```

---

## Migration Notes

### Backward Compatibility
All existing tools remain unchanged. New tools are additive only.

### Database Migration
New databases are created automatically on first use. No migration needed.

### 5. Location Management Tool (`blue/tools/locations.py`)
Manage favorite places and locations with geocoding and distance calculations.

**Features:**
- Save favorite locations with custom names and categories
- Automatic geocoding from addresses
- Location categories (home, work, restaurant, gym, etc.)
- Distance calculations between locations
- Visit tracking and history
- Search and filter saved locations
- Quick access to frequently visited places

**Usage Examples:**
```python
from blue.tools.locations import add_location_cmd, list_locations_cmd

# Add a location
add_location_cmd(
    name="Favorite Coffee Shop",
    address="123 Main St, Seattle, WA",
    category="restaurant",
    favorite=True
)

# List saved locations
list_locations_cmd(category="restaurant")
```

**Voice Commands:**
- "Save this location as home"
- "Show me my saved places"
- "Find restaurant locations"
- "Log visit to coffee shop"

---

### 6. Contact Management Tool (`blue/tools/contacts.py`)
Comprehensive contact management with communication tracking.

**Features:**
- Store contacts with complete information (email, phone, address, birthday, etc.)
- Contact categories (personal, work, family, friend, business)
- Birthday reminders with upcoming birthday tracking
- Communication history logging
- Quick search by name, email, or phone
- Tag and categorize contacts
- Favorite contacts
- Link contacts to face recognition data

**Usage Examples:**
```python
from blue.tools.contacts import add_contact_cmd, upcoming_birthdays_cmd

# Add a contact
add_contact_cmd(
    name="John Doe",
    email="john@example.com",
    phone="+1234567890",
    contact_type="friend",
    favorite=True
)

# Check upcoming birthdays
upcoming_birthdays_cmd(days=30)
```

**Voice Commands:**
- "Add new contact John Doe"
- "Show my contacts"
- "Who has a birthday coming up?"
- "Find contact with email john@example.com"
- "Show my favorite contacts"

---

### 7. Habit Tracking Tool (`blue/tools/habits.py`)
Track daily habits, build streaks, and achieve personal goals.

**Features:**
- Create habits with daily, weekly, or custom frequencies
- Automatic streak counting
- Best streak tracking
- Completion statistics and analytics
- Habit categories (health, fitness, learning, productivity, etc.)
- Target count per day/week
- Reminder times for habits
- 30-day completion rate tracking
- Visual progress tracking

**Usage Examples:**
```python
from blue.tools.habits import create_habit_cmd, complete_habit_cmd

# Create a habit
create_habit_cmd(
    name="Morning Meditation",
    description="Meditate for 10 minutes",
    frequency="daily",
    category="mindfulness"
)

# Complete a habit
complete_habit_cmd(habit_name="Morning Meditation")
```

**Voice Commands:**
- "Track new habit: daily exercise"
- "I completed my workout"
- "Show my habits for today"
- "What's my meditation streak?"
- "Show habit statistics"

---

## Version History

### v10.0.0 (2025-12-10)
- **Second Enhancement Session:**
  - Added Location Management tool
  - Added Contact Management tool with birthday tracking
  - Added Habit Tracking tool with streak counting
  - Updated tool selector with 3 new intent detectors
  - Updated tools package exports

### v9.0.0 (2025-12-10)
- **First Enhancement Session:**
  - Added Calendar & Events tool
  - Added Enhanced Weather tool with forecasting
  - Added Automation & Routines tool
  - Added Media Library tool
  - Updated tool selector with 4 new intent detectors
  - Updated tools package exports

---

## Support

For issues or questions about the new enhancements, please check:
1. This documentation file
2. Individual tool docstrings in source files
3. The main README.md for general Blue setup

---

## Credits

Enhancements developed for Blue Robot Middleware v9.0.0
