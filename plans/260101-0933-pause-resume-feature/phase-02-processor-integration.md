---
phase: 2
title: "LLMProcessor Integration with Checkpoints"
status: pending
effort: 2h
priority: P1
depends_on: [phase-01]
---

# Phase 2: LLMProcessor Integration

## Context

Integrate StateManager into LLMProcessor to save checkpoints after each chunk and support pause/resume during processing.

## Key Insights

**Checkpoint Strategy:**
- Save state after each successful chunk (file-level granularity)
- Check pause flag before processing next chunk
- Resume skips already-completed chunks
- Serialize ProcessedChunk to dict for JSON storage

**Pause Mechanism:**
- Use threading.Event for pause signaling
- Check flag between chunks (not mid-API call)
- Allow current chunk to complete before pausing

**Network Failure Recovery:**
- Existing tenacity retry handles transient failures
- Enhance to save state on persistent failure
- Enable resume from failure point

## Requirements

1. Modify `process_all_chunks` to use StateManager
2. Add pause/resume capability via threading.Event
3. Save checkpoint after each chunk completion
4. Skip completed chunks on resume
5. Serialize ProcessedChunk for state storage

## Related Code Files

| File | Modification |
|------|--------------|
| `src/llm_processor.py` | Add state integration, pause support |
| `src/state_manager.py` | Use for persistence |
| `src/__init__.py` | Export new classes |

## Implementation Steps

### Step 1: Add Serialization to ProcessedChunk

```python
# In src/llm_processor.py, add to ProcessedChunk class:

@dataclass
class ProcessedChunk:
    # ... existing fields ...

    def to_dict(self) -> dict:
        """Serialize for state storage"""
        return {
            "chunk_index": self.chunk_index,
            "original_text": self.original_text,
            "cleaned_text": self.cleaned_text,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost": self.cost,
            "model": self.model,
            "provider": self.provider
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProcessedChunk":
        return cls(**data)
```

### Step 2: Create ResumableProcessor Wrapper

```python
# src/llm_processor.py - add new class

from threading import Event
from typing import Optional, Callable
from .state_manager import StateManager, ProcessingState

class ResumableProcessor:
    """Wrapper for LLMProcessor with pause/resume support"""

    def __init__(
        self,
        processor: LLMProcessor,
        state_manager: Optional[StateManager] = None
    ):
        self.processor = processor
        self.state_manager = state_manager or StateManager()
        self._pause_event = Event()
        self._pause_event.set()  # Not paused initially
        self._stop_requested = False

    def pause(self) -> None:
        """Request pause after current chunk"""
        self._pause_event.clear()

    def resume(self) -> None:
        """Resume processing"""
        self._pause_event.set()

    def stop(self) -> None:
        """Request full stop (discard remaining)"""
        self._stop_requested = True
        self._pause_event.set()  # Unblock if paused

    @property
    def is_paused(self) -> bool:
        return not self._pause_event.is_set()

    def process_with_checkpoints(
        self,
        chunks: list,
        prompt_template: str,
        video_title: str,
        file_name: str,
        output_language: str = "English",
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        config: Optional[dict] = None
    ) -> tuple[list[ProcessedChunk], bool]:
        """
        Process chunks with checkpoint saves.

        Returns:
            (results, completed) - completed is False if paused/stopped
        """
        # Initialize or load state
        state = self._init_state(
            chunks, video_title, file_name, config or {}
        )

        results = self._restore_results(state)
        completed_set = set(state.completed_chunks)

        for chunk in chunks:
            # Check stop request
            if self._stop_requested:
                self.state_manager.set_status("paused")
                return results, False

            # Wait if paused
            if not self._pause_event.wait(timeout=0.1):
                self.state_manager.set_status("paused")
                if progress_callback:
                    progress_callback(len(results), len(chunks), "paused")
                self._pause_event.wait()  # Block until resumed

            # Skip completed chunks
            if chunk.index in completed_set:
                continue

            # Process chunk
            try:
                if progress_callback:
                    progress_callback(len(results), len(chunks), "processing")

                result = self.processor.process_chunk(
                    chunk, prompt_template, video_title, output_language
                )
                results.append(result)

                # Save checkpoint
                self.state_manager.update_chunk_complete(
                    chunk.index, result.to_dict()
                )

            except Exception as e:
                # Save error state for recovery
                self.state_manager.set_status("failed", str(e))
                raise

        # Mark complete and clear state
        self.state_manager.clear()
        return results, True

    def _init_state(
        self,
        chunks: list,
        video_title: str,
        file_name: str,
        config: dict
    ) -> ProcessingState:
        """Initialize new state or load existing"""
        existing = self.state_manager.load()

        # Resume if same file
        if existing and existing.file_name == file_name:
            existing.status = "running"
            self.state_manager.save(existing)
            return existing

        # New job
        state = ProcessingState(
            file_name=file_name,
            video_title=video_title,
            model=self.processor.model,
            provider=self.processor.provider.value,
            total_chunks=len(chunks),
            config=config,
            status="running"
        )
        self.state_manager.save(state)
        return state

    def _restore_results(self, state: ProcessingState) -> list[ProcessedChunk]:
        """Restore ProcessedChunk objects from state"""
        return [
            ProcessedChunk.from_dict(r)
            for r in state.processed_results
        ]
```

