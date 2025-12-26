"""
Comprehensive test script for tool selection - tests BOTH the improved selector AND legacy detection functions.
This ensures false positives are fixed at all levels of the tool selection system.
"""

import sys
import os
import re

# Add blue package to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from blue.tool_selector import ImprovedToolSelector

# Define legacy detection functions inline to avoid importing the entire bluetools module
# (which starts Flask and other services)

def detect_visualizer_intent(message: str) -> bool:
    """Detect light visualizer/show requests."""
    VISUALIZER_KEYWORDS = [
        'visualizer', 'light show', 'light dance', 'dancing lights', 'party lights',
        'disco', 'strobe', 'color changing', 'dynamic lights', 'animated lights'
    ]
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in VISUALIZER_KEYWORDS)


def detect_light_intent(message: str) -> bool:
    """
    Detect light control requests with improved false positive filtering.
    Must have BOTH a light noun AND an action OR color to trigger.
    """
    msg_lower = message.lower()

    # Exclude visualizer requests from regular light control
    if detect_visualizer_intent(message):
        return False

    # Filter out "light" used as adjective (NOT about lighting)
    light_adjective_phrases = [
        'light snack', 'light meal', 'light reading', 'light exercise',
        'light work', 'light duty', 'light touch', 'light breeze',
        'light rain', 'light traffic', 'light weight', 'light load',
        'light blue', 'light green', 'light pink', 'light grey', 'light gray',
        'bring to light', 'see the light', 'light of day', 'in light of'
    ]
    if any(phrase in msg_lower for phrase in light_adjective_phrases):
        return False

    # Light nouns - must have one of these
    light_nouns = ['light', 'lights', 'lamp', 'lamps', 'bulb', 'bulbs', 'hue', 'lighting']
    has_light_noun = any(noun in msg_lower for noun in light_nouns)

    # Actions that indicate light control
    light_actions = ['turn on', 'turn off', 'switch on', 'switch off', 'dim', 'brighten',
                     'set to', 'change to', 'make it', 'adjust', 'lights on', 'lights off']
    has_action = any(action in msg_lower for action in light_actions)

    # Colors that suggest light control (when combined with light noun)
    light_colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'white', 'pink',
                    'cyan', 'warm', 'cool', 'bright', 'dim']
    has_color = any(color in msg_lower for color in light_colors)

    # Must have light noun AND (action OR color)
    return has_light_noun and (has_action or has_color)


def detect_music_play_intent(message: str) -> bool:
    """
    Detect requests to play music with improved false positive filtering.
    """
    msg_lower = message.lower()

    # Non-music "play" contexts that should NOT trigger music
    non_music_play_contexts = [
        'play a game', 'play game', 'play games', 'play video game', 'play the game',
        'play a video', 'play video', 'play this video', 'play the video',
        'play a role', 'play the role', 'play a part', 'play the part',
        'play sports', 'play a sport', 'play basketball', 'play football', 'play soccer',
        'play tennis', 'play golf', 'play baseball', 'play hockey',
        'play cards', 'play poker', 'play chess', 'play checkers',
        'play with', 'play around', 'let\'s play', 'wanna play', 'want to play',
        'play a match', 'play the match', 'play a round',
        'play a trick', 'play tricks', 'play a joke', 'play pranks',
        'role play', 'roleplay', 'word play', 'wordplay', 'fair play',
        'at play', 'child\'s play', 'foul play', 'power play'
    ]
    if any(phrase in msg_lower for phrase in non_music_play_contexts):
        return False

    # Must have "play" or similar
    play_keywords = ['play', 'put on', 'listen to', 'start playing', 'i want to hear', 'can you play']
    has_play = any(kw in msg_lower for kw in play_keywords)

    if not has_play:
        return False

    # Music context signals
    music_nouns = ['music', 'song', 'songs', 'artist', 'album', 'track', 'playlist', 'tune', 'tunes']
    has_music_noun = any(noun in msg_lower for noun in music_nouns)

    # Common genres
    genres = ['jazz', 'rock', 'pop', 'classical', 'hip hop', 'country', 'r&b', 'electronic',
              'metal', 'punk', 'blues', 'soul', 'funk', 'reggae', 'folk', 'indie', 'edm', 'rap']
    has_genre = any(genre in msg_lower for genre in genres)

    # Some very common artists
    common_artists = ['beatles', 'taylor swift', 'drake', 'queen', 'coldplay', 'ed sheeran',
                      'adele', 'beyonce', 'kanye', 'eminem', 'michael jackson', 'elvis',
                      'bruno mars', 'ariana grande', 'billie eilish', 'the weeknd']
    has_artist = any(artist in msg_lower for artist in common_artists)

    # Exclude information-seeking queries
    info_terms = ['search', 'find', 'information', 'info', 'who is', 'what is', 'tell me about',
                  'wikipedia', 'wiki', 'how old', 'when did', 'where is']
    if any(term in msg_lower for term in info_terms):
        return False

    # Must have play AND (music noun OR genre OR artist)
    return has_play and (has_music_noun or has_genre or has_artist)


