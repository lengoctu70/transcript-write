"""Tests for transcript parser"""
import pytest
from src.transcript_parser import TranscriptParser, TranscriptSegment


class TestTranscriptParser:

    def test_parse_srt(self, tmp_path):
        """Parse valid SRT file"""
        srt_content = """1
00:00:01,000 --> 00:00:04,000
Hello, welcome to the lecture.

2
00:00:05,000 --> 00:00:08,000
Today we'll learn about Python.
"""
        srt_file = tmp_path / "test.srt"
        srt_file.write_text(srt_content)

        parser = TranscriptParser()
        segments = parser.parse(srt_file)

        assert len(segments) == 2
        assert segments[0].text == "Hello, welcome to the lecture."
        assert segments[0].start_time == "00:00:01"

    def test_deduplicate_segments(self, tmp_path):
        """Remove consecutive duplicate lines"""
        srt_content = """1
00:00:01,000 --> 00:00:02,000
Hello world

2
00:00:02,000 --> 00:00:03,000
Hello world

3
00:00:03,000 --> 00:00:04,000
Different text
"""
        srt_file = tmp_path / "test.srt"
        srt_file.write_text(srt_content)

        parser = TranscriptParser()
        segments = parser.parse(srt_file)

        assert len(segments) == 2

    def test_to_plain_text(self):
        """Convert segments to plain text"""
        segments = [
            TranscriptSegment(1, "00:00:01", "00:00:04", "First line"),
            TranscriptSegment(2, "00:00:05", "00:00:08", "Second line"),
        ]

        parser = TranscriptParser()
        text = parser.to_plain_text(segments)

        assert "[00:00:01]" in text
        assert "First line" in text

    def test_to_plain_text_normalization(self):
        """to_plain_text applies whitespace normalization"""
        segments = [
            TranscriptSegment(1, "00:00:01", "00:00:04", "First line"),
            TranscriptSegment(2, "00:00:01", "00:00:04", "Same timestamp"),
            TranscriptSegment(3, "00:00:10", "00:00:15", "Later line"),
        ]

        parser = TranscriptParser()
        text = parser.to_plain_text(segments)

        # Should not have excessive newlines
        assert "\n\n\n" not in text
        # Should contain all content
        assert "First line" in text
        assert "Same timestamp" in text
        assert "Later line" in text


class TestWhitespaceNormalization:
    """Tests for _normalize_transcript_whitespace method"""

    @pytest.fixture
    def parser(self):
        return TranscriptParser()

    def test_collapse_multiple_newlines(self, parser):
        """Multiple newlines collapse to max 2"""
        text = "Line 1\n\n\n\nLine 2"
        result = parser._normalize_transcript_whitespace(text)
        assert result == "Line 1\n\nLine 2"

    def test_timestamp_whitespace_removal(self, parser):
        """Whitespace around timestamps removed"""
        text = "Text before\n\n\n[00:01:30]\n\n\nText after"
        result = parser._normalize_transcript_whitespace(text)
        assert "[00:01:30] Text" in result
        assert "\n\n\n" not in result

    def test_line_level_strip(self, parser):
        """Line-level whitespace stripped"""
        text = "  Line with spaces  \n  Another line  "
        result = parser._normalize_transcript_whitespace(text)
        assert result == "Line with spaces\nAnother line"

    def test_empty_lines_removed(self, parser):
        """Empty lines between content collapsed"""
        text = "Content\n\n\n\n\nMore content"
        result = parser._normalize_transcript_whitespace(text)
        assert result == "Content\n\nMore content"

    def test_preserves_single_paragraph_break(self, parser):
        """Single paragraph breaks preserved"""
        text = "Paragraph 1\n\nParagraph 2"
        result = parser._normalize_transcript_whitespace(text)
        assert result == "Paragraph 1\n\nParagraph 2"

    def test_complex_srt_pattern(self, parser):
        """Handle realistic SRT output pattern"""
        text = """
[00:00:01]
Hello world.


[00:00:05]
This is a test.


[00:00:10]
Final line.
"""
        result = parser._normalize_transcript_whitespace(text)
        # Should have minimal whitespace
        assert "\n\n\n" not in result
        # Timestamps should be inline with following text
        assert "[00:00:01] Hello" in result or "[00:00:01]\nHello" in result

    def test_empty_input(self, parser):
        """Empty string returns empty"""
        result = parser._normalize_transcript_whitespace("")
        assert result == ""

    def test_no_timestamps(self, parser):
        """Works on text without timestamps"""
        text = "Just regular\n\n\n\ntext here"
        result = parser._normalize_transcript_whitespace(text)
        assert result == "Just regular\n\ntext here"
