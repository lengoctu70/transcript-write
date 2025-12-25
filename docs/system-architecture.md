# System Architecture

**Version:** 1.5
**Phase:** 6 - Testing & Polish Complete
**Last Updated:** 2025-12-25

---

## Architecture Overview

Transcript Cleaner uses a **layered pipeline architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                  STREAMLIT UI LAYER (Phase 5)               │
│  File Upload | Preview | Download | Cost Display           │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│           INPUT & CONFIGURATION LAYER (Phase 1)             │
│  .env (API keys) | requirements.txt | base_prompt.txt      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│          PROCESSING PIPELINE LAYER (Phases 2-4)             │
│                                                              │
│  ┌─────────────┐   ┌─────────────┐   ┌──────────────┐      │
│  │   Parser    │──▶│   Chunker   │──▶│ LLM Processor│      │
│  │(SRT/VTT/TXT)│   │(Token-aware)│   │(Claude API) │      │
│  └─────────────┘   └─────────────┘   └──────────────┘      │
│         │                                     │              │
│         └─────────────────┬───────────────────┘              │
│                           │                                  │
│                    ┌──────▼──────┐                          │
│                    │  Validator  │                          │
│                    │(Quality QA) │                          │
│                    └──────┬──────┘                          │
│                           │                                  │
│                    ┌──────▼────────┐                        │
│                    │    Writer     │                        │
│                    │ (Markdown Gen)│                        │
│                    └──────────────┘                         │
│                                                              │
│                    ┌──────────────────┐                     │
│                    │  Cost Estimator  │                     │
│                    │ (API Cost Calc) │                     │
│                    └──────────────────┘                     │
└──────────────────────────────────────────────────────────────┘
```

---

## Layer Descriptions

### 1. Input & Configuration Layer

**Components:**
- `.env` - Environment variable storage (API keys)
- `.env.example` - Template for required configuration
- `requirements.txt` - Python dependencies
- `prompts/base_prompt.txt` - Claude system prompt

**Responsibilities:**
- Manage secrets securely
- Define project dependencies
- Provide reusable cleaning rules

**Status:** ✓ Complete (Phase 1)

**Key Files:**
```
├── .env                     (not tracked in git)
├── .env.example             (template)
├── requirements.txt
└── prompts/
    └── base_prompt.txt
```

---

### 2. Input & Validation Layer (Parser)

**Component:** `src/transcript_parser.py`

**Classes:**
- `TranscriptSegment` - Dataclass for parsed subtitle entries
- `TranscriptParser` - Main parser class

**Responsibilities:**
- Accept multiple input formats (SRT, VTT)
- Parse and validate file structure
- Extract timestamps and content
- Normalize data format
- Remove HTML tags and duplicates

**Input Formats Supported:**
1. **SRT (SubRip)** - Standard subtitle format
   ```
   1
   00:00:01,000 --> 00:00:05,000
   First subtitle text
   ```

2. **VTT (WebVTT)** - Web video text track format
   ```
   WEBVTT

   00:00:01.000 --> 00:00:05.000
   First subtitle text
   ```

**Output Data Structure:**
```python
@dataclass
class TranscriptSegment:
    index: int           # Segment number
    start_time: str      # "HH:MM:SS" format
    end_time: str        # "HH:MM:SS" format
    text: str            # Cleaned text content
```

**Key Methods:**
- `parse(file_path)` - Auto-detect format and parse
- `parse_from_bytes(content, filename)` - Handle Streamlit uploads
- `to_plain_text(segments)` - Convert to timestamped text

**Status:** ✓ Complete (Phase 2)

---

### 3. Processing Pipeline - Chunker

**Component:** `src/chunker.py`

**Classes:**
- `Chunk` - Dataclass with text and metadata
- `SmartChunker` - Main chunking logic

**Responsibilities:**
- Split transcripts into manageable chunks
- Maintain context overlap between chunks
- Track chunk metadata (index, timestamps)
- Build LLM-ready text with context markers

**Chunking Strategy:**
- **Chunk Size:** 2,000 characters (default)
- **Overlap:** 200 characters from previous chunk
- **Boundary Priority:** Paragraph > Sentence > Timestamp > Fallback

**Data Structure:**
```python
@dataclass
class Chunk:
    index: int                        # Chunk number
    text: str                         # Main content
    start_timestamp: str              # First timestamp [HH:MM:SS]
    context_buffer: Optional[str]     # Overlap from previous

    @property
    def full_text_for_llm(self) -> str:
        """Build text with context markers"""
