# Phase 3: LLM Integration

**Effort:** 3 hours
**Dependencies:** Phase 2 (chunker ready)
**Deliverables:** llm_processor.py with Claude API integration, retry logic, token counting

---

## Tasks

### 3.1 Implement LLMProcessor (src/llm_processor.py)

```python
"""Process chunks via Claude API with retry logic"""
import os
from dataclasses import dataclass
from typing import Optional, Callable
from pathlib import Path

import anthropic
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from .chunker import Chunk


@dataclass
class ProcessedChunk:
    """Result of LLM processing"""
    chunk_index: int
    original_text: str
    cleaned_text: str
    input_tokens: int
    output_tokens: int
    cost: float
    model: str


class LLMProcessor:
    """Process transcript chunks via Claude API"""

    # Pricing per 1K tokens (Dec 2024)
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

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.3,
        max_tokens: int = 4096
    ):
        """
        Args:
            api_key: Anthropic API key (or from env ANTHROPIC_API_KEY)
            model: Model identifier
            temperature: Lower = more deterministic
            max_tokens: Max output tokens per request
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("API key required. Set ANTHROPIC_API_KEY env var.")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def load_prompt_template(
        self, template_path: Optional[str] = None
    ) -> str:
        """Load prompt template from file"""
        if template_path is None:
            # Default path relative to project root
            template_path = Path(__file__).parent.parent / "prompts" / "base_prompt.txt"

        with open(template_path, "r") as f:
            return f.read()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((
            anthropic.RateLimitError,
            anthropic.APIConnectionError,
            anthropic.InternalServerError
        ))
    )
    def process_chunk(
        self,
        chunk: Chunk,
        prompt_template: str,
        video_title: str = "Untitled"
    ) -> ProcessedChunk:
        """
        Process single chunk through Claude API.

        Args:
            chunk: Chunk object with text and context
            prompt_template: Template with {{fileName}} and {{chunkText}} placeholders
            video_title: Title for {{fileName}} placeholder

        Returns:
            ProcessedChunk with cleaned text and usage stats
        """
        # Build final prompt
        user_message = self._build_prompt(
            chunk, prompt_template, video_title
        )

        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{
                "role": "user",
                "content": user_message
            }]
        )

        # Extract result
        cleaned_text = response.content[0].text

        # Calculate cost
        cost = self._calculate_cost(
            response.usage.input_tokens,
            response.usage.output_tokens
        )

        return ProcessedChunk(
            chunk_index=chunk.index,
            original_text=chunk.text,
            cleaned_text=cleaned_text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost=cost,
            model=self.model
        )

    def process_all_chunks(
        self,
        chunks: list[Chunk],
        prompt_template: str,
        video_title: str = "Untitled",
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> list[ProcessedChunk]:
        """
        Process all chunks sequentially with progress tracking.

        Args:
            chunks: List of Chunk objects
            prompt_template: Prompt template
            video_title: Video title
            progress_callback: fn(current, total) called after each chunk

        Returns:
            List of ProcessedChunk objects
        """
        results = []

        for i, chunk in enumerate(chunks):
            result = self.process_chunk(chunk, prompt_template, video_title)
            results.append(result)

            if progress_callback:
                progress_callback(i + 1, len(chunks))

        return results

    def _build_prompt(
        self,
        chunk: Chunk,
        template: str,
        video_title: str
    ) -> str:
        """Build final prompt from template and chunk"""
        # Get chunk text with context
        chunk_text = chunk.full_text_for_llm

        # Replace placeholders
        prompt = template.replace("{{fileName}}", video_title)
        prompt = prompt.replace("{{chunkText}}", chunk_text)

        return prompt

    def _calculate_cost(
        self, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate cost based on token usage"""
        prices = self.PRICING.get(self.model, self.PRICING["claude-3-5-sonnet-20241022"])

        cost = (
            (input_tokens / 1000) * prices["input"] +
            (output_tokens / 1000) * prices["output"]
        )
        return round(cost, 6)


# Convenience function for single-file processing
def process_transcript(
    chunks: list[Chunk],
    api_key: str,
    video_title: str,
    model: str = "claude-3-5-sonnet-20241022",
    prompt_path: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> tuple[list[ProcessedChunk], dict]:
    """
    Process entire transcript and return results with summary.

    Returns:
        (processed_chunks, summary_dict)
    """
    processor = LLMProcessor(api_key=api_key, model=model)
    template = processor.load_prompt_template(prompt_path)

    results = processor.process_all_chunks(
        chunks, template, video_title, progress_callback
    )

    # Calculate totals
    total_input = sum(r.input_tokens for r in results)
    total_output = sum(r.output_tokens for r in results)
    total_cost = sum(r.cost for r in results)

    summary = {
        "chunks_processed": len(results),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cost": round(total_cost, 4),
        "model": model
    }

    return results, summary
```

