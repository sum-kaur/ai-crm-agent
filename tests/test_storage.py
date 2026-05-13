"""Tests for agent/storage.py — all run against an isolated temp DB."""
import pytest
import agent.storage as storage
from agent.tracer import TraceEntry


_SAMPLE = [
    {
        "name": "Alice Example",
        "email": "alice@example.com",
        "company": "ACME Corp",
        "role": "VP Sales",
        "last_activity": "2026-01-15",
        "notes": "Very interested, has budget.",
    },
    {
        "name": "Bob Test",
        "email": "bob@test.io",
        "company": "Startup Ltd",
        "role": "Founder",
        "last_activity": "2025-11-01",
        "notes": "Free tier user, price-sensitive.",
    },
]


def test_upsert_and_retrieve_contacts():
    storage.upsert_contacts(_SAMPLE)
    df = storage.get_contacts()
    assert len(df) == 2
    assert set(df["email"]) == {"alice@example.com", "bob@test.io"}


def test_upsert_deduplicates_by_email():
    storage.upsert_contacts(_SAMPLE)
    updated = [{**_SAMPLE[0], "company": "New Co"}]
    storage.upsert_contacts(updated)
    df = storage.get_contacts()
    assert len(df) == 2
    assert df[df["email"] == "alice@example.com"].iloc[0]["company"] == "New Co"


def test_update_segment_persists():
    storage.upsert_contacts(_SAMPLE)
    storage.update_segment(
        email="alice@example.com",
        segment="Enterprise Champion",
        reasoning="Large company, VP role, recent activity.",
        confidence=0.92,
        action="email",
    )
    row = storage.get_contact_by_id(1)
    assert row["segment"] == "Enterprise Champion"
    assert row["confidence"] == pytest.approx(0.92)
    assert row["recommended_action"] == "email"


def test_update_contact_status():
    storage.upsert_contacts(_SAMPLE)
    df = storage.get_contacts()
    contact_id = int(df.iloc[0]["id"])
    storage.update_contact_status(contact_id, "contacted")
    updated = storage.get_contact_by_id(contact_id)
    assert updated["status"] == "contacted"


def test_update_contact_status_rejects_invalid():
    storage.upsert_contacts(_SAMPLE)
    df = storage.get_contacts()
    contact_id = int(df.iloc[0]["id"])
    with pytest.raises(ValueError, match="Invalid status"):
        storage.update_contact_status(contact_id, "flying_saucer")


def test_save_and_retrieve_email():
    storage.upsert_contacts(_SAMPLE)
    df = storage.get_contacts()
    contact_id = int(df.iloc[0]["id"])
    storage.save_email(contact_id, "Hello Alice", "Hi Alice,\n\nHope you're well.", "Enterprise")
    email = storage.get_email_for_contact(contact_id)
    assert email is not None
    assert email["subject"] == "Hello Alice"
    assert email["segment_tag"] == "Enterprise"
    assert email["sent_at"] is None


def test_mark_email_sent():
    storage.upsert_contacts(_SAMPLE)
    df = storage.get_contacts()
    contact_id = int(df.iloc[0]["id"])
    email_id = storage.save_email(contact_id, "Subj", "Body", "Seg")
    storage.mark_email_sent(email_id)
    email = storage.get_email_for_contact(contact_id)
    assert email["sent_at"] is not None


def test_get_unsent_emails_excludes_sent():
    storage.upsert_contacts(_SAMPLE)
    df = storage.get_contacts()
    cid1 = int(df.iloc[0]["id"])
    cid2 = int(df.iloc[1]["id"])
    eid1 = storage.save_email(cid1, "Subj1", "Body1", "Seg")
    storage.save_email(cid2, "Subj2", "Body2", "Seg")
    storage.mark_email_sent(eid1)
    unsent = storage.get_unsent_emails()
    assert len(unsent) == 1
    assert unsent.iloc[0]["contact_email"] == "bob@test.io"


def test_log_execution_persists():
    entry = TraceEntry(
        operation="segmentation",
        input_summary="50 contacts",
        output_summary="4 segments",
        tokens_input=1200,
        tokens_output=800,
        latency_ms=1543.2,
        model="claude-test",
    )
    storage.log_execution(entry)
    log = storage.get_execution_log()
    assert len(log) == 1
    assert log.iloc[0]["operation"] == "segmentation"
    assert log.iloc[0]["tokens_input"] == 1200
