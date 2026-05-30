"""Load application configuration from config/app.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    # src/config_loader.py -> src -> repo root
    return Path(__file__).resolve().parent.parent


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    if path is None:
        path = repo_root() / "config" / "app.json"
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)
