# Process Documentation

This document describes the system architecture, prompts, iterations, and design decisions for the PDF-to-Podcast generator.

## System Overview

### High-Level Flow

```
PDF Document + Config
        │
        ▼
┌───────────────────┐
│  EXTRACTOR AGENT  │
│  - Parse PDF      │
│  - Extract text   │
│  - Identify keys  │
└───────────────────┘
        │
        ▼
   ExtractedDocument
   (sections + key points)
        │
        ▼
┌───────────────────┐
│  GENERATOR AGENT  │
│  Phase 1: Plan    │
│  Phase 2: Script  │
└───────────────────┘
        │
        ▼
    PodcastScript
   (~2000 word dialogue)
        │
        ▼
┌───────────────────┐
│  VERIFIER AGENT   │
│  - Extract claims │
│  - Verify source  │
│  - Check coverage │
└───────────────────┘
        │
        ▼
  VerificationReport
  (JSON with traceability)
```

### Why This Architecture?

**Lightweight multi-agent without a framework** was chosen because:

1. **Time constraints**: The assessment recommends 2-4 hours. Framework setup (CrewAI, LangGraph) adds overhead.
2. **Linear workflow**: No complex branching or cycles needed - a simple sequential pipeline suffices.
3. **Explainability**: Raw prompts are easier to review and iterate on than framework abstractions.
4. **Assessment criteria**: "A simple architecture well-justified beats a complex one poorly explained."

The system is still "agentic" because:
- Each stage has a specialized role and prompt
- Planning happens before generation (not single-shot)
- Self-verification checks output against source

---

## Prompts

### Extractor: Key Points Extraction

**Purpose**: Extract important facts, strategies, and insights from document sections.

```
You are an expert analyst extracting key points from a corporate document.

Given the following text from a section titled "{section_name}" (pages {pages}):

<document_text>
{text}
</document_text>

Extract the KEY POINTS that a reader MUST understand from this section. Focus on:
- **Facts**: Numbers, metrics, revenue figures, growth percentages, market share
- **Strategy**: Strategic decisions, stated intentions, future plans
- **Market**: Market assessments, industry trends, competitive position
- **Context**: Important background, challenges, or explanations

For each key point:
1. Summarize the point concisely (1-2 sentences)
2. Categorize it as: fact, strategy, market, or context
3. Include the EXACT quote from the text that supports it
4. Note the page number

Return your response as a JSON object with this structure:
{
    "key_points": [
        {
            "point": "Summary of the key point",
            "category": "fact|strategy|market|context",
            "source_quote": "Exact quote from the document",
            "page": page_number
        }
    ]
}

Extract 3-7 key points per section. Focus on what's MOST important for someone to understand the business.
```

**Design decisions**:
- Categorization helps prioritize facts vs. context
- Source quotes are extracted for verification traceability
- 3-7 points per section balances depth with podcast length constraints

---

### Generator: Podcast Planning

**Purpose**: Create a structured plan before generating dialogue.

```
You are planning a 10-minute two-host educational podcast episode about a corporate document.

DOCUMENT: {document_title}

HOSTS:
- **Alex**: The enthusiastic explainer. Good at analogies and making complex topics accessible. Asks clarifying questions like "right?" or "you know what I mean?"
- **Jordan**: The thoughtful skeptic. Pushes back on claims, asks tough questions, plays devil's advocate. Says things like "But wait..." or "I'm not sure I buy that..."

KEY POINTS TO COVER (extracted from the document):
{key_points}

Create a podcast plan that:
1. Opens with a HOOK that grabs attention (why should listeners care?)
2. Covers ALL the key points across 3-4 segments
3. Includes ONE clear FRICTION MOMENT where Jordan pushes back or disagrees with something
4. Ends with a clear TAKEAWAY ("so what" moment - what should listeners remember?)

Return your response as a JSON object:
{
    "title": "Catchy episode title",
    "opening_hook": "The hook that grabs attention in the first 30 seconds",
    "segments": [
        {
            "title": "Segment title",
            "key_points_to_cover": ["point 1", "point 2"],
            "approach": "How Alex and Jordan will discuss this"
        }
    ],
    "friction_moment": "Describe the specific moment where Jordan pushes back and why",
    "takeaway": "The clear 'so what' message listeners should remember"
}
```

**Design decisions**:
- Two-phase generation (plan → dialogue) produces more coherent scripts
- Host personas are defined upfront for consistent characterization
- Friction moment is planned explicitly to ensure it happens
- Takeaway is required to meet "land a takeaway" requirement

---

### Generator: Dialogue Generation

**Purpose**: Generate the actual podcast dialogue.