```

**Data Flow:**
```
Plain Text Transcript
     │
     ▼
[Split at chunk_size boundary]
     │
     ▼
[Find best split: paragraph > sentence > timestamp]
     │
     ▼
[Extract context from previous chunk]
     │
     ▼
Chunk objects with context_buffer
```

**Status:** ✓ Complete (Phase 2)

---

### 4. Processing Pipeline - LLM Processor

**Component:** `src/llm_processor.py`

**Classes:**
- `LLMProcessor` - Main processor class
- `ProcessedChunk` - Result dataclass with cleaning results
- `ProcessingError` - Custom exception for failures

**Responsibilities:**
- Load and template the base prompt
- Send chunks to Claude API
- Handle token counting and cost calculation
- Implement retry logic with tenacity
- Process responses with metadata tracking

**Prompt Structure:**
1. **System Prompt** - From `prompts/base_prompt.txt`
2. **Template Variables:**
   - `{{fileName}}` - Source file name
   - `{{chunkText}}` - Transcript chunk to process
3. **Claude Models:**
   - claude-3-5-sonnet-20241022 (default, $0.003/$0.015 per 1K tokens)
   - claude-3-5-haiku-20241022 (faster, $0.001/$0.005 per 1K tokens)

**API Integration:**
```python
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

response = client.messages.create(
    model=self.model,  # claude-3-5-sonnet-20241022 or haiku
    max_tokens=4096,
    temperature=0.3,
    messages=[{"role": "user", "content": user_message}]
)
```

**ProcessedChunk Data Structure:**
```python
@dataclass
class ProcessedChunk:
    chunk_index: int
    original_text: str
    cleaned_text: str
    input_tokens: int
    output_tokens: int
    cost: float
    model: str
```

**Retry Policy:**
- Max attempts: 3
- Backoff strategy: Exponential (1s, 2s, 4s... up to 10s)
- Retry on: RateLimitError, APIConnectionError, InternalServerError
- Implemented via: tenacity library

**Cost Calculation:**
```python
def _calculate_cost(input_tokens: int, output_tokens: int) -> float:
    prices = self.PRICING.get(self.model, {...})
    cost = (
        (input_tokens / 1000) * prices["input"] +
        (output_tokens / 1000) * prices["output"]
    )
    return round(cost, 6)
```

**Convenience Function:**
```python
def process_transcript(
    chunks: list[Chunk],
    api_key: str,
    video_title: str,
    model: str = "claude-3-5-sonnet-20241022"
) -> tuple[list[ProcessedChunk], dict]:
    """Returns (processed_chunks, summary_dict)"""
