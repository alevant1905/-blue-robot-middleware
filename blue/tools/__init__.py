"""
Blue Robot Tools Package
========================
Individual tool implementations for Blue's capabilities.

This package contains modular tool implementations:
    blue/tools/
    ├── __init__.py     # This file - exports all tools
    ├── music.py        # Music playback and control
    ├── vision.py       # Camera and image processing
    ├── documents.py    # Document management and search
    ├── lights.py       # Philips Hue control
    ├── web.py          # Web search and browsing
    ├── gmail.py        # Email operations
    ├── utilities.py    # Time, date, calculator, random
    ├── timers.py       # Timers, alarms, reminders
    ├── notes.py        # Notes, tasks, lists
    ├── system.py       # Clipboard, screenshots, notifications
    └── recognition.py  # Face and place recognition
"""

# Music tools
from .music import (
    init_youtube_music,
    search_youtube_music,
    get_music_mood,
    play_music,
    search_music_info,
    control_music,
    YOUTUBE_MUSIC_BROWSER,
    MUSIC_SERVICE,
)

# Vision tools
from .vision import (
    ImageInfo,
    VisionImageQueue,
    get_vision_queue,
    view_image,
    capture_camera_image,
    start_music_visualizer,
    stop_music_visualizer,
    is_visualizer_active,
    # Recognition integration
    capture_and_recognize,
    recognize_uploaded_image,
    get_recognition_context,
    teach_person,
    teach_place,
    who_do_i_know,
    where_do_i_know,
)

# Recognition tools
from .recognition import (
    FaceRecognitionEngine,
    PlaceRecognitionEngine,
    RecognitionManager,
    RecognitionResult,
    FaceMatch,
    PlaceMatch,
    get_recognition_manager,
    recognize_image,
    enroll_person,
    enroll_place,
    list_known_people,
    list_known_places,
    forget_person,
    execute_recognition_command,
)

# Document tools
from .documents import (
    UPLOAD_FOLDER,
    DOCUMENTS_FOLDER,
    MAX_FILE_SIZE,
    ALLOWED_EXTENSIONS,
    DOCUMENT_INDEX_FILE,
    load_document_index,
    save_document_index,
    allowed_file,
    ensure_unique_path,
    get_file_hash,
    encode_image_to_base64,
    extract_text_from_file,
    add_document_to_rag,
    search_documents_rag,
    search_documents_local,
    create_document_file,
)

# Light tools
from .lights import (
    HUE_CONFIG,
    BRIDGE_IP,
    HUE_USERNAME,
    COLOR_MAP,
    MOOD_PRESETS,
    get_hue_lights,
    find_light_by_name,
    control_hue_light,
    apply_mood_to_lights,
    execute_light_control,
)

# Web tools
from .web import (
    execute_web_search,
    get_weather_data,
    execute_browse_website,
    SEARCH_MAX_PER_MINUTE,
    SEARCH_CACHE_TTL_SEC,
    SEARCH_RESULTS_PER_QUERY,
)

# Gmail tools
from .gmail import (
    GMAIL_AVAILABLE,
    GMAIL_SCOPES,
    get_gmail_service,
    execute_read_gmail,
    execute_send_gmail,
    execute_reply_gmail,
)

# Gmail Enhanced tools
from .gmail_enhanced import (
    GmailEnhancedManager,
    EmailTemplate,
    EmailFilter,
    ScheduledEmail,
    TemplateType,
    EmailCategory,
    get_gmail_enhanced_manager,
    create_template_cmd,
    list_templates_cmd,
    schedule_email_cmd,
    list_scheduled_emails_cmd,
    execute_gmail_enhanced_command,
    PREDEFINED_TEMPLATES,
)

# Gmail AI tools
from .gmail_ai import (
    EmailPriority,
    EmailSentiment,
    EmailAnalysis,
    GmailAIManager,
    get_gmail_ai_manager,
    analyze_inbox_cmd,
    suggest_reply_cmd,
)

