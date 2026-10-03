import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { FilePlus2, Minus, Plus, Upload } from 'lucide-react'
import { cn } from '../../lib/utils'

/**
 * Faithful port of Lovable's DocumentViewer / CMS1500 presentation, bound to the
 * real backend-extracted claim (results.claimData). No claim value is hardcoded —
 * fields absent from the real extraction render as em dashes.
 *
 * `focus` (document regions the active agent is reading) and `focusLabel` are
 * presentation-only, derived in the Dashboard from the REAL current agent. They
 * drive the highlight micro-interaction; they never fabricate claim data.
 */

function fmtDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  return `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}/${d.getFullYear()}`
}

function fmtMoney(v) {
  return typeof v === 'number'
    ? `₹${v.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : '—'
}

function Field({ label, value, className }) {
  return (
    <div className={cn('border-r border-b border-border px-2.5 py-1.5 last:border-r-0', className)}>
      <p className="text-[10.5px] font-semibold uppercase tracking-wide text-subtle-foreground">{label}</p>
      <p className="mt-0.5 text-[13px] font-medium text-foreground">{value ?? '—'}</p>
    </div>
  )
}

/* Region focus overlay — highlights the part of the form the active agent reads. */
function Region({ id, focus, label, children }) {
  const on = focus.includes(id)
  return (
    <div className="relative">
      <motion.div
        aria-hidden
        className="pointer-events-none absolute inset-0 z-10 border-l-2 border-primary bg-primary-subtle/50"
        initial={false}
        animate={{ opacity: on ? 1 : 0 }}
        transition={{ duration: 0.35, ease: 'easeOut' }}
      />
      {on && label && (
        <motion.span
          initial={{ opacity: 0, y: -2 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute right-2 top-1.5 z-20 rounded border border-primary-border bg-surface px-1.5 py-0.5 text-[10.5px] font-semibold text-accent-foreground"
        >
          {label}
        </motion.span>
      )}
      <div className={cn('transition-opacity duration-300', focus.length > 0 && !on && 'opacity-70')}>
        {children}
      </div>
    </div>
  )
}

function CMS1500({ claim, scanning = false, focus = [], focusLabel }) {
  const c = claim || {}
  const dx = c.diagnosisCode || null
  const cpt = c.cptCode || null
  const billed = fmtMoney(c.totalBilled)
  const R = (id, children) => (
    <Region id={id} focus={focus} label={focusLabel}>
      {children}
    </Region>
  )

  return (
    <div className="relative overflow-hidden rounded-[6px] border border-border-strong bg-[color-mix(in_oklab,var(--color-surface)_96%,var(--color-primary-subtle))] shadow-paper ring-1 ring-foreground/[0.03]">
      {scanning && (
        <motion.div
          className="pointer-events-none absolute inset-x-0 z-30 h-10 -translate-y-full"
          initial={{ top: '0%' }}
          animate={{ top: ['0%', '100%'] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          aria-hidden="true"
        >
          <div className="h-full bg-gradient-to-b from-transparent to-primary-subtle/70" />
          <div className="h-px bg-primary/70" />
        </motion.div>
      )}

      <div className="flex items-center justify-between border-b border-border-strong bg-surface-muted px-4 py-3">
        <div>
          <p className="text-[13px] font-semibold tracking-tight text-foreground">HEALTH INSURANCE CLAIM FORM</p>
          <p className="text-[11px] text-muted-foreground">Approved by National Uniform Claim Committee · CMS-1500 (02/12)</p>
        </div>
        <p className="text-[11px] font-medium text-muted-foreground">PICA</p>
      </div>

      {R('insurance', (
        <>
          <div className="border-b border-border px-4 py-2">
            <p className="eyebrow">Insurance</p>
          </div>
          <div className="grid grid-cols-2 border-b border-border md:grid-cols-3">
            <Field label="1a. Insured ID no." value={c.policyNumber} />
            <Field label="11. Group no." value={c.groupNumber} />
            <Field label="Plan type" value={c.planType} />
          </div>
        </>
      ))}

      {R('patient', (
        <>
          <div className="border-b border-border px-4 py-2">
            <p className="eyebrow">Patient &amp; insured</p>
          </div>
          <div className="grid grid-cols-2 border-b border-border md:grid-cols-4">
            <Field label="2. Patient name" value={c.patientName} />
            <Field label="3. Birth date" value={c.dob ? fmtDate(c.dob) : undefined} />
            <Field label="6. Relationship" value={c.relationship} />
            <Field label="12. Signature" value={c.signature} />
          </div>
        </>
      ))}

      {R('provider', (
        <>
          <div className="border-b border-border px-4 py-2">
            <p className="eyebrow">Provider</p>
          </div>
          <div className="grid grid-cols-2 border-b border-border md:grid-cols-4">
            <Field label="33. Billing provider" value={c.provider} />
            <Field label="33a. NPI" value={c.providerNpi} />
            <Field label="32. Facility" value={c.provider} />
            <Field label="17. Referring" value={c.referringProvider} />
          </div>
        </>
      ))}

      {R('diagnosis', (
        <>
          <div className="border-b border-border px-4 py-2">
            <p className="eyebrow">21. Diagnosis or nature of illness (ICD-10-CM)</p>
          </div>
          <div className="grid grid-cols-2 border-b border-border md:grid-cols-4">
            <Field label="A." value={dx || undefined} />
            <Field label="B." value={undefined} />
            <Field label="C." value={undefined} />
            <Field label="D." value={undefined} />
          </div>
        </>
      ))}

      {R('services', (
        <>
          <div className="border-b border-border px-4 py-2">
            <p className="eyebrow">24. Service lines</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] border-collapse text-[12.5px]">
              <thead>
                <tr className="bg-surface-muted text-left text-[10.5px] uppercase tracking-wide text-subtle-foreground">
                  <th className="border-b border-border px-2.5 py-2 font-semibold">Date(s)</th>
                  <th className="border-b border-border px-2.5 py-2 font-semibold">POS</th>
                  <th className="border-b border-border px-2.5 py-2 font-semibold">CPT/HCPCS</th>
                  <th className="border-b border-border px-2.5 py-2 font-semibold">Mod</th>
                  <th className="border-b border-border px-2.5 py-2 font-semibold">Dx ptr</th>
                  <th className="border-b border-border px-2.5 py-2 font-semibold">Units</th>
                  <th className="border-b border-border px-2.5 py-2 text-right font-semibold">Charges</th>
                </tr>
              </thead>
              <tbody className="text-foreground">
                <tr className="border-b border-border last:border-b-0">
                  <td className="px-2.5 py-2 tabular-nums">{fmtDate(c.dateOfService)}</td>
                  <td className="px-2.5 py-2 tabular-nums">{c.placeOfService || '—'}</td>
                  <td className="px-2.5 py-2 font-medium tabular-nums">{cpt || '—'}</td>
                  <td className="px-2.5 py-2 tabular-nums">{c.modifier || '—'}</td>
                  <td className="px-2.5 py-2 tabular-nums">{dx ? 'A' : '—'}</td>
                  <td className="px-2.5 py-2 tabular-nums">{c.units || '—'}</td>
                  <td className="px-2.5 py-2 text-right font-medium tabular-nums">{billed}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      ))}

      {R('totals', (
        <div className="grid grid-cols-2 border-t border-border md:grid-cols-4">
          <Field label="28. Total charge" value={billed !== '—' ? billed : undefined} />
          <Field label="29. Amount paid" value={fmtMoney(c.approvedAmount) !== '—' ? fmtMoney(c.approvedAmount) : undefined} />
          <Field label="Patient resp." value={fmtMoney(c.patientResponsibility) !== '—' ? fmtMoney(c.patientResponsibility) : undefined} />
          <Field label="Date of service" value={c.dateOfService ? fmtDate(c.dateOfService) : undefined} />
        </div>
      ))}
    </div>
  )
}

export function DashboardDocumentViewer({
  fileName,
  hasDocument,
  claim,
  scanning = false,
  focus = [],
  focusLabel,
  statusText,
  onBrowse,
  onNewClaim,
  onDrop,
}) {
  const [zoom, setZoom] = useState(100)
  const [drag, setDrag] = useState(false)

  if (!hasDocument) {
    return (
      <section className="panel overflow-hidden">
        <header className="border-b border-border px-5 py-3.5">
          <h2 className="text-[19px] font-semibold text-foreground">Claim document</h2>
          <p className="mt-0.5 text-[13px] text-muted-foreground">Upload a CMS-1500 claim to begin</p>
        </header>
        <div
          className={cn(
            'flex min-h-[360px] flex-col items-center justify-center px-6 py-12 text-center transition-colors',
            drag && 'bg-primary-subtle',
          )}
          onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); onDrop?.(e) }}
        >
          <span className={cn('flex h-12 w-12 items-center justify-center rounded-lg', drag ? 'bg-primary-subtle' : 'bg-surface-muted')}>
            <Upload className={cn('h-6 w-6', drag ? 'text-primary' : 'text-subtle-foreground')} />
          </span>
          <h3 className="mt-5 text-[17px] font-semibold text-foreground">Drop a CMS-1500 claim here</h3>
          <p className="mt-1 text-[13.5px] text-muted-foreground">PDF, PNG, JPG or JPEG supported</p>
          <button
            onClick={onBrowse}
            className="mt-5 inline-flex h-11 items-center gap-2 rounded-md bg-primary px-5 text-[14px] font-semibold text-white transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 active:scale-[0.98]"
          >
            Browse files
          </button>
        </div>
      </section>
    )
  }

  return (
    <section className="panel overflow-hidden">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-3.5">
        <div className="min-w-0">
          <h2 className="text-[19px] font-semibold text-foreground">Claim document</h2>
          <p className="mt-0.5 truncate text-[13px] text-muted-foreground">
            {fileName} · {statusText}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center rounded-md border border-border bg-surface-muted">
            <button
              onClick={() => setZoom((z) => Math.max(70, z - 10))}
              className="flex h-9 w-9 items-center justify-center text-muted-foreground transition-colors hover:text-foreground"
              aria-label="Zoom out"
            >
              <Minus className="h-4 w-4" />
            </button>
            <span className="w-12 text-center text-xs font-medium tabular-nums text-foreground">{zoom}%</span>
            <button
              onClick={() => setZoom((z) => Math.min(130, z + 10))}
              className="flex h-9 w-9 items-center justify-center text-muted-foreground transition-colors hover:text-foreground"
              aria-label="Zoom in"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>
          <button
            onClick={onNewClaim}
            className="inline-flex h-9 items-center whitespace-nowrap gap-1.5 rounded-md border border-border px-3 text-[13px] font-medium text-foreground transition-colors hover:bg-surface-muted"
          >
            <FilePlus2 className="h-4 w-4 text-muted-foreground" />
            New claim
          </button>
        </div>
      </header>

      <div className="max-h-[560px] overflow-auto bg-background p-4 sm:p-6">
        <div className="origin-top transition-transform" style={{ transform: `scale(${zoom / 100})` }}>
          <CMS1500 claim={claim} scanning={scanning} focus={focus} focusLabel={focusLabel} />
        </div>
      </div>

      <footer className="flex items-center justify-between border-t border-border px-5 py-2.5 text-xs text-muted-foreground">
        <span>{claim ? 'Extracted from source document' : 'Awaiting analysis'}</span>
        <span className="tabular-nums">{fileName}</span>
      </footer>
    </section>
  )
}
