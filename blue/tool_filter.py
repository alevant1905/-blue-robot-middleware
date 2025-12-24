"""
Blue Robot Smart Tool Filtering System
========================================

This module implements intelligent tool filtering to reduce the number of tools
sent to the LLM on each request, improving tool selection accuracy.

Key Features:
1. Intent-based tool filtering - only send relevant tools
2. Tool categorization by domain
3. Default essential tools for unclear intents
4. Confidence-based tool set expansion
"""

# Future imports
from __future__ import annotations

# Standard library
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set


@dataclass
class ToolFilterResult:
    """Result from tool filtering."""
    filtered_tools: List[Dict[str, Any]]  # Tools to send to LLM
    tool_count: int  # Number of tools included
    categories_included: List[str]  # Which categories were included
    reasoning: str  # Why these tools were selected


# Tool categories - each tool belongs to one or more categories
TOOL_CATEGORIES = {
    "music": ["play_music", "control_music", "music_visualizer"],
    "email": ["read_gmail", "send_gmail", "reply_gmail"],
    "documents": ["search_documents", "create_document", "view_image"],
    "lights": ["control_lights", "music_visualizer"],
    "search": ["web_search", "search_documents"],
    "camera": ["capture_camera", "view_image", "remember_person", "remember_place"],
    "calendar": ["create_reminder", "get_upcoming_reminders", "complete_reminder"],
    "tasks": ["create_task", "get_tasks", "complete_task"],
    "notes": ["create_note", "search_notes"],
    "system": ["get_system_info", "take_screenshot", "launch_application", "set_volume"],
    "time": ["get_local_time", "get_sunrise_sunset", "set_timer", "check_timers"],
    "weather": ["get_weather"],
    "web": ["browse_website", "web_search"],
    "coding": ["run_javascript"],
    "educational": ["story_prompt", "educational_activity"],
    "files": ["list_files", "read_file", "write_file", "get_file_info"],
    "facebook": ["post_to_facebook", "get_facebook_posts"],
}

# Essential tools that should ALWAYS be included (for general conversation)
ESSENTIAL_TOOLS = [
    "get_local_time",
    "get_weather",
    "web_search",
]

# Core tools for common requests (included when no clear intent detected)
CORE_TOOLS = [
    "play_music",
    "control_lights",
    "read_gmail",
    "search_documents",
    "web_search",
    "capture_camera",
    "get_weather",
    "get_local_time",
]


def get_tools_for_intent(
    primary_tool: Optional[str],
    intent_confidence: float,
    detected_categories: List[str],
    all_tools: List[Dict[str, Any]]
) -> ToolFilterResult:
    """
    Filter tools based on detected intent and confidence.

    Args:
        primary_tool: The primary tool detected (e.g., "play_music")
        intent_confidence: Confidence score (0.0-1.0)
        detected_categories: List of detected intent categories
        all_tools: Complete list of available tools

    Returns:
        ToolFilterResult with filtered tools and metadata
    """
    # Create a set of tool names to include
    tools_to_include: Set[str] = set()
    categories_included: List[str] = []
    reasoning = ""

    # HIGH CONFIDENCE (0.85+): Only include tools from detected categories + essentials
    if intent_confidence >= 0.85 and detected_categories:
        reasoning = f"High confidence ({intent_confidence:.2f}) - limiting to {len(detected_categories)} categories"

        # Add all tools from detected categories
        for category in detected_categories:
            if category in TOOL_CATEGORIES:
                tools_to_include.update(TOOL_CATEGORIES[category])
                categories_included.append(category)

        # Always add essential tools for fallback
        tools_to_include.update(ESSENTIAL_TOOLS)

    # MEDIUM CONFIDENCE (0.65-0.85): Include detected categories + core tools
    elif intent_confidence >= 0.65 and detected_categories:
        reasoning = f"Medium confidence ({intent_confidence:.2f}) - including detected + core tools"

        # Add detected category tools
        for category in detected_categories:
            if category in TOOL_CATEGORIES:
                tools_to_include.update(TOOL_CATEGORIES[category])
                categories_included.append(category)

        # Add core tools for flexibility
        tools_to_include.update(CORE_TOOLS)

    # LOW CONFIDENCE or NO CLEAR INTENT: Use core tool set
    else:
        reasoning = f"Low confidence ({intent_confidence:.2f} if any) - using core tool set"
        tools_to_include.update(CORE_TOOLS)
        categories_included = ["core"]

    # Filter the actual tool objects
    filtered_tools = [
        tool for tool in all_tools
        if tool.get("function", {}).get("name") in tools_to_include
    ]

    return ToolFilterResult(
        filtered_tools=filtered_tools,
        tool_count=len(filtered_tools),
        categories_included=categories_included,
        reasoning=reasoning
    )


