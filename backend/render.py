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

import os
import re
import subprocess
import time
from pathlib import Path
from typing import Callable, List, Optional

# Output spec — vertical short.
WIDTH, HEIGHT = 1080, 1920
FPS = 30
# Upscale antes do zoompan (anti-jitter). 1200 (era 1400): ~25% menos pixels
# no zoompan, diferença visual mínima em 9:16.
WORK_WIDTH = 1200

# Qualidade do encode final, configurável por env (default 'fast' p/ free tier).
#   RENDER_QUALITY=fast -> veryfast (rápido, mesmo crf = mesma qualidade visual)
#   RENDER_QUALITY=high -> medium  (arquivo menor, mais lento)
_RENDER_QUALITY = os.environ.get("RENDER_QUALITY", "fast").lower()
FINAL_PRESET = "medium" if _RENDER_QUALITY == "high" else "veryfast"

# Production guardrails (Part C3).
MAX_IMAGE_SECONDS = 5.0     # nenhuma imagem parada > 5s sem aviso
RENDER_TIMEOUT_S = 600      # teto absoluto de segurança (fallback)
# Timeouts POR ETAPA (item 2): erro específico + resume recomeça só da etapa.
CLIP_TIMEOUT_S = 60         # por cena
CONCAT_TIMEOUT_S = 120
AUDIO_TIMEOUT_S = 120
ENCODE_TIMEOUT_S = 300      # encode final

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


