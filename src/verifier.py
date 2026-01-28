"""
Verification Agent (Cost-Optimized)

Verifies podcast script accuracy against source document.
Uses batching and Haiku model to minimize API costs.

Cost optimizations:
- Batch claim verification (10-15 claims per call instead of 1)
- Batch coverage analysis (all sections in 1 call)
- Use Haiku for verification tasks (10x cheaper than Sonnet)
"""
import json
from typing import List

import anthropic

from .models import (
    ExtractedDocument,
    PodcastScript,
    ExtractedClaim,
    ClaimVerification,
    CoverageItem,
    VerificationReport,
)
from .prompts import (
    CLAIM_EXTRACTION_PROMPT,
    BATCH_CLAIM_VERIFICATION_PROMPT,
    BATCH_COVERAGE_ANALYSIS_PROMPT,
)

# Model selection for cost optimization
EXTRACTION_MODEL = "claude-sonnet-4-20250514"  # Sonnet for claim extraction (needs accuracy)
VERIFICATION_MODEL = "claude-haiku-4-5-20251001"  # Haiku for verification (cheaper, still accurate)
BATCH_SIZE = 15  # Claims per verification batch


class VerifierAgent:
    """Agent responsible for verifying podcast script accuracy."""

    def __init__(self, anthropic_client: anthropic.Anthropic):
        self.client = anthropic_client

    def verify_script(
        self,
        script: PodcastScript,
        extracted_doc: ExtractedDocument
    ) -> VerificationReport:
        """
        Verify a podcast script against the source document.

        Cost-optimized: Uses batching and Haiku model.
        """
        print("[Verifier] Step 1: Extracting claims from script...")
        claims = self._extract_claims(script)
        print(f"[Verifier] Found {len(claims)} factual claims")

        print("[Verifier] Step 2: Verifying claims (batched)...")
        verifications = self._verify_claims_batched(claims, extracted_doc)

        print("[Verifier] Step 3: Analyzing coverage (batched)...")
        coverage = self._analyze_coverage_batched(script, extracted_doc)

        # Calculate statistics
        supported = sum(1 for v in verifications if v.status == "SUPPORTED")
        partial = sum(1 for v in verifications if v.status == "PARTIALLY_SUPPORTED")
        not_found = sum(1 for v in verifications if v.status == "NOT_FOUND")

        support_rate = (supported + partial * 0.5) / len(verifications) * 100 if verifications else 0

        # Calculate coverage percentage
        total_key_points = sum(c.key_points_total for c in coverage)
        covered_key_points = sum(c.key_points_covered for c in coverage)
        coverage_pct = covered_key_points / total_key_points * 100 if total_key_points > 0 else 0

        # Identify hallucinations
        hallucinations = [v for v in verifications if v.status == "NOT_FOUND"]

        print(f"[Verifier] Results: {supported} supported, {partial} partial, {not_found} not found")
        print(f"[Verifier] Coverage: {coverage_pct:.1f}%")

        return VerificationReport(
            document_title=extracted_doc.title,
            script_title=script.title,
            script_word_count=script.word_count,
            total_claims=len(claims),
            supported_claims=supported,
            partially_supported_claims=partial,
            unsupported_claims=not_found,
            support_rate=support_rate,
            overall_coverage_percentage=coverage_pct,
            claim_verifications=verifications,
            coverage_analysis=coverage,
            hallucination_flags=hallucinations
        )

    def _format_script_for_prompt(self, script: PodcastScript) -> str:
        """Format script for prompts."""
        lines = []
        for i, line in enumerate(script.dialogue):
            emotion = f" {line.emotion_cue}" if line.emotion_cue else ""
            lines.append(f"[{i}] {line.speaker}{emotion}: {line.text}")
        return "\n".join(lines)

    def _extract_claims(self, script: PodcastScript) -> List[ExtractedClaim]:
        """Extract factual claims from the script using Claude."""
        script_formatted = self._format_script_for_prompt(script)

        prompt = CLAIM_EXTRACTION_PROMPT.format(script=script_formatted)

        response = self.client.messages.create(
            model=EXTRACTION_MODEL,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = response.content[0].text
        json_str = self._extract_json(response_text)

        try:
            data = json.loads(json_str)
            claims = []
            for c in data.get("claims", []):
                claims.append(ExtractedClaim(
                    claim=c["claim"],
                    script_context=c["script_context"],
                    line_index=c.get("line_index", 0)
                ))
            return claims
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[Verifier] Warning: Failed to parse claims JSON: {e}")
            return []

    def _verify_claims_batched(
        self,
        claims: List[ExtractedClaim],
        doc: ExtractedDocument
    ) -> List[ClaimVerification]:
        """Verify claims in batches for cost efficiency."""
        source_sections = self._format_source_for_verification(doc)
        verifications = []

        # Process in batches
        for batch_start in range(0, len(claims), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(claims))
            batch = claims[batch_start:batch_end]
            batch_num = batch_start // BATCH_SIZE + 1
            total_batches = (len(claims) + BATCH_SIZE - 1) // BATCH_SIZE

            print(f"[Verifier] Verifying batch {batch_num}/{total_batches} ({len(batch)} claims)...")

            # Format claims for batch prompt
            claims_list = "\n".join([
                f"[{i}] Claim: \"{c.claim}\"\n    Context: \"{c.script_context}\""
                for i, c in enumerate(batch)
            ])

            prompt = BATCH_CLAIM_VERIFICATION_PROMPT.format(
                claims_list=claims_list,
                source_sections=source_sections,
                num_claims=len(batch)
            )

            response = self.client.messages.create(
                model=VERIFICATION_MODEL,
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = response.content[0].text
            json_str = self._extract_json(response_text)

            try:
                data = json.loads(json_str)
                batch_verifications = data.get("verifications", [])

                for i, claim in enumerate(batch):
                    # Find matching verification result
                    v_data = next(
                        (v for v in batch_verifications if v.get("claim_id") == i),
                        {"status": "NOT_FOUND", "explanation": "No verification returned"}
                    )

                    verifications.append(ClaimVerification(
                        claim=claim.claim,
                        script_context=claim.script_context,
                        source_page=v_data.get("source_page"),
                        source_quote=v_data.get("source_quote"),
                        status=v_data.get("status", "NOT_FOUND"),
                        explanation=v_data.get("explanation", "")
                    ))

            except (json.JSONDecodeError, KeyError) as e:
                print(f"[Verifier] Warning: Failed to parse batch verification: {e}")
                # Mark all claims in batch as unverified
                for claim in batch:
                    verifications.append(ClaimVerification(
                        claim=claim.claim,
                        script_context=claim.script_context,
                        source_page=None,
                        source_quote=None,
                        status="NOT_FOUND",
                        explanation="Batch verification failed"
                    ))

        return verifications

    def _format_source_for_verification(self, doc: ExtractedDocument) -> str:
        """Format source document for verification prompts."""
        sections = []
        for section in doc.sections:
            sections.append(f"## {section.name} (pages {', '.join(str(p) for p in section.pages)})")
            for kp in section.key_points:
                sections.append(f"- Page {kp.page}: \"{kp.source_quote}\"")
            # Truncate raw text to save tokens
            sections.append(f"\nRaw text excerpt:\n{section.raw_text[:1500]}...")
        return "\n\n".join(sections)

    def _analyze_coverage_batched(
        self,
        script: PodcastScript,
        doc: ExtractedDocument
    ) -> List[CoverageItem]:
        """Analyze coverage for all sections in one call."""
        script_formatted = self._format_script_for_prompt(script)

        # Format all sections and key points
        all_sections = []
        for section in doc.sections:
            key_points = "\n".join([f"  - {kp.point}" for kp in section.key_points])
            all_sections.append(f"### {section.name}\n{key_points}")

        all_sections_text = "\n\n".join(all_sections)

        prompt = BATCH_COVERAGE_ANALYSIS_PROMPT.format(
            all_sections_key_points=all_sections_text,
            script=script_formatted,
            num_sections=len(doc.sections)
        )

        response = self.client.messages.create(
            model=VERIFICATION_MODEL,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = response.content[0].text
        json_str = self._extract_json(response_text)

        try:
            data = json.loads(json_str)
            coverage_items = []

            for section in doc.sections:
                # Find matching coverage result
                c_data = next(
                    (c for c in data.get("coverage", []) if c.get("section") == section.name),
                    None
                )

                if c_data:
                    coverage_items.append(CoverageItem(
                        section=section.name,
                        status=c_data.get("status", "PARTIAL"),
                        key_points_total=c_data.get("key_points_total", len(section.key_points)),
                        key_points_covered=c_data.get("key_points_covered", 0),
                        covered=c_data.get("covered", []),
                        omitted=c_data.get("omitted", [])
                    ))
                else:
                    coverage_items.append(CoverageItem(
                        section=section.name,
                        status="PARTIAL",
                        key_points_total=len(section.key_points),
                        key_points_covered=0,
                        covered=[],
                        omitted=[kp.point for kp in section.key_points]
                    ))

            return coverage_items

        except (json.JSONDecodeError, KeyError) as e:
            print(f"[Verifier] Warning: Failed to parse coverage: {e}")
            return [
                CoverageItem(
                    section=section.name,
                    status="PARTIAL",
                    key_points_total=len(section.key_points),
                    key_points_covered=0,
                    covered=[],
                    omitted=[kp.point for kp in section.key_points]
                )
                for section in doc.sections
            ]

    def _extract_json(self, text: str) -> str:
        """Extract JSON from response text."""
        if "```json" in text:
            return text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            return text.split("```")[1].split("```")[0].strip()
        return text.strip()


def verify_script(
    script: PodcastScript,
    extracted_doc: ExtractedDocument,
    client: anthropic.Anthropic
) -> VerificationReport:
    """
    Convenience function to verify script.

    Args:
        script: Generated podcast script
        extracted_doc: Source document with key points
        client: Anthropic client

    Returns:
        VerificationReport with claim traceability and coverage
    """
    agent = VerifierAgent(client)
    return agent.verify_script(script, extracted_doc)
