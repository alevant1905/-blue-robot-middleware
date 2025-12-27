#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactive Tool Selector Test Script
======================================

Test the improved tool selector with real queries.
"""

import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from blue.tool_selector import ImprovedToolSelector

def test_query(selector, query, expected_tool=None):
    """Test a single query and display results."""
    print(f"\n{'='*70}")
    print(f"Query: '{query}'")
    print(f"{'='*70}")

    result = selector.select_tool(query, [])

    if result.primary_tool:
        print(f"[+] Tool Selected: {result.primary_tool.tool_name}")
        print(f"  Confidence: {result.primary_tool.confidence:.2f}")
        print(f"  Priority: {result.primary_tool.priority}")
        print(f"  Reason: {result.primary_tool.reason}")
        if result.primary_tool.extracted_params:
            print(f"  Parameters: {result.primary_tool.extracted_params}")

        if expected_tool and result.primary_tool.tool_name != expected_tool:
            print(f"  [!] Expected '{expected_tool}', got '{result.primary_tool.tool_name}'")

        if result.alternative_tools:
            print(f"\n  Alternatives ({len(result.alternative_tools)}):")
            for alt in result.alternative_tools[:3]:
                print(f"    - {alt.tool_name} (confidence: {alt.confidence:.2f})")

        if result.needs_disambiguation:
            print(f"\n  [!] Disambiguation needed!")
            print(f"  Question: {result.disambiguation_prompt}")

        if result.compound_request:
            print(f"\n  [i] Compound request detected")
    else:
        print("[-] No tool selected (casual conversation)")
        if expected_tool:
            print(f"  [!] Expected '{expected_tool}' but got nothing")

    return result


def run_test_suite():
    """Run a comprehensive test suite."""
    print("\n" + "="*70)
    print("TOOL SELECTOR TEST SUITE")
    print("="*70)

    selector = ImprovedToolSelector()

    # Music tests
    print("\n\n### MUSIC TESTS ###")
    test_query(selector, "play some Taylor Swift", "play_music")
    test_query(selector, "play beatls", "play_music")  # Typo test - should fuzzy match
    test_query(selector, "play jazz music", "play_music")
    test_query(selector, "pause the music", "control_music")
    test_query(selector, "skip this song", "control_music")
    test_query(selector, "turn up the volume", "control_music")

    # Non-music "play" contexts (should NOT trigger music)
    print("\n\n### NON-MUSIC 'PLAY' TESTS (Should NOT trigger music) ###")
    test_query(selector, "let's play a game", None)
    test_query(selector, "play video games", None)
    test_query(selector, "I like to play sports", None)

    # Lights tests
    print("\n\n### LIGHTS TESTS ###")
    test_query(selector, "turn on the lights", "control_lights")
    test_query(selector, "set lights to blue", "control_lights")
    test_query(selector, "dim the lights", "control_lights")
    test_query(selector, "lights off", "control_lights")

    # Non-lights "light" contexts (should NOT trigger lights)
    print("\n\n### NON-LIGHTS 'LIGHT' TESTS (Should NOT trigger lights) ###")
    test_query(selector, "light reading before bed", None)
    test_query(selector, "light snack", None)

    # Gmail tests
    print("\n\n### GMAIL TESTS ###")
    test_query(selector, "check my email", "read_gmail")
    test_query(selector, "read my gmail", "read_gmail")
    test_query(selector, "send email to john", "send_gmail")

    # Compound requests
    print("\n\n### COMPOUND REQUEST TESTS ###")
    test_query(selector, "turn on lights and play music", "control_lights")  # Should detect compound
    test_query(selector, "play music then turn off the lights", "play_music")  # Should detect compound

    # Casual conversation (should NOT trigger tools)
    print("\n\n### CASUAL CONVERSATION (Should NOT trigger tools) ###")
    test_query(selector, "hello", None)
    test_query(selector, "thanks", None)
    test_query(selector, "that's great", None)

    # Context-aware tests
    print("\n\n### CONTEXT-AWARE TESTS ###")
    history = [
        {'role': 'user', 'content': 'play some music', 'tool_used': 'play_music'},
        {'role': 'assistant', 'content': 'Playing music...'}
    ]
    print("\n(With music context in history)")
    result = selector.select_tool("skip this", history)
    print(f"Query: 'skip this' (with music context)")
    if result.primary_tool:
        print(f"[+] Tool: {result.primary_tool.tool_name} (confidence: {result.primary_tool.confidence:.2f})")

    print("\n\n" + "="*70)
    print("TEST SUITE COMPLETE")
    print("="*70)


def interactive_mode():
    """Interactive mode - keep testing queries."""
    print("\n" + "="*70)
    print("INTERACTIVE TOOL SELECTOR TEST")
    print("="*70)
    print("Enter queries to test tool selection.")
    print("Type 'exit' or 'quit' to stop.\n")

    selector = ImprovedToolSelector()
    conversation_history = []

    while True:
        try:
            query = input("\nEnter query > ").strip()

            if not query:
                continue

            if query.lower() in ['exit', 'quit', 'q']:
                print("Goodbye!")
                break

            # Special commands
            if query.lower() == 'clear':
                conversation_history = []
                print("Conversation history cleared.")
                continue

            if query.lower() == 'history':
                print(f"\nConversation history ({len(conversation_history)} messages):")
                for i, msg in enumerate(conversation_history[-5:], 1):
                    print(f"  {i}. {msg['role']}: {msg['content'][:50]}...")
                continue

            # Test the query
            result = test_query(selector, query)

            # Add to history
            conversation_history.append({'role': 'user', 'content': query})
            if result.primary_tool:
                conversation_history.append({
                    'role': 'assistant',
                    'content': f"Executed {result.primary_tool.tool_name}",
                    'tool_used': result.primary_tool.tool_name
                })

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


def main():
    """Main entry point."""

    if len(sys.argv) > 1:
        if sys.argv[1] == 'suite':
            run_test_suite()
        elif sys.argv[1] == 'interactive':
            interactive_mode()
        else:
            # Test specific query
            query = ' '.join(sys.argv[1:])
            selector = ImprovedToolSelector()
            test_query(selector, query)
    else:
        # Default: show menu
        print("\nTool Selector Test Options:")
        print("  1. Run full test suite")
        print("  2. Interactive mode")
        print("  3. Exit")

        choice = input("\nChoose option (1-3): ").strip()

        if choice == '1':
            run_test_suite()
        elif choice == '2':
            interactive_mode()
        else:
            print("Goodbye!")


if __name__ == "__main__":
    main()
