import React from 'react'

/**
 * SectionHeader — consistent panel/section title block.
 * Optional leading icon (lucide component) and trailing actions.
 */
export default function SectionHeader({
  icon: Icon,
  title,
  description,
  actions,
  className = '',
}) {
  return (
    <div className={`flex items-start justify-between gap-4 ${className}`}>
      <div className="flex items-start gap-3 min-w-0">
        {Icon && (
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-brand-subtle">
            <Icon className="h-[18px] w-[18px] text-brand" />
          </div>
        )}
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-foreground leading-tight truncate">{title}</h2>
          {description && <p className="mt-0.5 text-sm text-muted-foreground">{description}</p>}
        </div>
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  )
}
