"""
Prompt templates for the PDF-to-Podcast system.

All prompts are stored here for easy iteration and documentation.
"""

# ============================================================================
# EXTRACTOR PROMPTS
# ============================================================================

KEY_POINTS_EXTRACTION_PROMPT = """You are an expert analyst extracting key points from a corporate document.

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
{{
    "key_points": [
        {{
            "point": "Summary of the key point",
            "category": "fact|strategy|market|context",
            "source_quote": "Exact quote from the document",
            "page": page_number
        }}
    ]
}}

Extract 3-7 key points per section. Focus on what's MOST important for someone to understand the business."""


# ============================================================================
# GENERATOR PROMPTS
# ============================================================================

PODCAST_PLANNING_PROMPT = """You are planning a 10-minute two-host educational podcast episode about a corporate document.

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
{{
    "title": "Catchy episode title",
    "opening_hook": "The hook that grabs attention in the first 30 seconds",
    "segments": [
        {{
            "title": "Segment title",
            "key_points_to_cover": ["point 1", "point 2"],
            "approach": "How Alex and Jordan will discuss this"
        }}
    ],
    "friction_moment": "Describe the specific moment where Jordan pushes back and why",
    "takeaway": "The clear 'so what' message listeners should remember"
}}"""


DIALOGUE_GENERATION_PROMPT = """Write a natural two-host podcast dialogue based on this plan.

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
{{
    "title": "Episode title",
    "dialogue": [
        {{
            "speaker": "Alex",
            "text": "The dialogue text",
            "emotion_cue": "[optional emotion cue]" or null
        }}
    ],
    "friction_moment_summary": "Brief summary of the friction moment",
    "takeaway_summary": "Brief summary of the main takeaway"
}}

Start with Alex introducing the topic and make it engaging from the first line!"""


# ============================================================================
# VERIFIER PROMPTS
# ============================================================================

CLAIM_EXTRACTION_PROMPT = """Extract all FACTUAL CLAIMS from this podcast script.

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
{{
    "claims": [
        {{
            "claim": "The specific factual claim",
            "script_context": "The full dialogue line containing this claim",
            "line_index": index_of_dialogue_line
        }}
    ]
}}

Be thorough but precise - extract only verifiable factual claims."""


CLAIM_VERIFICATION_PROMPT = """Verify if this claim from a podcast script is supported by the source document.

CLAIM: "{claim}"

SCRIPT CONTEXT: "{script_context}"

SOURCE DOCUMENT SECTIONS:
{source_sections}

Determine if the source document supports this claim.

SUPPORTED: The claim is directly stated or clearly implied in the source
PARTIALLY_SUPPORTED: The claim is related to source content but adds interpretation or minor details not in source
NOT_FOUND: The claim cannot be traced to any passage in the source

Return a JSON object:
{{
    "status": "SUPPORTED|PARTIALLY_SUPPORTED|NOT_FOUND",
    "source_page": page_number_if_found_or_null,
    "source_quote": "exact_quote_if_found_or_null",
    "explanation": "Brief explanation of your assessment"
}}"""


COVERAGE_ANALYSIS_PROMPT = """Analyze how well the podcast script covers the key points from a document section.

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
{{
    "section": "{section_name}",
    "status": "FULL|PARTIAL|OMITTED",
    "key_points_total": total_count,
    "key_points_covered": covered_count,
    "covered": ["list of covered points"],
    "omitted": ["list of omitted points"]
}}

FULL = all or nearly all key points covered
PARTIAL = some key points covered, some omitted
OMITTED = section not meaningfully covered"""


# ============================================================================
# BATCH VERIFICATION PROMPTS (Cost-optimized)
# ============================================================================

BATCH_CLAIM_VERIFICATION_PROMPT = """Verify multiple claims from a podcast script against the source document.

CLAIMS TO VERIFY:
{claims_list}

SOURCE DOCUMENT:
{source_sections}

For EACH claim, determine:
- SUPPORTED: Directly stated or clearly implied in source
- PARTIALLY_SUPPORTED: Related but adds interpretation not in source
- NOT_FOUND: Cannot be traced to source

Return a JSON object with verification for each claim:
{{
    "verifications": [
        {{
            "claim_id": 0,
            "status": "SUPPORTED|PARTIALLY_SUPPORTED|NOT_FOUND",
            "source_page": page_number_or_null,
            "source_quote": "brief_supporting_quote_or_null",
            "explanation": "One sentence explanation"
        }}
    ]
}}

Be concise but accurate. Verify all {num_claims} claims."""


BATCH_COVERAGE_ANALYSIS_PROMPT = """Analyze how well the podcast script covers key points from ALL sections.

SECTIONS AND KEY POINTS:
{all_sections_key_points}

PODCAST SCRIPT:
{script}

For EACH section, determine coverage status:
- FULL: All or nearly all key points covered
- PARTIAL: Some covered, some omitted
- OMITTED: Section not meaningfully covered

Return a JSON object:
{{
    "coverage": [
        {{
            "section": "Section Name",
            "status": "FULL|PARTIAL|OMITTED",
            "key_points_total": N,
            "key_points_covered": M,
            "covered": ["point 1", "point 2"],
            "omitted": ["point 3"]
        }}
    ]
}}

Analyze all {num_sections} sections."""
