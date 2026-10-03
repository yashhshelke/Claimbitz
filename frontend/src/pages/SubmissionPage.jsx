import React, { useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, ExternalLink, ClipboardCheck, Building2 } from 'lucide-react'
import { cn } from '../lib/utils'

const INSURERS = [
  { id: 'aetna', name: 'Aetna Claim Portal', tagline: 'Enterprise provider workflow' },
  { id: 'uhc', name: 'UnitedHealthcare Portal', tagline: 'Fast adjudication pipeline' },
  { id: 'bcbs', name: 'Blue Cross Blue Shield', tagline: 'Standardized CMS-style intake' },
]

// Preserve backward-compatible localStorage key written by useClaimAgent.
const LATEST_CLAIM_KEY = 'binaryblitz.latestClaim'

export default function SubmissionPage() {
  const navigate = useNavigate()

  const claimSnapshot = useMemo(() => {
    try {
      const raw = localStorage.getItem(LATEST_CLAIM_KEY)
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  }, [])

  const openPortal = (insurerId) => {
    const url = `/portal/${insurerId}?autofill=1`
    const popup = window.open(url, '_blank', 'noopener,noreferrer')
    if (!popup) navigate(url)
  }

  const riskLabel = claimSnapshot?.riskLabel
  const riskTone =
    riskLabel === 'HIGH' ? 'bg-destructive/10 text-destructive' :
    riskLabel === 'MEDIUM' ? 'bg-warning-subtle text-warning' :
    'bg-success-subtle text-success'

  const summary = claimSnapshot
    ? [
        ['Patient', claimSnapshot.claimData?.patientName || '—'],
        ['Policy number', claimSnapshot.claimData?.policyNumber || '—'],
        ['Provider', claimSnapshot.claimData?.provider || '—'],
      ]
    : []

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1240px] items-center gap-3 px-5">
          <button
            onClick={() => navigate('/dashboard')}
            aria-label="Back to dashboard"
            className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-surface-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring cursor-pointer"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <Link to="/" className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary text-[13px] font-bold text-white" aria-label="ClaimBitz home">
            C
          </Link>
          <div className="min-w-0">
            <h1 className="text-[15px] font-semibold leading-tight tracking-tight text-foreground">Claim submission</h1>
            <p className="hidden text-xs text-muted-foreground sm:block">Route the processed claim to an insurer portal</p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1240px] space-y-6 px-5 py-6">
        {/* Claim snapshot */}
        <section className="panel p-5">
          <div className="flex items-start gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-primary-subtle">
              <ClipboardCheck className="h-[18px] w-[18px] text-primary" />
            </span>
            <div className="min-w-0">
              <h2 className="text-[15px] font-semibold text-foreground">Claim ready for submission</h2>
              <p className="mt-0.5 text-[13px] text-muted-foreground">Extracted from the most recently processed document</p>
            </div>
          </div>

          {!claimSnapshot ? (
            <div className="mt-4 flex items-start gap-3 rounded-md border border-warning/30 bg-warning-subtle px-4 py-3" role="alert">
              <div>
                <p className="text-sm font-semibold text-warning">No processed claim found</p>
                <p className="mt-0.5 text-sm text-warning/90">Process a document on the dashboard first, then return here to submit.</p>
              </div>
            </div>
          ) : (
            <dl className="mt-4 grid gap-x-8 sm:grid-cols-2">
              {summary.map(([label, value]) => (
                <div key={label} className="flex items-center justify-between gap-4 border-b border-border py-2.5">
                  <dt className="text-[13px] text-muted-foreground">{label}</dt>
                  <dd className="text-[13px] font-medium text-foreground">{value}</dd>
                </div>
              ))}
              <div className="flex items-center justify-between gap-4 border-b border-border py-2.5">
                <dt className="text-[13px] text-muted-foreground">Risk</dt>
                <dd>
                  <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold', riskTone)}>
                    {Math.round((claimSnapshot.riskScore || 0) * 100)}% · {claimSnapshot.riskLabel}
                  </span>
                </dd>
              </div>
            </dl>
          )}
        </section>

        {/* Insurer selection */}
        <div>
          <p className="eyebrow mb-3">Select insurer portal</p>
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {INSURERS.map((insurer) => (
              <div key={insurer.id} className="panel flex flex-col p-5 transition-colors hover:border-primary-border">
                <div className="flex items-start justify-between">
                  <span className="flex h-10 w-10 items-center justify-center rounded-md bg-primary-subtle">
                    <Building2 className="h-5 w-5 text-primary" />
                  </span>
                  <span
                    className={cn(
                      'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold',
                      claimSnapshot ? 'bg-success-subtle text-success' : 'bg-surface-muted text-muted-foreground',
                    )}
                  >
                    {claimSnapshot ? 'Ready' : 'No claim'}
                  </span>
                </div>
                <h3 className="mt-4 text-base font-semibold text-foreground">{insurer.name}</h3>
                <p className="mt-0.5 text-sm text-muted-foreground">{insurer.tagline}</p>
                <p className="mt-3 flex-1 text-xs leading-relaxed text-subtle-foreground">
                  Opens the portal and auto-fills fields from the processed claim. You submit manually from within the portal.
                </p>
                <button
                  disabled={!claimSnapshot}
                  onClick={() => openPortal(insurer.id)}
                  className="mt-4 inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-semibold text-white transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <ExternalLink className="h-4 w-4" />
                  Open &amp; auto-fill
                </button>
              </div>
            ))}
          </div>
        </div>

        <p className="text-xs text-subtle-foreground">
          Submission data comes from the local snapshot saved after the latest processed document.
        </p>
      </main>
    </div>
  )
}