```
Write a natural two-host podcast dialogue based on this plan.

EPISODE PLAN:
{plan}

SOURCE KEY POINTS (with page references):
{key_points_with_sources}

HOSTS:
- **Alex**: Enthusiastic explainer. Uses analogies. Natural speech patterns like "you know", "right?", brief reactions.
- **Jordan**: Thoughtful skeptic. Challenges assumptions. Says "But wait...", "Hmm", "I'm not sure about that..."

REQUIREMENTS:
- Target ~2000 words total (about 10 minutes of audio)
- Sound like REAL conversation, not alternating lectures
- Include natural speech: reactions, brief interjections, thinking pauses
- Include the planned FRICTION MOMENT where Jordan pushes back
- End with the clear TAKEAWAY
- Use LIGHTWEIGHT emotion cues in brackets: [laughs], [thoughtful], [surprised], [skeptical]
- DO NOT invent facts - only use information from the source material
- Each piece of dialogue should be 1-3 sentences max

Return your response as a JSON object:
{
    "title": "Episode title",
    "dialogue": [
        {
            "speaker": "Alex",
            "text": "The dialogue text",
            "emotion_cue": "[optional emotion cue]" or null
        }
    ],
    "friction_moment_summary": "Brief summary of the friction moment",
    "takeaway_summary": "Brief summary of the main takeaway"
}

Start with Alex introducing the topic and make it engaging from the first line!
```

**Design decisions**:
- Explicit instruction not to invent facts reduces hallucination
- Short dialogue lines (1-3 sentences) sound more natural
- Emotion cues are "lightweight and professional" per requirements
- JSON output enables structured processing and verification

---

### Verifier: Claim Extraction

**Purpose**: Identify factual claims to verify.

```
Extract all FACTUAL CLAIMS from this podcast script.

A factual claim is:
- An assertion about business performance, revenue, growth, market share
- A statement about strategy, plans, or intentions
- A market assessment or industry fact
- Specific numbers, dates, or named entities

A factual claim is NOT:
- Host opinions or subjective assessments ("I think this is interesting")
- General framing or transitions ("Let's talk about...")
- Banter or conversational filler ("Right?", "Exactly!")
- Hypotheticals or speculation clearly marked as such

PODCAST SCRIPT:
{script}

Return a JSON object with extracted claims:
{
    "claims": [
        {
            "claim": "The specific factual claim",
            "script_context": "The full dialogue line containing this claim",
            "line_index": index_of_dialogue_line
        }
    ]
}

Be thorough but precise - extract only verifiable factual claims.
```

**Design decisions**:
- Clear definition of what IS and ISN'T a factual claim
- Context (full dialogue line) preserved for report readability
- Line index enables traceability to script location

---

### Verifier: Claim Verification

**Purpose**: Check if each claim is supported by source.

```
Verify if this claim from a podcast script is supported by the source document.

CLAIM: "{claim}"

SCRIPT CONTEXT: "{script_context}"

SOURCE DOCUMENT SECTIONS:
{source_sections}

Determine if the source document supports this claim.

SUPPORTED: The claim is directly stated or clearly implied in the source
PARTIALLY_SUPPORTED: The claim is related to source content but adds interpretation or minor details not in source
NOT_FOUND: The claim cannot be traced to any passage in the source

Return a JSON object:
{
    "status": "SUPPORTED|PARTIALLY_SUPPORTED|NOT_FOUND",
    "source_page": page_number_if_found_or_null,
    "source_quote": "exact_quote_if_found_or_null",
    "explanation": "Brief explanation of your assessment"
}
```

**Design decisions**:
- Three-level status (supported/partial/not found) is more nuanced than binary
- Source quotes enable manual verification
- Explanation provides context for borderline cases

---

### Verifier: Coverage Analysis

**Purpose**: Check what key points were covered.

```
Analyze how well the podcast script covers the key points from a document section.

SECTION: {section_name}

KEY POINTS FROM SOURCE:
{key_points}

PODCAST SCRIPT:
{script}

For each key point, determine if it was:
- COVERED: The point is clearly discussed in the podcast
- MENTIONED: The point is touched on but not fully explained
- OMITTED: The point is not covered

Return a JSON object:
{
    "section": "{section_name}",
    "status": "FULL|PARTIAL|OMITTED",
    "key_points_total": total_count,
    "key_points_covered": covered_count,
    "covered": ["list of covered points"],
    "omitted": ["list of omitted points"]
}

FULL = all or nearly all key points covered
PARTIAL = some key points covered, some omitted
OMITTED = section not meaningfully covered
```

---

## Iterations and Dead Ends

### Iteration 1: Single-Shot Generation
**Attempt**: Generate podcast script in one prompt.
**Result**: Scripts were unfocused, missed key points, had inconsistent structure.
**Fix**: Added planning phase to create structure before dialogue.

