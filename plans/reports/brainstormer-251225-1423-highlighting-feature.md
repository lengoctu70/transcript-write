# Highlighting Feature - Solution Design

## Problem Statement

Add automatic LLM-powered highlighting to emphasize important points (key concepts & definitions) in transcript output, visible in Streamlit UI preview with combined visual styling (background highlight + bold/emoji).

## Requirements

**Functional:**
- LLM automatically identifies and marks key concepts during processing
- Highlights visible in Streamlit UI (Preview & Full Output tabs)
- Key concepts & definitions prioritized
- Combined visual approach: background color + optional emoji/bold

**Non-Functional:**
- Must work with Claude and DeepSeek providers
- Minimal code changes (KISS principle)
- No breaking changes to existing pipeline
- Negligible cost increase
- Maintain existing Markdown export functionality

## Evaluated Approaches

### Approach 1: Prompt Engineering + HTML/CSS (RECOMMENDED)

**Mechanism:**
1. Modify prompt to instruct LLM to wrap concepts in `==CONCEPT==` markers
2. Post-process output: convert markers → HTML `<mark>` tags with CSS
3. Render in Streamlit with `unsafe_allow_html=True`

**Code Impact:**
- Prompt modification: Add highlighting instructions to `prompts/base_prompt.txt`
- Writer update: Add `_apply_highlights_for_streamlit()` method to `src/markdown_writer.py`
- UI update: Enable HTML rendering in `app.py` (2 lines changed)

**Pros:**
- Simple prompt modification, no complex refactoring
- LLM has full context to determine importance
- Provider-agnostic (works with any LLM)
- Clean separation: prompt = logic, post-processing = rendering
- Exported Markdown stays readable (`==text==` visible as-is)
- Easy to tune via prompt iteration

**Cons:**
- Depends on LLM instruction-following (99% reliable for Claude/DeepSeek)
- Requires `unsafe_allow_html=True` (controlled content, low security risk)
- Exported Markdown won't render highlights in basic viewers

**Cost:** +~60 tokens/chunk = +$0.001 for 30-min video (negligible)

**Risk:** LOW

---

### Approach 2: Structured JSON Output + Metadata Tagging

**Mechanism:**
LLM outputs JSON with text segments + importance tags, parse and apply styling

**Verdict:** REJECT
- Over-engineered for current needs
- Breaks validator (expects plain text)
- Violates YAGNI principle
- Higher token cost

---

### Approach 3: Post-Processing NLP Analysis

**Mechanism:**
Clean transcript → NLP library (spaCy) identifies concepts → Apply highlights

**Verdict:** REJECT
- Adds unnecessary dependency
- NLP models inferior to LLMs for understanding importance
- Violates KISS principle
- Domain-specific tuning required

---

## Recommended Solution: Enhanced Approach 1

### Implementation Plan

#### Phase 1: Prompt Modification
**File:** `prompts/base_prompt.txt`

Add after "OUTPUT FORMAT" section:

```markdown
---

# HIGHLIGHTING KEY CONCEPTS

Mark important concepts for emphasis:

**Syntax:**
- ==KEY CONCEPT== for definitions and core concepts
- **secondary term** for supporting details

**What to highlight:**
- Technical term definitions on first mention
- Fundamental principles and concepts
- Critical statements requiring emphasis

**Guidelines:**
- Highlight sparingly (5-8% of content max)
- Prioritize educational value
- Avoid over-highlighting common terms

**Example:**
Input: "so basically machine learning is like when computers learn from data you know"
Output: "==Machine Learning== enables computers to learn patterns from data."
```

#### Phase 2: Post-Processing Logic
**File:** `src/markdown_writer.py`

Add method:
```python
def _apply_highlights_for_streamlit(self, text: str) -> str:
    """Convert ==highlight== markers to HTML for Streamlit rendering"""
    highlighted = re.sub(
        r'==([^=]+)==',
        r'<mark style="background-color: #fff3cd; padding: 2px 4px; border-radius: 3px;">\1</mark>',
        text
    )
    return highlighted
```

