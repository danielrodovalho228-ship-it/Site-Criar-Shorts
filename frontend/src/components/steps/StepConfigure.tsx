import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  arrayMove,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useStore } from '../../store'
import { api } from '../../api/client'
import { IMAGE_EFFECTS, type CaptionStyle } from '../../types'

const MAX_IMAGE_SECONDS = 5.0

function onScreenDurations(starts: number[], total: number): number[] {
  return starts.map((s, i) => (i + 1 < starts.length ? starts[i + 1] : total) - s)
}

function SortableRow({
  file,
  index,
}: {
  file: string
  index: number
}) {
  const project = useStore((s) => s.project)!
  const patchConfig = useStore((s) => s.patchConfig)
  const img = project.config.images[index]
  const total = project.config.audio.duration
  const durs = onScreenDurations(
    project.config.images.map((i) => i.start),
    total,
  )
  const dur = durs[index]
  const tooLong = dur > MAX_IMAGE_SECONDS
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: file })

  return (
    <tr
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={`border-b-2 border-navy/10 ${isDragging ? 'bg-mustard/20' : ''}`}
    >
      <td className="py-2">
        <button
          {...attributes}
          {...listeners}
          className="cursor-grab px-1 text-lg text-navy/40"
          aria-label="Reordenar"
        >
          ⠿
        </button>
      </td>
      <td>
        <img
          src={api.uploadUrl(project.id, file)}
          alt={file}
          className="h-16 w-9 rounded border-2 border-navy object-cover"
        />
      </td>
      <td className="max-w-[120px] truncate px-2 text-xs font-semibold text-navy/70">
        {file}
      </td>
      <td className="px-2">
        <input
          type="number"
          step="0.1"
          value={img.start}
          onChange={(e) =>
            patchConfig((c) => {
              c.images[index].start = parseFloat(e.target.value) || 0
            })
          }
          className="w-20 rounded-lg border-2 border-navy px-2 py-1 text-sm font-semibold"
        />
      </td>
      <td className="px-2">
        <select
          value={img.effect}
          onChange={(e) =>
            patchConfig((c) => {
              c.images[index].effect = e.target.value as (typeof IMAGE_EFFECTS)[number]
            })
          }
          className="rounded-lg border-2 border-navy px-2 py-1 text-sm font-semibold"
        >
          {IMAGE_EFFECTS.map((eff) => (
            <option key={eff} value={eff}>
              {eff}
            </option>
          ))}
        </select>
      </td>
      <td className="px-2">
        <span
          className={`text-xs font-bold ${tooLong ? 'text-coral' : 'text-teal'}`}
          title={tooLong ? 'Imagem parada demais (> 5s)' : ''}
        >
          {dur > 0 ? `${dur.toFixed(1)}s` : '—'} {tooLong && '⚠️'}
        </span>
      </td>
    </tr>
  )
}

