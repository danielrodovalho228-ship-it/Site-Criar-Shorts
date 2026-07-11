"""Media probing helpers (ffprobe)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def probe_duration(path: Path) -> float:
    """Return media duration in seconds via ffprobe, or 0.0 if unavailable."""
    try:
        out = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                Path(path).resolve().as_posix(),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
        if out.returncode != 0:
            return 0.0
        data = json.loads(out.stdout.decode("utf-8", "replace"))
        return float(data.get("format", {}).get("duration", 0.0))
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
        return 0.0