---

### 3.2 Error Handling Strategy

**Retry logic (via tenacity):**
- `RateLimitError`: Wait and retry (exponential backoff)
- `APIConnectionError`: Retry up to 3 times
- `InternalServerError`: Retry with backoff
- `BadRequestError`: Fail immediately (prompt issue)

**Error responses to UI:**
```python
class ProcessingError(Exception):
    """Custom error for processing failures"""
    def __init__(self, chunk_index: int, message: str, recoverable: bool = False):
        self.chunk_index = chunk_index
        self.message = message
        self.recoverable = recoverable
        super().__init__(f"Chunk {chunk_index}: {message}")
```

---

### 3.3 Rate Limit Handling

Claude API limits:
- Requests per minute (RPM)
- Tokens per minute (TPM)

**Approach:** Sequential processing with automatic backoff
- tenacity handles rate limits transparently
- No parallel processing in MVP (simpler, avoids rate limits)

---

### 3.4 Token Counting Utility

Add to `src/cost_estimator.py` (Phase 4) but define interface here:

```python
# Preview: token counting for cost estimation
import tiktoken

def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """Estimate tokens using tiktoken (Claude-compatible)"""
    try:
        enc = tiktoken.get_encoding(model)
        return len(enc.encode(text))
    except Exception:
        # Fallback: rough estimate (4 chars per token)
        return len(text) // 4
```

---

## Integration with Streamlit

**Progress callback usage:**
```python
# In app.py
progress_bar = st.progress(0)
status_text = st.empty()

def update_progress(current: int, total: int):
    progress_bar.progress(current / total)
    status_text.text(f"Processing chunk {current}/{total}...")

results, summary = process_transcript(
    chunks=chunks,
    api_key=api_key,
    video_title=video_title,
    progress_callback=update_progress
)
```

---

## Success Criteria

- [x] LLMProcessor connects to Claude API
- [x] Retry logic handles transient errors
- [x] Cost calculated correctly per chunk
- [x] Progress callback works with Streamlit
- [x] Template loading from file works
- [x] Error messages are user-friendly

---

## Security Checklist

- [x] API key never logged or displayed
- [x] API key loaded from env var or secure input
- [x] No hardcoded keys in source
- [x] Errors don't expose API key

---

## Testing Notes

**Mock testing (avoid real API calls):**
```python
# tests/test_llm_processor.py
from unittest.mock import Mock, patch

def test_process_chunk_success():
    """Test successful chunk processing"""
    with patch('anthropic.Anthropic') as mock_client:
        # Setup mock response
        mock_response = Mock()
        mock_response.content = [Mock(text="Cleaned text")]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 80
        mock_client.return_value.messages.create.return_value = mock_response

        processor = LLMProcessor(api_key="test-key")
        # ... test logic
```

**Integration test (with real API, optional):**
```bash
# Run only with ANTHROPIC_API_KEY set
pytest tests/test_llm_processor.py -v -m integration
```

---

## Implementation Status

**Status:** DONE (2025-12-25 00:37)
**Report:** `plans/reports/project-manager-251225-0037-phase3-completion.md`

### Files Delivered
- `src/llm_processor.py` (249 lines)
- `tests/test_llm_processor.py` (243 lines)

### Test Results
```
21 passed in 0.44s
Coverage: llm_processor.py 100%, overall 85%
```

### Code Review Summary
**Grade:** B+ (Good implementation, minor fixes recommended)

**Critical Issues:** 0
**High Priority Issues:** 2 (RESOLVED - fixes already applied)
1. Missing file existence check in `load_prompt_template` - FIXED
2. Type hint inconsistency (list vs List) - CONSISTENT

**Medium Priority Issues:** 2
1. Missing empty response validation (defer to Phase 6)
2. No max_tokens parameter validation (defer to Phase 6)

**Strengths:**
- Excellent retry logic with exponential backoff
- Proper API key handling (no hardcoded secrets)
- Clean architecture with separation of concerns
- Good test coverage with proper mocking
- Accurate cost calculation

**Security Posture:** PASS
- API key loaded from environment variable
- No secrets in source code
- Error messages don't expose credentials

### Completion Details
- **Completion Date:** 2025-12-25 00:37
- **Files Created:** 2 (implementation + tests)
- **Tests Passing:** 21/21 (100%)
- **Coverage:** 100% on llm_processor.py
- **Code Review:** B+ (production-ready for MVP)

### Next Steps
- **Phase 4:** Validation & Output (ready to proceed)
- **Phase 6:** Apply medium/low priority fixes
