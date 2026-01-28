# PDF-to-Podcast System: Implementation Plan

## Overview
Build a document-to-podcast system with verification layer using Anthropic Claude. Lightweight multi-agent architecture without heavy frameworks.

**LLM:** Anthropic Claude (claude-sonnet-4-20250514)

---

## Files to Create

```
pdftopod/
├── README.md                      # Setup & run instructions
├── requirements.txt               # Dependencies
├── config.yaml                    # Section configuration (test document)
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLI entry point & orchestrator
│   ├── extractor.py               # PDF extraction agent
│   ├── generator.py               # Script generation agent
│   ├── verifier.py                # Verification agent
│   ├── models.py                  # Pydantic schemas
│   └── prompts.py                 # All prompts in one place
├── output/                        # Generated outputs
│   ├── podcast_script.md
│   └── verification_report.json
└── docs/
    └── PROCESS.md                 # Process documentation + reflection
```

---

## Implementation Steps

### Step 1: Project Setup
- Create directory structure
- Write requirements.txt (anthropic, pymupdf4llm, pydantic, pyyaml)
- Create models.py with all Pydantic schemas
- Create prompts.py with all prompt templates

### Step 2: Extractor Agent (extractor.py)
- Load PDF with pymupdf4llm
- Parse config.yaml for section definitions
- Extract text from specified pages
- Call Claude to extract key points per section
- Return ExtractedDocument model

### Step 3: Generator Agent (generator.py)
- Phase 1: Generate podcast plan from key points
- Phase 2: Generate dialogue script from plan
- Ensure ~2000 words, friction moment, takeaway
- Return PodcastScript model

### Step 4: Verifier Agent (verifier.py)
- Extract factual claims from script
- Match each claim to source passages
- Calculate coverage per section
- Generate VerificationReport model

### Step 5: Orchestrator (main.py)
- CLI with argparse
- Load config, run pipeline
- Save outputs to output/
- Error handling

### Step 6: Test & Document
- Download Vestas PDF
- Run full pipeline
- Verify outputs manually
- Write PROCESS.md with prompts and reflections

---

## Key Models (models.py)

```python
class KeyPoint(BaseModel):
    point: str
    category: Literal["fact", "strategy", "market", "context"]
    source_quote: str
    page: int

class SectionContent(BaseModel):
    name: str
    pages: List[int]
    raw_text: str
    key_points: List[KeyPoint]

class ExtractedDocument(BaseModel):
    title: str
    sections: List[SectionContent]

class DialogueLine(BaseModel):
    speaker: Literal["Alex", "Jordan"]
    text: str
    emotion_cue: Optional[str] = None

class PodcastScript(BaseModel):
    title: str
    dialogue: List[DialogueLine]
    friction_moment: str
    takeaway: str
    word_count: int

class ClaimVerification(BaseModel):
    claim: str
    script_line: str
    source_page: Optional[int]
    source_quote: Optional[str]
    status: Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "NOT_FOUND"]

class CoverageItem(BaseModel):
    section: str
    status: Literal["FULL", "PARTIAL", "OMITTED"]
    covered: List[str]
    omitted: List[str]

class VerificationReport(BaseModel):
    total_claims: int
    supported: int
    hallucinations: int
    coverage_percentage: float
    claims: List[ClaimVerification]
    coverage: List[CoverageItem]
```

---

## Config Format (config.yaml)

```yaml
document:
  path: "vestas_annual_report_2024.pdf"
  title: "Vestas Annual Report 2024"

sections:
  - name: "Letter from Chair & CEO"
    pages: [3, 4]
  - name: "Market outlook"
    pages: [17, 18]
  - name: "Corporate strategy"
    pages: [19, 20, 21]
  - name: "Service"
    pages: [31]
```

---

## Verification

After implementation:
1. Download Vestas Annual Report 2024 PDF
2. Run: `python src/main.py --config config.yaml`
3. Check output/podcast_script.md has ~2000 words
4. Check output/verification_report.json is valid
5. Manually verify 3 claims match source
6. Ensure all 4 sections have coverage data
