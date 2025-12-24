# Phase 6: Testing & Polish

**Effort:** 2.5 hours
**Dependencies:** Phase 5 (UI complete)
**Deliverables:** Integration tests, documentation, prompt tuning, error handling improvements

---

## Tasks

### 6.1 Integration Testing with Real Transcripts

**Test with sample files:**

1. Create test fixtures:
```
tests/fixtures/
├── sample.srt           # Short sample (2-3 min)
├── sample.vtt           # VTT format sample
└── lecture-60min.srt    # Full lecture (optional, for manual testing)
```

2. **End-to-end test (mocked API):**

```python
# tests/test_integration.py
"""Integration tests for full pipeline"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src import (
    TranscriptParser,
    SmartChunker,
    LLMProcessor,
    OutputValidator,
    MarkdownWriter,
    CostEstimator
)


class TestFullPipeline:
    """Test complete processing pipeline"""

    @pytest.fixture
    def sample_srt(self, tmp_path):
        """Create sample SRT file"""
        content = """1
00:00:01,000 --> 00:00:05,000
Uh, hello everyone, welcome to the lecture.

2
00:00:06,000 --> 00:00:10,000
So, like, today we're going to talk about machine learning.

3
00:00:11,000 --> 00:00:15,000
You know, machine learning is basically a subset of AI.

4
00:00:16,000 --> 00:00:20,000
The concept is really quite simple, actually.

5
00:00:21,000 --> 00:00:25,000
Why does this matter? Because it helps automate decisions.
"""
        srt_file = tmp_path / "sample.srt"
        srt_file.write_text(content)
        return srt_file

    @pytest.fixture
    def prompt_template(self, tmp_path):
        """Create prompt template"""
        content = """Clean this transcript.

[VIDEO INFO]
Title: {{fileName}}

[TRANSCRIPT TO PROCESS]
{{chunkText}}
"""
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text(content)
        return prompt_file

    def test_parse_chunk_flow(self, sample_srt):
        """Test parsing and chunking"""
        # Parse
        parser = TranscriptParser()
        segments = parser.parse(sample_srt)

        assert len(segments) > 0
        assert all(s.text for s in segments)

        # Convert to text
        text = parser.to_plain_text(segments)
        assert "[00:00:01]" in text

        # Chunk
        chunker = SmartChunker(chunk_size=500, overlap=50)
        chunks = chunker.chunk_transcript(text)

        assert len(chunks) >= 1
        assert chunks[0].text

    @patch('src.llm_processor.anthropic.Anthropic')
    def test_full_pipeline(self, mock_anthropic, sample_srt, prompt_template, tmp_path):
        """Test complete pipeline with mocked API"""
        # Setup mock
        mock_response = Mock()
        mock_response.content = [Mock(text="[00:00:01]\nCleaned content here.")]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_anthropic.return_value.messages.create.return_value = mock_response

        # Parse
        parser = TranscriptParser()
        segments = parser.parse(sample_srt)
        text = parser.to_plain_text(segments)

        # Chunk
        chunker = SmartChunker(chunk_size=500, overlap=50)
        chunks = chunker.chunk_transcript(text)

        # Estimate cost
        estimator = CostEstimator()
        template = prompt_template.read_text()
        estimate = estimator.estimate_total(chunks, template)

        assert estimate.total_cost > 0
        assert estimate.chunks == len(chunks)

        # Process (mocked)
        processor = LLMProcessor(api_key="test-key")
        results = processor.process_all_chunks(chunks, template, "Test Video")

        assert len(results) == len(chunks)

        # Validate
        validator = OutputValidator()
        validation = validator.validate_all(results)

        # Should have no context markers in output
        context_errors = [i for i in validation.issues
                        if i.rule == "context_marker_in_output"]
        assert len(context_errors) == 0

        # Write
        writer = MarkdownWriter(output_dir=str(tmp_path / "output"))
        summary = {
            "chunks_processed": len(results),
            "total_input_tokens": 100,
            "total_output_tokens": 50,
            "total_cost": 0.01,
            "model": "test-model"
        }
        md_path, json_path = writer.write(results, "Test Video", summary)

        assert md_path.exists()
        assert json_path.exists()
        assert "Test Video" in md_path.read_text()


class TestErrorHandling:
    """Test error handling scenarios"""

    def test_invalid_file_format(self, tmp_path):
        """Reject unsupported file format"""
        txt_file = tmp_path / "invalid.txt"
        txt_file.write_text("Not a subtitle file")

        parser = TranscriptParser()
        with pytest.raises(ValueError, match="Unsupported format"):
            parser.parse(txt_file)

    def test_empty_file(self, tmp_path):
        """Handle empty file gracefully"""
        empty_srt = tmp_path / "empty.srt"
        empty_srt.write_text("")

        parser = TranscriptParser()
        segments = parser.parse(empty_srt)

        assert segments == []

    def test_malformed_srt(self, tmp_path):
        """Handle malformed SRT gracefully"""
        bad_srt = tmp_path / "bad.srt"
        bad_srt.write_text("Not valid SRT content\nJust random text")

        parser = TranscriptParser()
        # Should not crash, may return empty or partial
        try:
            segments = parser.parse(bad_srt)
            # If it parses, should be empty or have valid segments
            assert isinstance(segments, list)
        except Exception:
            # Some errors are acceptable for malformed input
            pass
```

