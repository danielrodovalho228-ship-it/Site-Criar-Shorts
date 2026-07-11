# 🏭 Short Factory

Fábrica de **Shorts verticais (1080×1920)** para YouTube / Reels / TikTok.

Filosofia (do plano master): **BYO assets + montagem perfeita**. O criador traz
a **própria voz** (narração MP3), as **próprias imagens** e o **próprio roteiro**
(SRT). O app faz a parte chata — sincronização por timestamp, zoom/pan, punch,
hook/CTA, SFX e legendas — com padrão profissional.

> **Fase atual: P0 (dogfood).** Sem login, sem billing, sem banco de dados.
> Projetos vivem em disco como `project.json`. Cada fase paga a próxima.

---

## Estrutura

```
backend/
  main.py             # FastAPI — rotas
  render.py           # MOTOR PURO (recebe config → devolve mp4). ⬅ PORT SITE
  models.py           # schemas Pydantic (== project.json)
  storage.py          # storage por interface (driver local; S3 = 1 arquivo)
  jobs.py             # fila por interface (BackgroundTasks; Redis depois)
  media.py            # ffprobe (duração)
  templates_loader.py # templates como DADOS
  templates/          # book_summary.json, custom.json
scripts/
  smoke_test.py       # QA: gera short de teste e valida 1080x1920 via ffprobe
storage/
  projects/{uuid}/    # project.json + uploads/ + output/
  assets/{sfx,music}/ # biblioteca licenciada (ver LICENSES.md)
```

## Pré-requisitos

- **Python 3.11+**
- **FFmpeg + ffprobe** no PATH
  - Windows: `winget install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Linux: `apt install ffmpeg`

## Rodar o backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Docs interativas: http://localhost:8000/docs

## Rotas (Sprint 1)

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/health` | health check |
| GET | `/api/templates` | lista templates |
| POST | `/api/projects` | cria projeto (aceita `template_id`) |
| GET | `/api/projects` | lista projetos |
| GET | `/api/projects/{id}` | detalha projeto |
| PUT | `/api/projects/{id}/config` | atualiza config |
| POST | `/api/projects/{id}/upload` | upload multipart `images[]` / `audio` / `srt` |
| POST | `/api/projects/{id}/generate` | enfileira render → `job_id` |
| GET | `/api/jobs/{job_id}` | status do job (polling) |
| GET | `/api/projects/{id}/download` | baixa o mp4 |
| GET | `/api/assets/sfx` · `/api/assets/music` | biblioteca de sons |

## Motor de render (`render.py`)

`render(config, work_dir, progress_cb) -> str` é **puro** e implementa o
pipeline completo (Sprint 1):

- **zoompan alternado**: zoom-in `1.0->1.12` / zoom-out `1.12->1.0` (+ pan-left,
  pan-right, fade, static)
- **punch de 0.15s** na entrada de cada clipe (pop de +8% que decai)
- **hook** com 2 linhas, navy `#1A233C` + coral `#E76F51`, contorno branco,
  visível do frame 0 **sem fade**
- **CTA** coral, contorno branco, na janela `start..end` (com quebra automática)
- **legendas** via `subtitles` + `force_style` navy/branco, com `caption_fixes`
  aplicados no SRT
- **áudio**: `amix` de narração + música em loop (volume do config) + SFX com
  `adelay`

Hardening de produção (Parte C3): pathlib + forward slashes, **nunca**
`-shortest` (usa `-map` + `-t`), concat `-f concat -safe 0`, aviso de imagem
>5s, aviso de MP3 trocado, timeout de 5 min, log completo do ffmpeg por projeto.

> ⚠️ **Reconciliar com o `short_factory.py`:** o motor foi portado a partir da
> **especificação detalhada** (o arquivo `.py` não chegou no anexo). Ao ter o
> `short_factory.py` original em mãos, faça um diff contra `render.py` e ajuste
> qualquer parâmetro do seu motor já testado que divirja.

## Smoke test

```bash
python scripts/smoke_test.py
```

Gera um short de teste (3 imagens, hook, CTA, 1 SFX) e valida duração +
resolução 1080×1920. Mostra `PENDING` (não falha) se faltar ffmpeg ou o motor
ainda não estiver portado.

## Licenças de áudio

Ver `storage/assets/LICENSES.md`. **Uso comercial + redistribuição obrigatório;
nunca sons do CapCut.**
