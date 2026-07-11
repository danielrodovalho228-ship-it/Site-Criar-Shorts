# 🚀 Deploy — acessar o Short Factory por uma URL

O app é **uma imagem Docker única**: o backend (FastAPI + ffmpeg) serve o
frontend já buildado **e** a API na mesma URL. Ou seja: 1 serviço → 1 link.

> Por que não Vercel/Netlify? Porque o app **renderiza vídeo com ffmpeg** (roda
> por minutos, grava arquivos). Isso precisa de um host que rode **Docker**, não
> de hospedagem serverless de site estático.

---

## Opção A — Render (recomendado, tem plano grátis) 🟢

1. Crie conta em **https://render.com** (pode logar com o GitHub).
2. **New +** → **Blueprint**.
3. Conecte este repositório. O Render lê o `render.yaml` e a `Dockerfile`
   sozinho.
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

## Biblioteca de sons no deploy

Os SFX/músicas ficam em `storage/assets/{sfx,music}/` e **não vão no Git**
(licenciamento). Para tê-los no deploy, suba os arquivos licenciados para essa
pasta (num VPS/volume) ou adicione um passo de download no build. Sem eles, o
app funciona — só não lista sons na biblioteca.
