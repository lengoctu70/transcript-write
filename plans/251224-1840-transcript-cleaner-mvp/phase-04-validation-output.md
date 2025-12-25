# Phase 4: Validation & Output

**Status:** DONE
**Completed:** 2025-12-25
**Effort:** 2 hours
**Dependencies:** Phase 3 (LLM processor ready) [COMPLETE]
**Deliverables:** validator.py, markdown_writer.py, cost_estimator.py [ALL DELIVERED]

---

## Tasks

### 4.1 Implement Validator (src/validator.py)

**Responsibility:** Rule-based validation to catch common LLM mistakes

```python
"""Rule-based validation for cleaned transcript output"""
import re
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class ValidationSeverity(Enum):
    ERROR = "error"      # Must fix
    WARNING = "warning"  # Should review
    INFO = "info"        # FYI


@dataclass
class ValidationIssue:
    """Single validation issue"""
    severity: ValidationSeverity
    rule: str
    message: str
    chunk_index: Optional[int] = None
    snippet: Optional[str] = None  # Relevant text excerpt


@dataclass
class ValidationResult:
    """Validation result for all chunks"""
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == ValidationSeverity.ERROR for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == ValidationSeverity.WARNING for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)

    def to_dict(self) -> dict:
        return {
            "total_issues": len(self.issues),
            "errors": self.error_count,
            "warnings": self.warning_count,
            "issues": [
                {
                    "severity": i.severity.value,
                    "rule": i.rule,
                    "message": i.message,
                    "chunk": i.chunk_index,
                    "snippet": i.snippet
                }
                for i in self.issues
            ]
        }


class OutputValidator:
    """Validate cleaned transcript against rules"""

    # Filler words/phrases to detect
    FILLERS = [
        r"\buh\b", r"\bum\b", r"\bah\b", r"\ber\b",
        r"\byou know\b", r"\blike\b(?!\s+this|\s+that)",  # "like" but not "like this"
        r"\bokay\b", r"\bso\b(?=\s*,)",  # "so" followed by comma
        r"\bbasically\b", r"\bactually\b", r"\breally\b",
        r"\bthe thing is\b", r"\bwhat I'm trying to say\b"
    ]

    # Context markers that shouldn't appear in output
    CONTEXT_MARKERS = [
        r"\[CONTEXT FROM PREVIOUS SECTION\]",
        r"\[NEW CONTENT TO PROCESS\]",
        r"\[VIDEO INFO\]",
        r"\[TRANSCRIPT TO PROCESS\]"
    ]

    def validate_chunk(
        self,
        original: str,
        cleaned: str,
        chunk_index: int
    ) -> List[ValidationIssue]:
        """Validate single cleaned chunk"""
        issues = []

        # Check for remaining fillers
        issues.extend(self._check_fillers(cleaned, chunk_index))

        # Check for context markers (shouldn't be in output)
        issues.extend(self._check_context_markers(cleaned, chunk_index))

        # Check timestamp format
        issues.extend(self._check_timestamp_format(cleaned, chunk_index))

        # Check content length (not overly truncated)
        issues.extend(self._check_content_length(original, cleaned, chunk_index))

        # Check for questions (should be converted to statements)
        issues.extend(self._check_questions(cleaned, chunk_index))

        return issues

    def validate_all(
        self,
        processed_chunks: list  # List[ProcessedChunk]
    ) -> ValidationResult:
        """Validate all processed chunks"""
        result = ValidationResult()

        for chunk in processed_chunks:
            issues = self.validate_chunk(
                original=chunk.original_text,
                cleaned=chunk.cleaned_text,
                chunk_index=chunk.chunk_index
            )
            result.issues.extend(issues)

        return result

    def _check_fillers(
        self, text: str, chunk_index: int
    ) -> List[ValidationIssue]:
        """Check for remaining filler words"""
        issues = []
        text_lower = text.lower()

        for pattern in self.FILLERS:
            matches = list(re.finditer(pattern, text_lower, re.IGNORECASE))
            if matches:
                for match in matches[:3]:  # Report max 3 per pattern
                    # Get surrounding context
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 20)
                    snippet = "..." + text[start:end] + "..."

                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        rule="filler_detected",
                        message=f"Possible filler word: '{match.group()}'",
                        chunk_index=chunk_index,
                        snippet=snippet
                    ))

        return issues

    def _check_context_markers(
        self, text: str, chunk_index: int
    ) -> List[ValidationIssue]:
        """Check for context markers that shouldn't appear in output"""
        issues = []

        for pattern in self.CONTEXT_MARKERS:
            if re.search(pattern, text):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    rule="context_marker_in_output",
                    message=f"Context marker found in output: {pattern}",
                    chunk_index=chunk_index
                ))

        return issues

    def _check_timestamp_format(
        self, text: str, chunk_index: int
    ) -> List[ValidationIssue]:
        """Check timestamp format is correct [HH:MM:SS]"""
        issues = []

        # Find all timestamp-like patterns
        timestamps = re.findall(r"\[[\d:\.]+\]", text)

        for ts in timestamps:
            # Valid format: [HH:MM:SS] or [MM:SS]
            if not re.match(r"\[\d{2}:\d{2}:\d{2}\]|\[\d{2}:\d{2}\]", ts):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    rule="invalid_timestamp_format",
                    message=f"Invalid timestamp format: {ts}",
                    chunk_index=chunk_index
                ))

        return issues

    def _check_content_length(
        self,
        original: str,
        cleaned: str,
        chunk_index: int
    ) -> List[ValidationIssue]:
        """Check that output isn't too short (over-truncated)"""
        issues = []

        original_len = len(original)
        cleaned_len = len(cleaned)

        # Cleaned should be 30-100% of original length
        # (removal of fillers shouldn't reduce more than 70%)
        ratio = cleaned_len / original_len if original_len > 0 else 0

        if ratio < 0.3:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                rule="excessive_truncation",
                message=f"Output too short ({ratio:.0%} of original). May have lost content.",
                chunk_index=chunk_index
            ))
        elif ratio > 1.2:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                rule="content_expansion",
                message=f"Output longer than original ({ratio:.0%}). LLM may have added content.",
                chunk_index=chunk_index
            ))

        return issues

    def _check_questions(
        self, text: str, chunk_index: int
    ) -> List[ValidationIssue]:
        """Check for questions (should be converted to statements)"""
        issues = []

        # Find sentences ending with ?
        questions = re.findall(r"[^.!?]*\?", text)

        # Allow max 2 questions per chunk (some are legitimate)
        if len(questions) > 2:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                rule="many_questions",
                message=f"Found {len(questions)} questions. Consider if they should be statements.",
                chunk_index=chunk_index
            ))

        return issues
```

