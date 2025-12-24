#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Blue Robot Middleware - Modular Entry Point
============================================

This is the new entry point that uses the refactored modular components.
Run with: python run.py

The original bluetools.py is kept as a backup.

Module Structure:
    blue/
    ├── __init__.py          # Core exports
    ├── utils.py             # Utility functions
    ├── memory.py            # Memory/facts system
    ├── llm.py               # LLM client
    ├── tool_selector.py     # Intent detection & tool selection
    └── tools/
        ├── music.py         # YouTube Music
        ├── vision.py        # Camera & visualizer
        ├── documents.py     # Document management
        ├── lights.py        # Philips Hue
        ├── web.py           # Web search & browsing
        └── gmail.py         # Email operations
"""

# Future imports
from __future__ import annotations

# Standard library
import io
import os
import sys

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Ensure we're in the right directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Add to path if needed
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

def print_banner():
    """Print startup banner."""
    print("=" * 60)
    print("🤖 Blue Robot Middleware - MODULAR VERSION")
    print("=" * 60)

def check_modular_imports():
    """Verify modular components are available."""
    print("\n📦 Checking modular components...")

    try:
        # Blue package
        from blue import (
            ImprovedToolSelector,
            LMStudioClient,
            ToolIntent,
            ToolSelectionResult,
            build_system_preamble,
            load_blue_facts,
            settings,
        )
        print("   ✅ blue package (core)")
    except ImportError as e:
        print(f"   ❌ blue package: {e}")
        return False

    try:
        # Blue package
        from blue.tools import (  # Music; Lights; Documents; Web; Gmail; Vision
            GMAIL_AVAILABLE,
            MOOD_PRESETS,
            apply_mood_to_lights,
            capture_camera_image,
            control_music,
            execute_read_gmail,
            execute_web_search,
            get_hue_lights,
            get_vision_queue,
            get_weather_data,
            init_youtube_music,
            load_document_index,
            play_music,
            search_documents_rag,
        )
        print("   ✅ blue.tools package")
    except ImportError as e:
        print(f"   ❌ blue.tools package: {e}")
        return False

    try:
        # Blue package
        from blue.tool_selector import ImprovedToolSelector
        selector = ImprovedToolSelector()
        # Quick test
        result = selector.select_tool("play some jazz music", [])
        if result.primary_tool:
            print(f"   ✅ Tool selector working (test: {result.primary_tool.tool_name})")
        else:
            print("   ✅ Tool selector loaded")
    except Exception as e:
        print(f"   ⚠️  Tool selector: {e}")

    return True

def check_services():
    """Check external service availability."""
    print("\n🔌 Checking services...")

    # Check Hue
    try:
        # Blue package
        from blue.tools.lights import BRIDGE_IP, HUE_USERNAME, get_hue_lights
        if BRIDGE_IP and HUE_USERNAME:
            lights = get_hue_lights()
            if lights:
                print(f"   ✅ Philips Hue: {len(lights)} light(s) at {BRIDGE_IP}")
            else:
                print(f"   ⚠️  Philips Hue: Configured but no lights found")
        else:
            print("   ⚠️  Philips Hue: Not configured")
    except Exception as e:
        print(f"   ❌ Philips Hue: {e}")

    # Check YouTube Music
    try:
        # Blue package
        from blue.tools.music import init_youtube_music
        if init_youtube_music():
            print("   ✅ YouTube Music: Ready")
        else:
            print("   ⚠️  YouTube Music: Not available (pip install ytmusicapi)")
    except Exception as e:
        print(f"   ❌ YouTube Music: {e}")

    # Check Gmail
    try:
        # Blue package
        from blue.tools.gmail import GMAIL_AVAILABLE
        if GMAIL_AVAILABLE:
            print("   ✅ Gmail: Available")
        else:
            print("   ⚠️  Gmail: Not configured")
    except Exception as e:
        print(f"   ❌ Gmail: {e}")

    # Check Documents
    try:
        # Blue package
        from blue.tools.documents import load_document_index
        index = load_document_index()
        doc_count = len(index.get('documents', []))
        print(f"   ✅ Documents: {doc_count} indexed")
    except Exception as e:
        print(f"   ❌ Documents: {e}")

def run_server():
    """Start the Flask server."""
    print("\n🚀 Starting server...")
    print("   Note: Using bluetools.py for Flask app (modular components loaded)")
    print("")

    # Import bluetools which will start the Flask server
    # The server runs at module level in bluetools.py
    # Blue package
    import bluetools

def main():
    """Main entry point."""
    print_banner()

    # Check modular components first
    if not check_modular_imports():
        print("\n❌ Modular components failed to load!")
        print("   Falling back to original bluetools.py...")
        # Blue package
        import bluetools
        return

    # Check services
    check_services()

    # Print usage info
    print("\n" + "=" * 60)
    print("📖 Usage Examples:")
    print("   🎵 'Play Bohemian Rhapsody by Queen'")
    print("   💡 'Set the lights to sunset mood'")
    print("   📧 'Check my email'")
    print("   🔍 'Search for AI news'")
    print("   📄 'What does my contract say about...'")
    print("=" * 60)

    # Start the server
    run_server()

if __name__ == "__main__":
    main()
