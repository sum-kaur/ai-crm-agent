"""SQLite storage layer for contacts, staged emails, and execution logs."""
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent.parent / "data" / "crm.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT    NOT NULL,
    email               TEXT    UNIQUE NOT NULL,
    company             TEXT,
    role                TEXT,
    last_activity       TEXT,
    notes               TEXT,
    segment             TEXT,
    segment_reasoning   TEXT,
    confidence          REAL,
    recommended_action  TEXT,
    segmented_at        TEXT,
    status              TEXT    DEFAULT 'new',
    created_at          TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS staged_emails (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id   INTEGER UNIQUE REFERENCES contacts(id),
    subject      TEXT,
    body         TEXT,
    segment_tag  TEXT,
    sent_at      TEXT,
    generated_at TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS execution_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT    NOT NULL,
    operation       TEXT    NOT NULL,
    input_summary   TEXT,
    output_summary  TEXT,
    tokens_input    INTEGER DEFAULT 0,
    tokens_output   INTEGER DEFAULT 0,
    latency_ms      REAL    DEFAULT 0,
    model           TEXT,
    status          TEXT    DEFAULT 'success',
    error           TEXT
);
"""

# Valid contact status values
CONTACT_STATUSES = ["new", "contacted", "replied", "converted", "ignored"]


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns introduced after initial release without breaking existing DBs."""
    contact_cols = {row[1] for row in conn.execute("PRAGMA table_info(contacts)")}
    if "status" not in contact_cols:
        conn.execute("ALTER TABLE contacts ADD COLUMN status TEXT DEFAULT 'new'")

    email_cols = {row[1] for row in conn.execute("PRAGMA table_info(staged_emails)")}
    if "sent_at" not in email_cols:
        conn.execute("ALTER TABLE staged_emails ADD COLUMN sent_at TEXT")


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)
        _migrate(conn)


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

def upsert_contacts(contacts: list[dict]) -> int:
    sql = """
    INSERT INTO contacts (name, email, company, role, last_activity, notes)
    VALUES (:name, :email, :company, :role, :last_activity, :notes)
    ON CONFLICT(email) DO UPDATE SET
        name          = excluded.name,
        company       = excluded.company,
        role          = excluded.role,
        last_activity = excluded.last_activity,
        notes         = excluded.notes
    """
    with _connect() as conn:
        conn.executemany(sql, contacts)
        return conn.total_changes


def update_segment(
    email: str,
    segment: str,
    reasoning: str,
    confidence: float,
    action: str,
) -> None:
    sql = """
    UPDATE contacts
    SET segment=?, segment_reasoning=?, confidence=?,
        recommended_action=?, segmented_at=datetime('now')
    WHERE email=?
    """
    with _connect() as conn:
        conn.execute(sql, (segment, reasoning, confidence, action, email))


def update_contact_status(contact_id: int, status: str) -> None:
    if status not in CONTACT_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of {CONTACT_STATUSES}")
    with _connect() as conn:
        conn.execute("UPDATE contacts SET status=? WHERE id=?", (status, contact_id))


def get_contacts() -> pd.DataFrame:
    with _connect() as conn:
        return pd.read_sql("SELECT * FROM contacts ORDER BY id", conn)


def get_contact_by_id(contact_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM contacts WHERE id=?", (contact_id,)
        ).fetchone()
        return dict(row) if row else None


def clear_segments() -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE contacts SET segment=NULL, segment_reasoning=NULL, "
            "confidence=NULL, recommended_action=NULL, segmented_at=NULL"
        )
        conn.execute("DELETE FROM staged_emails")


# ---------------------------------------------------------------------------
# Staged emails
# ---------------------------------------------------------------------------

def save_email(contact_id: int, subject: str, body: str, segment_tag: str) -> int:
    sql = """
    INSERT OR REPLACE INTO staged_emails (contact_id, subject, body, segment_tag)
    VALUES (?, ?, ?, ?)
    """
    with _connect() as conn:
        cur = conn.execute(sql, (contact_id, subject, body, segment_tag))
        return cur.lastrowid


def get_email_for_contact(contact_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM staged_emails WHERE contact_id=? ORDER BY id DESC LIMIT 1",
            (contact_id,),
        ).fetchone()
        return dict(row) if row else None


def get_all_emails() -> pd.DataFrame:
    sql = """
    SELECT e.*, c.name, c.email AS contact_email, c.company, c.role
    FROM staged_emails e
    JOIN contacts c ON e.contact_id = c.id
    ORDER BY e.id
    """
    with _connect() as conn:
        return pd.read_sql(sql, conn)


def get_unsent_emails() -> pd.DataFrame:
    sql = """
    SELECT e.*, c.name, c.email AS contact_email, c.company, c.role
    FROM staged_emails e
    JOIN contacts c ON e.contact_id = c.id
    WHERE e.sent_at IS NULL
    ORDER BY e.id
    """
    with _connect() as conn:
        return pd.read_sql(sql, conn)


def mark_email_sent(staged_email_id: int) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE staged_emails SET sent_at=datetime('now') WHERE id=?",
            (staged_email_id,),
        )


# ---------------------------------------------------------------------------
# Execution log
# ---------------------------------------------------------------------------

def log_execution(entry) -> None:
    sql = """
    INSERT INTO execution_log
        (timestamp, operation, input_summary, output_summary,
         tokens_input, tokens_output, latency_ms, model, status, error)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with _connect() as conn:
        conn.execute(
            sql,
            (
                entry.timestamp,
                entry.operation,
                entry.input_summary,
                entry.output_summary,
                entry.tokens_input,
                entry.tokens_output,
                entry.latency_ms,
                entry.model,
                entry.status,
                entry.error,
            ),
        )


def get_execution_log() -> pd.DataFrame:
    with _connect() as conn:
        return pd.read_sql("SELECT * FROM execution_log ORDER BY id DESC", conn)
