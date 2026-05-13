"""Tests for agent/tracer.py."""
import time
import pytest
from agent.tracer import AgentTracer


def test_trace_creates_entry():
    tracer = AgentTracer()
    with tracer.trace("my_op", "input summary") as entry:
        entry.tokens_input  = 100
        entry.tokens_output = 50
        entry.model = "claude-test"
        entry.output_summary = "done"
    assert len(tracer.entries) == 1
    e = tracer.entries[0]
    assert e.operation == "my_op"
    assert e.tokens_input == 100
    assert e.tokens_output == 50
    assert e.status == "success"


def test_trace_records_latency():
    tracer = AgentTracer()
    with tracer.trace("op", "in") as entry:
        time.sleep(0.02)
    assert tracer.entries[0].latency_ms >= 15


def test_trace_marks_error_on_exception():
    tracer = AgentTracer()
    with pytest.raises(ValueError):
        with tracer.trace("op", "in"):
            raise ValueError("boom")
    assert tracer.entries[0].status == "error"
    assert "boom" in tracer.entries[0].error


def test_summary_aggregates_correctly():
    tracer = AgentTracer()
    for i in range(3):
        with tracer.trace(f"op{i}", "in") as e:
            e.tokens_input  = 100
            e.tokens_output = 50
    s = tracer.summary()
    assert s["calls"] == 3
    assert s["tokens_in"] == 300
    assert s["tokens_out"] == 150
    assert s["total_tokens"] == 450
    assert s["errors"] == 0


def test_summary_counts_errors():
    tracer = AgentTracer()
    with tracer.trace("ok", "in") as e:
        e.tokens_input = 10
    with pytest.raises(RuntimeError):
        with tracer.trace("fail", "in"):
            raise RuntimeError("oops")
    assert tracer.summary()["errors"] == 1
    assert tracer.summary()["calls"] == 2