### Iteration 2: Long Dialogue Lines
**Attempt**: No constraint on dialogue length.
**Result**: Hosts gave 5-6 sentence monologues that didn't sound natural.
**Fix**: Added "1-3 sentences max" constraint in prompt.

### Iteration 3: Over-Elaborate Emotion Cues
**Attempt**: Detailed emotion cues like "[leaning forward with excitement]".
**Result**: Too theatrical, not professional.
**Fix**: Changed to "lightweight" cues: [laughs], [thoughtful], [skeptical].

### Iteration 4: Embedding-Based Verification
**Attempt**: Use embeddings for semantic similarity matching.
**Result**: Added complexity without significant improvement for this use case.
**Fix**: LLM-based NLI (natural language inference) is simpler and works well for claim verification.

### Iteration 5: Cost Optimization
**Problem**: Initial implementation cost $1.12 per run - unsustainable for iteration.
**Analysis**: Verification stage made 33+ API calls (1 per claim + 4 for coverage).
**Fix**: Implemented batching and model selection (see Cost Optimization section below).

---

## Cost Optimization

The initial implementation was expensive due to individual API calls for each verification task. Here's how we reduced costs by ~80%:

### The Problem

| Stage | Original Calls | Cost Driver |
|-------|---------------|-------------|
| Extraction | 4 calls | 1 per section (acceptable) |
| Generation | 2 calls | Planning + dialogue (acceptable) |
| Verification | 33+ calls | 1 per claim + 4 for coverage (expensive!) |

**Result**: $1.12 per run, mostly from verification.

### The Solution

#### 1. Batch Claim Verification
Instead of verifying one claim at a time:
```
# BEFORE: 33 API calls
for claim in claims:
    verify_single_claim(claim)  # 1 call each

# AFTER: 3 API calls
for batch in chunks(claims, 15):
    verify_batch(batch)  # 15 claims per call
```

#### 2. Batch Coverage Analysis
Instead of analyzing coverage per section:
```
# BEFORE: 4 API calls (1 per section)
for section in sections:
    analyze_coverage(section)

# AFTER: 1 API call
analyze_all_coverage(sections)  # All sections at once
```

#### 3. Model Selection
Used cheaper model for verification tasks:
```python
# src/verifier.py
EXTRACTION_MODEL = "claude-sonnet-4-20250514"    # Sonnet for claim extraction (needs accuracy)
VERIFICATION_MODEL = "claude-haiku-4-5-20251001" # Haiku for verification (10x cheaper)
```

### Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| API Calls (verification) | 37 | 4 | 90% reduction |
| Model Cost | Sonnet only | Sonnet + Haiku | ~10x cheaper for verification |
| Total Run Cost | ~$1.12 | ~$0.25 | ~80% reduction |

### Trade-offs

- **Batch size**: 15 claims per batch balances cost vs. context window limits
- **Haiku accuracy**: Slightly lower than Sonnet, but sufficient for verification tasks
- **Debugging**: Batched responses are harder to debug than individual calls

---

## AI Tool Usage

