"""Streamlit CRM dashboard for the AI CRM Agent.

Launch:  streamlit run dashboard/app.py
Via CLI: python cli.py dashboard
"""
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

import agent.storage as storage

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI CRM Agent",
    page_icon="robot",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    .seg-pill {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        color: #fff;
    }
    .status-pill {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    div[data-testid="metric-container"] {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 12px 16px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PALETTE = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444",
            "#8b5cf6", "#06b6d4", "#f97316", "#84cc16"]

_ACTION_COLOURS = {"email": "#10b981", "nurture": "#f59e0b", "ignore": "#ef4444"}

_STATUS_COLOURS = {
    "new":       "#6b7280",
    "contacted": "#3b82f6",
    "replied":   "#8b5cf6",
    "converted": "#10b981",
    "ignored":   "#ef4444",
}


@st.cache_data(ttl=2)
def _load_contacts() -> pd.DataFrame:
    return storage.get_contacts()


@st.cache_data(ttl=2)
def _load_log() -> pd.DataFrame:
    return storage.get_execution_log()


def _seg_colour_map(segments: list[str]) -> dict[str, str]:
    return {s: _PALETTE[i % len(_PALETTE)] for i, s in enumerate(sorted(segments))}


# ---------------------------------------------------------------------------
# Welcome / onboarding screen
# ---------------------------------------------------------------------------

def _welcome_screen() -> None:
    st.markdown("# Welcome to AI CRM Agent")
    st.markdown(
        "Segment contacts with Claude, generate personalised emails, "
        "track every LLM call — and send directly from the dashboard."
    )
    st.divider()

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("Upload your own contacts")
        st.caption("CSV with columns: name, email, company, role, last_activity, notes")
        _csv_import_widget(compact=False)

    with col2:
        st.subheader("Try with demo data")
        st.caption("50 synthetic contacts across 4 natural segments — ready in seconds.")
        st.write("")
        if st.button("Generate demo contacts", type="primary", use_container_width=True):
            _run_generate()


# ---------------------------------------------------------------------------
# CSV import
# ---------------------------------------------------------------------------

def _csv_import_widget(compact: bool = True) -> None:
    label = "Upload CSV" if compact else "Choose a CSV file"
    uploaded = st.file_uploader(label, type="csv", key="csv_upload")
    if not uploaded:
        return

    try:
        df = pd.read_csv(uploaded)
    except Exception as exc:
        st.error(f"Could not read CSV: {exc}")
        return

    st.caption(f"Detected {len(df)} rows, {len(df.columns)} columns")
    st.dataframe(df.head(3), use_container_width=True, hide_index=True)

    st.markdown("**Map your columns to the required fields:**")
    cols = ["(skip)"] + df.columns.tolist()

    # Auto-detect best match per field
    def _best_match(field: str) -> int:
        for i, c in enumerate(df.columns):
            if field.lower() in c.lower() or c.lower() in field.lower():
                return i + 1
        return 0

    fields = [
        ("name",          "Full Name *",        True),
        ("email",         "Email Address *",    True),
        ("company",       "Company",            False),
        ("role",          "Job Title / Role",   False),
        ("last_activity", "Last Activity Date", False),
        ("notes",         "Notes",              False),
    ]

    r1, r2 = st.columns(2)
    mappings: dict[str, str] = {}
    for idx, (field, label, required) in enumerate(fields):
        col = r1 if idx % 2 == 0 else r2
        sel = col.selectbox(label, cols, index=_best_match(field), key=f"map_{field}")
        if sel != "(skip)":
            mappings[field] = sel

    missing = [l for f, l, req in fields if req and f not in mappings]
    if missing:
        st.warning(f"Required fields not mapped: {', '.join(missing)}")
        return

    if st.button("Import contacts", type="primary", use_container_width=True):
        _do_csv_import(df, mappings)


def _do_csv_import(df: pd.DataFrame, mappings: dict[str, str]) -> None:
    contacts = []
    for _, row in df.iterrows():
        c = {
            "name":          str(row.get(mappings.get("name", ""), "")).strip(),
            "email":         str(row.get(mappings.get("email", ""), "")).strip().lower(),
            "company":       str(row.get(mappings.get("company", ""), "")).strip() if "company" in mappings else "",
            "role":          str(row.get(mappings.get("role", ""), "")).strip() if "role" in mappings else "",
            "last_activity": str(row.get(mappings.get("last_activity", ""), "")).strip() if "last_activity" in mappings else "",
            "notes":         str(row.get(mappings.get("notes", ""), "")).strip() if "notes" in mappings else "",
        }
        if c["name"] and c["email"]:
            contacts.append(c)

    if not contacts:
        st.error("No valid rows found after mapping.")
        return

    storage.upsert_contacts(contacts)
    _load_contacts.clear()
    st.success(f"Imported {len(contacts)} contacts.")
    st.rerun()


# ---------------------------------------------------------------------------
# Pipeline runners
# ---------------------------------------------------------------------------

def _run_generate() -> None:
    from data.generate_contacts import generate_and_save
    with st.status("Generating synthetic contacts...", expanded=True) as status:
        storage.init_db()
        contacts = generate_and_save()
        storage.upsert_contacts(contacts)
        st.write(f"Created {len(contacts)} contacts.")
        status.update(label=f"Done — {len(contacts)} contacts ready.", state="complete")
    _load_contacts.clear()
    st.rerun()


def _run_pipeline(criteria: str) -> None:
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        st.error(
            "**ANTHROPIC_API_KEY not set.**  \n"
            "Create a `.env` file:  `ANTHROPIC_API_KEY=sk-ant-...`"
        )
        return

    df = storage.get_contacts()
    if df.empty:
        st.warning("No contacts found.")
        return

    import anthropic
    from agent.tracer import AgentTracer
    from agent.segmentation import SegmentationEngine
    from agent.email_writer import EmailWriter

    client = anthropic.Anthropic(api_key=api_key)
    tracer = AgentTracer(storage)

    with st.status("Running agent pipeline...", expanded=True) as status:
        st.write(f"Segmenting **{len(df)} contacts**...")
        engine = SegmentationEngine(client, tracer)
        contacts_list = df.to_dict("records")
        result = engine.run(contacts_list, custom_criteria=criteria or None)
        engine.persist(result["assignments"])
        st.write(f"Found **{len(result['segments'])} segments**")

        st.write("Generating personalised emails...")
        writer = EmailWriter(client, tracer)
        emails = writer.generate_all(result["segments"], result["assignments"], contacts_list)
        writer.persist(emails, storage.get_contacts().to_dict("records"))
        st.write(f"Generated **{len(emails)} emails**")

        s = tracer.summary()
        st.write(
            f"**{s['calls']} API calls** · "
            f"**{s['total_tokens']:,} tokens** · "
            f"**{s['total_latency_ms'] / 1000:.1f}s**"
        )
        status.update(label="Pipeline complete!", state="complete")

    _load_contacts.clear()
    _load_log.clear()
    st.rerun()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def _sidebar() -> tuple[bool, bool, str]:
    with st.sidebar:
        st.markdown("## AI CRM Agent")
        st.caption("Segment · Email · Track")
        st.divider()

        st.subheader("Pipeline")
        criteria = st.text_area(
            "Custom segmentation criteria",
            placeholder="e.g. Focus on enterprise accounts with HIPAA requirements...",
            height=80,
        )
        c1, c2 = st.columns(2)
        run_btn = c1.button("Run Agent", type="primary", use_container_width=True)
        gen_btn = c2.button("Generate Data", use_container_width=True)

        st.divider()
        st.subheader("Import CSV")
        _csv_import_widget(compact=True)

        st.divider()
        df = storage.get_contacts()
        if not df.empty:
            st.metric("Contacts", len(df))
            st.metric("Segmented", f"{int(df['segment'].notna().sum())} / {len(df)}")
            sent = storage.get_all_emails()
            if not sent.empty and "sent_at" in sent.columns:
                n_sent = int(sent["sent_at"].notna().sum())
                st.metric("Emails Sent", n_sent)
            log = storage.get_execution_log()
            if not log.empty:
                st.caption(f"Last run: {log['timestamp'].iloc[0][:16].replace('T',' ')} UTC")
        st.caption(f"Model: {os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-5')}")

    return run_btn, gen_btn, criteria


# ---------------------------------------------------------------------------
# Tab: Contacts
# ---------------------------------------------------------------------------

def _tab_contacts(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No contacts yet — upload a CSV or generate demo data.")
        return

    seg_colour = _seg_colour_map(df["segment"].dropna().unique().tolist())
    st.subheader(f"Contacts ({len(df)})")

    fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 2])
    seg_opts    = ["All"] + sorted(df["segment"].dropna().unique().tolist())
    act_opts    = ["All"] + sorted(df["recommended_action"].dropna().unique().tolist())
    status_opts = ["All"] + sorted(df["status"].dropna().unique().tolist()) if "status" in df.columns else ["All"]
    sel_seg    = fc1.selectbox("Segment", seg_opts, key="flt_seg")
    sel_act    = fc2.selectbox("Action",  act_opts, key="flt_act")
    sel_status = fc3.selectbox("Status",  status_opts, key="flt_status")
    search     = fc4.text_input("Search", placeholder="Name / company...", key="flt_search")

    filt = df.copy()
    if sel_seg    != "All": filt = filt[filt["segment"] == sel_seg]
    if sel_act    != "All": filt = filt[filt["recommended_action"] == sel_act]
    if sel_status != "All": filt = filt[filt["status"] == sel_status]
    if search.strip():
        mask = (
            filt["name"].str.contains(search, case=False, na=False)
            | filt["company"].str.contains(search, case=False, na=False)
        )
        filt = filt[mask]

    show_cols = ["name", "company", "role", "last_activity", "segment",
                 "confidence", "recommended_action", "status"]
    avail = [c for c in show_cols if c in filt.columns]
    tbl = filt[avail].copy()
    if "confidence" in tbl.columns:
        tbl["confidence"] = tbl["confidence"].apply(
            lambda x: f"{x:.0%}" if pd.notna(x) else "—"
        )

    st.dataframe(tbl, use_container_width=True, hide_index=True, height=340)
    st.caption(f"Showing {len(filt)} of {len(df)} contacts")

    # ── Contact detail ────────────────────────────────────────────────────
    st.divider()
    st.subheader("Contact Detail")
    if filt.empty:
        st.info("No contacts match the current filters.")
        return

    chosen = st.selectbox("Select contact", filt["name"].tolist(), label_visibility="collapsed")
    if not chosen:
        return

    row = filt[filt["name"] == chosen].iloc[0]
    contact_id = int(row["id"])

    left, right = st.columns(2)
    with left:
        st.markdown(f"### {row['name']}")
        st.caption(f"{row.get('role', '')}  ·  {row.get('company', '')}")
        st.write(f"**Email:** {row['email']}")
        st.write(f"**Last Activity:** {row.get('last_activity', '—')}")
        notes = row.get("notes", "")
        if notes:
            with st.expander("Notes"):
                st.write(notes)

    with right:
        seg = row.get("segment")
        if pd.notna(seg) and seg:
            colour = seg_colour.get(seg, "#6b7280")
            st.markdown(
                f"**Segment:** <span class='seg-pill' style='background:{colour}'>{seg}</span>",
                unsafe_allow_html=True,
            )
            conf = row.get("confidence")
            if pd.notna(conf):
                st.write(f"**Confidence:** {conf:.0%}")
            action = row.get("recommended_action", "—")
            ac = _ACTION_COLOURS.get(action, "#6b7280")
            st.markdown(
                f"**Action:** <span class='seg-pill' style='background:{ac}'>{action}</span>",
                unsafe_allow_html=True,
            )
            with st.expander("Reasoning"):
                st.write(row.get("segment_reasoning") or "No reasoning stored.")
        else:
            st.info("Not segmented yet — run the agent pipeline.")

        # Status tracker
        current_status = row.get("status", "new") or "new"
        sc = _STATUS_COLOURS.get(current_status, "#6b7280")
        st.markdown(
            f"**Status:** <span class='status-pill' style='background:{sc};color:#fff'>"
            f"{current_status}</span>",
            unsafe_allow_html=True,
        )
        st.write("")
        btn_cols = st.columns(4)
        status_btns = [
            ("Contacted", "contacted"),
            ("Replied",   "replied"),
            ("Converted", "converted"),
            ("Ignored",   "ignored"),
        ]
        for col, (label, val) in zip(btn_cols, status_btns):
            if col.button(label, key=f"status_{contact_id}_{val}",
                          disabled=(current_status == val),
                          use_container_width=True):
                storage.update_contact_status(contact_id, val)
                _load_contacts.clear()
                st.rerun()

    email_rec = storage.get_email_for_contact(contact_id)
    if email_rec:
        st.divider()
        sent_label = (
            f"Sent at {email_rec['sent_at'][:16]}"
            if email_rec.get("sent_at")
            else "Not sent yet"
        )
        st.markdown(f"**Staged Email** — `{email_rec.get('segment_tag', '')}` · {sent_label}")
        st.write(f"**Subject:** {email_rec['subject']}")
        st.text_area("Body", email_rec["body"], height=200, disabled=True, key=f"body_{contact_id}")


