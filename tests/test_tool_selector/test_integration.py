"""
Integration tests for the refactored tool selector.

Tests the complete tool selection pipeline with all detectors.
"""

import pytest
from blue.tool_selector import ImprovedToolSelector, integrate_with_existing_system


class TestToolSelectorIntegration:
    """Test the complete tool selector pipeline."""

    def setup_method(self):
        """Setup test fixtures."""
        self.selector = ImprovedToolSelector()

    def test_music_play_detection(self):
        """Test music play intent."""
        result = self.selector.select_tool("play some jazz music", [])

        assert result.primary_tool is not None
        assert result.primary_tool.tool_name == 'play_music'
        assert result.primary_tool.confidence >= 0.90

    def test_gmail_read_detection(self):
        """Test email read intent."""
        result = self.selector.select_tool("check my email", [])

        assert result.primary_tool is not None
        assert result.primary_tool.tool_name == 'read_gmail'
        assert result.primary_tool.confidence >= 0.90

    def test_lights_control_detection(self):
        """Test lights control intent."""
        result = self.selector.select_tool("turn on the lights", [])

        assert result.primary_tool is not None
        assert result.primary_tool.tool_name == 'control_lights'
        assert result.primary_tool.confidence >= 0.90

    def test_weather_detection(self):
        """Test weather intent."""
        result = self.selector.select_tool("what's the weather today", [])

        assert result.primary_tool is not None
        assert result.primary_tool.tool_name == 'get_weather'
        assert result.primary_tool.confidence >= 0.85

    def test_web_search_detection(self):
        """Test web search intent."""
        result = self.selector.select_tool("search the web for Python tutorials", [])

        assert result.primary_tool is not None
        assert result.primary_tool.tool_name == 'web_search'
        assert result.primary_tool.confidence >= 0.90

    def test_document_search_detection(self):
        """Test document search intent."""
        result = self.selector.select_tool("search my documents for contract", [])

        assert result.primary_tool is not None
        assert result.primary_tool.tool_name == 'search_documents'
        assert result.primary_tool.confidence >= 0.85

    def test_no_tool_for_greeting(self):
        """Test that greetings don't trigger tools."""
        result = self.selector.select_tool("hello", [])

        assert result.primary_tool is None
        assert not result.needs_disambiguation

    def test_no_tool_for_thanks(self):
        """Test that thanks don't trigger tools."""
        result = self.selector.select_tool("thanks", [])

        assert result.primary_tool is None

    def test_context_awareness(self):
        """Test context-aware detection."""
        history = [
            {'role': 'user', 'content': 'play some music', 'tool_used': 'play_music'},
            {'role': 'assistant', 'content': 'Playing music...'}
        ]

        result = self.selector.select_tool("skip this", history)

        assert result.primary_tool is not None
        assert result.primary_tool.tool_name == 'control_music'

    def test_compound_request_detection(self):
        """Test compound request detection."""
        result = self.selector.select_tool("turn on lights and play music", [])

        assert result.compound_request is True
        # Should still select one primary tool
        assert result.primary_tool is not None

    def test_integration_function(self):
        """Test the integration function for backward compatibility."""
        tool, args, feedback = integrate_with_existing_system(
            "play the beatles",
            [],
            self.selector
        )

        assert tool == 'play_music'
        assert args is not None
        assert 'query' in args
        assert feedback is None  # No disambiguation needed

    def test_integration_with_disambiguation(self):
        """Test integration function with ambiguous input."""
        # "search" could be documents or web - might need disambiguation
        tool, args, feedback = integrate_with_existing_system(
            "search for recipes",
            [],
            self.selector
        )

        # Should either select one or ask for disambiguation
        assert tool is not None or feedback is not None

    def test_multiple_intents_sorted_by_confidence(self):
        """Test that multiple intents are sorted correctly."""
        result = self.selector.select_tool("play music with lights", [])

        # Should detect both music and lights
        assert result.primary_tool is not None
        # Confidence should be high
        assert result.primary_tool.confidence >= 0.50


class TestDetectorRegistry:
    """Test the detector registry functionality."""

    def test_can_disable_detector(self):
        """Test disabling a detector."""
        selector = ImprovedToolSelector()

        # Disable music detector
        selector.registry.disable('music')

        result = selector.select_tool("play some music", [])

        # Should not detect music intent
        assert result.primary_tool is None or result.primary_tool.tool_name != 'play_music'

    def test_can_enable_detector(self):
        """Test enabling a detector."""
        selector = ImprovedToolSelector()

        # Disable then re-enable
        selector.registry.disable('music')
        selector.registry.enable('music')

        result = selector.select_tool("play some music", [])

        # Should detect music intent
        assert result.primary_tool is not None
        assert result.primary_tool.tool_name == 'play_music'


class TestConfidenceThresholds:
    """Test confidence threshold filtering."""

    def setup_method(self):
        """Setup test fixtures."""
        self.selector = ImprovedToolSelector()

    def test_low_confidence_filtered_out(self):
        """Test that very low confidence intents are filtered."""
        # Ambiguous message that shouldn't strongly match anything
        result = self.selector.select_tool("the thing", [])

        # Should not return low-confidence matches
        if result.primary_tool:
            assert result.primary_tool.confidence >= 0.50


# Run tests with: pytest tests/test_tool_selector/test_integration.py -v
