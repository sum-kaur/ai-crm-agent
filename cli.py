"""CLI entry point.

  python cli.py run          # full pipeline (generate -> segment -> emails)
  python cli.py generate     # generate / refresh synthetic contacts only
  python cli.py segment      # re-run segmentation on existing contacts
  python cli.py dashboard    # launch the Streamlit CRM dashboard
"""
import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows (cp1252 default can't render Rich/Unicode chars)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

# Ensure project root is importable regardless of working directory
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()
console = Console()


def _require_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not key:
        console.print(
            "[bold red]Error:[/bold red] ANTHROPIC_API_KEY is not set.\n"
            "Create a [bold].env[/bold] file in this directory:\n\n"
            "  ANTHROPIC_API_KEY=sk-ant-..."
        )
        sys.exit(1)
    return key


def _make_client(api_key: str):
    import anthropic
    return anthropic.Anthropic(api_key=api_key)


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
def cli():
    """AI CRM Agent — intelligent contact segmentation and outreach."""


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------

@cli.command()
def generate():
    """Generate 50 synthetic contacts and initialise the database."""
    import agent.storage as storage
    from data.generate_contacts import generate_and_save

    with console.status("[bold green]Generating synthetic contacts…"):
        storage.init_db()
        contacts = generate_and_save()
        storage.upsert_contacts(contacts)

    console.print(
        f"[green]✓[/green] Generated and saved [bold]{len(contacts)}[/bold] contacts."
    )


# ---------------------------------------------------------------------------
# segment
# ---------------------------------------------------------------------------

@cli.command()
@click.option(
    "--criteria", "-c", default=None,
    help="Optional plain-English segmentation criteria for Claude to follow.",
)
def segment(criteria):
    """Run LLM segmentation on existing contacts."""
    import agent.storage as storage
    from agent.tracer import AgentTracer
    from agent.segmentation import SegmentationEngine

    api_key = _require_api_key()
    storage.init_db()

    df = storage.get_contacts()
    if df.empty:
        console.print("[yellow]No contacts found. Run [bold]python cli.py generate[/bold] first.[/yellow]")
        sys.exit(1)

    client = _make_client(api_key)
    tracer = AgentTracer(storage)

    console.print(
        Panel.fit(
            f"[bold]Segmenting {len(df)} contacts[/bold]\n"
            f"Criteria: {criteria or 'auto-detect from data'}",
            title="AI CRM Agent",
        )
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Calling Claude…", total=None)
        engine = SegmentationEngine(client, tracer)
        result = engine.run(df.to_dict("records"), custom_criteria=criteria)
        engine.persist(result["assignments"])
        progress.update(
            task,
            description=f"[green]Done — {len(result['segments'])} segments discovered[/green]",
        )

    _print_segment_table(result)
    _print_summary(tracer)


# ---------------------------------------------------------------------------
# run  (full pipeline)
# ---------------------------------------------------------------------------

@cli.command()
@click.option(
    "--criteria", "-c", default=None,
    help="Optional plain-English segmentation criteria.",
)
@click.option(
    "--skip-emails", is_flag=True,
    help="Skip email generation (segmentation only).",
)
@click.option(
    "--fresh", is_flag=True,
    help="Re-generate synthetic contacts before running.",
)
def run(criteria, skip_emails, fresh):
    """Run the full pipeline: (generate →) segment → write emails."""
    import agent.storage as storage
    from agent.tracer import AgentTracer
    from agent.segmentation import SegmentationEngine
    from agent.email_writer import EmailWriter

    api_key = _require_api_key()
    storage.init_db()

    # Optionally refresh contacts
    if fresh or storage.get_contacts().empty:
        from data.generate_contacts import generate_and_save
        with console.status("[green]Generating contacts…"):
            contacts = generate_and_save()
            storage.upsert_contacts(contacts)
        console.print(f"[green]✓[/green] {len(contacts)} contacts loaded.")

    df = storage.get_contacts()
    console.print(
        Panel.fit(
            f"[bold]AI CRM Agent Pipeline[/bold]\n"
            f"Contacts: {len(df)}  |  Criteria: {criteria or 'auto-detect'}  |"
            f"  Emails: {'skip' if skip_emails else 'generate'}",
            title="🤖 Running",
        )
    )

    client = _make_client(api_key)
    tracer = AgentTracer(storage)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:

        # Step 1 — Segmentation
        seg_task = progress.add_task("Segmenting contacts…", total=None)
        engine = SegmentationEngine(client, tracer)
        contacts_list = df.to_dict("records")
        result = engine.run(contacts_list, custom_criteria=criteria)
        engine.persist(result["assignments"])
        progress.update(
            seg_task,
            description=f"[green]✓ Segmented → {len(result['segments'])} segments[/green]",
        )

        # Step 2 — Email generation
        if not skip_emails:
            email_task = progress.add_task("Generating personalised emails…", total=None)
            writer = EmailWriter(client, tracer)
            emails = writer.generate_all(
                result["segments"],
                result["assignments"],
                contacts_list,
            )
            writer.persist(emails, storage.get_contacts().to_dict("records"))
            progress.update(
                email_task,
                description=f"[green]✓ Emails → {len(emails)} staged[/green]",
            )

    console.print()
    _print_segment_table(result)

    if not skip_emails:
        console.print(
            f"\n[green]✓[/green] [bold]{len(emails)}[/bold] emails staged in the database.\n"
        )

    _print_summary(tracer)
    console.print(
        "\n[dim]Launch dashboard:  python cli.py dashboard[/dim]"
    )


# ---------------------------------------------------------------------------
# dashboard
# ---------------------------------------------------------------------------

@cli.command()
def dashboard():
    """Open the Streamlit CRM dashboard in your browser."""
    import subprocess
    dashboard_path = Path(__file__).parent / "dashboard" / "app.py"
    console.print("[green]Launching Streamlit dashboard…[/green]")
    subprocess.run(
        ["streamlit", "run", str(dashboard_path)],
        check=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_segment_table(result: dict) -> None:
    seg_counts: dict[str, int] = {}
    action_counts: dict[str, dict[str, int]] = {}
    for a in result["assignments"]:
        seg = a["segment"]
        seg_counts[seg] = seg_counts.get(seg, 0) + 1
        action_counts.setdefault(seg, {})
        action = a["recommended_action"]
        action_counts[seg][action] = action_counts[seg].get(action, 0) + 1

    table = Table(title="Discovered Segments", show_header=True, header_style="bold")
    table.add_column("Segment", style="cyan bold")
    table.add_column("Contacts", justify="right")
    table.add_column("Email", justify="right", style="green")
    table.add_column("Nurture", justify="right", style="yellow")
    table.add_column("Ignore", justify="right", style="red")
    table.add_column("Strategy", max_width=55)

    for seg in result["segments"]:
        name = seg["name"]
        counts = action_counts.get(name, {})
        table.add_row(
            name,
            str(seg_counts.get(name, 0)),
            str(counts.get("email", 0)),
            str(counts.get("nurture", 0)),
            str(counts.get("ignore", 0)),
            seg.get("email_strategy", "")[:55],
        )

    console.print(table)


def _print_summary(tracer) -> None:
    s = tracer.summary()
    console.print(
        f"\n[bold]Agent Trace Summary[/bold]\n"
        f"  API calls : {s['calls']}\n"
        f"  Tokens    : {s['total_tokens']:,}  "
        f"({s['tokens_in']:,} in / {s['tokens_out']:,} out)\n"
        f"  Latency   : {s['total_latency_ms'] / 1000:.1f}s total\n"
        f"  Errors    : {s['errors']}"
    )


if __name__ == "__main__":
    cli()
