# 🚀 Deploy — acessar o Short Factory por uma URL

O app é **uma imagem Docker única**: o backend (FastAPI + ffmpeg) serve o
frontend já buildado **e** a API na mesma URL. Ou seja: 1 serviço → 1 link.

> ⚠️ **Render free = DEMO.** O plano grátis tem **512 MB de RAM**. O render foi
> otimizado para caber nisso (pico de ~295 MB no ffmpeg, medido no Short 1 de
> 47,7s — vídeo e áudio renderizados em passos separados, `-threads` limitado).
> Ainda assim, **para produção use uma instância com ≥ 2 GB** (ou um worker
> separado para o render): mais RAM = encode mais rápido, sem risco de restart.
> Se a instância reiniciar no meio, o app **retoma do último checkpoint**
> (botão "Retomar render") — nada é perdido.

> Por que não Vercel/Netlify? Porque o app **renderiza vídeo com ffmpeg** (roda
> por minutos, grava arquivos). Isso precisa de um host que rode **Docker**, não
> de hospedagem serverless de site estático.

---

## Opção A — Render (recomendado, tem plano grátis) 🟢

### Jeito mais rápido: botão de deploy

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/danielrodovalho228-ship-it/Site-Criar-Shorts/tree/claude/shorts-creation-site-1hgmiy)

Clique no botão → logue com o GitHub → **Apply**. O Render lê o `render.yaml`,
builda o `Dockerfile` (~5-10 min na 1ª vez) e te dá uma URL pública.

### Ou manualmente

1. Crie conta em **https://render.com** (pode logar com o GitHub).
2. **New +** → **Blueprint**.
3. Conecte este repositório e selecione a branch
   `claude/shorts-creation-site-1hgmiy`. O Render lê o `render.yaml` e a
   `Dockerfile` sozinho.
4. Clique **Apply**. Ele builda (5-10 min na 1ª vez) e te dá uma URL tipo
   `https://short-factory.onrender.com`.
5. Abra a URL → é o site. Use o preset ⭐ **The Chapter — Short 1**, suba os
   arquivos e gere.

**Avisos do plano grátis (ok para testar):**
- O serviço **hiberna** após ~15 min sem uso; o 1º acesso depois disso demora
  ~30-50s pra "acordar". Normal.
- **Disco é efêmero**: uploads e vídeos gerados somem quando o serviço
  reinicia. Baixe o mp4 logo após gerar. (Para persistir, use um disco pago —
  já deixei comentado no `render.yaml`.)
- Render grátis tem CPU limitada → o render pode ser mais lento que na sua
  máquina.

---

## Opção A2 — Frontend na Vercel + Backend no Render (split) 🔷

Bom se você já paga a Vercel: o **frontend** roda na Vercel (CDN rápido, seu
domínio) e o **backend + ffmpeg** fica no Render (o render pesado precisa do
container — não roda em serverless).

**Passos:**
1. O backend já está no Render (Opção A) — anote a URL, ex.:
   `https://short-factory-04vp.onrender.com`.
2. Na Vercel: **Add New → Project** → importe este repositório.
3. Em **Root Directory**, selecione **`frontend`** (o app Vite está lá).
4. Em **Environment Variables**, adicione:
   `VITE_API_BASE = https://short-factory-04vp.onrender.com`
   (a URL do seu backend Render, sem barra no final).
5. **Deploy.** A Vercel builda o Vite e te dá a URL do frontend.

Pronto: o frontend na Vercel chama a API do Render (CORS já liberado no
backend). O wake-up do app "acorda" o Render no primeiro clique.

> Sem `VITE_API_BASE`, o frontend chama `/api` na mesma origem (modo monólito
> do Render, Opção A). Com a variável, ele aponta para o backend remoto.

## Opção B — Railway (alternativa simples)

1. **https://railway.app** → New Project → **Deploy from GitHub repo**.
2. Selecione este repo. Railway detecta a `Dockerfile` e faz o deploy.
3. Em **Settings → Networking → Generate Domain** para obter a URL pública.

---

## Opção C — Seu próprio computador ou um VPS (Docker)

Com Docker instalado:

```bash
docker compose up --build
```

Abra **http://localhost:8000**. Num VPS, aponte um domínio/porta pra ele
(idealmente atrás de um proxy com HTTPS, ex.: Caddy/Nginx). O `docker-compose.yml`
já monta `./storage` como volume, então uploads/renders **persistem**.

---

## Opção D — Sem Docker, na máquina do Daniel

É o caminho do **[QUICKSTART.md](QUICKSTART.md)** (2 duplo-cliques no Windows).
Não dá URL pública, mas roda 100% local e rápido — é o recomendado para o
**gate P0**.

---

## Legendas automáticas (ElevenLabs Scribe) 🎙️→📝

O botão **"✨ Gerar legendas (auto)"** transcreve a narração e cria o SRT
sozinho (+ detecta as pausas p/ o "Auto-timing pela narração"). Precisa de uma
chave da ElevenLabs, definida como **variável de ambiente secreta** (nunca no
código):

- **Render:** Dashboard do serviço → **Environment** → adicione
  `ELEVENLABS_API_KEY` = *sua chave* → Save (o serviço reinicia).
- **Local (Windows):** antes de rodar o `start_backend.bat`, no mesmo terminal:
  `set ELEVENLABS_API_KEY=sua_chave` — ou defina nas variáveis de ambiente do
  Windows.

Sem a chave, o app funciona normalmente; só o botão de auto-legenda retorna um
aviso claro pedindo a chave.

## Biblioteca de sons no deploy

Os SFX/músicas ficam em `storage/assets/{sfx,music}/` e **não vão no Git**
(licenciamento). Para tê-los no deploy, suba os arquivos licenciados para essa
pasta (num VPS/volume) ou adicione um passo de download no build. Sem eles, o
app funciona — só não lista sons na biblioteca.
