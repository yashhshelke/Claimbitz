import React from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, Check } from 'lucide-react'
import { cn } from '../../lib/utils'

/**
 * Presentation-only connected agent timeline.
 *
 * `agents` is REQUIRED and supplied by the caller — on /dashboard it comes from
 * the real useClaimAgent state; on the landing page it comes from marketing demo
 * data. This component never owns or fabricates agent data.
 *
 * Each agent: { name, activity?, seconds? }
 * activeIndex: index currently processing (== agents.length when all complete)
 * failedIndex: index that failed (-1 when none)
 */
export function statusFor(index, activeIndex, failedIndex) {
  if (failedIndex >= 0) {
    if (index < failedIndex) return 'completed'
    if (index === failedIndex) return 'failed'
    return 'pending'
  }
  if (index < activeIndex) return 'completed'
  if (index === activeIndex) return 'processing'
  return 'pending'
}

export function AgentTimeline({
  agents,
  activeIndex,
  failedIndex = -1,
  compact = false,
  progress = 0,
}) {
  const list = agents || []

  return (
    <ol className="relative">
      {list.map((agent, i) => {
        const status = statusFor(i, activeIndex, failedIndex)
        const isLast = i === list.length - 1
        const nextDone = statusFor(i + 1, activeIndex, failedIndex) !== 'pending' || status === 'completed'
        return (
          <li key={agent.name || i} className="relative flex gap-3">
            {!isLast && (
              <span className="absolute left-[10px] top-[26px] bottom-[-2px] w-px bg-border" aria-hidden>
                <motion.span
                  className="absolute inset-x-0 top-0 block bg-primary/70 origin-top"
                  style={{ height: '100%' }}
                  initial={false}
                  animate={{ scaleY: status === 'completed' && nextDone ? 1 : 0 }}
                  transition={{ duration: 0.45, ease: 'easeOut' }}
                />
              </span>
            )}

            <span className="relative mt-[7px] flex h-[21px] w-[21px] shrink-0 items-center justify-center">
              {status === 'processing' && (
                <motion.span
                  className="absolute inset-0 rounded-full bg-primary/20"
                  animate={{ scale: [1, 1.45, 1], opacity: [0.5, 0, 0.5] }}
                  transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
                />
              )}
              <span
                className={cn(
                  'relative flex h-[17px] w-[17px] items-center justify-center rounded-full border bg-surface transition-colors duration-300',
                  status === 'completed' && 'border-success/40 bg-success-subtle',
                  status === 'processing' && 'border-primary bg-primary',
                  status === 'pending' && 'border-border-strong',
                  status === 'failed' && 'border-destructive bg-destructive',
                )}
              >
                <AnimatePresence initial={false}>
                  {status === 'completed' && (
                    <motion.span
                      key="c"
                      initial={{ scale: 0.3, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ type: 'spring', stiffness: 500, damping: 26 }}
                    >
                      <Check className="h-2.5 w-2.5 text-success" strokeWidth={3} />
                    </motion.span>
                  )}
                </AnimatePresence>
                {status === 'processing' && <span className="h-1.5 w-1.5 rounded-full bg-primary-foreground" />}
                {status === 'failed' && <AlertTriangle className="h-2.5 w-2.5 text-destructive-foreground" />}
              </span>
            </span>

            <div
              className={cn(
                'min-w-0 flex-1 rounded-md px-2.5 transition-colors duration-300',
                status === 'processing' ? 'my-1 bg-primary-subtle py-2' : 'py-[7px]',
                status === 'failed' && 'my-1 bg-destructive/10 py-2',
              )}
            >
              <div className="flex items-baseline justify-between gap-3">
                <p
                  className={cn(
                    'truncate',
                    status === 'processing' && 'text-[14px] font-semibold text-foreground',
                    status === 'completed' && 'text-[13px] font-medium text-muted-foreground',
                    status === 'pending' && 'text-[13px] font-medium text-subtle-foreground',
                    status === 'failed' && 'text-[14px] font-semibold text-destructive',
                  )}
                >
                  {agent.name}
                </p>
                {status === 'completed' && typeof agent.seconds === 'number' && (
                  <span className="shrink-0 text-[11.5px] tabular-nums text-subtle-foreground">
                    {agent.seconds.toFixed(1)}s
                  </span>
                )}
                {status === 'processing' && (
                  <span className="shrink-0 text-[11px] font-semibold uppercase tracking-wide text-accent-foreground">
                    Active
                  </span>
                )}
              </div>
              <AnimatePresence initial={false}>
                {(status === 'processing' || status === 'failed') && (agent.activity || status === 'failed') && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.25, ease: 'easeOut' }}
                    className="overflow-hidden"
                  >
                    <p className="mt-0.5 text-[12.5px] leading-snug text-foreground/80">
                      {status === 'failed' ? 'This step could not be completed' : agent.activity}
                    </p>
                    {status === 'processing' && typeof agent.checks === 'number' && progress > 0 && (() => {
                      const remaining = Math.max(1, Math.ceil(agent.checks * (1 - progress)))
                      return (
                        <p className={cn('mt-1 tabular-nums text-accent-foreground', compact ? 'text-[11px]' : 'text-[11.5px]')}>
                          {remaining} {remaining === 1 ? 'check' : 'checks'} remaining
                        </p>
                      )
                    })()}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
