---
title: "Phase 02: CostEstimator Multi-Provider Pricing"
description: "Update CostEstimator with DeepSeek pricing and provider awareness"
status: pending
priority: P2
effort: 1h
tags: [pricing, cost-estimator, deepseek]
---

## Overview

Update `CostEstimator` to support multi-provider pricing calculations including DeepSeek's competitive pricing.

---

## Current State

**File**: `src/cost_estimator.py`

```python
PRICING = {
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.005}
}

TIME_PER_CHUNK = {
    "claude-3-5-sonnet-20241022": 5,
    "claude-3-5-haiku-20241022": 3
}
```

**Issues**:
1. Flat pricing dict (no provider grouping)
2. DeepSeek models not included
3. No provider-aware model validation

---

## DeepSeek Pricing (Dec 2024)

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Per 1K Input | Per 1K Output |
|-------|----------------------|------------------------|--------------|---------------|
| deepseek-chat | $0.27 - $0.56 | $0.40 - $0.42 | $0.00056 | $0.00042 |
| deepseek-reasoner | ~$0.56 | ~$0.42 | $0.00056 | $0.00042 |

**Source**: https://api.deepseek.com/pricing

**Comparison** (per 1K tokens):
- Claude Sonnet: $0.003 input, $0.015 output
- Claude Haiku: $0.001 input, $0.005 output
- DeepSeek Chat: $0.00056 input, $0.00042 output
- **DeepSeek is ~5-10x cheaper than Claude Haiku**

---

## Design

### Provider-Grouped Pricing Structure

```python
class CostEstimator:
    """Multi-provider cost estimation"""

    # Pricing per 1K tokens (Dec 2024)
    PRICING = {
        "anthropic": {
            "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
            "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.005}
        },
        "deepseek": {
            "deepseek-chat": {"input": 0.00056, "output": 0.00042},
            "deepseek-reasoner": {"input": 0.00056, "output": 0.00042}
        }
    }

    # Processing time per chunk (seconds)
    TIME_PER_CHUNK = {
        "anthropic": {
            "claude-3-5-sonnet-20241022": 5,
            "claude-3-5-haiku-20241022": 3
        },
        "deepseek": {
            "deepseek-chat": 4,  # Similar to Haiku
            "deepseek-reasoner": 15  # Longer reasoning time
        }
    }
```

### Provider-Aware Methods

```python
def __init__(self, provider: str = "anthropic", model: str = None):
    self.provider = provider
    self.model = model or self._get_default_model(provider)

def _get_pricing(self, model: str) -> dict:
    """Get pricing for model from provider-specific dict"""
    provider_pricing = self.PRICING.get(self.provider, {})
    return provider_pricing.get(model, {})

def _get_time_per_chunk(self, model: str) -> int:
    """Get processing time for model"""
    provider_times = self.TIME_PER_CHUNK.get(self.provider, {})
    return provider_times.get(model, 5)  # Default fallback
```

---

## Implementation Tasks

### 1. Update PRICING dict structure (15 min)

**File**: `src/cost_estimator.py`

```python
class CostEstimator:
    """Estimate costs before processing (multi-provider)"""

    # Pricing per 1K tokens (Dec 2024)
    PRICING = {
        "anthropic": {
            "claude-3-5-sonnet-20241022": {
                "input": 0.003,
                "output": 0.015,
                "currency": "USD"
            },
            "claude-3-5-haiku-20241022": {
                "input": 0.001,
                "output": 0.005,
                "currency": "USD"
            }
        },
        "deepseek": {
            "deepseek-chat": {
                "input": 0.00056,
                "output": 0.00042,
                "currency": "USD"
            },
            "deepseek-reasoner": {
                "input": 0.00056,
                "output": 0.00042,
                "currency": "USD"
            }
        }
    }

    TIME_PER_CHUNK = {
        "anthropic": {
            "claude-3-5-sonnet-20241022": 5,
            "claude-3-5-haiku-20241022": 3
        },
        "deepseek": {
            "deepseek-chat": 4,
            "deepseek-reasoner": 15  # Reasoning model slower
        }
    }

    # Default model per provider
    DEFAULT_MODELS = {
        "anthropic": "claude-3-5-sonnet-20241022",
        "deepseek": "deepseek-chat"
    }

    def __init__(
        self,
        provider: str = "anthropic",
        model: Optional[str] = None
    ):
        """
        Args:
            provider: "anthropic" or "deepseek"
            model: Model ID (or default for provider)
        """
        if provider not in self.PRICING:
            raise ValueError(f"Unsupported provider: {provider}")

        self.provider = provider
        self.model = model or self.DEFAULT_MODELS[provider]

        # Validate model exists for provider
        if self.model not in self.PRICING[provider]:
            available = list(self.PRICING[provider].keys())
            raise ValueError(
                f"Model {self.model} not found for {provider}. "
                f"Available: {available}"
            )
```

