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
        <h1 className="font-display text-3xl font-bold tracking-tight text-navy">
          Short Factor<span className="text-coral">y</span>
        </h1>
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
      <header className="mb-7 flex flex-col items-center gap-4 text-center">
        <h1 className="font-display text-3xl font-bold tracking-tight text-navy">
          Short Factor<span className="text-coral">y</span>
        </h1>
        {step === 0 && (
          <div className="flex flex-col items-center gap-2">
            <p className="font-display text-2xl font-bold leading-tight text-navy sm:text-3xl">
              O short é seu. A edição é nossa.
            </p>
            <p className="max-w-md text-sm font-medium text-navy/55">
              Sobe voz, imagens e roteiro — sai o vídeo montado, sincronizado e
              legendado.
            </p>
          </div>
        )}
      </header>

      <div className="mb-8">
        <Stepper />
      </div>

      <main className="flex-1">
        {step === 0 && <StepUpload />}
        {step === 1 && <StepConfigure />}
        {step === 2 && <StepPreview />}
        {step === 3 && <StepGenerate />}
      </main>

      <footer className="mt-10 text-center text-sm text-gray-400">
        Demo — projetos duram a sessão · baixe o MP4 ao gerar
      </footer>

      <Toaster />
    </div>
  )
}
