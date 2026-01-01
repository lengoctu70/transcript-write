---
phase: 3
title: "Streamlit UI Enhancements"
status: pending
effort: 2h
priority: P1
depends_on: [phase-02]
---

# Phase 3: Streamlit UI Enhancements

## Context

Add pause/resume buttons to Streamlit UI and implement startup detection for incomplete jobs.

## Key Insights

**Streamlit Session State:**
- Use `st.session_state` for UI state persistence across reruns
- Store ResumableProcessor instance in session
- Track processing status: idle|running|paused

**Async Pattern for Long Operations:**
- Streamlit reruns on every interaction
- Use threading for background processing
- Polling pattern updates UI during processing

**Startup Detection:**
- Check for incomplete job on app load
- Show modal/banner prompting user to resume or discard
- Provide clear job info (file name, progress)

## Requirements

1. Pause/Resume buttons during active processing
2. Progress bar shows paused state visually
3. Startup detection prompts for incomplete jobs
4. Clear error states and recovery options
5. Discard option to clear stale state

## Related Code Files

| File | Modification |
|------|--------------|
| `app.py` | Add buttons, startup detection, session state |
| `src/state_manager.py` | Used for state checks |

## Implementation Steps

### Step 1: Initialize Session State

```python
# app.py - add after imports

def init_session_state():
    """Initialize session state for pause/resume"""
    if "processing_status" not in st.session_state:
        st.session_state.processing_status = "idle"  # idle|running|paused
    if "resumable_processor" not in st.session_state:
        st.session_state.resumable_processor = None
    if "current_progress" not in st.session_state:
        st.session_state.current_progress = (0, 0)  # (current, total)
    if "processing_thread" not in st.session_state:
        st.session_state.processing_thread = None
```

### Step 2: Add Startup Detection

```python
# app.py - add function

from src.state_manager import StateManager

def check_incomplete_job():
    """Check for incomplete job on startup"""
    state_manager = StateManager()
    state = state_manager.load()

    if state and state.is_resumable:
        progress = len(state.completed_chunks)
        total = state.total_chunks

        st.warning(f"""
        **Incomplete job detected**

        - File: `{state.file_name}`
        - Progress: {progress}/{total} chunks ({progress/total*100:.0f}%)
        - Started: {state.started_at[:16].replace('T', ' ')}
        """)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Resume Processing", type="primary"):
                st.session_state.resume_job = state
                st.rerun()
        with col2:
            if st.button("Discard & Start Fresh"):
                state_manager.clear()
                st.rerun()

        return True
    return False
```

### Step 3: Create Pause/Resume Button Component

```python
# app.py - add function

def render_processing_controls():
    """Render pause/resume buttons during processing"""
    status = st.session_state.processing_status
    processor = st.session_state.resumable_processor

    if status == "idle":
        return

    current, total = st.session_state.current_progress

    # Progress bar with status
    if status == "paused":
        st.progress(current / total if total > 0 else 0)
        st.info(f"Paused at chunk {current}/{total}")
    else:
        st.progress(current / total if total > 0 else 0)
        st.text(f"Processing chunk {current}/{total}...")

    # Control buttons
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if status == "running":
            if st.button("Pause", use_container_width=True):
                if processor:
                    processor.pause()
                    st.session_state.processing_status = "paused"
                    st.rerun()
        elif status == "paused":
            if st.button("Resume", type="primary", use_container_width=True):
                if processor:
                    processor.resume()
                    st.session_state.processing_status = "running"
                    st.rerun()

    with col2:
        if st.button("Cancel", use_container_width=True):
            if processor:
                processor.stop()
            st.session_state.processing_status = "idle"
            st.rerun()
```

### Step 4: Modify Processing Function for Threading

