"""Storage behind an interface (Part C1.2).

P0 ships a local-disk driver. Swapping to S3/R2 in P2 means writing one new
class that implements :class:`Storage` and changing the factory at the bottom —
no route or engine code changes.

Layout on disk::

    storage/
      projects/
        {uuid}/
          project.json
          uploads/        # user images / audio / srt
          output/         # rendered mp4 + ffmpeg log
      assets/
        sfx/              # licensed SFX library
        music/            # licensed music library
"""

from __future__ import annotations

import json
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from models import Project


class Storage(ABC):
    """Contract every driver must satisfy."""

    @abstractmethod
    def project_dir(self, project_id: str) -> Path: ...

    @abstractmethod
    def uploads_dir(self, project_id: str) -> Path: ...

    @abstractmethod
    def output_dir(self, project_id: str) -> Path: ...

    @abstractmethod
    def save_project(self, project: Project) -> None: ...

    @abstractmethod
    def load_project(self, project_id: str) -> Optional[Project]: ...

    @abstractmethod
    def list_projects(self) -> List[Project]: ...

    @abstractmethod
    def save_upload(self, project_id: str, filename: str, data: bytes) -> Path: ...

    @abstractmethod
    def assets_dir(self, kind: str) -> Path: ...


class LocalStorage(Storage):
    """Filesystem driver. All paths via ``pathlib`` (Part C3)."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.projects_root = self.root / "projects"
        self.assets_root = self.root / "assets"
        self.projects_root.mkdir(parents=True, exist_ok=True)
        (self.assets_root / "sfx").mkdir(parents=True, exist_ok=True)
        (self.assets_root / "music").mkdir(parents=True, exist_ok=True)

    # --- paths ------------------------------------------------------------- #
    def project_dir(self, project_id: str) -> Path:
        p = self.projects_root / project_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def uploads_dir(self, project_id: str) -> Path:
        p = self.project_dir(project_id) / "uploads"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def output_dir(self, project_id: str) -> Path:
        p = self.project_dir(project_id) / "output"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def assets_dir(self, kind: str) -> Path:
        if kind not in ("sfx", "music"):
            raise ValueError(f"unknown asset kind: {kind!r}")
        p = self.assets_root / kind
        p.mkdir(parents=True, exist_ok=True)
        return p

    # --- project.json ------------------------------------------------------ #
    def _project_json(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "project.json"

    def save_project(self, project: Project) -> None:
        path = self._project_json(project.id)
        path.write_text(project.model_dump_json(indent=2), encoding="utf-8")

    def load_project(self, project_id: str) -> Optional[Project]:
        path = self._project_json(project_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return Project.model_validate(data)

    def list_projects(self) -> List[Project]:
        projects: List[Project] = []
        for child in sorted(self.projects_root.iterdir()):
            if not child.is_dir():
                continue
            proj = self.load_project(child.name)
            if proj is not None:
                projects.append(proj)
        return projects

    # --- uploads ----------------------------------------------------------- #
    def save_upload(self, project_id: str, filename: str, data: bytes) -> Path:
        # Guard against path traversal from the client-supplied filename.
        safe_name = Path(filename).name
        dest = self.uploads_dir(project_id) / safe_name
        dest.write_bytes(data)
        return dest


def _default_root() -> Path:
    # backend/ -> project root -> storage/
    return Path(__file__).resolve().parent.parent / "storage"


def get_storage() -> Storage:
    """Factory — the single place to swap the driver in P2."""
    return LocalStorage(_default_root())


__all__ = ["Storage", "LocalStorage", "get_storage", "shutil"]