This project was developed using Claude Code (Anthropic's CLI tool). The prompts above went through multiple iterations with AI assistance to refine:

- JSON output structure reliability
- Balance between extraction detail and conciseness
- Natural dialogue generation
- Verification accuracy

No changes were made to "clean up" the prompt history - the iterations documented above reflect the actual development process.

---

## AI Suggestions Rejected or Modified

The following are examples where AI-generated suggestions were rejected or significantly modified:

### 1. CrewAI Framework Suggestion
**AI Suggested**: Use CrewAI or LangGraph for multi-agent orchestration.

**Rejected Because**: The workflow is a simple linear pipeline (extract → generate → verify) without branching or cycles. Framework overhead would add complexity without benefit. The assessment explicitly states "a simple architecture well-justified beats a complex one poorly explained."

### 2. Elaborate Host Personas
**AI Suggested**: Create detailed backstories for podcast hosts (Alex is a former financial analyst, Jordan studied journalism, etc.).

**Modified To**: Simple role descriptions ("enthusiastic explainer" and "thoughtful skeptic") with speech pattern examples.

**Why**: Backstories don't improve output quality and add prompt length. The LLM needs behavioral guidance, not fictional biographies.

### 3. Semantic Embedding Verification
**AI Suggested**: Use text-embedding-3-small to create vector embeddings for claim verification via cosine similarity.

**Rejected Because**: Added significant complexity (embedding generation, similarity thresholds, retrieval logic) while initial testing showed LLM-based verification worked adequately for this use case. The added precision wasn't worth the implementation cost for a 2-4 hour assessment.

### 4. Real-Time Streaming Output
**AI Suggested**: Stream dialogue generation token-by-token to show progress.

**Rejected Because**: Adds complexity without improving output quality. Batch generation with JSON parsing is simpler and more reliable. The assessment doesn't require real-time output.

### 5. Automatic Section Detection via PDF TOC
**AI Suggested**: Parse PDF table of contents to auto-detect sections.

**Rejected Because**:
1. TOC parsing is unreliable across PDF styles
2. The assessment explicitly uses page numbers for section specification
3. Page-based configuration is simpler and more predictable for testing on unseen documents

### 6. Multiple Verification Passes
**AI Suggested**: Run 3 verification passes with different prompts and ensemble the results.

**Modified To**: Single verification pass with batch processing and model selection for cost optimization.

**Why**: Multiple passes would 3x the already-expensive verification cost. Batch verification with Haiku achieved acceptable accuracy at ~80% lower cost.

### 7. Markdown Verification Report
**AI Suggested**: Output verification report as Markdown for human readability.

**Modified To**: JSON output with explanation in PROCESS.md.

**Why**: The assessment mentions testing against unseen documents, implying automated validation. JSON is machine-parseable; Markdown would require parsing. Added explanation of this choice to satisfy "explain your choice" requirement.

---

## Reflection Questions

### 1. Why did you choose this architecture/framework (or choose not to use one)?

I chose a **lightweight multi-agent architecture without a framework** (no CrewAI, LangGraph, etc.) for several reasons:

1. **Time constraints**: The assessment recommends 2-4 hours. Framework setup and learning curves would consume significant time.

2. **Workflow simplicity**: This is a linear pipeline (extract → generate → verify) without complex branching, human-in-the-loop decisions, or cycles. Frameworks like LangGraph excel at graph-based workflows with conditional routing, but that's overkill here.

3. **Explainability**: The assessment values "the choices you make" and states "a simple architecture well-justified beats a complex one poorly explained." Raw prompts in a clear module structure are easier to review and understand.

4. **Debugging**: With direct API calls, I can see exactly what's sent to and received from the LLM. Framework abstractions can obscure this.

5. **Reference implementations**: Together.ai's open-source NotebookLM uses a similar approach - JSON mode with structured generation and direct API calls.

The system is still "agentic" because each stage has a specialized role, planning precedes generation, and the output is self-verified against the source.

### 2. What's the weakest part of your system?

The **claim verification accuracy** is the weakest part. Specifically:

1. **Paraphrasing challenges**: LLM-based matching may miss subtle paraphrasing where the claim uses different words than the source but means the same thing.

2. **Context window limitations**: For very long documents, the full source text can't fit in context. The current approach uses key points + excerpts, which may miss relevant passages.

3. **False positives**: The model might find "supporting" text that's actually about a different topic but uses similar terminology.

4. **Coverage judgment**: What counts as "covered" vs. "mentioned" vs. "omitted" is subjective. Different annotators would likely disagree.

A production system would benefit from:
- Embedding-based semantic search for better recall
- Human-in-the-loop verification for critical claims
- Multiple verification passes with different prompts

### 3. If you had another 4 hours, what would you improve first?

I would add **iterative refinement** in this priority order:

1. **Verify-and-Regenerate Loop**: After verification flags hallucinations or coverage gaps, automatically regenerate weak sections. This would significantly improve accuracy.

2. **Semantic Search for Verification**: Use embeddings (text-embedding-3-small) to find the most relevant source passages for each claim, rather than passing the entire extracted text. This would improve claim matching accuracy.

3. **TTS Audio Generation**: Add text-to-speech output using a service like ElevenLabs or Cartesia to produce actual audio. The current system only generates scripts.

4. **Interactive Section Selection**: Add a mode where users can interactively specify sections by viewing the PDF structure, rather than needing to know page numbers upfront.

---

## Technical Notes

### Why JSON for Verification Report?

The verification report uses JSON instead of Markdown because:

1. **Automated testing**: The assessment mentions testing against unseen documents. JSON is machine-parseable for automated validation.

2. **Structured data**: Nested claim traceability and coverage analysis fit naturally in JSON.

3. **Downstream processing**: JSON enables further analysis, aggregation, or display transformation.

The report can easily be converted to Markdown for human reading if needed.

### Why Page-Based Section Configuration?

Page numbers are used instead of heading detection because:

1. **Reliability**: PDF heading detection is inconsistent across document styles.
2. **Explicit specification**: The assessment specifies sections by page number.
3. **Simplicity**: No need for heading parsing logic that might fail on edge cases.
4. **User control**: Users know exactly what's being extracted.
