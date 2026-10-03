import React from 'react'

/**
 * Button — the single source of truth for actions across ClaimBitz.
 *
 * variants: primary | secondary | ghost | danger
 * sizes:    sm | md | lg
 */
const VARIANTS = {
  primary:
    'bg-brand text-white border border-transparent hover:bg-brand-hover active:bg-brand-pressed disabled:bg-brand/50',
  secondary:
    'bg-surface text-foreground border border-default hover:bg-subtle active:bg-subtle disabled:opacity-50',
  ghost:
    'bg-transparent text-muted-foreground border border-transparent hover:bg-subtle hover:text-foreground active:bg-subtle disabled:opacity-50',
  danger:
    'bg-error text-white border border-transparent hover:brightness-95 active:brightness-90 disabled:opacity-50',
}

const SIZES = {
  sm: 'text-sm h-8 px-3 gap-1.5 rounded-md',
  md: 'text-sm h-10 px-4 gap-2 rounded-md',
  lg: 'text-base h-12 px-6 gap-2.5 rounded-md',
}

export default function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  type = 'button',
  disabled = false,
  children,
  ...props
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      className={`inline-flex items-center justify-center font-semibold whitespace-nowrap
        transition-colors duration-150 cursor-pointer disabled:cursor-not-allowed
        ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
