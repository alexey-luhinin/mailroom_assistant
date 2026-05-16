import { useState, useEffect, useRef } from 'react'
import { startRun, getRun, getEmails, getLatestBriefing, startBrief, getBrief, getCalendarEvents } from './api'
import Briefing from './components/Briefing'
import Calendar from './components/Calendar'
import Cleanup from './components/Cleanup'
import EmailCard from './components/EmailCard'
import FollowUp from './components/FollowUp'

const LABEL_ORDER  = ['urgent', 'action_needed', 'calendar', 'fyi', 'newsletter', 'promo', 'spam']
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
  const [section, setSection]             = useState('inbox')
  const [emails, setEmails]               = useState([])
  const [days, setDays]                   = useState(1)
  const [briefing, setBriefing]           = useState(null)
  const [briefingReady, setBriefingReady] = useState(false)
  const [calendarEvents, setCalendarEvents] = useState([])
  const [syncPhase, setSyncPhase]         = useState(null)   // null | 'pending' | 'failed'
  const [briefPhase, setBriefPhase]       = useState(null)   // null | 'pending' | 'failed'
  const [error, setError]                 = useState(null)

  const syncPollRef  = useRef(null)
  const briefPollRef = useRef(null)

  useEffect(() => {
    loadEmails(days)
    loadLatestBriefing()
    getCalendarEvents(1).then(d => setCalendarEvents(d.events ?? [])).catch(e => console.warn('Calendar fetch failed:', e))
    return () => {
      clearInterval(syncPollRef.current)
      clearInterval(briefPollRef.current)
    }
  }, [])

  async function loadEmails(d) {
    try { setEmails(await getEmails(d)) } catch { /* silent on first load */ }
  }

  async function loadLatestBriefing() {
    try { setBriefing(await getLatestBriefing()) } catch { /* 404 = no briefing yet */ }
    setBriefingReady(true)
  }

  function handleDaysChange(d) {
    setDays(d)
    loadEmails(d)
  }

  // ── Sync ──────────────────────────────────────────────────────────────────

  async function handleSync() {
    setSyncPhase('pending')
    setError(null)
    try {
      const job = await startRun(days)
      syncPollRef.current = setInterval(() => pollSync(job.job_id), 2000)
    } catch (e) {
      setError(e.message)
      setSyncPhase(null)
    }
  }

  async function pollSync(jobId) {
    try {
      const job = await getRun(jobId)
      if (job.status === 'done') {
        clearInterval(syncPollRef.current)
        setSyncPhase(null)
        loadEmails(days)
      } else if (job.status === 'failed') {
        clearInterval(syncPollRef.current)
        setSyncPhase('failed')
        setError(job.error || 'Sync failed.')
      }
    } catch { /* keep polling on transient errors */ }
  }

  // ── Briefing ──────────────────────────────────────────────────────────────

  async function handleBrief() {
    setBriefPhase('pending')
    setError(null)
    try {
      const job = await startBrief(days)
      briefPollRef.current = setInterval(() => pollBrief(job.job_id), 2000)
    } catch (e) {
      setError(e.message)
      setBriefPhase(null)
    }
  }

  async function pollBrief(jobId) {
    try {
      const job = await getBrief(jobId)
      if (job.status === 'done') {
        clearInterval(briefPollRef.current)
        setBriefPhase(null)
        loadLatestBriefing()
      } else if (job.status === 'failed') {
        clearInterval(briefPollRef.current)
        setBriefPhase('failed')
        setError(job.error || 'Briefing failed.')
      }
    } catch { /* keep polling on transient errors */ }
  }

  // ── Derived ───────────────────────────────────────────────────────────────

  const grouped = LABEL_ORDER.reduce((acc, label) => {
    const group = emails.filter(e => e.label === label)
    if (group.length) acc[label] = group
    return acc
  }, {})

  const hasEmails = Object.keys(grouped).length > 0

  function navClass(id) {
    return 'nav-item' + (section === id ? ' active' : '')
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="layout">
      <nav className="sidebar">
        <div className="sidebar-logo">Mailroom</div>

        <button className={navClass('inbox')} onClick={() => setSection('inbox')}>
          <span className="nav-icon">📬</span>Inbox
        </button>
        <button className="nav-sub-action" onClick={handleSync} disabled={syncPhase === 'pending'}>
          {syncPhase === 'pending' ? 'Syncing…' : 'Sync inbox'}
        </button>

        <button className={navClass('briefing')} onClick={() => setSection('briefing')}>
          <span className="nav-icon">📋</span>Briefing
        </button>
        <button className="nav-sub-action" onClick={handleBrief} disabled={briefPhase === 'pending'}>
          {briefPhase === 'pending' ? 'Running…' : 'Generate briefing'}
        </button>

        {[
          { id: 'cleanup',  icon: '🧹', label: 'Cleanup' },
          { id: 'calendar', icon: '📅', label: 'Calendar' },
          { id: 'followup', icon: '⏳', label: 'Follow-up' },
        ].map(item => (
          <button
            key={item.id}
            className={navClass(item.id)}
            onClick={() => setSection(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      <div className="main">
        <div className="content">
          {error && <div className="error">{error}</div>}

          {section === 'inbox' && (
            <>
              <div className="inbox-toolbar">
                <div className="days-selector">
                  {DAY_OPTIONS.map(d => (
                    <button
                      key={d}
                      className={'btn-day' + (days === d ? ' active' : '')}
                      onClick={() => handleDaysChange(d)}
                      disabled={syncPhase === 'pending'}
                    >
                      {d}d
                    </button>
                  ))}
                </div>
              </div>

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

              {!hasEmails && syncPhase !== 'pending' && (
                <div className="empty">
                  No emails yet. Click <strong>Sync</strong> to fetch and classify your inbox.
                </div>
              )}
            </>
          )}

          {section === 'briefing' && (
            <>
              {briefingReady && !briefing && (
                <div className="brief-placeholder">
                  No briefing yet. Click <strong>Brief</strong> in the sidebar to generate.
                </div>
              )}
              {briefing && <Briefing briefing={briefing} calendarEvents={calendarEvents} />}
            </>
          )}

          {section === 'cleanup' && <Cleanup />}

          {section === 'calendar' && <Calendar />}

          {section === 'followup' && <FollowUp />}
        </div>
      </div>
    </div>
  )
}

