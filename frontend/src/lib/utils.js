import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * cn — merge conditional class names and de-duplicate conflicting
 * Tailwind utilities. Shared by all ported Lovable UI components.
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs))
}
