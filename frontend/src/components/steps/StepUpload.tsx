import { useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useStore } from '../../store'
import { api } from '../../api/client'
import { PRESETS } from '../../presets'

function Dropzone({
  label,
  hint,
  accept,
  multiple,
  onFiles,
}: {
  label: string
  hint: string
  accept: Record<string, string[]>
  multiple: boolean
  onFiles: (files: File[]) => void
}) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept,
    multiple,
    onDrop: (accepted) => accepted.length && onFiles(accepted),
  })
  return (
    <div
      {...getRootProps()}
      className={`card-sticker cursor-pointer px-4 py-6 text-center transition ${
        isDragActive ? 'bg-mustard/30' : 'hover:bg-mustard/10'
      }`}
    >
      <input {...getInputProps()} />
      <div className="text-sm font-black text-navy">{label}</div>
      <div className="mt-1 text-xs font-medium text-navy/50">{hint}</div>
    </div>
  )
}

export function StepUpload() {
  const templates = useStore((s) => s.templates)
  const project = useStore((s) => s.project)
  const busy = useStore((s) => s.busy)
  const createFromTemplate = useStore((s) => s.createFromTemplate)
  const loadPreset = useStore((s) => s.loadPreset)
  const preset = useStore((s) => s.preset)
  const applyPresetLayout = useStore((s) => s.applyPresetLayout)
  const uploadFiles = useStore((s) => s.uploadFiles)
  const transcribe = useStore((s) => s.transcribe)
  const patchConfig = useStore((s) => s.patchConfig)
  const setStep = useStore((s) => s.setStep)
  const saveConfig = useStore((s) => s.saveConfig)
  const [name, setName] = useState('')
  const [srtPreview, setSrtPreview] = useState<string[]>([])

  // subtítulo humano por template (sem badge em CAPS)
  const templateSub = (id: string, fallback: string) =>
    id === 'book_summary'
      ? 'estilo resumo de livro'
      : id === 'custom'
        ? 'controle total'
        : fallback.toLowerCase()

  if (!project) {
    return (
      <section className="flex flex-col gap-6">
        <div>
          <label className="text-sm font-bold text-navy">Nome do projeto</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="ex: Short 3 — Enough"
            className="mt-1 w-full rounded-xl border-[3px] border-navy px-3 py-2 font-semibold outline-none placeholder:font-medium placeholder:text-navy/35 focus:bg-mustard/10"
          />
        </div>

        {PRESETS.length > 0 && (
          <div>
            <h2 className="mb-3 font-display text-lg font-bold text-navy">
              Continue de onde parou
            </h2>
            <div className="flex flex-col gap-4">
              {PRESETS.map((p) => (
                <button
                  key={p.id}
                  disabled={busy}
                  onClick={() => loadPreset(p)}
                  className="card-sticker flex items-stretch overflow-hidden bg-mustard/15 text-left transition hover:-translate-y-0.5 disabled:opacity-50"
                >
                  <img
                    src="/assets/short1_thumb.jpg"
                    alt="Prévia do Short 1"
                    className="w-24 shrink-0 border-r-[3px] border-navy object-cover sm:w-32"
                  />
                  <div className="flex flex-col justify-center gap-2 p-5">
                    <div className="font-display text-xl font-bold text-navy">
                      ⭐ {p.name}
                    </div>
                    <p className="max-w-md text-sm font-medium text-navy/70">
                      {p.description}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        <div>
          <h2 className="mb-3 font-display text-lg font-bold text-navy">
            Ou comece do zero
          </h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {templates.map((t) => (
              <button
                key={t.id}
                disabled={busy}
                onClick={() => createFromTemplate(t.id, name.trim() || 'Meu Short')}
                className="card-sticker flex flex-col gap-0.5 p-4 text-left transition hover:-translate-y-0.5 disabled:opacity-50"
              >
                <div className="font-display text-base font-bold text-navy">
                  {t.name}
                </div>
                <span className="text-xs font-medium text-navy/50">
                  {templateSub(t.id, t.niche)}
                </span>
              </button>
            ))}
          </div>
        </div>
      </section>
    )
  }

  const cfg = project.config
  const readSrt = (file: File) => {
    const reader = new FileReader()
    reader.onload = () => {
      const text = String(reader.result || '')
      const falas = text
        .split(/\r?\n\r?\n/)
        .map((b) => b.split(/\r?\n/).slice(2).join(' ').trim())
        .filter(Boolean)
        .slice(0, 3)
      setSrtPreview(falas)
    }
    reader.readAsText(file)
  }

  return (
    <section className="flex flex-col gap-5">
      {preset && (
        <div className="card-sticker flex flex-wrap items-center justify-between gap-2 bg-mustard/20 px-4 py-3">
          <span className="text-sm font-bold text-navy">
            ⭐ Preset ativo: {preset.name} — ordem, timing, hook, CTA e correções
            já configurados.
          </span>
          {cfg.images.length > 0 && (
            <button
              onClick={applyPresetLayout}
              className="btn-sticker bg-navy px-3 py-1.5 text-xs font-bold text-white active:btn-sticker-active"
            >
              Reaplicar ordem/timing
            </button>
          )}
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-3">
        <Dropzone
          label="🖼️ Imagens"
          hint="Arraste várias (JPG/PNG/WebP)"
          accept={{ 'image/*': ['.jpg', '.jpeg', '.png', '.webp'] }}
          multiple
          onFiles={(files) => uploadFiles({ images: files })}
        />
        <Dropzone
          label="🎙️ Narração"
          hint="Seu áudio (MP3/WAV/M4A)"
          accept={{ 'audio/*': ['.mp3', '.wav', '.m4a', '.aac', '.ogg'] }}
          multiple={false}
          onFiles={(files) => uploadFiles({ audio: files[0] })}
        />
        <Dropzone
          label="📝 Legendas"
          hint="Arquivo .srt (opcional)"
          accept={{ 'text/plain': ['.srt'], 'application/x-subrip': ['.srt'] }}
          multiple={false}
          onFiles={(files) => {
            readSrt(files[0])
            uploadFiles({ srt: files[0] })
          }}
        />
      </div>

      {/* image thumbnails */}
      {cfg.images.length > 0 && (
        <div className="card-sticker p-4">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="font-black text-navy">
              Imagens ({cfg.images.length})
            </h3>
            <span className="text-xs font-medium text-navy/50">
              A ordem e o timing são ajustados no próximo passo
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {cfg.images.map((img, i) => (
              <div key={img.file} className="relative">
                <img
                  src={api.uploadUrl(project.id, img.file)}
                  alt={img.file}
                  className="h-24 w-14 rounded-lg border-2 border-navy object-cover"
                />
                <span className="absolute left-0 top-0 rounded-br-lg rounded-tl-md bg-navy px-1 text-[10px] font-bold text-white">
                  {i + 1}
                </span>
                <button
                  onClick={() =>
                    patchConfig((c) => {
                      c.images = c.images.filter((x) => x.file !== img.file)
                    })
                  }
                  className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full border-2 border-navy bg-coral text-xs font-black text-white"
                  aria-label="Remover"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* audio + srt status */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card-sticker p-4">
          <h3 className="mb-2 font-black text-navy">🎙️ Narração</h3>
          {cfg.audio.file ? (
            <>
              <audio
                controls
                src={api.uploadUrl(project.id, cfg.audio.file)}
                className="w-full"
              />
              <p className="mt-2 text-xs font-medium text-navy/50">
                {cfg.audio.file} · {cfg.audio.duration.toFixed(1)}s
              </p>
            </>
          ) : (
            <p className="text-sm font-medium text-coral">Nenhum áudio enviado.</p>
          )}
        </div>
        <div className="card-sticker flex flex-col p-4">
          <h3 className="mb-2 font-black text-navy">📝 Legendas</h3>
          {cfg.srt ? (
            <>
              <p className="text-xs font-bold text-teal">{cfg.srt}</p>
              <ul className="mt-1 space-y-1 text-xs text-navy/60">
                {srtPreview.map((f, i) => (
                  <li key={i} className="truncate">
                    “{f}”
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="text-sm font-medium text-navy/40">
              Sem SRT — envie o arquivo ou gere automático da narração.
            </p>
          )}
          {cfg.audio.file && (
            <button
              disabled={busy}
              onClick={transcribe}
              title="Transcreve a narração e cria as legendas (ElevenLabs)"
              className="btn-sticker mt-3 self-start bg-teal px-3 py-1.5 text-xs font-bold text-white active:btn-sticker-active disabled:opacity-50"
            >
              ✨ {busy ? 'Transcrevendo…' : 'Gerar legendas (auto)'}
            </button>
          )}
        </div>
      </div>

      <div className="flex justify-end">
        <button
          disabled={!cfg.images.length || !cfg.audio.file}
          onClick={async () => {
            await saveConfig()
            setStep(1)
          }}
          className="btn-sticker bg-navy px-6 py-3 font-black text-white active:btn-sticker-active disabled:opacity-40"
        >
          Configurar →
        </button>
      </div>
    </section>
  )
}
