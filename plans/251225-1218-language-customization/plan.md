---
title: "Configurable Output Language for Transcript Cleaner"
description: "Add ability to customize output language (currently hardcoded to English)"
status: pending
priority: P2
effort: 3h
issue: none
branch: main
tags: [feature, frontend, prompt]
created: 2025-12-25
---

# Plan: Configurable Output Language

## Overview

Current system hardcodes output to English in `prompts/base_prompt.txt`. User wants Vietnamese output. Need configurable language selection.

## Current State

**Prompt Template:** `prompts/base_prompt.txt`
- Line 30: `Output language: English`
- Line 31: `Audience: Vietnamese learners`

**Usage Flow:**
1. `app.py:156` - Loads prompt from file
2. `app.py:194` - Passes to `process_transcript_ui()`
3. `src/llm_processor.py:272-274` - Replaces `{{fileName}}` and `{{chunkText}}`

## Design Options

### Option A: UI Language Selector (Recommended)
- Add dropdown in Streamlit sidebar
- Inject selected language into prompt via new placeholder
- Keep prompt template structure

**Pros:** User-friendly, no file edits needed
**Cons:** Requires prompt modification

### Option B: Multiple Prompt Files
- Create `prompts/base_prompt_vi.txt`, `prompts/base_prompt_en.txt`
- Select file based on language choice

**Pros:** Simple, separate prompts
**Cons:** Duplicate content, harder to maintain

### Option C: Config File
- YAML/JSON config with language setting
- Load and inject into prompt

**Pros:** Explicit configuration
**Cons:** Over-engineering for single setting

## Selected Approach: Option A (UI Selector)

**Rationale:** Most user-friendly, follows existing pattern (model selection), maintainable.

## Implementation Plan

### Phase 1: Modify Prompt Template
**File:** `prompts/base_prompt.txt`

**Changes:**
```
- Line 30: Output language: English
+ Line 30: Output language: {{outputLanguage}}

- Line 31: Audience: Vietnamese learners
+ Line 31: Audience: Vietnamese learners
```

### Phase 2: Update LLMProcessor
**File:** `src/llm_processor.py`

**Changes:**
- Add `output_language` parameter to `process_chunk()`, `process_all_chunks()`
- Update `_build_prompt()` to replace `{{outputLanguage}}` placeholder
- Default to `"English"` for backward compatibility

```python
def _build_prompt(
    self,
    chunk: Chunk,
    template: str,
    video_title: str,
    output_language: str = "English"
) -> str:
    prompt = template.replace("{{fileName}}", video_title)
    prompt = prompt.replace("{{chunkText}}", chunk.full_text_for_llm)
    prompt = prompt.replace("{{outputLanguage}}", output_language)
    return prompt
```

### Phase 3: Update Streamlit UI
**File:** `app.py`

**Changes:**
1. Add language selector in sidebar
```python
# After model selection (line 81)
output_language = st.selectbox(
    "Output Language",
    options=["English", "Vietnamese"],
    help="Language for the cleaned transcript output"
)
```

2. Pass language through processing chain
```python
# process_transcript_ui() call (line 189-195)
process_transcript_ui(
    chunks=chunks,
    api_key=api_key,
    model=model,
    video_title=video_title,
    prompt_template=prompt_template,
    output_language=output_language  # NEW
)
```

3. Update function signature and calls
```python
def process_transcript_ui(
    chunks: list,
    api_key: str,
    model: str,
    video_title: str,
    prompt_template: str,
    output_language: str = "English"  # NEW
):
    # ...
    result = process_transcript(
        chunks=chunks,
        api_key=api_key,
        video_title=video_title,
        model=model,
        output_language=output_language,  # NEW
        progress_callback=update_progress
    )
```

### Phase 4: Update Convenience Function
**File:** `src/llm_processor.py` - `process_transcript()`

```python
def process_transcript(
    chunks: list[Chunk],
    api_key: str,
    video_title: str,
    model: str = "claude-3-5-sonnet-20241022",
    prompt_path: Optional[str] = None,
    output_language: str = "English",  # NEW
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> tuple[list[ProcessedChunk], dict]:
```

## Affected Files

| File | Action | Change |
|------|--------|--------|
| `prompts/base_prompt.txt` | Modify | Add `{{outputLanguage}}` placeholder |
| `src/llm_processor.py` | Modify | Add `output_language` parameter to 3 functions |
| `app.py` | Modify | Add UI selector + pass through parameter |

## Testing Checklist

- [ ] English output works (backward compatibility)
- [ ] Vietnamese output selected correctly
- [ ] Placeholder replacement works
- [ ] Cost estimation unaffected
- [ ] No errors when switching languages

## Unresolved Questions

None. Design is straightforward.

## Notes

- Keep technical terms in original language (per existing rule)
- Vietnamese output should still preserve English technical terms
- Consider adding bilingual option in future (separate feature)
