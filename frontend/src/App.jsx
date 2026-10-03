import React from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { BootSplash } from './components/claimbitz/BootSplash'
import LandingPage from './pages/LandingPage'
import Dashboard from './pages/Dashboard'
import SubmissionPage from './pages/SubmissionPage'
import InsurerPortalPage from './pages/InsurerPortalPage'

function App() {
  const location = useLocation()

  return (
    <>
      <BootSplash />
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/submission" element={<SubmissionPage />} />
          <Route path="/portal/:insurerId" element={<InsurerPortalPage />} />
        </Routes>
      </AnimatePresence>
    </>
  )
}

export default App
