import React, { useEffect, useState } from 'react'
import { motion, useMotionValue, useTransform, animate } from 'framer-motion'
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

  const stroke =
    tone === 'destructive' ? 'var(--color-destructive)' :
    tone === 'warning' ? 'var(--color-warning)' :
    'var(--color-success)'

  useEffect(() => {
    const controls = animate(progress, value, { duration: 1.2, ease: 'easeOut' })
    return () => controls.stop()
  }, [value, progress])

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
  const [display, setDisplay] = useState(active ? 0 : value)

  useEffect(() => {
    if (!active) {
      setDisplay(value)
      return
    }
    const controls = animate(0, value, {
      duration: 1.2,
      ease: 'easeOut',
      onUpdate: (v) => setDisplay(Math.round(v)),
    })
    return () => controls.stop()
  }, [value, active])

  return <span className={cn('tabular-nums', className)}>{display}%</span>
}
