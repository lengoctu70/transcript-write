# Code Standards & Architecture Guidelines

**Version:** 1.0
**Last Updated:** 2025-12-24
**Applies To:** All Python code in src/ and related modules

---

## Core Principles

### YAGNI (You Aren't Gonna Need It)
- Only implement features when explicitly required
- Avoid premature abstraction or "future-proofing"
- Start simple; refactor when patterns emerge

### KISS (Keep It Simple, Stupid)
- Prioritize clarity and readability over cleverness
- Use straightforward solutions before complex ones
- Minimize hidden dependencies and side effects

### DRY (Don't Repeat Yourself)
- Extract common logic into reusable functions
- Use consistent patterns across modules
- Document shared utilities clearly

---

## File Organization

### Directory Structure
```
src/
├── __init__.py
├── transcript_parser.py   # Input handling (SRT, VTT)
├── chunker.py             # Transcript segmentation
├── llm_processor.py       # Claude API integration
├── validator.py           # Output quality checks
├── writer.py              # Markdown generation
└── utils.py               # Shared utilities

prompts/
└── base_prompt.txt     # Claude system prompt

tests/
├── __init__.py
├── fixtures/           # Test data
├── test_parser.py
├── test_chunker.py
├── test_llm_processor.py
├── test_validator.py
└── test_writer.py
```

### File Naming Convention
- Use **kebab-case** for Python files: `parser.py`, `cost_estimator.py`, `quality_validator.py`
- Use **snake_case** for functions and variables: `clean_transcript()`, `chunk_size`
- Use **PascalCase** for classes: `TranscriptParser`, `ContentChunker`
- Use **SCREAMING_SNAKE_CASE** for constants: `MAX_CHUNK_TOKENS`, `API_TIMEOUT_SECONDS`

### File Size Limit
- Target: **<200 lines per file** (including docstrings)
- Rationale: Improves readability, reduces cognitive load, easier testing
- Exception: test files may be longer; break into separate test classes if > 300 lines

---

## Code Style & Formatting

### Python Version
- Minimum: Python 3.9
- Target: Python 3.11+
- Type hints required for function signatures

### Imports
```python
# Standard library first
import os
from pathlib import Path
from typing import Optional, List

# Third-party libraries
import streamlit as st
from anthropic import Anthropic

# Local imports
from src.parser import TranscriptParser
from src.utils import load_prompt
```

### Type Hints
All public functions must include type hints:
```python
def clean_transcript(
    transcript: str,
    model: str = "claude-opus-4.5",
    temperature: float = 0.7
) -> str:
    """Clean and rewrite transcript for study purposes."""
    pass
```

### Docstrings
Use Google-style docstrings:
```python
def chunk_transcript(content: str, max_tokens: int = 4000) -> List[str]:
    """Split transcript into manageable chunks respecting token limits.

    Args:
        content: Raw transcript text
        max_tokens: Maximum tokens per chunk

    Returns:
        List of transcript chunks

    Raises:
        ValueError: If max_tokens < 500
    """
    pass
```

### Error Handling
```python
try:
    result = api_call()
except ValueError as e:
    logger.error(f"Invalid input: {e}")
    raise
except APIError as e:
    logger.warning(f"API error (will retry): {e}")
    # Tenacity handles retry logic
    raise
```

---

## Module Specifications

### 1. Parser Module (`src/parser.py`)
**Purpose:** Convert subtitle and transcript files to structured data

**Key Functions:**
- `parse_srt(file_path: str) -> List[TimestampedSegment]`
- `parse_vtt(file_path: str) -> List[TimestampedSegment]`
- `parse_text(file_path: str) -> List[TimestampedSegment]`

**Output Format:**
```python
@dataclass
class TimestampedSegment:
    timestamp: str        # "00:01:15" format
    content: str          # Transcript text
    duration: Optional[float]  # In seconds
```

### 2. Chunker Module (`src/chunker.py`)
**Purpose:** Split transcripts into token-aware chunks

**Constraints:**
- Max 4000 tokens per chunk (safety margin for Claude context)
- Maintain overlap (last 200 chars of previous chunk) for context
- Respect sentence boundaries when possible

