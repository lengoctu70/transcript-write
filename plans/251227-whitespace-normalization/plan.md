---
title: "Aggressive Whitespace Normalization for Transcript Parser"
description: "Add whitespace normalization to fix SRT format mismatch causing chunker quality degradation"
status: phase-2-complete
priority: P1
effort: 2h
branch: main
tags: [parser, optimization, cost-reduction]
created: 2025-12-27
updated: 2025-12-27
---

# Aggressive Whitespace Normalization Plan

## Problem Statement

SRT structural whitespace creates false paragraph boundaries in chunker, causing:
- **Current:** 1hr lecture -> 40 chunks, $0.60
- **Target:** 1hr lecture -> 26 chunks, $0.39 (35% savings)

Educational video transcripts only - no edge cases (code blocks, tables, poetry).

---

## Parallel Execution Strategy

```
                    ┌─────────────────────────┐
                    │  Phase 0: Verification  │
                    │  (Sequential - 5 min)   │
                    └──────────┬──────────────┘
                               │
         ┌─────────────────────┴─────────────────────┐
         │                                           │
         ▼                                           ▼
┌─────────────────────┐               ┌─────────────────────────┐
│   Phase 1A: Core    │               │   Phase 1B: Tests       │
│   Implementation    │               │   (Parallel)            │
│   (30 min)          │               │   (25 min)              │
└──────────┬──────────┘               └──────────┬──────────────┘
           │                                     │
           └─────────────────┬───────────────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  Phase 2: Integrate │
                  │  & Verify           │
                  │  (Sequential - 20m) │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  Phase 3: Docs      │
                  │  (10 min)           │
                  └─────────────────────┘
```

---

## Phase 0: Pre-Implementation Verification (5 min)

**Sequential - Must complete first**

### Tasks
1. Run existing test suite to establish baseline
   ```bash
   pytest tests/ -v --tb=short
   ```
2. Verify all 92 tests pass before changes
3. Check `to_plain_text()` output format for sample SRT

### Exit Criteria
- [ ] All 92 tests passing
- [ ] Baseline chunk count documented for test file

---

## Phase 1A: Core Implementation (30 min)

**Can run parallel with Phase 1B**

### Task 1A.1: Add Normalization Function
**File:** `src/transcript_parser.py`

Add after line 102 (after `_clean_text` method):

```python
def _normalize_transcript_whitespace(self, text: str) -> str:
    """Aggressive whitespace normalization for lecture transcripts.

    Designed for educational content only - no code blocks, tables, poetry.
    Reduces false paragraph boundaries from SRT format.

    Args:
        text: Raw transcript text with timestamps

    Returns:
        Normalized text with reduced whitespace
    """
    # Collapse all multiple newlines to max 2 (paragraph break)
    text = re.sub(r'\n{2,}', '\n\n', text)

    # Remove whitespace around timestamps: \n[00:00:00]\n -> \n[00:00:00]
    text = re.sub(r'\n+(\[[\d:]+\])\n+', r'\n\1 ', text)

    # Strip line-level whitespace
    text = '\n'.join(line.strip() for line in text.split('\n'))

    # Remove remaining multiple empty lines
    text = re.sub(r'\n\n+', '\n\n', text)

    return text.strip()
```

### Task 1A.2: Integrate into to_plain_text()
**File:** `src/transcript_parser.py`

Modify `to_plain_text` method (current lines 118-130):

```python
def to_plain_text(self, segments: List[TranscriptSegment]) -> str:
    """Convert segments to timestamped plain text with normalization."""
    lines = []
    current_time = None

    for seg in segments:
        if current_time != seg.start_time:
            lines.append(f"\n[{seg.start_time}]")
            current_time = seg.start_time

        lines.append(seg.text)

    raw_text = "\n".join(lines)
    return self._normalize_transcript_whitespace(raw_text)
```

### Exit Criteria
- [ ] `_normalize_transcript_whitespace()` method added
- [ ] `to_plain_text()` calls normalization after joining lines

---

## Phase 1B: Test Implementation (25 min)

