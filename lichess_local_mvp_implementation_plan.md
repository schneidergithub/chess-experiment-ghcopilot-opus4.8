# Lichess Daily Puzzle YouTube Bot — Local MVP Implementation Plan
Version: 1.0  
Status: Draft  
Audience: LLM coding agents, local LLMs, and human developers  
Primary goal: Build a local-first Python application that fetches the Lichess daily puzzle, renders a silent MP4 locally, uploads it to YouTube automatically, and runs on a local schedule.

---

## 1. One-Sentence Summary

Build a local Python pipeline that once per day fetches the Lichess daily puzzle, generates a silent 1080p MP4 showing the puzzle and official solution, uploads it to YouTube using OAuth, and avoids duplicate uploads through local idempotency markers.

---

## 2. Scope Lock

This document intentionally reduces scope from the broader project vision.

### In Scope
1. Fetch the Lichess daily puzzle from the public API.
2. Parse the puzzle metadata and official solution.
3. Render a silent local MP4.
4. Upload that MP4 to YouTube automatically.
5. Run the pipeline on a local daily schedule.
6. Store artifacts and logs locally.
7. Prevent duplicate uploads for the same day.

### Out of Scope
1. LLM chess analysis.
2. Narration generation.
3. Text-to-speech.
4. Audio tracks of any kind.
5. Thumbnail generation.
6. AI-generated titles, descriptions, or tags.
7. Webhooks, email alerts, or dashboards.
8. Cloud runners such as GitHub Actions.
9. Multi-channel support.
10. Distributed execution.

### V1 Definition of Done
The system runs locally once per day, creates a valid silent MP4 for that day’s Lichess puzzle, uploads it to YouTube, and does not upload a second time for the same date unless explicitly forced.

---

## 3. Product Goal

Create the smallest reliable daily automation pipeline that proves the end-to-end workflow:

`Lichess Daily Puzzle API -> Local Render -> Silent MP4 -> YouTube Upload -> Local Daily Schedule`

The first version should optimize for correctness, determinism, and maintainability rather than visual polish.

---

## 4. Functional Requirements

### FR-01 Puzzle Fetch
The system shall call the Lichess daily puzzle endpoint and store the raw JSON response locally.

### FR-02 Puzzle Parse
The system shall extract:
- puzzle id
- FEN
- rating
- themes
- solution move sequence
- side to move
- date used for artifact storage

### FR-03 Board Rendering
The system shall render the initial board position and each move in the official solution sequence.

### FR-04 Think-Time Segment
The system shall include a fixed think-time segment before the solution begins.

### FR-05 Silent Video Output
The system shall produce a silent H.264 MP4 at 1920x1080 resolution.

### FR-06 YouTube Upload
The system shall upload the final MP4 to YouTube using stored OAuth credentials.

### FR-07 Local Scheduling
The system shall be invokable by a local scheduler once per day.

### FR-08 Idempotency
The system shall not upload duplicates for the same date unless a force option is provided.

### FR-09 Logging
The system shall write structured logs locally with step names, timestamps, statuses, and artifact paths.

---

## 5. Non-Functional Requirements

### NFR-01 Local First
The full workflow must run on a single local machine.

### NFR-02 Deterministic Output
Given the same puzzle input and configuration, the generated video should be materially the same.

### NFR-03 Recoverability
If the job fails mid-run, a later rerun should resume safely or rebuild without duplicate upload.

### NFR-04 Maintainability
Behavioral settings must be configurable without editing core logic.

### NFR-05 Security
OAuth tokens and secrets must remain outside source control.

### NFR-06 Minimal Dependencies
Use only the libraries needed to fetch, render, encode, and upload.

---

## 6. External Interfaces

### 6.1 Lichess Input
Endpoint:
`https://lichess.org/api/puzzle/daily`

Expected useful fields:
- `puzzle.id`
- `puzzle.rating`
- `puzzle.solution`
- `puzzle.themes`
- `game.pgn`
- `game.players`
- `game.perf`
- `game.id`
- `fen`

Note:
The implementation should not assume extra undocumented fields beyond what is actually returned at runtime.

### 6.2 YouTube Output
The system uploads one MP4 per daily run using the YouTube Data API and a previously authorized OAuth token.

### 6.3 Local Scheduler Interface
The app must support a single command suitable for cron, launchd, Task Scheduler, or similar:
`python -m src.main run`

