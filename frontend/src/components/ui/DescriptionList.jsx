import React from 'react'

/**
 * DescriptionList — key/value pairs for claim fields and summaries.
 *
 * items: Array<{ label: string, value: React.ReactNode }>
 * columns: 1 | 2  (responsive grid on >= sm)
 */
export default function DescriptionList({ items = [], columns = 1, className = '' }) {
  const gridCols = columns === 2 ? 'sm:grid-cols-2' : 'grid-cols-1'
  return (
    <dl className={`grid ${gridCols} gap-x-6 ${className}`}>
      {items.map((item, i) => (
        <div
          key={item.label ?? i}
          className="flex items-center justify-between gap-4 border-b border-default py-2.5 last:border-0"
        >
          <dt className="text-sm text-muted-foreground">{item.label}</dt>
          <dd className="text-sm font-medium text-foreground text-right break-words">{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}
