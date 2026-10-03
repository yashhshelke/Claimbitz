import React from 'react'
import { AlertTriangle, X } from 'lucide-react'

/**
 * ErrorState — surfaces an error clearly.
 *
 * Use `inline` for a compact banner (e.g. above a form) or the default
 * block layout for full-panel errors. Optional onDismiss shows a close button.
 */
export default function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
  onDismiss,
  inline = false,
  className = '',
}) {
  if (inline) {
    return (
      <div
        role="alert"
        className={`flex items-start gap-3 rounded-md border border-error/30 bg-error-subtle px-4 py-3 ${className}`}
      >
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-error" />
        <div className="min-w-0 flex-1">
          {title && <p className="text-sm font-semibold text-error">{title}</p>}
          {message && <p className="mt-0.5 text-sm text-error/90 break-words">{message}</p>}
        </div>
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss error"
            className="rounded-sm p-0.5 text-error/70 hover:text-error transition-colors cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    )
  }

  return (
    <div role="alert" className={`flex flex-col items-center justify-center px-6 py-10 text-center ${className}`}>
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-error-subtle">
        <AlertTriangle className="h-6 w-6 text-error" />
      </div>
      <h3 className="text-base font-semibold text-foreground">{title}</h3>
      {message && <p className="mt-1 max-w-sm text-sm text-muted-foreground break-words">{message}</p>}
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-5 inline-flex h-10 items-center rounded-md bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-hover transition-colors cursor-pointer"
        >
          Try again
        </button>
      )}
    </div>
  )
}
