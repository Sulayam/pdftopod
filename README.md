# PDF to Podcast Generator

A system that transforms long-form PDF documents into engaging two-host podcast scripts with a verification layer that checks for accuracy and coverage.

## Features

- **PDF Extraction**: Extracts content from specified page ranges using pymupdf4llm
- **Auto-Compression**: Automatically compresses large PDFs (>10MB) before processing
- **Key Point Analysis**: Uses Claude to identify important facts, strategies, and insights
- **Script Generation**: Creates natural two-host dialogue with friction moments and clear takeaways
- **Verification Layer**: Traces factual claims to source passages and analyzes coverage

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Set API Key

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

### 3. Add Your PDF

Place your PDF in the project directory (or update the path in config.yaml).

### 4. Configure Sections

Edit `config.yaml` to specify which sections to cover:

```yaml
document:
  path: "your_document.pdf"
  title: "Document Title"

sections:
  - name: "Section Name"
    pages: [1, 2, 3]  # 1-indexed page numbers
```

### 5. Run

```bash
python -m src.main --config config.yaml --output output
```

### CLI Options

```bash
python -m src.main --help

Options:
  --config, -c           Path to configuration YAML file (default: config.yaml)
  --output, -o           Output directory (default: output)
  --compress-threshold   PDF size threshold in MB for auto-compression (default: 10.0)
  --compress             Compress a PDF file and exit (utility mode)
```

### Compress a PDF (Utility Mode)

```bash
# Compress a large PDF before processing
python -m src.main --compress your_large_document.pdf
```

## Output

The system generates two files in the output directory:

- `podcast_script.md` - The generated podcast script (~2000 words)
- `verification_report.json` - Verification report with claim traceability and coverage analysis

## Project Structure

```
pdftopod/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── config.yaml               # Section configuration
├── src/
│   ├── __init__.py
│   ├── main.py               # CLI entry point & orchestrator
│   ├── extractor.py          # PDF extraction agent
│   ├── generator.py          # Script generation agent
│   ├── verifier.py           # Verification agent
│   ├── models.py             # Pydantic schemas
│   ├── prompts.py            # All prompt templates
│   └── pdf_utils.py          # PDF compression utilities
├── output/                   # Generated outputs
│   ├── podcast_script.md
│   └── verification_report.json
└── docs/
    └── PROCESS.md            # Process documentation
```

## Configuration

### Section Configuration

Sections are specified by page numbers (1-indexed):

```yaml
sections:
  - name: "Introduction"
    pages: [1, 2]          # Pages 1-2
  - name: "Main Content"
    pages: [5, 6, 7, 8]    # Pages 5-8
```

**Why page-based?** Page numbers are the most reliable way to specify sections in PDF documents, as heading detection can be inconsistent across different document styles.

## Architecture

The system uses a lightweight multi-agent architecture:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  EXTRACTOR   │ ──▶ │  GENERATOR   │ ──▶ │  VERIFIER    │
│    Agent     │     │    Agent     │     │    Agent     │
└──────────────┘     └──────────────┘     └──────────────┘
```

1. **Extractor**: Parses PDF, extracts text, identifies key points
2. **Generator**: Plans episode structure, generates natural dialogue
3. **Verifier**: Extracts claims, verifies against source, analyzes coverage

See [docs/PROCESS.md](docs/PROCESS.md) for detailed documentation.

## Verification Report

The JSON verification report includes:

- **Claim Traceability**: Each factual claim mapped to source passage
- **Hallucination Flags**: Claims that couldn't be traced to source
- **Coverage Analysis**: What percentage of key points were covered per section

## Requirements

- Python 3.10+
- Anthropic API key

## License

MIT
