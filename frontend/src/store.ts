import { create } from 'zustand'
import { api } from './api/client'
import type {
  AssetInfo,
  CaptionStyle,
  ImageClip,
  Job,
  Project,
  ProjectConfig,
  Template,
} from './types'

export type Toast = { id: number; kind: 'error' | 'success' | 'info'; msg: string }

interface State {
  step: number
  templates: Template[]
  sfxLib: AssetInfo[]
  musicLib: AssetInfo[]
  project: Project | null
  job: Job | null
  busy: boolean
  toasts: Toast[]

  init: () => Promise<void>
  toast: (kind: Toast['kind'], msg: string) => void
  dismissToast: (id: number) => void
  setStep: (s: number) => void

  createFromTemplate: (templateId: string, name: string) => Promise<void>
  uploadFiles: (files: { images?: File[]; audio?: File; srt?: File }) => Promise<void>

  patchConfig: (fn: (c: ProjectConfig) => void) => void
  setImages: (imgs: ImageClip[]) => void
  autoTimingByName: () => void
  distributeEvenly: () => void
  setCaptionStyle: (s: CaptionStyle) => void
  saveConfig: () => Promise<void>

  generate: () => Promise<void>
  duplicate: () => Promise<void>
  reset: () => void
}

let toastId = 0

/** Parse "M_SS" (e.g. 0_26 -> 26s, 1_05 -> 65s) from a filename stem. */
function parseNameSeconds(file: string): number | null {
  const stem = file.replace(/\.[^.]+$/, '')
  const m = stem.match(/(\d+)[_:](\d{1,2})/)
  if (!m) return null
  return parseInt(m[1], 10) * 60 + parseInt(m[2], 10)
}

export const useStore = create<State>((set, get) => ({
  step: 0,
  templates: [],
  sfxLib: [],
  musicLib: [],
  project: null,
  job: null,
  busy: false,
  toasts: [],

  init: async () => {
    try {
      const [templates, sfxLib, musicLib] = await Promise.all([
        api.listTemplates(),
        api.listSfx(),
        api.listMusic(),
      ])
      set({ templates, sfxLib, musicLib })
    } catch (e) {
      get().toast('error', `Falha ao carregar dados: ${(e as Error).message}`)
    }
  },

  toast: (kind, msg) =>
    set((s) => ({ toasts: [...s.toasts, { id: ++toastId, kind, msg }] })),
  dismissToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

  setStep: (step) => set({ step }),

  createFromTemplate: async (templateId, name) => {
    set({ busy: true })
    try {
      const project = await api.createProject({ template_id: templateId, name })
      set({ project })
    } catch (e) {
      get().toast('error', `Não foi possível criar o projeto: ${(e as Error).message}`)
      throw e
    } finally {
      set({ busy: false })
    }
  },

  uploadFiles: async (files) => {
    const { project } = get()
    if (!project) return
    set({ busy: true })
    try {
      const updated = await api.upload(project.id, files)
      set({ project: updated })
      get().toast('success', 'Arquivos enviados.')
    } catch (e) {
      get().toast('error', `Falha no upload: ${(e as Error).message}`)
    } finally {
      set({ busy: false })
    }
  },

  patchConfig: (fn) =>
    set((s) => {
      if (!s.project) return {}
      const config: ProjectConfig = structuredClone(s.project.config)
      fn(config)
      return { project: { ...s.project, config } }
    }),

  setImages: (images) => get().patchConfig((c) => void (c.images = images)),

  autoTimingByName: () => {
    get().patchConfig((c) => {
      c.images.forEach((img) => {
        const secs = parseNameSeconds(img.file)
        if (secs !== null) img.start = secs
      })
    })
    get().toast('info', 'Auto-timing aplicado pelos nomes (M_SS).')
  },

  distributeEvenly: () => {
    get().patchConfig((c) => {
      const total = c.audio.duration || c.images.length * 3
      const per = c.images.length ? total / c.images.length : 0
      c.images.forEach((img, i) => (img.start = +(i * per).toFixed(2)))
    })
    get().toast('info', 'Imagens distribuídas uniformemente.')
  },

  setCaptionStyle: (style) => get().patchConfig((c) => void (c.caption_style = style)),

  saveConfig: async () => {
    const { project } = get()
    if (!project) return
    try {
      const updated = await api.updateConfig(project.id, {
        name: project.name,
        config: project.config,
      })
      set({ project: updated })
    } catch (e) {
      get().toast('error', `Falha ao salvar: ${(e as Error).message}`)
      throw e
    }
  },

  generate: async () => {
    const { project } = get()
    if (!project) return
    set({ busy: true, job: null })
    try {
      await get().saveConfig()
      const job = await api.generate(project.id)
      set({ job })
      // poll every 2s
      const poll = async () => {
        try {
          const j = await api.getJob(job.id)
          set({ job: j })
          if (j.status === 'done') {
            const p = await api.getProject(project.id)
            set({ project: p, busy: false })
            get().toast('success', 'Short gerado! 🎬')
            return
          }
          if (j.status === 'failed') {
            set({ busy: false })
            get().toast('error', `Render falhou: ${j.error ?? 'erro desconhecido'}`)
            return
          }
          setTimeout(poll, 2000)
        } catch (e) {
          set({ busy: false })
          get().toast('error', `Falha no polling: ${(e as Error).message}`)
        }
      }
      setTimeout(poll, 2000)
    } catch (e) {
      set({ busy: false })
      get().toast('error', `Não foi possível gerar: ${(e as Error).message}`)
    }
  },

  duplicate: async () => {
    const { project } = get()
    if (!project) return
    set({ busy: true })
    try {
      const copy = await api.createProject({
        template_id: project.template_id ?? undefined,
        name: `${project.name} (cópia)`,
      })
      const withConfig = await api.updateConfig(copy.id, {
        name: copy.name,
        config: project.config,
      })
      set({ project: withConfig, job: null, step: 1 })
      get().toast('info', 'Projeto duplicado — reenvie os arquivos para renderizar.')
    } catch (e) {
      get().toast('error', `Falha ao duplicar: ${(e as Error).message}`)
    } finally {
      set({ busy: false })
    }
  },

  reset: () => set({ project: null, job: null, step: 0 }),
}))
