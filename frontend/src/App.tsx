import { useEffect } from 'react'
import { useStore } from './store'
import { Stepper } from './components/Stepper'
import { Toaster } from './components/Toaster'
import { StepUpload } from './components/steps/StepUpload'
import { StepConfigure } from './components/steps/StepConfigure'
import { StepPreview } from './components/steps/StepPreview'
import { StepGenerate } from './components/steps/StepGenerate'

export default function App() {
  const init = useStore((s) => s.init)
  const step = useStore((s) => s.step)
  const waking = useStore((s) => s.waking)
  const wakeSeconds = useStore((s) => s.wakeSeconds)

  useEffect(() => {
    init()
  }, [init])

  if (waking) {
    return (
      <div className="flex min-h-full flex-col items-center justify-center gap-4 px-6 text-center">
        <span className="text-5xl">🏭</span>
        <h1 className="text-2xl font-black text-navy">Short Factory</h1>
        <div className="card-sticker bg-mustard/20 px-6 py-5">
          <p className="text-lg font-black text-navy">⏳ Acordando o servidor…</p>
          <p className="mt-1 text-sm font-medium text-navy/60">
            No plano grátis o servidor hiberna e leva até ~1 min pra acordar.
            {wakeSeconds > 0 && ` (${wakeSeconds}s)`}
          </p>
          <div className="mt-3 h-2 w-56 overflow-hidden rounded-full bg-navy/10">
            <div className="h-full w-1/3 animate-pulse rounded-full bg-teal" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto flex min-h-full max-w-5xl flex-col px-4 py-6">
      <header className="mb-6 flex flex-col items-center gap-3 text-center">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl border-[3px] border-navy bg-navy text-2xl">
            🏭
          </span>
          <h1 className="text-3xl font-black tracking-tight text-navy">
            Short Factory
          </h1>
        </div>
        <p className="max-w-lg text-sm font-medium text-navy/60">
          Traga sua voz, suas imagens e seu roteiro. A fábrica monta o Short
          vertical com sincronização, zoom, hook, CTA, legendas e SFX.
        </p>
      </header>

      {/* Aviso de persistência (item 3): free tier tem disco efêmero. */}
      <div className="mb-4 rounded-xl border-2 border-navy/15 bg-mustard/15 px-4 py-2 text-center text-xs font-semibold text-navy/70">
        ⚠️ Versão demo: seus projetos e uploads duram só esta sessão. Baixe o MP4
        <b> logo após gerar</b> — no plano grátis o arquivo é temporário.
      </div>

      <div className="mb-8">
        <Stepper />
      </div>

      <main className="flex-1">
        {step === 0 && <StepUpload />}
        {step === 1 && <StepConfigure />}
        {step === 2 && <StepPreview />}
        {step === 3 && <StepGenerate />}
      </main>

      <footer className="mt-8 text-center text-xs font-medium text-navy/40">
        P0 · dogfood · made with Short Factory
      </footer>

      <Toaster />
    </div>
  )
}
