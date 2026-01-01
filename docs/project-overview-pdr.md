# Project Overview & Product Development Requirements

## Project: Transcript Cleaner MVP

**Version:** 0.5.0
**Phase:** 7 - Pause/Resume & Resilience Complete
**Last Updated:** 2026-01-01

---

## Executive Summary

Transcript Cleaner is an automated tool that transforms raw lecture transcripts into structured, study-ready materials for Vietnamese learners of English. The tool cleans, rewrites, and organizes spoken content into professional study notes while preserving 100% of original meaning. Now with pause/resume capability for uninterrupted processing of long transcripts.

**Status:** Phase 7 Complete - Core MVP + Pause/Resume resilience, state management, and auto-recovery fully implemented with 112 passing tests.

---

## What We're Building

### Core Problem
Lecture transcripts contain filler language, hesitations, incomplete thoughts, and conversational noise that makes them unsuitable for studying. Manual cleaning is time-consuming and inconsistent.

### Solution
A Streamlit-based web application that:
1. Accepts transcript uploads (SRT, VTT, or plain text)
2. Splits transcripts into manageable chunks
3. Uses Claude API to intelligently rewrite each chunk
4. Validates output quality and consistency
5. Generates clean, study-ready Markdown files

### Target Users
Vietnamese learners who:
- Work with English lecture recordings
- Need high-quality study materials
- Want to convert spoken content into written format
- Require consistent, professional output

---

## Technical Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **UI Framework** | Streamlit | >=1.29.0 |
| **LLM Providers** | Anthropic Claude + DeepSeek | 0.75.0+ |
| **Core Language** | Python | 3.9+ |
| **Subtitle Parsing** | pysrt, webvtt-py | Latest |
| **Token Management** | tiktoken | >=0.5.2 |
| **Retry Logic** | tenacity | >=8.2.3 |
| **State Persistence** | filelock | >=4.0+ |
| **Config Management** | python-dotenv | >=1.0.0 |
| **Testing** | pytest | >=7.4.3 |

---

## Product Requirements

### Functional Requirements

#### FR1: Input Handling
- Accept SRT subtitle files (.srt)
- Accept WebVTT files (.vtt)
- Accept plain text transcripts
- Extract timestamps and content reliably

#### FR2: Content Processing
- Chunk transcripts to respect token limits (~4000 tokens per chunk)
- Maintain context between chunks
- Handle overlapping sections for coherence

#### FR3: Transcript Cleaning
- Apply base prompt rules (see `prompts/base_prompt.txt`)
- Remove all filler sounds and hesitation phrases
- Convert rhetorical questions to declarative statements
- Organize content by concept, not timestamp
- Preserve ALL technical information and meaning

#### FR4: Output Generation
- Generate Markdown-formatted output
- Include timestamps at logical section boundaries
- Create downloadable cleaned transcripts
- Support batch processing

#### FR5: Cost Tracking
- Estimate API costs before processing
- Track actual costs per transcript
- Display cost summary to user

#### FR6: Pause/Resume (Phase 7)
- Allow users to pause processing at any time
- Resume processing from saved checkpoint without data loss
- Auto-detect incomplete jobs on startup
- Track progress per-chunk with state persistence
- Auto-recover from network failures
- Cache completed chunks locally

### Non-Functional Requirements

#### NFR1: Performance
- Process transcripts within reasonable time (max 2 min for standard lecture)
- Handle transcripts up to 2 hours long
- Efficient chunk management and API calls

#### NFR2: Reliability
- Graceful error handling for malformed inputs
- Retry logic for API failures
- Validation of cleaned output
- State persistence with atomic writes
- Automatic recovery from crashes
- Data integrity with file locking
- Backup state files for corruption recovery

#### NFR3: Security
- API key management via environment variables
- No sensitive data in logs
- Secure input validation

#### NFR4: Maintainability
- Modular architecture with single-responsibility modules
- Clear separation: parsing, chunking, LLM, validation, output
- Comprehensive error messages
- Well-documented code and configuration

---

## Architecture Overview

