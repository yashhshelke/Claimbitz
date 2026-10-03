import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, Check, CheckCircle2, Copy, Download } from 'lucide-react'
import { cn } from '../../lib/utils'

const TABS = [
  { id: 'email', label: 'Email' },
  { id: 'whatsapp', label: 'WhatsApp' },
  { id: 'summary', label: 'Summary' },
  { id: 'findings', label: 'Findings' },
]

/*
 * Split a message (email/WhatsApp draft) into readable paragraph blocks on blank
 * lines. Single newlines inside a block are preserved via `whitespace-pre-line`.
 * Presentation only — the underlying text (already newline-normalized) is
 * unchanged and copy still uses the full original string.
 */
function toBlocks(text) {
  return String(text || '')
    .split(/\n{2,}/)
    .map((b) => b.trim())
    .filter(Boolean)
}

const VERDICT = {
  approve: 'bg-success-subtle text-success',
  reject: 'bg-destructive/10 text-destructive',
  flag: 'bg-warning-subtle text-warning',
}

function labelize(key) {
  return key.replace(/([A-Z])/g, ' $1').replace(/^./, (c) => c.toUpperCase()).trim()
}

function formatValue(key, value) {
  const k = key.toLowerCase()
  if (typeof value === 'number' && (k.includes('amount') || k.includes('billed') || k.includes('responsibility'))) {
    return `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
  }
  return String(value)
}

/*
 * Some drafts (e.g. the WhatsApp message) arrive with literal escaped "\n"
 * sequences rather than real newlines. Convert those to real line breaks for
 * display and copy. Real newline characters are left untouched, so this is safe
 * to apply uniformly and never double-converts.
 */
function normalizeNewlines(s) {
  return typeof s === 'string' ? s.replace(/\\n/g, '\n') : (s ?? '')
}

/**
 * Generated outputs — Lovable visual, REAL data from useClaimAgent results:
 * email / whatsapp drafts, claim summary (claimData) and agent findings.
 * Submit action navigates to the real submission flow.
 */
export function GeneratedOutput({ results, onSubmit, onAction }) {
  const [tab, setTab] = useState('email')
  const [copied, setCopied] = useState(false)

  const high = (results.riskLabel || '').toUpperCase() === 'HIGH'
  const emailText = normalizeNewlines(results.email)
  const whatsappText = normalizeNewlines(results.whatsapp)
  const copyText =
    tab === 'email' ? emailText :
    tab === 'whatsapp' ? whatsappText :
    tab === 'findings' ? JSON.stringify(results.findings, null, 2) :
    JSON.stringify(results.claimData, null, 2)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(copyText)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
      onAction?.('Copied ' + tab, tab === 'findings' ? 'JSON' : 'text')
    } catch (e) {
      console.error(e)
    }
  }

  const download = () => {
    const ext = tab === 'findings' || tab === 'summary' ? 'json' : 'txt'
    const blob = new Blob([copyText], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `claimbitz-${tab}.${ext}`
    a.click()
    URL.revokeObjectURL(url)
    onAction?.('Downloaded ' + tab, ext)
  }

  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      className="panel overflow-hidden"
    >
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-3.5">
        <div>
          <h2 className="text-[19px] font-semibold text-foreground">Generated outputs</h2>
          <p className="mt-0.5 text-[13px] text-muted-foreground">AI-generated drafts — review, copy or export before sending</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={copy}
            className="inline-flex h-9 items-center gap-1.5 rounded-md border border-border px-3 text-[13px] font-medium text-foreground transition-colors hover:bg-surface-muted"
          >
            {copied ? <Check className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4 text-muted-foreground" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
          <button
            onClick={download}
            className="inline-flex h-9 items-center gap-1.5 rounded-md border border-border px-3 text-[13px] font-medium text-foreground transition-colors hover:bg-surface-muted"
          >
            <Download className="h-4 w-4 text-muted-foreground" />
            Export
          </button>
          <button
            onClick={onSubmit}
            className="inline-flex h-9 items-center gap-1.5 rounded-md bg-primary px-3.5 text-[13px] font-semibold text-white transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:scale-[0.98]"
          >
            Continue to submission
          </button>
        </div>
      </header>

      <div className="flex gap-1 overflow-x-auto border-b border-border bg-surface-muted px-3 py-2" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              'relative rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors',
              tab === t.id ? 'text-primary' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {tab === t.id && (
              <motion.span
                layoutId="dash-output-tab"
                className="absolute inset-0 rounded-md bg-surface shadow-panel"
                transition={{ type: 'spring', stiffness: 420, damping: 34 }}
              />
            )}
            <span className="relative">{t.label}</span>
          </button>
        ))}
      </div>

      <div className="px-5 py-5">
        <div
          className={cn(
            'mb-4 flex items-center gap-2 rounded-md border px-3.5 py-2.5',
            high ? 'border-warning/30 bg-warning/10' : 'border-success/25 bg-success-subtle',
          )}
        >
          {high ? <AlertTriangle className="h-4 w-4 text-warning" /> : <CheckCircle2 className="h-4 w-4 text-success" />}
          <p className="text-[13px] font-medium text-foreground">
            {high
              ? `Claim processed · ${Math.round((results.riskScore || 0) * 100)}% risk exceeds the threshold · human review required`
              : `Claim processed successfully · recommendation ${results.recommendation || 'APPROVE'}`}
          </p>
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.22 }}
            className="max-h-[320px] overflow-y-auto"
          >
            {(tab === 'email' || tab === 'whatsapp') && (
              <div className="space-y-3">
                {toBlocks(tab === 'email' ? emailText : whatsappText).map((para, i) => (
                  <p
                    key={i}
                    className={cn(
                      'whitespace-pre-line text-[14.5px] leading-relaxed',
                      i === 0 ? 'font-semibold text-foreground' : 'text-muted-foreground',
                    )}
                  >
                    {para}
                  </p>
                ))}
              </div>
            )}

            {tab === 'summary' && (
              <dl className="divide-y divide-border">
                {Object.entries(results.claimData || {}).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between gap-4 py-2.5">
                    <dt className="text-[13px] text-muted-foreground">{labelize(key)}</dt>
                    <dd className="text-[13px] font-medium text-foreground text-right break-words">
                      {formatValue(key, value)}
                    </dd>
                  </div>
                ))}
                <div className="flex items-center justify-between gap-4 pt-3">
                  <dt className="text-[13px] text-muted-foreground">Recommendation</dt>
                  <dd className="text-[13px] font-semibold text-foreground">
                    {results.recommendation} · {results.riskScore} ({results.riskLabel})
                  </dd>
                </div>
              </dl>
            )}

            {tab === 'findings' && (
              <div className="space-y-2">
                {(results.findings || []).map((f, i) => (
                  <div key={i} className="rounded-md border border-border p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[13px] font-semibold capitalize text-foreground">
                        {f.agent.replace(/_/g, ' ')}
                      </span>
                      <span className={cn('rounded px-1.5 py-0.5 text-[10px] font-bold uppercase', VERDICT[f.verdict] || 'bg-surface-muted text-muted-foreground')}>
                        {f.verdict}
                      </span>
                      <span className="text-[11px] text-subtle-foreground">conf {(f.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <p className="mt-1 text-[12px] leading-relaxed text-muted-foreground">{f.reasoning}</p>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </motion.section>
  )
}
