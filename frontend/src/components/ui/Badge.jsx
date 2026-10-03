import React from 'react'

/**
 * Badge — compact status/label pill.
 * variants: success | warning | error | info | neutral | brand
 */
const VARIANTS = {
  success: 'bg-success-subtle text-success',
  warning: 'bg-warning-subtle text-warning',
  error: 'bg-error-subtle text-error',
  info: 'bg-info-subtle text-info',
  brand: 'bg-brand-subtle text-brand',
  neutral: 'bg-subtle text-muted-foreground',
}

export default function Badge({ variant = 'neutral', className = '', children, ...props }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5
        text-xs font-semibold ${VARIANTS[variant]} ${className}`}
      {...props}
    >
      {children}
    </span>
  )
}
