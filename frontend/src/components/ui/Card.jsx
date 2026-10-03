import React from 'react'

/**
 * Card — neutral surface container.
 *
 * variants:
 *   default     — surface + subtle border
 *   elevated    — surface + border + md shadow
 *   interactive — default + hover border/shadow (for clickable cards)
 */
const VARIANTS = {
  default: 'bg-surface border border-default',
  elevated: 'bg-surface border border-default shadow-[0_4px_12px_rgba(16,24,40,0.08)]',
  interactive:
    'bg-surface border border-default transition-all duration-150 hover:border-brand/40 hover:shadow-[0_4px_12px_rgba(16,24,40,0.08)]',
}

export default function Card({ variant = 'default', className = '', children, ...props }) {
  return (
    <div className={`rounded-lg ${VARIANTS[variant]} ${className}`} {...props}>
      {children}
    </div>
  )
}
