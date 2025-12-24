# Project Overview & Product Development Requirements

## Project: Transcript Cleaner MVP

**Version:** 0.3.0
**Phase:** 3 - LLM Integration Complete
**Last Updated:** 2025-12-25

---

## Executive Summary

Transcript Cleaner is an automated tool that transforms raw lecture transcripts into structured, study-ready materials for Vietnamese learners of English. The tool cleans, rewrites, and organizes spoken content into professional study notes while preserving 100% of original meaning.

**Status:** Phase 3 Complete - LLM integration with retry logic, cost calculation, and 100% test coverage.

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
| **LLM Provider** | Anthropic Claude API | 0.75.0+ |
| **Core Language** | Python | 3.9+ |
| **Subtitle Parsing** | pysrt, webvtt-py | Latest |
| **Token Management** | tiktoken | >=0.5.2 |
| **Retry Logic** | tenacity | >=8.2.3 |
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

### Non-Functional Requirements

#### NFR1: Performance
- Process transcripts within reasonable time (max 2 min for standard lecture)
- Handle transcripts up to 2 hours long
- Efficient chunk management and API calls

#### NFR2: Reliability
- Graceful error handling for malformed inputs
- Retry logic for API failures
- Validation of cleaned output

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
| **4** | Validation & Output | Pending | Quality validator, Markdown writer |
| **5** | Streamlit UI | Pending | Web interface, file uploads, previews |
| **6** | Testing & Polish | Pending | Unit tests, integration tests, documentation |

---

## Success Criteria

### Phase 1-3 (Complete)
- [x] Directory structure created and organized
- [x] requirements.txt with correct versions
- [x] .env.example with placeholder for API key
- [x] .gitignore configured
- [x] Base prompt extracted to prompts/base_prompt.txt
- [x] TranscriptParser for SRT/VTT formats (Phase 2)
- [x] SmartChunker with context preservation (Phase 2)
- [x] LLMProcessor with Claude API integration (Phase 3)
- [x] Retry logic with tenacity (Phase 3)
- [x] Cost calculation per request (Phase 3)
- [x] Comprehensive test suite (30 tests, Phase 3)

### Overall MVP
- Process transcript files in multiple formats
- Generate cleaned study materials in under 2 minutes
- Maintain 100% content preservation with improved clarity
- Cost tracking within 5% accuracy
- Zero data loss or corruption

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

- Phase 4 begins with implementing the Validator module
- All modules should follow patterns in `code-standards.md`
- API integration uses tenacity for robust retry handling (Phase 3 complete)
- Cost tracking integrated in llm_processor module (Phase 3 complete)
- Test coverage: 30 passing tests, 100% for llm_processor
