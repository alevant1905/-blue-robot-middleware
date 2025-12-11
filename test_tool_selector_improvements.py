"""
Test script for improved tool selector - verify false positives are fixed
"""

import sys
import os

# Add blue package to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from blue.tool_selector import ImprovedToolSelector

def test_tool_selector():
    """Test cases for tool selection improvements"""

    selector = ImprovedToolSelector()

    # Test cases that should NOT trigger music or lights
    false_positive_tests = [
        # Should NOT trigger music
        ("let's play a game", None, "Should not trigger music for 'play a game'"),
        ("play a video game", None, "Should not trigger music for 'play a video game'"),
        ("tell me about Taylor Swift", None, "Should not trigger music for info request"),
        ("what music do you like?", None, "Should not trigger music for question about music"),
        ("I like to play sports", None, "Should not trigger music for 'play sports'"),

        # Should NOT trigger lights
        ("let's have a party", None, "Should not trigger lights for 'party' without light context"),
        ("I need to focus on work", None, "Should not trigger lights for 'focus' alone"),
        ("that's a chill idea", None, "Should not trigger lights for 'chill' in conversation"),
        ("the sunset was beautiful", None, "Should not trigger lights for 'sunset' in description"),
        ("I want to relax", None, "Should not trigger lights for 'relax' alone"),
        ("it's a light snack", None, "Should not trigger lights for 'light' as adjective"),
        ("light reading before bed", None, "Should not trigger lights for 'light reading'"),

        # Edge cases
        ("can you play with the settings?", None, "Should not trigger music for 'play with'"),
        ("I'm in a romantic mood today", None, "Should not trigger lights for mood without clear intent"),
    ]

    # Test cases that SHOULD trigger music or lights
    true_positive_tests = [
        # Should trigger music
        ("play some Taylor Swift", "play_music", "Should trigger music for 'play [artist]'"),
        ("play music", "play_music", "Should trigger music for direct 'play music'"),
        ("put on some jazz", "play_music", "Should trigger music for 'put on [genre]'"),
        ("play the Beatles", "play_music", "Should trigger music for 'play the Beatles'"),

        # Should trigger lights
        ("turn on the lights", "control_lights", "Should trigger lights for 'turn on the lights'"),
        ("set the lights to blue", "control_lights", "Should trigger lights for color + lights"),
        ("make the lights red", "control_lights", "Should trigger lights for make lights [color]"),
        ("dim the lights", "control_lights", "Should trigger lights for 'dim the lights'"),
        ("lights off", "control_lights", "Should trigger lights for 'lights off'"),
    ]

    print("=" * 80)
    print("TESTING TOOL SELECTOR IMPROVEMENTS")
    print("=" * 80)
    print()

    # Test false positives (should NOT trigger)
    print("FALSE POSITIVE TESTS (Should NOT trigger music/lights)")
    print("-" * 80)
    false_positive_pass = 0
    false_positive_fail = 0

    for message, expected_tool, description in false_positive_tests:
        result = selector.select_tool(message)

        # Check if any music or light tool was selected
        triggered_music = result.primary_tool and result.primary_tool.tool_name in ['play_music', 'control_music', 'music_visualizer']
        triggered_lights = result.primary_tool and result.primary_tool.tool_name == 'control_lights'

        if triggered_music or triggered_lights:
            print(f"FAIL: {description}")
            print(f"  Message: '{message}'")
            print(f"  Incorrectly triggered: {result.primary_tool.tool_name} (confidence: {result.primary_tool.confidence:.2f})")
            print(f"  Reason: {result.primary_tool.reason}")
            print()
            false_positive_fail += 1
        else:
            print(f"PASS: {description}")
            false_positive_pass += 1

    print()
    print(f"False Positive Results: {false_positive_pass} passed, {false_positive_fail} failed")
    print()

    # Test true positives (SHOULD trigger)
    print("=" * 80)
    print("TRUE POSITIVE TESTS (SHOULD trigger correctly)")
    print("-" * 80)
    true_positive_pass = 0
    true_positive_fail = 0

    for message, expected_tool, description in true_positive_tests:
        result = selector.select_tool(message)

        if result.primary_tool and result.primary_tool.tool_name == expected_tool:
            print(f"PASS: {description}")
            print(f"  Correctly selected: {result.primary_tool.tool_name} (confidence: {result.primary_tool.confidence:.2f})")
            true_positive_pass += 1
        else:
            print(f"FAIL: {description}")
            print(f"  Message: '{message}'")
            if result.primary_tool:
                print(f"  Selected: {result.primary_tool.tool_name} (expected: {expected_tool})")
            else:
                print(f"  Selected: None (expected: {expected_tool})")
            print()
            true_positive_fail += 1

    print()
    print(f"True Positive Results: {true_positive_pass} passed, {true_positive_fail} failed")
    print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    total_pass = false_positive_pass + true_positive_pass
    total_fail = false_positive_fail + true_positive_fail
    total_tests = total_pass + total_fail

    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_pass} ({100*total_pass/total_tests:.1f}%)")
    print(f"Failed: {total_fail} ({100*total_fail/total_tests:.1f}%)")
    print()

    if total_fail == 0:
        print("SUCCESS: All tests passed!")
    else:
        print(f"ISSUES: {total_fail} tests failed")

    print("=" * 80)

    return total_fail == 0

if __name__ == "__main__":
    success = test_tool_selector()
    sys.exit(0 if success else 1)
