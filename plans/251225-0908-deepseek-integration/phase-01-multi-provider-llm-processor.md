---
title: "Phase 01: Multi-Provider LLMProcessor Refactor"
description: "Refactor LLMProcessor to support multiple LLM providers (Anthropic, DeepSeek)"
status: pending
priority: P2
effort: 2.5h
tags: [llm, refactor, deepseek]
---

## Overview

Refactor `LLMProcessor` from Anthropic-only to multi-provider architecture supporting Anthropic and DeepSeek APIs.

---

## Current State Analysis

**File**: `src/llm_processor.py`

```python
# Current architecture issues:
class LLMProcessor:
    def __init__(self, api_key, model, ...):
        self.client = anthropic.Anthropic(api_key=api_key)  # Hardcoded
        self.PRICING = { ... }  # Claude-only pricing

    def process_chunk(self, chunk, ...):
        response = self.client.messages.create(...)  # Anthropic-specific
```

**Problems**:
1. Hardcoded Anthropic SDK dependency
2. `process_chunk()` uses Anthropic-specific API format
3. Pricing dict embedded in processor (duplication with CostEstimator)
4. No provider abstraction

---

## Design

### Provider Support Strategy

| Provider | SDK | API Format | Base URL |
|----------|-----|------------|----------|
| Anthropic | `anthic` | Native Messages API | api.anthropic.com |
| DeepSeek | `openai` | OpenAI-compatible | api.deepseek.com |

### Class Structure

```python
class LLMProcessor:
    """Multi-provider LLM processor"""

    SUPPORTED_PROVIDERS = ["anthropic", "deepseek"]

    # Provider-specific model catalogs
    MODELS = {
        "anthropic": {
            "claude-3-5-sonnet-20241022": {"name": "Sonnet", "quality": "high"},
            "claude-3-5-haiku-20241022": {"name": "Haiku", "quality": "balanced"},
        },
        "deepseek": {
            "deepseek-chat": {"name": "DeepSeek Chat", "quality": "standard"},
            "deepseek-reasoner": {"name": "DeepSeek Reasoner", "quality": "analytical"},
        }
    }

    def __init__(self, provider: str, model: str, api_key: str = None):
        self.provider = provider
        self._init_client(api_key)

    def _init_client(self, api_key):
        """Initialize provider-specific client"""
        if self.provider == "anthropic":
            self.client = anthropic.Anthropic(api_key=api_key)
        elif self.provider == "deepseek":
            import openai
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
```

### API Call Abstraction

```python
def process_chunk(self, chunk, prompt_template, video_title):
    prompt = self._build_prompt(chunk, prompt_template, video_title)

    if self.provider == "anthropic":
        return self._call_anthropic(prompt)
    elif self.provider == "deepseek":
        return self._call_openai_compat(prompt)

def _call_anthropic(self, prompt):
    response = self.client.messages.create(
        model=self.model,
        max_tokens=self.max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return ProcessedChunk(
        cleaned_text=response.content[0].text,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )

def _call_openai_compat(self, prompt):
    response = self.client.chat.completions.create(
        model=self.model,
        max_tokens=self.max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return ProcessedChunk(
        cleaned_text=response.choices[0].message.content,
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
    )
```

---

## Implementation Tasks

### 1. Add OpenAI dependency (5 min)

**File**: `requirements.txt`

```diff
+ openai>=1.0.0
```

### 2. Refactor LLMProcessor.__init__ (30 min)

**File**: `src/llm_processor.py`

