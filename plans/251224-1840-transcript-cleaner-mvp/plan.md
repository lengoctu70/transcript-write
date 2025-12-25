---
title: "Transcript Cleaner MVP - Streamlit Implementation"
description: "Build Streamlit tool to convert lecture transcripts to clean study notes using Claude API"
status: completed
priority: P1
effort: 14h
branch: main
tags: [streamlit, llm, transcript-processing, mvp]
created: 2025-12-24
completed: 2025-12-25
---

# Transcript Cleaner MVP - Implementation Plan

## Overview

Build a Streamlit-based tool to convert English lecture transcripts (SRT/VTT) into clean, study-ready Markdown notes for Vietnamese learners. Uses Claude API with smart chunking strategy.

## Success Criteria

- Process 60-min transcript in <5 min
- Cost <$0.50 per video
- 90%+ filler removal accuracy
- Zero context duplication in output
- Preserves 100% technical terms

## Architecture Summary

```
┌─────────────────────────────────────────────────────┐
│                  Streamlit App                      │
│  ┌───────────────────────────────────────────────┐  │
│  │  UI Layer (app.py)                            │  │
│  │  - File upload, config, preview, download     │  │
│  └───────────────────────────────────────────────┘  │
│                      ↓                              │
│  ┌───────────────────────────────────────────────┐  │
│  │  Processing Layer                             │  │
│  │  - transcript_parser.py (SRT/VTT → text)      │  │
│  │  - chunker.py (split with context buffer)     │  │
│  │  - llm_processor.py (Claude API calls)        │  │
│  │  - validator.py (rule-based checks)           │  │
│  └───────────────────────────────────────────────┘  │
│                      ↓                              │
│  ┌───────────────────────────────────────────────┐  │
│  │  Output Layer                                 │  │
│  │  - markdown_writer.py                         │  │
│  │  - cost_estimator.py                          │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Final File Structure

```
transcript_write/
├── app.py                          # Streamlit main app
├── requirements.txt                # Dependencies
├── .env.example                    # API key template
├── .gitignore
├── README.md                       # Existing prompt spec
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
│   └── base_prompt.txt             # Main cleaning prompt
│
├── output/                         # Generated files
│
└── tests/
    ├── test_parser.py
    ├── test_chunker.py
    └── fixtures/
        └── sample.srt
```

## Phase Summary

| Phase | Focus | Effort | Status | Completed |
|-------|-------|--------|--------|-----------|
| 1 | Project Setup | 1h | DONE | 2025-12-24 22:49 |
| 2 | Parsing & Chunking | 2.5h | DONE | 2025-12-24 23:32 |
| 3 | LLM Integration | 3h | DONE | 2025-12-25 00:37 |
| 4 | Validation & Output | 2h | DONE | 2025-12-25 07:01 |
| 5 | Streamlit UI | 3h | DONE | 2025-12-25 07:17 |
| 6 | Testing & Polish | 2.5h | DONE | 2025-12-25 08:23 |

**Total: ~14 hours**

## Key Dependencies

```
streamlit>=1.29.0
anthropic>=0.8.0
python-dotenv>=1.0.0
pysrt>=1.1.2
webvtt-py>=0.4.6
tiktoken>=0.5.2
tenacity>=8.2.3
pytest>=7.4.3
```

## Cost Optimization Strategies

1. **Chunking**: 2000 char chunks with 200 char overlap
2. **Token counting**: Pre-estimate before API calls
3. **User confirmation**: Required for costs >$1
4. **Rule-based validation**: Avoid double-pass LLM validation

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Token limit exceeded | Conservative chunk size (2000 chars) + pre-validation |
| High API costs | Cost estimator + user confirmation |
| Context loss | 200-char overlap + sentence boundary splitting |
| LLM hallucination | Low temperature (0.3) + validator checks |

## Phase Details

See individual phase files:
- [Phase 1: Setup](./phase-01-setup.md)
- [Phase 2: Parsing & Chunking](./phase-02-parsing-chunking.md)
- [Phase 3: LLM Integration](./phase-03-llm-integration.md)
- [Phase 4: Validation & Output](./phase-04-validation-output.md)
- [Phase 5: Streamlit UI](./phase-05-streamlit-ui.md)
- [Phase 6: Testing & Polish](./phase-06-testing-polish.md)

---

## Unresolved Questions

1. **Prompt versioning**: How to track prompt changes? Suggest git-based version tags
2. **Quality metrics**: How to measure output quality quantitatively? Consider random sampling review
3. **Batch processing UI**: Defer to v1.1 or include in MVP? (Suggest defer)
