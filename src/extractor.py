"""
PDF Extractor Agent

Extracts content from PDF documents and identifies key points using Claude.
"""
import json
from typing import List

import pymupdf4llm
import pymupdf
import anthropic

from .models import (
    Config,
    SectionConfig,
    KeyPoint,
    SectionContent,
    ExtractedDocument,
)
from .prompts import KEY_POINTS_EXTRACTION_PROMPT
from .pdf_utils import auto_compress_if_large, get_pdf_info


class ExtractorAgent:
    """Agent responsible for extracting and analyzing PDF content."""

    def __init__(self, anthropic_client: anthropic.Anthropic, compress_threshold_mb: float = 10.0):
        self.client = anthropic_client
        self.compress_threshold_mb = compress_threshold_mb

    def extract_document(self, config: Config) -> ExtractedDocument:
        """
        Extract content from PDF based on configuration.

        Args:
            config: Configuration specifying document path and sections

        Returns:
            ExtractedDocument with extracted sections and key points
        """
        print(f"[Extractor] Opening PDF: {config.document.path}")

        # Auto-compress if PDF is large
        pdf_path = auto_compress_if_large(config.document.path, self.compress_threshold_mb)

        # Open PDF (use compressed version if available)
        doc = pymupdf.open(pdf_path)
        total_pages = len(doc)
        print(f"[Extractor] PDF has {total_pages} pages")

        sections = []
        for section_config in config.sections:
            print(f"[Extractor] Extracting section: {section_config.name}")
            section = self._extract_section(doc, section_config, config.document.title)
            sections.append(section)
            print(f"[Extractor] Found {len(section.key_points)} key points in {section_config.name}")

        doc.close()

        return ExtractedDocument(
            title=config.document.title,
            sections=sections
        )

    def _extract_section(
        self,
        doc: pymupdf.Document,
        section_config: SectionConfig,
        document_title: str
    ) -> SectionContent:
        """Extract a single section from the PDF."""
        # Extract text from specified pages (1-indexed in config, 0-indexed in pymupdf)
        pages_text = []
        for page_num in section_config.pages:
            page_idx = page_num - 1  # Convert to 0-indexed
            if 0 <= page_idx < len(doc):
                page = doc[page_idx]
                # Use pymupdf4llm for better text extraction
                text = pymupdf4llm.to_markdown(doc, pages=[page_idx])
                pages_text.append(f"[Page {page_num}]\n{text}")
            else:
                print(f"[Extractor] Warning: Page {page_num} out of range")

        raw_text = "\n\n".join(pages_text)

        # Extract key points using Claude
        key_points = self._extract_key_points(
            raw_text,
            section_config.name,
            section_config.pages
        )

        return SectionContent(
            name=section_config.name,
            pages=section_config.pages,
            raw_text=raw_text,
            key_points=key_points
        )

    def _extract_key_points(
        self,
        text: str,
        section_name: str,
        pages: List[int]
    ) -> List[KeyPoint]:
        """Use Claude to extract key points from section text."""
        pages_str = ", ".join(str(p) for p in pages)

        prompt = KEY_POINTS_EXTRACTION_PROMPT.format(
            section_name=section_name,
            pages=pages_str,
            text=text
        )

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse response
        response_text = response.content[0].text

        # Extract JSON from response (handle potential markdown code blocks)
        json_str = response_text
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]

        try:
            data = json.loads(json_str.strip())
            key_points = []
            for kp in data.get("key_points", []):
                key_points.append(KeyPoint(
                    point=kp["point"],
                    category=kp["category"],
                    source_quote=kp["source_quote"],
                    page=kp["page"]
                ))
            return key_points
        except json.JSONDecodeError as e:
            print(f"[Extractor] Warning: Failed to parse key points JSON: {e}")
            print(f"[Extractor] Raw response: {response_text[:500]}...")
            return []


def extract_document(config: Config, client: anthropic.Anthropic) -> ExtractedDocument:
    """
    Convenience function to extract document.

    Args:
        config: Configuration for extraction
        client: Anthropic client

    Returns:
        ExtractedDocument with extracted content
    """
    agent = ExtractorAgent(client)
    return agent.extract_document(config)
