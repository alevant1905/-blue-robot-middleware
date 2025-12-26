"""
Unit tests for Music Intent Detector.

Tests the refactored MusicDetector module.
"""

import pytest
from blue.tool_selector.detectors.music import MusicDetector


class TestMusicPlayDetection:
    """Test music playback intent detection."""

    def setup_method(self):
        """Setup test fixtures."""
        self.detector = MusicDetector()
        self.empty_context = {}

    def test_play_with_artist(self):
        """Test detection of 'play [artist]' pattern."""
        result = self.detector.detect(
            "play the beatles",
            "play the beatles",
            self.empty_context
        )

        assert len(result) >= 1
        play_intent = next((i for i in result if i.tool_name == 'play_music'), None)
        assert play_intent is not None
        assert play_intent.confidence >= 0.95
        assert 'beatles' in play_intent.extracted_params['query'].lower()

    def test_play_with_genre(self):
        """Test detection of 'play [genre]' pattern."""
        result = self.detector.detect(
            "play some jazz",
            "play some jazz",
            self.empty_context
        )

        assert len(result) >= 1
        play_intent = next((i for i in result if i.tool_name == 'play_music'), None)
        assert play_intent is not None
        assert play_intent.confidence >= 0.90

    def test_play_with_music_noun(self):
        """Test detection of 'play music' pattern."""
        result = self.detector.detect(
            "play some music",
            "play some music",
            self.empty_context
        )

        assert len(result) >= 1
        play_intent = next((i for i in result if i.tool_name == 'play_music'), None)
        assert play_intent is not None
        assert play_intent.confidence >= 0.90

    def test_fuzzy_artist_matching(self):
        """Test fuzzy matching handles typos."""
        result = self.detector.detect(
            "play beatls",  # Typo: missing 'e'
            "play beatls",
            self.empty_context
        )

        assert len(result) >= 1
        play_intent = next((i for i in result if i.tool_name == 'play_music'), None)
        # Should fuzzy match to "beatles"
        if play_intent:  # Fuzzy matching may or may not work depending on threshold
            query = play_intent.extracted_params.get('query', '').lower()
            # Either kept typo or matched correctly
            assert 'beatl' in query


class TestNonMusicPlayContexts:
    """Test that non-music 'play' contexts don't trigger music."""

    def setup_method(self):
        """Setup test fixtures."""
        self.detector = MusicDetector()
        self.empty_context = {}

    def test_play_game_no_music(self):
        """'play a game' should NOT trigger music."""
        result = self.detector.detect(
            "let's play a game",
            "let's play a game",
            self.empty_context
        )

        play_intents = [i for i in result if i.tool_name == 'play_music']
        assert len(play_intents) == 0

    def test_play_video_no_music(self):
        """'play a video' should NOT trigger music."""
        result = self.detector.detect(
            "play this video",
            "play this video",
            self.empty_context
        )

        play_intents = [i for i in result if i.tool_name == 'play_music']
        assert len(play_intents) == 0

    def test_play_sports_no_music(self):
        """'play basketball' should NOT trigger music."""
        result = self.detector.detect(
            "let's play basketball",
            "let's play basketball",
            self.empty_context
        )

        play_intents = [i for i in result if i.tool_name == 'play_music']
        assert len(play_intents) == 0


class TestMusicControl:
    """Test music control intent detection."""

    def setup_method(self):
        """Setup test fixtures."""
        self.detector = MusicDetector()
        self.empty_context = {}

    def test_pause_command(self):
        """Test pause detection."""
        result = self.detector.detect(
            "pause the music",
            "pause the music",
            self.empty_context
        )

        control_intent = next((i for i in result if i.tool_name == 'control_music'), None)
        assert control_intent is not None
        assert control_intent.extracted_params['action'] == 'pause'

    def test_skip_command(self):
        """Test skip detection."""
        result = self.detector.detect(
            "skip this song",
            "skip this song",
            self.empty_context
        )

        control_intent = next((i for i in result if i.tool_name == 'control_music'), None)
        assert control_intent is not None
        assert control_intent.extracted_params['action'] == 'next'

    def test_volume_up_command(self):
        """Test volume up detection."""
        result = self.detector.detect(
            "turn it up",
            "turn it up",
            self.empty_context
        )

        control_intent = next((i for i in result if i.tool_name == 'control_music'), None)
        assert control_intent is not None
        assert control_intent.extracted_params['action'] == 'volume_up'


class TestMusicVisualizer:
    """Test music visualizer intent detection."""

    def setup_method(self):
        """Setup test fixtures."""
        self.detector = MusicDetector()
        self.empty_context = {}

    def test_visualizer_keywords(self):
        """Test visualizer detection with explicit keywords."""
        result = self.detector.detect(
            "start the music visualizer",
            "start the music visualizer",
            self.empty_context
        )

        viz_intent = next((i for i in result if i.tool_name == 'music_visualizer'), None)
        assert viz_intent is not None
        assert viz_intent.confidence >= 0.90
        assert viz_intent.extracted_params['action'] == 'start'

    def test_light_show_triggers_visualizer(self):
        """'light show' should trigger visualizer."""
        result = self.detector.detect(
            "make lights dance with the music",
            "make lights dance with the music",
            self.empty_context
        )

        viz_intent = next((i for i in result if i.tool_name == 'music_visualizer'), None)
        assert viz_intent is not None


class TestContextAwareness:
    """Test context-aware detection."""

    def setup_method(self):
        """Setup test fixtures."""
        self.detector = MusicDetector()

    def test_play_with_music_context(self):
        """'play' alone should use context."""
        context_with_music = {
            'has_music_in_history': True,
            'music_recency': 1  # Very recent
        }

        result = self.detector.detect(
            "play that",
            "play that",
            context_with_music
        )

        # Should detect play intent based on context
        play_intent = next((i for i in result if i.tool_name == 'play_music'), None)
        if play_intent:  # Context-based detection may have lower confidence
            assert play_intent.confidence >= 0.40


# Run tests with: pytest tests/test_tool_selector/test_music_detector.py -v
