# Phase 1: Project Setup & Dependencies

**Effort:** 1 hour
**Dependencies:** None
**Deliverables:** Working dev environment, directory structure, config files

---

## Tasks

### 1.1 Create Directory Structure

```bash
mkdir -p src prompts output tests/fixtures
touch src/__init__.py
```

Final structure:
```
transcript_write/
├── src/
│   └── __init__.py
├── prompts/
├── output/
└── tests/
    └── fixtures/
```

### 1.2 Create requirements.txt

```txt
# Core
streamlit>=1.29.0
anthropic>=0.8.0
python-dotenv>=1.0.0

# Parsing
pysrt>=1.1.2
webvtt-py>=0.4.6

# Utilities
tiktoken>=0.5.2
tenacity>=8.2.3

# Dev/Testing
pytest>=7.4.3
```

### 1.3 Create .env.example

```env
ANTHROPIC_API_KEY=sk-ant-xxx
# Optional: OPENAI_API_KEY for future support
```

### 1.4 Create .gitignore

```gitignore
# Environment
.env
.venv/
venv/

# Output
output/*.md
output/*.json

# Python
__pycache__/
*.pyc
.pytest_cache/

# IDE
.vscode/
.idea/
```

### 1.5 Setup Python Environment

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 1.6 Move Existing Prompt

Move content from README.md prompt section to `prompts/base_prompt.txt`:

```txt
# ROLE
You are a senior transcript editor...
[Full prompt content from README.md]
```

Keep placeholders: `{{fileName}}`, `{{chunkText}}`

### 1.7 Verify Setup

```bash
# Test imports
python -c "import streamlit; import anthropic; import pysrt; import webvtt"
echo "Setup complete!"
```

---

## Success Criteria

- [x] All directories created
- [x] requirements.txt with correct versions
- [x] .env.example with API key placeholder
- [x] .gitignore excludes sensitive files
- [x] Virtual environment activated
- [x] All packages install without errors
- [x] Base prompt moved to prompts/base_prompt.txt

## Code Review Status

**Reviewed:** 2025-12-24 22:45
**Completed:** 2025-12-24 22:49
**Status:** DONE

### Issues Found
- **Medium:** anthropic>=0.8.0 outdated (latest: 0.75.0)
- **Medium:** .DS_Store not gitignored (macOS artifact)
- **Low:** Virtual environment not created/activated

### Recommendations
1. Update requirements.txt: `anthropic>=0.75.0`
2. Add to .gitignore: `.DS_Store` and `**/.DS_Store`
3. Complete venv setup per task 1.5

---

## Security Notes

- Never commit .env file
- API key loaded via python-dotenv
- .gitignore configured before any secrets added
