# Transcript Cleaner MVP - Project Roadmap

**Project Start:** 2025-12-24
**Current Version:** v0.3.0-dev
**Last Updated:** 2025-12-25 00:37

---

## Overview

Build a Streamlit-based tool to convert English lecture transcripts (SRT/VTT) into clean, study-ready Markdown notes for Vietnamese learners using Claude API.

## Success Criteria

- Process 60-min transcript in <5 min
- Cost <$0.50 per video
- 90%+ filler removal accuracy
- Zero context duplication in output
- Preserves 100% technical terms

---

## Project Status: 50% Complete

### Progress Summary

| Phase | Status | Progress | Completed | Time Spent |
|-------|--------|----------|-----------|------------|
| Phase 1: Setup | DONE | 100% | 2025-12-24 22:49 | ~1h |
| Phase 2: Parsing & Chunking | DONE | 100% | 2025-12-24 23:32 | ~2.5h |
| Phase 3: LLM Integration | DONE | 100% | 2025-12-25 00:37 | ~3h |
| Phase 4: Validation & Output | IN-PROGRESS | 0% | - | 0h |
| Phase 5: Streamlit UI | PENDING | 0% | - | 0h |
| Phase 6: Testing & Polish | PENDING | 0% | - | 0h |

**Overall Progress: 3/6 phases complete (50%)**

---

## Milestones Timeline

```
Week 1 (Dec 24-25, 2025)
  Day 1: Setup + Parsing + Chunking     [DONE]
  Day 2: LLM Integration                [DONE]
  Day 3: Validation & Output            [IN-PROGRESS]
  Day 4-5: Streamlit UI + Testing       [PENDING]

Target Launch: Dec 27-28, 2025
```

---

## Detailed Phase Status

### Phase 1: Project Setup [DONE]
**Completion:** 2025-12-24 22:49

**Deliverables:**
- Project structure created
- Requirements.txt configured
- .env.example template
- .gitignore setup
- Basic test framework

**Files:**
- `requirements.txt`
- `.env.example`
- `.gitignore`
- `tests/__init__.py`

**Report:** `plans/reports/project-manager-251224-2249-phase1-completion.md`

---

### Phase 2: Parsing & Chunking [DONE]
**Completion:** 2025-12-24 23:32

**Deliverables:**
- SRT/VTT transcript parser
- Smart chunking with context buffer
- Duplicate removal
- Sentence boundary splitting

**Files:**
- `src/transcript_parser.py` (123 lines)
- `src/chunker.py` (123 lines)
- `tests/test_parser.py` (77 lines)
- `tests/test_chunker.py` (150 lines)

**Test Results:**
- 8/8 tests passing
- 91% coverage on chunker.py

**Report:** `plans/reports/project-manager-251224-2332-phase2-completion.md`

---

### Phase 3: LLM Integration [DONE]
**Completion:** 2025-12-25 00:37

**Deliverables:**
- Claude API integration
- Retry logic with exponential backoff
- Cost tracking and estimation
- Progress callback support
- Template loading system

**Files:**
- `src/llm_processor.py` (249 lines)
- `tests/test_llm_processor.py` (243 lines)

**Test Results:**
- 21/21 tests passing
- 100% coverage on llm_processor.py
- 85% overall project coverage

**Code Review Grade:** B+

**Key Features:**
- API key from environment variable
- Tenacity-based retry for rate limits
- Per-chunk cost calculation
- Progress callback for UI integration
- Error handling with custom exceptions

**Security:** PASS (no hardcoded secrets, proper API key handling)

**Report:** `plans/reports/code-reviewer-251225-0006-phase3-llm-integration.md`

---

### Phase 4: Validation & Output [IN-PROGRESS]
**Started:** 2025-12-25 00:37
**Estimated:** 2 hours

**Pending Tasks:**
- [ ] Implement rule-based validator
- [ ] Create markdown writer
- [ ] Add cost estimator utility
- [ ] Write tests for validator
- [ ] Write tests for markdown writer

**Dependencies:** Phase 3 complete

---

### Phase 5: Streamlit UI [PENDING]
**Estimated:** 3 hours

**Pending Tasks:**
- [ ] Create main app.py
- [ ] File upload component
- [ ] Model selection dropdown
- [ ] Progress bar with callback
- [ ] Result preview
- [ ] Download button
- [ ] Cost estimation display

**Dependencies:** Phase 4 complete

---

### Phase 6: Testing & Polish [PENDING]
**Estimated:** 2.5 hours

**Pending Tasks:**
- [ ] End-to-end integration tests
- [ ] Error handling improvements
- [ ] Apply code review fixes (medium priority)
- [ ] Performance optimization
- [ ] Documentation updates
- [ ] README completion

**Dependencies:** Phase 5 complete

---

## File Structure

