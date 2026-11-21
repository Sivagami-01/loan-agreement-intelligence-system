"""scripts/offline_guard.py

Offline-proof network guard for zero-API-call tests.
Patches GeminiClient._send_request so any attempted live Gemini HTTP request
immediately increments `attempts`, records the model, and raises
OfflineLiveCallBlockedError without making network calls or sleeping.
"""

from __future__ import annotations

import os
import runpy
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.llm.gemini_client import GeminiClient


class OfflineLiveCallBlockedError(RuntimeError):
    """Raised immediately when offline_guard blocks an attempted live Gemini call."""


@dataclass
class OfflineGuardState:
    attempts: int = 0
    attempted_models: list[str] = field(default_factory=list)


@contextmanager
def offline_guard() -> Iterator[OfflineGuardState]:
    """Blocks any live Gemini HTTP request inside the context and counts attempts."""
    state = OfflineGuardState()
    orig_send = GeminiClient._send_request

    def _blocked_send(
        self: GeminiClient,
        model: str,
        prompt: str,
        image_bytes: bytes | None = None,
        mime_type: str = "image/png",
        temperature: float | None = None,
    ) -> tuple[str, float]:
        state.attempts += 1
        state.attempted_models.append(str(model))
        raise OfflineLiveCallBlockedError(
            f"Offline guard blocked attempted live Gemini call #{state.attempts} (model={model})."
        )

    GeminiClient._send_request = _blocked_send  # type: ignore[method-assign]
    try:
        yield state
    finally:
        GeminiClient._send_request = orig_send  # type: ignore[method-assign]


def run_script_under_offline_guard(script_path: Path, root: Path) -> tuple[int, OfflineGuardState]:
    """Executes another Python script in-process under offline_guard."""
    with offline_guard() as guard:
        orig_argv = list(sys.argv)
        try:
            sys.argv = [str(script_path)]
            try:
                runpy.run_path(str(script_path), run_name="__main__")
                rc = 0
            except SystemExit as exc:
                code = exc.code
                rc = 0 if code in (None, 0) else (int(code) if isinstance(code, int) else 1)
        finally:
            sys.argv = orig_argv
    return rc, guard


def _cli_main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/offline_guard.py <script_path>", file=sys.stderr)
        return 2
    target = Path(sys.argv[1]).resolve()
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.chdir(str(root))
    rc, guard = run_script_under_offline_guard(target, root)
    print(f"OFFLINE_GUARD_ATTEMPTS={guard.attempts} ATTEMPTED_MODELS={guard.attempted_models}", flush=True)
    if guard.attempts > 0:
        return 1
    return rc


if __name__ == "__main__":
    raise SystemExit(_cli_main())
