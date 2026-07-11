# ============================================================
#  Short Factory — imagem única (frontend buildado + API + ffmpeg)
#  Serve TUDO em uma URL só. Roda em qualquer host com Docker
#  (Render, Railway, Fly.io, um VPS...).
# ============================================================

# --- Estágio 1: build do frontend ---
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Estágio 2: runtime Python + ffmpeg ---
FROM python:3.11-slim
# ffmpeg (motor de render) + fontes DejaVu (hook/CTA/legendas)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY --from=frontend /app/frontend/dist frontend/dist

# pastas de trabalho (uploads/renders/biblioteca)
RUN mkdir -p storage/projects storage/assets/sfx storage/assets/music

WORKDIR /app/backend
ENV PORT=8000
EXPOSE 8000
# usa a porta do host (Render/Railway definem $PORT)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