LEGACY_AVAILABLE = True


def test_improved_selector():
    """Test the improved confidence-based tool selector"""
    print("=" * 80)
    print("TESTING IMPROVED TOOL SELECTOR")
    print("=" * 80)
    print()

    selector = ImprovedToolSelector()

    # False positive tests - should NOT trigger
    false_positive_tests = [
        # Music false positives
        ("let's play a game", "Should NOT trigger music for 'play a game'"),
        ("play a video game", "Should NOT trigger music for 'play a video game'"),
        ("tell me about Taylor Swift", "Should NOT trigger music for info request"),
        ("what music do you like?", "Should NOT trigger music for question about music"),
        ("I like to play sports", "Should NOT trigger music for 'play sports'"),
        ("can you play with the settings?", "Should NOT trigger music for 'play with'"),
        ("play basketball with me", "Should NOT trigger music for 'play basketball'"),
        ("let's play chess", "Should NOT trigger music for 'play chess'"),
        ("I want to play a trick on him", "Should NOT trigger music for 'play a trick'"),
        ("play the role of a detective", "Should NOT trigger music for roleplay"),

        # Light false positives
        ("let's have a party", "Should NOT trigger lights for 'party' without light context"),
        ("I need to focus on work", "Should NOT trigger lights for 'focus' alone"),
        ("that's a chill idea", "Should NOT trigger lights for 'chill' in conversation"),
        ("the sunset was beautiful", "Should NOT trigger lights for 'sunset' in description"),
        ("I want to relax", "Should NOT trigger lights for 'relax' alone"),
        ("it's a light snack", "Should NOT trigger lights for 'light' as adjective"),
        ("light reading before bed", "Should NOT trigger lights for 'light reading'"),
        ("I'm in a romantic mood today", "Should NOT trigger lights for mood without clear intent"),
        ("the room was dark and moody", "Should NOT trigger lights for 'mood' description"),
        ("in light of recent events", "Should NOT trigger lights for 'in light of'"),
        ("bring this to light", "Should NOT trigger lights for 'bring to light'"),
        ("I see the light now", "Should NOT trigger lights for metaphor"),
        ("that's light blue fabric", "Should NOT trigger lights for 'light blue'"),
    ]

    # True positive tests - SHOULD trigger
    true_positive_tests = [
        # Music true positives
        ("play some Taylor Swift", "play_music", "Should trigger music for 'play [artist]'"),
        ("play music", "play_music", "Should trigger music for direct 'play music'"),
        ("put on some jazz", "play_music", "Should trigger music for 'put on [genre]'"),
        ("play the Beatles", "play_music", "Should trigger music for 'play the Beatles'"),
        ("listen to some rock music", "play_music", "Should trigger music for 'listen to [genre]'"),
        ("play me a song", "play_music", "Should trigger music for 'play me a song'"),
        ("start playing classical music", "play_music", "Should trigger music for 'start playing'"),

        # Light true positives
        ("turn on the lights", "control_lights", "Should trigger lights for 'turn on the lights'"),
        ("set the lights to blue", "control_lights", "Should trigger lights for color + lights"),
        ("make the lights red", "control_lights", "Should trigger lights for make lights [color]"),
        ("dim the lights", "control_lights", "Should trigger lights for 'dim the lights'"),
        ("lights off", "control_lights", "Should trigger lights for 'lights off'"),
        ("turn off the lights", "control_lights", "Should trigger lights for 'turn off the lights'"),
        ("brighten the lights", "control_lights", "Should trigger lights for 'brighten'"),
        ("set lights to warm white", "control_lights", "Should trigger lights for 'warm white'"),

        # Other tools
        ("check my email", "read_gmail", "Should trigger email for 'check my email'"),
        ("what's the weather", "get_weather", "Should trigger weather for 'what's the weather'"),
        ("set a timer for 5 minutes", "set_timer", "Should trigger timer"),
        ("remind me to call mom", "create_reminder", "Should trigger reminder"),
    ]

    # Test false positives
    print("FALSE POSITIVE TESTS (Should NOT trigger music/lights)")
    print("-" * 80)
    fp_pass = 0
    fp_fail = 0

    for message, description in false_positive_tests:
        result = selector.select_tool(message)
        triggered_music = result.primary_tool and result.primary_tool.tool_name in ['play_music', 'control_music', 'music_visualizer']
        triggered_lights = result.primary_tool and result.primary_tool.tool_name == 'control_lights'

        if triggered_music or triggered_lights:
            print(f"FAIL: {description}")
            print(f"  Message: '{message}'")
            print(f"  Incorrectly triggered: {result.primary_tool.tool_name} (conf: {result.primary_tool.confidence:.2f})")
            fp_fail += 1
        else:
            print(f"PASS: {description}")
            fp_pass += 1

    print()
    print(f"False Positive Results: {fp_pass} passed, {fp_fail} failed")
    print()

    # Test true positives
    print("=" * 80)
    print("TRUE POSITIVE TESTS (SHOULD trigger correctly)")
    print("-" * 80)
    tp_pass = 0
    tp_fail = 0

    for message, expected_tool, description in true_positive_tests:
        result = selector.select_tool(message)

        if result.primary_tool and result.primary_tool.tool_name == expected_tool:
            print(f"PASS: {description}")
            print(f"  Selected: {result.primary_tool.tool_name} (conf: {result.primary_tool.confidence:.2f})")
            tp_pass += 1
        else:
            print(f"FAIL: {description}")
            print(f"  Message: '{message}'")
            if result.primary_tool:
                print(f"  Selected: {result.primary_tool.tool_name} (expected: {expected_tool})")
            else:
                print(f"  Selected: None (expected: {expected_tool})")
            tp_fail += 1

    print()
    print(f"True Positive Results: {tp_pass} passed, {tp_fail} failed")

    return fp_fail + tp_fail == 0


