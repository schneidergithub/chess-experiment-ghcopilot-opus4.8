# Chess Puzzle Video — Milestone 1 (local generation)

A local-first pipeline that fetches the daily Lichess puzzle, normalizes it,
renders board frames, and builds a silent MP4 — all on disk, no upload.

## Milestone 1 scope

This repository implements **only** Milestone 1: local file generation. A run
produces, under `artifacts/YYYY-MM-DD/`:

- `puzzle.json` — raw puzzle JSON from Lichess
- `metadata.json` — deterministic run metadata
- `frames/frame_00000.png` (and more) — rendered scene frames
- `video.mp4` — silent video assembled from the frames

## Requirements

- Python 3.11+
- FFmpeg on `PATH` (or set `ffmpeg.binary` in `config/app.json`)
- Python deps: `requests`, `chess` (python-chess), `Pillow`, `cairosvg`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Run

```bash
python -m src.main smoke-test
python -m src.main run --skip-upload
# regenerate everything, ignoring step markers:
python -m src.main run --skip-upload --force
```

`--skip-upload` is the standard Milestone 1 run mode.

### Offline / deterministic runs

The fetch step normally calls `https://lichess.org/api/puzzle/daily`. For
offline or reproducible runs, point it at a local fixture:

```bash
LICHESS_PUZZLE_FIXTURE=tests/fixtures/daily_puzzle_sample.json \
  python -m src.main run --skip-upload --force
```

## Pipeline stages

1. **fetch** (`src/fetch_puzzle.py`) — GET daily puzzle JSON; error on non-200; persist raw JSON.
2. **normalize** (`src/puzzle_model.py`) — extract `id`, `rating`, `themes`, `solution`, `fen`; derive side to move; handle `game.perf` as string or object. FEN resolution prefers `puzzle.fen`, then `raw.fen`, then `game.fen`.
3. **render** (`src/render_board.py`) — render intro, think-time, solution, and outro scenes; board via `chess.svg.board()` + `cairosvg`, fit with no clipping, vertically centered below the header.
4. **video** (`src/build_video.py`) — assemble a silent MP4 with FFmpeg using configured width/height/fps/codec/pixel format.
5. **metadata** (`src/metadata.py`) — write deterministic run metadata.

State markers (`src/state_manager.py`) under `artifacts/YYYY-MM-DD/.state/`
provide rerun safety; `--force` clears them.

## Configuration

See `config/app.json`. Milestone 1 baseline: 1920×1080, 30 fps, `board_size` 740, coordinates on.

## Tests

```bash
pytest -q
```

## Boundary

Local generation only. YouTube API, OAuth, token generation, and upload
automation are intentionally **out of scope** for Milestone 1 and are not
implemented or documented here.
