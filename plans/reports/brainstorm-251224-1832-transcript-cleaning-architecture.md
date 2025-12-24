# Transcript Cleaning Tool - Architecture & Implementation Plan

**Date:** 2024-12-24
**Status:** Architecture Decision
**Brainstorm Session Output**

---

## Problem Statement

Convert long English lecture transcripts (30-120 min) from SRT/VTT format into clean, study-ready Markdown notes optimized for Vietnamese learners using LLM processing with chunking strategy.

**Core Challenges:**
- Token limit management (long transcripts exceed context windows)
- Context preservation across chunks
- Cost optimization (minimize redundant LLM calls)
- Noise removal from spoken language
- Maintaining educational content integrity

---

## Requirements Summary

### Functional Requirements
- Upload SRT/VTT transcript files
- Process via Claude/OpenAI API with fixed + custom prompts
- Chunk transcripts intelligently (~2000-2500 chars)
- Preview cleaned output per chunk
- Download final Markdown
- Batch processing support (multiple files)

### Non-Functional Requirements
- **Performance:** Accept 1-5 min processing time for long videos
- **Cost:** Minimize API token usage via chunking + validation
- **Usability:** Simple UI for personal use, no auth needed
- **Deployment:** Local-first, optional cloud deploy later
- **Maintainability:** Easy prompt iteration, clear code structure

### Constraints
- Personal tool (not public SaaS)
- No real-time processing needed
- Budget-conscious API usage
- User is technical (comfortable with Python)

---

## Architecture Options Evaluated

### Option A: Streamlit (Python-Only) ⭐ RECOMMENDED

**Stack:**
```
Frontend: Streamlit (Python)
Backend: Same process
LLM: Claude/OpenAI API
Storage: Local filesystem
```

**Pros:**
- ✅ Build MVP in 1-2 hours
- ✅ Zero deployment friction (run locally)
- ✅ Built-in file upload, progress bars, download
- ✅ Perfect for iterative prompt development
- ✅ Single codebase (Python only)
- ✅ Easy debugging and cost tracking
- ✅ Free cloud deployment option (Streamlit Cloud)

**Cons:**
- ⚠️ UI customization limited vs custom React
- ⚠️ Not ideal for public multi-user scenarios

**When to Choose:**
- Need tool working THIS WEEK
- Prioritize functionality over aesthetics
- Solo user or small team (<10 people)
- Want rapid prompt iteration

**Effort:** 2-4 hours for MVP

---

### Option B: FastAPI + Alpine.js

**Stack:**
```
Backend: FastAPI (Python, async)
Frontend: HTML + Alpine.js (no build step)
LLM: Claude/OpenAI API
Storage: Local + optional S3
Communication: WebSocket for progress
```

**Pros:**
- ✅ More UI control than Streamlit
- ✅ Async processing (handle multiple uploads)
- ✅ RESTful API (reusable for other clients)
- ✅ Professional architecture
- ✅ Easier to add auth/multi-user later

**Cons:**
- ⚠️ 3-5x more code than Streamlit
- ⚠️ Manual progress tracking implementation
- ⚠️ Deployment more complex (2 components)

**When to Choose:**
- Plan to share with team (10+ users)
- Want API for future integrations
- Need custom branding/design
- Have 1-2 days for initial build

**Effort:** 1-2 days for MVP

---

### Option C: Next.js + Python Backend ❌ NOT RECOMMENDED

**Why Rejected:**
- ❌ Vercel serverless timeout (60s max, even Pro)
- ❌ Processing takes 1-5min → requires webhook/polling complexity
- ❌ Two codebases for personal tool = maintenance burden
- ❌ Overkill for non-public tool
- ❌ Higher deployment costs

**Only Consider If:**
- Building public SaaS
- Need SEO/marketing pages
- Want portfolio project (not productivity tool)
- Have 2+ weeks development time

---

## Recommended Solution: Streamlit MVP

### Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                  Streamlit App                      │
│  ┌───────────────────────────────────────────────┐  │
│  │  UI Layer (app.py)                            │  │
│  │  - File upload widget                         │  │
│  │  - Processing controls                        │  │
│  │  - Preview pane                               │  │
│  │  - Download button                            │  │
│  └───────────────────────────────────────────────┘  │
│                      ↓                              │
│  ┌───────────────────────────────────────────────┐  │
│  │  Processing Layer                             │  │
│  │  - transcript_parser.py (SRT/VTT → text)      │  │
│  │  - chunker.py (split with context buffer)    │  │
│  │  - llm_processor.py (API calls)               │  │
│  │  - validator.py (rule-based checks)           │  │
│  └───────────────────────────────────────────────┘  │
│                      ↓                              │
│  ┌───────────────────────────────────────────────┐  │
│  │  Output Layer                                 │  │
│  │  - markdown_writer.py                         │  │
│  │  - metadata_tracker.py                        │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
         ↓                               ↑
    Claude API                    Cleaned Markdown
    OpenAI API                    + Metadata JSON
```

### File Structure

```
transcript_write/
├── app.py                          # Streamlit main app
├── requirements.txt                # Dependencies
├── .env.example                    # API key template
├── README.md                       # Current prompt spec
│
├── src/
│   ├── __init__.py
│   ├── transcript_parser.py        # Parse SRT/VTT to text
│   ├── chunker.py                  # Smart chunking with context
│   ├── llm_processor.py            # API calls + retry logic
│   ├── validator.py                # Rule-based validation
│   ├── markdown_writer.py          # Format & save output
│   └── cost_estimator.py           # Token counting + cost calc
│
├── prompts/
│   ├── base_prompt.txt             # Your current README prompt
│   ├── lecture_prompt.txt          # Lecture-specific variant
│   └── qa_prompt.txt               # Q&A format variant
│
├── output/                         # Generated files
│   ├── {video-title}.md
│   ├── {video-title}-metadata.json
│   └── {video-title}-original.srt
│
├── tests/
│   ├── test_chunker.py
│   ├── test_parser.py
│   └── fixtures/
│       ├── sample.srt
│       └── sample.vtt
│
└── docs/
    └── architecture.md             # This document
```

---

## Module Design

### 1. `transcript_parser.py`

**Responsibility:** Convert SRT/VTT to plain text with timestamps

```python
class TranscriptParser:
    """Parse subtitle files to structured format"""

    def parse_srt(file_path: str) -> List[TranscriptSegment]
    def parse_vtt(file_path: str) -> List[TranscriptSegment]
    def to_plain_text(segments: List[TranscriptSegment]) -> str
```

**Key Features:**
- Detect format automatically
- Extract timestamps + text
- Remove duplicate lines
- Handle malformed entries gracefully

---

### 2. `chunker.py`

**Responsibility:** Split long transcripts with context preservation

```python
class SmartChunker:
    """Chunk transcript while preserving context"""

    def __init__(chunk_size: int = 2000, overlap: int = 200)

    def chunk_transcript(
        text: str,
        timestamps: List[Timestamp]
    ) -> List[Chunk]

    def get_context_buffer(
        previous_chunk: str,
        buffer_size: int = 200
    ) -> str
```

**Chunking Strategy:**
1. Split at sentence boundaries (prefer `.!?`)
2. Keep timestamp markers intact
3. Add context buffer from previous chunk (read-only)
4. Never split mid-sentence if possible

**Example Chunk Structure:**
```
[CONTEXT FROM PREVIOUS SECTION]
...last 200 chars of previous chunk...

[NEW CONTENT TO PROCESS]
[00:15:45]
The concept of gradient descent...
```

---

### 3. `llm_processor.py`

**Responsibility:** Handle LLM API calls with retry and error handling

```python
class LLMProcessor:
    """Process chunks via Claude/OpenAI API"""

    def __init__(
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.3
    )

    async def process_chunk(
        chunk: Chunk,
        prompt_template: str,
        context: Optional[str] = None
    ) -> ProcessedChunk

    def estimate_cost(chunks: List[Chunk]) -> float
