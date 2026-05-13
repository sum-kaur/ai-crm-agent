"""Tests for JSON parsing and contact formatting in segmentation/email_writer."""
import pytest
from agent.segmentation import _extract_json, _format_contacts
from agent.email_writer import _extract_json as ew_extract_json


# ---------------------------------------------------------------------------
# _extract_json
# ---------------------------------------------------------------------------

def test_extract_bare_json():
    data = '{"segments": [], "assignments": []}'
    result = _extract_json(data)
    assert result == {"segments": [], "assignments": []}


def test_extract_fenced_json():
    data = '```json\n{"segments": [{"name": "A"}], "assignments": []}\n```'
    result = _extract_json(data)
    assert result["segments"][0]["name"] == "A"


def test_extract_json_with_preamble():
    data = 'Here is the analysis:\n\n{"segments": [], "assignments": [{"email": "x@y.com"}]}'
    result = _extract_json(data)
    assert result["assignments"][0]["email"] == "x@y.com"


def test_extract_json_raises_on_garbage():
    with pytest.raises((ValueError, Exception)):
        _extract_json("this is not json at all, sorry")


def test_email_writer_extract_json():
    data = '{"emails": [{"email": "a@b.com", "subject": "Hi", "body": "Hello"}]}'
    result = ew_extract_json(data)
    assert len(result["emails"]) == 1
    assert result["emails"][0]["subject"] == "Hi"


# ---------------------------------------------------------------------------
# _format_contacts
# ---------------------------------------------------------------------------

def test_format_contacts_includes_all_fields():
    contacts = [
        {
            "email": "alice@co.com",
            "name": "Alice",
            "company": "ACME",
            "role": "VP",
            "last_activity": "2026-01-01",
            "notes": "Very interested.",
        }
    ]
    text = _format_contacts(contacts)
    assert "Alice" in text
    assert "alice@co.com" in text
    assert "ACME" in text
    assert "Very interested." in text


def test_format_contacts_numbers_each_entry():
    contacts = [
        {"email": "a@a.com", "name": "A", "company": "", "role": "", "last_activity": "", "notes": ""},
        {"email": "b@b.com", "name": "B", "company": "", "role": "", "last_activity": "", "notes": ""},
    ]
    text = _format_contacts(contacts)
    assert "Contact 1:" in text
    assert "Contact 2:" in text