---

### 6.2 Manual Testing Checklist

**Before release, manually test:**

- [ ] Upload 30-min lecture SRT
- [ ] Upload 60-min lecture VTT
- [ ] Verify cost estimate accuracy (within 20%)
- [ ] Check filler word removal
- [ ] Verify no context markers in output
- [ ] Verify timestamps preserved correctly
- [ ] Test with different chunk sizes
- [ ] Test error cases (invalid API key, network error)
- [ ] Download and verify Markdown output
- [ ] Download and verify JSON metadata

---

### 6.3 Prompt Tuning Guidelines

**Based on real transcript results:**

1. **Filler removal too aggressive?**
   - Adjust validator threshold
   - Review FILLERS list in validator.py

2. **Questions not converted?**
   - Strengthen prompt: "MUST convert all rhetorical questions"
   - Add examples in prompt

3. **Technical terms translated?**
   - Add explicit list to prompt: "NEVER translate: API, ML, AI, ..."
   - Add to validator check

4. **Output too short/long?**
   - Adjust validator ratio thresholds
   - Review prompt instructions

**Prompt iteration workflow:**
```bash
# Edit prompt
nano prompts/base_prompt.txt

# Test with same file
streamlit run app.py

# Compare outputs
diff output/test-v1.md output/test-v2.md
```

---

### 6.4 Error Handling Improvements

**Add user-friendly error messages in app.py:**

```python
# Error handling wrapper
def safe_process(func):
    """Wrap processing with user-friendly errors"""
    try:
        return func()
    except anthropic.AuthenticationError:
        st.error("❌ Invalid API key. Check your Anthropic API key.")
    except anthropic.RateLimitError:
        st.error("⏳ Rate limit reached. Please wait a moment and try again.")
    except anthropic.APIConnectionError:
        st.error("🌐 Network error. Check your internet connection.")
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        # Log full error for debugging
        import traceback
        with st.expander("Error details"):
            st.code(traceback.format_exc())
    return None
```

---

### 6.5 Documentation Updates

**Update README.md:**

```markdown
# Transcript Cleaning Tool

Convert lecture transcripts (SRT/VTT) to clean study notes using Claude API.

## Features

- Parse SRT and VTT subtitle files
- Smart chunking with context preservation
- Claude API integration with retry logic
- Cost estimation before processing
- Rule-based output validation
- Markdown export with metadata

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set API key:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-xxx
   ```

3. Run:
   ```bash
   streamlit run app.py
   ```

## Configuration

- **Model**: claude-3-5-sonnet (quality) or claude-3-5-haiku (speed)
- **Chunk size**: 1000-4000 chars (default 2000)
- **Overlap**: 0-500 chars (default 200)

## Cost Estimates

| Video Length | Estimated Cost |
|--------------|----------------|
| 30 min       | ~$0.20         |
| 60 min       | ~$0.40         |
| 90 min       | ~$0.60         |

## Project Structure

```
transcript_write/
├── app.py                 # Streamlit UI
├── src/                   # Core modules
│   ├── transcript_parser.py
│   ├── chunker.py
│   ├── llm_processor.py
│   ├── validator.py
│   ├── markdown_writer.py
│   └── cost_estimator.py
├── prompts/               # Prompt templates
├── output/                # Generated files
└── tests/                 # Unit & integration tests
```

## License

MIT
```

---

### 6.6 Final Checklist

**Code quality:**
- [ ] All functions have docstrings
- [ ] Type hints on public functions
- [ ] No hardcoded secrets
- [ ] Error handling in all modules

**Testing:**
- [ ] Unit tests pass: `pytest tests/ -v`
- [ ] Integration test passes
- [ ] Manual testing complete

**Documentation:**
- [ ] README.md updated
- [ ] .env.example includes all vars
- [ ] Inline comments where needed

**Deployment ready:**
- [ ] requirements.txt complete
- [ ] .gitignore covers all sensitive files
- [ ] No debug code left in

---

## Success Criteria (Final MVP)

- [ ] Process 60-min transcript in <5 min
- [ ] Cost <$0.50 per video
- [ ] 90%+ filler removal accuracy
- [ ] Zero context duplication in output
- [ ] Preserves 100% technical terms
- [ ] User can iterate prompt in <5 min
- [ ] Clean, downloadable Markdown output
- [ ] Accurate cost estimation

---

## Post-MVP Improvements (Deferred)

- Batch processing (multiple files)
- Custom prompt editor in UI
- Side-by-side comparison view
- Export to PDF/DOCX
- Cost tracking dashboard
- YouTube URL direct input
- Prompt versioning system
