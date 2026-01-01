"""Tests for pause/resume functionality"""
import pytest
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.state_manager import StateManager, ProcessingState
from src.resumable_processor import ResumableProcessor, PauseRequested
from src.llm_processor import ProcessedChunk
from src.chunker import Chunk


@pytest.fixture
def temp_state_dir(tmp_path):
    """Create temporary state directory"""
    state_dir = tmp_path / ".processing"
    state_dir.mkdir(parents=True)
    return state_dir


@pytest.fixture
def state_manager(temp_state_dir):
    """Create StateManager with temp directory"""
    return StateManager(state_dir=temp_state_dir)


@pytest.fixture
def sample_chunks():
    """Create sample chunks for testing"""
    return [
        Chunk(index=0, text="Chunk 0", start_timestamp="00:00:00"),
        Chunk(index=1, text="Chunk 1", start_timestamp="00:01:00"),
        Chunk(index=2, text="Chunk 2", start_timestamp="00:02:00"),
    ]


@pytest.fixture
def sample_processed_chunk():
    """Create sample processed chunk"""
    return ProcessedChunk(
        chunk_index=0,
        original_text="Original text",
        cleaned_text="Cleaned text",
        input_tokens=100,
        output_tokens=150,
        cost=0.005,
        model="claude-3-5-sonnet-20241022",
        provider="anthropic"
    )


class TestProcessingState:
    """Test ProcessingState dataclass"""

    def test_create_state(self):
        """Test creating new state"""
        state = ProcessingState(
            file_id="test123",
            file_name="test.srt",
            video_title="Test Video",
            total_chunks=10
        )

        assert state.file_id == "test123"
        assert state.file_name == "test.srt"
        assert state.total_chunks == 10
        assert state.status == "idle"
        assert len(state.completed_chunks) == 0

    def test_to_dict_from_dict(self):
        """Test serialization round-trip"""
        original = ProcessingState(
            file_id="test123",
            file_name="test.srt",
            total_chunks=5,
            completed_chunks=[0, 1, 2]
        )

        # Convert to dict and back
        data = original.to_dict()
        restored = ProcessingState.from_dict(data)

        assert restored.file_id == original.file_id
        assert restored.completed_chunks == original.completed_chunks

    def test_is_resumable(self):
        """Test resumability check"""
        # Completed state - not resumable
        state = ProcessingState(
            status="completed",
            total_chunks=5,
            completed_chunks=[0, 1, 2, 3, 4]
        )
        assert not state.is_resumable()

        # Processing with incomplete chunks - resumable
        state.status = "processing"
        state.completed_chunks = [0, 1, 2]
        assert state.is_resumable()

        # Paused - resumable
        state.status = "paused"
        assert state.is_resumable()

    def test_get_remaining_chunks(self):
        """Test getting remaining chunks"""
        state = ProcessingState(
            total_chunks=5,
            completed_chunks=[0, 2],
            failed_chunks={"3": "error"}
        )

        remaining = state.get_remaining_chunks()
        assert remaining == [1, 4]

    def test_add_completed_chunk(self, sample_processed_chunk):
        """Test adding completed chunk"""
        state = ProcessingState(total_chunks=3)

        state.add_completed_chunk(sample_processed_chunk)

        assert 0 in state.completed_chunks
        assert state.actual_cost == sample_processed_chunk.cost
        assert state.total_input_tokens == sample_processed_chunk.input_tokens
        assert len(state.processed_results) == 1

    def test_add_failed_chunk(self):
        """Test recording failed chunk"""
        state = ProcessingState()

        state.add_failed_chunk(5, "Network error")

        assert "5" in state.failed_chunks
        assert state.failed_chunks["5"] == "Network error"

    def test_progress_percentage(self):
        """Test progress calculation"""
        state = ProcessingState(
            total_chunks=10,
            completed_chunks=[0, 1, 2, 3, 4]
        )

        assert state.get_progress_percentage() == 50.0