Optional flags:
- `--date YYYY-MM-DD`
- `--force`
- `--skip-upload`
- `--dry-run`

---

## 7. Proposed Architecture

### 7.1 High-Level Flow

1. Determine target date.
2. Check local idempotency markers.
3. Fetch and store puzzle JSON.
4. Parse puzzle into internal model.
5. Render title card.
6. Render initial board frames for think-time.
7. Apply each official solution move and render transition frames.
8. Render end card.
9. Build silent MP4 with FFmpeg.
10. Generate deterministic metadata.
11. Upload to YouTube unless upload is disabled.
12. Save upload result and mark run complete.

### 7.2 Internal Components

#### Component: `fetch_puzzle`
Responsibility:
- Call Lichess
- Persist raw JSON
- Return normalized puzzle payload

Inputs:
- target date
- config

Outputs:
- `artifacts/YYYY-MM-DD/puzzle.json`
- normalized Python object

#### Component: `puzzle_model`
Responsibility:
- Validate and normalize puzzle data
- Compute side to move from FEN
- Provide move sequence and metadata accessors

Inputs:
- raw JSON

Outputs:
- internal dataclass or typed object

#### Component: `render_board`
Responsibility:
- Render board images and text overlays
- Generate per-frame PNGs or per-scene stills

Inputs:
- normalized puzzle model
- render config

Outputs:
- frame files in `artifacts/YYYY-MM-DD/frames/`

#### Component: `build_video`
Responsibility:
- Assemble frames into silent MP4
- Ensure fixed resolution, codec, and framerate

Inputs:
- frames directory
- FFmpeg config

Outputs:
- `artifacts/YYYY-MM-DD/video.mp4`

#### Component: `metadata`
Responsibility:
- Create deterministic title, description, and tags

Inputs:
- puzzle metadata
- date

Outputs:
- `artifacts/YYYY-MM-DD/metadata.json`

#### Component: `upload_youtube`
Responsibility:
- Load OAuth credentials
- Upload the video
- Persist returned video metadata

Inputs:
- video path
- metadata
- OAuth token/config

Outputs:
- `artifacts/YYYY-MM-DD/upload.json`

#### Component: `state_manager`
Responsibility:
- Step markers
- completion marker
- rerun safety

Inputs:
- target date
- step name

Outputs:
- marker files
- step status

#### Component: `main`
Responsibility:
- Orchestrate all steps
- provide CLI
- return non-zero on failure

---

## 8. Folder Structure

```text
youtube-chess-bot/
├── README.md
├── pyproject.toml
├── .gitignore
├── .env.example
├── config/
│   └── app.json
├── credentials/
│   ├── client_secret.json          # local only, never committed
│   └── youtube_token.json          # local only, never committed
├── logs/
├── artifacts/
│   └── YYYY-MM-DD/
│       ├── puzzle.json
│       ├── metadata.json
│       ├── upload.json
│       ├── video.mp4
│       ├── .step_fetch_done
│       ├── .step_render_done
│       ├── .step_video_done
│       ├── .step_upload_done
│       └── .done
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── fetch_puzzle.py
│   ├── puzzle_model.py
│   ├── render_board.py
│   ├── build_video.py
│   ├── metadata.py
│   ├── upload_youtube.py
│   ├── state_manager.py
│   └── logging_utils.py
└── tests/
    ├── test_fetch_puzzle.py
    ├── test_puzzle_model.py
    ├── test_render_board.py
    ├── test_metadata.py
    └── test_smoke.py
```

---

## 9. Artifact Contract

For each target date `D`:

Path:
`artifacts/D/`

Required files:
- `puzzle.json`
- `metadata.json`
- `video.mp4`
- `upload.json` if upload occurred

Markers:
- `.step_fetch_done`
- `.step_render_done`
- `.step_video_done`
- `.step_upload_done`
- `.done`

Failure files:
- `step_fetch_error.json`
- `step_render_error.json`
- `step_video_error.json`
- `step_upload_error.json`

Rules:
1. If `.done` exists and `--force` is not set, exit cleanly.
2. If a step marker exists, skip that step unless `--force` is set.
3. If upload already completed, do not upload again unless forced.
4. Every failure must emit a structured error file.

---

## 10. Configuration Schema