```

**Status:** ✓ Complete (Phase 3)

---

### 5. Processing Pipeline - Validator

**Component:** `src/validator.py`

**Classes:**
- `OutputValidator` - Main validator class
- `ValidationResult` - Aggregated validation result
- `ValidationIssue` - Individual issue with severity
- `ValidationSeverity` - Enum (ERROR, WARNING, INFO)

**Responsibilities:**
- Quality assurance on cleaned output
- Detect errors and anomalies
- Ensure content integrity
- Provide validation reports

**Validation Rules:**
1. **Filler Detection** - Warns if common fillers remain
   - Patterns: "uh", "um", "ah", "er", "you know", "like", "okay", "so,", "basically", "actually", "really"
   - Severity: WARNING (with context snippet)

2. **Context Markers** - Errors if template markers appear in output
   - Markers: `[CONTEXT FROM PREVIOUS SECTION]`, `[NEW CONTENT TO PROCESS]`, `[VIDEO INFO]`, `[TRANSCRIPT TO PROCESS]`
   - Severity: ERROR

3. **Timestamp Format** - Validates [HH:MM:SS] or [MM:SS] format
   - Rejects: [HH:MM:SS.mmm] (milliseconds), [H:MM] (missing leading zero)
   - Severity: WARNING

4. **Content Length** - Warns if output is too short or too long
   - Truncation: <30% of original length (WARNING)
   - Expansion: >120% of original length (WARNING)

5. **Question Count** - Info if too many questions remain
   - Threshold: >2 questions triggers INFO
   - Suggests converting to declarative statements

**Data Structures:**
```python
@dataclass
class ValidationIssue:
    severity: ValidationSeverity
    rule: str
    message: str
    chunk_index: Optional[int]
    snippet: Optional[str]

@dataclass
class ValidationResult:
    issues: List[ValidationIssue]

    @property
    def has_errors(self) -> bool
    @property
    def has_warnings(self) -> bool
    @property
    def error_count(self) -> int
    @property
    def warning_count(self) -> int
```

**Key Methods:**
- `validate_chunk(original, cleaned, chunk_index)` - Validate single chunk
- `validate_all(processed_chunks)` - Validate all chunks and aggregate

**Status:** ✓ Complete (Phase 4)

---

### 6. Processing Pipeline - Writer

**Component:** `src/markdown_writer.py`

**Classes:**
- `MarkdownWriter` - Main writer class
- `TranscriptMetadata` - Metadata for output

**Responsibilities:**
- Format cleaned chunks into final Markdown
- Organize content by concept
- Add timestamps and metadata
- Write to output file

**Output Format:**
```markdown
# Video Title

**Processed:** 2025-12-25
**Model:** claude-3-5-sonnet-20241022
**Cost:** $0.0150
**Duration:** 00:10:30

---

[00:00:00]
Clean, well-structured content here...

[00:05:00]
More content organized by concept...
```

**Metadata JSON Structure:**
```json
{
  "title": "Video Title",
  "original_duration": "00:10:30",
  "processed_at": "2025-12-25T10:30:00",
  "model": "claude-3-5-sonnet-20241022",
  "cost_usd": 0.015,
  "chunks_processed": 3,
  "tokens": {
    "input": 1500,
    "output": 1200,
    "total": 2700
  }
}
```

**Features:**
- Markdown-formatted output
- Metadata header with processing info
- Sanitized filenames from titles
- Preview generation for Streamlit
- Dual output: .md + -metadata.json

**Key Methods:**
- `write(processed_chunks, title, summary, duration)` - Write files
- `_build_markdown(chunks, metadata)` - Build markdown content
- `_sanitize_filename(title)` - Create safe filename
- `get_content_for_preview(chunks, max_chars)` - Generate preview

**Status:** ✓ Complete (Phase 4)

---

### 7. Utility - Cost Estimation

**Component:** `src/cost_estimator.py`

**Classes:**
- `CostEstimator` - Main estimator class
- `CostBreakdown` - Cost breakdown dataclass

**Responsibilities:**
- Calculate API costs before processing
- Estimate token usage with tiktoken
- Provide cost breakdown per chunk
- Estimate processing time

**Pricing Models (per 1K tokens, Dec 2024):**
```python
PRICING = {
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.005}
}

TIME_PER_CHUNK = {
    "claude-3-5-sonnet-20241022": 5,  # seconds
    "claude-3-5-haiku-20241022": 3
}
```

**CostBreakdown Dataclass:**
```python
@dataclass
class CostBreakdown:
    input_tokens: int
    output_tokens_est: int
    input_cost: float
    output_cost: float
    total_cost: float
    chunks: int
    processing_time_minutes: float
