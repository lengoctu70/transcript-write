---
title: "Phase 03: Streamlit UI Multi-Provider Updates"
description: "Update Streamlit UI for provider selection and model filtering"
status: pending
priority: P2
effort: 1.5h
tags: [ui, streamlit, multi-provider]
---

## Overview

Update Streamlit UI (`app.py`) to support provider selection (Anthropic/DeepSeek) with dynamic model filtering and API key management.

---

## Current UI State

**File**: `app.py`

```python
# Sidebar - hardcoded for Anthropic
api_key = st.text_input(
    "Anthropic API Key",
    value=os.getenv("ANTHROPIC_API_KEY", ""),
    type="password"
)

model = st.selectbox(
    "Model",
    options=[
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022"
    ]
)

# Later in code
estimator = CostEstimator(model=model)
```

**Issues**:
1. No provider selection
2. Model list hardcoded to Anthropic
3. Single API key input
4. Cost estimator called without provider

---

## Design

### UI Layout

```
┌─ Sidebar ──────────────────────────────┐
│ Configuration                           │
│                                         │
│ Provider:  ○ Anthropic  ○ DeepSeek     │
│                                         │
│ Model:    [claude-3-5-sonnet ▼]        │
│           (Sonnet: Higher quality...)   │
│                                         │
│ API Key:  [•••••••••••••••••]          │
│           Get key from console.anth...  │
│                                         │
│ Chunking                                │
│ [sliders...]                            │
└─────────────────────────────────────────┘
```

### Provider Selection Logic

1. User selects provider → Model dropdown filters to that provider's models
2. Model list populated from `CostEstimator.get_models_for_provider()`
3. API key label/placeholder updates per provider
4. Environment variable mapping handled automatically

---

## Implementation Tasks

### 1. Add provider selection (20 min)

**File**: `app.py`

```python
def main():
    st.title("📝 Transcript Cleaning Tool")
    st.markdown("Convert lecture transcripts to clean study notes")

    # Sidebar configuration
    with st.sidebar:
        st.header("Configuration")

        # Provider selection
        provider = st.radio(
            "LLM Provider",
            options=["anthropic", "deepseek"],
            format_func=lambda x: {
                "anthropic": "Anthropic (Claude)",
                "deepseek": "DeepSeek (~10x cheaper)"
            }.get(x, x.title()),
            help="Choose your LLM provider. DeepSeek is more cost-effective."
        )

        # Initialize session state for provider switching
        if "provider" not in st.session_state:
            st.session_state.provider = provider
        elif st.session_state.provider != provider:
            # Provider changed, reset model selection
            st.session_state.provider = provider
            st.session_state.model = None

        # Model selection (filtered by provider)
        available_models = CostEstimator.get_models_for_provider(provider)
        default_model = CostEstimator.get_default_model(provider)

        # Use session state to preserve model across reruns
        if "model" not in st.session_state or st.session_state.model not in available_models:
            st.session_state.model = default_model

        model = st.selectbox(
            "Model",
            options=available_models,
            index=available_models.index(st.session_state.model),
            key=f"model_select_{provider}",  # Force refresh on provider change
            help={
                "anthropic": {
                    "claude-3-5-sonnet-20241022": "Sonnet: Higher quality, higher cost",
                    "claude-3-5-haiku-20241022": "Haiku: Faster, cheaper"
                },
                "deepseek": {
                    "deepseek-chat": "Standard model, fast and affordable",
                    "deepseek-reasoner": "Advanced reasoning, slower"
                }
            }.get(provider, {}).get(st.session_state.model, "")
        )

        # Update session state
        st.session_state.model = model

        st.divider()

        # API Key (provider-specific)
        api_key_env_var = {
            "anthropic": "ANTHROPIC_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY"
        }[provider]

        api_key_help = {
            "anthropic": "Get your API key from console.anthropic.com",
            "deepseek": "Get your API key from platform.deepseek.com"
        }[provider]

        api_key = st.text_input(
            f"{provider.title()} API Key",
            value=os.getenv(api_key_env_var, ""),
            type="password",
            help=api_key_help,
            key=f"api_key_{provider}"
        )

        # Cost comparison info (collapsed)
        with st.expander("💡 Provider Comparison", expanded=False):
            st.markdown("""
            | Provider | Cost (1K tokens) | Speed | Quality |
            |----------|------------------|-------|---------|
            | **Anthropic Sonnet** | $0.018 | Fast | High |
            | **Anthropic Haiku** | $0.006 | Very fast | Good |
            | **DeepSeek Chat** | $0.001 | Fast | Good |
            | **DeepSeek Reasoner** | $0.001 | Slow | High |

            *DeepSeek is ~10x cheaper than Claude.*
            """)
```

### 2. Update cost estimator call (10 min)

**File**: `app.py`

```python
with col2:
    st.subheader("2. Cost Estimate")

    # Estimate cost (with provider)
    estimator = CostEstimator(provider=provider, model=model)
    prompt_path = Path(__file__).parent / "prompts" / "base_prompt.txt"

    if prompt_path.exists():
        prompt_template = prompt_path.read_text()
        estimate = estimator.estimate_total(chunks, prompt_template)

        # Display estimate
        metric_cols = st.columns(3)
        with metric_cols[0]:
            st.metric("Estimated Cost", f"${estimate.total_cost:.4f}")
        with metric_cols[1]:
            st.metric("Chunks", estimate.chunks)
        with metric_cols[2]:
            st.metric("Est. Time", f"~{estimate.processing_time_minutes} min")

        with st.expander("Cost breakdown"):
            st.markdown(estimator.format_estimate(estimate))
```

