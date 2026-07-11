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

  useEffect(() => {
    init()
  }, [init])

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
