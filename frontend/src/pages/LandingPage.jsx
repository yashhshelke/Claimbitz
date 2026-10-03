import React, { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { AnimatePresence, motion, useInView } from 'framer-motion'
import {
  AlertTriangle, ArrowRight, CheckCircle2, FileText, Send,
  ShieldAlert, ShieldCheck, UserCheck,
} from 'lucide-react'
import { WorkspacePreview } from '../components/landing/WorkspacePreview'
import { AnimatedPercent } from '../components/claimbitz/RiskRing'
import { cn } from '../lib/utils'

/* ---------- shared bits ---------- */

function useOnce() {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-80px' })
  return [ref, inView]
}

function CountUp({ to, decimals = 0, active }) {
  const [v, setV] = useState(0)
  useEffect(() => {
    if (!active) return
    let raf = 0
    const start = performance.now()
    const tick = (now) => {
      const p = Math.min(1, (now - start) / 900)
      setV(to * (1 - Math.pow(1 - p, 3)))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [to, active])
  return <span className="tabular-nums">{v.toFixed(decimals)}</span>
}

function SectionHead({ eyebrow, title, children }) {
  return (
    <div className="max-w-xl">
      <p className="eyebrow">{eyebrow}</p>
      <h2 className="mt-2 text-[28px] font-semibold leading-tight text-foreground sm:text-[32px]">{title}</h2>
      {children && <p className="mt-2 text-[15px] text-muted-foreground">{children}</p>}
    </div>
  )
}

/* ---------- workflow ---------- */

const STAGES = [
  { k: 'CMS-1500', rows: [['claim_10482.pdf', ''], ['2 pages', '']] },
  { k: 'Document analysis', rows: [['Fields extracted', '38'], ['Sections read', '6']] },
  { k: 'AI review', rows: [['Medical', '✓'], ['Policy', '✓'], ['Fraud', '✓']] },
  { k: 'Risk intelligence', rows: [['Rejection risk', '24%'], ['Band', 'Low']] },
  { k: 'Decision', rows: [['Recommendation', 'APPROVE']] },
]

function Workflow() {
  const [ref, inView] = useOnce()
  return (
    <div ref={ref} className="mt-10 overflow-hidden rounded-xl border border-border bg-surface shadow-panel">
      <div className="grid md:grid-cols-5">
        {STAGES.map((s, i) => {
          const last = i === STAGES.length - 1
          return (
            <motion.div
              key={s.k}
              initial={{ opacity: 0, y: 6 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ delay: i * 0.18, duration: 0.35 }}
              className={cn(
                'relative border-border p-5',
                !last && 'border-b md:border-b-0 md:border-r',
                last && 'bg-success-subtle',
              )}
            >
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    'flex h-5 w-5 items-center justify-center rounded-full font-mono text-[10px] font-semibold',
                    last ? 'bg-success text-white' : 'bg-primary-subtle text-accent-foreground',
                  )}
                >
                  {i + 1}
                </span>
                <p className="text-[11.5px] font-semibold uppercase tracking-wide text-foreground">{s.k}</p>
              </div>
              <dl className="mt-4 space-y-1.5">
                {s.rows.map(([a, b]) => (
                  <div key={a} className="flex items-baseline justify-between gap-2">
                    <dt className="text-[13px] text-muted-foreground">{a}</dt>
                    {b && (
                      <dd className={cn('font-mono text-[13px] font-medium', b === '✓' || b === 'APPROVE' ? 'text-success' : 'text-foreground')}>
                        {b}
                      </dd>
                    )}
                  </div>
                ))}
              </dl>
              {!last && (
                <motion.span
                  aria-hidden
                  className="absolute -right-px top-1/2 z-10 hidden h-px w-4 origin-left translate-x-1/2 bg-primary md:block"
                  initial={{ scaleX: 0 }}
                  animate={inView ? { scaleX: 1 } : {}}
                  transition={{ delay: i * 0.18 + 0.25, duration: 0.3 }}
                />
              )}
            </motion.div>
          )
        })}
      </div>
      <div className="h-[2px] bg-border/60">
        <motion.div
          className="h-full origin-left bg-primary"
          initial={{ scaleX: 0 }}
          animate={inView ? { scaleX: 1 } : {}}
          transition={{ duration: 1, ease: 'easeOut', delay: 0.1 }}
        />
      </div>
    </div>
  )
}

/* ---------- claim anatomy ---------- */

const ANATOMY = [
  { agent: 'Validation Agent', task: 'Required fields and formats', regions: ['patient', 'provider', 'totals'] },
  { agent: 'Medical Expert', task: 'Diagnosis ↔ procedure consistency', regions: ['diagnosis', 'services'] },
  { agent: 'Policy Expert', task: 'Payer and coverage rules', regions: ['insurance'] },
  { agent: 'Fraud Detection', task: 'Service lines and billing metadata', regions: ['services', 'totals'] },
]

function Box({ id, on, label, children }) {
  return (
    <div
      data-region={id}
      className={cn(
        'relative border-l-2 px-3 py-2 transition-colors duration-300',
        on ? 'border-primary bg-primary-subtle/70' : 'border-transparent',
      )}
    >
      <p className="text-[10px] font-semibold uppercase tracking-wide text-subtle-foreground">{label}</p>
      <div className={cn('mt-0.5 text-[12.5px] transition-opacity duration-300', on ? 'text-foreground' : 'text-muted-foreground')}>
        {children}
      </div>
    </div>
  )
}

function ClaimAnatomy() {
  const [idx, setIdx] = useState(0)
  const [hover, setHover] = useState(null)
  const [ref, inView] = useOnce()
  useEffect(() => {
    if (!inView || hover !== null) return
    const t = window.setInterval(() => setIdx((i) => (i + 1) % ANATOMY.length), 2200)
    return () => window.clearInterval(t)
  }, [inView, hover])
  const cur = hover ?? idx
  const on = (r) => ANATOMY[cur].regions.includes(r)

  return (
    <div ref={ref} className="mt-10 grid gap-6 lg:grid-cols-[1fr_1.35fr] lg:items-start">
      <ul className="space-y-1" onMouseLeave={() => setHover(null)}>
        {ANATOMY.map((a, i) => {
          const active = i === cur
          return (
            <li key={a.agent}>
              <button
                onMouseEnter={() => setHover(i)}
                onFocus={() => setHover(i)}
                onBlur={() => setHover(null)}
                className={cn(
                  'flex min-h-11 w-full items-center gap-3 rounded-md border px-3.5 py-2.5 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  active ? 'border-primary-border bg-surface' : 'border-transparent hover:bg-surface',
                )}
              >
                <span className={cn('h-2 w-2 shrink-0 rounded-full transition-colors', active ? 'bg-primary' : 'border border-border-strong')} aria-hidden />
                <span className="min-w-0">
                  <span className="block text-[14px] font-semibold text-foreground">{a.agent}</span>
                  <span className="block text-[12.5px] text-muted-foreground">{a.task}</span>
                </span>
                {active && <span className="ml-auto text-[11px] font-medium text-accent-foreground">Reading</span>}
              </button>
            </li>
          )
        })}
      </ul>

      <div className="rounded-lg bg-background p-3 sm:p-5">
        <div className="overflow-hidden rounded-[6px] border border-border-strong bg-surface shadow-paper">
          <div className="flex items-center justify-between border-b border-border-strong bg-surface-muted px-3 py-2">
            <p className="text-[11.5px] font-semibold text-foreground">HEALTH INSURANCE CLAIM FORM</p>
            <p className="font-mono text-[10.5px] text-muted-foreground">CMS-1500 (02/12)</p>
          </div>
          <div className="grid grid-cols-2 divide-x divide-border border-b border-border">
            <Box id="insurance" on={on('insurance')} label="1. Insurance · payer">Star Health Insurance · SH01</Box>
            <Box id="patient" on={on('patient')} label="2. Patient">Sharma, Ananya D · 17/04/1985</Box>
          </div>
          <div className="border-b border-border">
            <Box id="diagnosis" on={on('diagnosis')} label="21. Diagnosis (ICD-10)">
              <span className="font-mono">E11.9 · I10 · E78.5 · Z00.00</span>
            </Box>
          </div>
          <div className="border-b border-border">
            <Box id="services" on={on('services')} label="24. Procedures · service lines">
              <span className="font-mono">99214-25 · 83036 · 80061</span>
            </Box>
          </div>
          <div className="grid grid-cols-2 divide-x divide-border">
            <Box id="provider" on={on('provider')} label="33. Provider">Manipal Internal Medicine · Reg 1902847561</Box>
            <Box id="totals" on={on('totals')} label="28. Total charge">
              <span className="font-mono">₹41,200</span>
            </Box>
          </div>
        </div>
        <AnimatePresence mode="wait">
          <motion.p
            key={cur}
            initial={{ opacity: 0, y: 3 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="mt-3 text-[12.5px] text-muted-foreground"
          >
            <span className="font-semibold text-accent-foreground">{ANATOMY[cur].agent}</span> → {ANATOMY[cur].task.toLowerCase()}
          </motion.p>
        </AnimatePresence>
      </div>
    </div>
  )
}

/* ---------- evidence → decision + human review ---------- */

const EVIDENCE = [
  ['Eligibility', 'Verified'],
  ['Required fields', 'Complete'],
  ['Diagnosis', 'Consistent'],
  ['Procedure codes', 'Validated'],
  ['Policy match', 'High'],
  ['Fraud signals', 'None'],
]

function DelayedPercent({ value, delay }) {
  const [go, setGo] = useState(false)
  useEffect(() => {
    const t = window.setTimeout(() => setGo(true), delay * 1000)
    return () => window.clearTimeout(t)
  }, [delay])
  return go ? <AnimatedPercent value={value} /> : <span className="text-subtle-foreground">··</span>
}

function EvidenceDecision() {
  const [ref, inView] = useOnce()
  const decided = EVIDENCE.length * 0.18 + 0.3
  return (
    <div ref={ref} className="mt-10 overflow-hidden rounded-xl border border-border bg-surface shadow-panel">
      <div className="grid lg:grid-cols-[1.3fr_1fr]">
        <div className="border-b border-border p-5 lg:border-b-0 lg:border-r">
          <div className="flex items-center justify-between">
            <p className="eyebrow">Claim review · evidence found</p>
            <span className="font-mono text-[11px] text-subtle-foreground">claim_10482</span>
          </div>
          <dl className="mt-3 divide-y divide-border">
            {EVIDENCE.map(([k, v], i) => (
              <motion.div
                key={k}
                initial={{ opacity: 0, x: -4 }}
                animate={inView ? { opacity: 1, x: 0 } : {}}
                transition={{ delay: i * 0.18, duration: 0.3 }}
                className="flex items-center justify-between py-2.5"
              >
                <dt className="text-[14px] text-muted-foreground">{k}</dt>
                <dd className="inline-flex items-center gap-1.5 text-[14px] font-medium text-foreground">
                  <CheckCircle2 className="h-4 w-4 text-success" aria-hidden />
                  {v}
                </dd>
              </motion.div>
            ))}
          </dl>
        </div>

        <div className="flex flex-col justify-center gap-5 bg-surface-muted p-6">
          <p className="eyebrow">Decision</p>
          <motion.div initial={{ opacity: 0 }} animate={inView ? { opacity: 1 } : {}} transition={{ delay: decided - 0.2 }}>
            <p className="text-[56px] font-semibold leading-none tracking-tight text-foreground">
              {inView ? <DelayedPercent delay={decided - 0.2} value={24} /> : '—'}
            </p>
            <p className="mt-2 inline-flex items-center gap-1.5 text-[13px] font-semibold uppercase tracking-wide text-success">
              <ShieldCheck className="h-4 w-4" /> Low rejection risk
            </p>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: decided + 0.9 }}
            className="flex items-center gap-2 border-t border-border pt-4"
          >
            <CheckCircle2 className="h-5 w-5 text-success" />
            <span className="text-[22px] font-semibold tracking-tight text-foreground">APPROVE</span>
          </motion.div>
        </div>
      </div>
    </div>
  )
}

function ReviewPaths() {
  const paths = [
    {
      band: 'Low risk', risk: 24, icon: ShieldCheck, tone: 'text-success',
      title: 'Automated review complete', note: 'Below the approval threshold. Ready to submit.',
      action: 'Submit claim', ActionIcon: Send, primary: true,
    },
    {
      band: 'High risk', risk: 42, icon: ShieldAlert, tone: 'text-destructive',
      title: 'Human review required', note: 'Modifier 25 flagged · billing frequency above range.',
      action: 'Assign reviewer', ActionIcon: UserCheck, primary: false,
    },
  ]
  return (
    <div className="mt-4 grid overflow-hidden rounded-xl border border-border bg-surface shadow-panel sm:grid-cols-2">
      {paths.map((p, i) => (
        <div key={p.band} className={cn('p-5', i === 0 && 'border-b border-border sm:border-b-0 sm:border-r')}>
          <div className="flex items-center justify-between">
            <span className={cn('inline-flex items-center gap-1.5 text-[12px] font-semibold uppercase tracking-wide', p.tone)}>
              <p.icon className="h-4 w-4" /> {p.band}
            </span>
            <span className="font-mono text-[20px] font-semibold text-foreground">{p.risk}%</span>
          </div>
          <p className="mt-3 text-[15px] font-semibold text-foreground">{p.title}</p>
          <p className="mt-1 text-[13px] text-muted-foreground">{p.note}</p>
          <span
            className={cn(
              'mt-4 inline-flex h-9 items-center gap-1.5 rounded-md px-3.5 text-[13px] font-semibold',
              p.primary ? 'bg-primary text-white' : 'border border-border-strong bg-surface text-foreground',
            )}
          >
            <p.ActionIcon className="h-4 w-4" /> {p.action}
          </span>
        </div>
      ))}
    </div>
  )
}

/* ---------- audit trail + before/after ---------- */

const AUDIT = [
  ['09:42:12', 'Scanner Agent', 'Document received'],
  ['09:42:15', 'OCR Agent', '38 fields extracted'],
  ['09:42:18', 'Validation Agent', 'Required fields verified'],
  ['09:42:21', 'Medical Expert', 'Clinical consistency passed'],
  ['09:42:24', 'Policy Expert', 'No blocking exception'],
  ['09:42:27', 'Risk Assessment', '24% rejection risk'],
  ['09:42:28', 'Claim Decision', 'APPROVE'],
]

function AuditTrail() {
  const [ref, inView] = useOnce()
  return (
    <div ref={ref} className="overflow-hidden rounded-xl border border-border bg-terminal">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-2.5">
        <p className="font-mono text-[11px] font-medium uppercase tracking-wider text-terminal-muted">Audit trail · claim_10482</p>
        <span className="font-mono text-[11px] text-terminal-muted">7 events</span>
      </div>
      <ol className="px-4 py-3 font-mono text-[12.5px]">
        {AUDIT.map(([t, a, m], i) => (
          <motion.li
            key={t}
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ delay: i * 0.22 }}
            className="grid grid-cols-[4.5rem_1fr] gap-x-3 py-1 sm:grid-cols-[4.5rem_9rem_1fr]"
          >
            <span className="text-terminal-muted">{t}</span>
            <span className="text-primary-border">{a}</span>
            <span className={cn('col-start-2 sm:col-start-auto', i === AUDIT.length - 1 ? 'font-semibold text-terminal-foreground' : 'text-terminal-foreground/80')}>
              {m}
            </span>
          </motion.li>
        ))}
      </ol>
    </div>
  )
}