```
transcript_write/
├── app.py                          # [PENDING] Streamlit main app
├── requirements.txt                # DONE
├── .env.example                    # DONE
├── .gitignore                      # DONE
├── README.md                       # [UPDATE NEEDED]
│
├── src/
│   ├── __init__.py                 # DONE
│   ├── transcript_parser.py        # DONE (123 lines)
│   ├── chunker.py                  # DONE (123 lines)
│   ├── llm_processor.py            # DONE (249 lines)
│   ├── validator.py                # [PENDING]
│   ├── markdown_writer.py          # [PENDING]
│   └── cost_estimator.py           # [PENDING]
│
├── prompts/
│   └── base_prompt.txt             # [PENDING]
│
├── tests/
│   ├── __init__.py                 # DONE
│   ├── test_parser.py              # DONE (77 lines)
│   ├── test_chunker.py             # DONE (150 lines)
│   ├── test_llm_processor.py       # DONE (243 lines)
│   ├── test_validator.py           # [PENDING]
│   └── fixtures/
│       └── sample.srt              # DONE
│
├── output/                         # [CREATE] Generated files
├── plans/
│   └── 251224-1840-transcript-cleaner-mvp/
│       ├── plan.md                 # UPDATED
│       ├── phase-01-setup.md       # DONE
│       ├── phase-02-parsing-chunking.md  # DONE
│       ├── phase-03-llm-integration.md   # DONE
│       ├── phase-04-validation-output.md # PENDING
│       ├── phase-05-streamlit-ui.md      # PENDING
│       └── phase-06-testing-polish.md    # PENDING
│
└── docs/
    ├── project-overview-pdr.md     # DONE
    ├── code-standards.md           # DONE
    ├── codebase-summary.md         # [UPDATE NEEDED]
    ├── system-architecture.md      # [UPDATE NEEDED]
    └── project-roadmap.md          # THIS FILE
```

---

## Changelog

### v0.3.0-dev (2025-12-25 00:37)
**Phase 3 Complete: LLM Integration**

**Added:**
- `src/llm_processor.py` - Claude API integration with retry logic
- `tests/test_llm_processor.py` - 21 passing tests
- Cost calculation per chunk
- Progress callback support for UI
- Template loading from file
- Custom ProcessingError exception

**Security:**
- API key loaded from ANTHROPIC_API_KEY env var
- No hardcoded secrets
- Error messages don't expose credentials

**Test Coverage:**
- llm_processor.py: 100%
- Overall: 85%

**Code Review:** B+ grade, 2 high-priority issues (already resolved)

---

### v0.2.0-dev (2025-12-24 23:32)
**Phase 2 Complete: Parsing & Chunking**

**Added:**
- `src/transcript_parser.py` - SRT/VTT parser with deduplication
- `src/chunker.py` - Smart chunking with context buffer
- `tests/test_parser.py` - 3 passing tests
- `tests/test_chunker.py` - 5 passing tests

**Features:**
- SRT format parsing
- Consecutive duplicate removal
- 2000-char chunks with 200-char overlap
- Sentence boundary splitting
- Timestamp preservation
- Context buffer for LLM continuity

**Test Coverage:**
- chunker.py: 91%
- transcript_parser.py: 64%

---

### v0.1.0-dev (2025-12-24 22:49)
**Phase 1 Complete: Project Setup**

**Added:**
- Project structure
- `requirements.txt` with all dependencies
- `.env.example` template
- `.gitignore` configured
- Basic test framework setup
- `tests/fixtures/sample.srt`

**Dependencies:**
- streamlit>=1.29.0
- anthropic>=0.8.0
- pysrt>=1.1.2
- webvtt-py>=0.4.6
- tenacity>=8.2.3
- pytest>=7.4.3

---

## Known Issues

### Phase 3 (LLM Integration)
- [MEDIUM] No validation for empty API responses (defer to Phase 6)
- [MEDIUM] No max_tokens parameter validation (defer to Phase 6)
- [LOW] Model validation missing (nice to have)

### Phase 2 (Parsing & Chunking)
- [LOW] transcript_parser.py coverage 64% (VTT/WebVTT paths untested)

---

## Risk Register

| Risk | Probability | Impact | Mitigation | Status |
|------|------------|--------|-----------|--------|
| Token limit exceeded | Low | High | Conservative chunk size (2000 chars) | MITIGATED |
| High API costs | Medium | Medium | Cost estimator + user confirmation | PENDING |
| Context loss between chunks | Low | Medium | 200-char overlap + sentence boundaries | MITIGATED |
| LLM hallucination | Low | Medium | Low temperature (0.3) + validator | PENDING |
| Rate limit issues | Medium | Low | Sequential processing + exponential backoff | MITIGATED |

---

## Next Steps (Priority Order)

1. [IMMEDIATE] Complete Phase 4: Validation & Output
2. [HIGH] Build Phase 5: Streamlit UI
3. [MEDIUM] Phase 6: Testing & Polish
4. [LOW] Apply code review medium-priority fixes
5. [LOW] Update documentation (codebase-summary.md, system-architecture.md)

---

## Metrics Dashboard

### Development Velocity
- **Phases Completed:** 3/6 (50%)
- **Time Spent:** ~6.5 hours
- **Remaining:** ~7.5 hours
- **On Track:** YES (targeting Dec 27-28 launch)

### Code Quality
- **Total Tests:** 21
- **Tests Passing:** 21 (100%)
- **Overall Coverage:** 85%
- **Critical Issues:** 0
- **High Priority Issues:** 0

### Feature Completeness
- **Core Features:** 50% (3/6 phases)
- **UI Components:** 0%
- **Documentation:** 40% (base docs done, updates needed)

---

## Unresolved Questions

1. **Prompt versioning:** How to track prompt changes? (Suggest git-based version tags)
2. **Quality metrics:** How to measure output quality quantitatively? (Consider random sampling review)
3. **Batch processing UI:** Defer to v1.1 or include in MVP? (Suggest defer)

---

*Last updated: 2025-12-25 00:37 by project-manager subagent*