```

**Features:**
- Async processing (process chunks in parallel when safe)
- Retry logic (3 attempts with exponential backoff)
- Token counting before sending
- Rate limit handling
- Error recovery (save progress, resume from failed chunk)

---

### 4. `validator.py`

**Responsibility:** Rule-based validation to catch common LLM mistakes

```python
class OutputValidator:
    """Validate cleaned transcript against rules"""

    def validate_chunk(
        original: str,
        cleaned: str
    ) -> ValidationResult

    def check_filler_removal(text: str) -> bool
    def check_timestamp_format(text: str) -> bool
    def check_no_context_duplication(text: str) -> bool
    def check_technical_terms_preserved(text: str) -> bool
```

**Validation Rules:**
- ❌ No fillers remain (uh, um, like, you know)
- ❌ No context section in output
- ✅ Timestamps match format `[HH:MM:SS]`
- ✅ Technical terms not translated
- ✅ Content length reasonable (not truncated)

**Why Rule-Based?**
- Cheaper than LLM double-check
- Catches 80% of common errors
- Fast feedback loop

---

### 5. `markdown_writer.py`

**Responsibility:** Format and save cleaned transcript

```python
class MarkdownWriter:
    """Write cleaned transcript to markdown"""

    def write_markdown(
        chunks: List[ProcessedChunk],
        output_path: str,
        metadata: dict
    ) -> None

    def add_metadata_header(metadata: dict) -> str
    def merge_chunks(chunks: List[ProcessedChunk]) -> str
```

**Output Format:**
```markdown
# Video Title

**Original Duration:** 01:45:23
**Processed:** 2025-12-24 18:32:00
**Model:** claude-3-5-sonnet-20241022
**Cost:** $1.25

---

[00:00:15]
The lecture begins with an introduction to...

[00:02:30]
Machine Learning is a subset of artificial intelligence...
```

---

### 6. `cost_estimator.py`

**Responsibility:** Estimate costs before processing

```python
class CostEstimator:
    """Estimate API costs before processing"""

    PRICING = {
        "claude-3-5-sonnet-20241022": {
            "input": 0.003,   # per 1K tokens
            "output": 0.015
        },
        "gpt-4-turbo": {
            "input": 0.01,
            "output": 0.03
        }
    }

    def estimate_tokens(text: str) -> int
    def estimate_cost(chunks: List[Chunk], model: str) -> CostBreakdown
```

**Show Before Processing:**
```
Estimated Cost:
  Input tokens: 125,000 (~$0.38)
  Output tokens: 95,000 (~$1.43)
  Total: ~$1.81

Chunks: 42
Processing time: ~3-5 minutes

[Proceed] [Cancel]
```

---

## Streamlit UI Flow

### Main Page Layout

```
┌────────────────────────────────────────────────────┐
│  📝 Transcript Cleaning Tool                       │
│  Clean lecture transcripts for study notes         │
├────────────────────────────────────────────────────┤
│                                                    │
│  [Step 1: Upload Transcript]                       │
│  ┌──────────────────────────────────────────────┐  │
│  │  Drag & drop or browse                       │  │
│  │  Supported: .srt, .vtt                       │  │
│  └──────────────────────────────────────────────┘  │
│                                                    │
│  [Step 2: Configure]                               │
│  Model: [Claude 3.5 Sonnet ▼]                      │
│  Prompt: [Lecture (default) ▼] [Edit Prompt]       │
│  Chunk size: [2000] chars                          │
│                                                    │
│  💰 Estimated cost: $1.25 | ⏱️ Est. time: 3 min    │
│                                                    │
│  [Process Transcript]                              │
│                                                    │
│  [Step 3: Preview & Download]                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  Processing... 15/42 chunks (35%)            │  │
│  │  ▓▓▓▓▓▓▓▓░░░░░░░░░░░░                        │  │
│  └──────────────────────────────────────────────┘  │
│                                                    │
│  Preview:                                          │
│  ┌──────────────────────────────────────────────┐  │
│  │  [00:15:30]                                  │  │
│  │  The concept of gradient descent refers...   │  │
│  │                                              │  │
│  │  [00:16:45]                                  │  │
│  │  To optimize the loss function...           │  │
│  └──────────────────────────────────────────────┘  │
│                                                    │
│  [Download Markdown] [Download ZIP]                │
│                                                    │
└────────────────────────────────────────────────────┘
```

### Code Structure (`app.py`)

```python
import streamlit as st
from src import (
    TranscriptParser, SmartChunker, LLMProcessor,
    OutputValidator, MarkdownWriter, CostEstimator
)