### Step 3: Update process_transcript Function

```python
# src/llm_processor.py - modify existing function

def process_transcript(
    chunks: list[Chunk],
    api_key: str,
    video_title: str,
    file_name: str = "",
    model: str = "claude-3-5-sonnet-20241022",
    prompt_path: Optional[str] = None,
    output_language: str = "English",
    progress_callback: Optional[Callable[[int, int], None]] = None,
    state_manager: Optional[StateManager] = None,
    resumable: bool = False
) -> tuple[list[ProcessedChunk], dict, bool]:
    """
    Process entire transcript with optional resume support.

    Returns:
        (processed_chunks, summary_dict, completed)
    """
    processor = LLMProcessor(api_key=api_key, model=model)
    template = processor.load_prompt_template(prompt_path)

    if resumable:
        resumable_proc = ResumableProcessor(processor, state_manager)

        # Wrap callback to match signature
        def wrapped_callback(current, total, status):
            if progress_callback and status == "processing":
                progress_callback(current, total)

        results, completed = resumable_proc.process_with_checkpoints(
            chunks, template, video_title, file_name,
            output_language, wrapped_callback
        )
    else:
        results = processor.process_all_chunks(
            chunks, template, video_title, output_language, progress_callback
        )
        completed = True

    # Calculate totals
    summary = _calculate_summary(results, model)

    return results, summary, completed


def _calculate_summary(results: list[ProcessedChunk], model: str) -> dict:
    """Calculate processing summary"""
    total_input = sum(r.input_tokens for r in results)
    total_output = sum(r.output_tokens for r in results)
    total_cost = sum(r.cost for r in results)

    return {
        "chunks_processed": len(results),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cost": round(total_cost, 4),
        "model": model
    }
```

### Step 4: Enhance Retry Logic for Network Failures

```python
# In LLMProcessor.process_chunk, update retry decorator:

@retry(
    stop=stop_after_attempt(5),  # Increase attempts
    wait=wait_exponential(multiplier=2, min=4, max=60),  # Longer backoff
    retry=retry_if_exception_type(()),  # Will be set dynamically
    before_sleep=lambda retry_state: None  # Hook for state save
)
def process_chunk(self, chunk, prompt_template, video_title, output_language):
    # ... existing implementation ...
```

## Todo List

- [ ] Add to_dict/from_dict to ProcessedChunk
- [ ] Create ResumableProcessor class
- [ ] Implement pause/resume via threading.Event
- [ ] Add checkpoint saves after each chunk
- [ ] Implement chunk skipping on resume
- [ ] Update process_transcript for resume support
- [ ] Enhance retry logic for network failures
- [ ] Update src/__init__.py exports
- [ ] Write integration tests

## Success Criteria

1. Pause stops processing after current chunk completes
2. Resume continues from next unprocessed chunk
3. Checkpoints saved after each chunk
4. Network failures don't lose processed work
5. Resumed job produces identical output to uninterrupted job

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Race condition pause/resume | threading.Event is thread-safe |
| Memory buildup on large jobs | Stream results to disk progressively |
| Stale state on config change | Include config hash in state |

## Security Considerations

- ProcessedChunk contains original transcript text
- State file should have restricted permissions
- Clear state file on job completion

## Next Steps

After Phase 2 complete:
- Phase 3: Add Streamlit UI buttons for pause/resume
- Wire up startup detection for incomplete jobs
