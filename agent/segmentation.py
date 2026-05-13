"""LLM-powered contact segmentation using Claude.

Sends contact profiles in batches, receives structured JSON with:
  - emergent segment definitions (not predefined)
  - per-contact assignments with reasoning + confidence
"""
import json
import re
from typing import Any

import anthropic

import agent.storage as storage
from agent import MODEL
from agent.tracer import AgentTracer

_SYSTEM_PROMPT = """You are a B2B sales intelligence expert. Analyse the contact profiles below and identify natural segments that emerge from the data.

RULES:
- Discover 3–5 segments organically — do NOT use generic labels like "Segment A" or predefined categories
- Each segment must reflect a real behavioural or firmographic pattern visible in the data
- Assign every contact to exactly one segment
- confidence is 0.0–1.0: above 0.85 = clear fit, 0.65–0.85 = likely, below 0.65 = ambiguous
- recommended_action: "email" (ready for outreach now), "nurture" (build relationship first), "ignore" (not a fit)

Return ONLY valid JSON — no markdown fences, no explanation, just the object:

{
  "segments": [
    {
      "name": "2–4 word descriptive label",
      "description": "1–2 sentences: who belongs here and what unites them",
      "characteristics": ["trait 1", "trait 2", "trait 3"],
      "email_strategy": "1–2 sentences on how to approach outreach for this group"
    }
  ],
  "assignments": [
    {
      "email": "contact@company.com",
      "segment": "must exactly match a segment name above",
      "reasoning": "2–3 sentences referencing specific data points from their profile",
      "confidence": 0.87,
      "recommended_action": "email"
    }
  ]
}"""


def _format_contacts(contacts: list[dict]) -> str:
    parts = []
    for i, c in enumerate(contacts, 1):
        parts.append(
            f"Contact {i}:\n"
            f"  Email: {c['email']}\n"
            f"  Name: {c['name']}\n"
            f"  Company: {c.get('company', '')}\n"
            f"  Role: {c.get('role', '')}\n"
            f"  Last Activity: {c.get('last_activity', '')}\n"
            f"  Notes: {c.get('notes', '')}"
        )
    return "\n\n".join(parts)


def _extract_json(text: str) -> dict:
    """Parse JSON from response, tolerating markdown code fences."""
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped)
    if m:
        return json.loads(m.group(1).strip())
    m = re.search(r"\{[\s\S]*\}", stripped)
    if m:
        return json.loads(m.group())
    raise ValueError(f"Could not parse JSON from model response: {stripped[:300]}")


class SegmentationEngine:
    def __init__(
        self,
        client: anthropic.Anthropic,
        tracer: AgentTracer,
        batch_size: int = 25,
    ):
        self.client = client
        self.tracer = tracer
        self.batch_size = batch_size

    def run(
        self, contacts: list[dict], custom_criteria: str | None = None
    ) -> dict[str, Any]:
        """Segment all contacts. Returns {segments: [...], assignments: [...]}."""
        system = _SYSTEM_PROMPT
        if custom_criteria and custom_criteria.strip():
            system += (
                f"\n\nAdditional segmentation focus requested by user:\n{custom_criteria.strip()}"
            )

        batches = [
            contacts[i : i + self.batch_size]
            for i in range(0, len(contacts), self.batch_size)
        ]

        all_segments: dict[str, dict] = {}
        all_assignments: list[dict] = []

        for batch_num, batch in enumerate(batches):
            result = self._segment_batch(batch, system, batch_num)
            for seg in result.get("segments", []):
                if seg["name"] not in all_segments:
                    all_segments[seg["name"]] = seg
            all_assignments.extend(result.get("assignments", []))

        return {
            "segments": list(all_segments.values()),
            "assignments": all_assignments,
        }

    def _segment_batch(
        self, batch: list[dict], system: str, batch_num: int
    ) -> dict:
        contact_text = _format_contacts(batch)
        input_summary = f"Batch {batch_num + 1}: {len(batch)} contacts"

        with self.tracer.trace("segmentation", input_summary) as entry:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=8192,
                system=[
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Segment these {len(batch)} contacts:\n\n{contact_text}"
                        ),
                    }
                ],
            )
            entry.tokens_input = response.usage.input_tokens
            entry.tokens_output = response.usage.output_tokens
            entry.model = response.model

            result = _extract_json(response.content[0].text)
            entry.output_summary = (
                f"{len(result.get('segments', []))} segments, "
                f"{len(result.get('assignments', []))} assignments"
            )
            return result

    def persist(self, assignments: list[dict]) -> None:
        """Write segment results back to the database."""
        for a in assignments:
            storage.update_segment(
                email=a["email"],
                segment=a["segment"],
                reasoning=a["reasoning"],
                confidence=float(a.get("confidence", 0.0)),
                action=a["recommended_action"],
            )
