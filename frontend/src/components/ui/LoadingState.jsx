import React from 'react'
import { Loader2 } from 'lucide-react'

/**
 * LoadingState — consistent inline/block loading indicator.
 * Also exports a bare <Spinner /> for use inside buttons etc.
 */
export function Spinner({ className = '' }) {
  return <Loader2 className={`animate-spin ${className}`} />
}

export default function LoadingState({ label = 'Loading…', className = '' }) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 px-6 py-10 text-center ${className}`}>
      <Spinner className="h-6 w-6 text-brand" />
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  )
}