def run_ffmpeg_progress(cmd: List[str], log_path: Path, total_seconds: float,
                        report: Callable[[float, Optional[float]], None],
                        timeout: int = RENDER_TIMEOUT_S) -> None:
    """Como run_ffmpeg, mas faz stream do ``-progress`` do ffmpeg.

    Chama ``report(frac, eta_seconds)`` conforme o encode avança, para a barra
    do usuário nunca "travar" num passo longo (progresso honesto, item 4).
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as logf:
        logf.write(("\n$ " + " ".join(cmd) + "\n").encode("utf-8", "replace"))
    full = [cmd[0], "-progress", "pipe:1", "-nostats", *cmd[1:]]
    start = time.monotonic()
    with log_path.open("ab") as logf:
        proc = subprocess.Popen(full, stdout=subprocess.PIPE, stderr=logf, text=True)
        assert proc.stdout is not None
        try:
            for line in proc.stdout:
                if line.startswith("out_time_us=") and total_seconds > 0:
                    raw = line.strip().split("=", 1)[1]
                    try:
                        us = int(raw)
                    except ValueError:
                        continue
                    frac = max(0.0, min(1.0, us / 1e6 / total_seconds))
                    elapsed = time.monotonic() - start
                    eta = (elapsed / frac - elapsed) if frac > 0.03 else None
                    report(frac, eta)
                elif line.startswith("progress=end"):
                    report(1.0, 0.0)
                if time.monotonic() - start > timeout:
                    proc.kill()
                    raise RuntimeError(f"ffmpeg excedeu o timeout de {timeout}s")
        finally:
            proc.stdout.close()
        proc.wait()
    if proc.returncode != 0:
        tail = log_path.read_bytes().decode("utf-8", "replace").splitlines()[-15:]
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
                 log_path: Path, timeout: int = CLIP_TIMEOUT_S) -> None:
    z, x, y = _zoompan_expr(effect, duration)
    n_frames = max(2, int(round(duration * FPS)))
    # 1) cover-fill p/ 9:16, 2) UPSCALE (scale=1400:-1) antes do zoompan
    # (anti-jitter do zoom — motor original), 3) zoompan com fps=30 dentro.
    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},"
        f"scale={WORK_WIDTH}:-1,"
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
        # intermediário: ultrafast/crf18 (o encode final dá o acabamento).
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
        "-threads", "2",  # limita RAM do zoompan+encode (independe de nº de cores)
        "-pix_fmt", "yuv420p",
        ff_path(out_path),
    ]
    run_ffmpeg(cmd, log_path, timeout=timeout)


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
# Pre-flight (item 2): valida TODOS os assets antes de renderizar
# --------------------------------------------------------------------------- #
def validate_assets(config: dict, work_dir: Path) -> List[str]:
    """Confere existência/legibilidade de imagens, áudio, música, SFX e SRT.

    Retorna a lista de problemas (vazia = tudo ok). Chamado ANTES de qualquer
    ffmpeg, para falhar cedo e claro em vez de travar aos 85%.
    """
    work_dir = Path(work_dir)
    uploads = work_dir.parent / "uploads"
    problems: List[str] = []

    images = config.get("images", []) or []
    if not images:
        problems.append("Nenhuma imagem no projeto.")
    for img in images:
        if _resolve_image(work_dir, str(img.get("file", ""))) is None:
            problems.append(f"Imagem não encontrada: {img.get('file')}")

    audio_file = (config.get("audio", {}) or {}).get("file")
    if audio_file and _resolve_image(work_dir, audio_file) is None:
        problems.append(f"Áudio (narração) não encontrado: {audio_file}")

    music_file = (config.get("music", {}) or {}).get("file")
    if music_file and _resolve_asset(work_dir, music_file, "music") is None:
        problems.append(f"Música não encontrada: {music_file}")

    for sfx in config.get("sfx", []) or []:
        ref = sfx.get("file", "")
        if ref and _resolve_asset(work_dir, ref, "sfx") is None:
            problems.append(f"SFX não encontrado: {ref}")

    srt_rel = config.get("srt")
    if srt_rel and _resolve_image(work_dir, srt_rel) is None:
        problems.append(f"SRT não encontrado: {srt_rel}")

    _ = uploads  # (mantido para clareza do layout)
    return problems


def _build_video_filters(config: dict, work_dir: Path) -> List[str]:
    """Monta a cadeia de filtros de vídeo (subtitles + hook + CTA)."""
    font = _font_file()
    filters: List[str] = []

    # subtitles (com caption_fixes)
    srt_rel = config.get("srt")
    if srt_rel:
        srt_resolved = _resolve_image(work_dir, srt_rel)
        if srt_resolved:
            srt_src = Path(srt_resolved)
            fixed = work_dir / "captions_fixed.srt"
            fixed.write_text(
                _apply_caption_fixes(srt_src.read_text(encoding="utf-8", errors="replace"),
                                     config.get("caption_fixes", {})),
                encoding="utf-8",
            )
            style = _ASS_STYLES.get(config.get("caption_style", "navy-white"),
                                    _ASS_STYLES["navy-white"])
            filters.append(f"subtitles='{ff_path(fixed)}':force_style='{style}'")

    # hook: 2 linhas (navy + coral), frame 0 sem fade; "|" separa as linhas
    hook = config.get("hook", {}) or {}
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

    # CTA: coral, janela start..end, acima da faixa de legendas
    cta = config.get("cta", {}) or {}
    cta_text = (cta.get("text") or "").strip()
    cta_start = float(cta.get("start", 0.0) or 0.0)
    cta_end = float(cta.get("end", 0.0) or 0.0)
    if cta_text and cta_end > cta_start:
        (work_dir / "cta.txt").write_text(_wrap(cta_text, 58), encoding="utf-8")
        filters.append(_drawtext(work_dir / "cta.txt", CORAL, "h*0.58",
                                 f"between(t,{cta_start:.3f},{cta_end:.3f})", 58, font))
    return filters


def _run_audio_mix(config: dict, work_dir: Path, total_duration: float,
                   mix_path: Path, log_path: Path) -> bool:
    """Mixa SOMENTE o áudio (narração + música loop + SFX) -> mix.m4a.

    Passo separado do vídeo (item 1) e com ``-threads 1`` para derrubar o pico
    de RAM (era aqui o OOM no free tier de 512MB). Retorna True se há áudio.
    """
    audio_file = (config.get("audio", {}) or {}).get("file")
    inputs: List[str] = []
    idx = 0
    labels: List[str] = []
    afilters: List[str] = []

    # narração
    narr_path = _resolve_image(work_dir, audio_file) if audio_file else None
    if narr_path:
        inputs += ["-i", narr_path]
        afilters.append(f"[{idx}:a]volume=1.0[narr]")
        labels.append("[narr]")
        idx += 1

    # música em loop (-stream_loop antes do -i)
    music = config.get("music", {}) or {}
    if music.get("file"):
        mpath = _resolve_asset(work_dir, music["file"], "music")
        if mpath is not None:
            vol = float(music.get("volume", 0.2) or 0.2)
            inputs += ["-stream_loop", "-1", "-i", ff_path(mpath)]
            afilters.append(f"[{idx}:a]volume={vol}[mus]")
            labels.append("[mus]")
            idx += 1

    # SFX (adelay)
    for j, sfx in enumerate(config.get("sfx", []) or []):
        spath = _resolve_asset(work_dir, sfx.get("file", ""), "sfx")
        if spath is None:
            continue
        ms = int(float(sfx.get("time", 0.0) or 0.0) * 1000)
        vol = float(sfx.get("volume", 1.0) or 1.0)
        inputs += ["-i", ff_path(spath)]
        afilters.append(f"[{idx}:a]adelay={ms}|{ms},volume={vol}[sfx{j}]")
        labels.append(f"[sfx{j}]")
        idx += 1

    if not labels:
        return False  # sem áudio nenhum

    fc = list(afilters)
    if len(labels) == 1:
        fc.append(f"{labels[0]}apad,atrim=0:{total_duration:.3f}[aout]")
    else:
        # amix reconciliado: duration=first (dura o tempo da narração) + normalize=0.
        fc.append(
            "".join(labels)
            + f"amix=inputs={len(labels)}:duration=first:normalize=0,"
            + f"atrim=0:{total_duration:.3f}[aout]"
        )

    cmd = [
        "ffmpeg", "-y", "-threads", "1", *inputs,
        "-filter_complex", ";".join(fc),
        "-map", "[aout]", "-c:a", "aac", "-b:a", "192k",
        "-t", f"{total_duration:.3f}",
        ff_path(mix_path),
    ]
    run_ffmpeg(cmd, log_path, timeout=AUDIO_TIMEOUT_S)
    return True


# --------------------------------------------------------------------------- #
# The engine (pure) — passos separados p/ pouca RAM + resumíveis (checkpoints)
# --------------------------------------------------------------------------- #
def render(config: dict, work_dir: Path, progress_cb: ProgressMsgCb,
           resume: bool = False) -> str:
    """Assemble a 1080x1920 short from ``config`` and return the mp4 path.

    Pipeline em etapas, cada uma com saída em arquivo = checkpoint. Se
    ``resume=True``, pula etapas cuja saída já existe (retoma após um restart
    da instância). Vídeo e áudio são renderizados SEPARADOS e depois muxados
    sem re-encode (-c copy) para não estourar a RAM.
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    log_path = work_dir / "ffmpeg.log"
    if not resume:
        log_path.write_bytes(b"")
    clips_dir = work_dir / "clips"
    clips_dir.mkdir(exist_ok=True)

    images = config.get("images", []) or []
    audio = config.get("audio", {}) or {}
    audio_file = audio.get("file")
    total_duration = float(audio.get("duration", 0.0) or 0.0)
    if total_duration <= 0:
        total_duration = sum(_clip_durations(images, len(images) * 3.0))

    # --- 0) PRE-FLIGHT: valida assets ANTES de renderizar (item 2) --- #
    progress_cb(1.0, "Validando assets")
    problems = validate_assets(config, work_dir)
    if problems:
        raise RuntimeError("Assets ausentes ou ilegíveis:\n- " + "\n- ".join(problems))

    for w in check_image_durations(images, total_duration):
        with log_path.open("ab") as lg:
            lg.write((w + "\n").encode("utf-8", "replace"))
    for w in check_audio_name(audio_file, str(config.get("_project_name", ""))):
        with log_path.open("ab") as lg:
            lg.write((w + "\n").encode("utf-8", "replace"))

    # --- 1) cenas: 1 clipe por imagem (resumível: pula clipe já pronto) --- #
    durations = _clip_durations(images, total_duration)
    clip_paths: List[Path] = []
    n_imgs = max(1, len(images))
    for i, img in enumerate(images):
        clip_path = clips_dir / f"clip_{i:03d}.mp4"
        # cenas ocupam 2%..60% da barra (item 4)
        progress_cb(2.0 + 58.0 * i / n_imgs,
                    f"Renderizando cena {i + 1}/{len(images)}")
        if not (resume and clip_path.exists()):
            effect = img.get("effect") or ("zoom-in" if i % 2 == 0 else "zoom-out")
            img_path = _resolve_image(work_dir, str(img["file"]))
            if img_path is None:
                raise RuntimeError(f"Imagem não encontrada: {img.get('file')}")
            try:
                _render_clip(img_path, durations[i], effect, clip_path, log_path)
            except RuntimeError as exc:
                if "timeout" in str(exc).lower():
                    raise RuntimeError(
                        f"Cena {i + 1}/{len(images)} ({Path(str(img['file'])).name}) "
                        f"excedeu {CLIP_TIMEOUT_S}s. Use 'Retomar' para continuar "
                        f"daqui, ou RENDER_QUALITY/instância mais rápida."
                    ) from exc
                raise
        clip_paths.append(clip_path)

    # --- 2) concat (-f concat -safe 0), NUNCA -shortest (checkpoint) --- #
    silent_video = work_dir / "video_silent.mp4"
    if not (resume and silent_video.exists()):
        progress_cb(60.0, "Concatenando cenas (punch)")
        concat_list = work_dir / "concat.txt"
        concat_list.write_text(
            "".join(f"file '{ff_path(p)}'\n" for p in clip_paths), encoding="utf-8"
        )
        run_ffmpeg(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", ff_path(concat_list),
             "-c", "copy", ff_path(silent_video)],
            log_path, timeout=CONCAT_TIMEOUT_S,
        )

    # --- 3) VÍDEO: aplica legendas/hook/CTA num passo só, SEM áudio (checkpoint) --- #
    filters = _build_video_filters(config, work_dir)
    video_base = silent_video
    if filters:
        video_final = work_dir / "video_final.mp4"
        if not (resume and video_final.exists()):
            progress_cb(62.0, "Codificando vídeo (legendas, hook, CTA)")

            def _vreport(frac: float, eta: Optional[float]) -> None:
                msg = "Codificando vídeo (legendas, hook, CTA)"
                if eta and eta > 1:
                    msg += f" — ~{int(eta)}s restantes"
                progress_cb(62.0 + 30.0 * frac, msg)  # encode ocupa 62%..92%

            # -threads 1 + rc-lookahead baixo derrubam o pico de RAM do encode.
            # preset via RENDER_QUALITY (default veryfast); crf 19 = mesma
            # qualidade visual do medium, só arquivo um pouco maior.
            run_ffmpeg_progress(
                ["ffmpeg", "-y", "-i", ff_path(silent_video),
                 "-vf", ",".join(filters), "-an",
                 "-c:v", "libx264", "-preset", FINAL_PRESET, "-crf", "19",
                 "-threads", "1", "-x264-params", "rc-lookahead=10:sync-lookahead=0",
                 "-pix_fmt", "yuv420p", "-r", str(FPS),
                 "-t", f"{total_duration:.3f}",
                 "-movflags", "+faststart", ff_path(video_final)],
                log_path, total_duration, _vreport, timeout=ENCODE_TIMEOUT_S,
            )
        video_base = video_final

    # --- 4) ÁUDIO: mix leve em memória -> mix.m4a (-threads 1) (checkpoint) --- #
    mix_path = work_dir / "mix.m4a"
    if resume and mix_path.exists():
        have_audio = True
    else:
        progress_cb(93.0, "Mixando áudio (narração + música + SFX)")
        have_audio = _run_audio_mix(config, work_dir, total_duration, mix_path, log_path)

    # --- 5) MUX: junta vídeo + áudio SEM re-encode (-c copy) --- #
    progress_cb(97.0, "Finalizando (mux sem re-encode)")
    out_path = work_dir / "short.mp4"
    cmd = ["ffmpeg", "-y", "-i", ff_path(video_base)]
    if have_audio:
        cmd += ["-i", ff_path(mix_path)]
    cmd += ["-map", "0:v:0", "-c:v", "copy"]
    if have_audio:
        cmd += ["-map", "1:a:0", "-c:a", "copy"]
    cmd += ["-t", f"{total_duration:.3f}", "-movflags", "+faststart", ff_path(out_path)]
    run_ffmpeg(cmd, log_path, timeout=CONCAT_TIMEOUT_S)

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