# ---------------------------------------------------------------------------
# Tab: Analytics
# ---------------------------------------------------------------------------

def _tab_analytics(df: pd.DataFrame) -> None:
    seg_df = df.dropna(subset=["segment"])
    if seg_df.empty:
        st.info("Run the agent pipeline to see analytics.")
        return

    seg_colour = _seg_colour_map(seg_df["segment"].unique().tolist())

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Segments Found",  seg_df["segment"].nunique())
    k2.metric("Ready to Email",  int((seg_df["recommended_action"] == "email").sum()))
    k3.metric("To Nurture",      int((seg_df["recommended_action"] == "nurture").sum()))
    avg_c = seg_df["confidence"].mean()
    k4.metric("Avg Confidence",  f"{avg_c:.0%}" if pd.notna(avg_c) else "—")

    st.divider()
    c1, c2 = st.columns(2)

    with c1:
        counts = seg_df["segment"].value_counts().reset_index()
        counts.columns = ["Segment", "Count"]
        fig = px.pie(counts, values="Count", names="Segment",
                     title="Contacts by Segment", color="Segment",
                     color_discrete_map=seg_colour, hole=0.35)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        act = (seg_df.groupby(["segment", "recommended_action"])
               .size().reset_index(name="count"))
        fig2 = px.bar(act, x="segment", y="count", color="recommended_action",
                      title="Recommended Actions by Segment",
                      color_discrete_map=_ACTION_COLOURS, barmode="stack")
        fig2.update_layout(legend_title="Action", xaxis_tickangle=-20,
                           margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(fig2, use_container_width=True)

    conf_df = seg_df.dropna(subset=["confidence"])
    if not conf_df.empty:
        fig3 = px.box(conf_df, x="segment", y="confidence", color="segment",
                      color_discrete_map=seg_colour,
                      title="Confidence Score Distribution by Segment", points="all")
        fig3.update_layout(showlegend=False, xaxis_tickangle=-20)
        st.plotly_chart(fig3, use_container_width=True)

    # Status breakdown
    if "status" in df.columns:
        st.subheader("Contact Status")
        status_counts = df["status"].fillna("new").value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        fig4 = px.bar(status_counts, x="Status", y="Count",
                      title="Contacts by Status", color="Status",
                      color_discrete_map=_STATUS_COLOURS)
        fig4.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(fig4, use_container_width=True)

    st.subheader("Segment Summary")
    summary = (
        seg_df.groupby("segment").agg(
            contacts      =("email",              "count"),
            avg_confidence=("confidence",         "mean"),
            email_count   =("recommended_action", lambda x: (x == "email").sum()),
            nurture_count =("recommended_action", lambda x: (x == "nurture").sum()),
            ignore_count  =("recommended_action", lambda x: (x == "ignore").sum()),
        ).reset_index()
    )
    summary["avg_confidence"] = summary["avg_confidence"].apply(
        lambda x: f"{x:.0%}" if pd.notna(x) else "—"
    )
    summary.columns = ["Segment", "Contacts", "Avg Confidence", "Email", "Nurture", "Ignore"]
    st.dataframe(summary, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Tab: Staged Emails
# ---------------------------------------------------------------------------

def _tab_emails(df: pd.DataFrame) -> None:
    seg_df = df.dropna(subset=["segment"])
    if seg_df.empty:
        st.info("Run the agent pipeline to generate emails.")
        return

    seg_opts = ["All"] + sorted(seg_df["segment"].unique().tolist())
    sel_seg  = st.selectbox("Filter by Segment", seg_opts, key="email_seg")

    target = seg_df if sel_seg == "All" else seg_df[seg_df["segment"] == sel_seg]

    rows = []
    for _, r in target.iterrows():
        e = storage.get_email_for_contact(int(r["id"]))
        if e:
            rows.append({
                "name":        r["name"],
                "email":       r["email"],
                "company":     r["company"],
                "segment":     r["segment"],
                "subject":     e["subject"],
                "body":        e["body"],
                "sent_at":     e.get("sent_at") or "",
                "generated_at": (e.get("generated_at") or "")[:16],
            })

    if not rows:
        st.info("No staged emails yet.")
        return

    emails_df = pd.DataFrame(rows)
    n_sent    = int((emails_df["sent_at"] != "").sum())

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Total Staged", len(rows))
    mc2.metric("Sent",         n_sent)
    mc3.metric("Unsent",       len(rows) - n_sent)

    dl_col, _ = st.columns([1, 3])
    dl_col.download_button(
        "Export CSV",
        data=emails_df.to_csv(index=False),
        file_name=f"staged_emails_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.divider()
    seg_colour = _seg_colour_map(emails_df["segment"].unique().tolist())
    for e in rows:
        sent_badge = " SENT" if e["sent_at"] else ""
        with st.expander(f"{e['name']} ({e['company']}) — {e['subject'][:55]}{sent_badge}"):
            colour = seg_colour.get(e["segment"], "#6b7280")
            st.markdown(
                f"<span class='seg-pill' style='background:{colour}'>{e['segment']}</span>  "
                f"{'Sent: ' + e['sent_at'][:16] if e['sent_at'] else 'Not sent'}",
                unsafe_allow_html=True,
            )
            st.caption(f"To: {e['email']}  ·  Generated: {e['generated_at']}")
            st.write(f"**Subject:** {e['subject']}")
            st.divider()
            st.text(e["body"])


# ---------------------------------------------------------------------------
# Tab: Agent Log
# ---------------------------------------------------------------------------

def _tab_log(log_df: pd.DataFrame) -> None:
    if log_df.empty:
        st.info("No execution log yet — run the agent pipeline.")
        return

    k1, k2, k3, k4 = st.columns(4)
    total_tokens = (log_df["tokens_input"].fillna(0) + log_df["tokens_output"].fillna(0)).sum()
    k1.metric("API Calls",    len(log_df))
    k2.metric("Total Tokens", f"{int(total_tokens):,}")
    k3.metric("Avg Latency",  f"{log_df['latency_ms'].mean():.0f} ms")
    k4.metric("Errors",       int((log_df["status"] == "error").sum()))

    st.divider()
    recent = log_df.head(30).copy().reset_index(drop=True)
    recent.index = recent.index + 1

    fig = px.bar(recent, x=recent.index, y="latency_ms", color="operation",
                 title="Latency per API Call (last 30)",
                 labels={"latency_ms": "Latency (ms)", "x": "Call #"},
                 color_discrete_sequence=_PALETTE)
    fig.update_layout(legend_title="Operation", margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)

    tok = recent[["tokens_input", "tokens_output"]].copy()
    tok.index = recent.index
    tok_long = tok.reset_index().melt(id_vars="index", var_name="type", value_name="tokens")
    fig2 = px.bar(tok_long, x="index", y="tokens", color="type",
                  title="Token Usage per Call",
                  labels={"index": "Call #", "tokens": "Tokens"},
                  color_discrete_map={"tokens_input": "#3b82f6", "tokens_output": "#10b981"},
                  barmode="stack")
    fig2.update_layout(margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Raw Trace")
    show_cols = ["timestamp", "operation", "input_summary", "output_summary",
                 "tokens_input", "tokens_output", "latency_ms", "status", "model"]
    avail   = [c for c in show_cols if c in log_df.columns]
    display = log_df[avail].copy()
    if "latency_ms"  in display.columns:
        display["latency_ms"]  = display["latency_ms"].apply(lambda x: f"{x:.0f} ms" if pd.notna(x) else "—")
    if "timestamp"   in display.columns:
        display["timestamp"]   = display["timestamp"].str[:19].str.replace("T", " ")
    st.dataframe(display, use_container_width=True, hide_index=True, height=300)


# ---------------------------------------------------------------------------
# Tab: Settings (SMTP)
# ---------------------------------------------------------------------------

def _tab_settings() -> None:
    st.subheader("Email Settings (SMTP)")
    st.caption(
        "Send staged emails directly from this dashboard. "
        "Works with Gmail App Passwords, Outlook, or any SMTP server."
    )

    with st.expander("Gmail setup guide", expanded=False):
        st.markdown("""
1. Enable **2-Step Verification**: [myaccount.google.com/security](https://myaccount.google.com/security)
2. Create an **App Password**: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Select app: **Mail** · device: **Other** → copy the 16-character password
4. Paste it as `SMTP_PASSWORD` in your `.env` file (or fill in the fields below)
        """)

    from dotenv import load_dotenv
    load_dotenv()

    st.divider()
    c1, c2 = st.columns(2)
    smtp_host = c1.text_input("SMTP Host",     value=os.getenv("SMTP_HOST", "smtp.gmail.com"))
    smtp_port = c2.number_input("SMTP Port",   value=int(os.getenv("SMTP_PORT", "587")), step=1)
    smtp_user = c1.text_input("Email Address", value=os.getenv("SMTP_USER", ""),
                               placeholder="you@gmail.com")
    smtp_pass = c2.text_input("App Password",  value=os.getenv("SMTP_PASSWORD", ""),
                               type="password", placeholder="xxxx xxxx xxxx xxxx")
    from_name = st.text_input("From Name",     value=os.getenv("SMTP_FROM_NAME", "Alex"),
                               help="Shown as the sender name in the email client")

    from agent.email_sender import SMTPConfig, EmailSender
    config = SMTPConfig(
        host=smtp_host, port=int(smtp_port),
        user=smtp_user, password=smtp_pass, from_name=from_name,
    )
    sender = EmailSender(config)

    t1, t2 = st.columns(2)
    if t1.button("Test Connection", use_container_width=True):
        if not config.is_configured():
            st.warning("Fill in email address and password first.")
        else:
            with st.spinner("Connecting..."):
                ok, msg = sender.test_connection()
            (st.success if ok else st.error)(msg)

    st.divider()
    st.subheader("Send Staged Emails")

    unsent = storage.get_unsent_emails()
    all_emails = storage.get_all_emails()
    n_sent   = int(all_emails["sent_at"].notna().sum()) if not all_emails.empty and "sent_at" in all_emails.columns else 0
    n_unsent = len(unsent)

    mc1, mc2 = st.columns(2)
    mc1.metric("Ready to Send", n_unsent)
    mc2.metric("Already Sent",  n_sent)

    dry_run = st.checkbox(
        "Dry run (simulate sending — no emails actually sent)",
        value=True,
        help="Uncheck this when you are ready to send for real.",
    )

    if n_unsent == 0:
        st.info("No unsent emails. Run the agent pipeline to generate them.")
    elif not config.is_configured():
        st.warning("Configure SMTP credentials above before sending.")
    else:
        action_label = f"Dry Run ({n_unsent} emails)" if dry_run else f"Send {n_unsent} Emails"
        if t2.button(action_label, type="primary", use_container_width=True):
            with st.spinner("Sending..." if not dry_run else "Simulating..."):
                results = sender.send_all(dry_run=dry_run)

            if results["failed"] == 0:
                st.success(
                    f"{'Simulated' if dry_run else 'Sent'} {results['sent']} emails successfully."
                )
            else:
                st.warning(
                    f"{results['sent']} sent, {results['failed']} failed."
                )
                for err in results["errors"]:
                    st.caption(f"  - {err}")

            if not dry_run:
                _load_contacts.clear()
                st.rerun()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    storage.init_db()
    run_clicked, gen_clicked, criteria = _sidebar()

    if gen_clicked:
        _run_generate()
    if run_clicked:
        _run_pipeline(criteria)

    df     = _load_contacts()
    log_df = _load_log()

    # Segment diff banner
    if "prev_segments" in st.session_state and not df.empty:
        curr = set(df["segment"].dropna().unique())
        prev = set(st.session_state["prev_segments"])
        if curr != prev:
            new  = curr - prev
            gone = prev - curr
            parts = []
            if new:  parts.append(f"**New:** {', '.join(sorted(new))}")
            if gone: parts.append(f"**Removed:** {', '.join(sorted(gone))}")
            st.info("Segmentation changed since last run.  " + "  ·  ".join(parts))
    if not df.empty:
        st.session_state["prev_segments"] = list(df["segment"].dropna().unique())

    # Show welcome screen if no contacts loaded yet
    if df.empty:
        st.markdown("# AI CRM Agent")
        st.divider()
        _welcome_screen()
        return

    st.markdown("# AI CRM Agent")
    st.caption("Segment contacts with Claude · Generate personalised emails · Send and track")
    st.divider()

    tabs = st.tabs(["Contacts", "Analytics", "Staged Emails", "Agent Log", "Settings"])

    with tabs[0]: _tab_contacts(df)
    with tabs[1]: _tab_analytics(df)
    with tabs[2]: _tab_emails(df)
    with tabs[3]: _tab_log(log_df)
    with tabs[4]: _tab_settings()


if __name__ == "__main__":
    main()
