"""Process chunks via Claude/DeepSeek API with retry logic"""
import os
from dataclasses import dataclass
from typing import Optional, Callable
from pathlib import Path
from enum import Enum

import anthropic
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from .chunker import Chunk


class LLMProvider(Enum):
    """Available LLM providers"""
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"


@dataclass
class ProcessedChunk:
    """Result of LLM processing"""
    chunk_index: int
    original_text: str
    cleaned_text: str
    input_tokens: int
    output_tokens: int
    cost: float
    model: str
    provider: str


class ProcessingError(Exception):
    """Custom error for processing failures"""

    def __init__(self, chunk_index: int, message: str, recoverable: bool = False):
        self.chunk_index = chunk_index
        self.message = message
        self.recoverable = recoverable
        super().__init__(f"Chunk {chunk_index}: {message}")


class LLMProcessor:
    """Process transcript chunks via Claude or DeepSeek API"""

    # Provider env key mapping
    PROVIDER_ENV_KEYS = {
        LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
        LLMProvider.DEEPSEEK: "DEEPSEEK_API_KEY"
    }

    # Model to provider mapping
    MODEL_PROVIDER = {
        "claude-3-5-sonnet-20241022": LLMProvider.ANTHROPIC,
        "claude-3-5-haiku-20241022": LLMProvider.ANTHROPIC,
        "deepseek-chat": LLMProvider.DEEPSEEK,
        "deepseek-reasoner": LLMProvider.DEEPSEEK,
    }

    # Pricing per 1K tokens
    PRICING = {
        "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
        "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.005},
        "deepseek-chat": {"input": 0.00027, "output": 0.0011},
        "deepseek-reasoner": {"input": 0.00056, "output": 0.0022},
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        provider: Optional[LLMProvider] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096
    ):
        """
        Args:
            api_key: API key (or from provider-specific env var)
            model: Model identifier
            provider: LLM provider (inferred from model if not specified)
            temperature: Lower = more deterministic
            max_tokens: Max output tokens per request
        """
        # Determine provider from model if not specified
        if provider is None:
            provider = self.MODEL_PROVIDER.get(model, LLMProvider.ANTHROPIC)
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Get API key
        env_key = self.PROVIDER_ENV_KEYS[provider]
        self.api_key = api_key or os.getenv(env_key)
        if not self.api_key:
            raise ValueError(f"API key required. Set {env_key} env var.")

        # Initialize provider-specific client
        self.client = self._init_client()

    def _init_client(self):
        """Initialize provider-specific API client"""
        if self.provider == LLMProvider.ANTHROPIC:
            return anthropic.Anthropic(api_key=self.api_key)
        elif self.provider == LLMProvider.DEEPSEEK:
            from openai import OpenAI
            return OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def load_prompt_template(
        self, template_path: Optional[str] = None
    ) -> str:
        """Load prompt template from file"""
        if template_path is None:
            # Default path relative to project root
            template_path = Path(__file__).parent.parent / "prompts" / "base_prompt.txt"

        path = Path(template_path)
        if not path.exists():
            raise FileNotFoundError(f"Prompt template not found: {path}")

        with open(path, "r") as f:
            return f.read()

    def _get_retry_exceptions(self):
        """Get retryable exceptions for current provider"""
        if self.provider == LLMProvider.ANTHROPIC:
            return (anthropic.RateLimitError, anthropic.APIConnectionError,
                    anthropic.InternalServerError)
        elif self.provider == LLMProvider.DEEPSEEK:
            # OpenAI exceptions for DeepSeek
            from openai import RateLimitError, APIConnectionError, InternalServerError
            return (RateLimitError, APIConnectionError, InternalServerError)
        return ()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(())
    )
    def process_chunk(
        self,
        chunk: Chunk,
        prompt_template: str,
        video_title: str = "Untitled",
        output_language: str = "English"
    ) -> ProcessedChunk:
        """
        Process single chunk through LLM API.

        Args:
            chunk: Chunk object with text and context
            prompt_template: Template with {{fileName}}, {{chunkText}}, {{outputLanguage}} placeholders
            video_title: Title for {{fileName}} placeholder
            output_language: Output language (default: "English")

        Returns:
            ProcessedChunk with cleaned text and usage stats
        """
        # Build final prompt
        user_message = self._build_prompt(
            chunk, prompt_template, video_title, output_language
        )

        # Call provider API
        if self.provider == LLMProvider.ANTHROPIC:
            return self._call_anthropic(chunk, user_message)
        elif self.provider == LLMProvider.DEEPSEEK:
            return self._call_deepseek(chunk, user_message)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _call_anthropic(self, chunk: Chunk, user_message: str) -> ProcessedChunk:
        """Call Anthropic API"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": user_message}]
        )

        cleaned_text = response.content[0].text
        cost = self._calculate_cost(
            response.usage.input_tokens,
            response.usage.output_tokens
        )

        return ProcessedChunk(
            chunk_index=chunk.index,
            original_text=chunk.text,
            cleaned_text=cleaned_text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost=cost,
            model=self.model,
            provider=self.provider.value
        )

    def _call_deepseek(self, chunk: Chunk, user_message: str) -> ProcessedChunk:
        """Call DeepSeek API (OpenAI-compatible)"""
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": user_message}]
        )

        cleaned_text = response.choices[0].message.content
        cost = self._calculate_cost(
            response.usage.prompt_tokens,
            response.usage.completion_tokens
        )

        return ProcessedChunk(
            chunk_index=chunk.index,
            original_text=chunk.text,
            cleaned_text=cleaned_text,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            cost=cost,
            model=self.model,
            provider=self.provider.value
        )

    def process_all_chunks(
        self,
        chunks: list[Chunk],
        prompt_template: str,
        video_title: str = "Untitled",
        output_language: str = "English",
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> list[ProcessedChunk]:
        """
        Process all chunks sequentially with progress tracking.

        Args:
            chunks: List of Chunk objects
            prompt_template: Prompt template
            video_title: Video title
            output_language: Output language (default: "English")
            progress_callback: fn(current, total) called after each chunk

        Returns:
            List of ProcessedChunk objects
        """
        results = []

        for i, chunk in enumerate(chunks):
            result = self.process_chunk(chunk, prompt_template, video_title, output_language)
            results.append(result)

            if progress_callback:
                progress_callback(i + 1, len(chunks))

        return results

    def _build_prompt(
        self,
        chunk: Chunk,
        template: str,
        video_title: str,
        output_language: str = "English"
    ) -> str:
        """Build final prompt from template and chunk"""
        # Get chunk text with context
        chunk_text = chunk.full_text_for_llm

        # Replace placeholders
        prompt = template.replace("{{fileName}}", video_title)
        prompt = prompt.replace("{{chunkText}}", chunk_text)
        prompt = prompt.replace("{{outputLanguage}}", output_language)

        return prompt

    def _calculate_cost(
        self, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate cost based on token usage"""
        prices = self.PRICING.get(self.model, self.PRICING["claude-3-5-sonnet-20241022"])

        cost = (
            (input_tokens / 1000) * prices["input"] +
            (output_tokens / 1000) * prices["output"]
        )
        return round(cost, 6)


# Convenience function for single-file processing
def process_transcript(
    chunks: list[Chunk],
    api_key: str,
    video_title: str,
    model: str = "claude-3-5-sonnet-20241022",
    prompt_path: Optional[str] = None,
    output_language: str = "English",
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> tuple[list[ProcessedChunk], dict]:
    """
    Process entire transcript and return results with summary.

    Returns:
        (processed_chunks, summary_dict)
    """
    processor = LLMProcessor(api_key=api_key, model=model)
    template = processor.load_prompt_template(prompt_path)

    results = processor.process_all_chunks(
        chunks, template, video_title, output_language, progress_callback
    )

    # Calculate totals
    total_input = sum(r.input_tokens for r in results)
    total_output = sum(r.output_tokens for r in results)
    total_cost = sum(r.cost for r in results)

    summary = {
        "chunks_processed": len(results),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cost": round(total_cost, 4),
        "model": model
    }

    return results, summary
