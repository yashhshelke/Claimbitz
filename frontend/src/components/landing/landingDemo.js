/**
 * Landing-page marketing demo data ONLY.
 *
 * This is illustrative content for the public marketing site (the hero product
 * preview, workflow, claim anatomy, audit trail, etc.). It is intentionally
 * decoupled from the real application: it must NEVER be imported by /dashboard
 * or by useClaimAgent. The dashboard renders real backend results exclusively.
 */

export const DEMO_AGENTS = [
  { name: 'Scanner Agent', short: 'Scanner', description: 'Document structure detected', activity: 'Detecting form layout and page structure', checks: 3, seconds: 1.2, regions: [] },
  { name: 'OCR Agent', short: 'OCR', description: 'Fields extracted from claim', activity: 'Extracting 38 fields from the CMS-1500', checks: 4, seconds: 2.4, regions: ['patient', 'provider'] },
  { name: 'Validation Agent', short: 'Validation', description: 'Required fields and formats checked', activity: 'Checking required fields, IDs and date formats', checks: 5, seconds: 2.1, regions: ['patient', 'provider', 'totals'] },
  { name: 'Medical Expert', short: 'Medical', description: 'Diagnosis and procedures reviewed', activity: 'Reviewing diagnosis and procedure consistency', checks: 4, seconds: 4.6, regions: ['diagnosis', 'services'] },
  { name: 'Policy Expert', short: 'Policy', description: 'Payer policy rules checked', activity: 'Matching coverage against Star Health payer rules', checks: 3, seconds: 3.8, regions: ['insurance'] },
  { name: 'Fraud Detection', short: 'Fraud', description: 'Billing anomalies scanned', activity: 'Scanning service lines for billing anomalies', checks: 4, seconds: 4.1, regions: ['services', 'totals'] },
  { name: 'Risk Assessment', short: 'Risk', description: 'Rejection likelihood scored', activity: 'Scoring rejection likelihood from all findings', checks: 2, seconds: 3.5, regions: [] },
  { name: 'Communication', short: 'Comms', description: 'Payer response drafted', activity: 'Drafting the payer response and summary', checks: 2, seconds: 3.2, regions: [] },
  { name: 'Claim Decision', short: 'Decision', description: 'Final recommendation consolidated', activity: 'Consolidating the final recommendation', checks: 1, seconds: 2.5, regions: [] },
]

export const DEMO_CLAIM = {
  file: 'CLAIM_10482.pdf',
  form: 'CMS-1500 (02/12)',
  risk: 24,
  riskLabel: 'Low risk',
  recommendation: 'Approve',
  processingTime: '27.4 sec',
}
