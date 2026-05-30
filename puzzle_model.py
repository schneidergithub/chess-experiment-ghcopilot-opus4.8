"""Normalize raw Lichess puzzle JSON into a stable internal model."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any

from src._compat import chess


class PuzzleSchemaError(ValueError):
    """Raised when required puzzle fields cannot be resolved."""


def _resolve_fen(raw: dict[str, Any]) -> str:
    """Resolve FEN with the documented fallback order.

    Prefer ``puzzle.fen`` first, then ``raw.fen``, then ``game.fen``.
    """
    puzzle = raw.get("puzzle") or {}
    if isinstance(puzzle, dict) and puzzle.get("fen"):
        return str(puzzle["fen"])
    if raw.get("fen"):
        return str(raw["fen"])
    game = raw.get("game") or {}
    if isinstance(game, dict) and game.get("fen"):
        return str(game["fen"])
    raise PuzzleSchemaError("no FEN found in puzzle.fen, raw.fen, or game.fen")


def _resolve_perf(game: dict[str, Any]) -> str | None:
    """Handle ``game.perf`` as either a string or an object with name/key."""
    perf = game.get("perf")
    if perf is None:
        return None
    if isinstance(perf, str):
        return perf
    if isinstance(perf, dict):
        return perf.get("name") or perf.get("key")
    return str(perf)


@dataclass
class PuzzleModel:
    id: str
    rating: int | None
    themes: list[str]
    solution: list[str]
    fen: str
    side_to_move: str  # "white" or "black"
    perf: str | None = None
    last_move: str | None = None
    game_id: str | None = None
    players: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_puzzle(raw: dict[str, Any]) -> PuzzleModel:
    """Build a PuzzleModel from raw Lichess JSON."""
    puzzle = raw.get("puzzle") or {}
    game = raw.get("game") or {}

    fen = _resolve_fen(raw)

    try:
        board = chess.Board(fen)
    except ValueError as exc:
        raise PuzzleSchemaError(f"invalid FEN '{fen}': {exc}") from exc

    side_to_move = "white" if board.turn == chess.WHITE else "black"

    puzzle_id = str(puzzle.get("id") or raw.get("id") or "unknown")

    rating_val = puzzle.get("rating")
    rating = int(rating_val) if isinstance(rating_val, (int, float)) else None

    themes = list(puzzle.get("themes") or [])
    solution = list(puzzle.get("solution") or [])

    return PuzzleModel(
        id=puzzle_id,
        rating=rating,
        themes=themes,
        solution=solution,
        fen=fen,
        side_to_move=side_to_move,
        perf=_resolve_perf(game) if isinstance(game, dict) else None,
        last_move=puzzle.get("lastMove"),
        game_id=game.get("id") if isinstance(game, dict) else None,
        players=list(game.get("players") or []) if isinstance(game, dict) else [],
    )
