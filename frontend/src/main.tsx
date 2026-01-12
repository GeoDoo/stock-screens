/* eslint-disable react-refresh/only-export-components */
import { StrictMode, useState, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { GlossaryPage } from './components/GlossaryPage.tsx'
import { MemosPage } from './components/MemosPage.tsx'
import { MemoDetailPage } from './components/MemoDetailPage.tsx'
import FilingsPage from './components/FilingsPage.tsx'
import { FilingsAnalysisPage } from './pages/FilingsAnalysisPage.tsx'

function Router() {
  const [path, setPath] = useState(window.location.pathname)

  useEffect(() => {
    const handlePopState = () => setPath(window.location.pathname)
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  // Handle hash scrolling for glossary anchors
  useEffect(() => {
    if (path === '/glossary' && window.location.hash) {
      const id = window.location.hash.slice(1)
      setTimeout(() => {
        document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
      }, 100)
    }
  }, [path])

  // Forensic Analysis Route: /forensic/:symbol
  const forensicMatch = path.match(/^\/forensic\/([a-zA-Z0-9.-]+)$/)
  if (forensicMatch) {
    return <FilingsAnalysisPage symbol={forensicMatch[1]} />
  }

  if (path === '/glossary') {
    return <GlossaryPage />
  }

  if (path === '/memos') {
    return <MemosPage />
  }

  if (path === '/filings') {
    return <FilingsPage />
  }

  // Match /memos/:id
  const memoMatch = path.match(/^\/memos\/(\d+)$/)
  if (memoMatch) {
    return <MemoDetailPage memoId={parseInt(memoMatch[1])} />
  }

  return <App />
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Router />
  </StrictMode>,
)
