"""Per-run state markers for rerun safety and ``--force`` behavior."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class StateManager:
    """Manage step markers under ``<artifact_dir>/.state/``.

    A step marker file indicates that step completed. ``--force`` clears all
    markers so the run regenerates everything.
    """

    def __init__(self, artifact_dir: str | Path):
        self.artifact_dir = Path(artifact_dir)
        self.state_dir = self.artifact_dir / ".state"

    def reset(self) -> None:
        if self.state_dir.exists():
            for f in self.state_dir.glob("*"):
                try:
                    f.unlink()
                except OSError:
                    pass

    def _marker(self, step: str) -> Path:
        return self.state_dir / f"{step}.done"

    def is_done(self, step: str) -> bool:
        return self._marker(step).exists()

    def mark_done(self, step: str, **info: Any) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        payload = {"step": step, "ts": time.time(), **info}
        with self._marker(step).open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, default=str)

    def mark_run_complete(self, **info: Any) -> None:
        self.mark_done("run_complete", **info)

    def write_error(self, step: str, error_message: str) -> Path:
        """Write a step-scoped error file and return its path."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        err_path = self.state_dir / f"{step}.error"
        with err_path.open("w", encoding="utf-8") as fh:
            json.dump(
                {"step": step, "ts": time.time(), "error_message": error_message},
                fh,
                default=str,
            )
        return err_path
