import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, Loader2, Building2 } from 'lucide-react'
import Input from '../components/ui/Input'
import { cn } from '../lib/utils'

const insurerNameMap = {
  aetna: 'Aetna Claim Portal',
  uhc: 'UnitedHealthcare Portal',
  bcbs: 'Blue Cross Blue Shield',
}

// Preserve backward-compatible localStorage keys written elsewhere.
const LATEST_CLAIM_KEY = 'binaryblitz.latestClaim'
const LAST_APP_NUMBER_KEY = 'binaryblitz.lastApplicationNumber'

const FIELD_LABELS = {
  patientName: 'Patient name',
  policyNumber: 'Policy number',
  dob: 'Date of birth',
  provider: 'Provider',
  diagnosisCode: 'Diagnosis code',
  cptCode: 'CPT code',
  totalBilled: 'Total billed',
  approvedAmount: 'Approved amount',
  patientResponsibility: 'Patient responsibility',
  dateOfService: 'Date of service',
}

function buildApplicationNumber(prefix) {
  const rand = Math.floor(100000 + Math.random() * 900000)
  return `${prefix.toUpperCase()}-${new Date().getFullYear()}-${rand}`
}

export default function InsurerPortalPage() {
  const navigate = useNavigate()
  const { insurerId } = useParams()
  const [searchParams] = useSearchParams()
  const autoFill = searchParams.get('autofill') === '1'

  const claim = useMemo(() => {
    try {
      const raw = localStorage.getItem(LATEST_CLAIM_KEY)
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  }, [])

  const [form, setForm] = useState({
    patientName: '', policyNumber: '', dob: '', provider: '', diagnosisCode: '',
    cptCode: '', totalBilled: '', approvedAmount: '', patientResponsibility: '', dateOfService: '',
  })
  const [isFilling, setIsFilling] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [appNumber, setAppNumber] = useState('')

  useEffect(() => {
    if (!claim || !autoFill) return

    const source = claim.claimData || {}
    const steps = [
      ['patientName', source.patientName || ''],
      ['policyNumber', source.policyNumber || ''],
      ['dob', source.dob || ''],
      ['provider', source.provider || ''],
      ['diagnosisCode', source.diagnosisCode || ''],
      ['cptCode', source.cptCode || ''],
      ['totalBilled', String(source.totalBilled ?? '')],
      ['approvedAmount', String(source.approvedAmount ?? '')],
      ['patientResponsibility', String(source.patientResponsibility ?? '')],
      ['dateOfService', source.dateOfService || ''],
    ]

    let idx = 0
    setIsFilling(true)
    const timer = setInterval(() => {
      const current = steps[idx]
      if (!current) {
        clearInterval(timer)
        setIsFilling(false)
        setIsComplete(true)
        const applicationNo = buildApplicationNumber(insurerId || 'ins')
        setAppNumber(applicationNo)
        localStorage.setItem(LAST_APP_NUMBER_KEY, applicationNo)
        return
      }
      setForm((prev) => ({ ...prev, [current[0]]: current[1] }))
      idx += 1
    }, 260)

    return () => clearInterval(timer)
  }, [claim, autoFill, insurerId])

  const statusLabel = isFilling ? 'Auto-filling…' : isComplete ? 'Ready to submit' : 'Ready'
  const statusTone = isFilling ? 'bg-primary-subtle text-accent-foreground' : isComplete ? 'bg-success-subtle text-success' : 'bg-surface-muted text-muted-foreground'

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-4xl items-center justify-between gap-3 px-5 lg:px-8">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary-subtle">
              <Building2 className="h-5 w-5 text-primary" />
            </span>
            <div>
              <h1 className="text-[15px] font-semibold leading-tight tracking-tight text-foreground">
                {insurerNameMap[insurerId] || 'Insurer Portal'}
              </h1>
              <p className="text-xs text-muted-foreground">Provider claim intake</p>
            </div>
          </div>
          <span className={cn('inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-semibold', statusTone)}>
            {isFilling ? <Loader2 className="h-3 w-3 motion-safe:animate-spin" /> : isComplete ? <CheckCircle2 className="h-3 w-3" /> : null}
            {statusLabel}
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-5 px-5 py-6 lg:px-8">
        <button
          onClick={() => navigate('/submission')}
          className="inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring cursor-pointer"
        >
          <ArrowLeft className="h-4 w-4" /> Back to submission
        </button>

        {!claim && (
          <div className="flex items-start gap-3 rounded-md border border-warning/30 bg-warning-subtle px-4 py-3" role="alert">
            <div>
              <p className="text-sm font-semibold text-warning">No claim snapshot found</p>
              <p className="mt-0.5 text-sm text-warning/90">Process a claim first, then reopen this portal to auto-fill.</p>
            </div>
          </div>
        )}

        {claim && (
          <section className="panel p-5 sm:p-6">
            <h2 className="text-[15px] font-semibold text-foreground">Claim application form</h2>
            <p className="mt-0.5 text-[13px] text-muted-foreground">Fields auto-populated from extracted claim data</p>

            <form className="mt-5 grid gap-4 sm:grid-cols-2" onSubmit={(e) => e.preventDefault()}>
              {Object.keys(form).map((key) => (
                <Input key={key} label={FIELD_LABELS[key] || key} value={form[key]} readOnly placeholder="—" />
              ))}
            </form>
          </section>
        )}

        {/* Status bar */}
        <section className="panel flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {isFilling ? (
              <Loader2 className="h-4 w-4 text-primary motion-safe:animate-spin" />
            ) : (
              <CheckCircle2 className={cn('h-4 w-4', isComplete ? 'text-success' : 'text-subtle-foreground')} />
            )}
            {isFilling ? 'Agent is auto-filling the portal form…' : isComplete ? 'Form prepared — review fields, then submit manually through the portal' : 'Ready to auto-fill'}
          </div>
          {isComplete && (
            <div className="rounded-md border border-success/30 bg-success-subtle px-3 py-1.5 text-sm font-semibold text-success">
              Reference #: {appNumber}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
