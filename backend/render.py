"""Render engine — PURE (Part C1.5).

``render()`` knows nothing about HTTP: it takes a config dict, reports progress
through a callback, and returns the path to the finished mp4. It is the SAME
motor used by the CLI and the site.

╔══════════════════════════════════════════════════════════════════════════╗
║  MOTOR PORTADO do short_factory.py testado (Sprint 1).                    ║
║  Pipeline COMPLETO, sem simplificar:                                       ║
║    • zoompan alternado: zoom-in 1.0->1.12 / zoom-out 1.12->1.0            ║
║      (+ pan-left/right, fade, static)                                      ║
║    • punch de 0.15s na entrada de cada clipe (pop de +8% que decai)      ║
║    • drawtext do HOOK: 2 linhas, navy #1A233C + coral #E76F51,           ║
║      contorno branco, visível do frame 0 SEM fade                        ║
║    • drawtext do CTA: coral, contorno branco, janela start..end          ║
║    • legendas: subtitles + force_style navy/contorno branco, com         ║
║      caption_fixes aplicados no SRT                                        ║
║    • amix: narração + música em loop (volume do config) + SFX com adelay  ║
║                                                                            ║
║  Hardening de produção integrado (Parte C3):                             ║
║    pathlib + forward slashes | NUNCA -shortest (usa -map + -t) |          ║
║    concat -f concat -safe 0 | aviso de imagem >5s | aviso de MP3 trocado  ║
║    | timeout 5 min | log completo do ffmpeg por projeto (ffmpeg.log)      ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Callable, List, Optional

# Output spec — vertical short.
WIDTH, HEIGHT = 1080, 1920
FPS = 30

# Production guardrails (Part C3).
MAX_IMAGE_SECONDS = 5.0     # nenhuma imagem parada > 5s sem aviso
RENDER_TIMEOUT_S = 300      # 5 min por job

# Effect tuning (reconciliado com o short_factory.py original).
ZOOM_MIN, ZOOM_MAX = 1.0, 1.12
PUNCH_AMOUNT = 0.06         # +6% no pop de entrada (motor original)
PUNCH_SECONDS = 0.15        # dura 0.15s

# Brand palette (drawtext / legendas).
NAVY = "0x1A233C"
CORAL = "0xE76F51"
WHITE = "white"

# Progress callback: progress_cb(percent, message) -> None
ProgressMsgCb = Callable[[float, str], None]


class PortPendingError(NotImplementedError):
    """Mantido por compatibilidade; o motor já foi portado."""


# --------------------------------------------------------------------------- #
# Reusable production helpers
# --------------------------------------------------------------------------- #
def ff_path(p: Path | str) -> str:
    """Absolute path with forward slashes — safe to hand to ffmpeg on any OS."""
    return Path(p).resolve().as_posix()


def check_image_durations(images: list, total_duration: float) -> List[str]:
    """Warn if any image sits on screen longer than allowed (anti 'vídeo parado')."""
    warnings: List[str] = []
    starts = [float(img.get("start", 0.0)) for img in images]
    for i, img in enumerate(images):
        end = starts[i + 1] if i + 1 < len(images) else float(total_duration)
        on_screen = end - starts[i]
        if on_screen > MAX_IMAGE_SECONDS:
            name = img.get("file", f"#{i}")
            warnings.append(
                f"AVISO: Imagem '{Path(str(name)).name}' fica {on_screen:.1f}s na "
                f"tela (> {MAX_IMAGE_SECONDS:.0f}s) -- risco de 'vídeo parado'."
            )
    return warnings


def check_audio_name(audio_file: Optional[str], project_name: str) -> List[str]:
    """Warn if the audio filename shares no word with the project name."""
    if not audio_file:
        return []
    warnings: List[str] = []
    audio_stem = Path(str(audio_file)).stem.lower()
    proj_words = {w for w in re.split(r"[^a-z0-9]+", project_name.lower()) if len(w) >= 3}
    if proj_words and not any(w in audio_stem for w in proj_words):
        warnings.append(
            f"AVISO: Áudio '{Path(str(audio_file)).name}' não parece pertencer ao "
            f"projeto '{project_name}' -- confira se o MP3 está correto."
        )
    return warnings


def run_ffmpeg(cmd: List[str], log_path: Path, timeout: int = RENDER_TIMEOUT_S) -> None:
    """Run ffmpeg, append the full output to ``log_path``, raise on failure/timeout."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        log.write(("\n$ " + " ".join(cmd) + "\n").encode("utf-8", "replace"))
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        with log_path.open("ab") as log:
            log.write(exc.output or b"")
        raise RuntimeError(f"ffmpeg excedeu o timeout de {timeout}s") from exc

    with log_path.open("ab") as log:
        log.write(proc.stdout or b"")
    if proc.returncode != 0:
        tail = (proc.stdout or b"").decode("utf-8", "replace").splitlines()[-15:]
        raise RuntimeError("ffmpeg falhou (rc=" + str(proc.returncode) + "):\n" + "\n".join(tail))


