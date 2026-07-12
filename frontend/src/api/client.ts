import type { AssetInfo, Job, Project, ProjectConfig, Template } from '../types'

// Em dev/monólito (Render), VITE_API_BASE fica vazio -> usa "/api" na mesma
// origem. No split (frontend na Vercel), defina VITE_API_BASE com a URL do
// backend Render, ex.: https://short-factory-04vp.onrender.com
const API_ORIGIN = (import.meta.env.VITE_API_BASE ?? '').replace(/\/+$/, '')
const BASE = `${API_ORIGIN}/api`

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body?.detail) detail = String(body.detail)
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => fetch(`${BASE}/health`).then(j<{ status: string }>),

  listTemplates: () => fetch(`${BASE}/templates`).then(j<Template[]>),

  createProject: (body: { name?: string; template_id?: string }) =>
    fetch(`${BASE}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(j<Project>),

  getProject: (id: string) => fetch(`${BASE}/projects/${id}`).then(j<Project>),

  listProjects: () => fetch(`${BASE}/projects`).then(j<Project[]>),

  updateConfig: (id: string, body: { name?: string; config?: ProjectConfig }) =>
    fetch(`${BASE}/projects/${id}/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(j<Project>),

  upload: (
    id: string,
    files: { images?: File[]; audio?: File; srt?: File },
  ) => {
    const fd = new FormData()
    files.images?.forEach((f) => fd.append('images', f))
    if (files.audio) fd.append('audio', files.audio)
    if (files.srt) fd.append('srt', files.srt)
    return fetch(`${BASE}/projects/${id}/upload`, {
      method: 'POST',
      body: fd,
    }).then(j<Project>)
  },

  generate: (id: string) =>
    fetch(`${BASE}/projects/${id}/generate`, { method: 'POST' }).then(j<Job>),

  resume: (id: string) =>
    fetch(`${BASE}/projects/${id}/resume`, { method: 'POST' }).then(j<Job>),

  getJob: (jobId: string) => fetch(`${BASE}/jobs/${jobId}`).then(j<Job>),

  listSfx: () => fetch(`${BASE}/assets/sfx`).then(j<AssetInfo[]>),
  listMusic: () => fetch(`${BASE}/assets/music`).then(j<AssetInfo[]>),

  uploadUrl: (id: string, filename: string) =>
    `${BASE}/projects/${id}/uploads/${encodeURIComponent(filename)}`,
  downloadUrl: (id: string) => `${BASE}/projects/${id}/download`,
}