**Can run parallel with Phase 1A**

### Task 1B.1: Add Test Class for Normalization
**File:** `tests/test_parser.py`

Add new test class:

```python
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
```

### Task 1B.2: Add Integration Test for to_plain_text
**File:** `tests/test_parser.py`

Add to existing `TestTranscriptParser` class:

```python
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
```

### Exit Criteria
- [ ] 8 new unit tests for `_normalize_transcript_whitespace`
- [ ] 1 integration test for normalized `to_plain_text`
- [ ] Tests cover: multiple newlines, timestamps, empty lines, edge cases

---

## Phase 2: Integration & Verification (20 min)

**Sequential - Depends on Phase 1A + 1B**

### Task 2.1: Run Full Test Suite
```bash
pytest tests/ -v --tb=short
```

**Expected:** 92 existing + 9 new = 101 tests passing

### Task 2.2: Verify Chunk Reduction
Create temp verification script or manual check:
```bash
# Process sample SRT and compare chunk count
python -c "
from src.transcript_parser import TranscriptParser
from src.chunker import SmartChunker

parser = TranscriptParser()
# Use existing test fixture or sample file
segments = parser.parse('path/to/sample.srt')
text = parser.to_plain_text(segments)
chunker = SmartChunker()
chunks = chunker.chunk(text)
print(f'Chunk count: {len(chunks)}')
"
```

### Task 2.3: API Compatibility Check
Verify no breaking changes:
- `parse()` returns same segment structure
- `to_plain_text()` returns string (now normalized)
- No new required parameters

### Exit Criteria
- [x] All 104 tests pass (baseline 95 + 9 new whitespace tests)
- [x] Normalization verified working (no triple newlines, content preserved)
- [x] No API breaking changes (parse/to_plain_text signatures unchanged)

---

## Phase 3: Documentation (10 min)

**Sequential - After Phase 2**

### Task 3.1: Update system-architecture.md
**File:** `docs/system-architecture.md`

Add to Parser section (after line 95):

```markdown
**Whitespace Normalization:**
The parser applies aggressive whitespace normalization to transcript output:
- Collapses multiple newlines to max 2 (paragraph break)
- Removes excess whitespace around timestamps
- Strips line-level whitespace
- Designed for educational lecture transcripts (no code/tables/poetry)

This reduces chunk count by ~35% for typical 1hr lectures.
```

### Task 3.2: Update Key Methods List
Add to Parser Key Methods section:

```markdown
- `_normalize_transcript_whitespace(text)` - Aggressive whitespace cleanup
```

### Exit Criteria
- [ ] system-architecture.md updated with normalization docs
- [ ] Key methods list includes new function

---

## Implementation Checklist

### Files Modified
| File | Change Type | Lines Changed |
|------|-------------|---------------|
| `src/transcript_parser.py` | Add method + modify method | ~25 lines added |
| `tests/test_parser.py` | Add test class + 1 test | ~60 lines added |
| `docs/system-architecture.md` | Add documentation | ~10 lines added |

### Success Metrics
| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Test count | 92 | 101 | +9 |
| 1hr lecture chunks | 40 | ~26 | -35% |
| 1hr lecture cost | $0.60 | ~$0.39 | -35% |

### Rollback Plan
If issues arise:
1. Revert `to_plain_text()` to remove normalization call
2. Keep `_normalize_transcript_whitespace()` but unused
3. Remove new tests from test file

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Timestamp regex breaks edge case | Low | Medium | Comprehensive test coverage |
| Existing tests fail | Low | High | Run baseline before changes |
| Over-aggressive normalization | Low | Low | Educational content only scope |

---

## Time Estimate

| Phase | Duration | Parallelizable |
|-------|----------|----------------|
| Phase 0 | 5 min | No |
| Phase 1A + 1B | 30 min | Yes (parallel) |
| Phase 2 | 20 min | No |
| Phase 3 | 10 min | No |
| **Total** | **65 min** | - |

**Parallel execution saves:** ~25 minutes vs sequential approach.