# Gmail Bulk operations
from .gmail_bulk import (
    GmailBulkManager,
    AttachmentManager,
    get_bulk_manager,
    get_attachment_manager,
    bulk_archive_cmd,
    smart_cleanup_cmd,
    find_large_emails_cmd,
    unsubscribe_cmd,
)

# Utility tools
from .utilities import (
    get_current_time,
    get_current_date,
    get_datetime_info,
    calculate,
    convert_units,
    get_system_info,
    count_text,
    generate_random,
    execute_utility,
)

# Timer tools
from .timers import (
    TimerManager,
    TimerEntry,
    TimerType,
    get_timer_manager,
    set_timer,
    set_alarm,
    set_reminder,
    cancel_timer_cmd,
    list_timers_cmd,
    execute_timer_command,
    parse_duration,
    parse_time,
)

# Notes & Tasks tools
from .notes import (
    NotesManager,
    Note,
    Task,
    ListItem,
    TaskPriority,
    TaskStatus,
    get_notes_manager,
    create_note_cmd,
    search_notes_cmd,
    delete_note_cmd,
    create_task_cmd,
    complete_task_cmd,
    list_tasks_cmd,
    add_to_list_cmd,
    get_list_cmd,
    check_item_cmd,
    remove_from_list_cmd,
    execute_notes_command,
)

# System tools
from .system import (
    get_clipboard,
    set_clipboard,
    take_screenshot,
    list_screenshots,
    send_notification,
    launch_application,
    open_url,
    open_file,
    set_volume,
    get_volume,
    get_system_status,
    execute_system_command,
)

# Calendar tools
from .calendar import (
    CalendarManager,
    CalendarEvent,
    EventType,
    RecurrenceType,
    get_calendar_manager,
    create_event_cmd,
    list_events_cmd,
    search_events_cmd,
    delete_event_cmd,
    execute_calendar_command,
)

# Weather tools
from .weather import (
    WeatherManager,
    WeatherData,
    ForecastDay,
    WeatherCondition,
    get_weather_manager,
    get_current_weather_cmd,
    get_forecast_cmd,
    execute_weather_command,
)

# Automation tools
from .automation import (
    AutomationManager,
    Routine,
    Action,
    ActionType,
    TriggerType,
    get_automation_manager,
    create_routine_cmd,
    list_routines_cmd,
    execute_routine_cmd,
    delete_routine_cmd,
    install_predefined_routine,
    execute_automation_command,
    PREDEFINED_ROUTINES,
)

# Media Library tools
from .media_library import (
    MediaLibraryManager,
    MediaCollection,
    MediaItem,
    MediaType,
    MediaStatus,
    get_media_library_manager,
    subscribe_podcast_cmd,
    list_subscriptions_cmd,
    list_episodes_cmd,
    update_progress_cmd,
    search_media_cmd,
    get_recently_played_cmd,
    get_in_progress_cmd,
    execute_media_library_command,
)

# Location tools
from .locations import (
    LocationManager,
    Location,
    LocationCategory,
    get_location_manager,
    add_location_cmd,
    list_locations_cmd,
    search_locations_cmd,
    get_location_cmd,
    delete_location_cmd,
    log_visit_cmd,
    execute_location_command,
)

# Contact tools
from .contacts import (
    ContactManager,
    Contact,
    ContactType,
    CommunicationType,
    get_contact_manager,
    add_contact_cmd,
    list_contacts_cmd,
    search_contacts_cmd,
    get_contact_cmd,
    upcoming_birthdays_cmd,
    execute_contact_command,
)

# Habit tracking tools
from .habits import (
    HabitManager,
    Habit,
    HabitFrequency,
    HabitCategory,
    get_habit_manager,
    create_habit_cmd,
    list_habits_cmd,
    complete_habit_cmd,
    habit_stats_cmd,
    execute_habit_command,
)

