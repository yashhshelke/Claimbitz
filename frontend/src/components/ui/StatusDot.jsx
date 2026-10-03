import React from 'react'

/**
 * StatusDot — small colored indicator, optionally pulsing while active.
 * variants: success | warning | error | info | neutral
 */
const COLORS = {
  success: 'bg-success',
  warning: 'bg-warning',
  error: 'bg-error',
  info: 'bg-brand',
  neutral: 'bg-muted',
}

export default function StatusDot({ variant = 'neutral', pulse = false, className = '' }) {
  return (
    <span className={`relative inline-flex h-2 w-2 ${className}`}>
      {pulse && (
        <span
          className={`absolute inline-flex h-full w-full rounded-full opacity-60 ${COLORS[variant]} motion-safe:animate-ping`}
        />
      )}
      <span className={`relative inline-flex h-2 w-2 rounded-full ${COLORS[variant]}`} />
    </span>
  )
}
