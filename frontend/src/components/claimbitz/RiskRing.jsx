import React, { useEffect, useState } from 'react'
import { motion, useMotionValue, useTransform, animate, useReducedMotion } from 'framer-motion'
import { cn } from '../../lib/utils'

/**
 * RiskRing — animated circular risk gauge (presentation only).
 * `value` is a 0–100 percentage. `tone` selects the stroke color.
 */
export function RiskRing({ value, size = 96, tone = 'success' }) {
  const radius = size / 2 - 6
  const circumference = 2 * Math.PI * radius
  const progress = useMotionValue(0)
  const dash = useTransform(progress, (p) => `${(p / 100) * circumference} ${circumference}`)

  const reduceMotion = useReducedMotion()

  const stroke =
    tone === 'destructive' ? 'var(--color-destructive)' :
    tone === 'warning' ? 'var(--color-warning)' :
    'var(--color-success)'

  useEffect(() => {
    // Reduced motion: set the gauge to its final value instantly.
    if (reduceMotion) {
      progress.set(value)
      return
    }
    const controls = animate(progress, value, { duration: 1.2, ease: 'easeOut' })
    return () => controls.stop()
  }, [value, progress, reduceMotion])

  return (
    <svg width={size} height={size} className="-rotate-90" aria-hidden="true">
      <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--color-border)" strokeWidth={6} />
      <motion.circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={stroke}
        strokeWidth={6}
        strokeLinecap="round"
        style={{ strokeDasharray: dash }}
      />
    </svg>
  )
}

/**
 * AnimatedPercent — counts up to `value` and renders "N%".
 */
export function AnimatedPercent({ value, className, active = true }) {
  const reduceMotion = useReducedMotion()
  const [display, setDisplay] = useState(active && !reduceMotion ? 0 : value)

  useEffect(() => {
    // Reduced motion (or inactive): show the final value with no count-up.
    if (!active || reduceMotion) {
      setDisplay(value)
      return
    }
    const controls = animate(0, value, {
      duration: 1.2,
      ease: 'easeOut',
      onUpdate: (v) => setDisplay(Math.round(v)),
    })
    return () => controls.stop()
  }, [value, active, reduceMotion])

  return <span className={cn('tabular-nums', className)}>{display}%</span>
}