### 2. Update cost calculation methods (20 min)

**File**: `src/cost_estimator.py`

```python
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

    # Get provider-specific pricing
    prices = self._get_pricing(self.model)

    if not prices:
        # Fallback to default pricing
        prices = self.PRICING["anthropic"][self.DEFAULT_MODELS["anthropic"]]

    input_cost = (total_input / 1000) * prices["input"]
    output_cost = (total_output / 1000) * prices["output"]

    time_per_chunk = self._get_time_per_chunk(self.model)
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

def _get_pricing(self, model: str) -> dict:
    """Get pricing dict for model"""
    provider_pricing = self.PRICING.get(self.provider, {})
    return provider_pricing.get(model, {})

def _get_time_per_chunk(self, model: str) -> int:
    """Get processing time per chunk in seconds"""
    provider_times = self.TIME_PER_CHUNK.get(self.provider, {})
    return provider_times.get(model, 5)  # Default 5s
```

### 3. Update CostBreakdown dataclass (5 min)

**File**: `src/cost_estimator.py`

```python
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
    provider: str = "anthropic"  # Add provider field
    model: str = ""  # Add model field
```

### 4. Update format_estimate for provider display (10 min)

**File**: `src/cost_estimator.py`

```python
def format_estimate(self, breakdown: CostBreakdown) -> str:
    """Format estimate for display"""
    provider_name = {
        "anthropic": "Anthropic",
        "deepseek": "DeepSeek"
    }.get(breakdown.provider, breakdown.provider.title())

    return f"""
**Cost Estimate ({provider_name} · {breakdown.model})**
- Input tokens: {breakdown.input_tokens:,} (${breakdown.input_cost:.4f})
- Output tokens: ~{breakdown.output_tokens_est:,} (${breakdown.output_cost:.4f})
- **Total: ${breakdown.total_cost:.4f}**

**Processing**
- Chunks: {breakdown.chunks}
- Est. time: ~{breakdown.processing_time_minutes} minutes
""".strip()
```

### 5. Update estimate_total to populate new fields (5 min)

**File**: `src/cost_estimator.py`

```python
def estimate_total(self, chunks: list, prompt_template: str) -> CostBreakdown:
    # ... existing calculation ...

    return CostBreakdown(
        input_tokens=total_input,
        output_tokens_est=total_output,
        input_cost=round(input_cost, 4),
        output_cost=round(output_cost, 4),
        total_cost=round(input_cost + output_cost, 4),
        chunks=len(chunks),
        processing_time_minutes=round(time_minutes, 1),
        provider=self.provider,  # Add
        model=self.model  # Add
    )
```

### 6. Add utility methods for UI (5 min)

**File**: `src/cost_estimator.py`

```python
@classmethod
def get_available_providers(cls) -> list[str]:
    """Get list of supported providers"""
    return list(cls.PRICING.keys())

@classmethod
def get_models_for_provider(cls, provider: str) -> list[str]:
    """Get available models for provider"""
    return list(cls.PRICING.get(provider, {}).keys())

@classmethod
def get_default_model(cls, provider: str) -> str:
    """Get default model for provider"""
    return cls.DEFAULT_MODELS.get(provider)
```

---

## Tests

**File**: `tests/test_cost_estimator.py`

