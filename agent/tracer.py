"""Execution tracer — wraps every LLM call with timing and token logging."""
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Generator


@dataclass
class TraceEntry:
    operation: str
    input_summary: str
    output_summary: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: float = 0.0
    model: str = ""
    status: str = "success"
    error: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class AgentTracer:
    def __init__(self, storage=None):
        self._storage = storage
        self._entries: list[TraceEntry] = []

    @contextmanager
    def trace(
        self, operation: str, input_summary: str
    ) -> Generator[TraceEntry, None, None]:
        entry = TraceEntry(operation=operation, input_summary=input_summary)
        t0 = time.perf_counter()
        try:
            yield entry
        except Exception as exc:
            entry.status = "error"
            entry.error = str(exc)
            raise
        finally:
            entry.latency_ms = round((time.perf_counter() - t0) * 1000, 1)
            self._entries.append(entry)
            if self._storage:
                self._storage.log_execution(entry)

    @property
    def entries(self) -> list[TraceEntry]:
        return list(self._entries)

    def summary(self) -> dict:
        total_in = sum(e.tokens_input for e in self._entries)
        total_out = sum(e.tokens_output for e in self._entries)
        return {
            "calls": len(self._entries),
            "tokens_in": total_in,
            "tokens_out": total_out,
            "total_tokens": total_in + total_out,
            "total_latency_ms": round(
                sum(e.latency_ms for e in self._entries), 1
            ),
            "errors": sum(1 for e in self._entries if e.status == "error"),
        }
