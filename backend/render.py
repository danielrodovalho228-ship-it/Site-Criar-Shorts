"""Render engine — PURE (Part C1.5).

``render()`` knows nothing about HTTP: it takes a config dict, reports progress
through a callback, and returns the path to the finished mp4. It is the SAME
motor used by the CLI and the site.

╔══════════════════════════════════════════════════════════════════════════╗
║  PORT SITE — paste the ALREADY-TESTED short_factory.py logic here.        ║
║                                                                            ║
║  REGRA CENTRAL (do plano): NÃO simplificar nem remover efeitos. O motor   ║
║  já testado tem: zoompan alternado (zoom-in/out + pan), punch 0.15s entre ║
║  cenas, drawtext do hook (frame 0) e do CTA (janela start..end), legendas ║
║  via subtitles=...:force_style com caption_fixes aplicados no SRT, e o    ║
║  amix de narração + música em loop + SFX posicionados com adelay.         ║
║                                                                            ║
║  Melhorias OBRIGATÓRIAS de produção (Parte C3 + Sprint 1) já preparadas   ║
║  como helpers abaixo — use-as ao colar o motor:                          ║
║    • pathlib em todos os caminhos, forward slashes ao chamar ffmpeg       ║
║    • NUNCA -shortest → usar -map explícito                                 ║
║    • concat com  -f concat -safe 0                                         ║
║    • warning se qualquer imagem ficar > MAX_IMAGE_SECONDS na tela         ║
║    • warning se o nome do áudio não contiver palavras do nome do projeto  ║
║    • timeout de RENDER_TIMEOUT_S por job                                   ║
║    • log completo do ffmpeg salvo por projeto (output/ffmpeg.log)         ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Callable, List

# Output spec — vertical short.
WIDTH, HEIGHT = 1080, 1920
FPS = 30

# Production guardrails (Part C3).
MAX_IMAGE_SECONDS = 5.0     # nenhuma imagem parada > 5s sem aviso
RENDER_TIMEOUT_S = 300      # 5 min por job

# Progress callback: progress_cb(percent: float, message: str) -> None
ProgressCb = Callable[[float], None]
ProgressMsgCb = Callable[[float, str], None]


class PortPendingError(NotImplementedError):
    """Raised until short_factory.py is ported into :func:`render`."""


# --------------------------------------------------------------------------- #
# Reusable production helpers (safe to keep as-is when porting the motor)
# --------------------------------------------------------------------------- #
def ff_path(p: Path | str) -> str:
    """Absolute path with forward slashes — safe to hand to ffmpeg on any OS."""
    return Path(p).resolve().as_posix()


def check_image_durations(images: list, total_duration: float) -> List[str]:
    """Warn (return messages) if any image sits on screen longer than allowed.

    ``images`` is a list of ImageClip-like objects with ``.file`` and ``.start``.
    The last image runs until ``total_duration``.
    """
    warnings: List[str] = []
    starts = [float(getattr(img, "start", 0.0)) for img in images]
    for i, img in enumerate(images):
        end = starts[i + 1] if i + 1 < len(images) else float(total_duration)
        on_screen = end - starts[i]
        if on_screen > MAX_IMAGE_SECONDS:
            name = getattr(img, "file", f"#{i}")
            warnings.append(
                f"⚠️ Imagem '{Path(str(name)).name}' fica {on_screen:.1f}s na tela "
                f"(> {MAX_IMAGE_SECONDS:.0f}s) — risco de 'vídeo parado'."
            )
    return warnings


def check_audio_name(audio_file: str | None, project_name: str) -> List[str]:
    """Warn if the audio filename shares no word with the project name.

    Protects against the production bug where the wrong MP3 got attached.
    """
    if not audio_file:
        return []
    warnings: List[str] = []
    audio_stem = Path(str(audio_file)).stem.lower()
    proj_words = {w for w in re.split(r"[^a-z0-9]+", project_name.lower()) if len(w) >= 3}
    if proj_words and not any(w in audio_stem for w in proj_words):
        warnings.append(
            f"⚠️ Áudio '{Path(str(audio_file)).name}' não parece pertencer ao "
            f"projeto '{project_name}' — confira se o MP3 está correto."
        )
    return warnings


def run_ffmpeg(cmd: List[str], log_path: Path, timeout: int = RENDER_TIMEOUT_S) -> None:
    """Run ffmpeg, tee the full output to ``log_path``, raise on failure/timeout.

    NOTE: build ``cmd`` with explicit ``-map`` (NUNCA ``-shortest``) and, for
    the concat step, ``-f concat -safe 0``.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        log_path.write_bytes(exc.output or b"")
        raise RuntimeError(f"ffmpeg excedeu o timeout de {timeout}s") from exc

    log_path.write_bytes(proc.stdout or b"")
    if proc.returncode != 0:
        tail = (proc.stdout or b"").decode("utf-8", "replace").splitlines()[-15:]
        raise RuntimeError(
            "ffmpeg falhou (rc="
            + str(proc.returncode)
            + "):\n"
            + "\n".join(tail)
        )


# --------------------------------------------------------------------------- #
# The engine (pure)
# --------------------------------------------------------------------------- #
def render(config: dict, work_dir: Path, progress_cb: ProgressMsgCb) -> str:
    """Assemble a 1080x1920 short from ``config`` and return the mp4 path.

    Args:
        config: serialized ``ProjectConfig`` (audio, images, hook, cta, music,
            sfx, srt, caption_fixes, caption_style).
        work_dir: the project's ``output/`` directory (ffmpeg.log lives here).
        progress_cb: ``progress_cb(percent, message)`` — 0..100.

    Returns:
        Absolute path to the rendered ``short.mp4``.

    Raises:
        PortPendingError: until short_factory.py is ported below.
    """
    # >>> BEGIN PORT: paste the tested short_factory.py pipeline here. <<<
    #
    # Recommended shape when porting:
    #   1. progress_cb(2, "Validando assets")     -> check_image_durations / check_audio_name
    #   2. progress_cb(10, "Renderizando cenas")   -> per-image zoompan clips
    #   3. progress_cb(55, "Concatenando (punch)")  -> concat -f concat -safe 0
    #   4. progress_cb(70, "Aplicando legendas")    -> subtitles=...:force_style
    #   5. progress_cb(85, "Mixando áudio")          -> amix narração+música(loop)+SFX(adelay)
    #   6. progress_cb(100, "Concluído")            -> return ff_path(output/short.mp4)
    #
    # Use run_ffmpeg(cmd, work_dir / "ffmpeg.log") for every ffmpeg invocation
    # so the full log is saved per project.
    #
    raise PortPendingError(
        "render() ainda não foi portado. Cole o short_factory.py testado no "
        "PORT SITE de backend/render.py (mantendo todos os efeitos)."
    )
    # >>> END PORT <<<
