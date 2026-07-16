import { useStore } from '../../store'
import { api } from '../../api/client'

export function StepGenerate() {
  const project = useStore((s) => s.project)!
  const job = useStore((s) => s.job)
  const busy = useStore((s) => s.busy)
  const interrupted = useStore((s) => s.interrupted)
  const generate = useStore((s) => s.generate)
  const resume = useStore((s) => s.resume)
  const duplicate = useStore((s) => s.duplicate)
  const setStep = useStore((s) => s.setStep)

  const rendering = job?.status === 'queued' || job?.status === 'running'
  const done = project.status === 'done' && project.output_file
  const progress = job?.progress ?? project.progress ?? 0

  return (
    <section className="flex flex-col items-center gap-6">
      {!done && !interrupted && (
        <button
          disabled={busy || rendering}
          onClick={generate}
          className="btn-sticker bg-coral px-10 py-5 text-xl font-black text-white active:btn-sticker-active disabled:opacity-50"
        >
          {rendering ? 'Renderizando…' : '🎬 Gerar Short'}
        </button>
      )}

      {interrupted && !done && (
        <div className="card-sticker flex max-w-md flex-col items-center gap-3 bg-mustard/20 p-5 text-center">
          <p className="text-sm font-bold text-navy">
            ⚠️ O servidor não respondeu — a instância pode ter reiniciado durante
            o render. As etapas já concluídas foram salvas.
          </p>
          <button
            onClick={resume}
            disabled={busy}
            className="btn-sticker bg-navy px-8 py-3 font-black text-white active:btn-sticker-active disabled:opacity-50"
          >
            ↻ Retomar render
          </button>
        </div>
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

      {job?.status === 'failed' && !done && (
        <div className="card-sticker flex max-w-md flex-col items-center gap-3 bg-coral/10 p-4 text-sm font-medium text-navy">
          <b className="text-coral">O render parou antes de terminar.</b>
          <pre className="max-h-32 w-full overflow-auto whitespace-pre-wrap text-xs text-navy/70">
            {job.error}
          </pre>
          <p className="text-xs text-navy/60">
            As cenas já renderizadas foram salvas. Retome que ele continua de
            onde parou.
          </p>
          <button
            onClick={resume}
            disabled={busy}
            className="btn-sticker bg-navy px-8 py-3 font-black text-white active:btn-sticker-active disabled:opacity-50"
          >
            ↻ Retomar de onde parou
          </button>
        </div>
      )}

      {done && (
        <div className="flex w-full max-w-sm flex-col items-center gap-4">
          <p className="rounded-lg bg-coral/15 px-3 py-2 text-center text-xs font-bold text-navy">
            ⬇️ Baixe agora — no plano grátis o arquivo some se o servidor
            reiniciar.
          </p>
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