**Key Functions:**
- `chunk_transcript(content: str, max_tokens: int = 4000) -> List[TranscriptChunk]`

### 3. LLM Module (`src/llm_processor.py`)
**Purpose:** Interface with Claude API for transcript cleaning

**Classes:**
- `LLMProcessor` - Main processor class
- `ProcessedChunk` - Result dataclass
- `ProcessingError` - Custom exception

**Features:**
- Load base_prompt.txt dynamically
- Handle token counting with tiktoken
- Implement retry logic via tenacity
- Template variables: `{{fileName}}`, `{{chunkText}}`
- Cost calculation per request
- Progress callback support
- Multiple model support (Sonnet, Haiku)

**Pricing (per 1K tokens, Dec 2024):**
```python
PRICING = {
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.005}
}
```

**Key Functions:**
- `process_chunk(chunk: Chunk, prompt_template: str, video_title: str) -> ProcessedChunk`
- `process_all_chunks(chunks: list[Chunk], prompt_template: str, progress_callback: Optional[Callable]) -> list[ProcessedChunk]`
- `load_prompt_template(template_path: Optional[str]) -> str`
- `_calculate_cost(input_tokens: int, output_tokens: int) -> float`
- `_build_prompt(chunk: Chunk, template: str, video_title: str) -> str`

**Convenience Function:**
```python
def process_transcript(
    chunks: list[Chunk],
    api_key: str,
    video_title: str,
    model: str = "claude-3-5-sonnet-20241022",
    prompt_path: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> tuple[list[ProcessedChunk], dict]
```

### 4. Validator Module (`src/validator.py`)
**Purpose:** Quality assurance on cleaned output

**Classes:**
- `OutputValidator` - Main validator class
- `ValidationResult` - Aggregated validation result
- `ValidationIssue` - Individual issue with severity
- `ValidationSeverity` - Enum (ERROR, WARNING, INFO)

**Checks:**
- Filler word detection (uh, um, like, basically, etc.)
- Context marker detection (template markers shouldn't appear in output)
- Timestamp format validation ([HH:MM:SS] or [MM:SS])
- Content length ratio (warn if <30% or >120% of original)
- Question count (info if >2 questions)

**Severity Levels:**
- ERROR: Context markers in output
- WARNING: Filler words, excessive truncation/expansion
- INFO: Many questions detected

**Key Functions:**
- `validate_chunk(original: str, cleaned: str, chunk_index: int) -> List[ValidationIssue]`
- `validate_all(processed_chunks: list) -> ValidationResult`

### 5. Writer Module (`src/markdown_writer.py`)
**Purpose:** Generate final Markdown output

**Classes:**
- `MarkdownWriter` - Main writer class
- `TranscriptMetadata` - Metadata for output

**Features:**
- Format timestamps correctly
- Organize content by concept
- Add metadata (processed date, model, cost, duration)
- Sanitize filenames from titles
- Generate preview for Streamlit

**Output Files:**
- `{sanitized_title}-{timestamp}.md` - Markdown transcript
- `{sanitized_title}-{timestamp}-metadata.json` - Metadata JSON

**Key Functions:**
- `write(processed_chunks: list, title: str, summary: dict, duration: Optional[str]) -> tuple[Path, Path]`
- `_build_markdown(chunks: list, metadata: TranscriptMetadata) -> str`
- `_sanitize_filename(title: str) -> str`
- `get_content_for_preview(chunks: list, max_chars: int = 5000) -> str`

### 6. Cost Estimator Module (`src/cost_estimator.py`)
**Purpose:** Estimate API costs before processing

**Classes:**
- `CostEstimator` - Main estimator class
- `CostBreakdown` - Cost breakdown dataclass

**Features:**
- Token counting with tiktoken (fallback to char/4)
- Support for multiple Claude models
- Processing time estimation
- Cost breakdown per chunk and total

**Pricing Models (per 1K tokens, Dec 2024):**
```python
PRICING = {
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.005}
}
```

**Key Functions:**
- `count_tokens(text: str) -> int`
- `estimate_chunk_tokens(chunk_text: str, prompt_template: str) -> tuple[int, int]`
- `estimate_total(chunks: list, prompt_template: str) -> CostBreakdown`
- `format_estimate(breakdown: CostBreakdown) -> str`

---

## Error Handling Patterns

### API Errors
Use tenacity for automatic retry:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential())
def call_claude_api(prompt: str) -> str:
    # API call logic
    pass