---

### 4.2 Implement MarkdownWriter (src/markdown_writer.py)

```python
"""Format and save cleaned transcript as Markdown"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from pathlib import Path
import json


@dataclass
class TranscriptMetadata:
    """Metadata for processed transcript"""
    title: str
    original_duration: Optional[str]
    processed_at: str
    model: str
    total_cost: float
    chunks_processed: int
    input_tokens: int
    output_tokens: int


class MarkdownWriter:
    """Write cleaned transcript to Markdown file"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def write(
        self,
        processed_chunks: list,  # List[ProcessedChunk]
        title: str,
        summary: dict,
        duration: Optional[str] = None
    ) -> tuple[Path, Path]:
        """
        Write cleaned transcript to Markdown and metadata to JSON.

        Returns:
            (markdown_path, metadata_path)
        """
        # Build metadata
        metadata = TranscriptMetadata(
            title=title,
            original_duration=duration,
            processed_at=datetime.now().isoformat(),
            model=summary["model"],
            total_cost=summary["total_cost"],
            chunks_processed=summary["chunks_processed"],
            input_tokens=summary["total_input_tokens"],
            output_tokens=summary["total_output_tokens"]
        )

        # Build markdown content
        content = self._build_markdown(processed_chunks, metadata)

        # Generate filename (sanitize title)
        safe_title = self._sanitize_filename(title)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        base_name = f"{safe_title}-{timestamp}"

        # Write files
        md_path = self.output_dir / f"{base_name}.md"
        json_path = self.output_dir / f"{base_name}-metadata.json"

        md_path.write_text(content, encoding="utf-8")
        json_path.write_text(
            json.dumps(self._metadata_to_dict(metadata), indent=2),
            encoding="utf-8"
        )

        return md_path, json_path

    def _build_markdown(
        self,
        chunks: list,
        metadata: TranscriptMetadata
    ) -> str:
        """Build complete Markdown document"""
        lines = []

        # Header
        lines.append(f"# {metadata.title}")
        lines.append("")

        # Metadata block
        lines.append(f"**Processed:** {metadata.processed_at[:10]}")
        lines.append(f"**Model:** {metadata.model}")
        lines.append(f"**Cost:** ${metadata.total_cost:.4f}")
        if metadata.original_duration:
            lines.append(f"**Duration:** {metadata.original_duration}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Content
        for chunk in chunks:
            cleaned = chunk.cleaned_text.strip()
            if cleaned:
                lines.append(cleaned)
                lines.append("")  # Blank line between chunks

        return "\n".join(lines)

    def _metadata_to_dict(self, metadata: TranscriptMetadata) -> dict:
        """Convert metadata to dictionary"""
        return {
            "title": metadata.title,
            "original_duration": metadata.original_duration,
            "processed_at": metadata.processed_at,
            "model": metadata.model,
            "cost_usd": metadata.total_cost,
            "chunks_processed": metadata.chunks_processed,
            "tokens": {
                "input": metadata.input_tokens,
                "output": metadata.output_tokens,
                "total": metadata.input_tokens + metadata.output_tokens
            }
        }

    def _sanitize_filename(self, title: str) -> str:
        """Create safe filename from title"""
        import re
        # Remove invalid chars
        safe = re.sub(r'[<>:"/\\|?*]', '', title)
        # Replace spaces with hyphens
        safe = re.sub(r'\s+', '-', safe)
        # Limit length
        return safe[:50].strip('-')

    def get_content_for_preview(
        self, chunks: list, max_chars: int = 5000
    ) -> str:
        """Get preview content (for Streamlit display)"""
        content = []
        total_chars = 0

        for chunk in chunks:
            text = chunk.cleaned_text.strip()
            if total_chars + len(text) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 100:
                    content.append(text[:remaining] + "...")
                break
            content.append(text)
            total_chars += len(text)

        return "\n\n".join(content)
```

