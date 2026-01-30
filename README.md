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

### 3. Add Your PDF(s)

Place your PDF file(s) in the `data/` directory:

```bash
cp your_document.pdf data/
```

The system supports multiple PDFs - you'll be prompted to select one if multiple files exist.

### 4. Configure Sections

Edit `config.yaml` to specify which PDF to use and define the sections:

```yaml
document:
  path: "data/your_document.pdf"  # Path to PDF in data/ directory
  title: "Document Title"

sections:
  - name: "Section Name"
    pages: [1, 2, 3]  # 1-indexed page numbers
```

If the configured PDF is not found, the system will automatically list available PDFs and prompt you to select one.

### 5. Run

```bash
python -m src.main --config config.yaml --output output
```

**Interactive PDF Selection:**
If multiple PDFs exist in the `data/` directory or if the configured PDF is not found, the system will automatically prompt you to select one:

```
Found 3 PDF(s) in 'data/' directory:
  1. vestas_annual_report_2024.pdf (14.2 MB)
  2. vestas_annual_report_2024_compressed.pdf (14.1 MB)
  3. another_document.pdf (20.5 MB)

Select a PDF (1-3):
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

### Compress a Large PDF

If your PDF is larger than the threshold (default 10 MB), it will be automatically compressed:

```bash
# Manual compression
python -m src.main --compress data/large_document.pdf
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
├── data/                     # Input PDF documents (add your PDFs here)
│   ├── .gitkeep              # Placeholder to track directory in git
│   └── your_document.pdf     # e.g., vestas_annual_report_2024.pdf
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

## AI Collaboration Logs

Raw Claude Code session logs are included for transparency:

- [`docs/ai_chat_history/cf2dc0cd-e2d4-4619-8125-138549fb6c47.jsonl`](docs/ai_chat_history/cf2dc0cd-e2d4-4619-8125-138549fb6c47.jsonl)

## Requirements

- Python 3.10+
- Anthropic API key
