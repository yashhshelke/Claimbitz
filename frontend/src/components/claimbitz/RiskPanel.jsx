import React from 'react'
import { motion } from 'framer-motion'
import { Send, ShieldAlert, ShieldCheck } from 'lucide-react'
import { RiskRing, AnimatedPercent } from './RiskRing'
import { cn } from '../../lib/utils'

/**
 * Risk & decision panel — Lovable visual, REAL data.
 *
 * Props come straight from useClaimAgent results:
 *   score        0..1 rejection risk (riskScore)
 *   label        'LOW' | 'MEDIUM' | 'HIGH' (riskLabel)
 *   recommendation  'APPROVE' | 'REJECT' | 'REVIEW'
 *   reasons      string[] (riskReasons)
 *   onSubmit     navigate to submission
 */
function bandFor(score, label) {
  const l = (label || '').toUpperCase()
  if (l === 'HIGH' || score > 0.6) return { tone: 'destructive', high: true, readable: 'High risk' }
  if (l === 'MEDIUM' || score > 0.3) return { tone: 'warning', high: false, readable: 'Medium risk' }
  return { tone: 'success', high: false, readable: 'Low risk' }
}

export function RiskPanel({ score = 0, label, recommendation, reasons = [], onSubmit }) {
  const pct = Math.round((score || 0) * 100)
  const band = bandFor(score, label)
  const rec = recommendation || (band.high ? 'REVIEW' : 'APPROVE')

  return (
    <section className="panel overflow-hidden">
      <header className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
        <div>
          <h2 className="text-[19px] font-semibold text-foreground">Risk &amp; decision</h2>
          <p className="mt-0.5 text-[13px] text-muted-foreground">Model-based rejection risk assessment</p>
        </div>
        <span
          className={cn(
            'inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md px-2.5 py-1 text-xs font-semibold uppercase tracking-wide',
            band.high ? 'bg-destructive/10 text-destructive' : band.tone === 'warning' ? 'bg-warning-subtle text-warning' : 'bg-success-subtle text-success',
          )}
        >
          {band.high ? <ShieldAlert className="h-3.5 w-3.5" /> : <ShieldCheck className="h-3.5 w-3.5" />}
          {band.readable}
        </span>
      </header>

      <div className="grid gap-6 px-5 py-5 md:grid-cols-[auto_1fr] md:items-center">
        <div className="flex items-center gap-5">
          <div className="relative">
            <RiskRing value={pct} tone={band.tone} />
            <div className="absolute inset-0 flex items-center justify-center">
              <AnimatedPercent value={pct} className="text-2xl font-semibold tracking-tight text-foreground" />
            </div>
          </div>
          <div className="min-w-0">
            <p className="text-[15px] font-semibold text-foreground">
              {band.high ? 'Human review required' : 'Automated review complete'}
            </p>
            <p className="mt-1 max-w-[16rem] text-[13px] text-muted-foreground">
              {band.high
                ? 'The claim exceeds the automated approval threshold.'
                : 'Below the automated approval threshold.'}
            </p>
            <button
              onClick={onSubmit}
              className={cn(
                'mt-3 inline-flex h-9 items-center gap-1.5 rounded-md px-3.5 text-[13px] font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 active:scale-[0.98]',
                band.high
                  ? 'border border-border bg-surface text-foreground hover:bg-surface-muted'
                  : 'bg-primary text-white hover:bg-primary-hover',
              )}
            >
              <Send className="h-4 w-4" />
              {band.high ? 'Review before submission' : 'Continue to submission'}
            </button>
          </div>
        </div>

        <div className="rounded-md border border-border bg-surface-muted">
          <p className="border-b border-border px-3.5 py-2 text-[11px] font-semibold uppercase tracking-wide text-subtle-foreground">
            Decision
          </p>
          <div className="flex items-center justify-between gap-4 px-3.5 py-2.5">
            <span className="text-[13px] text-muted-foreground">Recommendation</span>
            <span
              className={cn(
                'rounded px-2 py-0.5 text-[12px] font-bold uppercase tracking-wide',
                rec === 'APPROVE' ? 'bg-success-subtle text-success' : rec === 'REJECT' ? 'bg-destructive/10 text-destructive' : 'bg-warning-subtle text-warning',
              )}
            >
              {rec}
            </span>
          </div>

          {reasons.length > 0 && (
            <dl className="divide-y divide-border border-t border-border">
              {reasons.slice(0, 5).map((r, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.28, delay: 0.15 + i * 0.05 }}
                  className="px-3.5 py-2 text-[12.5px] leading-relaxed text-muted-foreground"
                >
                  {r}
                </motion.div>
              ))}
            </dl>
          )}
        </div>
      </div>
    </section>
  )
}
