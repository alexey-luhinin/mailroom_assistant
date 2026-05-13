import { useState, useRef, useEffect } from 'react'
import { getLatestAnalysis, startAnalysis, getAnalysis } from '../api'

const RECO_COLORS = {
  unsubscribe: '#dc2626',
  consider:    '#ea580c',
}

export default function Cleanup() {
  const [phase, setPhase]   = useState('loading') // loading | idle | pending | done | failed
  const [result, setResult] = useState(null)
  const [error, setError]   = useState(null)
  const pollRef             = useRef(null)

  useEffect(() => {
    loadLatest()
    return () => clearInterval(pollRef.current)
  }, [])

  async function loadLatest() {
    try {
      const data = await getLatestAnalysis()
      setResult(data)
      setPhase('done')
    } catch {
      setPhase('idle')
    }
  }

  async function handleAnalyze() {
    setPhase('pending')
    setError(null)
    try {
      const job = await startAnalysis(30)
      pollRef.current = setInterval(async () => {
        try {
          const data = await getAnalysis(job.job_id)
          if (data.status === 'done') {
            clearInterval(pollRef.current)
            setResult(data)
            setPhase('done')
          } else if (data.status === 'failed') {
            clearInterval(pollRef.current)
            setError(data.error || 'Analysis failed.')
            setPhase('failed')
          }
        } catch { /* keep polling on transient errors */ }
      }, 2000)
    } catch (e) {
      setError(e.message)
      setPhase('failed')
    }
  }

  const candidates = result?.candidates ?? []

  return (
    <section>
      <div className="section-header">
        <h2 className="section-title">
          Cleanup
          {result && (
            <span className="inbox-days"> · {result.days}d window</span>
          )}
        </h2>
        <button
          className="btn-run"
          onClick={handleAnalyze}
          disabled={phase === 'pending' || phase === 'loading'}
        >
          {phase === 'pending' ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {phase === 'loading' && (
        <span className="run-status">Loading…</span>
      )}

      {(phase === 'idle' || (phase === 'failed' && !result)) && (
        <div className="empty">
          No cleanup data yet. Click <strong>Analyze</strong> to scan newsletter and promo emails.
        </div>
      )}

      {result && candidates.length === 0 && (
        <div className="empty">All senders are regularly read — no cleanup suggestions.</div>
      )}

      {candidates.map(c => (
        <div key={c.sender} className="email-card">
          <div className="email-meta">
            <span className="email-from">{c.name !== c.sender ? c.name : ''}</span>
            <span
              className="label-badge"
              style={{ background: RECO_COLORS[c.recommendation] }}
            >
              {c.recommendation}
            </span>
          </div>
          <div className="cleanup-sender">{c.sender}</div>
          <div className="cleanup-stats">
            {c.total} emails · {c.opened} opened · {Math.round(c.open_rate * 100)}% open rate
          </div>
          {c.unsubscribe_url && (
            <div className="cleanup-action">
              <a
                href={c.unsubscribe_url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-draft"
              >
                Unsubscribe ↗
              </a>
            </div>
          )}
        </div>
      ))}
    </section>
  )
}
