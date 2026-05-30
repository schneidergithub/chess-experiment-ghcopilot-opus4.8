"""Provide a ``chess`` module, preferring the real python-chess package.

Modules in this project do ``from src._compat import chess`` so that:
  * In a normal environment, the real ``python-chess`` is used (spec path).
  * In an offline/sandboxed environment without it, a minimal vendored
    fallback is substituted so the pipeline still runs end to end.

A flag ``USING_REAL_CHESS`` records which backend is active.
"""

from __future__ import annotations

import sys

try:
    import chess as _real_chess  # type: ignore

    chess = _real_chess
    USING_REAL_CHESS = True
except Exception:  # pragma: no cover - depends on environment
    from src._vendor import chess_fallback as _fb

    # Register so that ``import chess`` elsewhere also resolves to the fallback.
    sys.modules.setdefault("chess", _fb)
    chess = _fb
    USING_REAL_CHESS = False
