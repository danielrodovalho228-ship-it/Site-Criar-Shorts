import { useStore } from '../../store'
import { api } from '../../api/client'

const MAX_IMAGE_SECONDS = 5.0

export function StepPreview() {
  const project = useStore((s) => s.project)!
  const setStep = useStore((s) => s.setStep)
  const cfg = project.config
  const total = cfg.audio.duration || 1

  const pct = (t: number) => `${Math.max(0, Math.min(100, (t / total) * 100))}%`

  // warnings
  const warnings: string[] = []
  cfg.images.forEach((img, i) => {
    const end = i + 1 < cfg.images.length ? cfg.images[i + 1].start : total
    const dur = end - img.start
    if (dur > MAX_IMAGE_SECONDS)
      warnings.push(`Imagem "${img.file}" fica ${dur.toFixed(1)}s na tela (> 5s).`)
    if (dur < 0)
      warnings.push(`Imagem "${img.file}" começa depois da próxima — reordene.`)
  })
  if (cfg.images.length && cfg.images[cfg.images.length - 1].start >= total)
    warnings.push('A última cena começa depois do fim do áudio.')
  if (cfg.cta.text && cfg.cta.end > total)
    warnings.push('O CTA termina depois do fim do áudio.')
  if (cfg.cta.text && cfg.cta.end <= cfg.cta.start)
    warnings.push('A janela do CTA é inválida (fim ≤ início).')

  return (
    <section className="flex flex-col gap-5">
      <div className="card-sticker p-4">
        <h2 className="mb-3 text-lg font-black text-navy">Linha do tempo · {total.toFixed(1)}s</h2>

        {/* image track */}
        <div className="relative h-24 w-full overflow-hidden rounded-lg border-2 border-navy bg-navy/5">
          {cfg.images.map((img, i) => {
            const end = i + 1 < cfg.images.length ? cfg.images[i + 1].start : total
            const left = pct(img.start)
            const width = `${Math.max(0, ((end - img.start) / total) * 100)}%`
            return (
              <div
                key={img.file}
                className="absolute top-0 h-full border-r border-white/60"
                style={{ left, width }}
                title={`${img.file} · ${img.start.toFixed(1)}–${end.toFixed(1)}s`}
              >
                <img
                  src={api.uploadUrl(project.id, img.file)}
                  alt={img.file}
                  className="h-full w-full object-cover opacity-90"
                />
              </div>
            )
          })}
        </div>

        {/* marker track */}
        <div className="relative mt-2 h-8 w-full rounded bg-navy/5">
          {/* hook */}
          {cfg.hook.text && (
            <div
              className="absolute top-0 flex h-full items-center justify-center rounded bg-mustard text-[10px] font-bold text-navy"
              style={{ left: 0, width: pct(cfg.hook.duration) }}
              title="Hook"
            >
              HOOK
            </div>
          )}
          {/* cta */}
          {cfg.cta.text && cfg.cta.end > cfg.cta.start && (
            <div
              className="absolute top-0 flex h-full items-center justify-center rounded bg-coral text-[10px] font-bold text-white"
              style={{
                left: pct(cfg.cta.start),
                width: `${((cfg.cta.end - cfg.cta.start) / total) * 100}%`,
              }}
              title="CTA"
            >
              CTA
            </div>
          )}
          {/* sfx ticks */}
          {cfg.sfx.map((s, i) => (
            <div
              key={i}
              className="absolute top-0 h-full w-[3px] bg-teal"
              style={{ left: pct(s.time) }}
              title={`SFX ${s.file} @ ${s.time}s`}
            />
          ))}
        </div>
        <div className="mt-1 flex justify-between text-[10px] font-bold text-navy/40">
          <span>0s</span>
          <span>{total.toFixed(1)}s</span>
        </div>

        <div className="mt-3 flex gap-4 text-[11px] font-bold">
          <span className="flex items-center gap-1">
            <span className="h-3 w-3 rounded bg-mustard" /> Hook
          </span>
          <span className="flex items-center gap-1">
            <span className="h-3 w-3 rounded bg-coral" /> CTA
          </span>
          <span className="flex items-center gap-1">
            <span className="h-3 w-3 rounded bg-teal" /> SFX
          </span>
        </div>
      </div>

      {/* warnings */}
      <div className={`card-sticker p-4 ${warnings.length ? 'bg-coral/10' : 'bg-teal/10'}`}>
        <h3 className="mb-2 font-black text-navy">
          {warnings.length ? `⚠️ ${warnings.length} aviso(s)` : '✓ Tudo certo'}
        </h3>
        {warnings.length > 0 ? (
          <ul className="list-inside list-disc space-y-1 text-sm font-medium text-navy/70">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm font-medium text-navy/60">
            Nenhum problema detectado. Pronto para gerar.
          </p>
        )}
      </div>

      <div className="flex justify-between">
        <button
          onClick={() => setStep(1)}
          className="btn-sticker bg-white px-5 py-3 font-black text-navy active:btn-sticker-active"
        >
          ← Voltar
        </button>
        <button
          onClick={() => setStep(3)}
          className="btn-sticker bg-navy px-6 py-3 font-black text-white active:btn-sticker-active"
        >
          Gerar →
        </button>
      </div>
    </section>
  )
}
