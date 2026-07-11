import { useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { useStore } from '../../store'
import { api } from '../../api/client'

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
  const uploadFiles = useStore((s) => s.uploadFiles)
  const patchConfig = useStore((s) => s.patchConfig)
  const setStep = useStore((s) => s.setStep)
  const saveConfig = useStore((s) => s.saveConfig)
  const [name, setName] = useState('Meu Short')
  const [srtPreview, setSrtPreview] = useState<string[]>([])

  if (!project) {
    return (
      <section className="flex flex-col gap-5">
        <div>
          <label className="text-sm font-bold text-navy">Nome do projeto</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded-xl border-[3px] border-navy px-3 py-2 font-semibold outline-none focus:bg-mustard/10"
          />
        </div>
        <div>
          <h2 className="mb-3 text-lg font-black text-navy">Escolha um template</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {templates.map((t) => (
              <button
                key={t.id}
                disabled={busy}
                onClick={() => createFromTemplate(t.id, name.trim() || 'Meu Short')}
                className="card-sticker flex flex-col gap-2 p-5 text-left transition hover:-translate-y-0.5 disabled:opacity-50"
              >
                <div className="text-lg font-black text-navy">{t.name}</div>
                <div className="text-xs font-bold uppercase tracking-wide text-teal">
                  {t.niche}
                </div>
                <p className="text-sm font-medium text-navy/60">{t.description}</p>
                {t.recipe && (
                  <p className="mt-1 border-t-2 border-navy/10 pt-2 text-xs text-navy/45">
                    {t.recipe}
                  </p>
                )}
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
        <div className="card-sticker p-4">
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
            <p className="text-sm font-medium text-navy/40">Opcional — sem SRT.</p>
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
