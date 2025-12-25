"""Estimate API costs before processing"""
from dataclasses import dataclass
from typing import List

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False


@dataclass
class CostBreakdown:
    """Cost estimation breakdown"""
    input_tokens: int
    output_tokens_est: int
    input_cost: float
    output_cost: float
    total_cost: float
    chunks: int
    processing_time_minutes: float


class CostEstimator:
    """Estimate costs before processing"""

    PRICING = {
        "claude-3-5-sonnet-20241022": {
            "input": 0.003,
            "output": 0.015
        },
        "claude-3-5-haiku-20241022": {
            "input": 0.001,
            "output": 0.005
        }
    }

    TIME_PER_CHUNK = {
        "claude-3-5-sonnet-20241022": 5,
        "claude-3-5-haiku-20241022": 3
    }

    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        self.model = model
        self._encoder = None

    @property
    def encoder(self):
        """Lazy load tiktoken encoder"""
        if not HAS_TIKTOKEN:
            return None
        if self._encoder is None:
            self._encoder = tiktoken.get_encoding("cl100k_base")
        return self._encoder

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception:
                pass
        return len(text) // 4

    def estimate_chunk_tokens(
        self,
        chunk_text: str,
        prompt_template: str
    ) -> tuple[int, int]:
        """
        Estimate input and output tokens for a chunk.

        Returns:
            (input_tokens, estimated_output_tokens)
        """
        input_tokens = self.count_tokens(prompt_template) + self.count_tokens(chunk_text)
        output_estimate = int(self.count_tokens(chunk_text) * 0.8)
        return input_tokens, output_estimate

    def estimate_total(
        self,
        chunks: list,
        prompt_template: str
    ) -> CostBreakdown:
        """Estimate total cost for all chunks"""
        total_input = 0
        total_output = 0

        for chunk in chunks:
            input_t, output_t = self.estimate_chunk_tokens(
                chunk.full_text_for_llm,
                prompt_template
            )
            total_input += input_t
            total_output += output_t

        prices = self.PRICING.get(self.model, self.PRICING["claude-3-5-sonnet-20241022"])
        input_cost = (total_input / 1000) * prices["input"]
        output_cost = (total_output / 1000) * prices["output"]

        time_per_chunk = self.TIME_PER_CHUNK.get(self.model, 5)
        total_time_seconds = len(chunks) * time_per_chunk
        time_minutes = total_time_seconds / 60

        return CostBreakdown(
            input_tokens=total_input,
            output_tokens_est=total_output,
            input_cost=round(input_cost, 4),
            output_cost=round(output_cost, 4),
            total_cost=round(input_cost + output_cost, 4),
            chunks=len(chunks),
            processing_time_minutes=round(time_minutes, 1)
        )

    def format_estimate(self, breakdown: CostBreakdown) -> str:
        """Format estimate for display"""
        return f"""
**Cost Estimate**
- Input tokens: {breakdown.input_tokens:,} (${breakdown.input_cost:.4f})
- Output tokens: ~{breakdown.output_tokens_est:,} (${breakdown.output_cost:.4f})
- **Total: ${breakdown.total_cost:.4f}**

**Processing**
- Chunks: {breakdown.chunks}
- Est. time: ~{breakdown.processing_time_minutes} minutes
""".strip()
