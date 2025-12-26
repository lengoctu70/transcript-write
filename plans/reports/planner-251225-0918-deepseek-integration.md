# DeepSeek Integration Plan - Summary

**Date**: 2025-12-25
**Plan ID**: 251225-0908-deepseek-integration
**Status**: Ready for Implementation

## Overview

Add DeepSeek API as alternative LLM provider (~10x cheaper than Claude) with multi-provider architecture supporting both Anthropic and DeepSeek.

## Location

`/Users/lengoctu70/Documents/Python Code/transcript_write/plans/251225-0908-deepseek-integration/`

## Files Created

| File | Purpose |
|------|---------|
| `plan.md` | Master plan with overview & phases |
| `phase-01-multi-provider-llm-processor.md` | LLMProcessor refactor (2.5h) |
| `phase-02-cost-estimator-update.md` | CostEstimator pricing updates (1h) |
| `phase-03-ui-updates.md` | Streamlit UI provider selection (1.5h) |

## Total Effort

**6 hours** across 3 phases + tests/docs

## Key Decisions

1. **Universal Client**: Use OpenAI SDK for DeepSeek (OpenAI-compatible API), Anthropic SDK for Claude
2. **Provider Prefix**: Model IDs use provider prefix (e.g., `deepseek-chat`, `claude-3-5-sonnet-20241022`)
3. **Environment Variables**: Separate keys (`ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`)
4. **Backward Compatibility**: Default provider="anthropic" preserves existing behavior

## Pricing Comparison (per 1K tokens)

| Provider | Model | Input | Output |
|----------|-------|-------|--------|
| Anthropic | claude-3-5-sonnet | $0.003 | $0.015 |
| Anthropic | claude-3-5-haiku | $0.001 | $0.005 |
| DeepSeek | deepseek-chat | $0.00056 | $0.00042 |
| DeepSeek | deepseek-reasoner | $0.00056 | $0.00042 |

**DeepSeek is ~5-10x cheaper than Claude Haiku.**

## Implementation Order

1. **Phase 01**: Refactor `LLMProcessor` for multi-provider
2. **Phase 02**: Update `CostEstimator` with DeepSeek pricing
3. **Phase 03**: Update Streamlit UI for provider selection
4. **Phase 04**: Tests & documentation

## Dependencies

- `openai>=1.0.0` (add to requirements.txt)
- DeepSeek API access for testing

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| DeepSeek API downtime | Fallback to Claude |
| Output quality diff | User choice preserved |
| OpenAI SDK incompatibility | Tests verify compatibility |
| Breaking existing workflows | Default provider=anthropic |

## Unresolved Questions

1. Cache provider/model selection in session state? **Yes, recommended**
2. Default provider selection? **Anthropic (preserve existing behavior)**
3. DeepSeek reasoner longer response times? **Add UI note about slower speed**

## Next Steps

1. Review plan files for technical accuracy
2. Verify DeepSeek API access for testing
3. Begin Phase 01 implementation
