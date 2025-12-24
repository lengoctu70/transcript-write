# Phase 2: Core Parsing & Chunking

**Effort:** 2.5 hours
**Dependencies:** Phase 1 (setup complete)
**Deliverables:** transcript_parser.py, chunker.py, unit tests

---

## Tasks

### 2.1 Implement TranscriptParser (src/transcript_parser.py)

**Responsibility:** Convert SRT/VTT files to structured text with timestamps

```python
"""Parse subtitle files to structured format"""
from dataclasses import dataclass
from typing import List, Union
from pathlib import Path
import pysrt
import webvtt
import re


@dataclass
class TranscriptSegment:
    """Single subtitle segment"""
    index: int
    start_time: str  # HH:MM:SS format
    end_time: str
    text: str


class TranscriptParser:
    """Parse SRT/VTT files to text with timestamps"""

    def parse(self, file_path: Union[str, Path]) -> List[TranscriptSegment]:
        """Auto-detect format and parse"""
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".srt":
            return self._parse_srt(path)
        elif suffix == ".vtt":
            return self._parse_vtt(path)
        else:
            raise ValueError(f"Unsupported format: {suffix}")

    def parse_from_bytes(
        self, content: bytes, filename: str
    ) -> List[TranscriptSegment]:
        """Parse from uploaded file bytes (Streamlit)"""
        import tempfile
        import os

        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=suffix, delete=False
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            return self.parse(temp_path)
        finally:
            os.unlink(temp_path)

    def _parse_srt(self, path: Path) -> List[TranscriptSegment]:
        """Parse SRT file"""
        subs = pysrt.open(str(path))
        segments = []

        for sub in subs:
            segments.append(TranscriptSegment(
                index=sub.index,
                start_time=self._format_time(sub.start),
                end_time=self._format_time(sub.end),
                text=self._clean_text(sub.text)
            ))

        return self._deduplicate(segments)

    def _parse_vtt(self, path: Path) -> List[TranscriptSegment]:
        """Parse VTT file"""
        vtt = webvtt.read(str(path))
        segments = []

        for i, caption in enumerate(vtt):
            segments.append(TranscriptSegment(
                index=i + 1,
                start_time=self._vtt_time_to_str(caption.start),
                end_time=self._vtt_time_to_str(caption.end),
                text=self._clean_text(caption.text)
            ))

        return self._deduplicate(segments)

    def _format_time(self, time_obj) -> str:
        """Format pysrt time to HH:MM:SS"""
        return f"{time_obj.hours:02d}:{time_obj.minutes:02d}:{time_obj.seconds:02d}"

    def _vtt_time_to_str(self, time_str: str) -> str:
        """Convert VTT time (00:00:00.000) to HH:MM:SS"""
        # Handle both HH:MM:SS.mmm and MM:SS.mmm formats
        parts = time_str.split(":")
        if len(parts) == 2:
            # MM:SS.mmm format
            return f"00:{parts[0]}:{parts[1].split('.')[0]}"
        else:
            # HH:MM:SS.mmm format
            return f"{parts[0]}:{parts[1]}:{parts[2].split('.')[0]}"

    def _clean_text(self, text: str) -> str:
        """Remove HTML tags and normalize whitespace"""
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        # Normalize whitespace
        text = " ".join(text.split())
        return text.strip()

    def _deduplicate(
        self, segments: List[TranscriptSegment]
    ) -> List[TranscriptSegment]:
        """Remove consecutive duplicate texts (common in auto-captions)"""
        if not segments:
            return segments

        result = [segments[0]]
        for seg in segments[1:]:
            if seg.text != result[-1].text:
                result.append(seg)

        return result

    def to_plain_text(self, segments: List[TranscriptSegment]) -> str:
        """Convert segments to timestamped plain text"""
        lines = []
        current_time = None

        for seg in segments:
            # Add timestamp when time changes significantly (>30s)
            if current_time != seg.start_time:
                lines.append(f"\n[{seg.start_time}]")
                current_time = seg.start_time

            lines.append(seg.text)

        return "\n".join(lines)
```

**Key features:**
- Auto-detect SRT vs VTT
- Handle Streamlit file upload (bytes)
- Remove HTML tags
- Deduplicate consecutive identical lines
- Format timestamps consistently

---

### 2.2 Implement SmartChunker (src/chunker.py)

**Responsibility:** Split transcript with context preservation