---

### 4.3 Implement CostEstimator (src/cost_estimator.py)

```python
"""Estimate API costs before processing"""
from dataclasses import dataclass
from typing import List
import tiktoken


@dataclass
class CostBreakdown:
    """Cost estimation breakdown"""
    input_tokens: int
    output_tokens_est: int
    input_cost: float
    output_cost: float
    total_cost: float
    chunks: int
    processing_time_minutes: float


class CostEstimator:
    """Estimate costs before processing"""

    # Pricing per 1K tokens (keep in sync with LLMProcessor)
    PRICING = {
        "claude-3-5-sonnet-20241022": {
            "input": 0.003,
            "output": 0.015
        },
        "claude-3-5-haiku-20241022": {
            "input": 0.001,
            "output": 0.005
        }
    }

    # Processing time estimates (seconds per chunk)
    TIME_PER_CHUNK = {
        "claude-3-5-sonnet-20241022": 5,
        "claude-3-5-haiku-20241022": 3
    }

    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        self.model = model
        self._encoder = None

    @property
    def encoder(self):
        """Lazy load tiktoken encoder"""
        if self._encoder is None:
            self._encoder = tiktoken.get_encoding("cl100k_base")
        return self._encoder

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        try:
            return len(self.encoder.encode(text))
        except Exception:
            # Fallback: ~4 chars per token
            return len(text) // 4

    def estimate_chunk_tokens(
        self,
        chunk_text: str,
        prompt_template: str
    ) -> tuple[int, int]:
        """
        Estimate input and output tokens for a chunk.

        Returns:
            (input_tokens, estimated_output_tokens)
        """
        # Input = prompt template + chunk text
        input_tokens = self.count_tokens(prompt_template) + self.count_tokens(chunk_text)

        # Output estimate: ~80% of chunk text (cleaning reduces length)
        output_estimate = int(self.count_tokens(chunk_text) * 0.8)

        return input_tokens, output_estimate

    def estimate_total(
        self,
        chunks: list,  # List[Chunk]
        prompt_template: str
    ) -> CostBreakdown:
        """Estimate total cost for all chunks"""
        total_input = 0
        total_output = 0

        for chunk in chunks:
            input_t, output_t = self.estimate_chunk_tokens(
                chunk.full_text_for_llm,
                prompt_template
            )
            total_input += input_t
            total_output += output_t

        # Calculate costs
        prices = self.PRICING.get(self.model, self.PRICING["claude-3-5-sonnet-20241022"])
        input_cost = (total_input / 1000) * prices["input"]
        output_cost = (total_output / 1000) * prices["output"]

        # Estimate time
        time_per_chunk = self.TIME_PER_CHUNK.get(self.model, 5)
        total_time_seconds = len(chunks) * time_per_chunk
        time_minutes = total_time_seconds / 60

        return CostBreakdown(
            input_tokens=total_input,
            output_tokens_est=total_output,
            input_cost=round(input_cost, 4),
            output_cost=round(output_cost, 4),
            total_cost=round(input_cost + output_cost, 4),
            chunks=len(chunks),
            processing_time_minutes=round(time_minutes, 1)
        )

    def format_estimate(self, breakdown: CostBreakdown) -> str:
        """Format estimate for display"""
        return f"""
**Cost Estimate**
- Input tokens: {breakdown.input_tokens:,} (${breakdown.input_cost:.4f})
- Output tokens: ~{breakdown.output_tokens_est:,} (${breakdown.output_cost:.4f})
- **Total: ${breakdown.total_cost:.4f}**

**Processing**
- Chunks: {breakdown.chunks}
- Est. time: ~{breakdown.processing_time_minutes} minutes
""".strip()
```

