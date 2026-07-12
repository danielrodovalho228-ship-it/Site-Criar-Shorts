"""Short Factory API (Sprint 1, P0).

FastAPI thin layer over the pure render engine. All heavy logic lives in
``render.py`` (motor), ``storage.py`` (disk), ``jobs.py`` (queue) and
``templates_loader.py`` (presets).
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from jobs import registry
from media import probe_duration
from models import (
    AssetInfo,
    ConfigUpdate,
    Job,
    Project,
    ProjectConfig,
    ProjectCreate,
    ProjectStatus,
)
from models import JobStatus
from render import render, validate_assets
from storage import get_storage, shutil
from templates_loader import list_templates, load_template, template_config

app = FastAPI(title="Short Factory API", version="1.0.0")

# CORS: libera qualquer origem (frontend na Vercel + Vite dev). Sem cookies/
# auth em P0, então allow_credentials=False (permite usar "*").
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = get_storage()

# --------------------------------------------------------------------------- #
# Upload validation
# --------------------------------------------------------------------------- #
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
SRT_EXT = {".srt"}
MAX_IMAGE_BYTES = 25 * 1024 * 1024   # 25 MB / image
MAX_AUDIO_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_SRT_BYTES = 2 * 1024 * 1024      # 2 MB


def _ext(filename: str) -> str:
    return Path(filename or "").suffix.lower()


def _require_project(project_id: str) -> Project:
    project = storage.load_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return project


# --------------------------------------------------------------------------- #
# Health + templates
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "short-factory"}


@app.get("/api/templates")
def get_templates() -> List[dict]:
    return list_templates()


# --------------------------------------------------------------------------- #
# Projects
# --------------------------------------------------------------------------- #
@app.post("/api/projects", response_model=Project)
def create_project(body: ProjectCreate) -> Project:
    project_id = str(uuid.uuid4())

    # Start from defaults, overlay the template's config block if given.
    config = ProjectConfig()
    if body.template_id:
        if load_template(body.template_id) is None:
            raise HTTPException(
                status_code=400, detail=f"Template desconhecido: {body.template_id}"
            )
        merged = {**config.model_dump(), **template_config(body.template_id)}
        config = ProjectConfig.model_validate(merged)

    project = Project(
        id=project_id,
        user_id=body.user_id,
        name=body.name or "Untitled Short",
        template_id=body.template_id,
        status=ProjectStatus.DRAFT,
        config=config,
    )
    storage.save_project(project)
    return project


@app.get("/api/projects", response_model=List[Project])
def list_all_projects() -> List[Project]:
    return storage.list_projects()


@app.get("/api/projects/{project_id}", response_model=Project)
def get_project(project_id: str) -> Project:
    return _require_project(project_id)


@app.put("/api/projects/{project_id}/config", response_model=Project)
def update_config(project_id: str, body: ConfigUpdate) -> Project:
    project = _require_project(project_id)
    if body.name is not None:
        project.name = body.name
    if body.config is not None:
        project.config = body.config
    storage.save_project(project)
    return project


# --------------------------------------------------------------------------- #
# Upload (multipart)
# --------------------------------------------------------------------------- #
@app.post("/api/projects/{project_id}/upload", response_model=Project)
async def upload_assets(
    project_id: str,
    images: Optional[List[UploadFile]] = File(default=None),
    audio: Optional[UploadFile] = File(default=None),
    srt: Optional[UploadFile] = File(default=None),
) -> Project:
    project = _require_project(project_id)

    # --- images (append, preserving order) --- #
    if images:
        for up in images:
            ext = _ext(up.filename or "")
            if ext not in IMAGE_EXT:
                raise HTTPException(
                    status_code=400,
                    detail=f"Formato de imagem inválido: {up.filename} ({ext})",
                )
            data = await up.read()
            if len(data) > MAX_IMAGE_BYTES:
                raise HTTPException(
                    status_code=400, detail=f"Imagem muito grande: {up.filename}"
                )
            saved = storage.save_upload(project_id, up.filename or "image", data)
            existing = {img.file for img in project.config.images}
            if saved.name not in existing:
                from models import ImageClip

                project.config.images.append(ImageClip(file=saved.name))

    # --- audio (single) --- #
    if audio is not None:
        ext = _ext(audio.filename or "")
        if ext not in AUDIO_EXT:
            raise HTTPException(
                status_code=400, detail=f"Formato de áudio inválido: {audio.filename}"
            )
        data = await audio.read()
        if len(data) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=400, detail="Áudio muito grande")
        saved = storage.save_upload(project_id, audio.filename or "audio", data)
        project.config.audio.file = saved.name
        project.config.audio.duration = probe_duration(saved)

    # --- srt (single) --- #
    if srt is not None:
        ext = _ext(srt.filename or "")
        if ext not in SRT_EXT:
            raise HTTPException(
                status_code=400, detail=f"Legenda deve ser .srt: {srt.filename}"
            )
        data = await srt.read()
        if len(data) > MAX_SRT_BYTES:
            raise HTTPException(status_code=400, detail="SRT muito grande")
        saved = storage.save_upload(project_id, srt.filename or "captions.srt", data)
        project.config.srt = saved.name

    storage.save_project(project)
    return project


# --------------------------------------------------------------------------- #
# Generate (render) + jobs
# --------------------------------------------------------------------------- #
def _run_render(project_id: str, job_id: str, resume: bool = False) -> None:
    """Background worker: run the pure engine, mirror progress to job+project.

    ``resume=True`` reaproveita os checkpoints em disco (retoma após restart);
    ``resume=False`` limpa a saída anterior para um render limpo.
    """
    project = storage.load_project(project_id)
    if project is None:
        registry.update(job_id, status=JobStatus.FAILED, error="Projeto sumiu")
        return

    def progress_cb(percent: float, message: str = "") -> None:
        registry.update(job_id, status=JobStatus.RUNNING, progress=percent, message=message)
        project.progress = percent
        project.status = ProjectStatus.RENDERING
        storage.save_project(project)

    registry.update(job_id, status=JobStatus.RUNNING, progress=0.0,
                    message="Retomando" if resume else "Iniciando")
    project.status = ProjectStatus.RENDERING
    project.error = None
    storage.save_project(project)

    try:
        output_dir = storage.output_dir(project_id)
        if not resume:
            # render limpo: descarta checkpoints antigos (evita reusar config velha)
            shutil.rmtree(output_dir, ignore_errors=True)
            output_dir = storage.output_dir(project_id)
        out_path = render(project.config.model_dump(), output_dir, progress_cb, resume=resume)
        rel = Path(out_path).name
        project.output_file = rel
        project.status = ProjectStatus.DONE
        project.progress = 100.0
        storage.save_project(project)
        registry.update(
            job_id,
            status=JobStatus.DONE,
            progress=100.0,
            message="Concluído",
            output_file=rel,
        )
    except Exception as exc:  # noqa: BLE001 — surface any engine error to the client
        project.status = ProjectStatus.FAILED
        project.error = str(exc)
        storage.save_project(project)
        registry.update(job_id, status=JobStatus.FAILED, error=str(exc))


@app.post("/api/projects/{project_id}/generate", response_model=Job)
def generate(project_id: str, background_tasks: BackgroundTasks) -> Job:
    project = _require_project(project_id)
    if not project.config.images:
        raise HTTPException(status_code=400, detail="Adicione ao menos uma imagem")
    if not project.config.audio.file:
        raise HTTPException(status_code=400, detail="Adicione a narração (áudio)")

    # pré-voo: assets ausentes -> erro claro AGORA (não trava aos 85%)
    problems = validate_assets(project.config.model_dump(), storage.output_dir(project_id))
    if problems:
        raise HTTPException(status_code=400, detail="Assets faltando: " + "; ".join(problems))

    job = registry.create(project_id)
    project.status = ProjectStatus.QUEUED
    project.progress = 0.0
    storage.save_project(project)
    background_tasks.add_task(_run_render, project_id, job.id, False)
    return job


@app.post("/api/projects/{project_id}/resume", response_model=Job)
def resume(project_id: str, background_tasks: BackgroundTasks) -> Job:
    """Retoma um render do último checkpoint (após restart da instância).

    Baseado no projeto (jobs são em memória e somem no restart). Reaproveita
    cenas/concat/vídeo/mix já prontos em disco.
    """
    project = _require_project(project_id)
    if not project.config.images or not project.config.audio.file:
        raise HTTPException(status_code=400, detail="Projeto incompleto para retomar")

    job = registry.create(project_id)
    project.status = ProjectStatus.QUEUED
    storage.save_project(project)
    background_tasks.add_task(_run_render, project_id, job.id, True)
    return job


@app.get("/api/jobs/{job_id}", response_model=Job)
def get_job(job_id: str) -> Job:
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job


@app.get("/api/projects/{project_id}/uploads/{filename}")
def serve_upload(project_id: str, filename: str) -> FileResponse:
    """Serve an uploaded asset (thumbnails / audio player in the frontend)."""
    _require_project(project_id)
    safe = Path(filename).name  # block traversal
    path = storage.uploads_dir(project_id) / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(path)


@app.get("/api/projects/{project_id}/download")
def download(project_id: str) -> FileResponse:
    project = _require_project(project_id)
    if not project.output_file:
        raise HTTPException(status_code=404, detail="Nenhum render disponível ainda")
    path = storage.output_dir(project_id) / project.output_file
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de saída não encontrado")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"{project.name or 'short'}.mp4",
    )


# --------------------------------------------------------------------------- #
# Asset library (SFX / music)
# --------------------------------------------------------------------------- #
def _list_assets(kind: str) -> List[AssetInfo]:
    directory = storage.assets_dir(kind)
    assets: List[AssetInfo] = []
    for path in sorted(directory.glob("*")):
        if path.is_file() and not path.name.startswith("."):
            assets.append(
                AssetInfo(file=f"{kind}/{path.name}", name=path.stem, kind=kind)
            )
    return assets


@app.get("/api/assets/sfx", response_model=List[AssetInfo])
def list_sfx() -> List[AssetInfo]:
    return _list_assets("sfx")


@app.get("/api/assets/music", response_model=List[AssetInfo])
def list_music() -> List[AssetInfo]:
    return _list_assets("music")


# --------------------------------------------------------------------------- #
# Serve the built frontend (produção: uma URL só serve site + API).
# Em dev, o Vite roda separado (:5173) e este mount nem existe (sem dist).
# Registrado por ÚLTIMO para não sombrear as rotas /api/*.
# --------------------------------------------------------------------------- #
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _frontend_dist.exists():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