# --------------------------------------------------------------------------- #
# Fonts
# --------------------------------------------------------------------------- #
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def _font_file() -> Optional[str]:
    for cand in _FONT_CANDIDATES:
        if Path(cand).exists():
            return ff_path(cand)
    return None


# --------------------------------------------------------------------------- #
# Timeline: turn images[] + audio duration into per-clip durations
# --------------------------------------------------------------------------- #
def _clip_durations(images: list, total_duration: float) -> List[float]:
    n = len(images)
    if n == 0:
        return []
    if total_duration <= 0:
        total_duration = n * 3.0
    starts = [float(img.get("start", 0.0)) for img in images]
    # If starts are unusable (not increasing), distribute uniformly.
    increasing = all(starts[i] < starts[i + 1] for i in range(n - 1)) if n > 1 else True
    if not increasing or (n > 1 and starts == [0.0] * n):
        per = total_duration / n
        return [per] * n
    durations: List[float] = []
    for i in range(n):
        end = starts[i + 1] if i + 1 < n else total_duration
        durations.append(max(0.2, end - starts[i]))
    return durations


# --------------------------------------------------------------------------- #
# Per-image clip (zoompan alternado + punch de 0.15s)
# --------------------------------------------------------------------------- #
def _zoompan_expr(effect: str, duration: float) -> tuple[str, str, str]:
    """Return (z, x, y) expressions for zoompan. 'on' = output frame index (0-based)."""
    n_frames = max(2, int(round(duration * FPS)))
    inc = (ZOOM_MAX - ZOOM_MIN) / (n_frames - 1)
    punch_frames = max(1, int(round(PUNCH_SECONDS * FPS)))
    # Punch pop (motor original): if(lt(on,N), amount*(1-on/N), 0) somado ao z.
    punch = (
        f"if(lt(on\\,{punch_frames})\\,{PUNCH_AMOUNT}*(1-on/{punch_frames})\\,0)"
    )
    x_center = "iw/2-(iw/zoom/2)"
    y_center = "ih/2-(ih/zoom/2)"

    if effect == "zoom-out":
        z = f"max({ZOOM_MAX}-{inc}*on\\,{ZOOM_MIN})+{punch}"
        return z, x_center, y_center
    if effect == "pan-left":
        z = f"{ZOOM_MAX}+{punch}"
        x = f"(iw-iw/zoom)*(1-on/{n_frames - 1})"
        return z, x, y_center
    if effect == "pan-right":
        z = f"{ZOOM_MAX}+{punch}"
        x = f"(iw-iw/zoom)*(on/{n_frames - 1})"
        return z, x, y_center
    if effect == "static":
        z = f"{ZOOM_MIN}+{punch}"
        return z, x_center, y_center
    if effect == "fade":
        # static base; fade handled separately, keep gentle punch
        z = f"{ZOOM_MIN}+{punch}"
        return z, x_center, y_center
    # default zoom-in
    z = f"min({ZOOM_MIN}+{inc}*on\\,{ZOOM_MAX})+{punch}"
    return z, x_center, y_center


def _render_clip(image_path: str, duration: float, effect: str, out_path: Path,
                 log_path: Path) -> None:
    z, x, y = _zoompan_expr(effect, duration)
    n_frames = max(2, int(round(duration * FPS)))
    # cover-fill to exactly 1080x1920, then zoompan (z=1.0 => full frame).
    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},"
        f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={WIDTH}x{HEIGHT}:fps={FPS}"
    )
    if effect == "fade":
        fade_frames = min(9, n_frames)
        vf += f",fade=in:0:{fade_frames}"
    vf += ",format=yuv420p"
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", str(FPS), "-t", f"{duration:.3f}",
        "-i", ff_path(image_path),
        "-vf", vf,
        "-frames:v", str(n_frames),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        ff_path(out_path),
    ]
    run_ffmpeg(cmd, log_path)


