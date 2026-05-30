"""Structured JSON logging for the pipeline.

Each log event is a single JSON object on its own line, always including a
``step`` and ``event`` field and the run ``date`` when known. To avoid the
documented pitfall, callers must never pass a ``message`` key as both a
positional argument and a keyword. Exception text is logged under
``error_message`` rather than ``message``.
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any, TextIO


class StructuredLogger:
    def __init__(self, date: str | None = None, stream: TextIO | None = None):
        self.date = date
        self._stream = stream if stream is not None else sys.stderr

    def log(self, step: str, event: str, **fields: Any) -> None:
        record: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "step": step,
            "event": event,
        }
        if self.date is not None:
            record["date"] = self.date
        # Never collide with a positional ``message``; callers pass
        # exception text under ``error_message`` instead.
        for key, value in fields.items():
            record[key] = value
        self._stream.write(json.dumps(record, default=str) + "\n")
        self._stream.flush()

    def info(self, step: str, event: str, **fields: Any) -> None:
        self.log(step, event, level="info", **fields)

    def error(self, step: str, event: str, **fields: Any) -> None:
        self.log(step, event, level="error", **fields)
