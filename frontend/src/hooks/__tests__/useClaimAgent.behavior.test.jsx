/**
 * Behavioral tests for useClaimAgent — exercises the REAL hook (not mocks) for
 * the highest-value production paths:
 *   - demo LOW / MEDIUM / HIGH scenarios complete with scenario-specific results
 *   - reset clears state; reprocess clears results but keeps the uploaded file
 *   - API failure surfaces a user-facing error without throwing
 *
 * Deterministic: fake timers drive the demo delays; fetch is mocked. No real
 * OpenAI/Groq/Mongo/Pinecone/Redis/RabbitMQ or live backend is required.
 *
 * Note: we deliberately avoid @testing-library's waitFor here because it polls
 * on real timers, which deadlocks against vi.useFakeTimers(). Instead we drive
 * the hook's internal setTimeout-based pipeline with advanceTimersByTimeAsync,
 * which also flushes the awaited microtasks between timers.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useClaimAgent } from '../useClaimAgent'

beforeEach(() => {
  vi.useFakeTimers()
  try { localStorage.clear() } catch { /* ignore */ }
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

/** Advance fake time in chunks, flushing awaited microtasks each step. */
async function flush(ms = 300, iterations = 60) {
  for (let i = 0; i < iterations; i++) {
    await act(async () => {
      await vi.advanceTimersByTimeAsync(ms)
    })
  }
}

describe('useClaimAgent — demo scenarios', () => {
  it('LOW demo completes with APPROVE / LOW result', async () => {
    const { result } = renderHook(() => useClaimAgent())
    act(() => {
      result.current.setDemoMode(true)
      result.current.setDemoScenario('low')
    })

    await act(async () => { result.current.process() })
    await flush()

    expect(result.current.isComplete).toBe(true)
    expect(result.current.results.riskLabel).toBe('LOW')
    expect(result.current.results.recommendation).toBe('APPROVE')
    expect(result.current.riskScore).toBeCloseTo(0.24, 2)
    expect(result.current.agents.every((a) => a.status === 'completed')).toBe(true)
    expect(result.current.isProcessing).toBe(false)
  })

  it('MEDIUM demo completes with REVIEW / MEDIUM result', async () => {
    const { result } = renderHook(() => useClaimAgent())
    act(() => {
      result.current.setDemoMode(true)
      result.current.setDemoScenario('medium')
    })

    await act(async () => { result.current.process() })
    await flush()

    expect(result.current.isComplete).toBe(true)
    expect(result.current.results.riskLabel).toBe('MEDIUM')
    expect(result.current.results.recommendation).toBe('REVIEW')
    expect(result.current.resolutionStatus).toBe('action_required')
  })

  it('HIGH demo completes with HIGH risk and awaiting_review status', async () => {
    const { result } = renderHook(() => useClaimAgent())
    act(() => {
      result.current.setDemoMode(true)
      result.current.setDemoScenario('high')
    })

    await act(async () => { result.current.process() })
    await flush()

    expect(result.current.isComplete).toBe(true)
    expect(result.current.results.riskLabel).toBe('HIGH')
    expect(result.current.resolutionStatus).toBe('awaiting_review')
  })
})

describe('useClaimAgent — persistence and reset/reprocess', () => {
  it('persists the latest claim to localStorage after a demo run', async () => {
    const { result } = renderHook(() => useClaimAgent())
    act(() => { result.current.setDemoMode(true) })

    await act(async () => { result.current.process() })
    await flush()

    expect(result.current.isComplete).toBe(true)
    const stored = JSON.parse(localStorage.getItem('binaryblitz.latestClaim'))
    expect(stored).toBeTruthy()
    expect(stored.riskLabel).toBe('LOW')
    expect(stored.claimData).toBeTruthy()
  })

  it('reset clears results, risk and logs', async () => {
    const { result } = renderHook(() => useClaimAgent())
    act(() => { result.current.setDemoMode(true) })
    await act(async () => { result.current.process() })
    await flush()
    expect(result.current.isComplete).toBe(true)

    act(() => { result.current.reset() })

    expect(result.current.results).toBeNull()
    expect(result.current.riskScore).toBe(0)
    expect(result.current.isComplete).toBe(false)
    expect(result.current.terminalLogs).toHaveLength(0)
    expect(result.current.agents.every((a) => a.status === 'idle')).toBe(true)
  })

  it('reprocess clears results but keeps the uploaded file', async () => {
    const { result } = renderHook(() => useClaimAgent())
    const file = new File(['x'], 'claim.pdf', { type: 'application/pdf' })

    await act(async () => { await result.current.handleUpload(file) })
    expect(result.current.uploadedFile).toBe(file)

    act(() => { result.current.reprocess() })

    expect(result.current.results).toBeNull()
    expect(result.current.isComplete).toBe(false)
    expect(result.current.uploadedFile).toBe(file)
  })
})

describe('useClaimAgent — API failure handling', () => {
  it('surfaces a user-facing error when the backend fetch rejects', async () => {
    global.fetch = vi.fn(() => Promise.reject(new Error('network down')))
    const { result } = renderHook(() => useClaimAgent())
    const file = new File(['x'], 'claim.pdf', { type: 'application/pdf' })
    await act(async () => { await result.current.handleUpload(file) })

    await act(async () => { result.current.process() })
    await flush(300, 20)

    expect(result.current.errorMessage).toContain('network down')
    expect(result.current.isComplete).toBe(false)
    expect(result.current.isProcessing).toBe(false)
  })

  it('surfaces the backend detail message on a non-ok response', async () => {
    global.fetch = vi.fn(() => Promise.resolve({
      ok: false,
      json: () => Promise.resolve({ detail: 'Claim processing failed. Please try again.' }),
    }))
    const { result } = renderHook(() => useClaimAgent())
    const file = new File(['x'], 'claim.pdf', { type: 'application/pdf' })
    await act(async () => { await result.current.handleUpload(file) })

    await act(async () => { result.current.process() })
    await flush(300, 20)

    expect(result.current.errorMessage).toContain('Claim processing failed')
    expect(result.current.isProcessing).toBe(false)
  })
})
