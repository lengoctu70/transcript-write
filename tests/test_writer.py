"""Tests for Markdown writer"""
import pytest
import json
from pathlib import Path
from src.markdown_writer import (
    TranscriptMetadata,
    MarkdownWriter
)
from src.llm_processor import ProcessedChunk
from datetime import datetime


class TestTranscriptMetadata:
    """Test TranscriptMetadata dataclass"""

    def test_metadata_creation(self):
        """Create metadata with all fields"""
        metadata = TranscriptMetadata(
            title="Test Video Title",
            original_duration="00:10:30",
            processed_at="2024-01-15T10:30:00",
            model="claude-3-5-sonnet-20241022",
            total_cost=0.0150,
            chunks_processed=3,
            input_tokens=1500,
            output_tokens=1200
        )
        assert metadata.title == "Test Video Title"
        assert metadata.original_duration == "00:10:30"
        assert metadata.total_cost == 0.0150
        assert metadata.chunks_processed == 3

    def test_metadata_without_duration(self):
        """Create metadata without optional duration"""
        metadata = TranscriptMetadata(
            title="Test",
            original_duration=None,
            processed_at="2024-01-15T10:30:00",
            model="claude-3-5-sonnet-20241022",
            total_cost=0.01,
            chunks_processed=1,
            input_tokens=100,
            output_tokens=80
        )
        assert metadata.original_duration is None