Modify `get_content_for_preview()`:
```python
def get_content_for_preview(self, chunks: list, max_chars: int = 5000) -> str:
    """Get preview content with highlights for Streamlit"""
    content = []
    total_chars = 0

    for chunk in chunks:
        text = chunk.cleaned_text.strip()
        if total_chars + len(text) > max_chars:
            remaining = max_chars - total_chars
            if remaining > 100:
                content.append(text[:remaining] + "...")
            break
        content.append(text)
        total_chars += len(text)

    combined = "\n\n".join(content)
    return self._apply_highlights_for_streamlit(combined)  # NEW LINE
```

#### Phase 3: Streamlit UI Update
**File:** `app.py`

Modify lines 309 and 313-314:

```python
# Tab 1 - Preview
with tab1:
    preview = writer.get_content_for_preview(results, max_chars=3000)
    st.markdown(preview, unsafe_allow_html=True)  # ADD unsafe_allow_html

# Tab 2 - Full Output
with tab2:
    full_content = md_path.read_text()
    highlighted_content = writer._apply_highlights_for_streamlit(full_content)  # NEW
    st.markdown(highlighted_content, unsafe_allow_html=True)  # NEW
```

#### Phase 4 (Optional): Custom CSS Styling
**File:** `app.py` in `main()` function

Add after `st.set_page_config()`:

```python
st.markdown("""
<style>
mark {
    background-color: #fff3cd;
    padding: 2px 4px;
    border-radius: 3px;
    font-weight: 600;
}
mark::before {
    content: "💡 ";
    font-size: 0.9em;
}
</style>
""", unsafe_allow_html=True)
```

---

## Security Considerations

**Risk:** `unsafe_allow_html=True` enables HTML rendering

**Mitigation:**
- Content source: Trusted LLM APIs only (Claude/DeepSeek)
- No user-generated HTML input
- Regex limits to `<mark>` tags only (controlled conversion)
- Optional: Sanitize with `bleach` library if paranoid

**Verdict:** Safe for this use case

---

## Testing Strategy

1. Test prompt with sample transcript containing technical terms
2. Verify highlights appear in Streamlit tabs 1 & 2
3. Confirm exported Markdown remains readable (`==text==` visible)
4. Test with both Claude and DeepSeek models
5. Run existing validation suite (no breaking changes)
6. Check highlight density (should be 5-8% of content)

---

## Cost Impact Analysis

**Per 30-min video:**
- Prompt addition: ~60 tokens × 20 chunks = 1,200 tokens
- Cost increase (Claude Sonnet): 1,200 × $0.003/1K = $0.0036
- Cost increase (DeepSeek): 1,200 × $0.00027/1K = $0.0003

**Verdict:** Negligible (<1% increase)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM ignores instructions | Low | Low | Add examples in prompt, test both providers |
| Over-highlighting | Medium | Medium | Prompt specifies "5-8% max", tune iteratively |
| HTML security concerns | Low | Low | Controlled regex, trusted content source |
| Breaking validation | Very Low | High | Highlights = valid Markdown, validator agnostic |
| Export readability | Low | Low | `==text==` readable in plain text |

---

## Alternative Variations

### Option A: Emoji + Bold (No HTML)
```markdown
# In prompt:
- 🔑 **KEY CONCEPT** for definitions
- 💡 **insight** for important insights
```

**Pros:** No HTML needed, renders directly
**Cons:** Less visually distinct than background color

### Option B: Multiple Highlight Levels
```python
# Yellow for important, orange for critical
r'==([^=]+)==' → yellow background
r'===([^=]+)===' → orange background
```

**Pros:** More granular emphasis
**Cons:** Complexity increases, over-engineering risk

---

## Implementation Sequence

1. Modify `prompts/base_prompt.txt` (2 min)
2. Add `_apply_highlights_for_streamlit()` to `src/markdown_writer.py` (5 min)
3. Update `app.py` rendering (2 min)
4. Test with sample transcript (10 min)
5. Tune prompt based on results (iterative)
6. Add CSS styling (optional, 3 min)
7. Run test suite (5 min)

**Total effort:** ~30-45 min implementation + testing

---

## Success Metrics

- Highlight density: 5-8% of output content
- User comprehension improvement (subjective)
- No increase in validation errors
- Cost increase <1%
- Zero breaking changes to existing features

---

## Final Design Decisions

**User Requirements (Confirmed):**

1. **Emoji usage:** Yes, but extremely sparingly (cực kỳ tiết kiệm)
   - Only for truly critical concepts
   - Avoid overuse to maintain professional appearance