```python
class LLMProcessor:
    SUPPORTED_PROVIDERS = ["anthropic", "deepseek"]

    MODELS = {
        "anthropic": {
            "claude-3-5-sonnet-20241022": {"name": "Sonnet", "quality": "high"},
            "claude-3-5-haiku-20241022": {"name": "Haiku", "quality": "balanced"},
        },
        "deepseek": {
            "deepseek-chat": {"name": "DeepSeek Chat", "quality": "standard"},
            "deepseek-reasoner": {"name": "DeepSeek Reasoner", "quality": "analytical"},
        }
    }

    # Environment variable mapping
    API_KEY_ENV_VARS = {
        "anthropic": "ANTHROPIC_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY"
    }

    def __init__(
        self,
        provider: str = "anthropic",
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096
    ):
        if provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")

        # Validate model belongs to provider
        if model not in self.MODELS.get(provider, {}):
            raise ValueError(f"Model {model} not available for provider {provider}")

        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Get API key
        env_var = self.API_KEY_ENV_VARS[provider]
        self.api_key = api_key or os.getenv(env_var)
        if not self.api_key:
            raise ValueError(f"API key required. Set {env_var} env var.")

        # Initialize provider client
        self._init_client()

    def _init_client(self):
        """Initialize provider-specific API client"""
        if self.provider == "anthropic":
            self.client = anthropic.Anthropic(api_key=self.api_key)
        elif self.provider == "deepseek":
            import openai
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
```

### 3. Add provider-specific API call methods (45 min)

**File**: `src/llm_processor.py`

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RateLimitError, APIConnectionError, InternalServerError))
)
def process_chunk(
    self,
    chunk: Chunk,
    prompt_template: str,
    video_title: str = "Untitled"
) -> ProcessedChunk:
    prompt = self._build_prompt(chunk, prompt_template, video_title)

    if self.provider == "anthropic":
        return self._process_anthropic(prompt, chunk)
    elif self.provider == "deepseek":
        return self._process_openai_compat(prompt, chunk)

def _process_anthropic(self, prompt: str, chunk: Chunk) -> ProcessedChunk:
    response = self.client.messages.create(
        model=self.model,
        max_tokens=self.max_tokens,
        temperature=self.temperature,
        messages=[{"role": "user", "content": prompt}]
    )

    cost = self._calculate_cost(
        response.usage.input_tokens,
        response.usage.output_tokens
    )

    return ProcessedChunk(
        chunk_index=chunk.index,
        original_text=chunk.text,
        cleaned_text=response.content[0].text,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        cost=cost,
        model=self.model
    )

def _process_openai_compat(self, prompt: str, chunk: Chunk) -> ProcessedChunk:
    from openai import RateLimitError, APIConnectionError
    import openai

    response = self.client.chat.completions.create(
        model=self.model,
        max_tokens=self.max_tokens,
        temperature=self.temperature,
        messages=[{"role": "user", "content": prompt}]
    )

    cost = self._calculate_cost(
        response.usage.prompt_tokens,
        response.usage.completion_tokens
    )

    return ProcessedChunk(
        chunk_index=chunk.index,
        original_text=chunk.text,
        cleaned_text=response.choices[0].message.content,
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
        cost=cost,
        model=self.model
    )
```

### 4. Remove PRICING dict from LLMProcessor (10 min)

**Rationale**: Pricing already exists in `CostEstimator`; avoid duplication.

```python
# Remove this constant from LLMProcessor:
- PRICING = { ... }

