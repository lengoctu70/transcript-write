"""Tests for smart chunker"""
import pytest
from src.chunker import SmartChunker, Chunk


class TestSmartChunker:

    def test_basic_chunking(self):
        """Chunk text at target size"""
        text = "A" * 2500
        chunker = SmartChunker(chunk_size=1000, overlap=100)
        chunks = chunker.chunk_transcript(text)

        assert len(chunks) >= 2
        assert chunks[0].index == 0

    def test_sentence_boundary_split(self):
        """Prefer splitting at sentence boundaries"""
        text = "First sentence here. Second sentence follows. " * 50
        chunker = SmartChunker(chunk_size=100, overlap=20)
        chunks = chunker.chunk_transcript(text)

        for chunk in chunks[:-1]:
            assert chunk.text.rstrip().endswith(".")

    def test_context_buffer(self):
        """Second chunk has context from first"""
        text = "First part. " * 100 + "Second part. " * 100
        chunker = SmartChunker(chunk_size=500, overlap=100)
        chunks = chunker.chunk_transcript(text)

        assert chunks[0].context_buffer is None
        assert chunks[1].context_buffer is not None
        assert len(chunks[1].context_buffer) > 0

    def test_timestamp_extraction(self):
        """Extract timestamp from chunk"""
        text = "[00:01:30] This is the content."
        chunker = SmartChunker()
        chunks = chunker.chunk_transcript(text)

        assert chunks[0].start_timestamp == "00:01:30"

    def test_full_text_for_llm(self):
        """Build complete text for LLM with context"""
        chunk = Chunk(
            index=1,
            text="New content here",
            start_timestamp="00:01:00",
            context_buffer="Previous context"
        )

        llm_text = chunk.full_text_for_llm
        assert "[CONTEXT FROM PREVIOUS SECTION]" in llm_text
        assert "Previous context" in llm_text
        assert "[NEW CONTENT TO PROCESS]" in llm_text
        assert "New content here" in llm_text
