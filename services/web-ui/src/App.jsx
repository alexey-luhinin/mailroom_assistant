import { useState, useEffect, useRef } from 'react'
import { startRun, getRun, getEmails } from './api'
import Briefing from './components/Briefing'
import EmailCard from './components/EmailCard'

const LABEL_ORDER = ['urgent', 'action_needed', 'calendar', 'fyi', 'newsletter', 'promo', 'spam']

const LABEL_COLORS = {
  urgent:        '#dc2626',
  action_needed: '#ea580c',
  calendar:      '#2563eb',
  fyi:           '#6b7280',
  newsletter:    '#0d9488',
  promo:         '#7c3aed',
  spam:          '#52525b',
}

const DAY_OPTIONS = [1, 3, 7, 14, 30]

export default function App() {
  const [emails, setEmails]     = useState([])
  const [runJob, setRunJob]     = useState(null)
  const [briefing, setBriefing] = useState(null)
  const [running, setRunning]   = useState(false)
  const [error, setError]       = useState(null)
  const [days, setDays]         = useState(1)
  const pollRef = useRef(null)

  useEffect(() => {
    loadEmails(days)
    return () => clearInterval(pollRef.current)
  }, [])

  async function loadEmails(d) {
    try {
      setEmails(await getEmails(d))
    } catch { /* empty on first load is fine */ }
  }

  function handleDaysChange(d) {
    setDays(d)
    loadEmails(d)
  }

  async function handleRun() {
    setRunning(true)
    setError(null)
    try {
      const job = await startRun(days)
      setRunJob(job)
      pollRef.current = setInterval(() => pollRun(job.job_id), 2000)
    } catch (e) {
      setError(e.message)
      setRunning(false)
    }
  }

  async function pollRun(jobId) {
    try {
      const job = await getRun(jobId)
      setRunJob(job)
      if (job.status === 'done') {
        clearInterval(pollRef.current)
        setRunning(false)
        setBriefing(job.briefing)
        loadEmails(days)
      } else if (job.status === 'failed') {
        clearInterval(pollRef.current)
        setRunning(false)
        setError(job.error || 'Morning run failed.')
      }
    } catch { /* keep polling on transient errors */ }
  }

  const grouped = LABEL_ORDER.reduce((acc, label) => {
    const group = emails.filter(e => e.label === label)
    if (group.length) acc[label] = group
    return acc
  }, {})

  const hasEmails = Object.keys(grouped).length > 0

  return (
    <div className="app">
      <header className="app-header">
        <h1>Mailroom</h1>
        <div className="header-right">
          {running && runJob && (
            <span className="run-status">{runJob.step}…</span>
          )}
          <div className="days-selector">
            {DAY_OPTIONS.map(d => (
              <button
                key={d}
                className={`btn-day${days === d ? ' active' : ''}`}
                onClick={() => handleDaysChange(d)}
                disabled={running}
              >
                {d}d
              </button>
            ))}
          </div>
          <button className="btn-run" onClick={handleRun} disabled={running}>
            {running ? 'Running…' : 'Run'}
          </button>
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      {briefing && <Briefing briefing={briefing} />}

      {hasEmails && (
        <section className="email-section">
          <h2>Inbox <span className="inbox-days">· last {days} day{days !== 1 ? 's' : ''}</span></h2>
          {LABEL_ORDER.filter(l => grouped[l]).map(label => (
            <div key={label} className="label-group">
              <div className="label-group-header">
                <span
                  className="label-badge"
                  style={{ background: LABEL_COLORS[label] }}
                >
                  {label.replace('_', ' ')}
                </span>
                <span className="label-count">{grouped[label].length}</span>
              </div>
              {grouped[label].map(email => (
                <EmailCard key={email.id} email={email} />
              ))}
            </div>
          ))}
        </section>
      )}

      {!hasEmails && !running && (
        <div className="empty">
          No emails yet. Click <strong>Run</strong> to fetch and classify your inbox.
        </div>
      )}
    </div>
  )
}
