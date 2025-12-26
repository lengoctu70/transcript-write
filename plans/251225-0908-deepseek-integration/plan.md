---
title: "DeepSeek API Integration - Multi-Provider LLM Support"
description: "Add DeepSeek as alternative LLM provider with OpenAI-compatible API"
status: pending
priority: P2
effort: 6h
branch: main
tags: [llm, integration, deepseek, multi-provider]
created: 2025-12-25
---

## Overview

Add DeepSeek API as alternative LLM provider alongside existing Anthropic Claude integration. DeepSeek offers OpenAI-compatible API at ~10x lower cost ($0.27-$0.56/M input tokens vs $3.0/M for Claude Sonnet).

**Business Value**: Reduce processing costs by ~90% for cost-sensitive users while maintaining quality.

### Current State

- Single-provider architecture (Anthropic-only)
- `LLMProcessor` uses Anthropic SDK directly
- `CostEstimator` has Claude-only pricing dict
- UI has hardcoded Claude model dropdown

### Target State

- Multi-provider architecture supporting Anthropic + DeepSeek
- Provider selection in UI (radio button or dropdown)
- Unified pricing across both providers
- Tests covering both providers

---

## Phases

| Phase | Focus | Effort |
|-------|-------|--------|
| [01](./phase-01-multi-provider-llm-processor.md) | Refactor LLMProcessor for multi-provider | 2.5h |
| [02](./phase-02-cost-estimator-update.md) | Update CostEstimator with DeepSeek pricing | 1h |
| [03](./phase-03-ui-updates.md) | Update Streamlit UI for provider selection | 1.5h |
| 04 | Tests & documentation | 1h |

**Total Effort**: 6 hours

---

## Technical Decisions

### 1. Provider Abstraction Strategy

**Decision**: Use OpenAI SDK as universal client wrapper.

**Rationale**:
- DeepSeek is OpenAI-compatible (uses same API format)
- OpenAI SDK supports custom `base_url`
- Avoids dependency bloat (single SDK for multiple providers)
- Anthropic SDK still needed for Claude (different API format)

**Implementation**:
```python
# LLMProcessor will route to appropriate client
if provider == "anthropic":
    client = anthropic.Anthropic(api_key=api_key)
elif provider == "deepseek":
    client = openai.OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )
```

### 2. Environment Variables

**Decision**: Separate API keys per provider.

```
ANTHROPIC_API_KEY=sk-ant-xxx
DEEPSEEK_API_KEY=sk-deepseek-xxx
```

**Rationale**: Users may have keys for both providers; allows switching without re-entering keys.

### 3. Model Identification

**Decision**: Use provider prefix in model IDs.

| Provider | Model ID |
|----------|----------|
| anthropic | claude-3-5-sonnet-20241022 |
| anthropic | claude-3-5-haiku-20241022 |
| deepseek | deepseek-chat |
| deepseek | deepseek-reasoner |

**Rationale**: Prevents naming collisions; clear which provider a model belongs to.

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| DeepSeek API downtime | Low | Fallback to Claude; error handling in place |
| Output quality diff | Medium | Users can compare; provider choice preserved |
| OpenAI SDK incompatibility | Low | DeepSeek advertises OpenAI compatibility; verify in tests |
| Breaking existing workflows | Medium | Maintain backward compat; default provider=anthropic |

---

## Unresolved Questions

1. Should we cache provider/model selection per user in session state?
   - **Recommendation**: Yes, use `st.session_state` for UX

2. Default provider selection?
   - **Recommendation**: Anthropic (existing behavior preserved)

3. DeepSeek `deepseek-reasoner` model - longer response times acceptable?
   - **Recommendation**: Add to UI but note "slower but more analytical" in help text

---

## Dependencies

- **Required**: `openai>=1.0.0` (add to requirements.txt)
- **Optional**: Verify DeepSeek API access for testing

---

## Success Criteria

- [ ] User can select provider (Anthropic/DeepSeek) in UI
- [ ] Cost estimator shows accurate pricing for both providers
- [ ] Processing works with DeepSeek API (end-to-end test)
- [ ] All existing tests still pass (backward compat)
- [ ] New tests cover DeepSeek provider path
- [ ] `.env.example` updated with `DEEPSEEK_API_KEY`