```

**Key Methods:**
- `count_tokens(text)` - Count using tiktoken (fallback: char/4)
- `estimate_chunk_tokens(chunk_text, prompt_template)` - Per chunk estimate
- `estimate_total(chunks, prompt_template)` - Total cost estimate
- `format_estimate(breakdown)` - Format for display

**Status:** ✓ Complete (Phase 4)

---

### 8. Presentation Layer - Streamlit UI

**Component:** `app.py` (Phase 5, Phase 6 Enhanced)

**Responsibilities:**
- File upload and selection
- Model and chunking configuration
- Cost estimation and approval
- Progress tracking during processing
- Results preview and download
- Error handling and reporting

**Error Handling Wrapper (`safe_process`)**

Wraps LLM processing with user-friendly error messages:

```python
def safe_process(func):
    """Convert technical errors to user-friendly messages"""
    try:
        return func()
    except AuthenticationError:
        # Invalid API key
        st.error("❌ Invalid API key. Check your Anthropic API key.")
    except RateLimitError:
        # Hit rate limits
        st.error("⏳ Rate limit reached. Please wait a moment and try again.")
    except APIConnectionError:
        # Network issues
        st.error("🌐 Network error. Check your internet connection.")
    except Exception:
        # Unknown error with debug details
        st.error("❌ Unexpected error")
        st.expander("Error details"):
            st.code(traceback.format_exc())
```

**Error Detection Strategy:**
- Catch exceptions from LLM processing function
- Check exception type name (works even if anthropic not imported)
- Provide specific guidance for common errors
- Show full traceback in expandable debug section

**User Workflow:**
1. User uploads SRT/VTT file
2. System parses and chunks transcript
3. Cost estimation displayed with breakdown
4. User enters API key and confirms
5. Processing starts with progress bar
6. Validation results displayed (errors/warnings/info)
7. Markdown and metadata saved to output/
8. Download buttons provided for both files
9. Error handling with specific messages for common failures

**Status:** ✓ Complete (Phase 6)

---

## Data Flow Diagram

```
User Input (File)
     │
     ▼
  Parser
  {SRT/VTT/TXT → Segments}
     │
     ▼
  Chunker
  {Segments → Token-aware Chunks}
     │
     ▼
  Cost Estimator
  {Chunks → Estimated Cost}
     │
     ▼ [User approves]
     │
  LLM Processor (Retry loop)
  {Chunk + Prompt → Cleaned text}
     │
     ▼
  Validator
  {Cleaned text → Validation result}
     │
     ├─▶ [Invalid] ──▶ Error reporting
     │
     └─▶ [Valid] ──▶ Writer
                      {Content → Markdown}
                           │
                           ▼
                      Output File
                      {Title-TIMESTAMP.md}
                      + Metadata JSON
                      {Title-TIMESTAMP-metadata.json}
```

---

## Module Dependencies

```
Parser
  └── depends on: pathlib, pysrt, webvtt

Chunker
  └── depends on: tiktoken, Parser

LLM Processor
  └── depends on: Anthropic SDK, tenacity, base_prompt.txt, Chunker

Validator
  └── depends on: re (built-in), dataclasses (built-in)

Markdown Writer
  └── depends on: pathlib, json (built-in), datetime (built-in)

Cost Estimator
  └── depends on: tiktoken (optional, with fallback)

Streamlit UI
  └── depends on: streamlit, all above modules
```

---

## Error Handling Strategy (Phase 6 Enhanced)

### Multi-Layer Error Handling

**Layer 1: LLM Processor Retry Logic (via tenacity)**
- Retries transient API errors automatically
- Max 3 attempts with exponential backoff
- Retries on: RateLimitError, APIConnectionError, InternalServerError
- Backoff: 1s → 2s → 4s → up to 10s

**Layer 2: Integration Tests (test_integration.py)**
- Tests error conditions: invalid format, empty files, malformed input
- Validates error handling behavior end-to-end
- Ensures graceful degradation for edge cases

**Layer 3: UI Error Wrapper (app.py - safe_process)**
- Wraps user-facing processing functions
- Converts technical errors to user-friendly messages
- Provides specific guidance for common failures
- Shows debug details in expandable section

### Error Hierarchy
```
Python/Anthropic Exceptions
  ├── AuthenticationError → "Invalid API key"
  ├── RateLimitError → "Rate limit, wait and retry"
  ├── APIConnectionError → "Network issue"
  └── Exception → "Unexpected error with traceback"
