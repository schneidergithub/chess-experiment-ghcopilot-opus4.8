"""Render puzzle scenes to PNG frames.

Primary path (per Milestone 1 spec):
  * Build the board image with ``chess.svg.board()`` (filled SVG piece set).
  * Rasterize the SVG to PNG with ``cairosvg``.
  * Composite the board onto a 1920x1080 canvas with header text, vertically
    centered in the space below the header, with no clipping.

Scenes rendered: intro, think-time, solution move, outro.

A self-contained fallback renderer is used only when ``cairosvg`` (and/or the
``chess`` SVG path) is unavailable in the environment. The fallback draws a
real, filled-piece board so the pipeline still produces playable artifacts;
it is never used when the spec'd libraries are importable.
"""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from src._compat import chess, USING_REAL_CHESS

try:  # primary rasterizer per spec
    import cairosvg  # type: ignore

    _HAVE_CAIROSVG = True
except Exception:  # pragma: no cover - depends on environment
    _HAVE_CAIROSVG = False

if USING_REAL_CHESS:
    try:
        import chess.svg as chess_svg  # type: ignore

        _HAVE_CHESS_SVG = True
    except Exception:  # pragma: no cover
        _HAVE_CHESS_SVG = False
else:
    _HAVE_CHESS_SVG = False


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Board bitmap generation
# ---------------------------------------------------------------------------

def _board_png_via_cairosvg(
    board: chess.Board,
    size: int,
    show_coordinates: bool,
    lastmove: chess.Move | None,
    arrows: list[Any] | None,
) -> Image.Image:
    """Render the board to a PIL image using chess.svg + cairosvg (spec path)."""
    svg_markup = chess_svg.board(
        board=board,
        size=size,
        coordinates=show_coordinates,
        lastmove=lastmove,
        arrows=arrows or [],
    )
    png_bytes = cairosvg.svg2png(
        bytestring=svg_markup.encode("utf-8"),
        output_width=size,
        output_height=size,
    )
    return Image.open(io.BytesIO(png_bytes)).convert("RGBA")


# --- Fallback renderer (filled pieces, used only without cairosvg) ---------

_PIECE_UNICODE = {
    "P": "\u2659", "N": "\u2658", "B": "\u2657", "R": "\u2656", "Q": "\u2655", "K": "\u2654",
    "p": "\u265F", "n": "\u265E", "b": "\u265D", "r": "\u265C", "q": "\u265B", "k": "\u265A",
}

_LIGHT = (240, 217, 181, 255)
_DARK = (181, 136, 99, 255)
_HILITE = (205, 210, 106, 200)