st.set_page_config(page_title="Transcript Cleaner", layout="wide")

# Sidebar configuration
with st.sidebar:
    api_key = st.text_input("API Key", type="password")
    model = st.selectbox("Model", ["claude-3-5-sonnet", "gpt-4-turbo"])
    prompt_type = st.selectbox("Prompt", ["Lecture", "Q&A", "Custom"])

# Main content
st.title("📝 Transcript Cleaning Tool")

# Step 1: Upload
uploaded_file = st.file_uploader("Upload transcript", type=["srt", "vtt"])

if uploaded_file:
    # Parse transcript
    parser = TranscriptParser()
    segments = parser.parse(uploaded_file)

    # Show preview
    with st.expander("Original transcript preview"):
        st.text(segments[:500])

    # Estimate cost
    estimator = CostEstimator()
    cost = estimator.estimate(segments, model)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Estimated Cost", f"${cost.total:.2f}")
    with col2:
        st.metric("Processing Time", f"~{cost.time_minutes} min")

    # Process button
    if st.button("Process Transcript", type="primary"):
        # Create chunker
        chunker = SmartChunker()
        chunks = chunker.chunk_transcript(segments)

        # Process with progress bar
        processor = LLMProcessor(api_key, model)
        progress_bar = st.progress(0)

        cleaned_chunks = []
        for i, chunk in enumerate(chunks):
            result = processor.process_chunk(chunk)
            cleaned_chunks.append(result)
            progress_bar.progress((i + 1) / len(chunks))

        # Validate
        validator = OutputValidator()
        validation = validator.validate_all(cleaned_chunks)

        if validation.has_errors:
            st.warning(f"⚠️ {len(validation.errors)} validation issues")
            with st.expander("Show issues"):
                st.json(validation.errors)

        # Write output
        writer = MarkdownWriter()
        output_path = writer.write(cleaned_chunks)

        # Show preview
        st.success("✅ Processing complete!")
        st.markdown("### Preview")
        with open(output_path) as f:
            st.markdown(f.read())

        # Download button
        with open(output_path, "rb") as f:
            st.download_button(
                "Download Markdown",
                f,
                file_name=f"{uploaded_file.name}.md"
            )
```

---

## Cost Analysis

### Claude 3.5 Sonnet Pricing (Dec 2024)
- Input: $0.003 / 1K tokens
- Output: $0.015 / 1K tokens

### Example: 60-Minute Lecture

**Assumptions:**
- Transcript length: ~15,000 words
- Chunk size: 2000 chars (~400 words)
- Chunks: ~38 chunks
- Context buffer: 200 chars per chunk
- Prompt template: 500 tokens
- Average output: 80% of input length

**Token Calculation:**
```
Input tokens per chunk:
  - Chunk text: ~600 tokens
  - Context buffer: ~50 tokens
  - Prompt template: ~500 tokens
  - Total per chunk: ~1,150 tokens

Total input: 38 chunks × 1,150 = 43,700 tokens
Total output: 38 chunks × 480 = 18,240 tokens

Cost:
  Input: 43,700 / 1000 × $0.003 = $0.13
  Output: 18,240 / 1000 × $0.015 = $0.27
  Total: ~$0.40
