# 🏭 Short Factory

> 👉 **Só quer rodar o app no Windows e produzir Shorts?** Veja o
> **[QUICKSTART.md](QUICKSTART.md)** (à prova de leigo: 2 duplo-cliques).


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

## Rodar o frontend (Sprint 2)

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173 (proxia /api -> :8000)
```

Wizard de 4 passos (Upload → Configurar → Preview → Gerar): seletor de
template, dropzones com thumbnails/player/preview de SRT, tabela de cenas com
reordenação por drag (dnd-kit), auto-timing por nome (M_SS) + distribuir,
painel de hook/CTA/música/SFX/legendas/caption_fixes, barra de cobertura,
timeline proporcional com marcadores, e geração com progresso + player +
download + duplicar. Stack: React + TS + Vite + Tailwind v4 + Zustand + dnd-kit
+ react-dropzone. Backend precisa estar rodando na :8000.

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

### Parâmetros reconciliados com o motor original

- `force_style` navy: `FontName=DejaVu Sans,Bold=1,Fontsize=15,PrimaryColour=&H3C231A&,OutlineColour=&HFFFFFF&,Outline=2.2,MarginV=55,Alignment=2`
- punch dentro do zoompan: `if(lt(on,N),0.06*(1-on/N),0)` somado ao `z`
- áudio: `amix=...:duration=first:normalize=0`
- saída final: `-preset medium -crf 19`
- hook aceita `|` como quebra de linha (ex.: `A JANITOR DIED|WITH $9,000,000`)

Melhorias mantidas sobre o original: word-wrap do CTA/hook (safe area),
resolução robusta de caminhos (uploads/), CTA acima da faixa de legendas.

> ⚠️ O `.py` original ainda não chegou no anexo — o motor foi portado da spec +
> parâmetros exatos que o PO forneceu. Ao ter o `short_factory.py` em mãos, faça
> um diff final contra `render.py`.

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
