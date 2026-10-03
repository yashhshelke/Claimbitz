import { useState, useCallback, useRef } from 'react'

const AGENT_STEPS = [
  { id: 'scanner', name: 'Scanner Agent', description: 'Validating document format and quality', icon: 'ScanLine' },
  { id: 'ocr', name: 'OCR Agent', description: 'Extracting structured fields from document', icon: 'ScanLine' },
  { id: 'validator', name: 'Validator Agent', description: 'Checking data consistency & format', icon: 'ShieldCheck' },
  { id: 'medical', name: 'Medical Expert', description: 'Assessing clinical plausibility (ICD/CPT)', icon: 'Activity' },
  { id: 'policy', name: 'Policy Expert', description: 'Checking coverage rules & exclusions', icon: 'ShieldCheck' },
  { id: 'fraud', name: 'Fraud Detection', description: 'Analyzing fraud patterns & duplicates', icon: 'Activity' },
  { id: 'risk', name: 'Risk Assessment', description: 'Computing risk score & category', icon: 'Activity' },
  { id: 'comm', name: 'Communication', description: 'Drafting policyholder messages', icon: 'MessageSquare' },
]

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const LATEST_CLAIM_KEY = 'binaryblitz.latestClaim'

export function useClaimAgent() {
  const [demoMode, setDemoMode] = useState(false)
  const [demoScenario, setDemoScenario] = useState('low') // 'low' | 'medium' | 'high'
  const [agents, setAgents] = useState(
    AGENT_STEPS.map(a => ({
      ...a,
      status: 'idle', // idle | processing | completed | error
      logs: [],
    }))
  )
  const [currentStep, setCurrentStep] = useState(-1)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isComplete, setIsComplete] = useState(false)
  const [results, setResults] = useState(null)
  const [riskScore, setRiskScore] = useState(0)
  const [errorMessage, setErrorMessage] = useState('')
  const [terminalLogs, setTerminalLogs] = useState([])
  const [uploadedFile, setUploadedFile] = useState(null)
  const [resolutionStatus, setResolutionStatus] = useState(null)
  // null | 'analyzed' | 'action_required' | 'awaiting_review' | 'ready_to_submit'
  const [actionLog, setActionLog] = useState([])
  const abortRef = useRef(false)

  const persistClaim = useCallback((payload, sourceFileName) => {
    const toStore = {
      savedAt: new Date().toISOString(),
      sourceFileName: sourceFileName || 'demo-claim.pdf',
      claimData: payload.claimData,
      riskScore: payload.riskScore,
      riskLabel: payload.riskLabel,
      recommendation: payload.recommendation,
      riskReasons: payload.riskReasons || [],
      extractionIssues: payload.extractionIssues || [],
      extractionTextPreview: payload.extractionTextPreview || '',
      riskModel: payload.riskModel || null,
      email: payload.email,
      whatsapp: payload.whatsapp,
    }
    localStorage.setItem(LATEST_CLAIM_KEY, JSON.stringify(toStore))
  }, [])

  const addTerminalLog = useCallback((log) => {
    setTerminalLogs(prev => [...prev, { text: log, timestamp: new Date().toLocaleTimeString() }])
  }, [])

  const logAction = useCallback((action, detail) => {
    const ts = new Date().toLocaleTimeString()
    setActionLog(prev => [...prev, { action, detail: detail || '', timestamp: ts }])
    setTerminalLogs(prev => [...prev, { text: `[ACTION] ${action}${detail ? ' — ' + detail : ''}`, timestamp: ts }])
  }, [])

  const getDemoPayload = useCallback(() => {
    const base = {
      claimData: {
        patientName: 'Rahul Sharma',
        dob: '1985-03-14',
        policyNumber: 'SH-IND-884512',
        diagnosisCode: 'J18.9',
        diagnosisDesc: 'Pneumonia, unspecified organism',
        cptCode: '99213',
        provider: 'APOLLO SPECIALITY HOSPITAL',
        totalBilled: 145000,
        approvedAmount: 123250,
        patientResponsibility: 21750,
        dateOfService: '2026-04-10',
      },
      extractionIssues: [],
      extractionTextPreview: 'Demo claim text preview',
    }
    if (demoScenario === 'high') {
      return {
        ...base,
        riskScore: 0.42,
        riskLabel: 'HIGH',
        recommendation: 'REVIEW',
        riskReasons: ['Modifier 25 usage flagged', 'Billing frequency above expected range', 'Policy match is partial'],
        riskModel: { baseScore: 0.2, maxIssuePenalty: 0.5, issuePenaltyPerItem: 0.1, thresholds: { lowMax: 0.3, mediumMax: 0.6, highMax: 1.0 }, contributions: [{ rule: 'modifier_25_flag', delta: 0.12, reason: 'Modifier 25 flagged for review' }, { rule: 'billing_frequency', delta: 0.1, reason: 'Billing frequency above expected range' }] },
        findings: [{ agent: 'medical_expert', verdict: 'flag', confidence: 0.72, reasoning: 'Modifier 25 usage on E&M with bundled procedure — requires review' }, { agent: 'fraud_detection', verdict: 'flag', confidence: 0.65, reasoning: 'Billing frequency above expected 180-day range for this subscriber/provider pair' }, { agent: 'policy_expert', verdict: 'flag', confidence: 0.78, reasoning: 'Partial policy match — coverage exception possible' }],
        email: `Subject: Claim Review Required — Policy #SH-IND-884512\n\nDear Policyholder,\n\nYour medical claim requires additional review.\n\nDecision: HUMAN REVIEW\nRisk Level: HIGH (42%)\nBilled Amount: ₹1,45,000.00\n\nA reviewer will contact you within 2 business days.\n\nBest regards,\nClaimBitz Claim Agent`,
        whatsapp: 'Claim Status Update\\n\\nProvider: APOLLO SPECIALITY HOSPITAL\\nDiagnosis: J18.9\\nBilled: ₹1,45,000.00\\nDecision: HUMAN REVIEW (HIGH)\\nRisk Score: 0.42\\n\\nA reviewer will be in touch.',
      }
    }
    if (demoScenario === 'medium') {
      return {
        ...base,
        riskScore: 0.45,
        riskLabel: 'MEDIUM',
        recommendation: 'REVIEW',
        riskReasons: ['Slight diagnosis-procedure mismatch', 'Provider billing pattern under monitoring'],
        riskModel: { baseScore: 0.15, maxIssuePenalty: 0.4, issuePenaltyPerItem: 0.08, thresholds: { lowMax: 0.3, mediumMax: 0.6, highMax: 1.0 }, contributions: [{ rule: 'dx_procedure_mismatch', delta: 0.18, reason: 'Slight diagnosis-procedure mismatch detected' }, { rule: 'provider_monitoring', delta: 0.12, reason: 'Provider billing pattern under monitoring' }] },
        findings: [{ agent: 'medical_expert', verdict: 'flag', confidence: 0.80, reasoning: 'Diagnosis J18.9 and CPT 99213 — plausible but warrants review' }, { agent: 'fraud_detection', verdict: 'approve', confidence: 0.85, reasoning: 'No significant anomalies detected' }, { agent: 'risk_assessment', verdict: 'flag', confidence: 0.75, reasoning: 'Medium risk — manual review recommended' }],
        email: `Subject: Claim Under Review — Policy #SH-IND-884512\n\nDear Policyholder,\n\nYour medical claim is under review.\n\nDecision: REVIEW\nRisk Level: MEDIUM (45%)\nApproved Amount: Pending\n\nBest regards,\nClaimBitz Claim Agent`,
        whatsapp: 'Claim Status Update\\n\\nProvider: APOLLO SPECIALITY HOSPITAL\\nDiagnosis: J18.9\\nBilled: ₹1,45,000.00\\nDecision: REVIEW (MEDIUM)\\nRisk Score: 0.45',
      }
    }
    // low (default)
    return {
      ...base,
      riskScore: 0.24,
      riskLabel: 'LOW',
      recommendation: 'APPROVE',
      riskReasons: ['No major anomalies detected', 'Provider is in-network', 'Valid ICD and CPT format'],
      riskModel: { baseScore: 0.1, maxIssuePenalty: 0.3, issuePenaltyPerItem: 0.06, thresholds: { lowMax: 0.3, mediumMax: 0.6, highMax: 1.0 }, contributions: [{ rule: 'slight_approval_variance', delta: 0.1, reason: 'Slight variance between approved and billed amount' }, { rule: 'provider_in_network_bonus', delta: 0.04, reason: 'Provider appears in network reference list' }] },
      findings: [{ agent: 'scanner', verdict: 'approve', confidence: 0.95, reasoning: 'Document format valid, all pages readable' }, { agent: 'validator', verdict: 'approve', confidence: 0.92, reasoning: 'Required fields present, formats consistent' }, { agent: 'medical_expert', verdict: 'approve', confidence: 0.88, reasoning: 'Diagnosis J18.9 consistent with CPT 99213' }],
      email: `Subject: Claim Review Update — Policy #SH-IND-884512\n\nDear Policyholder,\n\nYour medical claim has been processed successfully.\n\nDecision: APPROVE\nRisk Level: LOW\nApproved Amount: ₹1,23,250.00\nPatient Responsibility: ₹21,750.00\n\nBest regards,\nClaimBitz Claim Agent`,
      whatsapp: 'Claim Status Update\\n\\nProvider: APOLLO SPECIALITY HOSPITAL\\nDiagnosis: J18.9\\nApproved: ₹1,23,250.00\\nYour Cost: ₹21,750.00\\nDecision: APPROVE (LOW)\\nRisk Score: 0.24',
    }
  }, [demoScenario])

  /**
   * Per-agent demo log messages — scenario-specific activity and result text
   * for the sequential 8-agent demo flow. Indices match AGENT_STEPS exactly.
   */
  const getDemoAgentLogs = useCallback(() => {
    const low = [
      { activity: 'Scanning document structure…', level: 'SUCCESS', result: 'Document format valid, 2 pages detected' },
      { activity: 'Extracting structured fields from CMS-1500…', level: 'SUCCESS', result: 'Extracted claim fields from document' },
      { activity: 'Validating data consistency and format…', level: 'SUCCESS', result: 'Required fields present, formats consistent' },
      { activity: 'Assessing clinical plausibility (ICD/CPT)…', level: 'SUCCESS', result: 'Diagnosis J18.9 consistent with CPT 99213' },
      { activity: 'Checking coverage rules and exclusions…', level: 'SUCCESS', result: 'No blocking policy exceptions found' },
      { activity: 'Analyzing fraud patterns and duplicates…', level: 'SUCCESS', result: 'No anomalies detected' },
      { activity: 'Computing risk score and category…', level: 'DATA', result: 'Risk scored at 24% — LOW' },
      { activity: 'Drafting policyholder messages…', level: 'SUCCESS', result: 'Payer response and notifications drafted' },
    ]
    const medium = [
      { activity: 'Scanning document structure…', level: 'SUCCESS', result: 'Document format valid, 2 pages detected' },
      { activity: 'Extracting structured fields from CMS-1500…', level: 'SUCCESS', result: 'Extracted claim fields from document' },
      { activity: 'Validating data consistency and format…', level: 'SUCCESS', result: 'Required fields present, minor date variance noted' },
      { activity: 'Assessing clinical plausibility (ICD/CPT)…', level: 'WARN', result: 'Slight diagnosis-procedure mismatch — review recommended' },
      { activity: 'Checking coverage rules and exclusions…', level: 'SUCCESS', result: 'Coverage confirmed with monitoring flag' },
      { activity: 'Analyzing fraud patterns and duplicates…', level: 'SUCCESS', result: 'No significant anomalies detected' },
      { activity: 'Computing risk score and category…', level: 'DATA', result: 'Risk scored at 45% — MEDIUM' },
      { activity: 'Drafting policyholder messages…', level: 'SUCCESS', result: 'Review notification drafted' },
    ]
    const high = [
      { activity: 'Scanning document structure…', level: 'SUCCESS', result: 'Document format valid, 2 pages detected' },
      { activity: 'Extracting structured fields from CMS-1500…', level: 'SUCCESS', result: 'Extracted claim fields from document' },
      { activity: 'Validating data consistency and format…', level: 'SUCCESS', result: 'Required fields present, formats consistent' },
      { activity: 'Assessing clinical plausibility (ICD/CPT)…', level: 'WARN', result: 'Modifier 25 usage flagged — bundled procedure concern' },
      { activity: 'Checking coverage rules and exclusions…', level: 'WARN', result: 'Partial policy match — coverage exception possible' },
      { activity: 'Analyzing fraud patterns and duplicates…', level: 'WARN', result: 'Billing frequency above expected range for subscriber' },
      { activity: 'Computing risk score and category…', level: 'DATA', result: 'Risk scored at 42% — HIGH' },
      { activity: 'Drafting policyholder messages…', level: 'SUCCESS', result: 'Human review notification drafted' },
    ]
    return demoScenario === 'high' ? high : demoScenario === 'medium' ? medium : low
  }, [demoScenario])

  const processReal = useCallback(async () => {
    if (!uploadedFile && !demoMode) {
      addTerminalLog('[ERROR] Please upload a claim document first')
      setErrorMessage('Please upload a claim document before processing.')
      return
    }

    let activeStep = 0
    const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms))
    const markProcessing = (index, log) => {
      activeStep = index
      setCurrentStep(index)
      setAgents(prev => prev.map((a, i) => (
        i < index ? { ...a, status: 'completed' }
          : i === index ? { ...a, status: 'processing' }
          : { ...a, status: 'idle' }
      )))
      addTerminalLog(log)
    }

    const markCompleted = (index, log) => {
      setAgents(prev => prev.map((a, i) => (
        i === index ? { ...a, status: 'completed' } : a
      )))
      addTerminalLog(log)
    }

    const markFailed = (index, log) => {
      setAgents(prev => prev.map((a, i) => (
        i === index ? { ...a, status: 'error' } : a
      )))
      addTerminalLog(log)
    }

    abortRef.current = false
    setIsProcessing(true)
    setIsComplete(false)
    setResults(null)
    setRiskScore(0)
    setErrorMessage('')
    setTerminalLogs([])
    setAgents(AGENT_STEPS.map(a => ({ ...a, status: 'idle', logs: [] })))
    setCurrentStep(-1)

    addTerminalLog('[SYSTEM] ClaimBitz Agent Pipeline — INITIALIZING')
    addTerminalLog(`[SYSTEM] Connected to backend: ${API_BASE_URL}`)
    addTerminalLog('─'.repeat(50))

    try {
      markProcessing(0, demoMode && !uploadedFile
        ? `[INFO] Scanner Agent: Starting ${demoScenario.toUpperCase()} risk demo analysis…`
        : '[INFO] Scanner Agent: Uploading and processing claim through 8-agent pipeline...')

      let data
      if (demoMode && !uploadedFile) {
        // Demo: execute through all 8 agents sequentially
        const demoLogs = getDemoAgentLogs()
        for (let i = 0; i < AGENT_STEPS.length; i++) {
          if (abortRef.current) return
          markProcessing(i, `[INFO] ${AGENT_STEPS[i].name}: ${demoLogs[i].activity}`)
          await wait(600 + Math.random() * 400) // 600-1000ms per agent
          markCompleted(i, `[${demoLogs[i].level}] ${AGENT_STEPS[i].name}: ${demoLogs[i].result}`)
          await wait(150)
        }
        data = getDemoPayload()
      } else {
        const formData = new FormData()
        formData.append('file', uploadedFile)

        // Start animating agent steps while backend processes
        const stepAnimator = setInterval(() => {
          setAgents(prev => {
            const nextIdle = prev.findIndex(a => a.status === 'idle')
            if (nextIdle > 0 && nextIdle < prev.length) {
              return prev.map((a, i) => {
                if (i < nextIdle) return { ...a, status: 'completed' }
                if (i === nextIdle) return { ...a, status: 'processing' }
                return a
              })
            }
            return prev
          })
          setCurrentStep(prev => Math.min(prev + 1, AGENT_STEPS.length - 2))
        }, 2500)

        const response = await fetch(`${API_BASE_URL}/process`, {
          method: 'POST',
          body: formData,
        })

        clearInterval(stepAnimator)

        if (!response.ok) {
          const err = await response.json().catch(() => ({}))
          throw new Error(err.detail || 'Backend processing failed')
        }

        data = await response.json()
        markCompleted(0, `[SUCCESS] Pipeline complete: ${data.findings?.length || 0} agents contributed`)
      }

      addTerminalLog('[AGENT] Pipeline: All agents processed claim data')
      await wait(100)

      // Show agent findings in terminal
      if (data.findings) {
        for (const f of data.findings) {
          addTerminalLog(`[${f.verdict === 'approve' ? 'SUCCESS' : f.verdict === 'reject' ? 'WARN' : 'DATA'}] ${f.agent}: ${f.verdict.toUpperCase()} (conf=${f.confidence?.toFixed(2)}) — ${f.reasoning?.slice(0, 60) || ''}`)
        }
      }

      // Mark all agents complete
      setAgents(AGENT_STEPS.map((a) => ({ ...a, status: 'completed', logs: [] })))
      setCurrentStep(AGENT_STEPS.length - 1)

      setResults(data)
      persistClaim(data, uploadedFile?.name)
      setRiskScore(data.riskScore ?? 0)
      addTerminalLog(`[DATA] Recommendation: ${data.recommendation} | Risk: ${data.riskLabel} (${data.riskScore})`)
      addTerminalLog(`[SYSTEM] Decision Steps: ${data.decisionSteps || '?'} | Stage: ${data.stage || 'completed'}`)
      addTerminalLog('[SYSTEM] ALL AGENTS COMPLETE — Claim processing finished')
      setIsComplete(true)

      // Derive resolution status from risk level
      const rl = (data.riskLabel || '').toUpperCase()
      if (rl === 'LOW') setResolutionStatus('ready_to_submit')
      else if (rl === 'MEDIUM') setResolutionStatus('action_required')
      else if (rl === 'HIGH') setResolutionStatus('awaiting_review')
      else setResolutionStatus('analyzed')
    } catch (error) {
      console.error('Process failed:', error)
      setErrorMessage(error.message || 'Failed to process claim. Please try again.')
      markFailed(activeStep, `[ERROR] Processing failed: ${error.message}`)
      addTerminalLog(`[ERROR] Processing failed: ${error.message}`)
    } finally {
      setIsProcessing(false)
    }
  }, [uploadedFile, demoMode, addTerminalLog, getDemoPayload, getDemoAgentLogs, persistClaim])

  const handleUpload = useCallback(async (file) => {
    setErrorMessage('')
    setUploadedFile(file)
  }, [])

  const process = useCallback(() => {
    processReal()
  }, [processReal])

  const reset = useCallback(() => {
    abortRef.current = true
    setAgents(AGENT_STEPS.map(a => ({ ...a, status: 'idle', logs: [] })))
    setCurrentStep(-1)
    setIsProcessing(false)
    setIsComplete(false)
    setResults(null)
    setRiskScore(0)
    setErrorMessage('')
    setTerminalLogs([])
    setUploadedFile(null)
    setResolutionStatus(null)
    setActionLog([])
  }, [])

  /** Reset processing state but keep the uploaded file for re-analysis. */
  const reprocess = useCallback(() => {
    abortRef.current = true
    setAgents(AGENT_STEPS.map(a => ({ ...a, status: 'idle', logs: [] })))
    setCurrentStep(-1)
    setIsProcessing(false)
    setIsComplete(false)
    setResults(null)
    setRiskScore(0)
    setErrorMessage('')
    setTerminalLogs([])
    setResolutionStatus(null)
    setActionLog([])
    // uploadedFile intentionally preserved for re-analysis
  }, [])

  return {
    demoMode,
    setDemoMode,
    demoScenario,
    setDemoScenario,
    agents,
    currentStep,
    isProcessing,
    isComplete,
    results,
    riskScore,
    errorMessage,
    terminalLogs,
    uploadedFile,
    handleUpload,
    process,
    reset,
    resolutionStatus,
    actionLog,
    logAction,
    reprocess,
  }
}

export { AGENT_STEPS }