function BeforeAfter() {
  const [ref, inView] = useOnce()
  const cols = [
    { k: 'Before', rows: ['Unreviewed claim', '38 fields', 'Unknown risk', 'Manual review', 'No decision'], tone: 'muted' },
    { k: 'ClaimBitz', rows: ['38 fields verified', '9 agents completed', '24% rejection risk', 'No blocking issues'], tone: 'copper' },
    { k: 'After', rows: ['APPROVE'], tone: 'success' },
  ]
  return (
    <div ref={ref} className="overflow-hidden rounded-xl border border-border bg-surface shadow-panel">
      {cols.map((c, i) => (
        <motion.div
          key={c.k}
          initial={{ opacity: i === 0 ? 1 : 0.25 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ delay: 0.3 + i * 0.6, duration: 0.4 }}
          className={cn('border-border px-5 py-4', i < cols.length - 1 && 'border-b', c.tone === 'success' && 'bg-success-subtle')}
        >
          <p className={cn('eyebrow', c.tone === 'copper' && '!text-accent-foreground')}>{c.k}</p>
          {c.tone === 'success' ? (
            <p className="mt-1.5 inline-flex items-center gap-2 text-[22px] font-semibold text-foreground">
              <CheckCircle2 className="h-5 w-5 text-success" /> APPROVE
            </p>
          ) : (
            <ul className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1">
              {c.rows.map((r) => (
                <li key={r} className={cn('inline-flex items-center gap-1.5 text-[13.5px]', c.tone === 'muted' ? 'text-subtle-foreground' : 'text-foreground')}>
                  {c.tone === 'muted' ? (
                    <span className="h-1.5 w-1.5 rounded-full border border-border-strong" />
                  ) : (
                    <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                  )}
                  {r}
                </li>
              ))}
            </ul>
          )}
        </motion.div>
      ))}
    </div>
  )
}