# Cost calculation will delegate to CostEstimator or use shared pricing
```

### 5. Update process_transcript() convenience function (20 min)

**File**: `src/llm_processor.py`

```python
def process_transcript(
    chunks: list[Chunk],
    provider: str,
    api_key: str,
    video_title: str,
    model: str = None,  # Default based on provider
    prompt_path: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> tuple[list[ProcessedChunk], dict]:
    """
    Process entire transcript with specified provider.

    Args:
        provider: "anthropic" or "deepseek"
        model: Model ID (or default for provider)
    """
    # Default model selection
    if model is None:
        model = {
            "anthropic": "claude-3-5-sonnet-20241022",
            "deepseek": "deepseek-chat"
        }[provider]

    processor = LLMProcessor(provider=provider, model=model, api_key=api_key)
    template = processor.load_prompt_template(prompt_path)

    results = processor.process_all_chunks(
        chunks, template, video_title, progress_callback
    )

    # Calculate totals
    total_input = sum(r.input_tokens for r in results)
    total_output = sum(r.output_tokens for r in results)
    total_cost = sum(r.cost for r in results)

    summary = {
        "provider": provider,
        "model": model,
        "chunks_processed": len(results),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cost": round(total_cost, 4)
    }

    return results, summary
```

### 6. Add error handling for DeepSeek (20 min)

**File**: `src/llm_processor.py`

```python
# Add provider-specific error mapping
PROVIDER_ERRORS = {
    "anthropic": {
        "rate_limit": anthropic.RateLimitError,
        "connection": anthropic.APIConnectionError,
        "internal": anthropic.InternalServerError,
        "auth": anthropic.AuthenticationError
    },
    "deepseek": {
        "rate_limit": None,  # OpenAI SDK has RateLimitError
        "connection": None,
        "internal": None,
        "auth": None
    }
}

# In retry decorator, catch OpenAI errors for DeepSeek
from openai import RateLimitError as OpenAIRateLimitError
from openai import APIConnectionError as OpenAIConnectionError
from openai import InternalServerError as OpenAIInternalError

@retry(
    retry=retry_if_exception_type((
        anthropic.RateLimitError,
        anthropic.APIConnectionError,
        anthropic.InternalServerError,
        OpenAIRateLimitError,
        OpenAIConnectionError,
        OpenAIInternalError
    ))
)
```

### 7. Update tests (30 min)

**File**: `tests/test_llm_processor.py`

```python
class TestLLMProcessorMultiProvider:
    """Test multi-provider support"""

    def test_init_anthropic_provider(self):
        with patch('src.llm_processor.anthropic.Anthropic'):
            processor = LLMProcessor(provider="anthropic")
            assert processor.provider == "anthropic"

    def test_init_deepseek_provider(self):
        with patch('src.llm_processor.openai.OpenAI'):
            processor = LLMProcessor(provider="deepseek", model="deepseek-chat")
            assert processor.provider == "deepseek"

    def test_unsupported_provider_raises_error(self):
        with pytest.raises(ValueError, match="Unsupported provider"):
            LLMProcessor(provider="invalid")

    def test_model_mismatch_with_provider(self):
        with pytest.raises(ValueError, match="not available for provider"):
            LLMProcessor(provider="deepseek", model="claude-3-5-sonnet-20241022")

    def test_api_key_env_var_mapping(self):
        # Verify correct env var is used per provider
        assert LLMProcessor.API_KEY_ENV_VARS["anthropic"] == "ANTHROPIC_API_KEY"
        assert LLMProcessor.API_KEY_ENV_VARS["deepseek"] == "DEEPSEEK_API_KEY"

    @patch('src.llm_processor.openai.OpenAI')
    def test_process_chunk_deepseek(self, mock_openai):
        # Mock OpenAI-compatible response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Cleaned text"))]
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 80

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        processor = LLMProcessor(provider="deepseek", model="deepseek-chat", api_key="test")
        chunk = Chunk(index=0, text="Original", start_timestamp="00:00:00")
        template = "Clean: {{chunkText}}"

        result = processor.process_chunk(chunk, template, "Test Video")

        assert result.cleaned_text == "Cleaned text"
        assert result.input_tokens == 100
        assert result.output_tokens == 80
```

---

## Testing Checklist

- [ ] LLMProcessor init with both providers
- [ ] Model validation per provider
- [ ] API key env var resolution
- [ ] Anthropic API call path (existing tests still pass)
- [ ] DeepSeek API call path (new tests)
- [ ] Cost calculation per provider
- [ ] Error handling for both providers
- [ ] Retry logic for both providers

---

## Backward Compatibility

**Breaking Change**: `LLMProcessor.__init__()` signature changes

**Old**:
```python
processor = LLMProcessor(api_key="xxx", model="claude-3-5-sonnet-20241022")
```

**New**:
```python
processor = LLMProcessor(provider="anthropic", model="claude-3-5-sonnet-20241022", api_key="xxx")
```

**Migration**: Update `app.py` to pass `provider` parameter. Maintain default `provider="anthropic"` for compatibility.

---

## Unresolved Questions

1. Should we expose `get_available_models(provider)` helper for UI?
   - **Recommendation**: Yes, useful for dynamic model dropdown in Phase 3

2. Retry configuration - should it be provider-specific?
   - **Recommendation**: No, keep uniform retry config for simplicity

---

## Files Modified

- `src/llm_processor.py` - Major refactor
- `requirements.txt` - Add openai>=1.0.0
- `tests/test_llm_processor.py` - New test cases
