"""Fetch the daily Lichess puzzle JSON and persist it to disk.

Source of truth: https://lichess.org/api/puzzle/daily

For offline / deterministic local runs, an optional fixture file can be
supplied via the ``LICHESS_PUZZLE_FIXTURE`` environment variable. When set,
its JSON contents are used verbatim instead of performing a network request.
This keeps the live-API path as the default while allowing reproducible runs
in sandboxed environments.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests


class PuzzleFetchError(RuntimeError):
    """Raised when the daily puzzle cannot be fetched."""


def fetch_daily_puzzle(url: str, timeout: float = 20.0) -> dict[str, Any]:
    """Return the daily puzzle JSON as a dict.

    Raises PuzzleFetchError on any non-200 response or transport error.
    """
    fixture = os.environ.get("LICHESS_PUZZLE_FIXTURE")
    if fixture:
        fixture_path = Path(fixture)
        if not fixture_path.exists():
            raise PuzzleFetchError(f"fixture not found: {fixture_path}")
        with fixture_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    try:
        resp = requests.get(url, timeout=timeout, headers={"Accept": "application/json"})
    except requests.RequestException as exc:  # pragma: no cover - network path
        raise PuzzleFetchError(f"request to {url} failed: {exc}") from exc

    if resp.status_code != 200:
        raise PuzzleFetchError(
            f"unexpected status {resp.status_code} from {url}"
        )

    try:
        return resp.json()
    except ValueError as exc:  # pragma: no cover - network path
        raise PuzzleFetchError(f"invalid JSON from {url}: {exc}") from exc


def persist_raw_puzzle(data: dict[str, Any], out_path: str | Path) -> Path:
    """Write the raw puzzle JSON to ``out_path`` and return the path."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    return out_path