# --------------------------------------------------------------------------- #
# drawtext / subtitles builders
# --------------------------------------------------------------------------- #
def _wrap(text: str, fontsize: int, margin_px: int = 90) -> str:
    """Word-wrap so the widest line fits inside 1080px minus safe margins.

    Bold sans glyphs average ~0.55*fontsize wide; keep lines within the usable
    width so drawtext never clips at the frame edges.
    """
    import textwrap

    usable = WIDTH - 2 * margin_px
    approx_char_w = max(1.0, 0.55 * fontsize)
    max_chars = max(6, int(usable / approx_char_w))
    out_lines: List[str] = []
    for para in text.split("\n"):
        wrapped = textwrap.wrap(para, width=max_chars) or [""]
        out_lines.extend(wrapped)
    return "\n".join(out_lines)


def _drawtext(textfile: Path, color: str, y_expr: str, enable: str,
              fontsize: int, font: Optional[str]) -> str:
    parts = [
        f"textfile='{ff_path(textfile)}'",
        f"fontcolor={color}",
        "bordercolor=white", "borderw=8",
        f"fontsize={fontsize}",
        "x=(w-text_w)/2",
        f"y={y_expr}",
        f"enable='{enable}'",
        "line_spacing=12",
        "text_align=C",  # centraliza linhas quebradas (ffmpeg 6.1+)
    ]
    if font:
        parts.insert(0, f"fontfile='{font}'")
    return "drawtext=" + ":".join(parts)


# force_style reconciliado com o short_factory.py original.
# Colour ASS = &HBBGGRR&. Navy #1A233C -> BGR 3C231A. Fontsize em espaço ASS
# (PlayResY default), não em px do vídeo.
_ASS_STYLES = {
    "navy-white": "FontName=DejaVu Sans,Bold=1,Fontsize=15,"
                  "PrimaryColour=&H3C231A&,OutlineColour=&HFFFFFF&,"
                  "Outline=2.2,MarginV=55,Alignment=2",
    "white-black": "FontName=DejaVu Sans,Bold=1,Fontsize=15,"
                   "PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,"
                   "Outline=2.2,MarginV=55,Alignment=2",
    "yellow-pop": "FontName=DejaVu Sans,Bold=1,Fontsize=17,"
                  "PrimaryColour=&H00F0FF&,OutlineColour=&H000000&,"
                  "Outline=3,MarginV=60,Alignment=2",
    "karaoke": "FontName=DejaVu Sans,Bold=1,Fontsize=15,"
               "PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,"
               "Outline=2.2,MarginV=55,Alignment=2",
}


def _apply_caption_fixes(srt_text: str, fixes: dict) -> str:
    for wrong, right in (fixes or {}).items():
        if not wrong:
            continue
        srt_text = re.sub(re.escape(wrong), right.replace("\\", r"\\"), srt_text,
                          flags=re.IGNORECASE)
    return srt_text


