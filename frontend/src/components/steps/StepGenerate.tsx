import { useStore } from '../../store'
import { api } from '../../api/client'

export function StepGenerate() {
  const project = useStore((s) => s.project)!
  const job = useStore((s) => s.job)
  const busy = useStore((s) => s.busy)
  const generate = useStore((s) => s.generate)
  const duplicate = useStore((s) => s.duplicate)
  const setStep = useStore((s) => s.setStep)

  const rendering = job?.status === 'queued' || job?.status === 'running'
  const done = project.status === 'done' && project.output_file
  const progress = job?.progress ?? project.progress ?? 0

  return (
    <section className="flex flex-col items-center gap-6">
      {!done && (
        <button
          disabled={busy || rendering}
          onClick={generate}
          className="btn-sticker bg-coral px-10 py-5 text-xl font-black text-white active:btn-sticker-active disabled:opacity-50"
        >
          {rendering ? 'Renderizando…' : '🎬 Gerar Short'}
        </button>
      )}

      {(rendering || busy) && (
        <div className="w-full max-w-md">
          <div className="h-6 w-full overflow-hidden rounded-full border-[3px] border-navy bg-white">
            <div
              className="h-full bg-teal transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="mt-2 text-center text-sm font-bold text-navy/70">
            {progress.toFixed(0)}% · {job?.message || 'preparando…'}
          </p>
        </div>
      )}

      {job?.status === 'failed' && (
        <div className="card-sticker max-w-md bg-coral/10 p-4 text-sm font-medium text-navy">
          <b className="text-coral">Falha no render.</b>
          <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-xs">
            {job.error}
          </pre>
        </div>
      )}

      {done && (
        <div className="flex w-full max-w-sm flex-col items-center gap-4">
          <video
            controls
            src={api.downloadUrl(project.id)}
            className="w-full rounded-xl border-[3px] border-navy shadow-[4px_4px_0_0_#1A233C]"
          />
          <div className="flex flex-wrap justify-center gap-3">
            <a
              href={api.downloadUrl(project.id)}
              download
              className="btn-sticker bg-teal px-6 py-3 font-black text-white active:btn-sticker-active"
            >
              ⬇ Baixar mp4
            </a>
            <button
              onClick={duplicate}
              className="btn-sticker bg-mustard px-6 py-3 font-black text-navy active:btn-sticker-active"
            >
              ⧉ Duplicar projeto
            </button>
          </div>
        </div>
      )}

      <button
        onClick={() => setStep(2)}
        className="btn-sticker bg-white px-5 py-2.5 text-sm font-black text-navy active:btn-sticker-active"
      >
        ← Voltar ao preview
      </button>
    </section>
  )
}