```

**Cost per video type:**
- 30-min lecture: ~$0.20
- 60-min lecture: ~$0.40
- 90-min lecture: ~$0.60

**Optimization opportunities:**
- Reduce prompt template size (current 500 tokens → 300 tokens = 30% savings)
- Use Claude Haiku for simple transcripts ($0.08 per 60-min video)
- Batch processing discount (if API supports)

---

## Migration Path (If Needed Later)

### When to Migrate from Streamlit

**Triggers:**
1. >10 concurrent users
2. Need user authentication
3. Want mobile app integration
4. Require custom branding
5. Need API for other tools

### Migration Strategy: Streamlit → FastAPI

**Phase 1: Extract business logic (1 day)**
```
Current:
  app.py (UI + logic mixed)

After:
  app.py (Streamlit UI only)
  src/service.py (business logic)
  src/api.py (FastAPI endpoints - optional)
```

**Phase 2: Add FastAPI alongside (2 days)**
```
Run both:
  - Streamlit for personal use (localhost:8501)
  - FastAPI for team API (localhost:8000)
```

**Phase 3: Replace frontend (3-5 days)**
```
Decommission Streamlit, build:
  - Next.js / React frontend
  - FastAPI backend (reuse existing logic)
```

**Key insight:** Clean separation NOW makes migration easy LATER.

---

## Success Metrics

### MVP Success Criteria (Week 1)
- ✅ Process 60-min transcript in <5 min
- ✅ Cost <$0.50 per video
- ✅ 90%+ filler removal accuracy
- ✅ Zero context duplication in output
- ✅ Preserves 100% technical terms
- ✅ Can iterate prompt in <5 min

### Production Metrics (Month 1)
- ✅ Process 20+ videos successfully
- ✅ <2% validation errors
- ✅ Average cost <$0.30 per video (via optimization)
- ✅ User satisfaction (self-reported)

---

## Implementation Timeline

### Week 1: MVP
**Day 1-2:**
- ✅ Setup Streamlit project structure
- ✅ Implement `transcript_parser.py`
- ✅ Implement `chunker.py`
- ✅ Basic Streamlit UI (upload + display)

**Day 3-4:**
- ✅ Implement `llm_processor.py`
- ✅ Integrate Claude API
- ✅ Add progress tracking
- ✅ Test with sample transcripts

**Day 5:**
- ✅ Implement `validator.py`
- ✅ Implement `markdown_writer.py`
- ✅ Add cost estimator
- ✅ Polish UI

**Day 6-7:**
- ✅ Testing + bug fixes
- ✅ Prompt tuning
- ✅ Documentation
- ✅ Deploy to Streamlit Cloud (optional)

### Week 2: Enhancement (Optional)
- Batch upload support
- Custom prompt editor
- Side-by-side comparison
- Export to PDF/DOCX
- Cost tracking dashboard

---

## Technology Stack

### Core Dependencies
```txt
# requirements.txt
streamlit==1.29.0
anthropic==0.8.0          # Claude API
openai==1.6.0             # OpenAI API (optional)
python-dotenv==1.0.0      # Environment variables
pysrt==1.1.2              # SRT parsing
webvtt-py==0.4.6          # VTT parsing
tiktoken==0.5.2           # Token counting
tenacity==8.2.3           # Retry logic
pytest==7.4.3             # Testing
```

### Development Tools
```txt
black==23.12.0            # Code formatting
ruff==0.1.9               # Linting
mypy==1.7.1               # Type checking
```

---

## Risk Analysis & Mitigation

### Risk 1: Token Limit Exceeded
**Probability:** Medium
**Impact:** High
**Mitigation:**
- Chunking strategy with conservative size (2000 chars)
- Pre-validation before API call
- Token counter with buffer (90% of limit)

### Risk 2: High API Costs
**Probability:** Medium
**Impact:** Medium
**Mitigation:**
- Cost estimator shown before processing
- Use cheaper models for simple transcripts (Haiku)
- Rule-based validation instead of double-pass LLM
- User confirmation required for >$1 costs

### Risk 3: Context Loss Between Chunks
**Probability:** Low
**Impact:** High
**Mitigation:**
- Context buffer from previous chunk
- Smart chunking at sentence boundaries
- Validation checks for incomplete thoughts
- Manual review UI for suspicious chunks

### Risk 4: LLM Hallucination
**Probability:** Low
**Impact:** Medium
**Mitigation:**
- Low temperature (0.3)
- Explicit "DO NOT add new information" in prompt
- Validator checks for content preservation
- Side-by-side preview for user verification

### Risk 5: Streamlit Limitations
**Probability:** Low (for personal use)
**Impact:** Low
**Mitigation:**
- Clean code separation (easy to migrate)
- FastAPI migration path documented
- No Streamlit-specific business logic

---

## Alternative Approaches Considered

### A. Use Existing Tools (e.g., Descript, Otter.ai)
**Why Rejected:**
- Not optimized for Vietnamese learner audience
- Can't customize cleaning rules
- Subscription costs vs API usage
- No control over prompt engineering

### B. Local LLM (Ollama, LM Studio)
**Why Deferred:**
- Initial quality testing needs best models (Claude/GPT-4)
- Can add later after prompt stabilization
- Complexity not worth it for personal tool
- API costs acceptable for current volume

### C. Fine-Tuned Model
**Why Rejected:**
- Massive overkill for personal tool
- Requires training data collection
- Maintenance burden
- Modern LLMs with good prompts are sufficient

### D. Rule-Based Only (No LLM)
**Why Rejected:**
- Cannot handle semantic restructuring
- Would produce transcript, not study notes
- Cannot convert questions to statements
- Misses the core value proposition

---

## Open Questions & Future Considerations

### Unresolved Questions
1. **Prompt versioning:** How to track prompt changes over time?
   - **Suggestion:** Git-based prompt templates with version tags

2. **Quality measurement:** How to quantitatively measure output quality?
   - **Options:**
     - Manual review of random 10% samples
     - Compare against gold-standard human-edited transcripts
     - User satisfaction survey after 20 videos

3. **Multi-language support:** Will you process Vietnamese transcripts later?
   - **Impact:** Would need separate prompt templates
   - **Decision:** Defer until needed (YAGNI)

4. **Collaboration:** Will you share with others who need API keys?
   - **Options:**
     - Shared API key (simple)
     - User brings own API key (Streamlit secrets)
     - Backend proxy with auth (complex, defer)

### Future Enhancements (Not MVP)
- YouTube URL direct input (auto-download captions)
- Audio file upload → transcribe → clean (two-step)
- Glossary management (custom technical terms)
- Multi-format export (PDF, DOCX, Notion)
- Comparison mode (original vs cleaned side-by-side)
- Analytics dashboard (costs, videos processed, time saved)
- Webhook integration (process → auto-upload to Google Drive)

---

## Conclusion & Recommendation

### Final Recommendation: **Streamlit MVP**

**Rationale:**
1. **Speed to value:** Working tool in 2 days vs 2 weeks
2. **Flexibility:** Easy prompt iteration (your primary need)
3. **Simplicity:** Single codebase, minimal deployment
4. **Cost:** Free to run locally, cheap to deploy
5. **Future-proof:** Clean architecture allows migration if needed

**Why NOT over-engineer:**
- You're the primary user (no scaling needed yet)
- Prompt quality > UI polish at this stage
- Can always migrate later with clear path
- YAGNI principle applies perfectly here

### Next Steps

1. **Immediate (This Week):**
   - Setup Streamlit project structure
   - Implement core modules (parser, chunker, processor)
   - Get first end-to-end test working

2. **Week 2:**
   - Polish UI/UX
   - Add validation + cost estimator
   - Process 5-10 real videos
   - Tune prompts based on results

3. **Month 2:**
   - Evaluate if Streamlit still fits needs
   - Consider FastAPI migration if sharing widely
   - Add enhancement features based on usage

**Success Indicator:** If you're using this tool weekly and finding value, the architecture is correct. If you're not using it, even the best architecture doesn't matter.

---

## Appendix: Code Examples

### Example: Smart Chunker

```python
# src/chunker.py
import re
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Chunk:
    """Represents a text chunk with metadata"""
    index: int
    text: str
    start_timestamp: str
    end_timestamp: str
    context_buffer: Optional[str] = None

