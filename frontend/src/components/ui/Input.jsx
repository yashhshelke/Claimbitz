import React, { useId } from 'react'

/**
 * Input — labelled text field.
 */
export default function Input({ label, id, hint, className = '', containerClassName = '', ...props }) {
  const autoId = useId()
  const inputId = id || autoId
  return (
    <div className={containerClassName}>
      {label && (
        <label htmlFor={inputId} className="mb-1 block text-xs font-medium text-muted-foreground">
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={`h-10 w-full rounded-md border border-default bg-surface px-3 text-sm text-foreground
          placeholder:text-subtle-foreground transition-colors
          focus:border-brand focus:outline-none focus-visible:outline-none
          disabled:bg-subtle disabled:text-muted-foreground ${className}`}
        {...props}
      />
      {hint && <p className="mt-1 text-xs text-subtle-foreground">{hint}</p>}
    </div>
  )
}
