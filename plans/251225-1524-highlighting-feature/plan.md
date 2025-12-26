# Implementation Plan: LLM-Powered Highlighting Feature

**Plan ID:** 251225-1524-highlighting-feature
**Created:** 2025-12-25
**Status:** Ready for Implementation

---

## Executive Summary

Add automatic highlighting to transcript output emphasizing key concepts and definitions. LLM identifies important points during processing, marks them with `==**text**==` syntax, post-processing converts to styled HTML for Streamlit UI display.

**Scope:**
- Modify 3 files: `prompts/base_prompt.txt`, `src/markdown_writer.py`, `app.py`
- ~30 lines of code changes total
- No breaking changes to existing functionality
- Works with both Claude and DeepSeek providers

**Effort Estimate:** 30-45 minutes implementation + testing

---

## Design References

**Based on:**
- [Brainstorming Report](../reports/brainstormer-251225-1423-highlighting-feature.md) - Solution evaluation and approach selection
- [UI/UX Design](../reports/ui-ux-design-251225-1524-highlighting-system.md) - Visual specifications and accessibility guidelines

**Key Design Decisions:**
- **Syntax:** `==**KEY CONCEPT**==` for highlighted bold text
- **Emoji:** Extremely sparingly (<1% of content) for most critical concepts only
- **Visual:** Yellow background (#FEF08A) + amber text (#713F12) + left border (#F59E0B)
- **Typography:** Font-weight 600 (semibold), line-height 1.75
- **Export:** Keep `==**markers**==` in exported Markdown files (readable, convertible)
- **Accessibility:** WCAG AA compliant (4.8:1 contrast ratio), respects `prefers-reduced-motion`

---

## Implementation Phases

### Phase 1: Prompt Engineering
**Objective:** Instruct LLM to identify and mark key concepts using `==**text**==` syntax

**Files Modified:**
- `prompts/base_prompt.txt`

**Tasks:**

#### Task 1.1: Add Highlighting Instructions Section
**Location:** After `# OUTPUT FORMAT` section in `prompts/base_prompt.txt`

**Content to Add:**
```markdown
---

# HIGHLIGHTING KEY CONCEPTS

Mark important concepts for emphasis using this syntax:

**Syntax:**
- ==**KEY CONCEPT**== for critical definitions and core principles
- **secondary term** for supporting details only

**Emoji Usage (EXTREMELY SPARINGLY):**
- Add emoji prefix ONLY for the most critical 1-2 concepts per chunk
- Example: ==**💡 Machine Learning**== for foundational definitions
- DO NOT overuse emojis - professional appearance required
- Emoji usage must be <1% of total content

**What to highlight:**
- Technical term definitions on first mention
- Fundamental principles and core concepts
- Critical statements requiring emphasis for learning

**Guidelines:**
- Highlight sparingly: 5-8% of content maximum
- Emoji for <1% of content only (most critical points)
- Prioritize educational value over aesthetic
- Avoid over-highlighting common terms
- One main concept per paragraph maximum

**Examples:**

Input: "so basically machine learning is like when computers learn from data you know and neural networks are important too"
Output: "==**💡 Machine Learning**== enables computers to learn patterns from data. ==**Neural networks**== are a fundamental architecture for deep learning."

Input: "the learning rate determines how fast the model learns basically it controls the step size"
Output: "The ==**learning rate**== determines optimization speed by controlling gradient descent step size."

**Critical Rules:**
- Do NOT highlight pronouns, articles, or common words
- Do NOT highlight the same term multiple times (first mention only)
- Do NOT use highlighting for emphasis in normal sentences
- Highlights should mark NEW information, not reinforce existing knowledge
```

**Validation:**
- [ ] Section added after OUTPUT FORMAT
- [ ] Examples are clear and demonstrate proper usage
- [ ] Guidelines specify <1% emoji usage
- [ ] Guidelines specify 5-8% total highlighting density

**Acceptance Criteria:**
- LLM outputs contain `==**text**==` markers for key concepts
- Emoji usage is minimal (1-2 per chunk maximum)
- Highlighting density is 5-8% of content
- Works with both Claude and DeepSeek models

---

### Phase 2: Python Backend - HTML Conversion
**Objective:** Convert `==**text**==` markers to styled HTML for Streamlit rendering

**Files Modified:**
- `src/markdown_writer.py`

**Tasks:**

#### Task 2.1: Add HTML Conversion Method
**Location:** Add new method to `MarkdownWriter` class in `src/markdown_writer.py`

**Implementation:**
```python
def _apply_highlights_for_streamlit(self, text: str) -> str:
    """Convert ==**highlight**== markers to HTML for Streamlit rendering

    Supports:
    - ==**text**== → primary highlight (key concept)
    - ==**💡 text**== → critical highlight with emoji

    Uses optimized colors from UI/UX design:
    - Background: #FEF08A (warm yellow, high visibility)
    - Text: #713F12 (dark amber, strong contrast)
    - Border: #F59E0B (amber accent, visual anchor)

    Returns:
        HTML string with <mark> tags for Streamlit rendering
    """
    import re

    # Pattern matches ==**content**== (with optional emoji at start)
    # Uses non-greedy matching to handle multiple highlights per line
    highlighted = re.sub(
        r'==\*\*([^*]+)\*\*==',
        r'<mark>\1</mark>',
        text
    )

    return highlighted
```

**Code Location:** Insert after `_sanitize_filename()` method, before `get_content_for_preview()`

**Validation:**
- [ ] Method properly handles `==**text**==` syntax
- [ ] Regex is non-greedy (handles multiple highlights per line)
- [ ] Method handles emoji within highlighted text
- [ ] Returns plain text if no markers found (graceful degradation)

---

#### Task 2.2: Update Preview Method
**Location:** Modify `get_content_for_preview()` method in `MarkdownWriter` class

**Current Code (lines 121-138):**
```python
def get_content_for_preview(
    self, chunks: list, max_chars: int = 5000
) -> str:
    """Get preview content (for Streamlit display)"""
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

    return "\n\n".join(content)
```

**Modified Code:**
```python
def get_content_for_preview(
    self, chunks: list, max_chars: int = 5000
) -> str:
    """Get preview content with highlights for Streamlit display"""
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
    return self._apply_highlights_for_streamlit(combined)  # NEW: Apply HTML conversion
```

**Changes:**
- Line 137: Extract combined text to variable
- Line 138: Apply highlighting conversion before returning

**Validation:**
- [ ] Preview method calls `_apply_highlights_for_streamlit()`
- [ ] Truncation still works correctly
- [ ] No performance degradation (regex is fast)

**Acceptance Criteria:**
- `_apply_highlights_for_streamlit()` method exists and works
- `get_content_for_preview()` returns HTML with `<mark>` tags
- Graceful degradation if no highlights present
- No breaking changes to existing preview functionality

---

### Phase 3: Streamlit UI - HTML Rendering & CSS
**Objective:** Enable HTML rendering and apply optimized CSS styling for highlights

**Files Modified:**
- `app.py`

**Tasks:**

#### Task 3.1: Add Custom CSS Styling
**Location:** In `main()` function, immediately after `st.set_page_config()` (after line 38)

**Implementation:**
```python
# Custom CSS for highlighting system (optimized for learning)
st.markdown("""
<style>
/* Import Google Fonts for better readability (optional - may not load in all environments) */
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600&display=swap');

/* Base typography for transcript content */
.main {
    font-family: 'Source Sans 3', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    line-height: 1.65;
    color: #1E293B;
}

/* Highlighted key concepts */
mark {
    /* Colors - from UI/UX design research */
    background-color: #FEF08A;  /* Warm yellow, better visibility than #fff3cd */
    color: #713F12;              /* Dark amber for strong contrast (4.8:1 ratio) */

    /* Spacing - crucial for readability */
    padding: 3px 6px;            /* Vertical: 3px, Horizontal: 6px */
    margin: 0 1px;               /* Prevents touching adjacent text */

    /* Visual definition */
    border-radius: 4px;          /* Soft corners, modern appearance */
    border-left: 3px solid #F59E0B; /* Amber accent - visual anchor */

    /* Typography */
    font-weight: 600;            /* Semibold for emphasis without heaviness */
    letter-spacing: 0.005em;     /* Slight tightening for bold text */
    line-height: 1.75;           /* Extra breathing room */

    /* Interaction */
    display: inline;             /* Keep inline with text flow */
    transition: background-color 150ms ease; /* Smooth, subtle */
}

/* Optional: Subtle hover feedback (non-distracting) */
mark:hover {
    background-color: #FDE047;   /* Slightly brighter yellow */
    box-shadow: 0 0 0 2px rgba(254, 240, 138, 0.3); /* Soft glow */
}

/* Accessibility: Respect reduced motion preference */
@media (prefers-reduced-motion: reduce) {
    mark {
        transition: none;        /* Disable transitions */
    }
    mark:hover {
        box-shadow: none;        /* No animation effects */
        background-color: #FEF08A; /* Keep original color */
    }
}

/* Optimal reading width for content */
.element-container {
    max-width: 65ch;             /* 60-75 characters optimal for reading */
}
</style>
""", unsafe_allow_html=True)
```

**Location Details:**
- Insert after line 38: `st.set_page_config(...)`
- Before line 41: `def main():`
- This ensures CSS loads once at app startup

**Validation:**
- [ ] CSS inserted in correct location (after page config)
- [ ] All color values match UI/UX design specifications
- [ ] `unsafe_allow_html=True` parameter present
- [ ] `prefers-reduced-motion` media query included

---

#### Task 3.2: Enable HTML Rendering in Preview Tab
**Location:** Modify Tab 1 (Preview) rendering in `app.py` around line 309

**Current Code (line 309-310):**
```python
with tab1:
    preview = writer.get_content_for_preview(results, max_chars=3000)
    st.markdown(preview)
```

**Modified Code:**
```python
with tab1:
    preview = writer.get_content_for_preview(results, max_chars=3000)
    st.markdown(preview, unsafe_allow_html=True)  # Enable HTML rendering for highlights
```

**Changes:**
- Line 310: Add `unsafe_allow_html=True` parameter

**Validation:**
- [ ] Parameter added to `st.markdown()` call
- [ ] Preview tab renders HTML correctly
- [ ] Highlights visible with proper styling

---

#### Task 3.3: Enable HTML Rendering in Full Output Tab
**Location:** Modify Tab 2 (Full Output) rendering in `app.py` around lines 313-314

**Current Code (lines 313-314):**
```python
with tab2:
    full_content = md_path.read_text()
    st.markdown(full_content)
```

**Modified Code:**
```python
with tab2:
    full_content = md_path.read_text()
    # Apply highlighting conversion to full output
    highlighted_content = writer._apply_highlights_for_streamlit(full_content)
    st.markdown(highlighted_content, unsafe_allow_html=True)  # Render with HTML
```

**Changes:**
- Line 315 (NEW): Apply highlighting conversion to full content
- Line 316: Add `unsafe_allow_html=True` parameter

**Validation:**
- [ ] Full content applies highlighting conversion
- [ ] HTML rendering enabled with `unsafe_allow_html=True`
- [ ] Full output tab displays highlights consistently with preview

**Acceptance Criteria:**
- Custom CSS loads on app startup
- Preview tab renders highlights with proper styling
- Full Output tab renders highlights consistently
- Colors match UI/UX design specifications (#FEF08A, #713F12, #F59E0B)
- Accessibility features work (reduced motion, contrast ratio)
- No breaking changes to existing Streamlit UI

---

### Phase 4: Testing & Validation
**Objective:** Ensure highlighting works correctly across all scenarios without breaking existing functionality

**Tasks:**

#### Task 4.1: Unit Testing - Regex Pattern
**Test File:** `tests/test_markdown_writer.py` (create if doesn't exist)

**Test Cases:**
```python
import pytest
from src.markdown_writer import MarkdownWriter


class TestHighlightConversion:
    """Test _apply_highlights_for_streamlit() method"""

    def test_single_highlight(self):
        """Single highlight converts correctly"""
        writer = MarkdownWriter()
        input_text = "This is ==**Machine Learning**== text."
        expected = "This is <mark>Machine Learning</mark> text."
        assert writer._apply_highlights_for_streamlit(input_text) == expected

    def test_multiple_highlights_same_line(self):
        """Multiple highlights on same line"""
        writer = MarkdownWriter()
        input_text = "==**ML**== and ==**DL**== are different."
        expected = "<mark>ML</mark> and <mark>DL</mark> are different."
        assert writer._apply_highlights_for_streamlit(input_text) == expected

    def test_emoji_in_highlight(self):
        """Highlight with emoji prefix"""
        writer = MarkdownWriter()
        input_text = "==**💡 Neural Network**== is fundamental."
        expected = "<mark>💡 Neural Network</mark> is fundamental."
        assert writer._apply_highlights_for_streamlit(input_text) == expected

    def test_no_highlights(self):
        """Text without highlights returns unchanged"""
        writer = MarkdownWriter()
        input_text = "Normal text with **bold** but no highlights."
        assert writer._apply_highlights_for_streamlit(input_text) == input_text

    def test_multiline_highlights(self):
        """Highlights across multiple lines"""
        writer = MarkdownWriter()
        input_text = "First ==**concept**==.\nSecond ==**term**==."
        expected = "First <mark>concept</mark>.\nSecond <mark>term</mark>."
        assert writer._apply_highlights_for_streamlit(input_text) == expected

    def test_nested_bold_not_matched(self):
        """Regular bold (**text**) without == not converted"""
        writer = MarkdownWriter()
        input_text = "This is **regular bold** text."
        assert writer._apply_highlights_for_streamlit(input_text) == input_text
```

**Run Tests:**
```bash
pytest tests/test_markdown_writer.py -v
```

**Validation:**
- [ ] All test cases pass
- [ ] Regex handles edge cases (emoji, multiple highlights, no highlights)
- [ ] Regular bold text not affected

---

#### Task 4.2: Integration Testing - End-to-End
**Test Scenarios:**

**Scenario 1: Claude Sonnet Processing**
1. Upload sample SRT file (technical content)
2. Select "Anthropic (Claude)" provider
3. Select "claude-3-5-sonnet-20241022" model
4. Process transcript
5. Verify:
   - [ ] Preview tab shows highlights (yellow background, bold text)
   - [ ] Full Output tab shows consistent highlights
   - [ ] Exported .md file contains `==**markers**==`
   - [ ] Highlight density ≤ 8%
   - [ ] Emoji usage ≤ 1%

**Scenario 2: DeepSeek Processing**
1. Upload same SRT file
2. Select "DeepSeek" provider
3. Select "deepseek-chat" model
4. Process transcript
5. Verify same criteria as Scenario 1

**Scenario 3: No Highlights Edge Case**
1. Process transcript with simple, non-technical content
2. Verify:
   - [ ] App doesn't crash if LLM produces no highlights
   - [ ] Content displays normally without highlights
   - [ ] No HTML rendering errors

**Scenario 4: Vietnamese Output Language**
1. Select "Vietnamese" output language
2. Process technical transcript
3. Verify:
   - [ ] Highlights appear on English technical terms
   - [ ] Vietnamese explanations not over-highlighted
   - [ ] Emoji usage remains minimal

---

#### Task 4.3: Accessibility Testing

**Contrast Ratio Verification:**
- [ ] Use browser DevTools or contrast checker
- [ ] Verify highlight text (#713F12) on highlight background (#FEF08A)
- [ ] Contrast ratio ≥ 4.5:1 (WCAG AA requirement)
- [ ] Expected: ~4.8:1 ratio

**Reduced Motion Testing:**
- [ ] Enable "Reduce motion" in OS accessibility settings
  - macOS: System Preferences → Accessibility → Display → Reduce motion
  - Windows: Settings → Ease of Access → Display → Show animations
- [ ] Verify hover transitions disabled when reduced motion active
- [ ] Highlights still visible, just no animation

**Screen Reader Testing (Optional):**
- [ ] Test with VoiceOver (macOS) or NVDA (Windows)
- [ ] Verify highlighted text announced properly
- [ ] No confusion from HTML tags

---

#### Task 4.4: Regression Testing

**Existing Functionality Verification:**
- [ ] File upload (SRT/VTT) still works
- [ ] Cost estimation accurate
- [ ] Chunking configuration works
- [ ] Validation rules still apply
- [ ] JSON metadata export unchanged
- [ ] Progress tracking displays correctly
- [ ] Error handling (API errors, invalid files) unchanged

**Performance Testing:**
- [ ] Processing time not significantly increased (<5% delta)
- [ ] Regex conversion is fast (test with 10,000-character output)
- [ ] No memory leaks from HTML rendering

**Acceptance Criteria:**
- All unit tests pass
- Both Claude and DeepSeek produce proper highlights
- Accessibility standards met (WCAG AA)
- No regressions in existing functionality
- Performance impact negligible

---

### Phase 5: Documentation & Cleanup
**Objective:** Document changes and update project documentation

**Tasks:**

#### Task 5.1: Update README.md
**Location:** `README.md`

**Section to Add:** After "## Features" section (around line 13)

**Content:**
```markdown
## Features

- Parse SRT and VTT subtitle files
- Smart chunking with context preservation
- **Multi-provider LLM support**: Anthropic Claude or DeepSeek
- **Smart highlighting**: LLM automatically highlights key concepts and definitions
- Cost estimation before processing
- Rule-based output validation
- Markdown export with metadata
```

**Optional: Add "Highlighting" subsection** (if detailed explanation needed):
```markdown
### Highlighting System

The LLM automatically identifies and highlights important concepts during processing:

- **Key concepts** highlighted with yellow background for easy scanning
- **Extremely sparing emoji usage** (💡) for most critical foundational concepts only
- **Accessible design**: WCAG AA compliant, respects reduced motion preferences
- **Export-friendly**: Highlighted text marked with `==**text**==` in exported Markdown

Highlight density: 5-8% of content for optimal learning without distraction.
```

**Validation:**
- [ ] Feature added to main feature list
- [ ] Optional subsection added if detailed explanation desired
- [ ] Markdown formatting correct

---

#### Task 5.2: Update PHASE6_DOCUMENTATION_COMPLETE.md (if exists)
**Location:** `PHASE6_DOCUMENTATION_COMPLETE.md`

**Add to changelog/features:**
```markdown
### Highlighting Feature (Added 2025-12-25)

**What:** LLM-powered automatic highlighting of key concepts in transcript output

**Implementation:**
- Prompt engineering: LLM marks important concepts with `==**text**==` syntax
- Python backend: Regex conversion to HTML `<mark>` tags
- Streamlit UI: Custom CSS styling optimized for learning

**Benefits:**
- Improves content scanning and comprehension
- Helps learners identify key concepts quickly
- Professional, accessible design (WCAG AA compliant)
- Minimal performance impact (<1% cost increase)

**Files Modified:**
- `prompts/base_prompt.txt` - LLM instructions
- `src/markdown_writer.py` - HTML conversion logic
- `app.py` - CSS styling and HTML rendering
```

---

#### Task 5.3: Code Comments & Docstrings
**Ensure all new code is well-documented:**

**In `src/markdown_writer.py`:**
- [ ] `_apply_highlights_for_streamlit()` has comprehensive docstring
- [ ] Docstring explains regex pattern and supported syntax
- [ ] Docstring documents color values and rationale

**In `app.py`:**
- [ ] CSS section has comment explaining purpose
- [ ] Color values documented with references to UI/UX design
- [ ] Accessibility features (reduced motion) commented

**In `prompts/base_prompt.txt`:**
- [ ] Highlighting section clearly structured
- [ ] Examples demonstrate correct vs incorrect usage
- [ ] Guidelines are specific and measurable (5-8%, <1%)

---

#### Task 5.4: Git Commit Message
**Commit Structure:**

```bash
git add prompts/base_prompt.txt src/markdown_writer.py app.py tests/test_markdown_writer.py README.md

git commit -m "feat: Add LLM-powered highlighting for key concepts

Implement automatic highlighting system to emphasize important points in
transcript output, improving learning comprehension and content scanning.

Changes:
- Prompt engineering: Instruct LLM to mark key concepts with ==**text**==
- Python backend: Add regex conversion to HTML <mark> tags
- Streamlit UI: Custom CSS with optimized learning-focused styling
- Testing: Unit tests for regex patterns and edge cases

Design features:
- Yellow background (#FEF08A) + amber text (#713F12) for strong contrast
- WCAG AA compliant (4.8:1 contrast ratio)
- Respects prefers-reduced-motion for accessibility
- Sparing emoji usage (<1%) for most critical concepts only
- Highlight density 5-8% to avoid over-emphasis

Cost impact: <1% increase (~$0.001 per 30-min video)
Performance: Negligible (fast regex conversion)

Based on:
- Brainstorming report: plans/reports/brainstormer-251225-1423-highlighting-feature.md
- UI/UX design: plans/reports/ui-ux-design-251225-1524-highlighting-system.md"
```

**Validation:**
- [ ] All modified files staged
- [ ] Commit message follows conventional commits format
- [ ] Message includes rationale and impact summary

**Acceptance Criteria:**
- README.md updated with highlighting feature
- All code properly documented
- Git commit created with comprehensive message
- Documentation reflects actual implementation

---

## Risk Mitigation

### Risk 1: LLM Not Following Highlighting Instructions
**Likelihood:** Low (Claude/DeepSeek are instruction-following models)
**Impact:** Medium (no highlights appear, but no breakage)

**Mitigation:**
- Include clear examples in prompt (good vs bad)
- Specify exact syntax and guidelines
- Test with both providers during Phase 4
- If needed, iterate on prompt wording (add more examples)

**Fallback:**
- If LLM produces no highlights, content displays normally
- Graceful degradation: `_apply_highlights_for_streamlit()` returns original text if no markers

---

### Risk 2: Over-Highlighting (>8% Density)
**Likelihood:** Medium (LLM may be overzealous)
**Impact:** Medium (cluttered UI, reduced effectiveness)

**Mitigation:**
- Explicit guidelines in prompt: "5-8% maximum"
- Clear examples showing restraint
- Testing phase validates density
- If over-highlighting occurs, refine prompt with stricter examples

**Corrective Action:**
- Add negative examples to prompt: "DO NOT highlight common terms"
- Increase specificity: "Only first mention of technical terms"
- Consider adding quantitative check in post-processing (count highlights, warn if >10%)

---

### Risk 3: HTML Injection Security
**Likelihood:** Very Low (content from trusted LLM APIs)
**Impact:** High (XSS vulnerability if exploited)

**Mitigation:**
- Content source: Trusted LLM providers only (Claude, DeepSeek)
- Regex limits conversion to `<mark>` tags only (no arbitrary HTML)
- No user-generated HTML input
- `unsafe_allow_html=True` only for controlled content

**Additional Protection (Optional):**
- Install `bleach` library for HTML sanitization
- Sanitize LLM output before regex conversion:
```python
import bleach

def _apply_highlights_for_streamlit(self, text: str) -> str:
    # Sanitize first (allow only <mark> tags)
    text = bleach.clean(text, tags=['mark'], strip=True)
    # Then apply regex conversion
    ...
```

**Verdict:** Low risk for this use case, but sanitization available if needed

---

### Risk 4: Breaking Changes to Existing Functionality
**Likelihood:** Low (minimal code changes)
**Impact:** High (existing features broken)

**Mitigation:**
- Comprehensive regression testing (Phase 4.4)
- Changes isolated to specific methods (no refactoring)
- Backward compatible: works even if LLM produces no highlights
- Test both providers (Claude and DeepSeek)

**Rollback Plan:**
- Git commit allows easy revert if issues found
- Each phase independent (can rollback to previous phase)

---

### Risk 5: Accessibility Issues
**Likelihood:** Low (design follows WCAG guidelines)
**Impact:** High (excludes users with disabilities)

**Mitigation:**
- Colors selected for WCAG AA compliance (4.8:1 contrast)
- `prefers-reduced-motion` support in CSS
- Semantic HTML (`<mark>` tag)
- Testing phase includes accessibility validation

**Monitoring:**
- User feedback on readability
- Browser DevTools contrast checker during testing

---

## Implementation Sequence

**Recommended Order:**

1. **Phase 1** (5 min) → Modify prompt
2. **Phase 2** (10 min) → Add Python backend logic
3. **Phase 3** (10 min) → Update Streamlit UI
4. **Phase 4.1** (10 min) → Unit tests
5. **Phase 4.2** (15 min) → Integration testing
6. **Phase 4.3** (5 min) → Accessibility testing
7. **Phase 4.4** (5 min) → Regression testing
8. **Phase 5** (10 min) → Documentation

**Total Estimated Time:** 70 minutes (including comprehensive testing)

**Fast Track (Minimal Testing):** 30 minutes
- Phases 1-3 only, manual smoke test, skip unit tests

---

## Success Metrics

### Quantitative Metrics

- [ ] **Highlight density:** 5-8% of content
- [ ] **Emoji usage:** <1% of content (1-2 per chunk max)
- [ ] **Contrast ratio:** ≥4.5:1 (WCAG AA)
- [ ] **Cost increase:** <1% (≤$0.001 per 30-min video)
- [ ] **Performance impact:** <5% processing time increase
- [ ] **Test coverage:** 100% of new code (regex method)

### Qualitative Metrics

- [ ] **Readability:** Highlights enhance comprehension, not distract
- [ ] **Professional appearance:** Clean, learning-focused design
- [ ] **Accessibility:** Works with screen readers, respects motion preferences
- [ ] **Cross-provider consistency:** Claude and DeepSeek produce similar highlight quality

### User Acceptance

- [ ] Vietnamese learners can quickly scan for key English technical terms
- [ ] Highlights feel natural, not forced or over-emphasized
- [ ] Exported Markdown remains readable with `==**markers**==` visible

---

## Rollback Plan

If critical issues found post-implementation:

**Option 1: Quick Disable (No Code Changes)**
- Comment out CSS in `app.py` (highlights become plain bold text)
- Keeps prompt changes, but highlights invisible

**Option 2: Full Rollback (Git Revert)**
```bash
git revert HEAD  # Revert commit
git push
```

**Option 3: Partial Rollback (Remove Prompt Instructions)**
- Remove highlighting section from `prompts/base_prompt.txt`
- LLM stops producing `==**markers**==`
- Backend code remains but does nothing

---

## Dependencies

**Python Libraries:**
- No new dependencies required (uses built-in `re` module)
- Optional: `bleach` for HTML sanitization (security paranoia)

**External Resources:**
- Google Fonts (optional, may not load in all Streamlit deployments)
- Fallback: System fonts work fine

**Environment:**
- Streamlit >= 1.0.0 (for `unsafe_allow_html` support)
- Python >= 3.8 (for regex and f-strings)

---

## Post-Implementation Tasks

**Immediate (After Phase 5):**
- [ ] Monitor first 10 processed transcripts for highlight quality
- [ ] Collect user feedback on readability and usefulness
- [ ] Check highlight density (if >8%, refine prompt)
- [ ] Verify cost increase is negligible (<1%)

**Short-term (1 week):**
- [ ] Analyze highlight patterns across different subjects (CS, biology, history)
- [ ] Fine-tune prompt if certain subjects over/under-highlighted
- [ ] Consider adding configuration option (toggle highlights on/off)

**Long-term (1 month):**
- [ ] Evaluate user comprehension improvement (subjective feedback)
- [ ] Consider A/B testing: with highlights vs without
- [ ] Explore secondary highlight color for supporting details (optional)

---

## Appendix: Code Snippets

### A1: Complete Prompt Section
See Phase 1, Task 1.1 for full text to add to `prompts/base_prompt.txt`

### A2: Complete Python Method
See Phase 2, Task 2.1 for `_apply_highlights_for_streamlit()` implementation

### A3: Complete CSS Styling
See Phase 3, Task 3.1 for full CSS to add to `app.py`

### A4: Test Suite
See Phase 4, Task 4.1 for complete unit tests

---

## References

- [Brainstorming Report](../reports/brainstormer-251225-1423-highlighting-feature.md)
- [UI/UX Design Specifications](../reports/ui-ux-design-251225-1524-highlighting-system.md)
- [WCAG 2.1 Contrast Guidelines](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html)
- [Streamlit HTML Rendering Docs](https://docs.streamlit.io/library/api-reference/text/st.markdown)

---

## Plan Approval

**Ready for implementation:** ✅

**Estimated effort:** 30-45 minutes (fast track) to 70 minutes (comprehensive)

**Risk level:** LOW

**Breaking changes:** NONE

**Requires review:** Optional (changes are isolated and reversible)

**Next step:** Begin Phase 1 (Prompt Engineering)
