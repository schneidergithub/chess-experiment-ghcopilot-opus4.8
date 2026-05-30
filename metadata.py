"""Write deterministic local run metadata JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_metadata(puzzle: Any, config: dict[str, Any], date: str, frame_count: int) -> dict[str, Any]:
    video = config["video"]
    return {
        "date": date,
        "milestone": 1,
        "puzzle": {
            "id": puzzle.id,
            "rating": puzzle.rating,
            "themes": puzzle.themes,
            "solution": puzzle.solution,
            "fen": puzzle.fen,
            "side_to_move": puzzle.side_to_move,
            "perf": puzzle.perf,
            "game_id": puzzle.game_id,
        },
        "video": {
            "width": int(video["width"]),
            "height": int(video["height"]),
            "fps": int(video["fps"]),
            "codec": video.get("codec"),
            "pixel_format": video.get("pixel_format"),
            "frame_count": frame_count,
        },
        "source": config.get("api", {}).get("daily_puzzle_url"),
    }


def save_metadata(metadata: dict[str, Any], out_path: str | Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        # sort_keys for determinism across runs with identical inputs.
        json.dump(metadata, fh, indent=2, ensure_ascii=False, sort_keys=True)
    return out_path
