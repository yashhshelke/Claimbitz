import React, { Suspense, lazy } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { BootSplash } from './components/claimbitz/BootSplash'
import LandingPage from './pages/LandingPage'

// Landing stays eager (first paint / marketing entry). The authenticated-feeling
// console routes are code-split so the landing bundle stays lean; deep links keep
// working through the Vercel SPA rewrite since chunks load from the same origin.
const Dashboard = lazy(() => import('./pages/Dashboard'))
const SubmissionPage = lazy(() => import('./pages/SubmissionPage'))
const InsurerPortalPage = lazy(() => import('./pages/InsurerPortalPage'))

/** Lightweight route-transition fallback, consistent with the warm-neutral theme. */
function RouteFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background" role="status" aria-label="Loading">
      <span className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
    </div>
  )
}

function App() {
  const location = useLocation()

  return (
    <>
      <BootSplash />
      <AnimatePresence mode="wait">
        <Suspense fallback={<RouteFallback />}>
          <Routes location={location} key={location.pathname}>
            <Route path="/" element={<LandingPage />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/submission" element={<SubmissionPage />} />
            <Route path="/portal/:insurerId" element={<InsurerPortalPage />} />
          </Routes>
        </Suspense>
      </AnimatePresence>
    </>
  )
}

export default App
