import { useState, useRef, useEffect } from 'react'
import { getLatestAnalysis, startAnalysis, getAnalysis } from '../api'

const RECO_ORDER  = ['unsubscribe', 'consider']
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

  const grouped = RECO_ORDER.reduce((acc, reco) => {
    const group = candidates.filter(c => c.recommendation === reco)
    if (group.length) acc[reco] = group
    return acc
  }, {})

  return (
    <section>
      <div className="section-header">
        <h2 className="section-title">
          Cleanup
          {result && <span className="inbox-days"> · {result.days}d window</span>}
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

      {phase === 'loading' && <span className="draft-status">Loading…</span>}

      {(phase === 'idle' || (phase === 'failed' && !result)) && (
        <div className="empty">
          No cleanup data yet. Click <strong>Analyze</strong> to scan newsletter and promo emails.
        </div>
      )}

      {result && candidates.length === 0 && (
        <div className="empty">All senders are regularly read — no cleanup suggestions.</div>
      )}

      {RECO_ORDER.filter(reco => grouped[reco]).map(reco => (
        <div key={reco} className="label-group">
          <div className="label-group-header">
            <span className="label-badge" style={{ background: RECO_COLORS[reco] }}>
              {reco}
            </span>
            <span className="label-count">{grouped[reco].length}</span>
          </div>
          {grouped[reco].map(c => (
            <div key={c.sender} className="email-card">
              <div className="cleanup-name">
                {c.name !== c.sender ? c.name : c.sender}
              </div>
              <div className="cleanup-detail">
                <span className="cleanup-stats">
                  {c.name !== c.sender ? `${c.sender} · ` : ''}
                  {c.total} emails · {c.opened} opened · {Math.round(c.open_rate * 100)}% open rate
                </span>
                {c.unsubscribe_url && (
                  <a
                    href={c.unsubscribe_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="cleanup-link"
                  >
                    unsubscribe ↗
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      ))}
    </section>
  )
}