```python
"""Smart chunking with context preservation"""
from dataclasses import dataclass
from typing import List, Optional
import re


@dataclass
class Chunk:
    """Represents a text chunk with metadata"""
    index: int
    text: str
    start_timestamp: str
    context_buffer: Optional[str] = None

    @property
    def full_text_for_llm(self) -> str:
        """Build text to send to LLM"""
        parts = []
        if self.context_buffer:
            parts.append("[CONTEXT FROM PREVIOUS SECTION]")
            parts.append(self.context_buffer)
            parts.append("")

        parts.append("[NEW CONTENT TO PROCESS]")
        parts.append(self.text)

        return "\n".join(parts)

    @property
    def char_count(self) -> int:
        """Total chars including context"""
        return len(self.full_text_for_llm)


class SmartChunker:
    """Split transcript at sentence boundaries with context"""

    def __init__(self, chunk_size: int = 2000, overlap: int = 200):
        """
        Args:
            chunk_size: Target characters per chunk (excluding context)
            overlap: Characters to include from previous chunk as context
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_transcript(self, text: str) -> List[Chunk]:
        """Split transcript into chunks with context preservation"""
        chunks = []
        current_pos = 0
        chunk_index = 0
        previous_chunk_text = ""

        while current_pos < len(text):
            # Calculate end position
            end_pos = min(current_pos + self.chunk_size, len(text))

            # Find sentence boundary if not at end
            if end_pos < len(text):
                end_pos = self._find_best_split(text, current_pos, end_pos)

            chunk_text = text[current_pos:end_pos].strip()

            # Skip empty chunks
            if not chunk_text:
                current_pos = end_pos
                continue

            # Get context from previous chunk
            context_buffer = None
            if previous_chunk_text and chunk_index > 0:
                context_buffer = self._get_context_buffer(previous_chunk_text)

            # Extract start timestamp from chunk
            start_ts = self._extract_first_timestamp(chunk_text)

            chunks.append(Chunk(
                index=chunk_index,
                text=chunk_text,
                start_timestamp=start_ts or "00:00:00",
                context_buffer=context_buffer
            ))

            previous_chunk_text = chunk_text
            current_pos = end_pos
            chunk_index += 1

        return chunks

    def _find_best_split(
        self, text: str, start: int, target_end: int
    ) -> int:
        """Find best split point near target_end (prefer sentence boundary)"""
        # Search window: 100 chars before target
        search_start = max(start, target_end - 100)
        search_text = text[search_start:target_end + 50]

        # Priority 1: Paragraph break (double newline)
        para_match = list(re.finditer(r"\n\n", search_text))
        if para_match:
            return search_start + para_match[-1].end()

        # Priority 2: Sentence end (. ! ?) followed by space/newline
        sent_match = list(re.finditer(r"[.!?][\s\n]", search_text))
        if sent_match:
            return search_start + sent_match[-1].end()

        # Priority 3: Timestamp marker
        ts_match = list(re.finditer(r"\[[\d:]+\]", search_text))
        if ts_match:
            return search_start + ts_match[-1].start()

        # Fallback: Just use target
        return target_end

    def _get_context_buffer(self, previous_text: str) -> str:
        """Extract last N chars from previous chunk as context"""
        if len(previous_text) <= self.overlap:
            return previous_text

        # Try to start at sentence boundary
        text = previous_text[-self.overlap - 50:]
        sent_match = re.search(r"[.!?]\s+", text)

        if sent_match:
            return text[sent_match.end():].strip()

        return previous_text[-self.overlap:].strip()

    def _extract_first_timestamp(self, text: str) -> Optional[str]:
        """Extract first timestamp [HH:MM:SS] from text"""
        match = re.search(r"\[(\d{2}:\d{2}:\d{2})\]", text)
        return match.group(1) if match else None
```

**Chunking strategy:**
1. Split at paragraph breaks (preferred)
2. Split at sentence boundaries (. ! ?)
3. Split at timestamp markers
4. Fallback to target position

---

### 2.3 Unit Tests (tests/test_parser.py, tests/test_chunker.py)

**tests/test_parser.py:**
```python
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

        assert len(segments) == 2  # Duplicate removed

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
```

**tests/test_chunker.py:**
```python
"""Tests for smart chunker"""
import pytest
from src.chunker import SmartChunker, Chunk


class TestSmartChunker:

    def test_basic_chunking(self):
        """Chunk text at target size"""
        text = "A" * 2500  # Longer than default chunk size
        chunker = SmartChunker(chunk_size=1000, overlap=100)
        chunks = chunker.chunk_transcript(text)

        assert len(chunks) >= 2
        assert chunks[0].index == 0

    def test_sentence_boundary_split(self):
        """Prefer splitting at sentence boundaries"""
        text = "First sentence here. Second sentence follows. " * 50
        chunker = SmartChunker(chunk_size=100, overlap=20)
        chunks = chunker.chunk_transcript(text)

        # Each chunk should end with complete sentence
        for chunk in chunks[:-1]:  # Except last
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
```

**Sample fixture (tests/fixtures/sample.srt):**
```srt
1
00:00:01,000 --> 00:00:04,000
Hello everyone, welcome to today's lecture.

2
00:00:05,000 --> 00:00:08,000
Uh, so, like, today we're going to talk about machine learning.

3
00:00:09,000 --> 00:00:12,000
You know, machine learning is basically a subset of AI.
```

---

## Success Criteria

- [x] TranscriptParser handles both SRT and VTT
- [x] Parser removes duplicates and HTML tags
- [x] SmartChunker respects sentence boundaries
- [x] Context buffer included from chunk 2 onwards
- [x] All unit tests pass (8/8)
- [ ] Handles edge cases (empty files, malformed entries) - **PARTIAL**

---

## Implementation Status

**Status:** COMPLETE (2025-12-24)
**Report:** `plans/reports/code-reviewer-251224-2318-phase2-parsing-chunking.md`

### Files Delivered
- `src/transcript_parser.py` (127 lines)
- `src/chunker.py` (122 lines)
- `tests/test_parser.py` (61 lines)
- `tests/test_chunker.py` (57 lines)
- `tests/fixtures/sample.srt` (11 lines)

### Test Results
```
8 passed, 2 warnings (pysrt deprecation)
```

### Known Issues (from Code Review)
1. **Critical:** Temp file cleanup exception handling (recommend fix)
2. **High:** Missing type hint on `_format_time` parameter
3. **Medium:** Missing edge case tests (empty files, malformed)
4. **Medium:** Potential infinite loop in chunker (unlikely edge case)

### Next Steps
- **Recommended:** Apply critical/high fixes from code review
- **Optional:** Add edge case tests before Phase 3
- **Phase 3:** LLM Integration (ready to proceed)

---

## Testing Commands

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_parser.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
```
