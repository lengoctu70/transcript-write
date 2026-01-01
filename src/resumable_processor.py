"""Resumable processor with pause/resume capability"""
import threading
from typing import Optional, Callable, List, Dict, Any
from pathlib import Path

from .llm_processor import LLMProcessor, ProcessedChunk, ProcessingError
from .chunker import Chunk
from .state_manager import StateManager, ProcessingState


class PauseRequested(Exception):
    """Raised when user requests pause"""
    pass


class ResumableProcessor:
    """
    Wrapper around LLMProcessor that adds pause/resume capability.

    Features:
    - Checkpoints after each chunk
    - Pause via threading.Event
    - Resume from saved state
    - Automatic crash recovery
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        state_dir: Optional[Path] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096
    ):
        """
        Args:
            api_key: API key for LLM provider
            model: Model identifier
            state_dir: Directory for state files (default: output/.processing)
            temperature: LLM temperature
            max_tokens: Max output tokens per request
        """
        self.processor = LLMProcessor(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        self.state_manager = StateManager(state_dir)
        self.pause_event = threading.Event()
        self._is_processing = False

    def start_new_job(
        self,
        chunks: List[Chunk],
        file_name: str,
        video_title: str,
        prompt_template: str,
        output_language: str = "English",
        estimated_cost: float = 0.0
    ) -> ProcessingState:
        """
        Start a new processing job (clears any existing state).

        Args:
            chunks: List of chunks to process
            file_name: Original file name
            video_title: Video title for prompts
            prompt_template: Prompt template
            output_language: Output language
            estimated_cost: Estimated total cost

        Returns:
            New ProcessingState
        """
        # Clear any existing state
        self.state_manager.clear_state()

        # Create new state
        config = {
            "model": self.processor.model,
            "provider": self.processor.provider.value,
            "output_language": output_language,
            "temperature": self.processor.temperature,
            "max_tokens": self.processor.max_tokens
        }

        state = self.state_manager.create_new_state(
            file_name=file_name,
            video_title=video_title,
            total_chunks=len(chunks),
            config=config,
            estimated_cost=estimated_cost
        )

        state.status = "idle"
        self.state_manager.write_state(state)

        return state

    def resume_from_state(self) -> Optional[ProcessingState]:
        """
        Load and return resumable state if it exists.

        Returns:
            ProcessingState if resumable, None otherwise
        """
        state = self.state_manager.read_state()
        if state is None or not state.is_resumable():
            return None
        return state

    def process_all_chunks(
        self,
        chunks: List[Chunk],
        prompt_template: str,
        video_title: str = "Untitled",
        output_language: str = "English",
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        resume: bool = False
    ) -> tuple[List[ProcessedChunk], Dict[str, Any]]:
        """
        Process all chunks with pause/resume capability.

        Args:
            chunks: List of chunks to process
            prompt_template: Prompt template
            video_title: Video title
            output_language: Output language
            progress_callback: fn(current, total, status) called after each chunk
            resume: Whether to resume from saved state

        Returns:
            (List of ProcessedChunk, summary dict)

        Raises:
            PauseRequested: When user pauses processing
        """
        self._is_processing = True
        self.pause_event.clear()

        # Load or create state
        if resume:
            state = self.state_manager.read_state()
            if state is None or not state.is_resumable():
                # Can't resume, start fresh
                resume = False

        if not resume:
            # Start new job
            state = self.state_manager.read_state()
            if state is None:
                raise ValueError("No state found. Call start_new_job() first.")

        # Update status to processing
        state.status = "processing"
        self.state_manager.write_state(state)

        # Rebuild results from cached data
        results = []
        for result_data in state.processed_results:
            result = ProcessedChunk(
                chunk_index=result_data["chunk_index"],
                original_text=result_data["original_text"],
                cleaned_text=result_data["cleaned_text"],
                input_tokens=result_data["input_tokens"],
                output_tokens=result_data["output_tokens"],
                cost=result_data["cost"],
                model=result_data["model"],
                provider=result_data["provider"]
            )
            results.append(result)

        # Sort results by chunk index
        results.sort(key=lambda r: r.chunk_index)

        try:
            # Process remaining chunks
            for i, chunk in enumerate(chunks):
                # Check if already processed
                if chunk.index in state.completed_chunks:
                    if progress_callback:
                        progress_callback(
                            len(state.completed_chunks),
                            state.total_chunks,
                            "skipped"
                        )
                    continue

                # Check pause signal
                if self.pause_event.is_set():
                    state.status = "paused"
                    self.state_manager.write_state(state)
                    self._is_processing = False
                    raise PauseRequested("Processing paused by user")

                # Process chunk
                try:
                    if progress_callback:
                        progress_callback(
                            len(state.completed_chunks),
                            state.total_chunks,
                            "processing"
                        )

                    result = self.processor.process_chunk(
                        chunk,
                        prompt_template,
                        video_title,
                        output_language
                    )

                    # Add to results
                    results.append(result)
                    results.sort(key=lambda r: r.chunk_index)

                    # Update state
                    state.add_completed_chunk(result)
                    self.state_manager.write_state(state)

                    if progress_callback:
                        progress_callback(
                            len(state.completed_chunks),
                            state.total_chunks,
                            "completed"
                        )

                except Exception as e:
                    # Record failure
                    error_msg = str(e)
                    state.add_failed_chunk(chunk.index, error_msg)
                    self.state_manager.write_state(state)

                    # Re-raise if not recoverable
                    if not self._is_recoverable_error(e):
                        state.status = "crashed"
                        self.state_manager.write_state(state)
                        raise

            # All chunks processed successfully
            state.status = "completed"
            self.state_manager.write_state(state)

            # Build summary
            summary = {
                "chunks_processed": len(results),
                "total_input_tokens": state.total_input_tokens,
                "total_output_tokens": state.total_output_tokens,
                "total_cost": round(state.actual_cost, 4),
                "model": self.processor.model,
                "failed_chunks": len(state.failed_chunks)
            }

            self._is_processing = False
            return results, summary

        except PauseRequested:
            # Already handled above
            raise
        except Exception as e:
            # Unexpected error
            state.status = "crashed"
            self.state_manager.write_state(state)
            self._is_processing = False
            raise

    def pause(self):
        """Request pause (will complete current chunk before pausing)"""
        self.pause_event.set()

    def is_processing(self) -> bool:
        """Check if currently processing"""
        return self._is_processing

    def get_current_state(self) -> Optional[ProcessingState]:
        """Get current processing state"""
        return self.state_manager.read_state()

    def clear_state(self):
        """Clear saved state"""
        self.state_manager.clear_state()

    def _is_recoverable_error(self, error: Exception) -> bool:
        """Check if error is recoverable (network, rate limit, etc.)"""
        # Import here to avoid circular dependency issues
        try:
            import anthropic
            recoverable_anthropic = (
                anthropic.RateLimitError,
                anthropic.APIConnectionError,
                anthropic.InternalServerError
            )
        except ImportError:
            recoverable_anthropic = ()

        try:
            from openai import RateLimitError, APIConnectionError, InternalServerError
            recoverable_openai = (RateLimitError, APIConnectionError, InternalServerError)
        except ImportError:
            recoverable_openai = ()

        all_recoverable = recoverable_anthropic + recoverable_openai

        return isinstance(error, all_recoverable)


# Convenience function for simple use cases
def process_transcript_resumable(
    chunks: List[Chunk],
    api_key: str,
    video_title: str,
    model: str = "claude-3-5-sonnet-20241022",
    prompt_path: Optional[str] = None,
    output_language: str = "English",
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    resume: bool = False
) -> tuple[List[ProcessedChunk], Dict[str, Any]]:
    """
    Process entire transcript with pause/resume capability.

    Args:
        chunks: List of chunks
        api_key: API key
        video_title: Video title
        model: Model name
        prompt_path: Path to prompt template
        output_language: Output language
        progress_callback: Progress callback function
        resume: Whether to resume from saved state

    Returns:
        (processed_chunks, summary_dict)
    """
    processor = ResumableProcessor(api_key=api_key, model=model)
    template = processor.processor.load_prompt_template(prompt_path)

    results = processor.process_all_chunks(
        chunks,
        template,
        video_title,
        output_language,
        progress_callback,
        resume
    )

    return results
