"""Tests for puzzle normalization and FEN fallback ordering."""

import json
from pathlib import Path

from src.puzzle_model import normalize_puzzle, _resolve_fen, PuzzleSchemaError

FIXTURE = Path(__file__).parent / "fixtures" / "daily_puzzle_sample.json"


def _load():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_normalize_sample():
    model = normalize_puzzle(_load())
    assert model.id == "N5nr0"
    assert model.rating == 1804
    assert model.side_to_move == "black"
    assert model.solution == ["f6e5", "f4e5", "e8e5"]
    assert model.perf == "Classical"
    assert "middlegame" in model.themes


def test_fen_fallback_order():
    fen_p = "r2qr1k1/pp1n1ppp/3n1b2/2P1N3/5B2/2N5/PPP1Q1PP/R4RK1 b - - 0 1"
    # puzzle.fen preferred
    assert _resolve_fen({"puzzle": {"fen": fen_p}}) == fen_p
    # raw.fen second
    assert _resolve_fen({"fen": fen_p, "puzzle": {}}) == fen_p
    # game.fen third
    assert _resolve_fen({"game": {"fen": fen_p}}) == fen_p


def test_fen_missing_raises():
    try:
        _resolve_fen({"puzzle": {}, "game": {}})
    except PuzzleSchemaError:
        return
    raise AssertionError("expected PuzzleSchemaError")


def test_perf_as_string():
    raw = _load()
    raw["game"]["perf"] = "classical"
    model = normalize_puzzle(raw)
    assert model.perf == "classical"