class TestMarkdownWriter:
    """Test MarkdownWriter class"""

    def test_init_creates_output_dir(self, tmp_path):
        """Initialize writer and create output directory"""
        output_dir = tmp_path / "custom_output"
        writer = MarkdownWriter(str(output_dir))
        assert writer.output_dir == output_dir
        assert output_dir.exists()

    def test_init_default_output_dir(self, tmp_path):
        """Initialize with default output directory"""
        writer = MarkdownWriter()
        assert writer.output_dir == Path("output")

    def test_sanitize_filename(self):
        """Sanitize filename by removing invalid characters"""
        writer = MarkdownWriter()
        safe = writer._sanitize_filename('Test/Video:Title?"<>|*File')
        # All invalid chars should be removed
        assert "/" not in safe
        assert ":" not in safe
        assert '"' not in safe
        assert "<" not in safe
        assert ">" not in safe
        assert "|" not in safe
        assert "?" not in safe
        assert "*" not in safe
        # Result should be concatenated without invalid chars
        assert "Test" in safe
        assert "Video" in safe
        assert "Title" in safe
        assert "File" in safe

    def test_sanitize_filename_long_title(self):
        """Truncate long filenames to 50 characters"""
        writer = MarkdownWriter()
        long_title = "A" * 100
        safe = writer._sanitize_filename(long_title)
        assert len(safe) <= 50

    def test_sanitize_filename_replaces_spaces(self):
        """Replace spaces with hyphens"""
        writer = MarkdownWriter()
        safe = writer._sanitize_filename("Test Video Title")
        assert " " not in safe
        assert "-" in safe

    def test_build_markdown(self, tmp_path):
        """Build complete markdown document"""
        writer = MarkdownWriter(str(tmp_path))

        chunks = [
            ProcessedChunk(
                chunk_index=0,
                original_text="Original 1",
                cleaned_text="[00:00:00] First cleaned content.",
                input_tokens=100,
                output_tokens=80,
                cost=0.001,
                model="claude-3-5-sonnet-20241022"
            ),
            ProcessedChunk(
                chunk_index=1,
                original_text="Original 2",
                cleaned_text="[00:01:00] Second cleaned content.",
                input_tokens=120,
                output_tokens=90,
                cost=0.0012,
                model="claude-3-5-sonnet-20241022"
            )
        ]

        metadata = TranscriptMetadata(
            title="Test Video",
            original_duration="00:05:00",
            processed_at="2024-01-15T10:00:00",
            model="claude-3-5-sonnet-20241022",
            total_cost=0.0022,
            chunks_processed=2,
            input_tokens=220,
            output_tokens=170
        )

        md_content = writer._build_markdown(chunks, metadata)

        assert "# Test Video" in md_content
        assert "First cleaned content." in md_content
        assert "Second cleaned content." in md_content
        assert "2024-01-15" in md_content
        assert "claude-3-5-sonnet-20241022" in md_content
        assert "0.0022" in md_content

    def test_metadata_to_dict(self):
        """Convert metadata to dictionary"""
        metadata = TranscriptMetadata(
            title="Test Title",
            original_duration="00:10:00",
            processed_at="2024-01-15T10:00:00",
            model="claude-3-5-sonnet-20241022",
            total_cost=0.015,
            chunks_processed=5,
            input_tokens=1000,
            output_tokens=800
        )

        writer = MarkdownWriter()
        data = writer._metadata_to_dict(metadata)

        assert data["title"] == "Test Title"
        assert data["original_duration"] == "00:10:00"
        assert data["model"] == "claude-3-5-sonnet-20241022"
        assert data["cost_usd"] == 0.015
        assert data["chunks_processed"] == 5
        assert data["tokens"]["input"] == 1000
        assert data["tokens"]["output"] == 800
        assert data["tokens"]["total"] == 1800

    def test_write_creates_files(self, tmp_path):
        """Write markdown and metadata files"""
        writer = MarkdownWriter(str(tmp_path))

        chunks = [
            ProcessedChunk(
                chunk_index=0,
                original_text="Original",
                cleaned_text="[00:00:00] Cleaned content.",
                input_tokens=50,
                output_tokens=40,
                cost=0.0005,
                model="claude-3-5-sonnet-20241022"
            )
        ]

        summary = {
            "model": "claude-3-5-sonnet-20241022",
            "total_cost": 0.0005,
            "chunks_processed": 1,
            "total_input_tokens": 50,
            "total_output_tokens": 40
        }

        md_path, json_path = writer.write(
            processed_chunks=chunks,
            title="Test Video",
            summary=summary,
            duration="00:03:00"
        )

        assert md_path.exists()
        assert json_path.exists()
        assert md_path.suffix == ".md"
        assert json_path.name.endswith("-metadata.json")

    def test_write_markdown_content(self, tmp_path):
        """Verify markdown file content"""
        writer = MarkdownWriter(str(tmp_path))

        chunks = [
            ProcessedChunk(
                chunk_index=0,
                original_text="Original",
                cleaned_text="[00:00:00] Cleaned transcript content.",
                input_tokens=30,
                output_tokens=25,
                cost=0.0003,
                model="claude-3-5-sonnet-20241022"
            )
        ]

        summary = {
            "model": "claude-3-5-sonnet-20241022",
            "total_cost": 0.0003,
            "chunks_processed": 1,
            "total_input_tokens": 30,
            "total_output_tokens": 25
        }

        md_path, _ = writer.write(
            processed_chunks=chunks,
            title="My Test Video",
            summary=summary
        )

        content = md_path.read_text(encoding="utf-8")
        assert "# My Test Video" in content
        assert "[00:00:00] Cleaned transcript content." in content
        assert "Duration:" not in content  # No duration provided

    def test_write_json_metadata(self, tmp_path):
        """Verify JSON metadata file content"""
        writer = MarkdownWriter(str(tmp_path))

        chunks = [
            ProcessedChunk(
                chunk_index=0,
                original_text="Original",
                cleaned_text="Cleaned",
                input_tokens=100,
                output_tokens=80,
                cost=0.001,
                model="claude-3-5-sonnet-20241022"
            )
        ]

        summary = {
            "model": "claude-3-5-sonnet-20241022",
            "total_cost": 0.001,
            "chunks_processed": 1,
            "total_input_tokens": 100,
            "total_output_tokens": 80
        }

        _, json_path = writer.write(
            processed_chunks=chunks,
            title="Test Video",
            summary=summary,
            duration="00:05:00"
        )

        metadata = json.loads(json_path.read_text(encoding="utf-8"))
        assert metadata["title"] == "Test Video"
        assert metadata["original_duration"] == "00:05:00"
        assert metadata["model"] == "claude-3-5-sonnet-20241022"
        assert metadata["cost_usd"] == 0.001
        assert metadata["tokens"]["total"] == 180

    def test_write_multiple_chunks(self, tmp_path):
        """Write multiple chunks in sequence"""
        writer = MarkdownWriter(str(tmp_path))

        chunks = [
            ProcessedChunk(
                chunk_index=0,
                original_text="O1",
                cleaned_text="[00:00:00] First chunk.",
                input_tokens=20,
                output_tokens=15,
                cost=0.0002,
                model="claude-3-5-sonnet-20241022"
            ),
            ProcessedChunk(
                chunk_index=1,
                original_text="O2",
                cleaned_text="[00:01:00] Second chunk.",
                input_tokens=25,
                output_tokens=20,
                cost=0.00025,
                model="claude-3-5-sonnet-20241022"
            ),
            ProcessedChunk(
                chunk_index=2,
                original_text="O3",
                cleaned_text="[00:02:00] Third chunk.",
                input_tokens=30,
                output_tokens=25,
                cost=0.0003,
                model="claude-3-5-sonnet-20241022"
            )
        ]

        summary = {
            "model": "claude-3-5-sonnet-20241022",
            "total_cost": 0.00075,
            "chunks_processed": 3,
            "total_input_tokens": 75,
            "total_output_tokens": 60
        }

        md_path, _ = writer.write(
            processed_chunks=chunks,
            title="Multi Chunk Test",
            summary=summary
        )

        content = md_path.read_text(encoding="utf-8")
        assert "First chunk." in content
        assert "Second chunk." in content
        assert "Third chunk." in content
        # Verify order maintained
        first_pos = content.find("First chunk.")
        second_pos = content.find("Second chunk.")
        third_pos = content.find("Third chunk.")
        assert first_pos < second_pos < third_pos

    def test_get_content_for_preview_full(self, tmp_path):
        """Get full preview for short content"""
        writer = MarkdownWriter(str(tmp_path))

        chunks = [
            ProcessedChunk(
                chunk_index=0,
                original_text="Original",
                cleaned_text="Short content",
                input_tokens=10,
                output_tokens=8,
                cost=0.0001,
                model="claude-3-5-sonnet-20241022"
            )
        ]

        preview = writer.get_content_for_preview(chunks, max_chars=1000)
        assert "Short content" in preview
        assert "..." not in preview  # Not truncated

    def test_get_content_for_preview_truncated(self, tmp_path):
        """Get truncated preview for long content"""
        writer = MarkdownWriter(str(tmp_path))

        chunks = [
            ProcessedChunk(
                chunk_index=0,
                original_text="Original",
                cleaned_text="A" * 10000,  # Very long content
                input_tokens=1000,
                output_tokens=800,
                cost=0.01,
                model="claude-3-5-sonnet-20241022"
            )
        ]

        preview = writer.get_content_for_preview(chunks, max_chars=1000)
        assert len(preview) <= 1100  # Allow some buffer for "..."
        assert "..." in preview  # Should be truncated

    def test_get_content_for_preview_multiple_chunks(self, tmp_path):
        """Preview stops at max_chars across multiple chunks"""
        writer = MarkdownWriter(str(tmp_path))

        chunks = [
            ProcessedChunk(
                chunk_index=0,
                original_text="O1",
                cleaned_text="A" * 3000,
                input_tokens=500,
                output_tokens=400,
                cost=0.005,
                model="claude-3-5-sonnet-20241022"
            ),
            ProcessedChunk(
                chunk_index=1,
                original_text="O2",
                cleaned_text="B" * 3000,
                input_tokens=500,
                output_tokens=400,
                cost=0.005,
                model="claude-3-5-sonnet-20241022"
            )
        ]

        preview = writer.get_content_for_preview(chunks, max_chars=5000)
        # Should include first chunk and part of second
        assert "A" in preview
        assert "..." in preview

    def test_get_content_for_preview_empty_chunks(self, tmp_path):
        """Handle empty chunks gracefully"""
        writer = MarkdownWriter(str(tmp_path))
        preview = writer.get_content_for_preview([])
        assert preview == ""

    def test_write_with_special_characters_in_title(self, tmp_path):
        """Write files with special characters in title"""
        writer = MarkdownWriter(str(tmp_path))

        chunks = [
            ProcessedChunk(
                chunk_index=0,
                original_text="Original",
                cleaned_text="Cleaned",
                input_tokens=10,
                output_tokens=8,
                cost=0.0001,
                model="claude-3-5-sonnet-20241022"
            )
        ]

        summary = {
            "model": "claude-3-5-sonnet-20241022",
            "total_cost": 0.0001,
            "chunks_processed": 1,
            "total_input_tokens": 10,
            "total_output_tokens": 8
        }

        md_path, json_path = writer.write(
            processed_chunks=chunks,
            title='Video: "What is Python?" (2024)',
            summary=summary
        )

        # Files should be created with sanitized names
        assert md_path.exists()
        assert json_path.exists()
        assert ":" not in md_path.name
        assert '"' not in md_path.name
        assert "?" not in md_path.name

    def test_write_empty_chunks(self, tmp_path):
        """Handle empty cleaned text"""
        writer = MarkdownWriter(str(tmp_path))

        chunks = [
            ProcessedChunk(
                chunk_index=0,
                original_text="Original",
                cleaned_text="   ",  # Whitespace only
                input_tokens=10,
                output_tokens=0,
                cost=0.0,
                model="claude-3-5-sonnet-20241022"
            )
        ]

        summary = {
            "model": "claude-3-5-sonnet-20241022",
            "total_cost": 0.0,
            "chunks_processed": 1,
            "total_input_tokens": 10,
            "total_output_tokens": 0
        }

        md_path, _ = writer.write(
            processed_chunks=chunks,
            title="Empty Test",
            summary=summary
        )

        content = md_path.read_text(encoding="utf-8")
        # Should have header but no content
        assert "# Empty Test" in content