```
User Input (Streamlit UI)
    ↓
Parser (handles SRT/VTT/TXT)
    ↓
Chunker (respects token limits)
    ↓
LLM Processor (Claude API with base prompt)
    ↓
Validator (quality checks)
    ↓
Writer (Markdown output)
    ↓
Cost Estimator
    ↓
User Output (Download/Preview)
```

See `system-architecture.md` for detailed architecture.

---

## Development Phases

| Phase | Focus | Status | Deliverables |
|-------|-------|--------|--------------|
| **1** | Setup & Dependencies | ✓ Complete | requirements.txt, .env.example, .gitignore, src structure, base prompt |
| **2** | Parsing & Chunking | ✓ Complete | Parser module, Chunker module, tests |
| **3** | LLM Integration | ✓ Complete | Claude API integration, retry logic, cost tracking, tests |
| **4** | Validation & Output | ✓ Complete | Quality validator, Markdown writer, cost estimator, tests |
| **5** | Streamlit UI | ✓ Complete | Web interface, file uploads, previews, error handling |
| **6** | Testing & Polish | ✓ Complete | Unit tests, integration tests, documentation (92 tests) |
| **7** | Pause/Resume & Resilience | ✓ Complete | StateManager, ResumableProcessor, auto-resume UI, 20 new tests |

---

## Success Criteria

### Phase 1-7 (Complete)
- [x] Directory structure created and organized
- [x] requirements.txt with correct versions
- [x] .env.example with placeholder for API key
- [x] .gitignore configured
- [x] Base prompt extracted to prompts/base_prompt.txt
- [x] TranscriptParser for SRT/VTT formats (Phase 2)
- [x] SmartChunker with context preservation (Phase 2)
- [x] LLMProcessor with multi-provider support (Phase 3)
- [x] Retry logic with tenacity (Phase 3)
- [x] Cost calculation per request (Phase 3)
- [x] OutputValidator with rule-based validation (Phase 4)
- [x] MarkdownWriter with metadata support (Phase 4)
- [x] CostEstimator with tiktoken integration (Phase 4)
- [x] Streamlit UI with file uploads and previews (Phase 5)
- [x] Comprehensive test suite (92 tests, Phase 6)
- [x] StateManager with atomic writes and file locking (Phase 7)
- [x] ResumableProcessor with pause/resume capability (Phase 7)
- [x] Auto-resume prompt on startup (Phase 7)
- [x] Pause/Resume tests (20 tests, Phase 7)
- [x] Total: 112 passing tests with 100% coverage

### Overall MVP + Phase 7
- [x] Process transcript files in multiple formats
- [x] Generate cleaned study materials in under 2 minutes
- [x] Maintain 100% content preservation with improved clarity
- [x] Cost tracking within 5% accuracy
- [x] Zero data loss or corruption
- [x] Pause/resume without progress loss
- [x] Automatic crash recovery and resumption
- [x] State persistence with atomic writes

---

## Configuration

### Required
- `ANTHROPIC_API_KEY`: API key from Anthropic (get from console.anthropic.com)

### Environment Setup
```bash
cp .env.example .env
# Add your API key to .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Key Constraints

1. **Token Limits**: Claude API has context window limits; chunks sized accordingly
2. **API Costs**: Processing long transcripts generates multiple API calls
3. **Quality**: Output quality depends on prompt clarity and chunk size
4. **Language**: Designed for Vietnamese learners; English output assumed

---

## References

- **Base Prompt:** `/prompts/base_prompt.txt` - Complete cleaning rules and examples
- **Plan Details:** `/plans/251224-1840-transcript-cleaner-mvp/` - Full development plan by phase
- **README:** Project overview and quick start guide

---

## Notes for Development Teams

- All phases complete. Project is production-ready MVP with resilience.
- All modules should follow patterns in `code-standards.md`
- API integration uses tenacity for robust retry handling (Phase 3 complete)
- Cost tracking integrated in cost_estimator module (Phase 4 complete)
- Pause/Resume uses state_manager + resumable_processor (Phase 7 complete)
- Test coverage: 112 passing tests, 100% for all modules
- See `pause-resume-guide.md` for user-facing documentation
- See `system-architecture.md` Phase 7 section for technical details
- See `code-standards.md` State Management section for coding patterns
