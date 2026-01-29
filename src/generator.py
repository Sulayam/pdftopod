"""
Script Generator Agent

Generates podcast scripts from extracted document content using Claude.
Two-phase approach: Planning → Dialogue Generation
"""
import json
from typing import List

import anthropic

from .models import (
    ExtractedDocument,
    PodcastPlan,
    PodcastSegment,
    DialogueLine,
    PodcastScript,
    KeyPoint,
)
from .prompts import PODCAST_PLANNING_PROMPT, DIALOGUE_GENERATION_PROMPT


class GeneratorAgent:
    """Agent responsible for generating podcast scripts."""

    def __init__(self, anthropic_client: anthropic.Anthropic):
        self.client = anthropic_client

    def generate_script(self, extracted_doc: ExtractedDocument) -> PodcastScript:
        """
        Generate a podcast script from extracted document.

        Args:
            extracted_doc: Document with extracted sections and key points

        Returns:
            PodcastScript with dialogue and metadata
        """
        # Phase 1: Planning
        print("[Generator] Phase 1: Creating podcast plan...")
        plan = self._create_plan(extracted_doc)
        print(f"[Generator] Plan created: {plan.title}")
        print(f"[Generator] Friction moment: {plan.friction_moment[:100]}...")

        # Phase 2: Dialogue Generation
        print("[Generator] Phase 2: Generating dialogue...")
        script = self._generate_dialogue(plan, extracted_doc)
        print(f"[Generator] Script generated: {script.word_count} words")

        return script

    def _format_key_points_for_prompt(self, doc: ExtractedDocument) -> str:
        """Format key points for the planning prompt."""
        lines = []
        for section in doc.sections:
            lines.append(f"\n## {section.name} (pages {', '.join(str(p) for p in section.pages)})")
            for kp in section.key_points:
                lines.append(f"- [{kp.category.upper()}] {kp.point}")
        return "\n".join(lines)

    def _format_key_points_with_sources(self, doc: ExtractedDocument) -> str:
        """Format key points with source quotes for dialogue generation."""
        lines = []
        for section in doc.sections:
            lines.append(f"\n## {section.name}")
            for kp in section.key_points:
                lines.append(f"- {kp.point}")
                lines.append(f"  Source (p.{kp.page}): \"{kp.source_quote[:200]}...\"" if len(kp.source_quote) > 200 else f"  Source (p.{kp.page}): \"{kp.source_quote}\"")
        return "\n".join(lines)

    def _create_plan(self, doc: ExtractedDocument) -> PodcastPlan:
        """Create a podcast plan using Claude."""
        key_points_formatted = self._format_key_points_for_prompt(doc)

        prompt = PODCAST_PLANNING_PROMPT.format(
            document_title=doc.title,
            key_points=key_points_formatted
        )

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = response.content[0].text

        # Extract JSON
        json_str = self._extract_json(response_text)

        try:
            data = json.loads(json_str)
            segments = [
                PodcastSegment(
                    title=s["title"],
                    key_points_to_cover=s["key_points_to_cover"],
                    approach=s["approach"]
                )
                for s in data.get("segments", [])
            ]
            return PodcastPlan(
                title=data["title"],
                opening_hook=data["opening_hook"],
                segments=segments,
                friction_moment=data["friction_moment"],
                takeaway=data["takeaway"]
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[Generator] Warning: Failed to parse plan JSON: {e}")
            print(f"[Generator] Raw response: {response_text[:500]}...")
            # Return a default plan
            return PodcastPlan(
                title=f"Deep Dive: {doc.title}",
                opening_hook="Let's explore what this document reveals...",
                segments=[],
                friction_moment="Hosts discuss implications",
                takeaway="Key insights from the document"
            )

    def _generate_dialogue(self, plan: PodcastPlan, doc: ExtractedDocument) -> PodcastScript:
        """Generate the actual dialogue script with length enforcement."""
        key_points_with_sources = self._format_key_points_with_sources(doc)

        # Format plan for prompt
        plan_formatted = json.dumps({
            "title": plan.title,
            "opening_hook": plan.opening_hook,
            "segments": [
                {
                    "title": s.title,
                    "key_points_to_cover": s.key_points_to_cover,
                    "approach": s.approach
                }
                for s in plan.segments
            ],
            "friction_moment": plan.friction_moment,
            "takeaway": plan.takeaway
        }, indent=2)

        prompt = DIALOGUE_GENERATION_PROMPT.format(
            plan=plan_formatted,
            key_points_with_sources=key_points_with_sources
        )

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,  # Larger for ~2000 word dialogue
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = response.content[0].text
        json_str = self._extract_json(response_text)
        script = self._parse_dialogue_json(json_str, plan)

        # Check if script is too short and expand if needed
        min_words = 1800
        max_expansion_attempts = 2

        for attempt in range(max_expansion_attempts):
            if script.word_count >= min_words:
                break

            print(f"[Generator] Script too short ({script.word_count} words), expanding (attempt {attempt + 1})...")
            script = self._expand_script(script, plan, key_points_with_sources)

        return script

    def _parse_dialogue_json(self, json_str: str, plan: PodcastPlan) -> PodcastScript:
        """Parse dialogue JSON into PodcastScript."""
        try:
            data = json.loads(json_str)
            dialogue = [
                DialogueLine(
                    speaker=d["speaker"],
                    text=d["text"],
                    emotion_cue=d.get("emotion_cue")
                )
                for d in data.get("dialogue", [])
            ]
            return PodcastScript(
                title=data.get("title", plan.title),
                dialogue=dialogue,
                friction_moment_summary=data.get("friction_moment_summary", plan.friction_moment),
                takeaway_summary=data.get("takeaway_summary", plan.takeaway)
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[Generator] Warning: Failed to parse dialogue JSON: {e}")
            return PodcastScript(
                title=plan.title,
                dialogue=[],
                friction_moment_summary=plan.friction_moment,
                takeaway_summary=plan.takeaway
            )

    def _expand_script(self, script: PodcastScript, plan: PodcastPlan, key_points_with_sources: str) -> PodcastScript:
        """Expand a short script to meet the word count target."""
        current_dialogue = "\n".join([
            f"{d.speaker}: {d.text}" for d in script.dialogue
        ])

        expand_prompt = f"""The following podcast script is too short at {script.word_count} words. It MUST be expanded to 2000-2200 words.

CURRENT SCRIPT ({script.word_count} words):
{current_dialogue}

SOURCE KEY POINTS (for adding more detail):
{key_points_with_sources}

EXPANSION REQUIREMENTS:
1. Keep ALL existing dialogue but ADD MORE exchanges between Alex and Jordan
2. Expand discussions of statistics - add context, implications, comparisons
3. Add more back-and-forth reactions: "Wait, really?", "That's surprising", "Tell me more"
4. Explore implications of key points more deeply
5. Add more questions from Jordan challenging the information
6. Target 2000-2200 words total - you are REQUIRED to hit this target
7. Maintain the same friction moment and takeaway themes

Return the EXPANDED script as JSON:
{{
    "title": "{script.title}",
    "dialogue": [
        {{"speaker": "Alex", "text": "dialogue text", "emotion_cue": "[optional]" or null}}
    ],
    "friction_moment_summary": "{script.friction_moment_summary}",
    "takeaway_summary": "{script.takeaway_summary}"
}}"""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            messages=[
                {"role": "user", "content": expand_prompt}
            ]
        )

        response_text = response.content[0].text
        json_str = self._extract_json(response_text)
        return self._parse_dialogue_json(json_str, plan)

    def _extract_json(self, text: str) -> str:
        """Extract JSON from response text, handling markdown code blocks."""
        if "```json" in text:
            return text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            return text.split("```")[1].split("```")[0].strip()
        return text.strip()


def generate_script(extracted_doc: ExtractedDocument, client: anthropic.Anthropic) -> PodcastScript:
    """
    Convenience function to generate script.

    Args:
        extracted_doc: Extracted document with key points
        client: Anthropic client

    Returns:
        PodcastScript with generated dialogue
    """
    agent = GeneratorAgent(client)
    return agent.generate_script(extracted_doc)
