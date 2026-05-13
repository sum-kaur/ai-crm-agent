# AI CRM Agent

An end-to-end AI workflow that ingests contacts, uses Claude to discover natural
audience segments, writes a personalised email for every contact, and surfaces
everything in a lightweight CRM dashboard — no human sorting required.

---

## Why this exists

Sales and marketing teams waste hours manually triaging contact lists: who's ready
to buy, who needs nurturing, who should be ignored.  This project automates that
entire workflow.  The LLM reads the raw behavioural and firmographic signals in each
contact's profile — activity recency, company size, role seniority, conversation
notes — and **discovers** the segments itself.  No predefined buckets, no hard-coded
rules.  The segments that emerge are the ones actually present in the data.

Real-world equivalents of this pattern:
- Segmenting a B2B pipeline into *enterprise deals in motion*, *growth-stage founders*,
  *slow procurement evaluators*, and *cold / churned* contacts
- Personalising post-event follow-up across 500+ attendees
- Routing inbound leads to the right sequence without a RevOps team

Everything runs locally.  No external services beyond the Anthropic API.
Synthetic data is included so you can clone and demo it immediately.

---

## Architecture

```
ai-crm-agent/
├── agent/
│   ├── segmentation.py   # LLM segmentation engine
│   ├── email_writer.py   # LLM personalised email generation
│   ├── tracer.py         # execution log (wraps every API call)
│   └── storage.py        # SQLite read/write layer
├── data/
│   └── generate_contacts.py   # 50 synthetic contacts (4 natural clusters)
├── dashboard/
│   └── app.py            # Streamlit CRM dashboard
├── cli.py                # pipeline entry point
└── pyproject.toml
```

**Data flow:**

```
contacts.csv  →  SQLite (contacts)
                     │
          SegmentationEngine (Claude)
                     │  returns: segment label, reasoning, confidence, action
                     ▼
            SQLite (contacts + segments)
                     │
           EmailWriter (Claude)
                     │  returns: subject + personalised body per contact
                     ▼
            SQLite (staged_emails)
                     │
           Streamlit dashboard  ←  execution_log (every API call traced)
```

---

## Quick start

### 1. Install

```bash
cd ai-crm-agent
pip install -e .
```

Requires Python 3.11+.

### 2. Configure

```bash
cp .env.example .env
# then edit .env and set your ANTHROPIC_API_KEY
```

### 3. Run the full pipeline

```bash
python cli.py run
```

This will:
1. Generate 50 synthetic contacts and store them in SQLite
2. Send the profiles to Claude for segmentation (emergent segments, not predefined)
3. Generate a personalised email for each contact
4. Print a Rich summary of discovered segments + agent trace

### 4. Open the dashboard

```bash
python cli.py dashboard
# or: streamlit run dashboard/app.py
```

---

## CLI reference

| Command | What it does |
|---|---|
| `python cli.py run` | Full pipeline (generate → segment → emails) |
| `python cli.py run --fresh` | Force-regenerate contacts before running |
| `python cli.py run --criteria "..."` | Pass custom segmentation focus to Claude |
| `python cli.py run --skip-emails` | Segmentation only, skip email generation |
| `python cli.py generate` | Generate/refresh synthetic contacts only |
| `python cli.py segment` | Re-run segmentation on existing contacts |
| `python cli.py dashboard` | Launch the Streamlit dashboard |

---

## Dashboard features

| Tab | What you see |
|---|---|
| **Contacts** | Filterable table · Segment + action badges · Click-to-expand contact detail with staged email |
| **Analytics** | Segment distribution (pie) · Action breakdown by segment (stacked bar) · Confidence score box plots · Segment summary table |
| **Staged Emails** | Browse emails by segment · Full subject + body preview · Export all to CSV |
| **Agent Log** | Every LLM call: operation, latency, token usage · Latency bar chart · Token usage per call |

The **Run Agent** button in the sidebar triggers the full pipeline with live
status updates.  A custom segmentation criteria input lets you re-run with a
different focus (e.g. "prioritise HIPAA-sensitive sectors") and the dashboard
shows a diff banner if the segments changed.

---

## What the synthetic data looks like

The 50 contacts are spread across four natural behavioural clusters — but the
labels are never hardcoded.  Claude sees only raw profiles and discovers the
structure:

| What you'd expect Claude to find | Signals in the data |
|---|---|
| Enterprise deals in motion | Large companies, C-suite / VP roles, activity 1–14 days ago, notes mention POCs, budget allocation, legal review |
| Growth-stage founders | Small companies (5–25 people), CEO/CTO/Founder roles, activity 15–35 days ago, notes mention seed/Series A, price sensitivity |
| Mid-market evaluators | Mid-size companies, manager/director roles, activity 35–70 days ago, notes mention committee decisions, procurement process |
| Cold / dormant / disqualified | Mixed, activity 4–12 months ago, notes mention budget freezes, acquisitions, pivots, no response |

Ambiguous contacts are intentionally included (e.g. a startup that just raised a
Series A and is moving fast vs. a startup founder who's been unresponsive for 35
days) to make the segmentation non-trivial.

---

## Extending this

- **Different data source** — swap `generate_contacts.py` for a CSV export from
  HubSpot, Salesforce, or Apollo.  The schema is `name, email, company, role,
  last_activity, notes`.
- **Different segments** — use the "Custom Criteria" input to guide Claude toward
  the segmentation that matters for your use case.
- **Send emails** — replace `storage.save_email()` with a call to SendGrid /
  Resend / SES.  The staged email JSON is already structured for this.
- **Webhook trigger** — wrap `cli.py run` in a Lambda / Cloud Run function and
  call it from a CRM webhook on new contact creation.

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | — | Your Anthropic API key |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-5` | Override the Claude model |
