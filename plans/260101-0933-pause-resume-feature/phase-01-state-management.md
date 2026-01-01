---
phase: 1
title: "Core State Management Infrastructure"
status: pending
effort: 1.5h
priority: P1
---

# Phase 1: Core State Management Infrastructure

## Context

Create foundational state management for tracking processing progress at file-level granularity.

## Key Insights

**State Design Principles:**
- Immutable dataclass for ProcessingState (thread-safe)
- Atomic file writes (write temp, then rename)
- File locking prevents concurrent corruption
- Schema versioning enables future migrations

**File-Level Granularity:**
- Track completed chunk indices per file
- Store chunk results for processed items
- Enable resume from any interruption point

## Requirements

1. ProcessingState dataclass storing job metadata + progress
2. StateManager class for load/save with atomic writes
3. File locking for concurrent access safety
4. Corruption recovery (backup before write)

## Architecture Decision

**State File Location:** `.processing_state.json` in project root
- Hidden file (dot prefix) keeps directory clean
- Single file simplifies management
- JSON format for human readability/debugging

**State Schema v1:**
```python
@dataclass
class ProcessingState:
    version: str = "1.0"
    job_id: str                      # UUID for job
    status: str                      # pending|running|paused|completed|failed
    file_name: str                   # Original transcript filename
    video_title: str
    model: str
    provider: str
    total_chunks: int
    completed_chunks: list[int]      # Indices of processed chunks
    processed_results: list[dict]    # Serialized ProcessedChunk data
    started_at: str                  # ISO timestamp
    updated_at: str
    error_message: Optional[str]
    config: dict                     # chunk_size, overlap, language
```

## Related Code Files

| File | Role |
|------|------|
| `src/state_manager.py` | New: StateManager + ProcessingState |
| `src/llm_processor.py` | Reference: ProcessedChunk structure |

## Implementation Steps

### Step 1: Create ProcessingState Dataclass

```python
# src/state_manager.py
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime
import uuid

@dataclass
class ProcessingState:
    """Immutable state for processing job"""
    version: str = "1.0"
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"  # pending|running|paused|completed|failed
    file_name: str = ""
    video_title: str = ""
    model: str = ""
    provider: str = ""
    total_chunks: int = 0
    completed_chunks: list[int] = field(default_factory=list)
    processed_results: list[dict] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    error_message: Optional[str] = None
    config: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ProcessingState":
        return cls(**data)

    @property
    def is_resumable(self) -> bool:
        return self.status in ("running", "paused") and len(self.completed_chunks) < self.total_chunks

    @property
    def next_chunk_index(self) -> int:
        if not self.completed_chunks:
            return 0
        return max(self.completed_chunks) + 1
```

### Step 2: Create StateManager Class

```python
import json
from pathlib import Path
from filelock import FileLock

class StateManager:
    """Manage processing state with atomic file operations"""

    DEFAULT_PATH = Path(".processing_state.json")
    LOCK_TIMEOUT = 10  # seconds

    def __init__(self, state_path: Optional[Path] = None):
        self.state_path = state_path or self.DEFAULT_PATH
        self.lock_path = self.state_path.with_suffix(".lock")
        self._lock = FileLock(self.lock_path, timeout=self.LOCK_TIMEOUT)

    def load(self) -> Optional[ProcessingState]:
        """Load state from file, return None if not exists"""
        if not self.state_path.exists():
            return None
        with self._lock:
            try:
                data = json.loads(self.state_path.read_text())
                return ProcessingState.from_dict(data)
            except (json.JSONDecodeError, KeyError) as e:
                # Corrupted file - try backup
                return self._load_backup()

    def save(self, state: ProcessingState) -> None:
        """Atomic save: write temp file, then rename"""
        state.updated_at = datetime.now().isoformat()
        temp_path = self.state_path.with_suffix(".tmp")

        with self._lock:
            # Backup existing state
            if self.state_path.exists():
                backup_path = self.state_path.with_suffix(".bak")
                backup_path.write_text(self.state_path.read_text())

            # Write to temp, then atomic rename
            temp_path.write_text(json.dumps(state.to_dict(), indent=2))
            temp_path.rename(self.state_path)

    def clear(self) -> None:
        """Remove state file (job completed)"""
        with self._lock:
            if self.state_path.exists():
                self.state_path.unlink()
            # Clean up backup too
            backup = self.state_path.with_suffix(".bak")
            if backup.exists():
                backup.unlink()

    def _load_backup(self) -> Optional[ProcessingState]:
        """Attempt recovery from backup file"""
        backup = self.state_path.with_suffix(".bak")
        if backup.exists():
            try:
                data = json.loads(backup.read_text())
                return ProcessingState.from_dict(data)
            except:
                pass
        return None

    def has_incomplete_job(self) -> bool:
        """Check if there's a resumable job"""
        state = self.load()
        return state is not None and state.is_resumable
```

### Step 3: Add Helper Methods for Chunk Updates

```python
# Add to StateManager class
def update_chunk_complete(self, chunk_index: int, result: dict) -> None:
    """Mark chunk as completed and save result"""
    state = self.load()
    if state:
        if chunk_index not in state.completed_chunks:
            state.completed_chunks.append(chunk_index)
        state.processed_results.append(result)
        state.status = "running"
        self.save(state)

def set_status(self, status: str, error: Optional[str] = None) -> None:
    """Update job status"""
    state = self.load()
    if state:
        state.status = status
        state.error_message = error
        self.save(state)
```

## Todo List

- [ ] Create `src/state_manager.py` file
- [ ] Implement ProcessingState dataclass
- [ ] Implement StateManager with atomic writes
- [ ] Add file locking with filelock
- [ ] Implement backup/recovery logic
- [ ] Add helper methods for chunk updates
- [ ] Add `filelock` to requirements.txt
- [ ] Write unit tests for state_manager

## Success Criteria

1. State persists to JSON file correctly
2. Atomic writes prevent corruption on crash
3. File locking prevents race conditions
4. Backup recovery works when primary file corrupted
5. State correctly tracks chunk-level progress

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| File corruption on crash | Atomic write (temp + rename) |
| Concurrent access | FileLock with timeout |
| Schema changes | Version field for migrations |
| Disk full | Catch IOError, notify user |

## Security Considerations

- State file may contain API usage info (costs) - acceptable
- No API keys stored in state
- File permissions: user-readable only (0600)

## Next Steps

After Phase 1 complete:
- Phase 2: Integrate StateManager into LLMProcessor
- Add checkpoint saves after each chunk
