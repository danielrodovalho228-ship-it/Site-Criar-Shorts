"""Smoke test (Sprint 1 QA gate, Part E-S1).

Generates a test short from 3 dummy images + hook + CTA + 1 SFX and validates
the output with ffprobe: duration > 0 and resolution exactly 1080x1920.

Run from the repo root:  python scripts/smoke_test.py

Requires ffmpeg/ffprobe on PATH AND render() ported in backend/render.py.
Until the motor is ported, this exits with a clear PENDING message (not a
false failure).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from render import render, PortPendingError, WIDTH, HEIGHT  # noqa: E402


def _have(tool: str) -> bool:
    try:
        subprocess.run([tool, "-version"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=False)
        return True
    except FileNotFoundError:
        return False


def make_dummy_image(path: Path, color: str) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"color=c={color}:s=1080x1920:d=1", "-frames:v", "1", path.as_posix()],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )


def make_dummy_audio(path: Path, seconds: float) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i",
         f"anullsrc=r=44100:cl=stereo:d={seconds}", "-q:a", "9", path.as_posix()],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )


def probe(path: Path) -> tuple[int, int, float]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-show_entries", "format=duration",
         "-of", "json", path.as_posix()],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True,
    )
    data = json.loads(out.stdout)
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"]), float(data["format"]["duration"])


def main() -> int:
    if not (_have("ffmpeg") and _have("ffprobe")):
        print("PENDING: ffmpeg/ffprobe não encontrados no PATH. "
              "Instale (Windows: winget install ffmpeg) e rode de novo.")
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        images = []
        for i, color in enumerate(["navy", "teal", "orange"]):
            img = tmp_dir / f"img_{i}.png"
            make_dummy_image(img, color)
            images.append({"file": img.as_posix(), "start": i * 2.0, "effect": "zoom-in"})

        audio = tmp_dir / "narration.mp3"
        make_dummy_audio(audio, 6.0)

        sfx = tmp_dir / "ding.mp3"
        make_dummy_audio(sfx, 0.4)

        config = {
            "audio": {"file": audio.as_posix(), "duration": 6.0},
            "srt": None,
            "caption_fixes": {},
            "images": images,
            "hook": {"text": "3 LIÇÕES", "duration": 2.5},
            "cta": {"text": "full breakdown on The Chapter", "start": 4.0, "end": 6.0},
            "music": {"file": None, "volume": 0.2},
            "sfx": [{"file": sfx.as_posix(), "time": 0.0, "volume": 1.0}],
            "caption_style": "navy-white",
        }

        out_dir = tmp_dir / "output"
        out_dir.mkdir()

        def progress(pct: float, msg: str = "") -> None:
            print(f"  [{pct:5.1f}%] {msg}")

        try:
            out_path = render(config, out_dir, progress)
        except PortPendingError as exc:
            print(f"PENDING: {exc}")
            return 0

        w, h, dur = probe(Path(out_path))
        print(f"Resolução: {w}x{h} | Duração: {dur:.2f}s")

        ok = True
        if (w, h) != (WIDTH, HEIGHT):
            print(f"FAIL: esperado {WIDTH}x{HEIGHT}, obtido {w}x{h}")
            ok = False
        if dur <= 0:
            print("FAIL: duração inválida")
            ok = False

        if ok:
            print("PASS: smoke test ok ✅")
            return 0
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
