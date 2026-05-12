"""Streamlit CRM dashboard for the AI CRM Agent.

Launch with:  streamlit run dashboard/app.py
Or via CLI:   python cli.py dashboard
"""
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Make parent importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import agent.storage as storage

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI CRM Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown(
    """
<style>
    /* Tighten header */
    .block-container { padding-top: 1.5rem; }

    /* Segment colour pills rendered in markdown */
    .seg-pill {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        color: #fff;
    }
    /* Metric box tweak */
    div[data-testid="metric-container"] {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 12px 16px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Colour palette — assigned dynamically per segment name
# ---------------------------------------------------------------------------

_PALETTE = [
    "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
    "#8b5cf6", "#06b6d4", "#f97316", "#84cc16",
]

_ACTION_COLOURS = {
    "email":   "#10b981",
    "nurture": "#f59e0b",
    "ignore":  "#ef4444",
}


@st.cache_data(ttl=2)  # short TTL so the table refreshes after pipeline runs
def _load_contacts() -> pd.DataFrame:
    return storage.get_contacts()


@st.cache_data(ttl=2)
def _load_log() -> pd.DataFrame:
    return storage.get_execution_log()


def _seg_colour_map(segments: list[str]) -> dict[str, str]:
    return {s: _PALETTE[i % len(_PALETTE)] for i, s in enumerate(sorted(segments))}


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def _sidebar() -> tuple[bool, bool, str]:
    """Render sidebar, return (run_clicked, generate_clicked, criteria)."""
    with st.sidebar:
        st.markdown("## 🤖 AI CRM Agent")
        st.caption("Intelligent contact segmentation & personalised outreach")
        st.divider()

        st.subheader("Pipeline Controls")

        criteria = st.text_area(
            "Custom Segmentation Criteria",
            placeholder=(
                "Optional — describe any focus you want.\n"
                "e.g. 'Prioritise enterprise accounts with CISO involvement.'"
            ),
            height=90,
            help="Leave blank to let Claude discover segments automatically.",
        )

        col_run, col_gen = st.columns(2)
        run_clicked = col_run.button(
            "▶ Run Agent",
            type="primary",
            use_container_width=True,
            help="Segment contacts + generate emails",
        )
        gen_clicked = col_gen.button(
            "⟳ Generate Data",
            use_container_width=True,
            help="(Re-)create 50 synthetic contacts",
        )

        st.divider()

        # Quick stats
        df = storage.get_contacts()
        if df.empty:
            st.info("No contacts yet.\nClick **Generate Data** to start.")
        else:
            st.metric("Total Contacts", len(df))
            n_seg = int(df["segment"].notna().sum())
            st.metric("Segmented", f"{n_seg} / {len(df)}")
            log = storage.get_execution_log()
            if not log.empty:
                last_ts = log["timestamp"].iloc[0][:16].replace("T", " ")
                st.caption(f"Last run: {last_ts} UTC")
        st.divider()
        st.caption("Model: " + os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5"))

    return run_clicked, gen_clicked, criteria


# ---------------------------------------------------------------------------
# Pipeline runner (called from sidebar button)
# ---------------------------------------------------------------------------

def _run_pipeline(criteria: str) -> None:
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        st.error(
            "**ANTHROPIC_API_KEY not set.**  \n"
            "Create a `.env` file in the `ai-crm-agent/` directory with:  \n"
            "`ANTHROPIC_API_KEY=sk-ant-...`"
        )
        return

    df = storage.get_contacts()
    if df.empty:
        st.warning("No contacts found — generate data first.")
        return

    import anthropic
    from agent.tracer import AgentTracer
    from agent.segmentation import SegmentationEngine
    from agent.email_writer import EmailWriter

    client = anthropic.Anthropic(api_key=api_key)
    tracer = AgentTracer(storage)

    with st.status("Running agent pipeline…", expanded=True) as status:

        # 1. Segmentation
        st.write(f"🔍 Segmenting **{len(df)} contacts**…")
        engine = SegmentationEngine(client, tracer)
        contacts_list = df.to_dict("records")
        result = engine.run(contacts_list, custom_criteria=criteria or None)
        engine.persist(result["assignments"])
        n_segs = len(result["segments"])
        st.write(f"✅ Found **{n_segs} segments** across {len(result['assignments'])} contacts")

        # 2. Email generation
        st.write("✉️ Generating personalised emails…")
        writer = EmailWriter(client, tracer)
        emails = writer.generate_all(
            result["segments"],
            result["assignments"],
            contacts_list,
        )
        fresh_contacts = storage.get_contacts().to_dict("records")
        writer.persist(emails, fresh_contacts)
        st.write(f"✅ Generated **{len(emails)} emails**")

        # Summary
        s = tracer.summary()
        st.write(
            f"📊 **{s['calls']} API calls** · "
            f"**{s['total_tokens']:,} tokens** · "
            f"**{s['total_latency_ms'] / 1000:.1f}s**"
        )
        status.update(label="✅ Pipeline complete!", state="complete")

    # Invalidate cached data
    _load_contacts.clear()
    _load_log.clear()
    st.rerun()


def _run_generate() -> None:
    from data.generate_contacts import generate_and_save

    with st.status("Generating synthetic contacts…", expanded=True) as status:
        storage.init_db()
        contacts = generate_and_save()
        n = storage.upsert_contacts(contacts)
        st.write(f"✅ {len(contacts)} contacts written to database")
        status.update(label=f"Done — {len(contacts)} contacts generated!", state="complete")

    _load_contacts.clear()
    st.rerun()


# ---------------------------------------------------------------------------
# Tab: Contacts
# ---------------------------------------------------------------------------

def _tab_contacts(df: pd.DataFrame) -> None:
    if df.empty:
        st.info(
            "No contacts loaded yet.  \n"
            "Click **Generate Data** in the sidebar to create 50 synthetic contacts."
        )
        return

    seg_colour = _seg_colour_map(df["segment"].dropna().unique().tolist())

    st.subheader(f"Contacts  ({len(df)})")

    # ── Filters ──────────────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns([2, 2, 2])
    seg_options = ["All"] + sorted(df["segment"].dropna().unique().tolist())
    act_options = ["All"] + sorted(df["recommended_action"].dropna().unique().tolist())
    sel_seg = fc1.selectbox("Segment", seg_options, key="flt_seg")
    sel_act = fc2.selectbox("Action", act_options, key="flt_act")
    search   = fc3.text_input("Search name / company", placeholder="…", key="flt_search")

    filt = df.copy()
    if sel_seg != "All":
        filt = filt[filt["segment"] == sel_seg]
    if sel_act != "All":
        filt = filt[filt["recommended_action"] == sel_act]
    if search.strip():
        mask = (
            filt["name"].str.contains(search, case=False, na=False)
            | filt["company"].str.contains(search, case=False, na=False)
        )
        filt = filt[mask]

    # ── Table ─────────────────────────────────────────────────────────────
    display_cols = [
        "name", "company", "role", "last_activity",
        "segment", "confidence", "recommended_action",
    ]
    show = [c for c in display_cols if c in filt.columns]
    tbl = filt[show].copy()
    if "confidence" in tbl.columns:
        tbl["confidence"] = tbl["confidence"].apply(
            lambda x: f"{x:.0%}" if pd.notna(x) else "—"
        )

    st.dataframe(
        tbl,
        use_container_width=True,
        hide_index=True,
        height=380,
        column_config={
            "segment": st.column_config.TextColumn("Segment", width="medium"),
            "recommended_action": st.column_config.TextColumn("Action", width="small"),
            "confidence": st.column_config.TextColumn("Confidence", width="small"),
        },
    )
    st.caption(f"Showing {len(filt)} of {len(df)} contacts")

    # ── Contact Detail ────────────────────────────────────────────────────
    st.divider()
    st.subheader("Contact Detail")

    if filt.empty:
        st.info("No contacts match the current filters.")
        return

    names = filt["name"].tolist()
    chosen = st.selectbox("Select a contact", names, label_visibility="collapsed")
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
                f"**Segment:** "
                f'<span class="seg-pill" style="background:{colour}">{seg}</span>',
                unsafe_allow_html=True,
            )
            conf = row.get("confidence")
            st.write(
                f"**Confidence:** {conf:.0%}" if pd.notna(conf) else "**Confidence:** —"
            )
            action = row.get("recommended_action", "—")
            action_col = _ACTION_COLOURS.get(action, "#6b7280")
            st.markdown(
                f"**Action:** "
                f'<span class="seg-pill" style="background:{action_col}">{action}</span>',
                unsafe_allow_html=True,
            )
            with st.expander("Reasoning"):
                st.write(row.get("segment_reasoning") or "No reasoning stored.")
        else:
            st.info("Not yet segmented. Run the agent pipeline.")

    email_rec = storage.get_email_for_contact(contact_id)
    if email_rec:
        st.divider()
        st.markdown(f"**✉ Staged Email**  ·  `{email_rec.get('segment_tag', '')}` segment")
        st.write(f"**Subject:** {email_rec['subject']}")
        st.text_area(
            "Body",
            value=email_rec["body"],
            height=200,
            disabled=True,
            key=f"body_{contact_id}",
        )


# ---------------------------------------------------------------------------
# Tab: Analytics
# ---------------------------------------------------------------------------

def _tab_analytics(df: pd.DataFrame) -> None:
    seg_df = df.dropna(subset=["segment"])
    if seg_df.empty:
        st.info("Run the agent pipeline to see analytics.")
        return

    seg_colour = _seg_colour_map(seg_df["segment"].unique().tolist())

    # ── KPI row ───────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Segments Found", seg_df["segment"].nunique())
    k2.metric("Ready to Email", int((seg_df["recommended_action"] == "email").sum()))
    k3.metric("To Nurture",     int((seg_df["recommended_action"] == "nurture").sum()))
    avg_c = seg_df["confidence"].mean()
    k4.metric("Avg Confidence", f"{avg_c:.0%}" if pd.notna(avg_c) else "—")

    st.divider()

    # ── Charts row 1 ──────────────────────────────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        counts = seg_df["segment"].value_counts().reset_index()
        counts.columns = ["Segment", "Count"]
        fig = px.pie(
            counts,
            values="Count",
            names="Segment",
            title="Contacts by Segment",
            color="Segment",
            color_discrete_map=seg_colour,
            hole=0.35,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        act = (
            seg_df.groupby(["segment", "recommended_action"])
            .size()
            .reset_index(name="count")
        )
        fig2 = px.bar(
            act,
            x="segment",
            y="count",
            color="recommended_action",
            title="Recommended Actions by Segment",
            color_discrete_map=_ACTION_COLOURS,
            barmode="stack",
        )
        fig2.update_layout(
            legend_title="Action",
            xaxis_tickangle=-20,
            margin=dict(t=40, b=0, l=0, r=0),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Charts row 2 ──────────────────────────────────────────────────────
    conf_df = seg_df.dropna(subset=["confidence"])
    if not conf_df.empty:
        fig3 = px.box(
            conf_df,
            x="segment",
            y="confidence",
            color="segment",
            color_discrete_map=seg_colour,
            title="Confidence Score Distribution by Segment",
            points="all",
        )
        fig3.update_layout(showlegend=False, xaxis_tickangle=-20)
        st.plotly_chart(fig3, use_container_width=True)

    # ── Summary table ─────────────────────────────────────────────────────
    st.subheader("Segment Summary")
    summary = (
        seg_df.groupby("segment")
        .agg(
            contacts     =("email",              "count"),
            avg_confidence=("confidence",         "mean"),
            email_count  =("recommended_action", lambda x: (x == "email").sum()),
            nurture_count=("recommended_action", lambda x: (x == "nurture").sum()),
            ignore_count =("recommended_action", lambda x: (x == "ignore").sum()),
        )
        .reset_index()
    )
    summary["avg_confidence"] = summary["avg_confidence"].apply(
        lambda x: f"{x:.0%}" if pd.notna(x) else "—"
    )
    summary.columns = [
        "Segment", "Contacts", "Avg Confidence",
        "Email", "Nurture", "Ignore",
    ]
    st.dataframe(summary, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Tab: Staged Emails
# ---------------------------------------------------------------------------

def _tab_emails(df: pd.DataFrame) -> None:
    seg_df = df.dropna(subset=["segment"])
    if seg_df.empty:
        st.info("Run the agent pipeline to generate emails.")
        return

    seg_options = ["All"] + sorted(seg_df["segment"].unique().tolist())
    sel_seg = st.selectbox("Filter by Segment", seg_options, key="email_seg")

    target = seg_df if sel_seg == "All" else seg_df[seg_df["segment"] == sel_seg]

    rows = []
    for _, r in target.iterrows():
        e = storage.get_email_for_contact(int(r["id"]))
        if e:
            rows.append(
                {
                    "name":        r["name"],
                    "email":       r["email"],
                    "company":     r["company"],
                    "segment":     r["segment"],
                    "subject":     e["subject"],
                    "body":        e["body"],
                    "generated_at": (e.get("generated_at") or "")[:16],
                }
            )

    if not rows:
        st.info("No staged emails yet — run the agent first.")
        return

    emails_df = pd.DataFrame(rows)

    # ── Export ────────────────────────────────────────────────────────────
    col_count, col_btn = st.columns([3, 1])
    col_count.caption(f"**{len(rows)}** emails staged")
    col_btn.download_button(
        "⬇ Export CSV",
        data=emails_df.to_csv(index=False),
        file_name=f"staged_emails_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.divider()

    # ── Email cards ───────────────────────────────────────────────────────
    seg_colour = _seg_colour_map(emails_df["segment"].unique().tolist())
    for e in rows:
        colour = seg_colour.get(e["segment"], "#6b7280")
        label = (
            f"**{e['name']}** &nbsp;·&nbsp; {e['company']} &nbsp;·&nbsp; "
            f'<span class="seg-pill" style="background:{colour}">{e["segment"]}</span>'
        )
        with st.expander(f"{e['name']} ({e['company']}) — {e['subject'][:55]}"):
            st.markdown(label, unsafe_allow_html=True)
            st.caption(f"Generated: {e['generated_at']}  ·  To: {e['email']}")
            st.write(f"**Subject:** {e['subject']}")
            st.divider()
            st.text(e["body"])


# ---------------------------------------------------------------------------
# Tab: Agent Log
# ---------------------------------------------------------------------------

def _tab_log(log_df: pd.DataFrame) -> None:
    if log_df.empty:
        st.info("No execution log yet — run the agent pipeline to see traces.")
        return

    # ── KPI row ───────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    total_tokens = (
        log_df["tokens_input"].fillna(0) + log_df["tokens_output"].fillna(0)
    ).sum()
    k1.metric("API Calls",      len(log_df))
    k2.metric("Total Tokens",   f"{int(total_tokens):,}")
    k3.metric("Avg Latency",    f"{log_df['latency_ms'].mean():.0f} ms")
    k4.metric("Errors",         int((log_df["status"] == "error").sum()))

    st.divider()

    # ── Latency chart ─────────────────────────────────────────────────────
    recent = log_df.head(30).copy().reset_index(drop=True)
    recent.index = recent.index + 1
    fig = px.bar(
        recent,
        x=recent.index,
        y="latency_ms",
        color="operation",
        title="Latency per API Call (most recent 30)",
        labels={"latency_ms": "Latency (ms)", "x": "Call #"},
        color_discrete_sequence=_PALETTE,
    )
    fig.update_layout(legend_title="Operation", margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)

    # ── Token usage per call ──────────────────────────────────────────────
    tok = recent[["tokens_input", "tokens_output"]].copy()
    tok.index = recent.index
    tok_long = tok.reset_index().melt(
        id_vars="index", var_name="type", value_name="tokens"
    )
    fig2 = px.bar(
        tok_long,
        x="index",
        y="tokens",
        color="type",
        title="Token Usage per Call",
        labels={"index": "Call #", "tokens": "Tokens"},
        color_discrete_map={
            "tokens_input":  "#3b82f6",
            "tokens_output": "#10b981",
        },
        barmode="stack",
    )
    fig2.update_layout(margin=dict(t=40, b=0, l=0, r=0))
    st.plotly_chart(fig2, use_container_width=True)

    # ── Raw log table ─────────────────────────────────────────────────────
    st.subheader("Raw Trace")
    show_cols = [
        "timestamp", "operation", "input_summary", "output_summary",
        "tokens_input", "tokens_output", "latency_ms", "status", "model",
    ]
    avail = [c for c in show_cols if c in log_df.columns]
    display = log_df[avail].copy()
    if "latency_ms" in display.columns:
        display["latency_ms"] = display["latency_ms"].apply(
            lambda x: f"{x:.0f} ms" if pd.notna(x) else "—"
        )
    if "timestamp" in display.columns:
        display["timestamp"] = display["timestamp"].str[:19].str.replace("T", " ")

    st.dataframe(display, use_container_width=True, hide_index=True, height=300)


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

    # Load data (cached)
    df      = _load_contacts()
    log_df  = _load_log()

    # ── Header ────────────────────────────────────────────────────────────
    st.markdown("# 🤖 AI CRM Agent")
    st.caption(
        "Segment contacts with Claude · Generate personalised emails · Track every LLM call"
    )
    st.divider()

    # ── Diff banner (if segments changed since last run) ──────────────────
    if "prev_segments" in st.session_state and not df.empty:
        current_segs = set(df["segment"].dropna().unique())
        prev_segs    = set(st.session_state["prev_segments"])
        new_segs     = current_segs - prev_segs
        gone_segs    = prev_segs - current_segs
        if new_segs or gone_segs:
            parts = []
            if new_segs:
                parts.append(f"**New segments:** {', '.join(sorted(new_segs))}")
            if gone_segs:
                parts.append(f"**Removed:** {', '.join(sorted(gone_segs))}")
            st.info("🔄 Segmentation changed since last run.  " + "  ·  ".join(parts))

    # Store current segments for next run comparison
    if not df.empty:
        st.session_state["prev_segments"] = list(df["segment"].dropna().unique())

    # ── Tabs ──────────────────────────────────────────────────────────────
    t_contacts, t_analytics, t_emails, t_log = st.tabs(
        ["📋 Contacts", "📊 Analytics", "✉️ Staged Emails", "🔍 Agent Log"]
    )

    with t_contacts:
        _tab_contacts(df)

    with t_analytics:
        _tab_analytics(df)

    with t_emails:
        _tab_emails(df)

    with t_log:
        _tab_log(log_df)


if __name__ == "__main__":
    main()