```python
# app.py - modify process_transcript_ui

import threading
from queue import Queue

def process_transcript_ui(
    chunks: list,
    api_key: str,
    model: str,
    video_title: str,
    file_name: str,
    prompt_template: str,
    output_language: str = "English"
):
    """Process transcript with pause/resume support"""

    # Initialize processor
    from src.llm_processor import LLMProcessor, ResumableProcessor
    from src.state_manager import StateManager

    processor = LLMProcessor(api_key=api_key, model=model)
    state_manager = StateManager()
    resumable = ResumableProcessor(processor, state_manager)

    st.session_state.resumable_processor = resumable
    st.session_state.processing_status = "running"

    # Result queue for thread communication
    result_queue = Queue()

    def process_thread():
        try:
            results, completed = resumable.process_with_checkpoints(
                chunks=chunks,
                prompt_template=prompt_template,
                video_title=video_title,
                file_name=file_name,
                output_language=output_language,
                progress_callback=lambda c, t, s: update_progress(c, t, s),
                config={"model": model, "language": output_language}
            )
            result_queue.put(("success", results, completed))
        except Exception as e:
            result_queue.put(("error", str(e), None))

    def update_progress(current, total, status):
        st.session_state.current_progress = (current, total)
        if status == "paused":
            st.session_state.processing_status = "paused"

    # Start processing thread
    thread = threading.Thread(target=process_thread, daemon=True)
    thread.start()
    st.session_state.processing_thread = thread

    # Polling loop for progress updates
    progress_placeholder = st.empty()
    controls_placeholder = st.empty()

    while thread.is_alive() and result_queue.empty():
        with progress_placeholder.container():
            render_progress_bar()
        with controls_placeholder.container():
            render_processing_controls()
        time.sleep(0.5)
        st.rerun()

    # Get result
    if not result_queue.empty():
        status, data, completed = result_queue.get()
        if status == "success":
            if completed:
                handle_success(data, video_title, model)
            else:
                st.info("Processing paused. Resume anytime.")
        else:
            st.error(f"Error: {data}")

    st.session_state.processing_status = "idle"
```

### Step 5: Update Main Function

```python
# app.py - modify main()

def main():
    st.title("Transcript Cleaning Tool")
    st.markdown("Convert lecture transcripts to clean study notes")

    # Initialize session state
    init_session_state()

    # Check for incomplete job on startup
    if st.session_state.processing_status == "idle":
        if check_incomplete_job():
            return  # Show resume prompt only

    # Handle resume from previous session
    if "resume_job" in st.session_state:
        # TODO: Restore state and continue processing
        del st.session_state.resume_job

    # Rest of existing main() code...
    # ... sidebar config ...
    # ... file upload ...
    # ... process button ...
```

### Step 6: Add Visual Feedback Styles

```python
# app.py - add CSS for pause state

st.markdown("""
<style>
/* Paused state styling */
.paused-indicator {
    background-color: #FEF3C7;
    border: 1px solid #F59E0B;
    border-radius: 8px;
    padding: 1rem;
    margin: 1rem 0;
}

/* Processing animation */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.processing-status {
    animation: pulse 2s infinite;
}
</style>
""", unsafe_allow_html=True)
```

## Todo List

- [ ] Add session state initialization
- [ ] Implement startup detection for incomplete jobs
- [ ] Create pause/resume button components
- [ ] Add threading for background processing
- [ ] Implement polling pattern for UI updates
- [ ] Add visual feedback for pause state
- [ ] Handle resume from previous session
- [ ] Add cancel/discard functionality
- [ ] Test UI responsiveness
- [ ] Handle edge cases (rapid click, refresh)

## Success Criteria

1. Pause button appears during processing
2. Resume button appears when paused
3. Progress bar shows paused state
4. Startup detects incomplete jobs
5. User can resume or discard incomplete job
6. Cancel properly stops processing

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Thread safety issues | Use Queue for communication |
| UI freeze during processing | Threading + polling |
| State mismatch on refresh | Re-check state on load |
| Rapid button clicks | Debounce/disable during transition |

## Security Considerations

- No sensitive data displayed in UI
- API key masked in sidebar
- State file not exposed to frontend

## Next Steps

After Phase 3 complete:
- Phase 4: Write comprehensive tests
- Verify end-to-end resume flow