```

### Input Validation
```python
def process_file(file_path: str) -> str:
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not file_path.endswith(('.srt', '.vtt', '.txt')):
        raise ValueError("Unsupported file format")

    return parse_and_process(file_path)
```

### Custom Exceptions
```python
class TranscriptCleanerError(Exception):
    """Base exception for all cleaning errors."""
    pass

class ParsingError(TranscriptCleanerError):
    """Raised when file parsing fails."""
    pass

class APIError(TranscriptCleanerError):
    """Raised when Claude API call fails."""
    pass
```

---

## Testing Standards

### Test File Organization
- One test file per source module: `test_parser.py`, `test_chunker.py`
- Use pytest fixtures for common setup
- Name test functions: `test_<function>_<scenario>`

### Minimum Coverage
- Target: 80%+ code coverage
- All public functions must have at least one test
- Edge cases and error paths required

### Example Test Pattern
```python
import pytest
from src.parser import parse_srt

def test_parse_srt_valid_file(tmp_path):
    """Test parsing a valid SRT file."""
    srt_content = "1\n00:00:01,000 --> 00:00:05,000\nHello world"
    srt_file = tmp_path / "test.srt"
    srt_file.write_text(srt_content)

    result = parse_srt(str(srt_file))
    assert len(result) == 1
    assert result[0].content == "Hello world"

def test_parse_srt_invalid_file():
    """Test parsing a non-existent file."""
    with pytest.raises(FileNotFoundError):
        parse_srt("/nonexistent/file.srt")
```

---

## Configuration Management

### Environment Variables
- Load via python-dotenv: `python-dotenv>=1.0.0`
- Required: `ANTHROPIC_API_KEY`
- Never hardcode secrets

```python
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY not set in .env")
```

### Constants
Define in module or `config.py`:
```python
# Token limits
MAX_CHUNK_TOKENS = 4000
CHUNK_OVERLAP_CHARS = 200

# API settings
API_TIMEOUT_SECONDS = 30
MAX_RETRIES = 3

# File formats
SUPPORTED_FORMATS = {'.srt', '.vtt', '.txt'}
```

---

## Performance Considerations

### Optimization Priority
1. **Correctness** - Output quality first
2. **Clarity** - Code readability second
3. **Performance** - Speed optimizations only when needed

### Token Management
- Always count tokens before API calls
- Cache prompt tokens if reusing base_prompt.txt
- Estimate total cost before processing

### Memory Usage
- Stream large files instead of loading fully
- Process chunks sequentially
- Clean up temporary data after each step

---

## Documentation Requirements

### Inline Comments
- Only for "why", not "what"
- Explain non-obvious logic
- Keep comments updated with code changes

### README in Each Module
Add module docstring:
```python
"""Parser module - Handles transcript file formats (SRT, VTT, TXT).

This module provides functions to convert subtitle files and plain text
transcripts into structured TimestampedSegment objects.

Usage:
    from src.parser import parse_srt
    segments = parse_srt('lecture.srt')
"""
```

---

## Code Review Checklist

Before committing, verify:
- [ ] Type hints on all public functions
- [ ] Docstrings for all public functions
- [ ] Error handling for edge cases
- [ ] Tests written and passing
- [ ] No hardcoded secrets or API keys
- [ ] File size < 200 lines (except tests)
- [ ] Follows naming conventions
- [ ] No unused imports or variables
- [ ] Error messages are helpful

---

## References

- **Project Overview:** `project-overview-pdr.md`
- **System Architecture:** `system-architecture.md`
- **Development Plan:** `/plans/251224-1840-transcript-cleaner-mvp/`