# --------------------------------------------------------------------------- #
# The engine (pure)
# --------------------------------------------------------------------------- #
def render(config: dict, work_dir: Path, progress_cb: ProgressMsgCb) -> str:
    """Assemble a 1080x1920 short from ``config`` and return the mp4 path."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    log_path = work_dir / "ffmpeg.log"
    log_path.write_bytes(b"")  # fresh log per render
    clips_dir = work_dir / "clips"
    clips_dir.mkdir(exist_ok=True)

    images = config.get("images", []) or []
    if not images:
        raise RuntimeError("Nenhuma imagem no projeto.")

    audio = config.get("audio", {}) or {}
    audio_file = audio.get("file")
    total_duration = float(audio.get("duration", 0.0) or 0.0)
    if total_duration <= 0:
        total_duration = sum(_clip_durations(images, len(images) * 3.0))

    # --- 1) validation warnings (Part C3) --- #
    progress_cb(2.0, "Validando assets")
    for w in check_image_durations(images, total_duration):
        with log_path.open("ab") as lg:
            lg.write((w + "\n").encode("utf-8", "replace"))
    for w in check_audio_name(audio_file, str(config.get("_project_name", ""))):
        with log_path.open("ab") as lg:
            lg.write((w + "\n").encode("utf-8", "replace"))

    # --- 2) per-image clips (zoompan alternado + punch) --- #
    durations = _clip_durations(images, total_duration)
    clip_paths: List[Path] = []
    for i, img in enumerate(images):
        effect = img.get("effect") or ("zoom-in" if i % 2 == 0 else "zoom-out")
        clip_path = clips_dir / f"clip_{i:03d}.mp4"
        progress_cb(5.0 + 45.0 * i / max(1, len(images)),
                    f"Renderizando cena {i + 1}/{len(images)}")
        img_path = _resolve_image(work_dir, str(img["file"]))
        if img_path is None:
            raise RuntimeError(f"Imagem não encontrada: {img.get('file')}")
        _render_clip(img_path, durations[i], effect, clip_path, log_path)
        clip_paths.append(clip_path)

    # --- 3) concat (-f concat -safe 0), NUNCA -shortest --- #
    progress_cb(55.0, "Concatenando cenas (punch)")
    concat_list = work_dir / "concat.txt"
    concat_list.write_text(
        "".join(f"file '{ff_path(p)}'\n" for p in clip_paths), encoding="utf-8"
    )
    silent_video = work_dir / "video_silent.mp4"
    run_ffmpeg(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", ff_path(concat_list),
         "-c", "copy", ff_path(silent_video)],
        log_path,
    )

    # --- 4) build final video filter: subtitles + hook + CTA --- #
    progress_cb(70.0, "Aplicando legendas, hook e CTA")
    font = _font_file()
    vchain: List[str] = ["[0:v]"]
    filters: List[str] = []

    # subtitles (com caption_fixes)
    srt_rel = config.get("srt")
    if srt_rel:
        srt_src = work_dir.parent / "uploads" / Path(srt_rel).name
        if srt_src.exists():
            fixed = work_dir / "captions_fixed.srt"
            fixed.write_text(
                _apply_caption_fixes(srt_src.read_text(encoding="utf-8", errors="replace"),
                                     config.get("caption_fixes", {})),
                encoding="utf-8",
            )
            style = _ASS_STYLES.get(config.get("caption_style", "navy-white"),
                                    _ASS_STYLES["navy-white"])
            filters.append(f"subtitles='{ff_path(fixed)}':force_style='{style}'")

    # hook: 2 linhas (navy + coral), frame 0 sem fade
    hook = config.get("hook", {}) or {}
    # aceita "|" como separador de linha (ex.: "A JANITOR DIED|WITH $9,000,000")
    hook_text = (hook.get("text") or "").replace("|", "\n").strip()
    hook_dur = float(hook.get("duration", 2.5) or 2.5)
    if hook_text:
        lines = hook_text.split("\n")
        line1 = lines[0]
        line2 = "\n".join(lines[1:]) if len(lines) > 1 else ""
        (work_dir / "hook1.txt").write_text(_wrap(line1, 84), encoding="utf-8")
        filters.append(_drawtext(work_dir / "hook1.txt", NAVY, "h*0.30",
                                 f"between(t,0,{hook_dur:.3f})", 84, font))
        if line2:
            (work_dir / "hook2.txt").write_text(_wrap(line2, 84), encoding="utf-8")
            filters.append(_drawtext(work_dir / "hook2.txt", CORAL, "h*0.30+110",
                                     f"between(t,0,{hook_dur:.3f})", 84, font))

    # CTA: coral, janela start..end
    cta = config.get("cta", {}) or {}
    cta_text = (cta.get("text") or "").strip()
    cta_start = float(cta.get("start", 0.0) or 0.0)
    cta_end = float(cta.get("end", 0.0) or 0.0)
    if cta_text and cta_end > cta_start:
        # CTA acima da faixa de legendas (que fica no rodapé) para não colidir.
        (work_dir / "cta.txt").write_text(_wrap(cta_text, 58), encoding="utf-8")
        filters.append(_drawtext(work_dir / "cta.txt", CORAL, "h*0.58",
                                 f"between(t,{cta_start:.3f},{cta_end:.3f})", 58, font))

    # --- 5) audio: amix narração + música(loop) + SFX(adelay) --- #
    progress_cb(85.0, "Mixando áudio (narração + música + SFX)")
    uploads = work_dir.parent / "uploads"
    inputs: List[str] = ["-i", ff_path(silent_video)]        # 0:v
    input_idx = 1
    amix_labels: List[str] = []
    afilters: List[str] = []

    # narration
    have_audio = bool(audio_file) and (uploads / Path(audio_file).name).exists()
    if have_audio:
        inputs += ["-i", ff_path(uploads / Path(audio_file).name)]
        afilters.append(f"[{input_idx}:a]volume=1.0[narr]")
        amix_labels.append("[narr]")
        input_idx += 1

    # music (looped) — -stream_loop before its -i
    music = config.get("music", {}) or {}
    music_file = music.get("file")
    music_vol = float(music.get("volume", 0.2) or 0.2)
    if music_file:
        mpath = _resolve_asset(work_dir, music_file, "music")
        if mpath is not None:
            inputs += ["-stream_loop", "-1", "-i", ff_path(mpath)]
            afilters.append(f"[{input_idx}:a]volume={music_vol}[mus]")
            amix_labels.append("[mus]")
            input_idx += 1

    # SFX (adelay)
    for j, sfx in enumerate(config.get("sfx", []) or []):
        spath = _resolve_asset(work_dir, sfx.get("file", ""), "sfx")
        if spath is None:
            continue
        ms = int(float(sfx.get("time", 0.0) or 0.0) * 1000)
        vol = float(sfx.get("volume", 1.0) or 1.0)
        inputs += ["-i", ff_path(spath)]
        afilters.append(f"[{input_idx}:a]adelay={ms}|{ms},volume={vol}[sfx{j}]")
        amix_labels.append(f"[sfx{j}]")
        input_idx += 1

    # assemble filter_complex
    fc_parts: List[str] = []
    if filters:
        fc_parts.append("[0:v]" + ",".join(filters) + "[v]")
        vmap = "[v]"
    else:
        vmap = "0:v"
    have_mixed_audio = len(amix_labels) > 0
    if have_mixed_audio:
        fc_parts.extend(afilters)
        if len(amix_labels) == 1:
            fc_parts.append(f"{amix_labels[0]}apad,atrim=0:{total_duration:.3f}[aout]")
        else:
            # amix reconciliado com o original: duration=first (dura o tempo da
            # narração, que é o 1º input) + normalize=0 (preserva níveis).
            fc_parts.append(
                "".join(amix_labels)
                + f"amix=inputs={len(amix_labels)}:duration=first:normalize=0,"
                + f"atrim=0:{total_duration:.3f}[aout]"
            )

    out_path = work_dir / "short.mp4"
    cmd = ["ffmpeg", "-y", *inputs]
    if fc_parts:
        cmd += ["-filter_complex", ";".join(fc_parts)]
    cmd += ["-map", vmap]
    if have_mixed_audio:
        cmd += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
    cmd += [
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        "-t", f"{total_duration:.3f}",       # explícito, NUNCA -shortest
        "-movflags", "+faststart",
        ff_path(out_path),
    ]
    run_ffmpeg(cmd, log_path)

    progress_cb(100.0, "Concluído")
    return ff_path(out_path)


def _resolve_image(work_dir: Path, ref: str) -> Optional[str]:
    """Resolve an image reference to a real path (absolute, or under uploads/)."""
    if not ref:
        return None
    p = Path(ref)
    if p.is_absolute() and p.exists():
        return ff_path(p)
    up = work_dir.parent / "uploads" / p.name
    if up.exists():
        return ff_path(up)
    if p.exists():
        return ff_path(p)
    return None


def _resolve_asset(work_dir: Path, ref: str, kind: str) -> Optional[Path]:
    """Resolve a sound reference to a real path (project upload or shared library)."""
    if not ref:
        return None
    name = Path(ref).name
    # 1) library: storage/assets/{kind}/name   (ref may be "sfx/foo.mp3")
    assets_root = work_dir.parent.parent.parent / "assets" / kind
    cand = assets_root / name
    if cand.exists():
        return cand
    # 2) absolute/relative path as given
    p = Path(ref)
    if p.exists():
        return p
    # 3) project upload
    up = work_dir.parent / "uploads" / name
    if up.exists():
        return up
    return None
