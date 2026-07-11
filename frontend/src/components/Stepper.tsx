import { useStore } from '../store'

const STEPS = ['Upload', 'Configurar', 'Preview', 'Gerar']

export function Stepper() {
  const step = useStore((s) => s.step)
  const project = useStore((s) => s.project)
  const setStep = useStore((s) => s.setStep)

  return (
    <nav className="flex items-center justify-center gap-2 sm:gap-4">
      {STEPS.map((label, i) => {
        const done = i < step
        const active = i === step
        // can't jump ahead of where the project allows
        const reachable = i === 0 || !!project
        return (
          <div key={label} className="flex items-center gap-2 sm:gap-4">
            <button
              disabled={!reachable}
              onClick={() => reachable && setStep(i)}
              className={[
                'flex items-center gap-2 rounded-xl border-[3px] border-navy px-3 py-2 text-sm font-bold transition',
                active
                  ? 'bg-navy text-white shadow-[3px_3px_0_0_#E9C46A]'
                  : done
                    ? 'bg-teal text-white'
                    : 'bg-white text-navy',
                reachable ? 'cursor-pointer' : 'cursor-not-allowed opacity-40',
              ].join(' ')}
            >
              <span
                className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                  active ? 'bg-mustard text-navy' : done ? 'bg-white text-teal' : 'bg-navy text-white'
                }`}
              >
                {done ? '✓' : i + 1}
              </span>
              <span className="hidden sm:inline">{label}</span>
            </button>
            {i < STEPS.length - 1 && <span className="h-1 w-4 rounded bg-navy/30 sm:w-8" />}
          </div>
        )
      })}
    </nav>
  )
}