/* ---------- page ---------- */

export default function LandingPage() {
  const [mRef, mIn] = useOnce()
  return (
    <div className="min-h-screen overflow-x-hidden bg-background">
      <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1240px] items-center justify-between px-5">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-[13px] font-bold text-white">C</span>
            <span className="text-[15px] font-semibold tracking-tight text-foreground">ClaimBitz</span>
          </Link>
          <nav className="hidden items-center gap-7 md:flex">
            {[
              ['Workflow', 'how-it-works'],
              ['Claim anatomy', 'anatomy'],
              ['Decisions', 'decisions'],
              ['Audit', 'audit'],
            ].map(([l, id]) => (
              <a
                key={l}
                href={`#${id}`}
                onClick={(e) => { e.preventDefault(); document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' }) }}
                className="story-link text-[13.5px] font-medium text-muted-foreground transition-colors hover:text-foreground"
              >
                <span>{l}</span>
              </a>
            ))}
          </nav>
          <Link
            to="/dashboard"
            className="group inline-flex h-9 items-center gap-1.5 rounded-md bg-primary px-3.5 text-[13.5px] font-semibold text-white transition-colors hover:bg-primary-hover active:scale-[0.98] active:bg-primary-pressed"
          >
            Launch console
          </Link>
        </div>
      </header>

      <main>
        {/* HERO */}
        <section className="border-b border-border">
          <div className="mx-auto grid max-w-[1240px] gap-10 px-5 pb-14 pt-10 lg:grid-cols-[0.8fr_1.2fr] lg:items-center lg:pt-14">
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }}>
              <p className="eyebrow !text-accent-foreground">Read. Validate. Decide. Resolve.</p>
              <h1 className="mt-4 text-[clamp(2.3rem,3.8vw,3.4rem)] font-semibold leading-[1.05] tracking-[-0.035em] text-foreground">
                Medical claim processing, reviewed and resolved in seconds.
              </h1>
              <p className="mt-4 max-w-md text-[16px] leading-relaxed text-muted-foreground">
                ClaimBitz turns a CMS-1500 into an intelligent, explainable, and actionable claims workflow.
              </p>
              <div className="mt-6 flex flex-wrap items-center gap-3">
                <Link
                  to="/dashboard"
                  className="group inline-flex h-11 items-center gap-2 rounded-md bg-primary px-5 text-[14.5px] font-semibold text-white transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 active:scale-[0.98] active:bg-primary-pressed"
                >
                  Launch console
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-[3px]" />
                </Link>
                <a
                  href="#how-it-works"
                  onClick={(e) => { e.preventDefault(); document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' }) }}
                  className="inline-flex h-11 items-center rounded-md border border-border bg-surface px-5 text-[14.5px] font-semibold text-foreground transition-colors hover:bg-surface-muted active:scale-[0.98]"
                >
                  How it works
                </a>
              </div>

              <dl ref={mRef} className="mt-9 grid max-w-md grid-cols-3 border-t border-border pt-5">
                {[
                  { v: 27.4, d: 1, s: 's', l: 'Processing time' },
                  { v: 38, d: 0, s: '', l: 'Fields extracted' },
                  { v: 9, d: 0, s: '', l: 'Agents completed' },
                ].map((m) => (
                  <div key={m.l}>
                    <dd className="text-[24px] font-semibold tracking-tight text-foreground">
                      <CountUp to={m.v} decimals={m.d} active={mIn} />
                      {m.s}
                    </dd>
                    <dt className="mt-0.5 text-[11.5px] text-muted-foreground">{m.l}</dt>
                  </div>
                ))}
              </dl>
              <p className="mt-2 text-[11px] text-subtle-foreground">Figures from the demo claim claim_10482.</p>
            </motion.div>

            <div className="min-w-0 lg:-mr-4">
              <WorkspacePreview />
            </div>
          </div>
        </section>

        {/* WORKFLOW */}
        <section id="how-it-works" className="scroll-mt-16 border-b border-border">
          <div className="mx-auto max-w-[1240px] px-5 py-16">
            <SectionHead eyebrow="How it works" title="From claim to resolution in five stages.">
              Eight agents analyze the claim in sequence. Each stage produces evidence, findings, and a recommended action.
            </SectionHead>
            <Workflow />
          </div>
        </section>

        {/* ANATOMY */}
        <section id="anatomy" className="scroll-mt-16 border-b border-border bg-surface">
          <div className="mx-auto max-w-[1240px] px-5 py-16">
            <SectionHead eyebrow="Claim anatomy" title="Every agent reads its part of the form.">
              Hover an agent to see the regions it analyzes.
            </SectionHead>
            <ClaimAnatomy />
          </div>
        </section>

        {/* DECISIONS */}
        <section id="decisions" className="scroll-mt-16 border-b border-border">
          <div className="mx-auto max-w-[1240px] px-5 py-16">
            <SectionHead eyebrow="Evidence → decision" title="Automated when it's safe. Escalated when it isn't.">
              A recommendation is only made after the evidence is in. Claims above the threshold go to a person.
            </SectionHead>
            <EvidenceDecision />
            <ReviewPaths />
          </div>
        </section>

        {/* AUDIT + BEFORE/AFTER */}
        <section id="audit" className="scroll-mt-16 border-b border-border bg-surface">
          <div className="mx-auto max-w-[1240px] px-5 py-16">
            <SectionHead eyebrow="Auditability" title="Every step leaves a record." />
            <div className="mt-10 grid gap-5 lg:grid-cols-[1.25fr_1fr]">
              <AuditTrail />
              <BeforeAfter />
            </div>
          </div>
        </section>

        <section>
          <div className="mx-auto flex max-w-[1240px] flex-wrap items-center justify-between gap-4 px-5 py-10">
            <div className="flex items-center gap-3">
              <FileText className="h-5 w-5 text-primary" />
              <p className="text-[15px] font-semibold text-foreground">Run the demo claim through the console.</p>
            </div>
            <Link
              to="/dashboard"
              className="group inline-flex h-11 items-center gap-2 rounded-md bg-primary px-5 text-[14.5px] font-semibold text-white transition-colors hover:bg-primary-hover active:scale-[0.98]"
            >
              Launch console
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-[3px]" />
            </Link>
          </div>
          <p className="border-t border-border px-5 py-4 text-center text-[11.5px] text-subtle-foreground">
            <AlertTriangle className="mr-1 inline h-3 w-3" aria-hidden />
            Prototype · all claims, figures and outcomes shown are demo data.
          </p>
        </section>
      </main>
    </div>
  )
}
