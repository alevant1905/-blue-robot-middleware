# Blue Robot Middleware 🤖

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-11.0.0-green.svg)](https://github.com/yourusername/blue-robot-middleware)

A comprehensive personal assistant middleware system with advanced AI capabilities, smart home integration, and productivity tools.

## 🌟 Features

Blue Robot Middleware is a modular, extensible platform that provides:

### 🎯 Personal Management
- **Calendar & Events** - Full event management with conflict detection
- **Contact Management** - Comprehensive contact database with birthday tracking
- **Habit Tracking** - Build streaks and achieve goals
- **Notes & Tasks** - Organize thoughts and to-dos
- **Timers & Reminders** - Never miss important moments

### 📧 Email & Communication
- **Gmail Integration** - Read, send, reply with smart features
- **Email Templates** - Reusable templates with variables
- **Email Scheduling** - Send emails at the perfect time
- **Smart Filters** - Automatic email organization
- **Quick Replies** - One-word triggers for responses

### 🏠 Smart Home
- **Philips Hue Control** - Full lighting control
- **Mood Presets** - Pre-configured scenes
- **Location Management** - Save and track favorite places
- **Automation Routines** - Chain multiple actions together

### 🎵 Entertainment
- **YouTube Music** - Play and control music
- **Media Library** - Manage podcasts and audiobooks
- **Music Visualizer** - Visual feedback for playback

### 🤖 AI & Recognition
- **Face Recognition** - Identify people in photos
- **Place Recognition** - Remember locations
- **Vision System** - Camera integration
- **Natural Language** - Conversational interface

### 🌤️ Information
- **Weather Forecasting** - 16-day forecasts with suggestions
- **Web Search** - Integrated search capabilities
- **Document Management** - RAG-based document search

### ⚙️ System Control
- **Clipboard Management** - Copy/paste automation
- **Screenshots** - Capture and manage screenshots
- **Application Launching** - Voice-controlled app opening
- **Volume Control** - System audio management

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.8 or higher
python --version

# pip package manager
pip --version
```

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/blue-robot-middleware.git
cd blue-robot-middleware
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure services (optional):**
```bash
# Gmail (for email features)
# Place gmail_credentials.json in project root

# Philips Hue (for smart lights)
# Edit hue_config.json with your bridge IP and username

# YouTube Music (for music features)
pip install ytmusicapi
```

4. **Run Blue:**
```bash
python run.py
```

## 📖 Usage

### Basic Commands

```python
# Via Python API
from blue import tools

# Send an email using template
template = tools.create_template_cmd(
    name="Meeting Request",
    subject="Let's meet about {topic}",
    body="Hi {name}, ..."
)

# Track a habit
tools.create_habit_cmd(
    name="Morning Meditation",
    description="10 minutes of mindfulness",
    frequency="daily"
)

# Schedule an event
tools.create_event_cmd(
    title="Team Meeting",
    start_time="tomorrow at 2pm",
    duration_minutes=60
)
```

### Voice Commands

Blue understands natural language:

- "What's the weather forecast for this week?"
- "Schedule email to John for tomorrow at 9am"
- "I completed my workout"
- "Show my contacts"
- "Run good morning routine"
- "Create an event for Friday at 3pm"

## 🏗️ Architecture

```
blue-robot-middleware/
├── blue/                      # Core package
│   ├── __init__.py           # Package exports
│   ├── utils.py              # Utility functions
│   ├── memory.py             # Memory & facts system
│   ├── llm.py                # LLM client
│   ├── tool_selector.py      # Intent detection
│   └── tools/                # Tool implementations
│       ├── calendar.py       # Calendar & events
│       ├── contacts.py       # Contact management
│       ├── habits.py         # Habit tracking
│       ├── gmail.py          # Gmail integration
│       ├── gmail_enhanced.py # Advanced Gmail features
│       ├── weather.py        # Weather forecasting
│       ├── automation.py     # Routines & automation
│       ├── media_library.py  # Podcast management
│       ├── locations.py      # Place management
│       ├── music.py          # Music playback
│       ├── lights.py         # Smart home control
│       ├── vision.py         # Camera & vision
│       ├── recognition.py    # Face/place recognition
│       ├── documents.py      # Document management
│       ├── web.py            # Web search
│       ├── notes.py          # Notes & tasks
│       ├── timers.py         # Timers & reminders
│       ├── system.py         # System control
│       └── utilities.py      # Misc utilities
├── data/                     # SQLite databases
├── run.py                    # Main entry point
├── bluetools.py              # Legacy compatibility
├── requirements.txt          # Python dependencies
└── config.py                 # Configuration

```

## 📊 Database Schema

Blue uses SQLite for persistent storage:

| Database | Purpose |
|----------|---------|
| `blue.db` | Core facts and memory |
| `calendar.db` | Events and schedules |
| `contacts.db` | Contact information |
| `habits.db` | Habit tracking data |
| `gmail_enhanced.db` | Email templates & filters |
| `weather_cache.db` | Weather data cache |
| `automation.db` | Routines and automations |
| `media_library.db` | Podcasts and media |
| `locations.db` | Saved places |
| `notes.db` | Notes and tasks |
| `timers.db` | Timers and reminders |
| `recognition.db` | Face/place recognition data |

## 🛠️ Configuration

### Environment Variables

```bash
# LLM Configuration
export LM_STUDIO_URL="http://localhost:1234/v1/chat/completions"
export LM_STUDIO_MODEL="your-model-name"

# Gmail
export GMAIL_USER_EMAIL="your.email@gmail.com"

# Database Locations (optional)
export BLUE_CALENDAR_DB="path/to/calendar.db"
export BLUE_CONTACTS_DB="path/to/contacts.db"
# ... etc
```

### Gmail Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Download as `gmail_credentials.json`
6. Place in project root
7. Run Blue - it will prompt for authorization

### Philips Hue Setup

1. Find your bridge IP address
2. Press the bridge button
3. Run Blue's Hue discovery
4. Save credentials to `hue_config.json`

## 📚 Documentation

- **[Enhancements Guide](ENHANCEMENTS.md)** - Complete feature documentation
- **[Gmail Enhanced](GMAIL_ENHANCEMENTS.md)** - Advanced email features
- **[Latest Updates](LATEST_UPDATES.md)** - Recent changes and new features
- **[API Reference](docs/)** - Detailed API documentation

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install pytest black mypy

# Run tests
pytest

# Format code
black blue/

# Type checking
mypy blue/
```

## 🗺️ Roadmap

### Planned Features

- [ ] Multi-language support
- [ ] Voice input/output
- [ ] Mobile app companion
- [ ] Cloud sync
- [ ] Plugin marketplace
- [ ] AI-powered email composition
- [ ] Advanced automation builder UI
- [ ] Integration with more smart home platforms
- [ ] Shared calendars and collaboration
- [ ] Export/import functionality

## 🐛 Troubleshooting

### Common Issues

**Import Errors:**
```bash
# Ensure all dependencies are installed
pip install -r requirements.txt --upgrade
```

**Gmail Not Working:**
```bash
# Delete old token and reauthorize
rm gmail_token.pickle
python run.py
```

**Database Errors:**
```bash
# Create data directory
mkdir -p data

# Check permissions
chmod 755 data
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **LM Studio** - Local LLM inference
- **Google APIs** - Gmail integration
- **Philips Hue** - Smart lighting
- **Open-Meteo** - Weather data
- **ytmusicapi** - YouTube Music integration

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/blue-robot-middleware/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/blue-robot-middleware/discussions)
- **Documentation:** [Wiki](https://github.com/yourusername/blue-robot-middleware/wiki)

## 📈 Stats

- **17+** Tool categories
- **100+** Features
- **8** New tools in latest release
- **~7,000** Lines of code
- **12** SQLite databases
- **Save ~7 hours/week** with automation features

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/blue-robot-middleware&type=Date)](https://star-history.com/#yourusername/blue-robot-middleware&Date)

## 🔖 Version History

### v11.0.0 (2025-12-10) - Gmail Enhanced
- Added email templates with variables
- Added email scheduling
- Added smart filters and auto-rules
- Added quick replies
- Added email categorization

### v10.0.0 (2025-12-10) - Personal Management
- Added location management
- Added contact management
- Added habit tracking with streaks

### v9.0.0 (2025-12-10) - Productivity Suite
- Added calendar & events
- Added weather forecasting
- Added automation routines
- Added media library

---

**Made with ❤️ by the Blue Robot Team**

*Turn your computer into an intelligent personal assistant*