2. **Visual style:** Highlight + bold for important points
   - Yellow background + bold text for maximum visibility
   - Clean, professional appearance

3. **Highlight levels:** Single level (yellow)
   - One color for all important concepts
   - Maintains simplicity, follows KISS principle
   - No complexity from multi-level system

4. **Export format:** Keep `==markers==`
   - Exported Markdown contains `==text==` syntax
   - Readable in plain text editors
   - Can be processed/converted later if needed
   - Preserves highlighting intent

---

## Final Implementation Specification

### Prompt Instructions (Updated)

**File:** `prompts/base_prompt.txt`

```markdown
---

# HIGHLIGHTING KEY CONCEPTS

Mark important concepts for emphasis:

**Syntax:**
- ==**KEY CONCEPT**== for critical definitions and core principles
- **secondary term** for supporting details

**Emoji Usage (EXTREMELY SPARINGLY):**
- Add emoji prefix ONLY for the most critical 1-2 concepts per section
- Example: ==**💡 Machine Learning**== for foundational definitions
- DO NOT overuse emojis - professional appearance required

**What to highlight:**
- Technical term definitions on first mention
- Fundamental principles and core concepts
- Critical statements requiring emphasis

**Guidelines:**
- Highlight sparingly (5-8% of content max)
- Emoji for <1% of content only (most critical points)
- Prioritize educational value
- Avoid over-highlighting common terms

**Example:**
Input: "so basically machine learning is like when computers learn from data you know and neural networks are important too"
Output: "==**💡 Machine Learning**== enables computers to learn patterns from data. ==**Neural networks**== are a fundamental architecture for deep learning."
```

### Post-Processing Logic (Updated)

**File:** `src/markdown_writer.py`

```python
def _apply_highlights_for_streamlit(self, text: str) -> str:
    """Convert ==**highlight**== markers to HTML for Streamlit rendering

    Supports:
    - ==**text**== → highlighted bold
    - ==**💡 text**== → emoji + highlighted bold
    """
    # Pattern matches ==**content**== (with optional emoji)
    highlighted = re.sub(
        r'==\*\*([^*]+)\*\*==',
        r'<mark style="background-color: #fff3cd; padding: 2px 6px; border-radius: 3px; font-weight: 600;">\1</mark>',
        text
    )
    return highlighted
```

### CSS Styling (Simplified)

**File:** `app.py` - Add in `main()` after `st.set_page_config()`:

```python
st.markdown("""
<style>
mark {
    background-color: #fff3cd;
    padding: 2px 6px;
    border-radius: 3px;
    font-weight: 600;
    color: #333;
}
</style>
""", unsafe_allow_html=True)
```

**Note:** Removed `mark::before` CSS - emoji comes from LLM output, not CSS injection.

### Export Behavior

**Exported Markdown contains:**
```markdown
==**Machine Learning**== is a subset of AI.
==**💡 Neural networks**== are computational models.
```

**Rendering:**
- Streamlit UI: Yellow highlight + bold + emoji (if present)
- Downloaded .md: Plain text with markers visible
- Can be converted later: Search/replace `==**` → `**` to strip highlights

---

## Implementation Checklist

- [ ] Update `prompts/base_prompt.txt` with highlighting instructions
- [ ] Add `_apply_highlights_for_streamlit()` method to `src/markdown_writer.py`
- [ ] Update `get_content_for_preview()` to call highlighting method
- [ ] Modify `app.py` tab1 (Preview) to use `unsafe_allow_html=True`
- [ ] Modify `app.py` tab2 (Full Output) to apply highlights
- [ ] Add CSS styling to `app.py` main() function
- [ ] Test with sample transcript (Claude & DeepSeek)
- [ ] Verify exported Markdown contains `==**markers**==`
- [ ] Run existing test suite for regressions
- [ ] Tune prompt if highlight density > 8%

---

## Final Recommendation

Proceed with implementation using specifications above:
- **Emoji usage:** Extremely sparingly (<1% of content)
- **Visual style:** Yellow background + bold text
- **Highlight syntax:** `==**text**==` for bold highlights
- **Export format:** Keep markers in .md files
- **Total effort:** ~30-45 minutes

**Next step:** Begin implementation following checklist above.