def get_categories_from_tool_name(tool_name: str) -> List[str]:
    """Get which categories a tool belongs to."""
    categories = []
    for category, tools in TOOL_CATEGORIES.items():
        if tool_name in tools:
            categories.append(category)
    return categories


def detect_intent_categories(user_message: str) -> List[str]:
    """
    Detect which tool categories might be relevant for a user message.
    This is a lightweight, keyword-based detector.

    Args:
        user_message: The user's message

    Returns:
        List of potentially relevant categories
    """
    msg_lower = user_message.lower()
    categories = []

    # Music detection
    if any(word in msg_lower for word in ["play ", "music", "song", "artist", "pause", "skip", "volume", "next track", "previous track"]):
        categories.append("music")

    # Email detection
    if any(word in msg_lower for word in ["email", "gmail", "inbox", "send to", "@", "mail", "fanmail"]):
        categories.append("email")

    # Document detection
    if any(phrase in msg_lower for phrase in ["my document", "my file", "my contract", "my pdf", "uploaded", "document"]):
        categories.append("documents")

    # Lights detection
    if any(word in msg_lower for word in ["light", "lights", "lamp", "brightness", "color", "mood", "hue"]):
        categories.append("lights")

    # Camera/vision detection
    if any(phrase in msg_lower for phrase in ["what do you see", "look at", "camera", "take a picture", "what's in front"]):
        categories.append("camera")

    # Weather detection
    if any(word in msg_lower for word in ["weather", "temperature", "forecast", "rain", "sunny"]):
        categories.append("weather")

    # Web search detection
    if any(phrase in msg_lower for phrase in ["search for", "google", "look up", "find information about", "what is ", "who is "]):
        # But NOT if it's about user's documents
        if not any(phrase in msg_lower for phrase in ["my document", "my file", "my contract"]):
            categories.append("search")

    # Calendar/reminder detection
    if any(word in msg_lower for word in ["remind", "reminder", "appointment", "calendar", "schedule"]):
        categories.append("calendar")

    # Task detection
    if any(word in msg_lower for word in ["task", "todo", "to-do", "to do list"]):
        categories.append("tasks")

    # Notes detection
    if any(word in msg_lower for word in ["note", "notes", "memo", "write down", "remember that"]):
        categories.append("notes")

    # System detection
    if any(phrase in msg_lower for phrase in ["system info", "cpu", "memory", "disk space", "screenshot", "launch ", "open ", "volume"]):
        categories.append("system")

    # Time detection
    if any(phrase in msg_lower for phrase in ["what time", "current time", "sunrise", "sunset", "set a timer", "timer"]):
        categories.append("time")

    # Web browsing detection
    if any(word in msg_lower for word in ["http://", "https://", "browse", "visit website", ".com", ".org", ".net"]):
        categories.append("web")

    # Facebook detection
    if any(word in msg_lower for word in ["facebook", "fb post", "post to facebook", "facebook feed"]):
        categories.append("facebook")

    return categories


def create_tool_choice_param(tool_name: str) -> Dict[str, Any]:
    """
    Create a strict tool_choice parameter to force the LLM to use a specific tool.

    Args:
        tool_name: The name of the tool to force

    Returns:
        tool_choice parameter for OpenAI API
    """
    return {
        "type": "function",
        "function": {"name": tool_name}
    }


# Example usage and testing
if __name__ == "__main__":
    # Test category detection
    test_messages = [
        "Play some jazz music",
        "Check my email",
        "Turn on the lights",
        "What's the weather like?",
        "Search for recent news",
        "What do you see right now?",
        "Remind me to call mom tomorrow",
    ]

    print("=== Tool Category Detection Tests ===\n")
    for msg in test_messages:
        categories = detect_intent_categories(msg)
        print(f"Message: {msg}")
        print(f"Detected categories: {categories}")
        print(f"Tools that would be included: ", end="")
        tools = set()
        for cat in categories:
            if cat in TOOL_CATEGORIES:
                tools.update(TOOL_CATEGORIES[cat])
        print(list(tools))
        print()