export function StepConfigure() {
  const project = useStore((s) => s.project)!
  const musicLib = useStore((s) => s.musicLib)
  const sfxLib = useStore((s) => s.sfxLib)
  const patchConfig = useStore((s) => s.patchConfig)
  const setImages = useStore((s) => s.setImages)
  const autoTimingByName = useStore((s) => s.autoTimingByName)
  const distributeEvenly = useStore((s) => s.distributeEvenly)
  const autotimeNarration = useStore((s) => s.autotimeNarration)
  const busy = useStore((s) => s.busy)
  const setStep = useStore((s) => s.setStep)
  const saveConfig = useStore((s) => s.saveConfig)
  const cfg = project.config
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }))

  const total = cfg.audio.duration
  const durs = onScreenDurations(cfg.images.map((i) => i.start), total)
  const longCount = durs.filter((d) => d > MAX_IMAGE_SECONDS).length
  const lastStart = cfg.images.length ? cfg.images[cfg.images.length - 1].start : 0
  const covered = cfg.images.length > 0 && lastStart < total
  const increasing = cfg.images.every(
    (im, i) => i === 0 || im.start > cfg.images[i - 1].start,
  )

  const onDragEnd = (e: DragEndEvent) => {
    const { active, over } = e
    if (!over || active.id === over.id) return
    const oldIdx = cfg.images.findIndex((i) => i.file === active.id)
    const newIdx = cfg.images.findIndex((i) => i.file === over.id)
    setImages(arrayMove(cfg.images, oldIdx, newIdx))
  }

  return (
    <section className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
      {/* LEFT: image table */}
      <div className="card-sticker flex flex-col p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-black text-navy">Cenas ({cfg.images.length})</h2>
          <div className="flex gap-2">
            <button
              onClick={autoTimingByName}
              className="btn-sticker bg-mustard px-3 py-1.5 text-xs font-bold text-navy active:btn-sticker-active"
            >
              Auto-timing (M_SS)
            </button>
            <button
              onClick={distributeEvenly}
              className="btn-sticker bg-teal px-3 py-1.5 text-xs font-bold text-white active:btn-sticker-active"
            >
              Distribuir
            </button>
            <button
              onClick={autotimeNarration}
              disabled={busy}
              title="Distribui as cenas nas pausas da narração (precisa transcrever antes)"
              className="btn-sticker bg-coral px-3 py-1.5 text-xs font-bold text-white active:btn-sticker-active disabled:opacity-50"
            >
              ✨ Auto-timing (narração)
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-[11px] uppercase tracking-wide text-navy/40">
                <th></th>
                <th>Img</th>
                <th className="px-2">Nome</th>
                <th className="px-2">Início (s)</th>
                <th className="px-2">Efeito</th>
                <th className="px-2">Tela</th>
              </tr>
            </thead>
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
              <SortableContext
                items={cfg.images.map((i) => i.file)}
                strategy={verticalListSortingStrategy}
              >
                <tbody>
                  {cfg.images.map((img, i) => (
                    <SortableRow key={img.file} file={img.file} index={i} />
                  ))}
                </tbody>
              </SortableContext>
            </DndContext>
          </table>
        </div>
      </div>

      {/* RIGHT: side panel */}
      <div className="flex flex-col gap-4">
        {/* HOOK */}
        <div className="card-sticker p-4">
          <h3 className="mb-2 font-black text-navy">Hook</h3>
          <textarea
            value={cfg.hook.text}
            onChange={(e) => patchConfig((c) => void (c.hook.text = e.target.value))}
            placeholder="Linha 1 | Linha 2"
            rows={2}
            className="w-full rounded-lg border-2 border-navy px-2 py-1 text-sm font-semibold"
          />
          <label className="mt-2 flex items-center gap-2 text-xs font-bold text-navy/60">
            Duração (s)
            <input
              type="number"
              step="0.5"
              value={cfg.hook.duration}
              onChange={(e) =>
                patchConfig((c) => void (c.hook.duration = parseFloat(e.target.value) || 0))
              }
              className="w-20 rounded-lg border-2 border-navy px-2 py-1"
            />
          </label>
        </div>

        {/* CTA */}
        <div className="card-sticker p-4">
          <h3 className="mb-2 font-black text-navy">CTA</h3>
          <input
            value={cfg.cta.text}
            onChange={(e) => patchConfig((c) => void (c.cta.text = e.target.value))}
            placeholder="FULL BREAKDOWN -> @canal"
            className="w-full rounded-lg border-2 border-navy px-2 py-1 text-sm font-semibold"
          />
          <div className="mt-2 flex gap-2 text-xs font-bold text-navy/60">
            <label className="flex items-center gap-1">
              início
              <input
                type="number"
                step="0.1"
                value={cfg.cta.start}
                onChange={(e) =>
                  patchConfig((c) => void (c.cta.start = parseFloat(e.target.value) || 0))
                }
                className="w-16 rounded-lg border-2 border-navy px-2 py-1"
              />
            </label>
            <label className="flex items-center gap-1">
              fim
              <input
                type="number"
                step="0.1"
                value={cfg.cta.end}
                onChange={(e) =>
                  patchConfig((c) => void (c.cta.end = parseFloat(e.target.value) || 0))
                }
                className="w-16 rounded-lg border-2 border-navy px-2 py-1"
              />
            </label>
          </div>
        </div>

        {/* MUSIC */}
        <div className="card-sticker p-4">
          <h3 className="mb-2 font-black text-navy">Música</h3>
          <select
            value={cfg.music.file ?? ''}
            onChange={(e) =>
              patchConfig((c) => void (c.music.file = e.target.value || null))
            }
            className="w-full rounded-lg border-2 border-navy px-2 py-1 text-sm font-semibold"
          >
            <option value="">— sem música —</option>
            {musicLib.map((m) => (
              <option key={m.file} value={m.file}>
                {m.name}
              </option>
            ))}
          </select>
          <label className="mt-2 flex items-center gap-2 text-xs font-bold text-navy/60">
            Volume {Math.round(cfg.music.volume * 100)}%
            <input
              type="range"
              min={0}
              max={1}
              step={0.02}
              value={cfg.music.volume}
              onChange={(e) =>
                patchConfig((c) => void (c.music.volume = parseFloat(e.target.value)))
              }
              className="flex-1 accent-teal"
            />
          </label>
          {musicLib.length === 0 && (
            <p className="mt-1 text-[11px] text-navy/40">
              Biblioteca vazia (adicione em storage/assets/music).
            </p>
          )}
        </div>

        {/* SFX */}
        <div className="card-sticker p-4">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="font-black text-navy">SFX</h3>
            <button
              onClick={() =>
                patchConfig((c) =>
                  c.sfx.push({ file: sfxLib[0]?.file ?? '', time: 0, volume: 1 }),
                )
              }
              className="btn-sticker bg-navy px-2 py-1 text-xs font-bold text-white active:btn-sticker-active"
            >
              + som
            </button>
          </div>
          <div className="flex flex-col gap-2">
            {cfg.sfx.map((s, i) => (
              <div key={i} className="flex items-center gap-1">
                <select
                  value={s.file}
                  onChange={(e) =>
                    patchConfig((c) => void (c.sfx[i].file = e.target.value))
                  }
                  className="min-w-0 flex-1 rounded-lg border-2 border-navy px-1 py-1 text-xs font-semibold"
                >
                  {sfxLib.map((a) => (
                    <option key={a.file} value={a.file}>
                      {a.name}
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  step="0.1"
                  value={s.time}
                  title="tempo (s)"
                  onChange={(e) =>
                    patchConfig((c) => void (c.sfx[i].time = parseFloat(e.target.value) || 0))
                  }
                  className="w-14 rounded-lg border-2 border-navy px-1 py-1 text-xs"
                />
                <button
                  onClick={() => patchConfig((c) => void c.sfx.splice(i, 1))}
                  className="text-coral"
                  aria-label="Remover"
                >
                  ×
                </button>
              </div>
            ))}
            {cfg.sfx.length === 0 && (
              <p className="text-[11px] text-navy/40">Nenhum SFX.</p>
            )}
          </div>
        </div>

        {/* LEGENDAS */}
        <div className="card-sticker p-4">
          <h3 className="mb-2 font-black text-navy">Legendas</h3>
          <select
            value={cfg.caption_style}
            onChange={(e) =>
              patchConfig((c) => void (c.caption_style = e.target.value as CaptionStyle))
            }
            className="w-full rounded-lg border-2 border-navy px-2 py-1 text-sm font-semibold"
          >
            <option value="navy-white">Navy / branco (The Chapter)</option>
            <option value="white-black">Branco / preto (clássico)</option>
            <option value="yellow-pop">Amarelo pop (MrBeast)</option>
            <option value="karaoke">Karaokê</option>
          </select>
          <p className="mt-2 text-xs font-bold text-navy/60">Correções (caption_fixes)</p>
          {Object.entries(cfg.caption_fixes).map(([k, v], i) => (
            <div key={i} className="mt-1 flex items-center gap-1 text-xs">
              <input
                value={k}
                onChange={(e) =>
                  patchConfig((c) => {
                    const entries = Object.entries(c.caption_fixes)
                    entries[i] = [e.target.value, v]
                    c.caption_fixes = Object.fromEntries(entries)
                  })
                }
                className="min-w-0 flex-1 rounded border-2 border-navy px-1 py-1"
                placeholder="errado"
              />
              <span>→</span>
              <input
                value={v}
                onChange={(e) =>
                  patchConfig((c) => void (c.caption_fixes[k] = e.target.value))
                }
                className="min-w-0 flex-1 rounded border-2 border-navy px-1 py-1"
                placeholder="certo"
              />
              <button
                onClick={() =>
                  patchConfig((c) => {
                    delete c.caption_fixes[k]
                  })
                }
                className="text-coral"
                aria-label="Remover"
              >
                ×
              </button>
            </div>
          ))}
          <button
            onClick={() => patchConfig((c) => void (c.caption_fixes[''] = ''))}
            className="mt-2 text-xs font-bold text-teal"
          >
            + correção
          </button>
        </div>
      </div>

      {/* COVERAGE BAR (full width) */}
      <div
        className={`card-sticker col-span-full flex flex-wrap items-center justify-between gap-3 p-4 ${
          covered && increasing && longCount === 0 ? 'bg-teal/10' : 'bg-coral/10'
        }`}
      >
        <div className="text-sm font-bold text-navy">
          Áudio: {total.toFixed(1)}s · Última cena começa em {lastStart.toFixed(1)}s
        </div>
        <div className="flex flex-wrap gap-3 text-xs font-bold">
          <span className={covered ? 'text-teal' : 'text-coral'}>
            {covered ? '✓ cobre o áudio' : '⚠️ última cena além do áudio'}
          </span>
          <span className={increasing ? 'text-teal' : 'text-coral'}>
            {increasing ? '✓ tempos crescentes' : '⚠️ tempos fora de ordem'}
          </span>
          <span className={longCount === 0 ? 'text-teal' : 'text-coral'}>
            {longCount === 0
              ? '✓ nenhuma cena > 5s'
              : `⚠️ ${longCount} cena(s) > 5s`}
          </span>
        </div>
      </div>

      <div className="col-span-full flex justify-between">
        <button
          onClick={() => setStep(0)}
          className="btn-sticker bg-white px-5 py-3 font-black text-navy active:btn-sticker-active"
        >
          ← Voltar
        </button>
        <button
          onClick={async () => {
            await saveConfig()
            setStep(2)
          }}
          className="btn-sticker bg-navy px-6 py-3 font-black text-white active:btn-sticker-active"
        >
          Preview →
        </button>
      </div>
    </section>
  )
}
