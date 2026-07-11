import type { CaptionStyle, ImageEffect } from './types'

/** A preset pre-loads the full config; the user only supplies the uploads. */
export interface PresetImage {
  token: string // "M_SS" token to match against uploaded filenames (e.g. 0_26)
  start: number
  effect: ImageEffect
}
export interface Preset {
  id: string
  name: string
  description: string
  template_id: string
  hook: { text: string; duration: number }
  cta: { text: string; start: number; end: number }
  caption_fixes: Record<string, string>
  caption_style: CaptionStyle
  images: PresetImage[] // in play order (0_26 antes de 0_20!)
}

/** Extract the "M_SS" token (e.g. "0_26") from any filename. */
export function fileToken(file: string): string | null {
  const m = file.match(/(\d+)[_:](\d{1,2})(?!\d)/)
  return m ? `${parseInt(m[1], 10)}_${m[2].padStart(2, '0')}` : null
}

export const SHORT1: Preset = {
  id: 'the-chapter-short-1',
  name: 'The Chapter — Short 1',
  description:
    'Config completo do Short 1 (janitor / $9M). Ordem, timing, hook, CTA e correções prontos — falta só subir as 13 imagens + MP3 + SRT.',
  template_id: 'book_summary',
  hook: { text: 'A JANITOR DIED|WITH $9,000,000', duration: 4.0 },
  cta: { text: 'FULL BREAKDOWN -> @TheChapterBooks', start: 38.6, end: 43.8 },
  caption_fixes: { 'Ronald Reed': 'Ronald Read', Reed: 'Read' },
  caption_style: 'navy-white',
  images: [
    { token: '0_00', start: 0.0, effect: 'zoom-in' },
    { token: '0_04', start: 4.0, effect: 'zoom-out' },
    { token: '0_07', start: 7.1, effect: 'zoom-in' },
    { token: '0_09', start: 9.8, effect: 'zoom-out' },
    { token: '0_13', start: 11.2, effect: 'zoom-in' },
    { token: '0_16', start: 14.1, effect: 'zoom-out' },
    { token: '0_26', start: 19.7, effect: 'zoom-in' },
    { token: '0_20', start: 23.4, effect: 'zoom-out' },
    { token: '0_29', start: 26.0, effect: 'zoom-in' },
    { token: '0_32', start: 29.4, effect: 'zoom-out' },
    { token: '0_36', start: 34.5, effect: 'zoom-in' },
    { token: '0_40', start: 38.6, effect: 'zoom-out' },
    { token: '0_44', start: 43.8, effect: 'zoom-in' },
  ],
}

export const PRESETS: Preset[] = [SHORT1]
