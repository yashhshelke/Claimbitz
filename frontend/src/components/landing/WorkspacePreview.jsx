import React, { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { CheckCircle2, FileText } from 'lucide-react'
import { AgentTimeline } from '../claimbitz/AgentTimeline'
import { AnimatedPercent, RiskRing } from '../claimbitz/RiskRing'
import { DEMO_AGENTS, DEMO_CLAIM } from './landingDemo'
import { cn } from '../../lib/utils'

const SHOWN = 7
const STEP_MS = 850

/**
 * Landing-page product demo (marketing only). Steps through agents once,
 * then holds the completed claim. Uses DEMO_AGENTS/DEMO_CLAIM — never real data.
 * A full page reload restarts the sequence.
 */
export function WorkspacePreview() {
  const [step, setStep] = useState(0) // 0..SHOWN-1 processing, SHOWN = complete

  useEffect(() => {
    if (step >= SHOWN) return // done — hold final state
    const t = window.setTimeout(() => setStep((s) => s + 1), STEP_MS)
    return () => window.clearTimeout(t)
  }, [step])

  const done = step >= SHOWN
  const regions = done ? [] : DEMO_AGENTS[step].regions
  const rows = [
    ['Insured ID', 'SH4481902', 'insurance'],
    ['Patient', 'Sharma, Ananya D', 'patient'],
    ['Provider Reg.', '1487563920', 'provider'],
    ['Diagnosis', 'E11.9 · I10 · E78.5', 'diagnosis'],
    ['Procedures', '99214 · 83036 · 80061', 'services'],
    ['Total charge', '₹41,200', 'totals'],
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.15, ease: 'easeOut' }}
      className="rounded-xl border border-border bg-surface shadow-elevated"
      aria-label="Live product demo"
    >
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div className="flex items-center gap-2.5">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary-subtle">
            <FileText className="h-3.5 w-3.5 text-primary" />
          </span>
          <div>
            <p className="text-[13px] font-semibold text-foreground">{DEMO_CLAIM.file}</p>
            <p className="text-[11px] text-muted-foreground">CMS-1500 · 2 pages</p>
          </div>
        </div>
        <span
          className={cn(
            'inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-semibold transition-colors duration-300',
            done ? 'bg-success-subtle text-success' : 'bg-primary-subtle text-accent-foreground',
          )}
        >
          {done ? <CheckCircle2 className="h-3 w-3" /> : <span className="h-1.5 w-1.5 rounded-full bg-primary" />}
          {done ? 'Processed' : `Processing · ${step + 1}/9`}
        </span>
      </div>
      <div className="h-[2px] bg-border/60">
        <motion.div
          className={cn('h-full origin-left', done ? 'bg-success' : 'bg-primary')}
          animate={{ scaleX: done ? 1 : (step + 0.5) / 9 }}
          transition={{ duration: step === 0 ? 0 : 0.5, ease: 'easeOut' }}
        />
      </div>

      <div className="grid gap-0 sm:grid-cols-[1.05fr_1fr]">
        <div className="border-b border-border p-4 sm:border-b-0 sm:border-r">
          <p className="eyebrow">Document preview</p>
          <div className="relative mt-3 space-y-0.5 overflow-hidden rounded-md border border-border-strong bg-surface-muted p-2">
            {step <= 2 && (
              <motion.div
                aria-hidden
                className="pointer-events-none absolute inset-x-0 z-10 h-px bg-primary/70"
                initial={{ top: '0%' }}
                animate={{ top: ['0%', '100%'] }}
                transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
              />
            )}
            {rows.map(([k, v, r]) => {
              const on = regions.includes(r)
              return (
                <div
                  key={k}
                  className={cn(
                    'flex items-baseline justify-between gap-3 rounded-sm border-l-2 px-1.5 py-0.5 transition-colors duration-300',
                    on ? 'border-primary bg-primary-subtle' : 'border-transparent',
                  )}
                >
                  <span className="text-[11.5px] text-muted-foreground">{k}</span>
                  <span className="text-[12px] font-medium text-foreground">{v}</span>
                </div>
              )
            })}
          </div>

          <div className="mt-4 min-h-[90px] rounded-md border border-border p-3">
            <AnimatePresence mode="wait" initial={false}>
              {done ? (
                <motion.div
                  key="done"
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center gap-4"
                >
                  <div className="relative shrink-0">
                    <RiskRing value={DEMO_CLAIM.risk} size={64} />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <AnimatedPercent value={DEMO_CLAIM.risk} className="text-sm font-semibold text-foreground" />
                    </div>
                  </div>
                  <div>
                    <p className="text-[11.5px] text-muted-foreground">9 agents completed</p>
                    <p className="text-[13px] font-semibold uppercase tracking-wide text-success">{DEMO_CLAIM.riskLabel}</p>
                    <p className="mt-1 text-[11.5px] text-muted-foreground">
                      Recommendation <span className="font-bold uppercase text-foreground">{DEMO_CLAIM.recommendation}</span>
                    </p>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="wait"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex h-[64px] flex-col justify-center"
                >
                  <p className="text-[11.5px] text-muted-foreground">Rejection risk</p>
                  <p className="text-[13px] font-semibold text-subtle-foreground">Scored after all agents complete</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        <div className="p-4">
          <p className="eyebrow">AI processing timeline</p>
          <div className="mt-3">
            <AgentTimeline agents={DEMO_AGENTS.slice(0, SHOWN)} activeIndex={done ? SHOWN : step} compact progress={0.4} />
          </div>
        </div>
      </div>

      <div className="border-t border-border bg-surface-muted px-4 py-2.5" aria-live="polite">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5">
          <span className="eyebrow !text-[10.5px]">Live claim activity</span>
          {[step - 2, step - 1, step, step + 1]
            .filter((i) => i >= 0 && i < SHOWN && !done)
            .map((i) => {
              const a = DEMO_AGENTS[i]
              const state = i < step ? 'done' : i === step ? 'active' : 'wait'
              return (
                <motion.span
                  layout
                  key={a.name}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="inline-flex items-center gap-1.5 text-[11.5px]"
                >
                  {state === 'done' ? (
                    <CheckCircle2 className="h-3 w-3 text-success" aria-label="Completed" />
                  ) : state === 'active' ? (
                    <span className="relative flex h-2 w-2" aria-label="Processing">
                      <span className="absolute inset-0 motion-safe:animate-ping rounded-full bg-primary/40" />
                      <span className="relative h-2 w-2 rounded-full bg-primary" />
                    </span>
                  ) : (
                    <span className="h-2 w-2 rounded-full border border-border-strong" aria-label="Pending" />
                  )}
                  <span className={cn('font-semibold', state === 'wait' ? 'text-subtle-foreground' : 'text-foreground')}>
                    {a.short}
                  </span>
                  <span className="hidden text-muted-foreground lg:inline">
                    {state === 'done' ? a.description : state === 'active' ? a.activity : 'Waiting'}
                  </span>
                </motion.span>
              )
            })}
          {done && (
            <span className="inline-flex items-center gap-1.5 text-[11.5px] font-semibold text-success">
              <CheckCircle2 className="h-3 w-3" /> Claim processed · 9 / 9 agents · 27.4s
            </span>
          )}
        </div>
      </div>
    </motion.div>
  )
}
