import React, { useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Link, useNavigate } from 'react-router-dom'
import {
  AlertTriangle, CheckCircle2, FlaskConical, Loader2, Play, RotateCcw,
  ShieldQuestion, UploadCloud,
} from 'lucide-react'
import { useClaimAgent } from '../hooks/useClaimAgent'
import { AgentTimeline } from '../components/claimbitz/AgentTimeline'
import { DashboardDocumentViewer } from '../components/claimbitz/DashboardDocumentViewer'
import { RiskPanel } from '../components/claimbitz/RiskPanel'
import { GeneratedOutput } from '../components/claimbitz/GeneratedOutput'
import { ProcessingLogs } from '../components/claimbitz/ProcessingLogs'
import { AnimatedPercent } from '../components/claimbitz/RiskRing'
import { ResolutionLayer } from '../components/claimbitz/ResolutionLayer'
import { cn } from '../lib/utils'

/* Derive the console status from real hook state. */
function deriveStatus({ isProcessing, isComplete, errorMessage, uploadedFile, demoMode, results }) {
  if (errorMessage) return 'error'
  if (isProcessing) return 'processing'
  if (isComplete) return 'completed'
  if (uploadedFile || demoMode || results) return 'ready'
  return 'empty'
}

/* Map real agents → the timeline's shape (name + activity + completion time). */
function toTimelineAgents(agents) {
  return agents.map((a) => ({ name: a.name, activity: a.description }))
}

/*
 * Presentation-only map: which CMS-1500 regions each real agent conceptually
 * reads. Drives the document highlight micro-interaction off the REAL active
 * agent. It does not fabricate any claim data — only which region glows.
 */
const AGENT_REGIONS = {
  scanner: [],
  ocr: ['patient', 'provider'],
  validator: ['patient', 'provider', 'totals'],
  medical: ['diagnosis', 'services'],
  policy: ['insurance'],
  fraud: ['services', 'totals'],
  risk: [],
  comm: [],
}

