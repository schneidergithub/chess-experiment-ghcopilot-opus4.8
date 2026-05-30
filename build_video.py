"""Build a silent MP4 from the rendered PNG frame sequence using FFmpeg."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


class VideoBuildError(RuntimeError):
    """Raised when FFmpeg is missing or the encode fails."""


def resolve_ffmpeg(config: dict[str, Any]) -> str:
    binary = (config.get("ffmpeg") or {}).get("binary", "ffmpeg")
    found = shutil.which(binary)
    if found:
        return found
    # Allow an absolute path configured directly.
    if Path(binary).exists():
        return binary
    raise VideoBuildError(f"FFmpeg binary not found on PATH: {binary}")


def build_video(
    frames_dir: str | Path,
    out_path: str | Path,
    config: dict[str, Any],
) -> Path:
    """Encode frame_%05d.png in ``frames_dir`` into a silent MP4 at ``out_path``."""
    frames_dir = Path(frames_dir)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    video = config["video"]
    fps = int(video["fps"])
    codec = video.get("codec", "libx264")
    pix_fmt = video.get("pixel_format", "yuv420p")

    ffmpeg = resolve_ffmpeg(config)
    pattern = str(frames_dir / "frame_%05d.png")

    cmd = [
        ffmpeg,
        "-y",
        "-framerate", str(fps),
        "-i", pattern,
        "-c:v", codec,
        "-pix_fmt", pix_fmt,
        "-an",  # silent: no audio track
        str(out_path),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise VideoBuildError(
            f"ffmpeg failed (exit {proc.returncode}): {proc.stderr.strip()[-800:]}"
        )
    if not out_path.exists() or out_path.stat().st_size == 0:
        raise VideoBuildError(f"ffmpeg produced no output at {out_path}")
    return out_path