```python
class TestCostEstimatorMultiProvider:
    """Test multi-provider cost estimation"""

    def test_init_with_provider(self):
        estimator = CostEstimator(provider="deepseek")
        assert estimator.provider == "deepseek"
        assert estimator.model == "deepseek-chat"

    def test_invalid_provider_raises_error(self):
        with pytest.raises(ValueError, match="Unsupported provider"):
            CostEstimator(provider="invalid")

    def test_invalid_model_for_provider_raises_error(self):
        with pytest.raises(ValueError, match="not found for"):
            CostEstimator(provider="deepseek", model="claude-3-5-sonnet-20241022")

    def test_deepseek_pricing(self):
        estimator = CostEstimator(provider="deepseek", model="deepseek-chat")
        chunk = Chunk(index=0, text="Test content", start_timestamp="00:00:00")

        with patch.object(estimator, 'count_tokens', return_value=1000):
            breakdown = estimator.estimate_total(
                chunks=[chunk],
                prompt_template="Template"
            )

            # DeepSeek: $0.00056/1K input, $0.00042/1K output
            # Should be cheaper than Claude
            assert breakdown.total_cost > 0
            assert breakdown.provider == "deepseek"

    def test_deepseek_reasoner_longer_time(self):
        estimator = CostEstimator(provider="deepseek", model="deepseek-reasoner")
        chunk = Chunk(index=0, text="Test", start_timestamp="00:00:00")

        with patch.object(estimator, 'count_tokens', return_value=100):
            breakdown = estimator.estimate_total(
                chunks=[chunk],
                prompt_template="Template"
            )

            # Reasoner: 15s per chunk
            assert breakdown.processing_time_minutes >= 0.2  # 15s/60 = 0.25

    def test_get_available_providers(self):
        providers = CostEstimator.get_available_providers()
        assert "anthropic" in providers
        assert "deepseek" in providers

    def test_get_models_for_provider(self):
        anthropic_models = CostEstimator.get_models_for_provider("anthropic")
        assert "claude-3-5-sonnet-20241022" in anthropic_models

        deepseek_models = CostEstimator.get_models_for_provider("deepseek")
        assert "deepseek-chat" in deepseek_models
        assert "deepseek-reasoner" in deepseek_models

    def test_cost_comparison_deepseek_vs_claude(self):
        """Verify DeepSeek is significantly cheaper"""
        chunk = Chunk(index=0, text="Test content", start_timestamp="00:00:00")

        with patch.object(CostEstimator, 'count_tokens', return_value=1000):
            # Claude Sonnet
            claude_estimator = CostEstimator(provider="anthropic")
            claude_cost = claude_estimator.estimate_total(
                chunks=[chunk],
                prompt_template="Template"
            ).total_cost

            # DeepSeek Chat
            deepseek_estimator = CostEstimator(provider="deepseek")
            deepseek_cost = deepseek_estimator.estimate_total(
                chunks=[chunk],
                prompt_template="Template"
            ).total_cost

            # DeepSeek should be at least 3x cheaper
            assert deepseek_cost < claude_cost / 3

    def test_format_estimate_includes_provider(self):
        estimator = CostEstimator(provider="deepseek", model="deepseek-chat")
        chunk = Chunk(index=0, text="Test", start_timestamp="00:00:00")

        with patch.object(estimator, 'count_tokens', return_value=100):
            breakdown = estimator.estimate_total(
                chunks=[chunk],
                prompt_template="Template"
            )

        formatted = estimator.format_estimate(breakdown)
        assert "DeepSeek" in formatted
        assert "deepseek-chat" in formatted
```

---

## Backward Compatibility

**Breaking Change**: `CostEstimator.__init__()` signature changes

**Old**:
```python
estimator = CostEstimator(model="claude-3-5-sonnet-20241022")
```

**New**:
```python
estimator = CostEstimator(provider="anthropic", model="claude-3-5-sonnet-20241022")
```

**Mitigation**: Default `provider="anthropic"` maintains compatibility for single-param calls:

```python
# Still works - provider defaults to "anthropic"
estimator = CostEstimator(model="claude-3-5-sonnet-20241022")
```

---

## Files Modified

- `src/cost_estimator.py` - Multi-provider pricing structure
- `tests/test_cost_estimator.py` - New test cases

---

## Unresolved Questions

1. Should we display cost savings percentage when switching providers?
   - **Recommendation**: Nice-to-have for UI, not for estimator core

2. Currency hardcoding - future-proof for other currencies?
   - **Recommendation**: Keep USD-only for now, add currency param later if needed
