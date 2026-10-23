export function ApiBanner({ message, onRetry, onDismiss }: { message: string; onRetry: () => void; onDismiss: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
      <span>{message}</span>
      <span className="flex gap-2">
        <button onClick={onRetry} className="rounded-md bg-red-400/20 px-3 py-1 font-medium hover:bg-red-400/30">
          Retry
        </button>
        <button onClick={onDismiss} className="rounded-md px-2 py-1 text-red-200/70 hover:text-red-100" aria-label="Dismiss">
          ✕
        </button>
      </span>
    </div>
  );
}
