import { create } from 'zustand'
import { api } from './api/client'
import { fileToken, type Preset } from './presets'
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
  preset: Preset | null
  interrupted: boolean
  waking: boolean
  wakeSeconds: number

  init: () => Promise<void>
  toast: (kind: Toast['kind'], msg: string) => void
  dismissToast: (id: number) => void
  setStep: (s: number) => void

  createFromTemplate: (templateId: string, name: string) => Promise<void>
  loadPreset: (preset: Preset) => Promise<void>
  applyPresetLayout: () => void
  uploadFiles: (files: { images?: File[]; audio?: File; srt?: File }) => Promise<void>

  patchConfig: (fn: (c: ProjectConfig) => void) => void
  setImages: (imgs: ImageClip[]) => void
  autoTimingByName: () => void
  distributeEvenly: () => void
  setCaptionStyle: (s: CaptionStyle) => void
  transcribe: () => Promise<void>
  autotimeNarration: () => Promise<void>
  saveConfig: () => Promise<void>

  generate: () => Promise<void>
  resume: () => Promise<void>
  startPolling: (jobId: string) => void
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
  preset: null,
  interrupted: false,
  waking: true,
  wakeSeconds: 0,

  init: async () => {
    // Wake-up (item 2): no free tier o Render hiberna após 15 min e leva ~50s
    // pra acordar. Pinga /health com retry mostrando "acordando o servidor".
    set({ waking: true, wakeSeconds: 0 })
    let awake = false
    const t0 = Date.now()
    for (let attempt = 0; attempt < 45; attempt++) {
      try {
        await api.health()
        awake = true
        break
      } catch {
        set({ wakeSeconds: Math.round((Date.now() - t0) / 1000) })
        await new Promise((r) => setTimeout(r, 2000))
      }
    }
    set({ waking: false })
    if (!awake) {
      get().toast('error', 'Servidor não respondeu. Recarregue a página em 1 min.')
      return
    }
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

  toast: (kind, msg) => {
    const id = ++toastId
    set((s) => ({ toasts: [...s.toasts, { id, kind, msg }] }))
    // auto-dismiss (evita empilhar e cobrir botões)
    setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), 5000)
  },
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

  loadPreset: async (preset) => {
    set({ busy: true })
    try {
      const project = await api.createProject({
        template_id: preset.template_id,
        name: preset.name,
      })
      set({ project, preset })
      get().patchConfig((c) => {
        c.hook = { text: preset.hook.text, duration: preset.hook.duration }
        c.cta = { ...preset.cta }
        c.caption_fixes = { ...preset.caption_fixes }
        c.caption_style = preset.caption_style
      })
      await get().saveConfig()
      get().toast(
        'info',
        `Preset "${preset.name}" carregado. Suba as imagens (nomes M_SS), o MP3 e o SRT.`,
      )
    } catch (e) {
      get().toast('error', `Falha ao carregar preset: ${(e as Error).message}`)
    } finally {
      set({ busy: false })
    }
  },

  applyPresetLayout: () => {
    const { preset, project } = get()
    if (!preset || !project || project.config.images.length === 0) return
    const byToken = new Map<string, ImageClip>()
    project.config.images.forEach((im) => {
      const t = fileToken(im.file)
      if (t) byToken.set(t, im)
    })
    const ordered: ImageClip[] = []
    const used = new Set<string>()
    const missing: string[] = []
    preset.images.forEach((pi) => {
      const im = byToken.get(pi.token)
      if (im) {
        ordered.push({ ...im, start: pi.start, effect: pi.effect })
        used.add(im.file)
      } else {
        missing.push(pi.token)
      }
    })
    // keep any uploaded images not covered by the preset, appended in order
    project.config.images.forEach((im) => {
      if (!used.has(im.file)) ordered.push(im)
    })
    get().patchConfig((c) => void (c.images = ordered))
    if (missing.length) {
      get().toast('info', `Preset aplicado. Faltam imagens: ${missing.join(', ')}.`)
    } else {
      get().toast('success', 'Preset aplicado às imagens (ordem + timing).')
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
      // if a preset is active and images were sent, snap ordering + timing
      // and PERSIST it, so later uploads don't clobber the reorder.
      if (get().preset && files.images?.length) {
        get().applyPresetLayout()
        await get().saveConfig()
      }
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

  transcribe: async () => {
    const { project } = get()
    if (!project) return
    set({ busy: true })
    try {
      const r = await api.transcribe(project.id)
      const p = await api.getProject(project.id)
      set({ project: p })
      get().toast(
        'success',
        `Legendas geradas: ${r.cue_count} trechos, ${r.pause_count} pausas detectadas.`,
      )
    } catch (e) {
      get().toast('error', `Falha ao transcrever: ${(e as Error).message}`)
    } finally {
      set({ busy: false })
    }
  },

  autotimeNarration: async () => {
    const { project } = get()
    if (!project) return
    set({ busy: true })
    try {
      const p = await api.autotime(project.id)
      set({ project: p })
      get().toast('success', 'Cenas distribuídas nas pausas da narração.')
    } catch (e) {
      get().toast('error', `Auto-timing pela narração: ${(e as Error).message}`)
    } finally {
      set({ busy: false })
    }
  },

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

  // Polling resiliente (item 4): backoff exponencial 2s→4s→8s antes de
  // declarar interrupção. Compartilhado por generate e resume.
  startPolling: (jobId: string) => {
    const { project } = get()
    if (!project) return
    let fails = 0
    const MAX_FAILS = 5
    const poll = async () => {
      try {
        const j = await api.getJob(jobId)
        fails = 0
        set({ job: j })
        if (j.status === 'done') {
          const p = await api.getProject(project.id)
          set({ project: p, busy: false, interrupted: false })
          get().toast('success', 'Short gerado! 🎬')
          return
        }
        if (j.status === 'failed') {
          set({ busy: false })
          get().toast('error', `Render falhou: ${j.error ?? 'erro desconhecido'}`)
          return
        }
        setTimeout(poll, 2000)
      } catch {
        fails += 1
        if (fails >= MAX_FAILS) {
          // item 3: provável restart da instância → oferece retomar
          set({ busy: false, interrupted: true })
          get().toast(
            'info',
            'O servidor não respondeu (pode ter reiniciado). Você pode retomar o render de onde parou.',
          )
          return
        }
        const delay = Math.min(2000 * 2 ** (fails - 1), 8000) // 2s, 4s, 8s, 8s…
        setTimeout(poll, delay)
      }
    }
    setTimeout(poll, 2000)
  },

  generate: async () => {
    const { project } = get()
    if (!project) return
    set({ busy: true, job: null, interrupted: false })
    try {
      await get().saveConfig()
      const job = await api.generate(project.id)
      set({ job })
      get().startPolling(job.id)
    } catch (e) {
      set({ busy: false })
      get().toast('error', `Não foi possível gerar: ${(e as Error).message}`)
    }
  },

  resume: async () => {
    const { project } = get()
    if (!project) return
    set({ busy: true, interrupted: false })
    try {
      const job = await api.resume(project.id)
      set({ job })
      get().toast('info', 'Retomando o render…')
      get().startPolling(job.id)
    } catch (e) {
      set({ busy: false, interrupted: true })
      get().toast('error', `Não foi possível retomar: ${(e as Error).message}`)
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

  reset: () =>
    set({ project: null, job: null, step: 0, preset: null, interrupted: false }),
}))