```

### Error Recovery Paths
| Error Type | Detection | User Message | Recovery |
|------------|-----------|--------------|----------|
| Invalid API Key | AuthenticationError | Check your API key | Update key and retry |
| Rate Limit | RateLimitError | Wait and retry later | Auto-retry or manual retry |
| Network Issue | APIConnectionError | Check internet connection | Retry on new connection |
| Malformed Input | ValueError (parser) | Check file format | Select different file |
| Empty File | Empty segments list | File contains no content | Choose valid file |
| Unknown Error | Generic Exception | Show full traceback | Check error details |

### Validation Error Handling
- **Errors:** Context markers in output (should never happen)
- **Warnings:** Filler words remaining, content expansion/truncation
- **Info:** High question count (informational only)
- All validation issues displayed in expandable UI section

---

## Security Considerations

### API Key Management
- Loaded from `.env` via python-dotenv
- Never logged or displayed
- .env excluded from version control

### Input Validation
- File type checking (extensions)
- Size limits for uploads
- Character encoding validation

### Output Security
- No API keys in output files
- No user data retention after processing
- Temporary files cleaned up

---

## Performance Targets

| Aspect | Target | Method |
|--------|--------|--------|
| Parsing | <500ms | Optimize regex patterns |
| Chunking | <1s | Efficient token counting |
| LLM Processing | ~5-10s per chunk | Depends on API |
| Validation | <500ms | Lightweight regex checks |
| Total for 1hr lecture | <3 min | Parallel processing potential |

---

## Testing & Quality Assurance (Phase 6)

### Unit Tests Coverage
- **test_parser.py:** 3 tests (parser functionality)
- **test_chunker.py:** 5 tests (chunking strategy)
- **test_llm_processor.py:** 22 tests (API integration, mocked)
- **test_validator.py:** 17 tests (validation rules)
- **test_writer.py:** 25 tests (markdown generation)
- **test_cost_estimator.py:** 20 tests (token counting, pricing)
- **Total:** 92 unit tests with 100% module coverage

### Integration Tests (test_integration.py)
- **TestFullPipeline:** 2 tests
  - `test_parse_chunk_flow()` - Parser → Chunker → Text
  - `test_full_pipeline()` - Complete end-to-end with mocked API
- **TestErrorHandling:** 3 tests
  - `test_invalid_file_format()` - Unsupported file rejection
  - `test_empty_file()` - Empty input handling
  - `test_malformed_srt()` - Malformed content handling
- **Total:** 5 integration tests covering full pipeline

### Test Execution
```bash
# All tests (86 total)
pytest

# Unit tests only
pytest tests/ --ignore=tests/test_integration.py

# Integration tests only
pytest tests/test_integration.py

# Specific module
pytest tests/test_parser.py -v
```

## Scalability Considerations

### Current Design (Phase 1-6 - MVP Complete)
- Single-user, sequential processing
- Suitable for production MVP
- Handles lectures up to 90 minutes
- Estimated cost: $0.20-$0.60 per hour of video

### Future Enhancements
- Batch processing for multiple files
- Parallel chunk processing (async/concurrent)
- Caching of base prompt tokens
- Streaming results to user in real-time
- Database for processing history and metrics
- Queue system for high-volume processing

---

## References

- **Project Overview:** `project-overview-pdr.md`
- **Code Standards:** `code-standards.md`
- **Base Prompt:** `../prompts/base_prompt.txt`
- **Development Plan:** `../plans/251224-1840-transcript-cleaner-mvp/`