---

### 4.4 Update src/__init__.py

```python
"""Transcript cleaning modules"""
from .transcript_parser import TranscriptParser, TranscriptSegment
from .chunker import SmartChunker, Chunk
from .llm_processor import LLMProcessor, ProcessedChunk, process_transcript
from .validator import OutputValidator, ValidationResult, ValidationSeverity
from .markdown_writer import MarkdownWriter
from .cost_estimator import CostEstimator, CostBreakdown

__all__ = [
    "TranscriptParser",
    "TranscriptSegment",
    "SmartChunker",
    "Chunk",
    "LLMProcessor",
    "ProcessedChunk",
    "process_transcript",
    "OutputValidator",
    "ValidationResult",
    "ValidationSeverity",
    "MarkdownWriter",
    "CostEstimator",
    "CostBreakdown",
]
```

---

## Success Criteria

- [x] Validator catches common issues (fillers, context markers, truncation)
- [x] MarkdownWriter produces clean output with metadata
- [x] CostEstimator provides accurate pre-processing estimate
- [x] All modules importable from src package
- [x] Output files saved to output/ directory
- [x] Metadata JSON contains all relevant stats

---

## Testing Notes

```bash
# Test validator
pytest tests/test_validator.py -v

# Test writer
pytest tests/test_writer.py -v

# Test cost estimator
pytest tests/test_cost_estimator.py -v
```