Preferred file:
`config/app.json`

Example:

```json
{
  "app": {
    "timezone": "UTC",
    "artifact_root": "./artifacts",
    "log_root": "./logs"
  },
  "video": {
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "codec": "libx264",
    "pixel_format": "yuv420p",
    "think_time_seconds": 15,
    "intro_seconds": 3,
    "outro_seconds": 3,
    "seconds_per_solution_move": 2
  },
  "render": {
    "board_size": 900,
    "show_coordinates": true,
    "background_style": "plain_dark",
    "overlay_title": "Lichess Daily Puzzle"
  },
  "youtube": {
    "category_id": "17",
    "privacy_status": "private",
    "default_language": "en"
  },
  "paths": {
    "ffmpeg_binary": "ffmpeg",
    "client_secret_file": "./credentials/client_secret.json",
    "oauth_token_file": "./credentials/youtube_token.json"
  }
}
```

Environment variables:
- `YOUTUBE_CLIENT_SECRET_FILE`
- `YOUTUBE_TOKEN_FILE`

Do not store secrets in `config/app.json` if that file may be committed.

---

## 11. CLI Contract

Primary command:

```bash
python -m src.main run
```

Supported options:

```bash
python -m src.main run --date 2026-04-13
python -m src.main run --force
python -m src.main run --skip-upload
python -m src.main run --dry-run
```

Expected behavior:
- `run` executes the full pipeline
- `--date` allows backfill/testing
- `--force` ignores marker files and rebuilds
- `--skip-upload` creates the video only
- `--dry-run` validates inputs and planned actions without uploading

---

## 12. Recommended Implementation Order

### Milestone 1: Fetch and Parse
Deliverables:
- `fetch_puzzle.py`
- `puzzle_model.py`
- unit tests for parsing

Acceptance criteria:
1. The app fetches the daily puzzle successfully.
2. The raw response is saved as `puzzle.json`.
3. The normalized model contains FEN, solution, themes, rating, and side to move.
4. The process exits non-zero if the API response is invalid.

### Milestone 2: Render Frames
Deliverables:
- `render_board.py`
- render config handling
- frame output directory creation

Acceptance criteria:
1. The start position renders correctly.
2. Official solution moves are applied without illegal move errors.
3. Think-time frames are created.
4. End-card frames are created.

### Milestone 3: Build Silent MP4
Deliverables:
- `build_video.py`
- FFmpeg invocation wrapper

Acceptance criteria:
1. `video.mp4` is generated.
2. Resolution is 1920x1080.
3. Codec is H.264.
4. Video plays locally with no audio stream required.

### Milestone 4: Deterministic Metadata
Deliverables:
- `metadata.py`

Acceptance criteria:
1. Title is generated from a fixed template.
2. Description includes date, rating, and themes.
3. Tags are deterministic and bounded.

### Milestone 5: YouTube Upload
Deliverables:
- `upload_youtube.py`
- token load/refresh logic

Acceptance criteria:
1. The generated video uploads successfully.
2. Returned video metadata is stored.
3. Upload is skipped if already completed and not forced.

### Milestone 6: Local Scheduling and Idempotency
Deliverables:
- `state_manager.py`
- scheduler documentation

Acceptance criteria:
1. Daily reruns do not duplicate uploads.
2. Step markers survive process interruption.
3. Non-zero exit status is returned on failure.
4. Scheduler can call the command without manual interaction.

---

## 13. Simplified Video Specification

### Visual Structure
1. Intro card
2. Initial board position
3. Fixed think-time window
4. Official solution playback
5. End card

### Video Defaults
- Resolution: 1920x1080
- FPS: 30
- Codec: H.264
- Audio: none
- Background: simple static style
- Board: centered and large
- Text overlays: minimal

### Overlay Data
- title
- puzzle date
- rating
- themes
- side to move

### Avoid in V1
- piece animation complexity
- fancy transitions
- branding polish
- intros with logos
- multiple layouts

---

## 14. Metadata Templates

### Title Template
`Lichess Daily Puzzle - {date} - Rating {rating}`

### Description Template
```text
Daily Lichess puzzle for {date}.

Rating: {rating}
Themes: {themes_csv}
Puzzle ID: {puzzle_id}

This video shows the starting position, a short think-time window, and the official solution sequence.
```

