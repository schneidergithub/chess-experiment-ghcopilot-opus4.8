"""Vendored minimal fallbacks used ONLY when the spec'd third-party libraries
(python-chess, cairosvg) are not importable in the environment.

These exist so the Milestone 1 pipeline can still produce real, playable
artifacts in sandboxed/offline conditions. In a normal environment with the
declared dependencies installed, these modules are never imported.
"""
