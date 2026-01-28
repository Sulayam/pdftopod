"""
Pydantic models for the PDF-to-Podcast system.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ============================================================================
# Extractor Models
# ============================================================================

class KeyPoint(BaseModel):
    """A key point extracted from a document section."""
    point: str = Field(description="The key point summary")
    category: Literal["fact", "strategy", "market", "context"] = Field(
        description="Category of the key point"
    )
    source_quote: str = Field(description="Exact quote from source supporting this point")
    page: int = Field(description="Page number where this point was found")


class SectionContent(BaseModel):
    """Content extracted from a document section."""
    name: str = Field(description="Section name")
    pages: List[int] = Field(description="Page numbers covered")
    raw_text: str = Field(description="Raw extracted text")
    key_points: List[KeyPoint] = Field(default_factory=list, description="Extracted key points")


class ExtractedDocument(BaseModel):
    """Complete extracted document with all sections."""
    title: str = Field(description="Document title")
    sections: List[SectionContent] = Field(description="Extracted sections")

    @property
    def all_key_points(self) -> List[KeyPoint]:
        """Get all key points from all sections."""
        return [kp for section in self.sections for kp in section.key_points]

    @property
    def total_key_points(self) -> int:
        """Total number of key points."""
        return len(self.all_key_points)


# ============================================================================
# Generator Models
# ============================================================================

class PodcastSegment(BaseModel):
    """A segment in the podcast plan."""
    title: str = Field(description="Segment title")
    key_points_to_cover: List[str] = Field(description="Key points this segment covers")
    approach: str = Field(description="How to present this segment")


class PodcastPlan(BaseModel):
    """Plan for the podcast episode."""
    title: str = Field(description="Podcast episode title")
    opening_hook: str = Field(description="Opening hook to grab attention")
    segments: List[PodcastSegment] = Field(description="Planned segments")
    friction_moment: str = Field(description="The moment where hosts disagree or push back")
    takeaway: str = Field(description="Clear 'so what' takeaway at the end")


class DialogueLine(BaseModel):
    """A single line of dialogue in the podcast script."""
    speaker: Literal["Alex", "Jordan"] = Field(description="Speaker name")
    text: str = Field(description="The dialogue text")
    emotion_cue: Optional[str] = Field(default=None, description="Emotion cue like [laughs], [thoughtful]")


class PodcastScript(BaseModel):
    """Complete podcast script."""
    title: str = Field(description="Episode title")
    dialogue: List[DialogueLine] = Field(description="The dialogue lines")
    friction_moment_summary: str = Field(description="Summary of the friction/disagreement moment")
    takeaway_summary: str = Field(description="Summary of the main takeaway")

    @property
    def word_count(self) -> int:
        """Calculate total word count of dialogue."""
        return sum(len(line.text.split()) for line in self.dialogue)

    def to_markdown(self) -> str:
        """Convert script to markdown format."""
        lines = [f"# {self.title}", "", f"*~{self.word_count} words*", "", "---", ""]

        for line in self.dialogue:
            emotion = f" {line.emotion_cue}" if line.emotion_cue else ""
            lines.append(f"**{line.speaker}:**{emotion} {line.text}")
            lines.append("")

        lines.extend([
            "---",
            "",
            f"**Friction Moment:** {self.friction_moment_summary}",
            "",
            f"**Key Takeaway:** {self.takeaway_summary}"
        ])

        return "\n".join(lines)


# ============================================================================
# Verifier Models
# ============================================================================

class ExtractedClaim(BaseModel):
    """A factual claim extracted from the podcast script."""
    claim: str = Field(description="The factual claim")
    script_context: str = Field(description="The dialogue line containing this claim")
    line_index: int = Field(description="Index of the dialogue line")


class ClaimVerification(BaseModel):
    """Verification result for a single claim."""
    claim: str = Field(description="The factual claim")
    script_context: str = Field(description="Context from script")
    source_page: Optional[int] = Field(default=None, description="Page where evidence was found")
    source_quote: Optional[str] = Field(default=None, description="Supporting quote from source")
    status: Literal["SUPPORTED", "PARTIALLY_SUPPORTED", "NOT_FOUND"] = Field(
        description="Verification status"
    )
    explanation: str = Field(description="Explanation for the verification status")


class CoverageItem(BaseModel):
    """Coverage analysis for a single section."""
    section: str = Field(description="Section name")
    status: Literal["FULL", "PARTIAL", "OMITTED"] = Field(description="Coverage status")
    key_points_total: int = Field(description="Total key points in section")
    key_points_covered: int = Field(description="Number of key points covered")
    covered: List[str] = Field(description="Key points that were covered")
    omitted: List[str] = Field(description="Key points that were omitted")


class VerificationReport(BaseModel):
    """Complete verification report."""
    document_title: str = Field(description="Title of the source document")
    script_title: str = Field(description="Title of the podcast script")
    script_word_count: int = Field(description="Word count of the script")

    # Summary statistics
    total_claims: int = Field(description="Total factual claims found")
    supported_claims: int = Field(description="Claims supported by source")
    partially_supported_claims: int = Field(description="Claims partially supported")
    unsupported_claims: int = Field(description="Claims not found in source (potential hallucinations)")
    support_rate: float = Field(description="Percentage of claims supported")

    # Coverage
    overall_coverage_percentage: float = Field(description="Overall coverage percentage")

    # Details
    claim_verifications: List[ClaimVerification] = Field(description="Detailed claim verifications")
    coverage_analysis: List[CoverageItem] = Field(description="Coverage by section")
    hallucination_flags: List[ClaimVerification] = Field(
        description="Claims flagged as potential hallucinations"
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "metadata": {
                "document_title": self.document_title,
                "script_title": self.script_title,
                "script_word_count": self.script_word_count
            },
            "summary": {
                "total_claims": self.total_claims,
                "supported": self.supported_claims,
                "partially_supported": self.partially_supported_claims,
                "unsupported_hallucinations": self.unsupported_claims,
                "support_rate": f"{self.support_rate:.1f}%",
                "coverage_percentage": f"{self.overall_coverage_percentage:.1f}%"
            },
            "claim_traceability": [
                {
                    "claim": cv.claim,
                    "script_context": cv.script_context,
                    "source_page": cv.source_page,
                    "source_quote": cv.source_quote,
                    "status": cv.status,
                    "explanation": cv.explanation
                }
                for cv in self.claim_verifications
            ],
            "hallucination_flags": [
                {
                    "claim": hf.claim,
                    "script_context": hf.script_context,
                    "reason": hf.explanation
                }
                for hf in self.hallucination_flags
            ],
            "coverage_analysis": [
                {
                    "section": ci.section,
                    "status": ci.status,
                    "key_points_total": ci.key_points_total,
                    "key_points_covered": ci.key_points_covered,
                    "covered": ci.covered,
                    "omitted": ci.omitted
                }
                for ci in self.coverage_analysis
            ]
        }


# ============================================================================
# Configuration Models
# ============================================================================

class SectionConfig(BaseModel):
    """Configuration for a section to extract."""
    name: str = Field(description="Section name")
    pages: List[int] = Field(description="Page numbers to extract (1-indexed)")


class DocumentConfig(BaseModel):
    """Configuration for the document."""
    path: str = Field(description="Path to the PDF file")
    title: str = Field(description="Document title")


class Config(BaseModel):
    """Complete configuration."""
    document: DocumentConfig = Field(description="Document configuration")
    sections: List[SectionConfig] = Field(description="Sections to extract")
