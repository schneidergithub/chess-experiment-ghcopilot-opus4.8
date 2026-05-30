"""Milestone 1 orchestrator: fetch -> normalize -> render -> video -> metadata.

Commands:
  smoke-test                 Validate environment and core logic; exits 0 on success.
  run --skip-upload [--force]  Generate local artifacts for today's date.

``--skip-upload`` is the standard Milestone 1 run mode. No YouTube/OAuth/upload
behavior exists in this milestone.
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from datetime import date
from pathlib import Path
from typing import Any

from src._compat import chess, USING_REAL_CHESS
from src.config_loader import load_config, repo_root
from src.logging_utils import StructuredLogger
from src.fetch_puzzle import fetch_daily_puzzle, persist_raw_puzzle, PuzzleFetchError
from src.puzzle_model import normalize_puzzle, PuzzleSchemaError
from src.render_board import render_scenes
from src.build_video import build_video, resolve_ffmpeg, VideoBuildError
from src.metadata import build_metadata, save_metadata
from src.state_manager import StateManager


def _today() -> str:
    return date.today().isoformat()


def _artifact_dir(config: dict[str, Any], run_date: str) -> Path:
    root = repo_root() / config.get("artifacts", {}).get("root", "artifacts")
    return root / run_date


def cmd_smoke_test(config: dict[str, Any], logger: StructuredLogger) -> int:
    """Lightweight checks: imports, FFmpeg, FEN parsing, a tiny render."""
    logger.info("smoke-test", "start", real_chess=USING_REAL_CHESS)
    try:
        # FFmpeg presence
        ffmpeg = resolve_ffmpeg(config)
        logger.info("smoke-test", "ffmpeg_ok", path=ffmpeg)

        # FEN parsing + side to move
        sample_fen = "r2qr1k1/pp1n1ppp/3n1b2/2P1N3/5B2/2N5/PPP1Q1PP/R4RK1 b - - 0 1"
        board = chess.Board(sample_fen)
        side = "white" if board.turn == chess.WHITE else "black"
        assert side == "black", "side-to-move derivation failed"
        logger.info("smoke-test", "fen_ok", side_to_move=side)

        # Normalization on the documented sample shape
        sample_raw = {
            "game": {"id": "x", "perf": {"key": "classical", "name": "Classical"}, "players": []},
            "puzzle": {
                "id": "N5nr0",
                "rating": 1804,
                "solution": ["f6e5", "f4e5", "e8e5"],
                "themes": ["middlegame", "advantage", "short"],
                "fen": sample_fen,
                "lastMove": "d4c5",
            },
        }
        model = normalize_puzzle(sample_raw)
        assert model.fen == sample_fen
        assert model.side_to_move == "black"
        assert model.perf == "Classical"
        logger.info("smoke-test", "normalize_ok", puzzle_id=model.id)

        logger.info("smoke-test", "success")
        return 0
    except Exception as exc:  # noqa: BLE001
        logger.error("smoke-test", "failure", error_message=str(exc))
        traceback.print_exc()
        return 1


def cmd_run(config: dict[str, Any], skip_upload: bool, force: bool) -> int:
    run_date = _today()
    logger = StructuredLogger(date=run_date)
    artifact_dir = _artifact_dir(config, run_date)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    state = StateManager(artifact_dir)
    if force:
        state.reset()

    logger.info("run", "start", skip_upload=skip_upload, force=force, real_chess=USING_REAL_CHESS)

    puzzle_json_path = artifact_dir / "puzzle.json"
    metadata_path = artifact_dir / "metadata.json"
    frames_dir = artifact_dir / "frames"
    video_path = artifact_dir / "video.mp4"

    try:
        # 1. Fetch
        if force or not state.is_done("fetch") or not puzzle_json_path.exists():
            raw = fetch_daily_puzzle(
                config["api"]["daily_puzzle_url"],
                timeout=float(config["api"].get("timeout_seconds", 20)),
            )
            persist_raw_puzzle(raw, puzzle_json_path)
            state.mark_done("fetch", path=str(puzzle_json_path))
            logger.info("fetch", "ok", artifact=str(puzzle_json_path))
        else:
            import json
            raw = json.loads(puzzle_json_path.read_text(encoding="utf-8"))
            logger.info("fetch", "skip_cached", artifact=str(puzzle_json_path))

        # 2. Normalize
        puzzle = normalize_puzzle(raw)
        logger.info(
            "normalize", "ok",
            puzzle_id=puzzle.id, side_to_move=puzzle.side_to_move, rating=puzzle.rating,
        )

        # 3. Render frames
        if force or not state.is_done("render") or not frames_dir.exists() or not any(frames_dir.glob("*.png")):
            if frames_dir.exists():
                for f in frames_dir.glob("*.png"):
                    f.unlink()
            frame_paths = render_scenes(puzzle, config, frames_dir)
            state.mark_done("render", count=len(frame_paths))
            logger.info("render", "ok", artifact=str(frames_dir), frame_count=len(frame_paths))
        else:
            frame_paths = sorted(frames_dir.glob("frame_*.png"))
            logger.info("render", "skip_cached", artifact=str(frames_dir), frame_count=len(frame_paths))

        # 4. Build video
        if force or not state.is_done("video") or not video_path.exists():
            build_video(frames_dir, video_path, config)
            state.mark_done("video", path=str(video_path))
            logger.info("video", "ok", artifact=str(video_path))
        else:
            logger.info("video", "skip_cached", artifact=str(video_path))

        # 5. Metadata
        meta = build_metadata(puzzle, config, run_date, frame_count=len(frame_paths))
        save_metadata(meta, metadata_path)
        state.mark_done("metadata", path=str(metadata_path))
        logger.info("metadata", "ok", artifact=str(metadata_path))

        if not skip_upload:
            # Milestone 1 has no upload behavior. The standard path is
            # --skip-upload; without it we simply note that upload is out of
            # scope for this milestone and finish locally.
            logger.info("upload", "out_of_scope_milestone1")

        state.mark_run_complete()
        logger.info("run", "success", artifact=str(artifact_dir))
        return 0

    except (PuzzleFetchError, PuzzleSchemaError) as exc:
        step = "fetch" if isinstance(exc, PuzzleFetchError) else "normalize"
        state.write_error(step, str(exc))
        logger.error(step, "failure", error_message=str(exc))
        return 1
    except VideoBuildError as exc:
        state.write_error("video", str(exc))
        logger.error("video", "failure", error_message=str(exc))
        return 1
    except Exception as exc:  # noqa: BLE001
        state.write_error("run", str(exc))
        logger.error("run", "failure", error_message=str(exc))
        traceback.print_exc()
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="src.main", description="Milestone 1 local pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("smoke-test", help="Validate environment and core logic")

    run_p = sub.add_parser("run", help="Generate local artifacts")
    run_p.add_argument("--skip-upload", action="store_true", help="Standard Milestone 1 mode")
    run_p.add_argument("--force", action="store_true", help="Ignore state markers and regenerate")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config()

    if args.command == "smoke-test":
        logger = StructuredLogger(date=_today())
        return cmd_smoke_test(config, logger)
    if args.command == "run":
        return cmd_run(config, skip_upload=args.skip_upload, force=args.force)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
