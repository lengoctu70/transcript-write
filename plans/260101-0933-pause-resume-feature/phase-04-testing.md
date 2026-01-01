---
phase: 4
title: "Testing and Validation"
status: pending
effort: 0.5h
priority: P2
depends_on: [phase-03]
---

# Phase 4: Testing and Validation

## Context

Validate pause/resume functionality through unit tests, integration tests, and manual testing scenarios.

## Key Insights

**Testing Strategy:**
- Unit tests for StateManager (isolated file operations)
- Unit tests for ResumableProcessor (mock LLM calls)
- Integration tests for full resume flow
- Manual testing for Streamlit UI

**Mock Strategy:**
- Mock LLM API calls to avoid costs
- Simulate network failures
- Test file corruption recovery

## Requirements

1. Unit tests for state_manager.py
2. Unit tests for ResumableProcessor
3. Integration tests for resume flow
4. Manual test checklist for UI

## Related Code Files

| File | Tests |
|------|-------|
| `tests/test_state_manager.py` | New: StateManager tests |
| `tests/test_resumable_processor.py` | New: Processor tests |
| `tests/test_integration.py` | Modify: Add resume tests |

## Implementation Steps

### Step 1: StateManager Unit Tests

```python
# tests/test_state_manager.py

import pytest
import json
from pathlib import Path
from src.state_manager import StateManager, ProcessingState

@pytest.fixture
def temp_state_file(tmp_path):
    """Create temp state file for testing"""
    return tmp_path / ".processing_state.json"

@pytest.fixture
def state_manager(temp_state_file):
    return StateManager(state_path=temp_state_file)

class TestProcessingState:
    def test_to_dict_roundtrip(self):
        state = ProcessingState(
            file_name="test.srt",
            video_title="Test Video",
            total_chunks=10
        )
        data = state.to_dict()
        restored = ProcessingState.from_dict(data)
        assert restored.file_name == state.file_name
        assert restored.total_chunks == state.total_chunks

    def test_is_resumable(self):
        state = ProcessingState(
            status="running",
            total_chunks=10,
            completed_chunks=[0, 1, 2]
        )
        assert state.is_resumable is True

        state.status = "completed"
        assert state.is_resumable is False

    def test_next_chunk_index(self):
        state = ProcessingState(completed_chunks=[0, 1, 2])
        assert state.next_chunk_index == 3

        state = ProcessingState(completed_chunks=[])
        assert state.next_chunk_index == 0

class TestStateManager:
    def test_save_and_load(self, state_manager, temp_state_file):
        state = ProcessingState(file_name="test.srt", total_chunks=5)
        state_manager.save(state)

        assert temp_state_file.exists()

        loaded = state_manager.load()
        assert loaded.file_name == "test.srt"
        assert loaded.total_chunks == 5

    def test_atomic_write(self, state_manager, temp_state_file):
        """Verify atomic write creates backup"""
        state1 = ProcessingState(file_name="first.srt")
        state_manager.save(state1)

        state2 = ProcessingState(file_name="second.srt")
        state_manager.save(state2)

        backup = temp_state_file.with_suffix(".bak")
        assert backup.exists()
        backup_data = json.loads(backup.read_text())
        assert backup_data["file_name"] == "first.srt"

    def test_clear(self, state_manager, temp_state_file):
        state = ProcessingState(file_name="test.srt")
        state_manager.save(state)
        state_manager.clear()

        assert not temp_state_file.exists()

    def test_load_nonexistent(self, state_manager):
        result = state_manager.load()
        assert result is None

    def test_corruption_recovery(self, state_manager, temp_state_file):
        """Recover from backup when main file corrupted"""
        state = ProcessingState(file_name="good.srt")
        state_manager.save(state)

        # Corrupt main file
        temp_state_file.write_text("invalid json{{{")

        # Save backup manually
        backup = temp_state_file.with_suffix(".bak")
        backup.write_text(json.dumps(state.to_dict()))

        loaded = state_manager.load()
        assert loaded.file_name == "good.srt"

    def test_update_chunk_complete(self, state_manager):
        state = ProcessingState(file_name="test.srt", total_chunks=5)
        state_manager.save(state)

        result = {"chunk_index": 0, "cleaned_text": "test"}
        state_manager.update_chunk_complete(0, result)

        loaded = state_manager.load()
        assert 0 in loaded.completed_chunks
        assert len(loaded.processed_results) == 1

    def test_has_incomplete_job(self, state_manager):
        assert state_manager.has_incomplete_job() is False

        state = ProcessingState(
            status="running",
            total_chunks=10,
            completed_chunks=[0, 1]
        )
        state_manager.save(state)
        assert state_manager.has_incomplete_job() is True
```

### Step 2: ResumableProcessor Unit Tests

