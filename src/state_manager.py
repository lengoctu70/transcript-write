"""State management for pause/resume functionality"""
import json
import os
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from filelock import FileLock

from .llm_processor import ProcessedChunk


@dataclass
class ProcessingState:
    """Represents the current state of transcript processing"""
    version: str = "1.0"
    file_id: str = ""
    file_name: str = ""
    video_title: str = ""
    status: str = "idle"  # idle, processing, paused, completed, crashed
    started_at: str = ""
    last_updated: str = ""

    # Processing configuration
    config: Dict[str, Any] = field(default_factory=dict)

    # Progress tracking
    total_chunks: int = 0
    completed_chunks: List[int] = field(default_factory=list)
    failed_chunks: Dict[str, str] = field(default_factory=dict)  # {chunk_idx: error_msg}

    # Results cache
    processed_results: List[Dict[str, Any]] = field(default_factory=list)

    # Cost tracking
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ProcessingState':
        """Create from dictionary"""
        return cls(**data)

    def update_timestamp(self):
        """Update last_updated timestamp"""
        self.last_updated = datetime.now(timezone.utc).isoformat()

    def is_resumable(self) -> bool:
        """Check if this state can be resumed"""
        return (
            self.status in ["processing", "paused"] and
            len(self.completed_chunks) < self.total_chunks
        )

    def get_remaining_chunks(self) -> List[int]:
        """Get list of chunk indices that still need processing"""
        all_chunks = set(range(self.total_chunks))
        completed = set(self.completed_chunks)
        failed = set(int(idx) for idx in self.failed_chunks.keys())
        return sorted(list(all_chunks - completed - failed))

    def add_completed_chunk(self, chunk_result: ProcessedChunk):
        """Add a successfully processed chunk"""
        if chunk_result.chunk_index not in self.completed_chunks:
            self.completed_chunks.append(chunk_result.chunk_index)
            self.completed_chunks.sort()

        # Update totals
        self.actual_cost += chunk_result.cost
        self.total_input_tokens += chunk_result.input_tokens
        self.total_output_tokens += chunk_result.output_tokens

        # Cache the result
        result_dict = {
            "chunk_index": chunk_result.chunk_index,
            "original_text": chunk_result.original_text,
            "cleaned_text": chunk_result.cleaned_text,
            "input_tokens": chunk_result.input_tokens,
            "output_tokens": chunk_result.output_tokens,
            "cost": chunk_result.cost,
            "model": chunk_result.model,
            "provider": chunk_result.provider
        }

        # Update or append result
        existing_idx = None
        for i, r in enumerate(self.processed_results):
            if r["chunk_index"] == chunk_result.chunk_index:
                existing_idx = i
                break

        if existing_idx is not None:
            self.processed_results[existing_idx] = result_dict
        else:
            self.processed_results.append(result_dict)

        self.update_timestamp()

    def add_failed_chunk(self, chunk_index: int, error_msg: str):
        """Record a failed chunk"""
        self.failed_chunks[str(chunk_index)] = error_msg
        self.update_timestamp()

    def get_progress_percentage(self) -> float:
        """Get completion percentage"""
        if self.total_chunks == 0:
            return 0.0
        return (len(self.completed_chunks) / self.total_chunks) * 100


class StateManager:
    """Manages processing state persistence with atomic writes and file locking"""

    def __init__(self, state_dir: Path = None):
        """
        Args:
            state_dir: Directory to store state files (default: output/.processing)
        """
        if state_dir is None:
            state_dir = Path(__file__).parent.parent / "output" / ".processing"

        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.state_dir / "processing_state.json"
        self.lock_file = self.state_dir / ".processing_state.lock"
        self.backup_file = self.state_dir / "processing_state.backup.json"

    @contextmanager
    def _atomic_write(self, filepath: Path):
        """Context manager for atomic file writes"""
        temp_path = filepath.parent / f".{filepath.name}.tmp"
        try:
            with open(temp_path, 'w') as f:
                yield f
            # Atomic rename
            os.replace(temp_path, filepath)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    def _generate_file_id(self, file_name: str, file_size: int = 0) -> str:
        """Generate unique file ID from name and size"""
        content = f"{file_name}:{file_size}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def read_state(self) -> Optional[ProcessingState]:
        """Read current processing state (thread-safe)"""
        with FileLock(self.lock_file, timeout=10):
            if not self.state_file.exists():
                return None

            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                return ProcessingState.from_dict(data)
            except (json.JSONDecodeError, Exception) as e:
                # Try backup file
                if self.backup_file.exists():
                    try:
                        with open(self.backup_file, 'r') as f:
                            data = json.load(f)
                        return ProcessingState.from_dict(data)
                    except Exception:
                        pass
                return None

    def write_state(self, state: ProcessingState) -> None:
        """Write processing state with atomic guarantee (thread-safe)"""
        state.update_timestamp()

        with FileLock(self.lock_file, timeout=10):
            # Backup existing state before overwriting
            if self.state_file.exists():
                try:
                    self.state_file.rename(self.backup_file)
                except Exception:
                    pass

            # Write new state atomically
            with self._atomic_write(self.state_file) as f:
                json.dump(state.to_dict(), f, indent=2)

    def create_new_state(
        self,
        file_name: str,
        video_title: str,
        total_chunks: int,
        config: dict,
        estimated_cost: float = 0.0
    ) -> ProcessingState:
        """Create a new processing state"""
        file_id = self._generate_file_id(file_name)

        state = ProcessingState(
            file_id=file_id,
            file_name=file_name,
            video_title=video_title,
            status="idle",
            started_at=datetime.now(timezone.utc).isoformat(),
            last_updated=datetime.now(timezone.utc).isoformat(),
            config=config,
            total_chunks=total_chunks,
            estimated_cost=estimated_cost
        )

        return state

    def clear_state(self) -> None:
        """Clear current state (delete state file)"""
        with FileLock(self.lock_file, timeout=10):
            self.state_file.unlink(missing_ok=True)
            self.backup_file.unlink(missing_ok=True)

    def has_resumable_state(self) -> bool:
        """Check if there's a resumable state"""
        state = self.read_state()
        return state is not None and state.is_resumable()

    def get_state_summary(self) -> Optional[Dict[str, Any]]:
        """Get summary of current state for display"""
        state = self.read_state()
        if state is None:
            return None

        return {
            "video_title": state.video_title,
            "file_name": state.file_name,
            "status": state.status,
            "progress": f"{len(state.completed_chunks)}/{state.total_chunks}",
            "progress_pct": state.get_progress_percentage(),
            "failed_chunks": len(state.failed_chunks),
            "estimated_cost": state.estimated_cost,
            "actual_cost": state.actual_cost,
            "started_at": state.started_at,
            "last_updated": state.last_updated,
            "config": state.config
        }