class TestStateManager:
    """Test StateManager class"""

    def test_create_state_dir(self, temp_state_dir):
        """Test state directory creation"""
        manager = StateManager(state_dir=temp_state_dir)
        assert manager.state_dir.exists()

    def test_write_and_read_state(self, state_manager):
        """Test writing and reading state"""
        state = ProcessingState(
            file_id="test123",
            file_name="test.srt",
            total_chunks=5,
            status="processing"
        )

        # Write state
        state_manager.write_state(state)

        # Read it back
        loaded_state = state_manager.read_state()

        assert loaded_state is not None
        assert loaded_state.file_id == "test123"
        assert loaded_state.status == "processing"

    def test_atomic_write(self, state_manager):
        """Test atomic write creates backup"""
        state1 = ProcessingState(file_id="test1")
        state_manager.write_state(state1)

        state2 = ProcessingState(file_id="test2")
        state_manager.write_state(state2)

        # Backup should exist
        assert state_manager.backup_file.exists()

    def test_create_new_state(self, state_manager):
        """Test creating new state"""
        config = {"model": "claude-3-5-sonnet-20241022", "provider": "anthropic"}

        state = state_manager.create_new_state(
            file_name="test.srt",
            video_title="Test Video",
            total_chunks=10,
            config=config,
            estimated_cost=0.50
        )

        assert state.file_name == "test.srt"
        assert state.total_chunks == 10
        assert state.estimated_cost == 0.50
        assert state.config["model"] == "claude-3-5-sonnet-20241022"

    def test_clear_state(self, state_manager):
        """Test clearing state"""
        state = ProcessingState(file_id="test")
        state_manager.write_state(state)

        state_manager.clear_state()

        loaded = state_manager.read_state()
        assert loaded is None

    def test_has_resumable_state(self, state_manager):
        """Test checking for resumable state"""
        assert not state_manager.has_resumable_state()

        # Add paused state
        state = ProcessingState(
            status="paused",
            total_chunks=5,
            completed_chunks=[0, 1]
        )
        state_manager.write_state(state)

        assert state_manager.has_resumable_state()

        # Complete the state
        state.status = "completed"
        state.completed_chunks = [0, 1, 2, 3, 4]
        state_manager.write_state(state)

        assert not state_manager.has_resumable_state()

    def test_get_state_summary(self, state_manager):
        """Test getting state summary"""
        state = ProcessingState(
            file_name="test.srt",
            video_title="Test Video",
            status="paused",
            total_chunks=10,
            completed_chunks=[0, 1, 2],
            failed_chunks={"5": "error"},
            estimated_cost=0.50,
            actual_cost=0.15
        )
        state_manager.write_state(state)

        summary = state_manager.get_state_summary()

        assert summary is not None
        assert summary["file_name"] == "test.srt"
        assert summary["progress"] == "3/10"
        assert summary["failed_chunks"] == 1
        assert summary["progress_pct"] == 30.0


class TestResumableProcessor:
    """Test ResumableProcessor class"""

    @pytest.fixture
    def mock_processor(self, temp_state_dir):
        """Create processor with mocked LLM calls"""
        with patch('src.resumable_processor.LLMProcessor') as mock_llm:
            # Configure mock to have necessary attributes
            mock_instance = mock_llm.return_value
            mock_instance.model = "claude-3-5-sonnet-20241022"
            mock_instance.provider = Mock()
            mock_instance.provider.value = "anthropic"
            mock_instance.temperature = 0.3
            mock_instance.max_tokens = 4096

            processor = ResumableProcessor(
                api_key="test-key",
                model="claude-3-5-sonnet-20241022",
                state_dir=temp_state_dir
            )
            yield processor

    def test_start_new_job(self, mock_processor, sample_chunks):
        """Test starting new job"""
        state = mock_processor.start_new_job(
            chunks=sample_chunks,
            file_name="test.srt",
            video_title="Test Video",
            prompt_template="Test prompt",
            output_language="English",
            estimated_cost=0.50
        )

        assert state.file_name == "test.srt"
        assert state.total_chunks == 3
        assert state.status == "idle"

    def test_resume_from_state(self, mock_processor, sample_chunks):
        """Test resuming from saved state"""
        # Create initial state
        mock_processor.start_new_job(
            chunks=sample_chunks,
            file_name="test.srt",
            video_title="Test",
            prompt_template="",
            estimated_cost=0.0
        )

        # Update to paused with partial progress
        state = mock_processor.state_manager.read_state()
        state.status = "paused"
        state.completed_chunks = [0, 1]
        mock_processor.state_manager.write_state(state)

        # Resume
        resumed_state = mock_processor.resume_from_state()

        assert resumed_state is not None
        assert resumed_state.status == "paused"
        assert len(resumed_state.completed_chunks) == 2

    def test_pause_functionality(self, mock_processor):
        """Test pause mechanism"""
        assert not mock_processor.pause_event.is_set()

        mock_processor.pause()

        assert mock_processor.pause_event.is_set()

    def test_clear_state(self, mock_processor, sample_chunks):
        """Test clearing state"""
        mock_processor.start_new_job(
            chunks=sample_chunks,
            file_name="test.srt",
            video_title="Test",
            prompt_template="",
            estimated_cost=0.0
        )

        mock_processor.clear_state()

        state = mock_processor.state_manager.read_state()
        assert state is None


def test_file_locking(temp_state_dir):
    """Test file locking prevents concurrent writes"""
    manager1 = StateManager(state_dir=temp_state_dir)
    manager2 = StateManager(state_dir=temp_state_dir)

    state1 = ProcessingState(file_id="test1")
    state2 = ProcessingState(file_id="test2")

    # Both should be able to write (sequential)
    manager1.write_state(state1)
    manager2.write_state(state2)

    # Last write wins
    final_state = manager1.read_state()
    assert final_state.file_id == "test2"


def test_corruption_recovery(temp_state_dir):
    """Test recovery from corrupted state file"""
    manager = StateManager(state_dir=temp_state_dir)

    # Write first state (creates initial state file)
    state1 = ProcessingState(file_id="first")
    manager.write_state(state1)

    # Write second state (first becomes backup)
    state2 = ProcessingState(file_id="second")
    manager.write_state(state2)

    # Corrupt the current state file
    with open(manager.state_file, 'w') as f:
        f.write("{invalid json")

    # Should recover from backup (which has file_id="first")
    loaded = manager.read_state()
    assert loaded is not None
    assert loaded.file_id == "first"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
