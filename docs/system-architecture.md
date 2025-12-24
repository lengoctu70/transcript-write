# System Architecture

**Version:** 1.2
**Phase:** 3 - LLM Integration Complete
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

**Responsibilities:**
- Quality assurance on cleaned output
- Detect errors and anomalies
- Ensure content integrity
- Provide validation reports

**Validation Checks:**
1. **Length Check** - Output within 80%-120% of input length
2. **Content Check** - No corrupted/gibberish text
3. **Format Check** - Valid Markdown syntax
4. **Timestamp Check** - Correct format [HH:MM:SS]
5. **Completeness** - No truncated chunks

**Output:**
```python
@dataclass
class ValidationResult:
    is_valid: bool
    score: float          # 0.0-1.0
    errors: List[str]
    warnings: List[str]
```

**Status:** Pending (Phase 4)

---

### 6. Processing Pipeline - Writer

**Component:** `src/writer.py`

**Responsibilities:**
- Format cleaned chunks into final Markdown
- Organize content by concept
- Add timestamps and metadata
- Write to output file

**Output Format:**
```markdown
# Cleaned Transcript: [filename]

**Cleaned:** 2025-12-24 10:30:00
**Original Duration:** 45 minutes
**Chunks Processed:** 8
**Estimated Cost:** $0.12

---

## [Section Name]

[00:01:15]

Clean, well-structured content here...

More content organized by concept...
```

**Features:**
- Markdown-formatted output
- Readable structure and hierarchy
- Timestamps at logical section starts
- Metadata header with processing info

**Status:** Pending (Phase 4)

---

### 7. Utility - Cost Estimation

**Component:** Integrated in `src/llm_processor.py`

**Responsibilities:**
- Calculate API costs per processed chunk
- Track token usage per request
- Provide summary with total costs
- Support multiple model pricing tiers

**Cost Calculation:**
```python
# Per-chunk calculation
cost = (input_tokens / 1000) * prices["input"] +
       (output_tokens / 1000) * prices["output"]

# Summary totals
total_input = sum(r.input_tokens for r in results)
total_output = sum(r.output_tokens for r in results)
total_cost = sum(r.cost for r in results)
```

**Current Pricing (per 1K tokens, Dec 2024):**
- claude-3-5-sonnet-20241022: Input $0.003, Output $0.015
- claude-3-5-haiku-20241022: Input $0.001, Output $0.005

**Summary Output:**
```python
{
    "chunks_processed": len(results),
    "total_input_tokens": total_input,
    "total_output_tokens": total_output,
    "total_cost": round(total_cost, 4),
    "model": model
}
```

**Status:** ✓ Complete (Phase 3)

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
                      + Cost Report
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
  └── depends on: (minimal)

Writer
  └── depends on: pathlib, Validator

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