### Tags Template
- `lichess daily puzzle`
- `chess puzzle`
- `chess tactics`
- `{date}`
- `{rating}`
- each theme as its own tag

---

## 15. Testing Strategy

### Unit Tests
1. Parse Lichess response into internal model.
2. Determine side to move from FEN.
3. Validate solution list handling.
4. Validate deterministic metadata generation.

### Integration Tests
1. Fetch a real or fixture puzzle.
2. Render a small test frame set.
3. Build a short MP4.
4. Skip YouTube upload during normal CI tests.

### Smoke Test
One command should verify:
- config loads
- FFmpeg exists
- credentials paths are readable
- artifact directory is writable

---

## 16. Logging Contract

Each run should write structured logs with fields such as:
- timestamp
- level
- step
- event
- target_date
- artifact_path
- error_type
- message

Preferred format:
JSON lines

Example event types:
- `run_started`
- `fetch_started`
- `fetch_completed`
- `render_started`
- `video_built`
- `upload_started`
- `upload_completed`
- `run_completed`
- `run_failed`

---

## 17. Error Handling Rules

1. Fail fast on invalid or incomplete puzzle data.
2. Do not write `.done` unless all enabled steps complete successfully.
3. If upload fails, preserve the generated video for retry.
4. Every exception should produce:
   - log entry
   - step-specific error JSON file
   - non-zero process exit

---

## 18. Scheduler Guidance

The application should not contain scheduler-specific logic.  
Scheduling belongs to the operating system or external task runner.

Examples:
- macOS: `launchd`
- Linux: `cron` or `systemd` timer
- Windows: Task Scheduler

The app’s responsibility is only:
- one-shot execution
- clean exit codes
- idempotent rerun behavior

---

## 19. Security Rules

1. Never commit OAuth tokens.
2. Never commit client secrets.
3. Keep `credentials/` in `.gitignore`.
4. Prefer environment variables or local untracked files for secret paths.
5. Avoid printing tokens or secret file contents in logs.

---

## 20. Design Decisions

### Decision 1: Silent video only
Reason:
This removes LLM and TTS complexity and makes the first milestone achievable.

### Decision 2: Local scheduler instead of cloud automation
Reason:
This matches the current goal of implementing locally first.

### Decision 3: Deterministic metadata instead of AI metadata
Reason:
This reduces variability and debugging effort.

### Decision 4: File-based state markers
Reason:
Simple, inspectable, and adequate for a single-machine daily job.

---

## 21. Deferred Future Enhancements

Do not implement these in V1:
1. Spoken narration
2. TTS
3. LLM annotations
4. Puzzle explanation overlays
5. Thumbnail generation
6. Automatic publish scheduling windows
7. Failure webhooks
8. Multi-channel upload support
9. Multiple puzzle formats
10. Branding templates

---

## 22. Machine-Readable Summary

```json
{
  "project_name": "Lichess Daily Puzzle YouTube Bot",
  "scope_version": "local_mvp_silent_video",
  "primary_goal": "Fetch daily puzzle, render silent local MP4, upload to YouTube, run daily on local scheduler",
  "language": "Python",
  "runtime_model": "single-machine local execution",
  "in_scope": [
    "Lichess daily puzzle fetch",
    "puzzle parsing",
    "board rendering",
    "silent MP4 creation",
    "deterministic metadata",
    "YouTube upload",
    "local scheduling compatibility",
    "idempotent reruns"
  ],
  "out_of_scope": [
    "LLM analysis",
    "narration",
    "TTS",
    "audio",
    "thumbnails",
    "SEO generation by AI",
    "webhooks",
    "cloud execution"
  ],
  "primary_command": "python -m src.main run",
  "artifacts_root": "./artifacts/{date}/",
  "completion_marker": ".done",
  "step_markers": [
    ".step_fetch_done",
    ".step_render_done",
    ".step_video_done",
    ".step_upload_done"
  ]
}
```

---

## 23. Immediate Next Step for Code Generation

Create the repository skeleton and implement the first vertical slice in this order:
1. config loader
2. puzzle fetcher
3. puzzle model normalizer
4. frame renderer for start position only
5. FFmpeg video builder for a short silent test video
6. basic CLI orchestration
7. local artifact and marker handling
8. YouTube upload integration

This sequence produces visible progress quickly and reduces integration risk.
