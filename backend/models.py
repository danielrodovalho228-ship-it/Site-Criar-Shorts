"""Pydantic schemas for Short Factory (P0).

Design rules carried from the master plan (Part C1) so we never rewrite in P2:
- ``user_id`` is nullable EVERYWHERE from day 1 (P0 uses a local user; P2 plugs
  auth in without a painful migration).
- Templates are DATA (JSON), never hardcoded — a template only pre-fills these
  same fields.
- The render engine is pure: it consumes a ``ProjectConfig`` dict and knows
  nothing about HTTP.

The on-disk ``project.json`` is exactly a serialized :class:`Project`.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class ImageEffect(str, Enum):
    """Per-image motion. v1 already had zoom in/out; pan = zoompan with moving x."""

    ZOOM_IN = "zoom-in"
    ZOOM_OUT = "zoom-out"
    PAN_LEFT = "pan-left"
    PAN_RIGHT = "pan-right"
    FADE = "fade"
    STATIC = "static"


class CaptionStyle(str, Enum):
    """The 4 subtitle looks from the plan (Part B2)."""

    NAVY_WHITE = "navy-white"        # The Chapter house style
    WHITE_BLACK = "white-black"      # classic
    YELLOW_POP = "yellow-pop"        # MrBeast style
    KARAOKE = "karaoke"              # word-by-word


class ProjectStatus(str, Enum):
    DRAFT = "draft"          # created, still being configured
    QUEUED = "queued"        # generate requested, waiting for a worker
    RENDERING = "rendering"  # ffmpeg running
    DONE = "done"            # mp4 ready to download
    FAILED = "failed"        # render error (see log)


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


# --------------------------------------------------------------------------- #
# Config sub-models (these mirror the render engine's config contract)
# --------------------------------------------------------------------------- #
class AudioTrack(BaseModel):
    """The creator's OWN narration — the BYO-voice differentiator."""

    file: Optional[str] = None
    duration: float = 0.0  # seconds, extracted with ffprobe on upload


class ImageClip(BaseModel):
    file: str
    start: float = 0.0                       # seconds into the video
    effect: ImageEffect = ImageEffect.ZOOM_IN


class Hook(BaseModel):
    """Opening text — for Book Summary it carries the number in frame 0."""

    text: str = ""
    duration: float = 2.5  # seconds visible from the start


class CTA(BaseModel):
    text: str = ""
    start: float = 0.0
    end: float = 0.0


class Music(BaseModel):
    file: Optional[str] = None
    volume: float = Field(default=0.2, ge=0.0, le=1.0)  # 20% under narration


class SFX(BaseModel):
    file: str
    time: float = 0.0
    volume: float = Field(default=1.0, ge=0.0, le=2.0)


# --------------------------------------------------------------------------- #
# Project (== project.json)
# --------------------------------------------------------------------------- #
class ProjectConfig(BaseModel):
    """The editable part of a project — exactly what ``render()`` consumes."""

    audio: AudioTrack = Field(default_factory=AudioTrack)
    srt: Optional[str] = None                       # relative path to the .srt
    caption_fixes: dict[str, str] = Field(default_factory=dict)  # {"wrong": "right"}
    images: List[ImageClip] = Field(default_factory=list)
    hook: Hook = Field(default_factory=Hook)
    cta: CTA = Field(default_factory=CTA)
    music: Music = Field(default_factory=Music)
    sfx: List[SFX] = Field(default_factory=list)
    caption_style: CaptionStyle = CaptionStyle.NAVY_WHITE


class Project(BaseModel):
    id: str
    user_id: Optional[str] = None       # nullable from day 1 (Part C1.1)
    name: str = "Untitled Short"
    template_id: Optional[str] = None
    status: ProjectStatus = ProjectStatus.DRAFT
    progress: float = 0.0               # 0..100
    output_file: Optional[str] = None   # relative path to the rendered mp4
    error: Optional[str] = None

    # editable config (flattened into the same document for convenience)
    config: ProjectConfig = Field(default_factory=ProjectConfig)


# --------------------------------------------------------------------------- #
# API request/response bodies
# --------------------------------------------------------------------------- #
class ProjectCreate(BaseModel):
    name: Optional[str] = None
    template_id: Optional[str] = None
    user_id: Optional[str] = None


class ConfigUpdate(BaseModel):
    """PUT /api/projects/{id}/config — partial update of the editable fields."""

    name: Optional[str] = None
    config: Optional[ProjectConfig] = None


class Job(BaseModel):
    id: str
    project_id: str
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    message: str = ""
    error: Optional[str] = None
    output_file: Optional[str] = None


class AssetInfo(BaseModel):
    """An entry from the SFX / music library."""

    file: str          # relative path under /storage/assets
    name: str          # human label
    kind: str          # "sfx" | "music"
