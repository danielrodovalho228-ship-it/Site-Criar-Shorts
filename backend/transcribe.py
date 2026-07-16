"""Auto-transcrição da narração via ElevenLabs Scribe (aprendido do video-use).

Transforma o MP3 do criador em:
  1) legendas automáticas (SRT) — sem SRT manual;
  2) pausas da narração -> sugestão de cortes (auto-timing, o "segredo do ritmo").

A chave da API vem SEMPRE de os.environ['ELEVENLABS_API_KEY'] (segredo, nunca
hardcoded/commitado).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

SCRIBE_URL = "https://api.elevenlabs.io/v1/speech-to-text"
SCRIBE_MODEL = "scribe_v1"


class TranscriptionError(RuntimeError):
    pass


def api_key() -> Optional[str]:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    return key or None


def transcribe_audio(audio_path: Path, language_code: Optional[str] = None) -> Dict[str, Any]:
    """Chama o Scribe e retorna {text, words:[{text,start,end,type}]}."""
    key = api_key()
    if not key:
        raise TranscriptionError(
            "ELEVENLABS_API_KEY não configurada no servidor. Adicione a variável "
            "de ambiente (segredo) e tente de novo."
        )
    data: Dict[str, str] = {"model_id": SCRIBE_MODEL}
    if language_code:
        data["language_code"] = language_code
    try:
        with open(audio_path, "rb") as fh:
            resp = requests.post(
                SCRIBE_URL,
                headers={"xi-api-key": key},
                data=data,
                files={"file": (Path(audio_path).name, fh, "audio/mpeg")},
                timeout=300,
            )
    except requests.RequestException as exc:
        raise TranscriptionError(f"Falha de rede ao chamar o Scribe: {exc}") from exc

    if resp.status_code == 401:
        raise TranscriptionError("Chave da ElevenLabs inválida (401).")
    if resp.status_code >= 400:
        raise TranscriptionError(
            f"Scribe respondeu {resp.status_code}: {resp.text[:200]}"
        )
    return resp.json()


# --------------------------------------------------------------------------- #
# SRT a partir das palavras
# --------------------------------------------------------------------------- #
def _words_only(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        w
        for w in payload.get("words", [])
        if w.get("type") == "word" and w.get("text", "").strip()
    ]


def words_to_cues(words: List[Dict[str, Any]], max_words: int = 5,
                  max_dur: float = 2.8, gap: float = 0.5) -> List[Dict[str, Any]]:
    """Agrupa palavras em legendas curtas (quebra por nº, duração, pausa, pontuação)."""
    cues: List[Dict[str, Any]] = []
    cur: List[Dict[str, Any]] = []
    for i, w in enumerate(words):
        cur.append(w)
        text = w["text"].strip()
        nxt = words[i + 1] if i + 1 < len(words) else None
        pause_ahead = nxt is not None and (float(nxt["start"]) - float(w["end"])) > gap
        ends_sentence = text.endswith((".", "!", "?", ","))
        dur = float(cur[-1]["end"]) - float(cur[0]["start"])
        if (len(cur) >= max_words or dur >= max_dur or pause_ahead
                or ends_sentence or nxt is None):
            cues.append({
                "start": float(cur[0]["start"]),
                "end": float(cur[-1]["end"]),
                "text": " ".join(x["text"].strip() for x in cur).strip(),
            })
            cur = []
    return cues


def _ts(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms == 1000:
        s += 1
        ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def cues_to_srt(cues: List[Dict[str, Any]]) -> str:
    blocks = []
    for i, c in enumerate(cues, 1):
        blocks.append(f"{i}\n{_ts(c['start'])} --> {_ts(c['end'])}\n{c['text']}\n")
    return "\n".join(blocks)


# --------------------------------------------------------------------------- #
# Pausas -> auto-timing dos cortes
# --------------------------------------------------------------------------- #
def compute_pauses(words: List[Dict[str, Any]], gap: float = 0.35) -> List[float]:
    """Pontos (s) onde há pausa > gap entre palavras — candidatos a corte."""
    pauses: List[float] = []
    for i in range(len(words) - 1):
        gap_len = float(words[i + 1]["start"]) - float(words[i]["end"])
        if gap_len > gap:
            pauses.append(round(float(words[i + 1]["start"]), 2))
    return pauses


def distribute_starts(pauses: List[float], total: float, n: int) -> List[float]:
    """Distribui n cenas ao longo do áudio, encostando cada início numa pausa."""
    if n <= 0:
        return []
    if total <= 0 or n == 1:
        return [0.0] * n
    cand = sorted(p for p in pauses if 0.3 < p < total - 0.3)
    starts = [0.0]
    for i in range(1, n):
        target = i * total / n
        best = None
        for p in cand:
            if p <= starts[-1] + 0.5:
                continue
            if best is None or abs(p - target) < abs(best - target):
                best = p
        val = best if best is not None else max(starts[-1] + total / n, target)
        val = min(val, total - 0.2)  # nunca começar depois do fim do áudio
        if val <= starts[-1]:
            val = starts[-1] + 0.1    # garante ordem crescente (caso degenerado)
        starts.append(val)
    return [round(s, 2) for s in starts]


def save_transcript(uploads_dir: Path, words: List[Dict[str, Any]],
                    pauses: List[float]) -> None:
    (uploads_dir / "_transcript.json").write_text(
        json.dumps({"words": words, "pauses": pauses}), encoding="utf-8"
    )


def load_pauses(uploads_dir: Path) -> Optional[List[float]]:
    path = uploads_dir / "_transcript.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("pauses", [])
    except (json.JSONDecodeError, OSError):
        return None


__all__ = [
    "TranscriptionError", "api_key", "transcribe_audio", "words_to_cues",
    "cues_to_srt", "compute_pauses", "distribute_starts", "save_transcript",
    "load_pauses", "_words_only",
]