### 3. Update process_transcript call (15 min)

**File**: `app.py`

```python
def process_transcript_ui(
    chunks: list,
    provider: str,
    model: str,
    api_key: str,
    video_title: str,
    prompt_template: str
):
    """Process transcript with progress tracking"""

    # Progress UI
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(current: int, total: int):
        progress_bar.progress(current / total)
        status_text.text(f"Processing chunk {current}/{total}...")

    # Process with error handling
    def do_process():
        return process_transcript(
            chunks=chunks,
            provider=provider,
            api_key=api_key,
            video_title=video_title,
            model=model,
            progress_callback=update_progress
        )

    # ... rest of function unchanged
```

**Update the caller:**

```python
if st.button("🚀 Process Transcript", type="primary", use_container_width=True):
    process_transcript_ui(
        chunks=chunks,
        provider=provider,
        model=model,
        api_key=api_key,
        video_title=video_title,
        prompt_template=prompt_template
    )
```

### 4. Update error handling for OpenAI errors (20 min)

**File**: `app.py`

```python
try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from openai import RateLimitError as OpenAIRateLimitError
    from openai import AuthenticationError as OpenAIAuthError
    from openai import APIConnectionError as OpenAIConnectionError
    has_openai = True
except ImportError:
    has_openai = False


def safe_process(func):
    """Wrap processing with user-friendly errors"""
    try:
        return func()
    except Exception as e:
        error_name = type(e).__name__

        # Anthropic errors
        if anthropic and error_name == "AuthenticationError":
            st.error("❌ Invalid API key. Check your Anthropic API key.")
        elif anthropic and error_name == "RateLimitError":
            st.error("⏳ Rate limit reached. Please wait a moment and try again.")
        elif anthropic and error_name == "APIConnectionError":
            st.error("🌐 Network error. Check your internet connection.")

        # OpenAI/DeepSeek errors
        elif has_openai and error_name == "AuthenticationError":
            st.error("❌ Invalid API key. Check your DeepSeek API key.")
        elif has_openai and error_name == "RateLimitError":
            st.error("⏳ Rate limit reached. Please wait a moment and try again.")
        elif has_openai and error_name == "APIConnectionError":
            st.error("🌐 Network error connecting to DeepSeek API.")

        else:
            st.error(f"❌ Unexpected error: {str(e)}")
            with st.expander("Error details"):
                st.code(traceback.format_exc())
        return None
```

### 5. Add provider indicator to results (5 min)

**File**: `app.py`

```python
# Success message
st.success(f"✅ Processing complete! Cost: ${summary['total_cost']:.4f}")

# Show provider/model used
st.caption(f"Provider: {summary['provider'].title()} | Model: {summary['model']}")
```

### 6. Update .env.example (5 min)

**File**: `.env.example`

```diff
# Anthropic API (default provider)
ANTHROPIC_API_KEY=sk-ant-xxx

+# DeepSeek API (alternative provider)
+DEEPSEEK_API_KEY=sk-deepseek-xxx
```

---

## Testing Checklist

- [ ] Provider radio button switches between Anthropic/DeepSeek
- [ ] Model dropdown updates when provider changes
- [ ] API key input shows correct help text per provider
- [ ] Cost estimates reflect provider-specific pricing
- [ ] "Process Transcript" works with DeepSeek provider
- [ ] Error handling for invalid DeepSeek API key
- [ ] Session state preserves model selection within provider
- [ ] Model resets when switching providers
- [ ] Provider comparison expander displays correctly

---

## Edge Cases

### 1. User switches provider without API key

**Solution**: Show warning if no API key for selected provider

```python
# Check for API key based on provider
api_key_env_var = {"anthropic": "ANTHROPIC_API_KEY", "deepseek": "DEEPSEEK_API_KEY"}[provider]
if not api_key and not os.getenv(api_key_env_var):
    st.warning(f"⚠️ No {provider.title()} API key found. Enter key above to continue.")
```

### 2. Processing in progress, user switches provider

**Solution**: Disable provider selection during processing

```python
# Use session state to track processing status
if st.session_state.get("processing"):
    st.info("Processing in progress...")
    # Disable provider selection during processing
    st.radio("LLM Provider", options=[provider], disabled=True)
```

### 3. Model becomes unavailable (API changes)

**Solution**: Graceful fallback with error message

```python
try:
    available_models = CostEstimator.get_models_for_provider(provider)
except Exception as e:
    st.error(f"Could not load models for {provider}: {e}")
    available_models = ["claude-3-5-sonnet-20241022"]  # Fallback
```

---

## Files Modified

- `app.py` - Major UI updates
- `.env.example` - Add DEEPSEEK_API_KEY

---

## Unresolved Questions

1. Should we add "Quick Switch" button to re-process with different provider?
   - **Recommendation**: Nice-to-have, allows easy A/B comparison

2. Display cost savings when switching from Anthropic to DeepSeek?
   - **Recommendation**: Yes, show "Save ~$X.XX vs Anthropic" when DeepSeek selected

3. Remember user's provider preference in browser?
   - **Recommendation**: Use st.session_state persists per session, no localStorage needed