```python
# tests/test_resumable_processor.py

import pytest
from unittest.mock import Mock, patch
from threading import Thread
import time

from src.llm_processor import ResumableProcessor, LLMProcessor, ProcessedChunk
from src.state_manager import StateManager, ProcessingState
from src.chunker import Chunk

@pytest.fixture
def mock_processor():
    processor = Mock(spec=LLMProcessor)
    processor.model = "test-model"
    processor.provider = Mock()
    processor.provider.value = "test"
    return processor

@pytest.fixture
def mock_state_manager(tmp_path):
    return StateManager(state_path=tmp_path / ".state.json")

@pytest.fixture
def sample_chunks():
    return [
        Chunk(index=0, text="First chunk", start_timestamp="00:00:00"),
        Chunk(index=1, text="Second chunk", start_timestamp="00:01:00"),
        Chunk(index=2, text="Third chunk", start_timestamp="00:02:00"),
    ]

class TestResumableProcessor:
    def test_pause_and_resume(self, mock_processor, mock_state_manager, sample_chunks):
        mock_processor.process_chunk.return_value = ProcessedChunk(
            chunk_index=0, original_text="", cleaned_text="clean",
            input_tokens=10, output_tokens=20, cost=0.001,
            model="test", provider="test"
        )

        resumable = ResumableProcessor(mock_processor, mock_state_manager)

        # Start processing in thread
        results = []
        def process():
            nonlocal results
            r, _ = resumable.process_with_checkpoints(
                sample_chunks, "template", "title", "file.srt"
            )
            results = r

        thread = Thread(target=process)
        thread.start()

        # Pause after short delay
        time.sleep(0.1)
        resumable.pause()
        assert resumable.is_paused is True

        # Resume
        time.sleep(0.1)
        resumable.resume()

        thread.join(timeout=5)

    def test_skip_completed_chunks(self, mock_processor, mock_state_manager, sample_chunks):
        # Pre-populate state with completed chunk
        state = ProcessingState(
            file_name="file.srt",
            total_chunks=3,
            completed_chunks=[0],
            processed_results=[{
                "chunk_index": 0, "original_text": "", "cleaned_text": "done",
                "input_tokens": 10, "output_tokens": 20, "cost": 0.001,
                "model": "test", "provider": "test"
            }]
        )
        mock_state_manager.save(state)

        mock_processor.process_chunk.return_value = ProcessedChunk(
            chunk_index=1, original_text="", cleaned_text="clean",
            input_tokens=10, output_tokens=20, cost=0.001,
            model="test", provider="test"
        )

        resumable = ResumableProcessor(mock_processor, mock_state_manager)
        results, completed = resumable.process_with_checkpoints(
            sample_chunks, "template", "title", "file.srt"
        )

        # Should only process chunks 1 and 2
        assert mock_processor.process_chunk.call_count == 2

    def test_checkpoint_saves(self, mock_processor, mock_state_manager, sample_chunks):
        call_count = 0

        def mock_process(*args, **kwargs):
            nonlocal call_count
            result = ProcessedChunk(
                chunk_index=call_count, original_text="", cleaned_text=f"clean{call_count}",
                input_tokens=10, output_tokens=20, cost=0.001,
                model="test", provider="test"
            )
            call_count += 1
            return result

        mock_processor.process_chunk.side_effect = mock_process

        resumable = ResumableProcessor(mock_processor, mock_state_manager)
        results, completed = resumable.process_with_checkpoints(
            sample_chunks[:2], "template", "title", "file.srt"
        )

        # State should be cleared on completion
        assert mock_state_manager.load() is None
        assert completed is True
```

### Step 3: Manual Testing Checklist

```markdown
## Manual Testing Checklist

### Pause/Resume Flow
- [ ] Click Pause during processing - processing stops after current chunk
- [ ] Click Resume - processing continues from next chunk
- [ ] Progress bar shows correct state when paused
- [ ] Cancel stops processing and clears state

### Startup Detection
- [ ] Close app during processing
- [ ] Reopen app - prompt appears with file name and progress
- [ ] Click Resume - continues from where it left off
- [ ] Click Discard - clears state and allows fresh start

### Network Failure Recovery
- [ ] Disconnect internet during processing
- [ ] Retry kicks in with exponential backoff
- [ ] After retries exhausted, state is saved
- [ ] Reconnect and resume continues from failure point

### Edge Cases
- [ ] Pause immediately after starting - handles gracefully
- [ ] Resume after long pause (minutes) - works correctly
- [ ] Multiple rapid pause/resume clicks - no crashes
- [ ] Refresh browser during processing - can resume

### State File Integrity
- [ ] Delete .processing_state.json - app handles missing file
- [ ] Corrupt .processing_state.json - app recovers from backup
- [ ] State file updates after each chunk (verify with cat command)
```

## Todo List

- [ ] Create tests/test_state_manager.py
- [ ] Create tests/test_resumable_processor.py
- [ ] Run unit tests and fix failures
- [ ] Perform manual testing with checklist
- [ ] Test edge cases (refresh, network, corruption)
- [ ] Document any found issues
- [ ] Update tests for full coverage

## Success Criteria

1. All unit tests pass
2. Manual checklist items verified
3. Edge cases handled gracefully
4. No data loss during interruption
5. Resume produces same output as uninterrupted

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Flaky async tests | Use proper synchronization |
| Missing edge cases | Comprehensive manual testing |
| Mocking not realistic | Integration tests with real flow |

## Security Considerations

- Tests don't use real API keys
- Temp files cleaned up after tests
- No sensitive data in test fixtures

## Next Steps

After Phase 4 complete:
- Feature ready for PR
- Document in README
- Consider future enhancements (batch file support)