function Stat({ label, value, muted }) {
  return (
    <div className="min-w-0">
      <p className="eyebrow">{label}</p>
      <p className={cn('mt-0.5 text-[15px] font-semibold tabular-nums', muted ? 'text-[14px] font-medium text-foreground/80' : 'text-foreground')}>
        {value}
      </p>
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const {
    agents, currentStep, isProcessing, isComplete,
    results, riskScore, demoMode, setDemoMode, demoScenario, setDemoScenario,
    terminalLogs, uploadedFile, errorMessage, handleUpload, process, reset,
    resolutionStatus, actionLog, logAction, reprocess,
  } = useClaimAgent()
  const fileInputRef = useRef(null)

  const status = deriveStatus({ isProcessing, isComplete, errorMessage, uploadedFile, demoMode, results })

  const onFileChange = (e) => {
    const file = e.target.files?.[0]
    if (file) handleUpload(file)
  }
  const onDrop = (e) => {
    const file = e.dataTransfer.files?.[0]
    if (file) handleUpload(file)
  }

  // Real pipeline progress
  const total = agents.length
  const completedCount = agents.filter((a) => a.status === 'completed').length
  const failedIndex = agents.findIndex((a) => a.status === 'error')
  const activeIndex = isComplete
    ? total
    : isProcessing
      ? Math.max(0, currentStep)
      : failedIndex >= 0
        ? failedIndex
        : -1
  const activeAgent = isProcessing && currentStep >= 0 && currentStep < total ? agents[currentStep] : undefined
  const timelineAgents = toTimelineAgents(agents)

  // Document region highlight follows the REAL active agent (presentation only).
  const focusRegions = activeAgent ? (AGENT_REGIONS[activeAgent.id] || []) : []
  const focusLabel = activeAgent ? `${activeAgent.name.split(' ')[0]} reviewing` : undefined

  const logState = isComplete ? 'complete' : isProcessing ? 'running' : errorMessage ? 'failed' : 'idle'
  const fileName = uploadedFile?.name || (demoMode ? 'demo-claim.pdf' : 'claim.pdf')
  const claim = results?.claimData

  const pct = Math.round((riskScore || 0) * 100)
  const riskHigh = (results?.riskLabel || '').toUpperCase() === 'HIGH'

  const goSubmit = () => navigate('/submission')

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between gap-3 px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-2.5">
            <Link
              to="/"
              aria-label="ClaimBitz home"
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary text-[13px] font-bold text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              C
            </Link>
            <div className="min-w-0">
              <p className="text-[15px] font-semibold leading-tight tracking-tight text-foreground">ClaimBitz</p>
              <p className="hidden text-xs text-muted-foreground sm:block">Claims Processing Workspace</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Demo mode toggle (real hook demo mode) */}
            <label
              title="Demo mode loads a built-in sample claim instead of calling the backend."
              className="inline-flex h-9 cursor-pointer items-center gap-1.5 rounded-md border border-dashed border-warning/40 bg-warning/5 pl-2.5 pr-3 text-xs font-semibold uppercase tracking-wide text-warning"
            >
              <FlaskConical className="h-3.5 w-3.5" aria-hidden />
              <span className="hidden md:inline">Demo mode</span>
              <button
                type="button"
                role="switch"
                aria-checked={demoMode}
                aria-label="Toggle demo mode"
                onClick={() => setDemoMode(!demoMode)}
                className={cn('relative h-4 w-8 rounded-full transition-colors', demoMode ? 'bg-warning' : 'bg-border-strong')}
              >
                <span
                  className="absolute top-0.5 h-3 w-3 rounded-full bg-white transition-all"
                  style={{ left: demoMode ? '18px' : '2px' }}
                />
              </button>
            </label>

            {/* Demo risk scenario selector — only visible when demo mode is on */}
            {demoMode && !isProcessing && (
              <div className="hidden items-center gap-1 rounded-md border border-dashed border-warning/40 bg-warning/5 p-1 sm:flex">
                {[
                  { id: 'low', label: 'Low', tone: 'text-success' },
                  { id: 'medium', label: 'Med', tone: 'text-warning' },
                  { id: 'high', label: 'High', tone: 'text-destructive' },
                ].map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => setDemoScenario(s.id)}
                    className={cn(
                      'rounded px-2 py-1 text-[11px] font-semibold uppercase tracking-wide transition-colors',
                      demoScenario === s.id
                        ? `${s.tone} bg-surface shadow-sm`
                        : 'text-muted-foreground hover:text-foreground',
                    )}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            )}

            {(isComplete || status === 'error') && (
              <button
                onClick={reset}
                className="inline-flex h-9 items-center gap-1.5 rounded-md border border-border bg-surface px-3 text-[13px] font-medium text-foreground transition-colors hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <RotateCcw className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
                <span className="sr-only sm:not-sr-only">New claim</span>
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1440px] px-4 pb-14 pt-5 sm:px-6">
        <CommandPanel
          status={status}
          fileName={fileName}
          activeAgent={activeAgent}
          completedCount={completedCount}
          total={total}
          pct={pct}
          riskLabel={results?.riskLabel}
          recommendation={results?.recommendation}
          riskHigh={riskHigh}
          errorMessage={errorMessage}
          demoMode={demoMode}
          onRun={process}
          onBrowse={() => fileInputRef.current?.click()}
        />

        {status === 'empty' ? (
          <EmptyState onBrowse={() => fileInputRef.current?.click()} onDrop={onDrop} />
        ) : (
          <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-12 lg:items-start">
            <div className="min-w-0 space-y-5 lg:col-span-8">
              <DashboardDocumentViewer
                fileName={fileName}
                hasDocument
                claim={claim}
                scanning={isProcessing && activeIndex <= 2}
                focus={focusRegions}
                focusLabel={focusLabel}
                statusText={
                  isProcessing ? `${activeAgent?.name || 'Pipeline'} running`
                    : isComplete ? 'Verified'
                    : status === 'error' ? 'Could not analyze'
                    : 'Ready for analysis'
                }
                onNewClaim={reset}
              />

              {isComplete && results ? (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.45, delay: 0.6, ease: 'easeOut' }}
                  className="space-y-5"
                >
                  <RiskPanel
                    score={riskScore}
                    label={results.riskLabel}
                    recommendation={results.recommendation}
                    reasons={results.riskReasons || []}
                    onSubmit={goSubmit}
                  />
                  <ResolutionLayer
                    recommendation={results.recommendation}
                    riskLabel={results.riskLabel}
                    findings={results.findings}
                    riskReasons={results.riskReasons}
                    resolutionStatus={resolutionStatus}
                    actionLog={actionLog}
                    onPortal={() => { logAction('Navigate to submission', 'insurer portal'); goSubmit() }}
                    onReprocess={() => { logAction('Re-process claim', uploadedFile?.name || 'demo'); reprocess() }}
                  />
                  <GeneratedOutput results={results} onSubmit={goSubmit} onAction={logAction} />
                </motion.div>
              ) : status === 'error' ? (
                <ErrorState message={errorMessage} onRetry={process} />
              ) : (
                <PendingResults processing={isProcessing} onRun={process} />
              )}
            </div>

            <aside aria-labelledby="pipeline-heading" className="min-w-0 space-y-3 lg:sticky lg:top-[84px] lg:col-span-4">
              <div className="flex items-baseline justify-between px-1">
                <h2 id="pipeline-heading" className="eyebrow">AI agent pipeline</h2>
                <span className="text-xs tabular-nums text-muted-foreground">
                  {isComplete ? total : Math.max(0, completedCount)} / {total} agents
                  {demoMode && <span className="ml-2 text-warning">· demo</span>}
                </span>
              </div>
              <section className="rounded-lg border border-border bg-surface-muted px-3 py-3">
                <AgentTimeline agents={timelineAgents} activeIndex={activeIndex} failedIndex={failedIndex} />
              </section>
              <ProcessingLogs logs={terminalLogs} state={logState} />
            </aside>
          </div>
        )}
      </main>

      {/* Real hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg"
        onChange={onFileChange}
        className="hidden"
      />
    </div>
  )
}

function CommandPanel({
  status, fileName, activeAgent, completedCount, total, pct, riskLabel,
  recommendation, riskHigh, errorMessage, demoMode, onRun, onBrowse,
}) {
  const barPct = status === 'completed' ? 1 : status === 'processing' ? completedCount / total : status === 'error' ? 0.4 : 0
  const bar = status === 'completed' ? 'bg-success' : status === 'error' ? 'bg-destructive' : 'bg-primary'

  const title = {
    empty: 'No claim loaded',
    ready: 'Claim loaded',
    processing: 'Processing claim',
    completed: 'Claim processed',
    error: 'Unable to process claim',
  }[status]

  const dot = {
    empty: 'bg-subtle-foreground',
    ready: 'bg-foreground',
    processing: 'bg-primary',
    completed: 'bg-success',
    error: 'bg-destructive',
  }[status]

  return (
    <section
      aria-label="Claim status"
      aria-live="polite"
      className={cn(
        'relative overflow-hidden rounded-lg border bg-surface transition-colors duration-500',
        status === 'processing' && 'border-primary-border',
        status === 'completed' && 'border-success/30',
        status === 'error' && 'border-destructive/30',
        (status === 'ready' || status === 'empty') && 'border-border',
      )}
    >
      <div className="flex flex-col gap-4 px-5 py-4 lg:flex-row lg:items-center lg:gap-8">
        <div className="min-w-0 lg:w-[250px] lg:shrink-0">
          <p
            className={cn(
              'flex items-center gap-2 text-[11.5px] font-bold uppercase tracking-[0.08em]',
              status === 'processing' && 'text-accent-foreground',
              status === 'completed' && 'text-success',
              status === 'error' && 'text-destructive',
              (status === 'ready' || status === 'empty') && 'text-muted-foreground',
            )}
          >
            {status === 'completed' ? (
              <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 420, damping: 20 }}>
                <CheckCircle2 className="h-4 w-4" />
              </motion.span>
            ) : status === 'error' ? (
              <AlertTriangle className="h-4 w-4" />
            ) : (
              <span className="relative flex h-2 w-2">
                {status === 'processing' && (
                  <motion.span
                    className="absolute inset-0 rounded-full bg-primary"
                    animate={{ scale: [1, 2.2], opacity: [0.5, 0] }}
                    transition={{ duration: 1.4, repeat: Infinity }}
                  />
                )}
                <span className={cn('relative h-2 w-2 rounded-full', dot)} />
              </span>
            )}
            {title}
          </p>
          <p className="mt-1.5 truncate text-[17px] font-semibold tracking-tight text-foreground">
            {status === 'empty' ? 'Waiting for a document' : fileName}
          </p>
          <p className="text-[12.5px] text-muted-foreground">
            {status === 'empty' ? 'CMS-1500 · PDF or image' : demoMode ? 'CMS-1500 · demo claim' : 'CMS-1500'}
          </p>
        </div>

        <div className="min-w-0 flex-1">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={status === 'processing' ? `p${activeAgent?.name}` : status}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.22 }}
            >
              {status === 'processing' && (
                <div className="grid gap-x-8 gap-y-1 sm:grid-cols-[auto_1fr]">
                  <Stat label="Current agent" value={activeAgent?.name || 'Starting…'} />
                  <Stat label="Current activity" value={activeAgent?.description || 'Running pipeline'} muted />
                </div>
              )}
              {status === 'completed' && (
                <div className="flex flex-wrap items-end gap-x-8 gap-y-3">
                  <Stat label="Agents" value={`${total} / ${total} completed`} />
                  <div>
                    <p className="eyebrow">Rejection risk</p>
                    <p className={cn('mt-0.5 text-[15px] font-semibold', riskHigh ? 'text-destructive' : 'text-success')}>
                      <AnimatedPercent value={pct} /> · {riskLabel}
                    </p>
                  </div>
                  <div>
                    <p className="eyebrow">Decision</p>
                    <p className={cn('mt-1 inline-flex rounded-md px-2 py-0.5 text-[13px] font-bold uppercase tracking-wide', riskHigh ? 'bg-warning-subtle text-warning' : 'bg-success-subtle text-success')}>
                      {recommendation}
                    </p>
                  </div>
                </div>
              )}
              {status === 'ready' && <Stat label="Next step" value="Ready for analysis · agents queued" muted />}
              {status === 'error' && <Stat label="Error" value={errorMessage || 'The document could not be analyzed.'} muted />}
              {status === 'empty' && <Stat label="Next step" value="Load a claim document to begin" muted />}
            </motion.div>
          </AnimatePresence>
        </div>

        <div className="flex shrink-0 items-center gap-6">
          {(status === 'processing' || status === 'completed' || status === 'error') && (
            <Stat label="Progress" value={`${status === 'completed' ? total : completedCount} / ${total}`} />
          )}
          {status === 'ready' && (
            <button
              onClick={onRun}
              className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-[14px] font-semibold text-white transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 active:scale-[0.98]"
            >
              <Play className="h-4 w-4" aria-hidden /> Analyze
            </button>
          )}
          {status === 'empty' && (
            <button
              onClick={onBrowse}
              className="inline-flex h-10 items-center gap-2 rounded-md border border-border-strong bg-surface px-4 text-[14px] font-semibold text-foreground transition-colors hover:bg-surface-muted"
            >
              Upload claim
            </button>
          )}
        </div>
      </div>

      <div className="h-[3px] bg-border/60" aria-hidden>
        <motion.div
          className={cn('h-full origin-left', bar)}
          initial={false}
          animate={{ scaleX: barPct }}
          transition={{ duration: status === 'processing' ? 0.12 : 0.5, ease: 'linear' }}
        />
      </div>
    </section>
  )
}

function PendingResults({ processing, onRun }) {
  return (
    <section className="panel flex flex-col gap-4 px-5 py-6 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">
        {processing ? (
          <Loader2 className="mt-0.5 h-4 w-4 motion-safe:animate-spin text-primary" aria-hidden />
        ) : (
          <ShieldQuestion className="mt-0.5 h-4 w-4 text-muted-foreground" aria-hidden />
        )}
        <div>
          <h2 className="text-[15px] font-semibold text-foreground">
            {processing ? 'Analyzing claim…' : 'Risk and findings not analyzed yet'}
          </h2>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            {processing
              ? 'Risk assessment and outputs appear once all agents complete.'
              : 'Run the analysis to score rejection risk and generate findings.'}
          </p>
        </div>
      </div>
      {!processing && (
        <button
          onClick={onRun}
          className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-md bg-primary px-4 text-[14px] font-semibold text-white transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 active:scale-[0.98]"
        >
          <Play className="h-4 w-4" aria-hidden />
          Analyze claim
        </button>
      )}
    </section>
  )
}

function ErrorState({ message, onRetry }) {
  return (
    <div className="panel px-6 py-8 text-center" role="alert">
      <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-md bg-destructive/10">
        <AlertTriangle className="h-5 w-5 text-destructive" />
      </span>
      <h2 className="mt-5 text-[22px] font-semibold tracking-tight text-foreground">Unable to process claim</h2>
      <p className="mx-auto mt-2 max-w-md text-[14.5px] leading-relaxed text-muted-foreground">
        {message || 'The document could not be analyzed. Please try again or upload a clearer file.'}
      </p>
      <button
        onClick={onRetry}
        className="mt-6 inline-flex h-11 items-center gap-2 rounded-md bg-primary px-5 text-[14px] font-semibold text-white transition-colors hover:bg-primary-hover active:scale-[0.98]"
      >
        <RotateCcw className="h-4 w-4" />
        Try again
      </button>
    </div>
  )
}

function EmptyState({ onBrowse, onDrop }) {
  const [drag, setDrag] = useState(false)
  return (
    <div className="mx-auto max-w-2xl py-12">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="panel px-8 py-10 text-center"
      >
        <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-md bg-primary-subtle">
          <UploadCloud className="h-5 w-5 text-primary" />
        </span>
        <h1 className="mt-5 text-[26px] font-semibold tracking-tight text-foreground">No claim loaded</h1>
        <p className="mx-auto mt-2 max-w-md text-[14.5px] leading-relaxed text-muted-foreground">
          Upload a CMS-1500 claim document to start the agent pipeline. Supported formats: PDF, PNG, JPG, JPEG.
        </p>
        <div
          className={cn(
            'mt-7 rounded-lg border border-dashed px-6 py-10 transition-colors',
            drag ? 'border-primary bg-primary-subtle' : 'border-border-strong bg-surface-muted',
          )}
          onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); onDrop?.(e) }}
        >
          <p className="text-[14.5px] font-semibold text-foreground">Drop a CMS-1500 claim here</p>
          <p className="mt-1 text-[13px] text-muted-foreground">or use demo mode from the header</p>
          <button
            onClick={onBrowse}
            className="mt-5 inline-flex h-11 items-center gap-2 rounded-md bg-primary px-5 text-[14px] font-semibold text-white transition-colors hover:bg-primary-hover active:scale-[0.98]"
          >
            Browse files
          </button>
        </div>
      </motion.div>
    </div>
  )
}