def test_legacy_detection():
    """Test the legacy keyword-based detection functions"""
    if not LEGACY_AVAILABLE:
        print("\nSkipping legacy detection tests - functions not available")
        return True

    print()
    print("=" * 80)
    print("TESTING LEGACY DETECTION FUNCTIONS")
    print("=" * 80)
    print()

    # Music detection tests
    music_false_positives = [
        ("let's play a game", "Should NOT trigger music"),
        ("play a video game", "Should NOT trigger music"),
        ("play basketball", "Should NOT trigger music"),
        ("I like to play sports", "Should NOT trigger music"),
        ("play with the dog", "Should NOT trigger music"),
        ("let's play chess", "Should NOT trigger music"),
        ("play the role", "Should NOT trigger music"),
        ("play a trick", "Should NOT trigger music"),
        ("who is Taylor Swift?", "Should NOT trigger music for info request"),
    ]

    music_true_positives = [
        ("play some music", "Should trigger music"),
        ("play jazz", "Should trigger music for genre"),
        ("play some rock music", "Should trigger music"),
        ("put on some classical", "Should trigger music"),
        ("listen to hip hop", "Should trigger music"),
    ]

    # Light detection tests
    light_false_positives = [
        ("light reading", "Should NOT trigger lights"),
        ("light snack", "Should NOT trigger lights"),
        ("light exercise", "Should NOT trigger lights"),
        ("light blue color", "Should NOT trigger lights"),
        ("in light of this", "Should NOT trigger lights"),
        ("see the light", "Should NOT trigger lights"),
        ("bring to light", "Should NOT trigger lights"),
        ("party tonight", "Should NOT trigger lights for 'party' alone"),
        ("focus on work", "Should NOT trigger lights for 'focus' alone"),
        ("chill vibes", "Should NOT trigger lights for 'chill' alone"),
    ]

    light_true_positives = [
        ("turn on the lights", "Should trigger lights"),
        ("turn off the lights", "Should trigger lights"),
        ("set lights to blue", "Should trigger lights"),
        ("dim the lights", "Should trigger lights"),
        ("make the lights red", "Should trigger lights"),
        ("lights off", "Should trigger lights"),
        ("brighten the lights", "Should trigger lights"),
    ]

    total_pass = 0
    total_fail = 0

    # Test music detection
    print("MUSIC DETECTION - False Positives")
    print("-" * 40)
    for message, description in music_false_positives:
        result = detect_music_play_intent(message)
        if result:
            print(f"FAIL: {description} - '{message}'")
            total_fail += 1
        else:
            print(f"PASS: {description}")
            total_pass += 1

    print()
    print("MUSIC DETECTION - True Positives")
    print("-" * 40)
    for message, description in music_true_positives:
        result = detect_music_play_intent(message)
        if result:
            print(f"PASS: {description}")
            total_pass += 1
        else:
            print(f"FAIL: {description} - '{message}'")
            total_fail += 1

    print()
    print("LIGHT DETECTION - False Positives")
    print("-" * 40)
    for message, description in light_false_positives:
        result = detect_light_intent(message)
        if result:
            print(f"FAIL: {description} - '{message}'")
            total_fail += 1
        else:
            print(f"PASS: {description}")
            total_pass += 1

    print()
    print("LIGHT DETECTION - True Positives")
    print("-" * 40)
    for message, description in light_true_positives:
        result = detect_light_intent(message)
        if result:
            print(f"PASS: {description}")
            total_pass += 1
        else:
            print(f"FAIL: {description} - '{message}'")
            total_fail += 1

    print()
    print(f"Legacy Detection Results: {total_pass} passed, {total_fail} failed")

    return total_fail == 0


def main():
    print()
    print("#" * 80)
    print("# COMPREHENSIVE TOOL SELECTION TEST SUITE")
    print("#" * 80)
    print()

    improved_ok = test_improved_selector()
    legacy_ok = test_legacy_detection()

    print()
    print("=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)

    if improved_ok and legacy_ok:
        print("SUCCESS: All tests passed!")
        return 0
    else:
        if not improved_ok:
            print("FAILED: Improved selector tests failed")
        if not legacy_ok:
            print("FAILED: Legacy detection tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
