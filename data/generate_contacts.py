"""Generate 50 realistic synthetic contacts for the AI CRM demo.

The contacts span several natural behavioural/firmographic clusters — the
exact groupings are intentionally *not* labelled here so the LLM can
discover them from the data.
"""
import csv
from datetime import datetime, timedelta
from pathlib import Path

_DATA_DIR = Path(__file__).parent
_CSV_PATH = _DATA_DIR / "contacts.csv"
_FIELDS = ["name", "email", "company", "role", "last_activity", "notes"]


def _ago(days: int) -> str:
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Raw contact definitions — 50 profiles across four natural clusters.
# Cluster A: Large-org decision-makers, very recent activity, deal in motion.
# Cluster B: Early-stage startup founders, active recently, price-sensitive.
# Cluster C: Mid-market evaluators, slower procurement, multi-stakeholder.
# Cluster D: Cold / dormant / disqualified — various reasons for going quiet.
# ---------------------------------------------------------------------------

def _contacts() -> list[dict]:
    return [

        # ── Cluster A: Enterprise deal in motion ──────────────────────────

        {
            "name": "Sarah Chen",
            "email": "sarah.chen@apexanalytics.com",
            "company": "Apex Analytics",
            "role": "VP of Sales Operations",
            "last_activity": _ago(3),
            "notes": (
                "Attended our enterprise pricing webinar and requested a custom proposal. "
                "Confirmed Q3 budget is allocated for this initiative. "
                "Decision authority over a 600-person sales org; wants to replace a legacy Salesforce add-on."
            ),
        },
        {
            "name": "Marcus Johnson",
            "email": "m.johnson@meridianfinancial.io",
            "company": "Meridian Financial",
            "role": "Chief Technology Officer",
            "last_activity": _ago(5),
            "notes": (
                "Completed a full platform demo, praised the API design. "
                "Evaluating for an 800-person engineering organisation. "
                "Asked specifically about SOC 2 compliance and on-premise deployment options."
            ),
        },
        {
            "name": "Elena Vasquez",
            "email": "evasquez@globalmeds.com",
            "company": "GlobalMed Systems",
            "role": "SVP of Operations",
            "last_activity": _ago(7),
            "notes": (
                "Three stakeholder calls completed including CISO and CFO. "
                "Compliance requirements have been mapped to our feature set. "
                "Procurement team has been engaged and is running a formal vendor assessment."
            ),
        },
        {
            "name": "David Park",
            "email": "dpark@terrascalecorp.com",
            "company": "TerraScale Corp",
            "role": "VP of Engineering",
            "last_activity": _ago(2),
            "notes": (
                "POC completed last week; results exceeded internal benchmarks by 40%. "
                "Now building the business case for CFO sign-off. "
                "Mentioned a competitor is also in the running but their POC underperformed."
            ),
        },
        {
            "name": "Rachel Torres",
            "email": "r.torres@nexgenretail.com",
            "company": "NexGen Retail",
            "role": "Chief Revenue Officer",
            "last_activity": _ago(1),
            "notes": (
                "NDA signed, pricing discussion started for a 1,000+ seat deal. "
                "On a fast track — internal deadline to decide before end of quarter. "
                "Has executive sponsor support at board level."
            ),
        },
        {
            "name": "James Okafor",
            "email": "j.okafor@continuumins.com",
            "company": "Continuum Insurance",
            "role": "Director of IT",
            "last_activity": _ago(10),
            "notes": (
                "IT security review passed with no major findings. "
                "Stakeholder alignment meeting scheduled for next week. "
                "Wants a phased rollout starting with a 200-seat pilot."
            ),
        },
        {
            "name": "Patricia Williams",
            "email": "pwilliams@quantumdynamics.co",
            "company": "Quantum Dynamics",
            "role": "VP of Product",
            "last_activity": _ago(4),
            "notes": (
                "Submitted a detailed feature request list after the second demo. "
                "Integration architecture reviewed with our solutions team — no blockers found. "
                "Has an internal champion in the data engineering team."
            ),
        },
        {
            "name": "Thomas Berg",
            "email": "tberg@nordiclogistics.eu",
            "company": "Nordic Logistics",
            "role": "Head of Digital Transformation",
            "last_activity": _ago(6),
            "notes": (
                "Pilot programme approved by the board last month. "
                "Discussing implementation timeline; wants go-live by Q4. "
                "Company is 1,200 employees across five countries."
            ),
        },
        {
            "name": "Aisha Patel",
            "email": "a.patel@fortisbank.com",
            "company": "Fortis Bank",
            "role": "Senior Director of Analytics",
            "last_activity": _ago(8),
            "notes": (
                "Data governance requirements documented and approved internally. "
                "CISO has signed off on the security review. "
                "Procurement now comparing contract terms; finalising SLA requirements."
            ),
        },
        {
            "name": "Robert Kim",
            "email": "rkim@pacifichealthnetwork.org",
            "company": "Pacific Health Network",
            "role": "EVP Technology",
            "last_activity": _ago(12),
            "notes": (
                "Contract redlines in progress between legal teams. "
                "Scoping a 3-year enterprise agreement with optional expansion clauses. "
                "Key concern is HIPAA compliance — already addressed in our BAA template."
            ),
        },
        {
            "name": "Naomi Suzuki",
            "email": "naomi.suzuki@titansoftware.com",
            "company": "Titan Software",
            "role": "VP of Customer Success",
            "last_activity": _ago(9),
            "notes": (
                "Expanding from current 200-seat deployment to 800 seats. "
                "Success metrics and KPIs defined in a shared doc. "
                "Reference call completed with a peer at a similar company — very positive."
            ),
        },
        {
            "name": "Carlos Mendez",
            "email": "cmendez@metrocitygroup.com",
            "company": "MetroCity Group",
            "role": "Chief Digital Officer",
            "last_activity": _ago(14),
            "notes": (
                "Executive sponsor identified and briefed. "
                "Integration roadmap was presented to the board last week. "
                "Wants to sign before fiscal year-end; legal review is the remaining gate."
            ),
        },

        # ── Cluster B: Growth-stage startup founders ───────────────────────

        {
            "name": "Jake Thornton",
            "email": "jake@loopcraft.io",
            "company": "Loopcraft",
            "role": "CEO & Co-founder",
            "last_activity": _ago(18),
            "notes": (
                "Met at Y Combinator demo day. Excited about automation possibilities. "
                "Currently on free tier, building a prototype workflow. "
                "8-person team, pre-Series A, price-sensitive but willing to pay for the right tool."
            ),
        },
        {
            "name": "Priya Anand",
            "email": "priya@datasprout.ai",
            "company": "DataSprout",
            "role": "Founder & CEO",
            "last_activity": _ago(22),
            "notes": (
                "Free-trial user who built a working prototype in three days. "
                "12-person company, just closed seed round. "
                "Asked whether we have a startup discount programme."
            ),
        },
        {
            "name": "Kevin Liu",
            "email": "kevin@stackwise.dev",
            "company": "Stackwise",
            "role": "Co-founder & CTO",
            "last_activity": _ago(15),
            "notes": (
                "Series A closed last month — team growing from 6 to 25 over the next year. "
                "Evaluating tools now before the hiring wave hits. "
                "Technical founder who read our API docs and asked smart integration questions."
            ),
        },
        {
            "name": "Mia Hernandez",
            "email": "mia@fluxboard.co",
            "company": "Fluxboard",
            "role": "CEO",
            "last_activity": _ago(30),
            "notes": (
                "Raised $2M seed two months ago, found product-market fit. "
                "Wants to systematise outreach before hiring a sales team. "
                "20-person company, moving fast, asked about onboarding timeline."
            ),
        },
        {
            "name": "Samuel Osei",
            "email": "samuel@buildkitlabs.com",
            "company": "Buildkit Labs",
            "role": "Founder",
            "last_activity": _ago(19),
            "notes": (
                "Solo founder wearing many hats — values simplicity above all else. "
                "4-person bootstrapped team; no VC funding. "
                "Free tier user for 3 months, engages with product updates on LinkedIn."
            ),
        },
        {
            "name": "Alyssa Kim",
            "email": "alyssa@parcel.app",
            "company": "Parcel",
            "role": "CEO",
            "last_activity": _ago(25),
            "notes": (
                "Series A fundraise imminent — term sheets being reviewed. "
                "15-person team, wants to set up repeatable processes before scaling. "
                "Mentioned they tried a competitor but found it too complex for their team."
            ),
        },
        {
            "name": "Raj Malhotra",
            "email": "raj@clearbridgeai.com",
            "company": "Clearbridge AI",
            "role": "Co-founder & CTO",
            "last_activity": _ago(28),
            "notes": (
                "Impressed by the API, started building a custom integration as a side project. "
                "9-person company, AI-native. "
                "Asked about developer-tier pricing and whether we offer usage-based billing."
            ),
        },
        {
            "name": "Nina Foster",
            "email": "nina@waveline.co",
            "company": "Waveline",
            "role": "Founder",
            "last_activity": _ago(20),
            "notes": (
                "Referred by an existing customer who spoke highly of us. "
                "Quick to implement — deployed a trial workflow in 48 hours. "
                "11-person startup, asked about white-label options for reselling to their clients."
            ),
        },
        {
            "name": "Chris Adeyemi",
            "email": "chris@springboard-analytics.com",
            "company": "Springboard Analytics",
            "role": "CTO",
            "last_activity": _ago(35),
            "notes": (
                "Technical founder, reviewed API docs thoroughly, has a strong internal champion. "
                "7-person team, bootstrapped, risk-averse about adding new subscriptions. "
                "Hasn't responded since initial inquiry but still opens our emails."
            ),
        },
        {
            "name": "Sophie Larsson",
            "email": "sophie@mintflow.io",
            "company": "Mintflow",
            "role": "CEO",
            "last_activity": _ago(17),
            "notes": (
                "Actively comparing three vendors, price is the primary decision factor. "
                "22-person company, post-seed. "
                "Asked for customer case studies from companies at a similar stage."
            ),
        },
        {
            "name": "Ben Goldstein",
            "email": "ben@auxilio.io",
            "company": "Auxilio",
            "role": "Founder",
            "last_activity": _ago(32),
            "notes": (
                "Building B2B SaaS, wants automation infrastructure from day one. "
                "5-person pre-revenue team, budget is very tight. "
                "Engaged on every product announcement email we've sent."
            ),
        },
        {
            "name": "Zoe Chen",
            "email": "zoe@resonancehq.com",
            "company": "Resonance",
            "role": "Co-founder",
            "last_activity": _ago(27),
            "notes": (
                "Growth mode — team expanding from 18 to 40 over the next 6 months. "
                "Asked about flexible per-seat pricing and volume discounts. "
                "Series A just closed, has budget but wants a good deal."
            ),
        },

        # ── Cluster C: Mid-market in slow procurement ──────────────────────

        {
            "name": "Mark Davidson",
            "email": "mdavidson@riversideconsulting.com",
            "company": "Riverside Consulting",
            "role": "Operations Manager",
            "last_activity": _ago(45),
            "notes": (
                "In a formal vendor selection process with three competing tools. "
                "85-person company, committee decision expected in Q4. "
                "Has been thorough in evaluation but moves slowly due to internal process."
            ),
        },
        {
            "name": "Lindsey Park",
            "email": "lpark@criterionsoftware.com",
            "company": "Criterion Software",
            "role": "Senior Product Manager",
            "last_activity": _ago(38),
            "notes": (
                "Ran multiple internal demos to different stakeholders. "
                "150-person company — waiting for legal to review the contract terms. "
                "Legal review has been queued for three weeks with no update."
            ),
        },
        {
            "name": "Greg Morris",
            "email": "g.morris@clearwatermedia.net",
            "company": "Clearwater Media",
            "role": "Head of Marketing Operations",
            "last_activity": _ago(50),
            "notes": (
                "Attended our webinar six weeks ago and downloaded the ROI calculator. "
                "200-person company; hasn't responded to two follow-up emails since. "
                "LinkedIn profile shows they've been posting about team changes."
            ),
        },
        {
            "name": "Jennifer Walsh",
            "email": "jwalsh@highlandeducation.org",
            "company": "Highland Education",
            "role": "Director of Operations",
            "last_activity": _ago(42),
            "notes": (
                "Budget approved but procurement is running behind schedule. "
                "120-person non-profit, this initiative is queued behind two other projects. "
                "Very interested in the product but blocked by internal process."
            ),
        },
        {
            "name": "Alex Nguyen",
            "email": "anguyen@bayshoremfg.com",
            "company": "Bayshore Manufacturing",
            "role": "Senior IT Manager",
            "last_activity": _ago(55),
            "notes": (
                "IT architecture review in progress, needs internal approval from VP of IT. "
                "300-person manufacturing company with complex on-prem requirements. "
                "Has not been responsive in the last month."
            ),
        },
        {
            "name": "Donna Mitchell",
            "email": "dmitchell@crestlinehc.com",
            "company": "Crestline Healthcare",
            "role": "VP of Marketing",
            "last_activity": _ago(40),
            "notes": (
                "Strong internal champion but needs sign-off from a new VP who joined last month. "
                "180-person company undergoing a leadership transition. "
                "Mentioned the process should settle down in about 6 weeks."
            ),
        },
        {
            "name": "Paul Chen",
            "email": "pchen@graystonefinancial.com",
            "company": "Graystone Financial",
            "role": "Business Analyst",
            "last_activity": _ago(60),
            "notes": (
                "Building an internal ROI case; requested reference customers in financial services. "
                "250-person company, slow procurement cycle typical for the sector. "
                "Provided two references — hasn't followed up after that."
            ),
        },
        {
            "name": "Michelle Turner",
            "email": "mturner@ironwooddist.com",
            "company": "Ironwood Distribution",
            "role": "Director of Sales",
            "last_activity": _ago(48),
            "notes": (
                "Second meeting completed, requirements gathering document shared. "
                "95-person company, decision-making is slow due to committee involvement. "
                "Positive signals but no urgency."
            ),
        },
        {
            "name": "Nathan Davis",
            "email": "ndavis@suncoastenergy.com",
            "company": "Suncoast Energy",
            "role": "IT Director",
            "last_activity": _ago(35),
            "notes": (
                "Security questionnaire submitted two weeks ago. "
                "Waiting on internal vendor assessment team who reviews all new SaaS tools. "
                "400-person utility company, process is thorough but slow."
            ),
        },
        {
            "name": "Rebecca Collins",
            "email": "rcollins@lakewoodrealty.com",
            "company": "Lakewood Real Estate",
            "role": "Marketing Manager",
            "last_activity": _ago(65),
            "notes": (
                "Downloaded ROI calculator and our case study PDF two months ago. "
                "70-person company, no response since despite three follow-up attempts. "
                "LinkedIn activity suggests she's still in the same role."
            ),
        },
        {
            "name": "Tom Reynolds",
            "email": "treynolds@hillcrestmedia.co",
            "company": "Hillcrest Media",
            "role": "Head of Growth",
            "last_activity": _ago(44),
            "notes": (
                "Initially engaged well, but a competitor won a pilot project two months ago. "
                "130-person media company; mentioned they may revisit our product next year. "
                "Worth keeping warm but no near-term opportunity."
            ),
        },
        {
            "name": "Diana Flores",
            "email": "dflores@cascadesystems.com",
            "company": "Cascade Systems",
            "role": "Product Owner",
            "last_activity": _ago(58),
            "notes": (
                "Multiple demos with positive feedback but internal alignment is painfully slow. "
                "220-person company, product and ops teams have conflicting priorities. "
                "Has been a champion but can't get buy-in from her director."
            ),
        },

        # ── Cluster D: Cold, dormant, or disqualified ──────────────────────

        {
            "name": "Steven Clarke",
            "email": "sclarke@barringtoncorp.com",
            "company": "Barrington Corp",
            "role": "VP of Marketing",
            "last_activity": _ago(180),
            "notes": (
                "Was very interested six months ago but cited a budget freeze after company restructuring. "
                "500-person company that went through significant layoffs in Q1. "
                "No response to two re-engagement emails sent in the past two months."
            ),
        },
        {
            "name": "Amy Powell",
            "email": "apowell@thorntongroup.co",
            "company": "Thornton Group",
            "role": "Operations Director",
            "last_activity": _ago(200),
            "notes": (
                "Three meetings held over two months, then contact stopped abruptly. "
                "300-person company; industry rumour is they signed with a competitor. "
                "No confirmation received despite a direct follow-up."
            ),
        },
        {
            "name": "Richard Lee",
            "email": "rlee@streamlineservices.com",
            "company": "Streamline Services",
            "role": "CTO",
            "last_activity": _ago(240),
            "notes": (
                "Completed a technical deep dive and then went completely silent eight months ago. "
                "100-person company; LinkedIn shows he may have left the organisation. "
                "No other contact identified at the company."
            ),
        },
        {
            "name": "Sandra Ross",
            "email": "s.ross@pinnaclesolutions.net",
            "company": "Pinnacle Solutions",
            "role": "VP of Sales",
            "last_activity": _ago(150),
            "notes": (
                "Showed strong interest but the company was acquired five months ago. "
                "200-person firm now absorbed into a larger parent; unclear on new org structure. "
                "No response since the acquisition was announced."
            ),
        },
        {
            "name": "Michael Grant",
            "email": "mgrant@dawnridgetech.com",
            "company": "Dawnridge Tech",
            "role": "Head of Product",
            "last_activity": _ago(160),
            "notes": (
                "Seemed interested initially, but the company pivoted to a different product direction. "
                "60-person startup, new strategic focus makes our tool no longer relevant. "
                "Politely disengaged five months ago."
            ),
        },
        {
            "name": "Laura Kim",
            "email": "laura.kim@bridgewayconsulting.com",
            "company": "Bridgeway Consulting",
            "role": "Marketing Lead",
            "last_activity": _ago(210),
            "notes": (
                "Downloaded three resources including the enterprise guide and a webinar recording. "
                "45-person company; never scheduled a demo despite four outreach attempts. "
                "No indication of why — just never responded."
            ),
        },
        {
            "name": "Derek Johnson",
            "email": "derek@pivotlabs.io",
            "company": "Pivotlabs",
            "role": "Founder",
            "last_activity": _ago(270),
            "notes": (
                "Started a free trial nine months ago, had low engagement metrics throughout. "
                "8-person startup; website now shows a 'coming soon' page — possibly pivoting or defunct. "
                "No response to any outreach in six months."
            ),
        },
        {
            "name": "Christine Hall",
            "email": "chall@westgatefinancial.com",
            "company": "Westgate Financial",
            "role": "Sales Manager",
            "last_activity": _ago(130),
            "notes": (
                "Was enthusiastic in the initial call, but her team was subsequently downsized. "
                "180-person firm, deal fell through when headcount reductions removed the budget owner. "
                "Sent a polite 'not this year' email four months ago."
            ),
        },
        {
            "name": "Brian Smith",
            "email": "bsmith@northshoreindustries.com",
            "company": "Northshore Industries",
            "role": "IT Manager",
            "last_activity": _ago(190),
            "notes": (
                "Submitted an inquiry via the website form, never responded to our reply. "
                "90-person manufacturing company. "
                "Likely a low-intent form fill; no qualifying information provided."
            ),
        },
        {
            "name": "Amanda White",
            "email": "awhite@crossroadslogistics.co",
            "company": "Crossroads Logistics",
            "role": "COO",
            "last_activity": _ago(175),
            "notes": (
                "Was evaluating before going on maternity leave six months ago. "
                "75-person company; a new COO was brought in and the evaluation context was lost. "
                "New COO has not been responsive to re-engagement attempts."
            ),
        },
        {
            "name": "Kevin O'Brien",
            "email": "kobrien@shorelinemcs.com",
            "company": "Shoreline Systems",
            "role": "Head of Engineering",
            "last_activity": _ago(220),
            "notes": (
                "Downloaded the trial and created an account, but never completed the setup wizard. "
                "150-person company; engagement score was the lowest in our cohort from that period. "
                "No meaningful activity in seven months."
            ),
        },
        {
            "name": "Paula Garcia",
            "email": "pgarcia@coastalcapital.com",
            "company": "Coastal Capital",
            "role": "Director of Finance",
            "last_activity": _ago(145),
            "notes": (
                "Budget discussion was positive but no movement in five months. "
                "400-person financial services firm; she does not appear to be the actual decision-maker. "
                "Three attempts to set up a meeting with her VP have been ignored."
            ),
        },
        {
            "name": "Eric Thompson",
            "email": "ethompson@ashgrovemanufacturing.com",
            "company": "Ashgrove Manufacturing",
            "role": "VP of Operations",
            "last_activity": _ago(160),
            "notes": (
                "Evaluated the platform 18 months ago and chose a competitor. "
                "600-person company; competitor contract is likely up for renewal within 6–12 months. "
                "Flagged as a potential re-engagement target in the future."
            ),
        },
        {
            "name": "Jennifer Moore",
            "email": "jmoore@redwoodenterprises.com",
            "company": "Redwood Enterprises",
            "role": "Sales Representative",
            "last_activity": _ago(300),
            "notes": (
                "Generic website inquiry; follow-up revealed they were looking for a CRM, not automation. "
                "50-person company, wrong ICP — never qualified past the first call. "
                "Removed from active pipeline 10 months ago."
            ),
        },
    ]


def generate_and_save() -> list[dict]:
    """Build the contact list and save to CSV. Returns the list of dicts."""
    contacts = _contacts()
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(contacts)
    return contacts


def load_from_csv() -> list[dict]:
    """Load contacts from the CSV file."""
    if not _CSV_PATH.exists():
        raise FileNotFoundError(f"Contacts CSV not found: {_CSV_PATH}")
    with open(_CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    rows = generate_and_save()
    print(f"Generated {len(rows)} contacts → {_CSV_PATH}")
