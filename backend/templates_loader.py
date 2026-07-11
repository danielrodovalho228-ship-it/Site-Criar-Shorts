"""Template loading (Part B1 / C1.4).

A template is a preset stored as ``backend/templates/{id}.json``. It carries
metadata (name, niche, recipe, suggested cut range and SFX) plus a ``config``
block whose keys mirror :class:`ProjectConfig`. Creating a project with a
``template_id`` pre-fills that config. Adding a template = adding a file — no
code change.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def _templates_dir() -> Path:
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    return TEMPLATES_DIR


def load_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Return the raw template dict, or None if the id is unknown."""
    # Guard against traversal via a crafted template_id.
    safe_id = Path(template_id).name
    path = _templates_dir() / f"{safe_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def template_config(template_id: str) -> Dict[str, Any]:
    """Return just the ``config`` block a new project should start from."""
    tpl = load_template(template_id)
    if not tpl:
        return {}
    return tpl.get("config", {}) or {}


def list_templates() -> List[Dict[str, Any]]:
    """Return metadata for every template (without the full config block)."""
    out: List[Dict[str, Any]] = []
    for path in sorted(_templates_dir().glob("*.json")):
        try:
            tpl = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        out.append(
            {
                "id": tpl.get("id", path.stem),
                "name": tpl.get("name", path.stem),
                "description": tpl.get("description", ""),
                "niche": tpl.get("niche", ""),
                "recipe": tpl.get("recipe", ""),
                "cut_range": tpl.get("cut_range"),
                "suggested_sfx": tpl.get("suggested_sfx", []),
            }
        )
    return out
