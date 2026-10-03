import React, { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'

/**
 * BootSplash — faithful port of Lovable's branded initialization splash
 * (~1s, once per load, then fades out). Presentation only.
 */
export function BootSplash() {
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    const t = window.setTimeout(() => setVisible(false), 1000)
    return () => window.clearTimeout(t)
  }, [])

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="boot"
          exit={{ opacity: 0 }}
          transition={{ duration: 0.35, ease: 'easeOut' }}
          className="fixed inset-0 z-[100] flex items-center justify-center bg-background"
          role="status"
          aria-label="Initializing workspace"
        >
          <div className="w-[220px]">
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-[14px] font-bold text-primary-foreground">
                C
              </span>
              <div>
                <p className="text-[17px] font-semibold leading-tight tracking-tight text-foreground">ClaimBitz</p>
                <p className="text-[12px] text-muted-foreground">Claims Intelligence</p>
              </div>
            </div>
            <div className="mt-5 h-[2px] overflow-hidden rounded-full bg-border">
              <motion.div
                className="h-full origin-left bg-primary"
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={{ duration: 0.9, ease: [0.4, 0, 0.2, 1] }}
              />
            </div>
            <p className="mt-2.5 text-[12px] text-muted-foreground">Initializing workspace…</p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
