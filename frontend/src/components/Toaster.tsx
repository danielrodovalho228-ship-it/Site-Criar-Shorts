import { useStore } from '../store'

const STYLES: Record<string, string> = {
  error: 'bg-coral text-white',
  success: 'bg-teal text-white',
  info: 'bg-mustard text-navy',
}

export function Toaster() {
  const toasts = useStore((s) => s.toasts)
  const dismiss = useStore((s) => s.dismissToast)
  return (
    <div className="fixed bottom-5 right-5 z-50 flex w-80 flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`card-sticker flex items-start justify-between gap-3 px-4 py-3 text-sm font-semibold ${STYLES[t.kind]}`}
          role="status"
        >
          <span className="whitespace-pre-wrap break-words">{t.msg}</span>
          <button
            onClick={() => dismiss(t.id)}
            className="shrink-0 text-lg leading-none opacity-80 hover:opacity-100"
            aria-label="Fechar"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
