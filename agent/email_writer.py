"""LLM email generation — one API call per segment, personalised per contact."""
import json
import re

import anthropic

import agent.storage as storage
from agent import MODEL
from agent.tracer import AgentTracer

_SYSTEM_PROMPT = """You are an expert B2B copywriter specialising in personalised cold outreach.

For each contact provided, write a personalised email that:
- Opens with something specific to that person (role, company size, activity, or a note detail)
- Delivers clear, relevant value — no generic pitches
- Has one low-pressure, concrete call-to-action
- Stays under 180 words
- Sounds like it's from a real human named Alex, not a marketing tool

Match tone to seniority: C-suite / VP = brief and strategic; managers = more detailed and tactical.

Return ONLY valid JSON — no markdown fences, no explanation:

{
  "emails": [
    {
      "email": "contact@company.com",
      "subject": "specific, personalised subject line (max 60 chars)",
      "body": "full email body — use \\n for line breaks. Sign off as Alex."
    }
  ]
}

Write an email for every contact in the list."""


def _extract_json(text: str) -> dict:
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


class EmailWriter:
    def __init__(self, client: anthropic.Anthropic, tracer: AgentTracer):
        self.client = client
        self.tracer = tracer

    def generate_for_segment(
        self,
        segment_name: str,
        segment_info: dict,
        contacts: list[dict],
    ) -> list[dict]:
        """Generate personalised emails for every contact in one segment."""
        if not contacts:
            return []

        contacts_text = "\n\n".join(
            f"Contact:\n"
            f"  Email: {c['email']}\n"
            f"  Name: {c['name']}\n"
            f"  Company: {c.get('company', '')}\n"
            f"  Role: {c.get('role', '')}\n"
            f"  Last Activity: {c.get('last_activity', '')}\n"
            f"  Notes: {c.get('notes', '')}"
            for c in contacts
        )

        user_msg = (
            f"Segment: {segment_name}\n"
            f"Who they are: {segment_info.get('description', '')}\n"
            f"Email strategy: {segment_info.get('email_strategy', '')}\n\n"
            f"Contacts ({len(contacts)}):\n{contacts_text}\n\n"
            f"Write one personalised email per contact above."
        )

        with self.tracer.trace(
            "email_generation", f"'{segment_name}': {len(contacts)} contacts"
        ) as entry:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=8192,
                system=[
                    {
                        "type": "text",
                        "text": _SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_msg}],
            )
            entry.tokens_input = response.usage.input_tokens
            entry.tokens_output = response.usage.output_tokens
            entry.model = response.model

            result = _extract_json(response.content[0].text)
            emails = result.get("emails", [])
            entry.output_summary = f"{len(emails)} emails generated"
            return emails

    def generate_all(
        self,
        segments: list[dict],
        assignments: list[dict],
        contacts: list[dict],
    ) -> list[dict]:
        """Generate emails for all actionable segments. Returns flat email list."""
        seg_map = {s["name"]: s for s in segments}
        contact_map = {c["email"]: c for c in contacts}

        by_segment: dict[str, list[dict]] = {}
        for a in assignments:
            if a.get("recommended_action") == "ignore":
                continue
            contact = contact_map.get(a["email"])
            if contact:
                by_segment.setdefault(a["segment"], []).append(contact)

        all_emails: list[dict] = []
        for seg_name, seg_contacts in by_segment.items():
            emails = self.generate_for_segment(
                seg_name, seg_map.get(seg_name, {}), seg_contacts
            )
            for e in emails:
                e["segment_tag"] = seg_name
            all_emails.extend(emails)

        return all_emails

    def persist(self, emails: list[dict], contacts: list[dict]) -> None:
        """Save staged emails to the database."""
        id_map = {c["email"]: c["id"] for c in contacts}
        for e in emails:
            contact_id = id_map.get(e["email"])
            if contact_id:
                storage.save_email(
                    contact_id=int(contact_id),
                    subject=e.get("subject", ""),
                    body=e.get("body", ""),
                    segment_tag=e.get("segment_tag", ""),
                )
