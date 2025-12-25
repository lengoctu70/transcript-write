# System Architecture

**Version:** 1.3
**Phase:** 4 - Validation & Output Complete
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

**Component:** `app.py` (TBD - Phase 5)

**Responsibilities:**
- User interface for file upload
- Progress display during processing
- Results preview and download
- Cost summary display

**User Workflow:**
1. User uploads SRT/VTT/TXT file
2. System estimates cost
3. User confirms or cancels
4. Processing starts with progress bar
5. Results displayed with download option
6. Cost summary shown

**Status:** Pending (Phase 5)

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

## Error Handling Strategy

### Error Hierarchy
```
TranscriptCleanerError (base)
  ├── ParsingError
  ├── ChunkingError
  ├── APIError (with retry logic)
  ├── ValidationError
  └── WriterError
```

### Retry Policy
- **Automatic Retries:** API errors only (via tenacity)
- **Manual Retries:** User-triggered for validation failures
- **Max Attempts:** 3 for API calls
- **Backoff:** Exponential (2^n seconds)

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

## Scalability Considerations

### Current Design (Phase 1-6)
- Single-user, sequential processing
- Suitable for MVP and small batches

### Future Enhancements
- Batch processing for multiple files
- Parallel chunk processing (async)
- Caching of base prompt tokens
- Streaming results to user
- Database for processing history

---

## References

- **Project Overview:** `project-overview-pdr.md`
- **Code Standards:** `code-standards.md`
- **Base Prompt:** `../prompts/base_prompt.txt`
- **Development Plan:** `../plans/251224-1840-transcript-cleaner-mvp/`
