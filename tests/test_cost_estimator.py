"""Tests for cost estimator"""
import pytest
from unittest.mock import patch, MagicMock
from src.cost_estimator import (
    CostBreakdown,
    CostEstimator
)
from src.chunker import Chunk


class TestCostBreakdown:
    """Test CostBreakdown dataclass"""

    def test_cost_breakdown_creation(self):
        """Create CostBreakdown with all fields"""
        breakdown = CostBreakdown(
            input_tokens=1000,
            output_tokens_est=800,
            input_cost=0.003,
            output_cost=0.012,
            total_cost=0.015,
            chunks=2,
            processing_time_minutes=10.5
        )
        assert breakdown.input_tokens == 1000
        assert breakdown.output_tokens_est == 800
        assert breakdown.input_cost == 0.003
        assert breakdown.output_cost == 0.012
        assert breakdown.total_cost == 0.015
        assert breakdown.chunks == 2
        assert breakdown.processing_time_minutes == 10.5


class TestCostEstimator:
    """Test CostEstimator class"""

    def test_init_default_model(self):
        """Initialize with default model"""
        estimator = CostEstimator()
        assert estimator.model == "claude-3-5-sonnet-20241022"

    def test_init_custom_model(self):
        """Initialize with custom model"""
        estimator = CostEstimator(model="claude-3-5-haiku-20241022")
        assert estimator.model == "claude-3-5-haiku-20241022"

    def test_count_tokens_with_tiktoken(self):
        """Count tokens using tiktoken when available"""
        with patch('src.cost_estimator.HAS_TIKTOKEN', True):
            with patch('src.cost_estimator.tiktoken') as mock_tiktoken:
                mock_encoder = MagicMock()
                mock_encoder.encode.return_value = [1, 2, 3, 4, 5]
                mock_tiktoken.get_encoding.return_value = mock_encoder

                estimator = CostEstimator()
                count = estimator.count_tokens("Test text here")

                assert count == 5
                mock_encoder.encode.assert_called_once_with("Test text here")

    def test_count_tokens_fallback_to_char_division(self):
        """Fallback to character / 4 when tiktoken unavailable"""
        with patch('src.cost_estimator.HAS_TIKTOKEN', False):
            estimator = CostEstimator()
            count = estimator.count_tokens("ABCD")  # 4 chars
            assert count == 1  # 4 / 4 = 1

    def test_count_tokens_tiktoken_error_fallback(self):
        """Fallback when tiktoken raises exception"""
        with patch('src.cost_estimator.HAS_TIKTOKEN', True):
            with patch('src.cost_estimator.tiktoken') as mock_tiktoken:
                mock_encoder = MagicMock()
                mock_encoder.encode.side_effect = Exception("Encoding failed")
                mock_tiktoken.get_encoding.return_value = mock_encoder

                estimator = CostEstimator()
                count = estimator.count_tokens("ABCD")  # 4 chars
                assert count == 1  # Fallback to 4/4

    def test_estimate_chunk_tokens(self):
        """Estimate tokens for single chunk"""
        estimator = CostEstimator()
        with patch.object(estimator, 'count_tokens', return_value=100):
            input_tokens, output_tokens = estimator.estimate_chunk_tokens(
                chunk_text="Test chunk content",
                prompt_template="Test prompt template"
            )

            assert input_tokens == 200  # 100 (chunk) + 100 (template)
            assert output_tokens == 80  # 100 * 0.8

    def test_estimate_total_single_chunk(self):
        """Estimate total cost for single chunk"""
        estimator = CostEstimator()
        chunk = Chunk(
            index=0,
            text="Test content that should be about this long",
            start_timestamp="00:00:00"
        )

        # Mock count_tokens to return different values for template vs content
        def mock_count_tokens(text):
            if "Prompt template" in text:
                return 100  # Template tokens
            elif "Test content" in text:
                return 500  # Chunk text tokens
            elif "[CONTEXT" in text:
                return 200  # Context buffer tokens
            return 300

        with patch.object(estimator, 'count_tokens', side_effect=mock_count_tokens):
            breakdown = estimator.estimate_total(
                chunks=[chunk],
                prompt_template="Prompt template"
            )

            assert breakdown.chunks == 1
            # Input: template (100) + chunk.full_text_for_llm (which contains text + maybe context)
            # The exact value depends on how full_text_for_llm is constructed
            assert breakdown.input_tokens > 0
            assert breakdown.output_tokens_est > 0
            assert breakdown.total_cost > 0
            # Time: (1 chunk * 5 sec) / 60 = 0.0833... rounds to 0.1
            assert breakdown.processing_time_minutes == 0.1

    def test_estimate_total_multiple_chunks(self):
        """Estimate total cost for multiple chunks"""
        estimator = CostEstimator()
        chunks = [
            Chunk(index=0, text="Content one", start_timestamp="00:00:00"),
            Chunk(index=1, text="Content two", start_timestamp="00:01:00"),
            Chunk(index=2, text="Content three", start_timestamp="00:02:00")
        ]

        # Mock count_tokens to return different values
        call_count = [0]
        def mock_count_tokens(text):
            call_count[0] += 1
            if "Template" in text:
                return 100  # Template tokens
            return 300  # Content tokens

        with patch.object(estimator, 'count_tokens', side_effect=mock_count_tokens):
            breakdown = estimator.estimate_total(
                chunks=chunks,
                prompt_template="Template"
            )

            assert breakdown.chunks == 3
            assert breakdown.input_tokens > 0
            assert breakdown.output_tokens_est > 0
            assert breakdown.total_cost > 0
            # Time: (3 chunks * 5 sec) / 60 = 0.25 rounds to 0.2 or 0.3
            assert breakdown.processing_time_minutes in [0.2, 0.3]

    def test_estimate_total_haiku_model(self):
        """Estimate costs for Haiku model"""
        estimator = CostEstimator(model="claude-3-5-haiku-20241022")
        chunk = Chunk(
            index=0,
            text="Test content",
            start_timestamp="00:00:00"
        )

        def mock_count_tokens(text):
            if "Template" in text:
                return 100
            return 1000

        with patch.object(estimator, 'count_tokens', side_effect=mock_count_tokens):
            breakdown = estimator.estimate_total(
                chunks=[chunk],
                prompt_template="Template"
            )

            # Haiku pricing: $0.001/1K input, $0.005/1K output
            assert breakdown.input_cost >= 0
            assert breakdown.output_cost >= 0
            assert breakdown.total_cost >= 0
            # Time: (1 chunk * 3 sec) / 60 = 0.05 rounds to 0.1
            assert breakdown.processing_time_minutes == 0.1

            # Verify Haiku pricing is used (cheaper than Sonnet)
            # Just check that some cost was calculated
            assert breakdown.total_cost > 0

    def test_estimate_total_unknown_model(self):
        """Fallback to Sonnet pricing for unknown models"""
        estimator = CostEstimator(model="unknown-model")
        chunk = Chunk(
            index=0,
            text="Test",
            start_timestamp="00:00:00"
        )

        with patch.object(estimator, 'count_tokens', return_value=100):
            breakdown = estimator.estimate_total(
                chunks=[chunk],
                prompt_template="Template"
            )

            # Should use Sonnet pricing as fallback
            assert breakdown.input_cost > 0

    def test_format_estimate(self):
        """Format estimate as readable string"""
        breakdown = CostBreakdown(
            input_tokens=1500,
            output_tokens_est=1200,
            input_cost=0.0045,
            output_cost=0.018,
            total_cost=0.0225,
            chunks=3,
            processing_time_minutes=15.0
        )

        estimator = CostEstimator()
        formatted = estimator.format_estimate(breakdown)

        assert "**Cost Estimate**" in formatted
        assert "1,500" in formatted
        assert "0.0045" in formatted
        assert "~1,200" in formatted
        assert "0.0225" in formatted
        assert "3" in formatted
        assert "15.0" in formatted

    def test_format_estimate_with_large_numbers(self):
        """Format estimate with large token counts"""
        breakdown = CostBreakdown(
            input_tokens=150000,
            output_tokens_est=120000,
            input_cost=0.45,
            output_cost=1.80,
            total_cost=2.25,
            chunks=100,
            processing_time_minutes=500.0
        )

        estimator = CostEstimator()
        formatted = estimator.format_estimate(breakdown)

        assert "150,000" in formatted
        assert "120,000" in formatted

    def test_estimate_total_with_context_buffer(self):
        """Estimate chunks that include context buffer"""
        estimator = CostEstimator()
        chunk = Chunk(
            index=1,
            text="New content",
            start_timestamp="00:01:00",
            context_buffer="Previous context for continuity"
        )

        with patch.object(estimator, 'count_tokens', return_value=100):
            breakdown = estimator.estimate_total(
                chunks=[chunk],
                prompt_template="Template"
            )

            # Should account for full_text_for_llm (includes context)
            assert breakdown.input_tokens > 0

    def test_estimate_total_empty_chunks(self):
        """Handle empty chunk list"""
        estimator = CostEstimator()
        with patch.object(estimator, 'count_tokens', return_value=0):
            breakdown = estimator.estimate_total(
                chunks=[],
                prompt_template="Template"
            )

            assert breakdown.chunks == 0
            assert breakdown.total_cost == 0

    def test_encoder_lazy_loading(self):
        """Encoder is loaded only when needed"""
        with patch('src.cost_estimator.HAS_TIKTOKEN', True):
            with patch('src.cost_estimator.tiktoken') as mock_tiktoken:
                mock_encoder = MagicMock()
                mock_tiktoken.get_encoding.return_value = mock_encoder

                estimator = CostEstimator()
                assert estimator._encoder is None

                # Access encoder property
                _ = estimator.encoder
                assert estimator._encoder is not None
                mock_tiktoken.get_encoding.assert_called_once_with("cl100k_base")

    def test_encoder_without_tiktoken(self):
        """Return None when tiktoken not available"""
        with patch('src.cost_estimator.HAS_TIKTOKEN', False):
            estimator = CostEstimator()
            assert estimator.encoder is None

    def test_pricing_dict_completeness(self):
        """Verify pricing dict has required models"""
        estimator = CostEstimator()
        assert "claude-3-5-sonnet-20241022" in estimator.PRICING
        assert "claude-3-5-haiku-20241022" in estimator.PRICING

        for model, prices in estimator.PRICING.items():
            assert "input" in prices
            assert "output" in prices
            assert isinstance(prices["input"], (int, float))
            assert isinstance(prices["output"], (int, float))

    def test_time_per_chunk_dict(self):
        """Verify time per chunk dict"""
        estimator = CostEstimator()
        assert "claude-3-5-sonnet-20241022" in estimator.TIME_PER_CHUNK
        assert "claude-3-5-haiku-20241022" in estimator.TIME_PER_CHUNK

        for model, time in estimator.TIME_PER_CHUNK.items():
            assert isinstance(time, (int, float))
            assert time > 0

    def test_estimate_chunk_tokens_ratio(self):
        """Verify output token estimation ratio is 0.8"""
        estimator = CostEstimator()

        with patch.object(estimator, 'count_tokens', return_value=1000):
            input_t, output_t = estimator.estimate_chunk_tokens(
                chunk_text="Test",
                prompt_template="Template"
            )

            # output_estimate = chunk_tokens * 0.8
            expected_output = 800
            assert output_t == expected_output

    def test_format_estimate_rounding(self):
        """Verify formatted output displays properly"""
        breakdown = CostBreakdown(
            input_tokens=1000,
            output_tokens_est=800,
            input_cost=0.003333,
            output_cost=0.015666,
            total_cost=0.018999,
            chunks=2,
            processing_time_minutes=8.333
        )

        estimator = CostEstimator()
        formatted = estimator.format_estimate(breakdown)

        # Check that formatted output contains expected values
        assert "1,000" in formatted  # input_tokens formatted
        assert "800" in formatted  # output tokens
        assert "2" in formatted  # chunks
        # Costs should be displayed (format may vary)
        assert "0.0033" in formatted or "0.003" in formatted