class SmartChunker:
    """Split transcript into chunks with context preservation"""

    def __init__(self, chunk_size: int = 2000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_transcript(
        self,
        text: str,
        timestamps: List[tuple]
    ) -> List[Chunk]:
        """Split transcript at sentence boundaries with context"""

        chunks = []
        current_pos = 0
        chunk_index = 0
        previous_chunk_text = ""

        while current_pos < len(text):
            # Extract chunk
            end_pos = min(current_pos + self.chunk_size, len(text))

            # Find sentence boundary
            if end_pos < len(text):
                # Look for sentence end within 100 chars
                search_start = max(end_pos - 100, current_pos)
                sentence_end = self._find_sentence_boundary(
                    text[search_start:end_pos + 100]
                )
                if sentence_end:
                    end_pos = search_start + sentence_end

            chunk_text = text[current_pos:end_pos]

            # Get context buffer from previous chunk
            context_buffer = None
            if previous_chunk_text:
                context_buffer = previous_chunk_text[-self.overlap:]

            # Find timestamps for this chunk
            start_ts, end_ts = self._get_chunk_timestamps(
                current_pos, end_pos, timestamps
            )

            chunks.append(Chunk(
                index=chunk_index,
                text=chunk_text,
                start_timestamp=start_ts,
                end_timestamp=end_ts,
                context_buffer=context_buffer
            ))

            previous_chunk_text = chunk_text
            current_pos = end_pos
            chunk_index += 1

        return chunks

    def _find_sentence_boundary(self, text: str) -> Optional[int]:
        """Find last sentence ending in text"""
        # Look for . ! ? followed by space or newline
        pattern = r'[.!?][\s\n]'
        matches = list(re.finditer(pattern, text))

        if matches:
            # Return position after punctuation + space
            return matches[-1].end()
        return None

    def _get_chunk_timestamps(
        self,
        start_pos: int,
        end_pos: int,
        timestamps: List[tuple]
    ) -> tuple:
        """Get start and end timestamps for chunk"""
        # Implementation depends on timestamp format
        # Returns (start_timestamp, end_timestamp)
        pass
```

### Example: LLM Processor with Retry

```python
# src/llm_processor.py
import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential
from dataclasses import dataclass

@dataclass
class ProcessedChunk:
    """Result of LLM processing"""
    chunk_index: int
    cleaned_text: str
    input_tokens: int
    output_tokens: int
    cost: float
    model: str

class LLMProcessor:
    """Process chunks via Claude API with retry logic"""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.3
    ):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.temperature = temperature

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def process_chunk(
        self,
        chunk: Chunk,
        prompt_template: str
    ) -> ProcessedChunk:
        """Process single chunk with retry on failure"""

        # Build prompt
        user_message = self._build_message(chunk, prompt_template)

        # Call API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
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
            cleaned_text=cleaned_text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost=cost,
            model=self.model
        )

    def _build_message(self, chunk: Chunk, template: str) -> str:
        """Build prompt with chunk and context"""

        message_parts = []

        # Add context buffer if exists
        if chunk.context_buffer:
            message_parts.append(
                "[CONTEXT FROM PREVIOUS SECTION]\n"
                f"{chunk.context_buffer}\n"
            )

        # Add instruction
        message_parts.append(
            "[NEW CONTENT TO PROCESS]\n"
            f"{chunk.text}"
        )

        # Combine with template
        return template.replace("{{chunkText}}", "\n".join(message_parts))

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage"""
        PRICING = {
            "claude-3-5-sonnet-20241022": {
                "input": 0.003,
                "output": 0.015
            }
        }

        prices = PRICING[self.model]
        cost = (
            (input_tokens / 1000) * prices["input"] +
            (output_tokens / 1000) * prices["output"]
        )
        return cost
```

---

**End of Architecture Document**

**Status:** Ready for implementation
**Estimated MVP Timeline:** 5-7 days
**Estimated MVP Cost:** <$20 (including testing with real transcripts)

**Approval Required:** None (personal project)
**Next Action:** Begin implementation with Streamlit MVP
