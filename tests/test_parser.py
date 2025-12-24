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
