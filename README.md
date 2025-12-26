# Transcript Cleaning Tool

Convert lecture transcripts (SRT/VTT) to clean study notes using Claude or DeepSeek API.

## Features

- Parse SRT and VTT subtitle files
- Smart chunking with context preservation
- **Multi-provider LLM support**: Anthropic Claude or DeepSeek
- Cost estimation before processing
- Rule-based output validation
- Markdown export with metadata

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set API key (choose one):
   ```bash
   # For Anthropic Claude
   export ANTHROPIC_API_KEY=sk-ant-xxx

   # For DeepSeek
   export DEEPSEEK_API_KEY=sk-xxx
   ```

3. Run:
   ```bash
   streamlit run app.py
   ```

## Configuration

### LLM Providers

| Provider | Models | Cost (per 1K tokens) |
|----------|--------|---------------------|
| **Anthropic** | claude-3-5-sonnet-20241022 | $0.003 input / $0.015 output |
| **Anthropic** | claude-3-5-haiku-20241022 | $0.001 input / $0.005 output |
| **DeepSeek** | deepseek-chat | $0.00027 input / $0.0011 output |
| **DeepSeek** | deepseek-reasoner | $0.00056 input / $0.0022 output |

**Note:** DeepSeek is ~10x cheaper than Claude Sonnet.

### Chunking

- **Chunk size**: 1000-4000 chars (default 2000)
- **Overlap**: 0-500 chars (default 200)

## Cost Estimates

| Video Length | Claude Sonnet | Claude Haiku | DeepSeek Chat |
|--------------|---------------|--------------|---------------|
| 30 min       | ~$0.20        | ~$0.07       | ~$0.02        |
| 60 min       | ~$0.40        | ~$0.14       | ~$0.04        |
| 90 min       | ~$0.60        | ~$0.21       | ~$0.06        |

## Project Structure

```
transcript_write/
├── app.py                 # Streamlit UI
├── src/                   # Core modules
│   ├── transcript_parser.py
│   ├── chunker.py
│   ├── llm_processor.py   # Multi-provider support
│   ├── validator.py
│   ├── markdown_writer.py
│   └── cost_estimator.py
├── prompts/               # Prompt templates
├── output/                # Generated files
└── tests/                 # Unit & integration tests
```

## License

MIT
