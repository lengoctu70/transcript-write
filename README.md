# Transcript Cleaning Tool

Convert lecture transcripts (SRT/VTT) to clean study notes using Claude API.

## Features

- Parse SRT and VTT subtitle files
- Smart chunking with context preservation
- Claude API integration with retry logic
- Cost estimation before processing
- Rule-based output validation
- Markdown export with metadata

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set API key:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-xxx
   ```

3. Run:
   ```bash
   streamlit run app.py
   ```

## Configuration

- **Model**: claude-3-5-sonnet (quality) or claude-3-5-haiku (speed)
- **Chunk size**: 1000-4000 chars (default 2000)
- **Overlap**: 0-500 chars (default 200)

## Cost Estimates

| Video Length | Estimated Cost |
|--------------|----------------|
| 30 min       | ~$0.20         |
| 60 min       | ~$0.40         |
| 90 min       | ~$0.60         |

## Project Structure

```
transcript_write/
├── app.py                 # Streamlit UI
├── src/                   # Core modules
│   ├── transcript_parser.py
│   ├── chunker.py
│   ├── llm_processor.py
│   ├── validator.py
│   ├── markdown_writer.py
│   └── cost_estimator.py
├── prompts/               # Prompt templates
├── output/                # Generated files
└── tests/                 # Unit & integration tests
```

## License

MIT
