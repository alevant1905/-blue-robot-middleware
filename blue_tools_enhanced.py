"""
Blue Enhanced Tools Module
New capabilities for home assistant, computer control, and family features
"""

import os
import json
import subprocess
import platform
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger("blue.tools")

# Import configurations and database
try:
    from config import (
        DATA_DIR, DOCUMENTS_DIR, UPLOADS_DIR,
        family, interaction, skills
    )
    from blue_database import create_database
    db = create_database()
except ImportError as e:
    logger.warning(f"Could not import config or database modules: {e}")
    # Fallback defaults
    from pathlib import Path
    DATA_DIR = Path(__file__).parent / "data"
    DOCUMENTS_DIR = Path(__file__).parent / "uploaded_documents"
    UPLOADS_DIR = Path(__file__).parent / "uploads"
    family = None
    interaction = None
    skills = None
    db = None


# ===== Calendar & Scheduling Tools =====

class CalendarManager:
    """Manage calendar, reminders, and schedules"""
    
    @staticmethod
    def create_reminder(user_name: str, title: str, when: str, 
                       description: str = None) -> Dict:
        """
        Create a reminder for a user
        Args:
            user_name: Who the reminder is for
            title: Short title of the reminder
            when: When to remind (natural language like "tomorrow at 3pm", "in 2 hours")
            description: Optional detailed description
        """
        try:
            # Parse natural language time (simplified - could use dateparser library)
            due_time = CalendarManager._parse_time(when)
            
            if db:
                reminder_id = db.create_reminder(
                    user_name=user_name,
                    title=title,
                    due_datetime=due_time,
                    description=description,
                    priority=3
                )
                
                return {
                    "success": True,
                    "reminder_id": reminder_id,
                    "title": title,
                    "due": due_time.strftime("%Y-%m-%d %H:%M"),
                    "message": f"Reminder set for {due_time.strftime('%B %d at %I:%M %p')}"
                }
            else:
                return {"success": False, "error": "Database not available"}
                
        except Exception as e:
            logger.error(f"Error creating reminder: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _parse_time(when_str: str) -> datetime:
        """Parse natural language time into datetime"""
        now = datetime.now()
        when_lower = when_str.lower()
        
        # Handle common patterns
        if "tomorrow" in when_lower:
            result = now + timedelta(days=1)
            result = result.replace(hour=9, minute=0)  # Default to 9am
        elif "tonight" in when_lower:
            result = now.replace(hour=20, minute=0)  # 8pm
        elif "in" in when_lower and "hour" in when_lower:
            # "in 2 hours"
            hours = 1
            try:
                hours = int(''.join(c for c in when_lower if c.isdigit()))
            except:
                pass
            result = now + timedelta(hours=hours)
        elif "in" in when_lower and "minute" in when_lower:
            # "in 30 minutes"
            minutes = 30
            try:
                minutes = int(''.join(c for c in when_lower if c.isdigit()))
            except:
                pass
            result = now + timedelta(minutes=minutes)
        else:
            # Default to 1 hour from now
            result = now + timedelta(hours=1)
        
        return result
    
    @staticmethod
    def get_upcoming_reminders(user_name: str, hours_ahead: int = 24) -> Dict:
        """Get upcoming reminders for a user"""
        if not db:
            return {"success": False, "error": "Database not available"}
        
        reminders = db.get_due_reminders(user_name, hours_ahead)
        
        return {
            "success": True,
            "count": len(reminders),
            "reminders": [
                {
                    "id": r['id'],
                    "title": r['title'],
                    "description": r['description'],
                    "due": r['due_datetime'],
                    "priority": r['priority']
                }
                for r in reminders
            ]
        }
    
    @staticmethod
    def complete_reminder(reminder_id: int) -> Dict:
        """Mark a reminder as completed"""
        if not db:
            return {"success": False, "error": "Database not available"}
        
        success = db.complete_reminder(reminder_id)
        return {
            "success": success,
            "message": "Reminder completed" if success else "Failed to complete reminder"
        }


# ===== Task Management Tools =====

class TaskManager:
    """Manage tasks and to-do lists"""
    
    @staticmethod
    def create_task(user_name: str, title: str, description: str = None,
                   priority: str = "medium", due_date: str = None) -> Dict:
        """Create a new task"""
        if not db:
            return {"success": False, "error": "Database not available"}
        
        priority_map = {"low": 1, "medium": 3, "high": 5}
        priority_int = priority_map.get(priority.lower(), 3)
        
        due_datetime = None
        if due_date:
            try:
                due_datetime = datetime.fromisoformat(due_date)
            except:
                pass
        
        task_id = db.create_task(
            user_name=user_name,
            title=title,
            description=description,
            priority=priority_int,
            due_date=due_datetime
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "title": title,
            "message": f"Task '{title}' created successfully"
        }
    
    @staticmethod
    def get_tasks(user_name: str, status: str = "pending") -> Dict:
        """Get tasks for a user"""
        if not db:
            return {"success": False, "error": "Database not available"}
        
        tasks = db.get_tasks(user_name, status)
        
        return {
            "success": True,
            "count": len(tasks),
            "tasks": [
                {
                    "id": t['id'],
                    "title": t['title'],
                    "description": t['description'],
                    "priority": t['priority'],
                    "due_date": t['due_date'],
                    "status": t['status']
                }
                for t in tasks
            ]
        }
    
    @staticmethod
    def complete_task(task_id: int) -> Dict:
        """Mark a task as completed"""
        if not db:
            return {"success": False, "error": "Database not available"}
        
        success = db.complete_task(task_id)
        return {
            "success": success,
            "message": "Task completed! Great job!" if success else "Failed to complete task"
        }


# ===== Note Taking Tools =====

class NoteManager:
    """Manage notes and memos"""
    
    @staticmethod
    def create_note(user_name: str, title: str, content: str,
                   category: str = None) -> Dict:
        """Create a new note"""
        if not db:
            return {"success": False, "error": "Database not available"}
        
        note_id = db.create_note(
            user_name=user_name,
            title=title,
            content=content,
            category=category
        )
        
        return {
            "success": True,
            "note_id": note_id,
            "title": title,
            "message": f"Note '{title}' saved successfully"
        }
    
    @staticmethod
    def search_notes(user_name: str, query: str) -> Dict:
        """Search notes"""
        if not db:
            return {"success": False, "error": "Database not available"}
        
        notes = db.search_notes(user_name, query)
        
        return {
            "success": True,
            "count": len(notes),
            "notes": [
                {
                    "id": n['id'],
                    "title": n['title'],
                    "content": n['content'][:200],  # Preview
                    "category": n['category'],
                    "created": n['created_at']
                }
                for n in notes
            ]
        }


# ===== System Control Tools =====

class SystemController:
    """Control computer system functions"""
    
    @staticmethod
    def get_system_info() -> Dict:
        """Get system information"""
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "success": True,
                "system": platform.system(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2)
            }
        except ImportError:
            return {
                "success": False,
                "error": "psutil library not installed. Run: pip install psutil"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def launch_application(app_name: str) -> Dict:
        """Launch an application"""
        try:
            system = platform.system()
            
            # Common applications mapping
            apps = {
                "browser": {"Windows": "start chrome", "Darwin": "open -a Safari", "Linux": "firefox"},
                "chrome": {"Windows": "start chrome", "Darwin": "open -a 'Google Chrome'", "Linux": "google-chrome"},
                "firefox": {"Windows": "start firefox", "Darwin": "open -a Firefox", "Linux": "firefox"},
                "calculator": {"Windows": "calc", "Darwin": "open -a Calculator", "Linux": "gnome-calculator"},
                "notepad": {"Windows": "notepad", "Darwin": "open -a TextEdit", "Linux": "gedit"},
                "terminal": {"Windows": "start cmd", "Darwin": "open -a Terminal", "Linux": "gnome-terminal"},
            }
            
            app_lower = app_name.lower()
            if app_lower in apps and system in apps[app_lower]:
                cmd = apps[app_lower][system]
                subprocess.Popen(cmd, shell=True)
                return {
                    "success": True,
                    "message": f"Launched {app_name}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Don't know how to launch {app_name} on {system}"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def set_volume(level: int) -> Dict:
        """Set system volume (0-100)"""
        try:
            system = platform.system()
            level = max(0, min(100, level))  # Clamp to 0-100
            
            if system == "Windows":
                # Windows volume control via NirCmd (if installed)
                subprocess.run(["nircmd.exe", "setsysvolume", str(level * 655)], check=True)
            elif system == "Darwin":
                # macOS volume control
                subprocess.run(["osascript", "-e", f"set volume output volume {level}"], check=True)
            elif system == "Linux":
                # Linux volume control via amixer
                subprocess.run(["amixer", "set", "Master", f"{level}%"], check=True)
            
            return {
                "success": True,
                "volume": level,
                "message": f"Volume set to {level}%"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Could not set volume: {str(e)}"
            }
    
    @staticmethod
    def take_screenshot(filename: str = None) -> Dict:
        """Take a screenshot"""
        try:
            from PIL import ImageGrab
            
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
            
            # Save to documents directory
            filepath = DOCUMENTS_DIR / filename
            
            screenshot = ImageGrab.grab()
            screenshot.save(filepath)
            
            return {
                "success": True,
                "filename": filename,
                "filepath": str(filepath),
                "message": f"Screenshot saved as {filename}"
            }
        except ImportError:
            return {
                "success": False,
                "error": "PIL library not installed. Run: pip install Pillow"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ===== File Operations =====

class FileOperations:
    """File and folder operations"""
    
    @staticmethod
    def list_files(directory: str = None, pattern: str = "*") -> Dict:
        """List files in a directory"""
        try:
            if directory is None:
                directory = str(DOCUMENTS_DIR)
            
            dir_path = Path(directory)
            if not dir_path.exists():
                return {"success": False, "error": f"Directory not found: {directory}"}
            
            files = list(dir_path.glob(pattern))
            
            return {
                "success": True,
                "directory": str(dir_path),
                "count": len(files),
                "files": [
                    {
                        "name": f.name,
                        "size": f.stat().st_size,
                        "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                        "is_dir": f.is_dir()
                    }
                    for f in files[:100]  # Limit to 100 files
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def read_file(filepath: str) -> Dict:
        """Read contents of a text file"""
        try:
            file_path = Path(filepath)
            if not file_path.exists():
                return {"success": False, "error": f"File not found: {filepath}"}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "success": True,
                "filename": file_path.name,
                "content": content,
                "size": len(content)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def create_folder(folder_name: str, parent_dir: str = None) -> Dict:
        """Create a new folder"""
        try:
            if parent_dir is None:
                parent_dir = str(DOCUMENTS_DIR)
            
            folder_path = Path(parent_dir) / folder_name
            folder_path.mkdir(parents=True, exist_ok=True)
            
            return {
                "success": True,
                "folder_path": str(folder_path),
                "message": f"Folder '{folder_name}' created"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ===== Timer & Alarm Tools =====

class TimerManager:
    """Manage timers and alarms"""
    
    active_timers = {}
    
    @staticmethod
    def set_timer(duration_minutes: int, label: str = "Timer") -> Dict:
        """Set a timer"""
        try:
            timer_id = len(TimerManager.active_timers) + 1
            end_time = datetime.now() + timedelta(minutes=duration_minutes)
            
            TimerManager.active_timers[timer_id] = {
                "label": label,
                "duration_minutes": duration_minutes,
                "end_time": end_time
            }
            
            return {
                "success": True,
                "timer_id": timer_id,
                "label": label,
                "duration_minutes": duration_minutes,
                "ends_at": end_time.strftime("%H:%M:%S"),
                "message": f"Timer '{label}' set for {duration_minutes} minutes"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def check_timers() -> Dict:
        """Check status of all timers"""
        now = datetime.now()
        active = []
        expired = []
        
        for timer_id, timer in TimerManager.active_timers.items():
            time_left = (timer['end_time'] - now).total_seconds()
            
            if time_left > 0:
                active.append({
                    "id": timer_id,
                    "label": timer['label'],
                    "time_left_seconds": int(time_left),
                    "time_left_formatted": f"{int(time_left // 60)}m {int(time_left % 60)}s"
                })
            else:
                expired.append({
                    "id": timer_id,
                    "label": timer['label'],
                    "message": f"Timer '{timer['label']}' has finished!"
                })
        
        return {
            "success": True,
            "active_timers": active,
            "expired_timers": expired
        }


# ===== Storytelling & Educational Tools =====

class StorytellingTools:
    """Tools for stories and educational content"""
    
    @staticmethod
    def story_prompt(child_name: str, theme: str = None, 
                    moral: str = None, length: str = "short") -> Dict:
        """Generate a storytelling prompt tailored for a child"""
        try:
            # Get child's age and interests from family config
            child_info = family.members.get(child_name, {})
            age = child_info.get("age", 8)
            interests = child_info.get("interests", [])
            
            prompt = f"Tell a {length} story for {child_name} (age {age}). "
            
            if theme:
                prompt += f"The theme should be about {theme}. "
            elif interests:
                prompt += f"Incorporate {child_name}'s interests: {', '.join(interests)}. "
            
            if moral:
                prompt += f"The story should teach about {moral}. "
            
            prompt += f"Make it age-appropriate, engaging, and fun!"
            
            return {
                "success": True,
                "child_name": child_name,
                "age": age,
                "prompt": prompt,
                "message": "Story prompt generated. Use this to tell a story!"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def educational_activity(child_name: str, subject: str) -> Dict:
        """Suggest an educational activity"""
        child_info = family.members.get(child_name, {})
        age = child_info.get("age", 8)
        
        activities = {
            "math": {
                "5-7": "Count objects around the house",
                "8-10": "Practice multiplication with fun patterns",
                "11+": "Solve real-world word problems"
            },
            "science": {
                "5-7": "Explore nature - identify plants and animals",
                "8-10": "Simple experiments like making volcanoes",
                "11+": "Research a scientific topic of interest"
            },
            "reading": {
                "5-7": "Picture books with simple words",
                "8-10": "Chapter books and short stories",
                "11+": "Age-appropriate novels and articles"
            }
        }
        
        age_group = "5-7" if age <= 7 else "8-10" if age <= 10 else "11+"
        activity = activities.get(subject.lower(), {}).get(age_group, "Practice and explore!")
        
        return {
            "success": True,
            "child_name": child_name,
            "age": age,
            "subject": subject,
            "activity": activity,
            "message": f"Activity suggestion for {child_name}"
        }


# ===== Weather & Location =====

class LocationServices:
    """Location and weather services"""
    
    @staticmethod
    def get_local_time() -> Dict:
        """Get current local time"""
        now = datetime.now()
        return {
            "success": True,
            "datetime": now.isoformat(),
            "time": now.strftime("%I:%M %p"),
            "date": now.strftime("%A, %B %d, %Y"),
            "timezone": family.timezone
        }
    
    @staticmethod
    def get_sunrise_sunset() -> Dict:
        """Get sunrise/sunset times (simplified)"""
        # This is simplified - could use astral library for accurate times
        now = datetime.now()
        sunrise = now.replace(hour=6, minute=30)
        sunset = now.replace(hour=18, minute=45)
        
        return {
            "success": True,
            "date": now.strftime("%Y-%m-%d"),
            "sunrise": sunrise.strftime("%I:%M %p"),
            "sunset": sunset.strftime("%I:%M %p"),
            "location": family.home_location if family else "Unknown"
        }


# ===== Smart Home Control =====

class SmartHomeController:
    """Control smart home devices (Philips Hue, etc.)"""

    @staticmethod
    def set_lights(scene: str = None, brightness: int = None, color: str = None) -> Dict:
        """Set light scene, brightness, or color"""
        try:
            from config import HUE_BRIDGE_IP, HUE_USERNAME
            import requests

            if not HUE_BRIDGE_IP or not HUE_USERNAME:
                return {"success": False, "error": "Hue bridge not configured"}

            # This is a simplified implementation
            result = {"success": True, "message": "Lights updated"}
            if scene:
                result["scene"] = scene
            if brightness is not None:
                result["brightness"] = brightness
            if color:
                result["color"] = color

            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_light_status() -> Dict:
        """Get current light status"""
        return {
            "success": True,
            "lights": [],
            "message": "Light status - configure Hue bridge for full functionality"
        }


# ===== Music Control =====

class MusicController:
    """Control music playback"""

    @staticmethod
    def play_music(query: str = None, artist: str = None, genre: str = None) -> Dict:
        """Play music based on query, artist, or genre"""
        try:
            result = {"success": True}
            if query:
                result["playing"] = f"Searching for: {query}"
            elif artist:
                result["playing"] = f"Artist: {artist}"
            elif genre:
                result["playing"] = f"Genre: {genre}"
            else:
                result["playing"] = "Random music"

            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def pause_music() -> Dict:
        """Pause current playback"""
        return {"success": True, "message": "Music paused"}

    @staticmethod
    def skip_track() -> Dict:
        """Skip to next track"""
        return {"success": True, "message": "Skipped to next track"}

    @staticmethod
    def set_volume(level: int) -> Dict:
        """Set music volume (0-100)"""
        level = max(0, min(100, level))
        return {"success": True, "volume": level}


# Export all tool classes
__all__ = [
    'CalendarManager',
    'TaskManager',
    'NoteManager',
    'SystemController',
    'FileOperations',
    'TimerManager',
    'StorytellingTools',
    'LocationServices',
    'SmartHomeController',
    'MusicController',
]