# Social Media Management
from .social_media import (
    SocialMediaManager,
    SocialPost,
    ContentIdea,
    PlatformAccount,
    Platform,
    PostStatus,
    ContentType,
    ApprovalStatus,
    get_social_media_manager,
    draft_post_cmd,
    approve_post_cmd,
    list_posts_cmd,
    get_scheduled_posts_cmd,
    add_content_idea_cmd,
    get_content_ideas_cmd,
    get_engagement_stats_cmd,
    suggest_hashtags_cmd,
    connect_account_cmd,
)

# Facebook integration
from .facebook_integration import (
    FacebookOAuthManager,
    FacebookAPIClient,
    FacebookIntegration,
    get_facebook_integration,
    setup_facebook_app_cmd,
    connect_facebook_cmd,
    complete_facebook_auth_cmd,
    publish_to_facebook_cmd,
    sync_facebook_engagement_cmd,
)


__all__ = [
    # Music
    'init_youtube_music',
    'search_youtube_music',
    'get_music_mood',
    'play_music',
    'search_music_info',
    'control_music',
    'YOUTUBE_MUSIC_BROWSER',
    'MUSIC_SERVICE',

    # Vision
    'ImageInfo',
    'VisionImageQueue',
    'get_vision_queue',
    'view_image',
    'capture_camera_image',
    'start_music_visualizer',
    'stop_music_visualizer',
    'is_visualizer_active',
    'capture_and_recognize',
    'recognize_uploaded_image',
    'get_recognition_context',
    'teach_person',
    'teach_place',
    'who_do_i_know',
    'where_do_i_know',

    # Recognition
    'FaceRecognitionEngine',
    'PlaceRecognitionEngine',
    'RecognitionManager',
    'RecognitionResult',
    'FaceMatch',
    'PlaceMatch',
    'get_recognition_manager',
    'recognize_image',
    'enroll_person',
    'enroll_place',
    'list_known_people',
    'list_known_places',
    'forget_person',
    'execute_recognition_command',

    # Documents
    'UPLOAD_FOLDER',
    'DOCUMENTS_FOLDER',
    'MAX_FILE_SIZE',
    'ALLOWED_EXTENSIONS',
    'DOCUMENT_INDEX_FILE',
    'load_document_index',
    'save_document_index',
    'allowed_file',
    'ensure_unique_path',
    'get_file_hash',
    'encode_image_to_base64',
    'extract_text_from_file',
    'add_document_to_rag',
    'search_documents_rag',
    'search_documents_local',
    'create_document_file',

    # Lights
    'HUE_CONFIG',
    'BRIDGE_IP',
    'HUE_USERNAME',
    'COLOR_MAP',
    'MOOD_PRESETS',
    'get_hue_lights',
    'find_light_by_name',
    'control_hue_light',
    'apply_mood_to_lights',
    'execute_light_control',

    # Web
    'execute_web_search',
    'get_weather_data',
    'execute_browse_website',
    'SEARCH_MAX_PER_MINUTE',
    'SEARCH_CACHE_TTL_SEC',
    'SEARCH_RESULTS_PER_QUERY',

    # Gmail
    'GMAIL_AVAILABLE',
    'GMAIL_SCOPES',
    'get_gmail_service',
    'execute_read_gmail',
    'execute_send_gmail',
    'execute_reply_gmail',

    # Gmail Enhanced
    'GmailEnhancedManager',
    'EmailTemplate',
    'EmailFilter',
    'ScheduledEmail',
    'TemplateType',
    'EmailCategory',
    'get_gmail_enhanced_manager',
    'create_template_cmd',
    'list_templates_cmd',
    'schedule_email_cmd',
    'list_scheduled_emails_cmd',
    'execute_gmail_enhanced_command',
    'PREDEFINED_TEMPLATES',

    # Gmail AI
    'EmailPriority',
    'EmailSentiment',
    'EmailAnalysis',
    'GmailAIManager',
    'get_gmail_ai_manager',
    'analyze_inbox_cmd',
    'suggest_reply_cmd',

    # Gmail Bulk
    'GmailBulkManager',
    'AttachmentManager',
    'get_bulk_manager',
    'get_attachment_manager',
    'bulk_archive_cmd',
    'smart_cleanup_cmd',
    'find_large_emails_cmd',
    'unsubscribe_cmd',

    # Utilities
    'get_current_time',
    'get_current_date',
    'get_datetime_info',
    'calculate',
    'convert_units',
    'get_system_info',
    'count_text',
    'generate_random',
    'execute_utility',

    # Timers
    'TimerManager',
    'TimerEntry',
    'TimerType',
    'get_timer_manager',
    'set_timer',
    'set_alarm',
    'set_reminder',
    'cancel_timer_cmd',
    'list_timers_cmd',
    'execute_timer_command',
    'parse_duration',
    'parse_time',

    # Notes & Tasks
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

    # System
    'get_clipboard',
    'set_clipboard',
    'take_screenshot',
    'list_screenshots',
    'send_notification',
    'launch_application',
    'open_url',
    'open_file',
    'set_volume',
    'get_volume',
    'get_system_status',
    'execute_system_command',

    # Calendar
    'CalendarManager',
    'CalendarEvent',
    'EventType',
    'RecurrenceType',
    'get_calendar_manager',
    'create_event_cmd',
    'list_events_cmd',
    'search_events_cmd',
    'delete_event_cmd',
    'execute_calendar_command',

    # Weather
    'WeatherManager',
    'WeatherData',
    'ForecastDay',
    'WeatherCondition',
    'get_weather_manager',
    'get_current_weather_cmd',
    'get_forecast_cmd',
    'execute_weather_command',

    # Automation
    'AutomationManager',
    'Routine',
    'Action',
    'ActionType',
    'TriggerType',
    'get_automation_manager',
    'create_routine_cmd',
    'list_routines_cmd',
    'execute_routine_cmd',
    'delete_routine_cmd',
    'install_predefined_routine',
    'execute_automation_command',
    'PREDEFINED_ROUTINES',

    # Media Library
    'MediaLibraryManager',
    'MediaCollection',
    'MediaItem',
    'MediaType',
    'MediaStatus',
    'get_media_library_manager',
    'subscribe_podcast_cmd',
    'list_subscriptions_cmd',
    'list_episodes_cmd',
    'update_progress_cmd',
    'search_media_cmd',
    'get_recently_played_cmd',
    'get_in_progress_cmd',
    'execute_media_library_command',

    # Locations
    'LocationManager',
    'Location',
    'LocationCategory',
    'get_location_manager',
    'add_location_cmd',
    'list_locations_cmd',
    'search_locations_cmd',
    'get_location_cmd',
    'delete_location_cmd',
    'log_visit_cmd',
    'execute_location_command',

    # Contacts
    'ContactManager',
    'Contact',
    'ContactType',
    'CommunicationType',
    'get_contact_manager',
    'add_contact_cmd',
    'list_contacts_cmd',
    'search_contacts_cmd',
    'get_contact_cmd',
    'upcoming_birthdays_cmd',
    'execute_contact_command',

    # Habits
    'HabitManager',
    'Habit',
    'HabitFrequency',
    'HabitCategory',
    'get_habit_manager',
    'create_habit_cmd',
    'list_habits_cmd',
    'complete_habit_cmd',
    'habit_stats_cmd',
    'execute_habit_command',

    # Social Media
    'SocialMediaManager',
    'SocialPost',
    'ContentIdea',
    'PlatformAccount',
    'Platform',
    'PostStatus',
    'ContentType',
    'ApprovalStatus',
    'get_social_media_manager',
    'draft_post_cmd',
    'approve_post_cmd',
    'list_posts_cmd',
    'get_scheduled_posts_cmd',
    'add_content_idea_cmd',
    'get_content_ideas_cmd',
    'get_engagement_stats_cmd',
    'suggest_hashtags_cmd',
    'connect_account_cmd',

    # Facebook
    'FacebookOAuthManager',
    'FacebookAPIClient',
    'FacebookIntegration',
    'get_facebook_integration',
    'setup_facebook_app_cmd',
    'connect_facebook_cmd',
    'complete_facebook_auth_cmd',
    'publish_to_facebook_cmd',
    'sync_facebook_engagement_cmd',
]
