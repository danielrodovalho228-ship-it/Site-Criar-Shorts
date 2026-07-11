// Mirrors backend/models.py

export type ImageEffect =
  | 'zoom-in'
  | 'zoom-out'
  | 'pan-left'
  | 'pan-right'
  | 'fade'
  | 'static'

export const IMAGE_EFFECTS: ImageEffect[] = [
  'zoom-in',
  'zoom-out',
  'pan-left',
  'pan-right',
  'fade',
  'static',
]

export type CaptionStyle = 'navy-white' | 'white-black' | 'yellow-pop' | 'karaoke'

export type ProjectStatus =
  | 'draft'
  | 'queued'
  | 'rendering'
  | 'done'
  | 'failed'

export type JobStatus = 'queued' | 'running' | 'done' | 'failed'

export interface AudioTrack {
  file: string | null
  duration: number
}
export interface ImageClip {
  file: string
  start: number
  effect: ImageEffect
}
export interface Hook {
  text: string
  duration: number
}
export interface CTA {
  text: string
  start: number
  end: number
}
export interface Music {
  file: string | null
  volume: number
}
export interface SFX {
  file: string
  time: number
  volume: number
}
export interface ProjectConfig {
  audio: AudioTrack
  srt: string | null
  caption_fixes: Record<string, string>
  images: ImageClip[]
  hook: Hook
  cta: CTA
  music: Music
  sfx: SFX[]
  caption_style: CaptionStyle
}
export interface Project {
  id: string
  user_id: string | null
  name: string
  template_id: string | null
  status: ProjectStatus
  progress: number
  output_file: string | null
  error: string | null
  config: ProjectConfig
}

export interface Template {
  id: string
  name: string
  description: string
  niche: string
  recipe: string
  cut_range: [number, number] | null
  suggested_sfx: { trigger: string; file: string; note?: string }[]
}

export interface AssetInfo {
  file: string
  name: string
  kind: 'sfx' | 'music'
}

export interface Job {
  id: string
  project_id: string
  status: JobStatus
  progress: number
  message: string
  error: string | null
  output_file: string | null
}
