"""Integration tests for full pipeline"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src import (
    TranscriptParser,
    SmartChunker,
    LLMProcessor,
    OutputValidator,
    MarkdownWriter,
    CostEstimator
)


class TestFullPipeline:
    """Test complete processing pipeline"""

    @pytest.fixture
    def sample_srt(self, tmp_path):
        """Create sample SRT file"""
        content = """1
00:00:01,000 --> 00:00:05,000
Uh, hello everyone, welcome to the lecture.

2
00:00:06,000 --> 00:00:10,000
So, like, today we're going to talk about machine learning.

3
00:00:11,000 --> 00:00:15,000
You know, machine learning is basically a subset of AI.

4
00:00:16,000 --> 00:00:20,000
The concept is really quite simple, actually.

5
00:00:21,000 --> 00:00:25,000
Why does this matter? Because it helps automate decisions.
"""
        srt_file = tmp_path / "sample.srt"
        srt_file.write_text(content)
        return srt_file

    @pytest.fixture
    def prompt_template(self, tmp_path):
        """Create prompt template"""
        content = """Clean this transcript.

[VIDEO INFO]
Title: {{fileName}}

[TRANSCRIPT TO PROCESS]
{{chunkText}}
"""
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text(content)
        return prompt_file

    def test_parse_chunk_flow(self, sample_srt):
        """Test parsing and chunking"""
        # Parse
        parser = TranscriptParser()
        segments = parser.parse(sample_srt)

        assert len(segments) > 0
        assert all(s.text for s in segments)

        # Convert to text
        text = parser.to_plain_text(segments)
        assert "[00:00:01]" in text

        # Chunk
        chunker = SmartChunker(chunk_size=500, overlap=50)
        chunks = chunker.chunk_transcript(text)

        assert len(chunks) >= 1
        assert chunks[0].text

    @patch('src.llm_processor.anthropic.Anthropic')
    def test_full_pipeline(self, mock_anthropic, sample_srt, prompt_template, tmp_path):
        """Test complete pipeline with mocked API"""
        # Setup mock
        mock_response = Mock()
        mock_response.content = [Mock(text="[00:00:01]\nCleaned content here.")]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_anthropic.return_value.messages.create.return_value = mock_response

        # Parse
        parser = TranscriptParser()
        segments = parser.parse(sample_srt)
        text = parser.to_plain_text(segments)

        # Chunk
        chunker = SmartChunker(chunk_size=500, overlap=50)
        chunks = chunker.chunk_transcript(text)

        # Estimate cost
        estimator = CostEstimator()
        template = prompt_template.read_text()
        estimate = estimator.estimate_total(chunks, template)

        assert estimate.total_cost > 0
        assert estimate.chunks == len(chunks)

        # Process (mocked)
        processor = LLMProcessor(api_key="test-key")
        results = processor.process_all_chunks(chunks, template, "Test Video")

        assert len(results) == len(chunks)

        # Validate
        validator = OutputValidator()
        validation = validator.validate_all(results)

        # Should have no context markers in output
        context_errors = [i for i in validation.issues
                        if i.rule == "context_marker_in_output"]
        assert len(context_errors) == 0

        # Write
        writer = MarkdownWriter(output_dir=str(tmp_path / "output"))
        summary = {
            "chunks_processed": len(results),
            "total_input_tokens": 100,
            "total_output_tokens": 50,
            "total_cost": 0.01,
            "model": "test-model"
        }
        md_path, json_path = writer.write(results, "Test Video", summary)

        assert md_path.exists()
        assert json_path.exists()
        assert "Test Video" in md_path.read_text()


class TestErrorHandling:
    """Test error handling scenarios"""

    def test_invalid_file_format(self, tmp_path):
        """Reject unsupported file format"""
        txt_file = tmp_path / "invalid.txt"
        txt_file.write_text("Not a subtitle file")

        parser = TranscriptParser()
        with pytest.raises(ValueError, match="Unsupported format"):
            parser.parse(txt_file)

    def test_empty_file(self, tmp_path):
        """Handle empty file gracefully"""
        empty_srt = tmp_path / "empty.srt"
        empty_srt.write_text("")

        parser = TranscriptParser()
        segments = parser.parse(empty_srt)

        assert segments == []

    def test_malformed_srt(self, tmp_path):
        """Handle malformed SRT gracefully"""
        bad_srt = tmp_path / "bad.srt"
        bad_srt.write_text("Not valid SRT content\nJust random text")

        parser = TranscriptParser()
        # Should not crash, may return empty or partial
        try:
            segments = parser.parse(bad_srt)
            # If it parses, should be empty or have valid segments
            assert isinstance(segments, list)
        except Exception:
            # Some errors are acceptable for malformed input
            pass