def _board_png_fallback(
    board: chess.Board,
    size: int,
    show_coordinates: bool,
    lastmove: chess.Move | None,
) -> Image.Image:
    """Draw a filled-piece board without cairosvg.

    Pieces are drawn as solid filled glyphs (not outline/text-only): a filled
    body shape per piece type plus a glyph, so squares read as real pieces.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    sq = size // 8
    glyph_font = _load_font(int(sq * 0.74))

    last_squares = set()
    if lastmove is not None:
        last_squares = {lastmove.from_square, lastmove.to_square}

    for rank in range(8):  # 0 = rank 8 (top)
        for file in range(8):
            x0 = file * sq
            y0 = rank * sq
            x1 = x0 + sq
            y1 = y0 + sq
            is_light = (file + rank) % 2 == 0
            draw.rectangle([x0, y0, x1, y1], fill=_LIGHT if is_light else _DARK)

            board_square = chess.square(file, 7 - rank)
            if board_square in last_squares:
                overlay = Image.new("RGBA", (sq, sq), _HILITE)
                img.alpha_composite(overlay, (x0, y0))

            piece = board.piece_at(board_square)
            if piece is None:
                continue
            symbol = piece.symbol()
            is_white = symbol.isupper()
            body = (250, 250, 250, 255) if is_white else (40, 40, 40, 255)
            edge = (30, 30, 30, 255) if is_white else (220, 220, 220, 255)
            cx = x0 + sq / 2
            cy = y0 + sq / 2
            r = sq * 0.34
            # Filled disc as the piece body so it is never a bare glyph.
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=body, outline=edge, width=max(2, sq // 40))
            glyph = _PIECE_UNICODE.get(symbol, symbol)
            glyph_color = (30, 30, 30, 255) if is_white else (245, 245, 245, 255)
            bbox = draw.textbbox((0, 0), glyph, font=glyph_font)
            gw = bbox[2] - bbox[0]
            gh = bbox[3] - bbox[1]
            draw.text(
                (cx - gw / 2 - bbox[0], cy - gh / 2 - bbox[1]),
                glyph,
                font=glyph_font,
                fill=glyph_color,
            )

    if show_coordinates:
        coord_font = _load_font(max(12, sq // 6))
        files = "abcdefgh"
        for file in range(8):
            draw.text((file * sq + 4, size - sq // 6 - 6), files[file], font=coord_font, fill=(80, 80, 80, 255))
        for rank in range(8):
            draw.text((4, rank * sq + 4), str(8 - rank), font=coord_font, fill=(80, 80, 80, 255))

    return img


def render_board_image(
    board: chess.Board,
    size: int,
    show_coordinates: bool,
    lastmove: chess.Move | None = None,
    arrows: list[Any] | None = None,
) -> Image.Image:
    """Return a square RGBA board image, using the spec path when available."""
    if _HAVE_CAIROSVG and _HAVE_CHESS_SVG:
        return _board_png_via_cairosvg(board, size, show_coordinates, lastmove, arrows)
    return _board_png_fallback(board, size, show_coordinates, lastmove)


# ---------------------------------------------------------------------------
# Scene composition
# ---------------------------------------------------------------------------

_BG = (24, 26, 30, 255)
_FG = (235, 235, 235, 255)
_ACCENT = (120, 190, 255, 255)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def compose_scene(
    board: chess.Board,
    width: int,
    height: int,
    board_size: int,
    show_coordinates: bool,
    title: str,
    subtitle: str,
    lastmove: chess.Move | None = None,
    arrows: list[Any] | None = None,
) -> Image.Image:
    """Compose a full 1920x1080 frame: header text + centered board."""
    canvas = Image.new("RGBA", (width, height), _BG)
    draw = ImageDraw.Draw(canvas)

    title_font = _load_font(64)
    sub_font = _load_font(38)

    header_top = 40
    y = header_top
    for line in _wrap(draw, title, title_font, width - 160):
        tw = draw.textlength(line, font=title_font)
        draw.text(((width - tw) / 2, y), line, font=title_font, fill=_FG)
        y += 74
    for line in _wrap(draw, subtitle, sub_font, width - 160):
        tw = draw.textlength(line, font=sub_font)
        draw.text(((width - tw) / 2, y), line, font=sub_font, fill=_ACCENT)
        y += 48

    header_bottom = y + 20

    # Clamp board size so it never clips in the remaining vertical space.
    available_h = height - header_bottom - 40
    safe_size = min(board_size, available_h, width - 80)
    safe_size = max(64, safe_size)

    board_img = render_board_image(board, safe_size, show_coordinates, lastmove, arrows)

    bx = (width - safe_size) // 2
    # Vertically center the board within the space below the header.
    by = header_bottom + (available_h - safe_size) // 2
    by = max(header_bottom, by)
    canvas.alpha_composite(board_img, (bx, by))

    return canvas


def render_scenes(
    puzzle: Any,
    config: dict[str, Any],
    frames_dir: str | Path,
) -> list[Path]:
    """Render intro, think-time, solution, and outro scenes to PNG frames.

    Returns the ordered list of frame paths written.
    """
    frames_dir = Path(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)

    video = config["video"]
    render = config["render"]
    width = int(video["width"])
    height = int(video["height"])
    fps = int(video["fps"])
    board_size = int(render["board_size"])
    show_coords = bool(render["show_coordinates"])

    base_board = chess.Board(puzzle.fen)
    side = puzzle.side_to_move.capitalize()
    rating_txt = f"Rating {puzzle.rating}" if puzzle.rating else ""
    themes_txt = ", ".join(puzzle.themes[:4])

    # Build the scene plan as (title, subtitle, board, lastmove, seconds).
    scenes: list[tuple[str, str, chess.Board, chess.Move | None, float]] = []

    # Intro: starting position, whose move.
    last_mv = None
    if puzzle.last_move:
        try:
            last_mv = chess.Move.from_uci(puzzle.last_move)
        except ValueError:
            last_mv = None
    scenes.append(
        (
            "Daily Chess Puzzle",
            f"{side} to move  -  {rating_txt}".strip(" -"),
            base_board.copy(),
            last_mv,
            float(render["intro_seconds"]),
        )
    )

    # Think time: same position, prompt to solve.
    scenes.append(
        (
            "Find the best move",
            themes_txt or f"{side} to play",
            base_board.copy(),
            last_mv,
            float(render["think_seconds"]),
        )
    )

    # Solution: play through the solution moves, one sub-scene each.
    sol_board = base_board.copy()
    sol_seconds = float(render["solution_seconds"])
    legal_solution = True
    for i, uci in enumerate(puzzle.solution):
        try:
            mv = chess.Move.from_uci(uci)
        except ValueError:
            legal_solution = False
            break
        if mv not in sol_board.legal_moves:
            legal_solution = False
            break
        san = sol_board.san(mv)
        sol_board.push(mv)
        scenes.append(
            (
                "Solution",
                f"{i + 1}. {san}",
                sol_board.copy(),
                mv,
                sol_seconds,
            )
        )
    if not legal_solution:
        # Still produce a coherent video; note the issue in the subtitle.
        scenes.append(
            (
                "Solution",
                "(solution sequence unavailable)",
                base_board.copy(),
                last_mv,
                sol_seconds,
            )
        )

    # Outro.
    scenes.append(
        (
            "Solved!",
            "New puzzle daily",
            sol_board.copy(),
            None,
            float(render["outro_seconds"]),
        )
    )

    # Render: each scene is a still held for (seconds * fps) frames. We render
    # the still once and copy it across the held frames to keep it fast.
    frame_paths: list[Path] = []
    frame_index = 0
    for title, subtitle, board, mv, seconds in scenes:
        n_frames = max(1, int(round(seconds * fps)))
        still = compose_scene(
            board=board,
            width=width,
            height=height,
            board_size=board_size,
            show_coordinates=show_coords,
            title=title,
            subtitle=subtitle,
            lastmove=mv,
        ).convert("RGB")
        for _ in range(n_frames):
            fp = frames_dir / f"frame_{frame_index:05d}.png"
            still.save(fp)
            frame_paths.append(fp)
            frame_index += 1

    return frame_paths
