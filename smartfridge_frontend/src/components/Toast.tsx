type ToastProps = {
  toast: { message: string; tone: 'success' | 'error' } | null
}

function Toast({ toast }: ToastProps) {
  if (!toast) return null

  return (
    <div className="toast-stack" role="status" aria-live="polite">
      <div className={`toast ${toast.tone}`}>
        <span className="toast-dot" aria-hidden="true" />
        <span>{toast.message}</span>
      </div>
    </div>
  )
}

export default Toast
