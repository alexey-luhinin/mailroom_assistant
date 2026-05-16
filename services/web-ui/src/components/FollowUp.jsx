import { useState, useRef, useEffect } from 'react'
import { startFollowup, getFollowup, getEmail, startDraft, getDraft, approveFollowupDraft } from '../api'

function parseTo(to) {
  const m = to.match(/^"?([^"<]+?)"?\s*<([^>]+)>/)
  if (!m) return to
  const name = m[1].trim()
  const addr = m[2].trim()
  return name === addr ? addr : name
}

function formatDate(iso) {
  const d = new Date(iso)
  const now = new Date()
  const diff = Math.floor((now - d) / 86400000)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Yesterday'
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function FollowUpCard({ email }) {
  const [bodyPhase, setBodyPhase]       = useState(null) // null | 'loading' | 'done' | 'failed'
  const [bodyText, setBodyText]         = useState(null)
  const [draftPhase, setDraftPhase]     = useState(null) // null | 'input' | 'pending' | 'done' | 'failed'
  const [instructions, setInstructions] = useState('')
  const [step, setStep]                 = useState(null)
  const [jobId, setJobId]               = useState(null)
  const [editSubject, setEditSubject]   = useState('')
  const [editBody, setEditBody]         = useState('')
  const [approvePhase, setApprovePhase] = useState(null) // null | 'pending' | 'done' | 'failed'
  const [approveError, setApproveError] = useState(null)
  const [draftError, setDraftError]     = useState(null)
  const pollRef = useRef(null)

  useEffect(() => () => clearInterval(pollRef.current), [])

  async function handleShowBody() {
    setBodyPhase('loading')
    try {
      const data = await getEmail(email.id)
      setBodyText(data.body || '(no message body)')
      setBodyPhase('done')
    } catch {
      setBodyPhase('failed')
    }
  }

  async function handleSubmitDraft() {
    setDraftPhase('pending')
    setStep('researching')
    setDraftError(null)
    try {
      const job = await startDraft(email.id, instructions)
      setJobId(job.job_id)
      pollRef.current = setInterval(async () => {
        try {
          const result = await getDraft(job.job_id)
          setStep(result.step)
          if (result.status === 'done') {
            clearInterval(pollRef.current)
            setEditSubject(result.draft?.subject || '')
            setEditBody(result.draft?.body || '')
            setDraftPhase('done')
          } else if (result.status === 'failed') {
            clearInterval(pollRef.current)
            setDraftError(result.error || 'Draft failed.')
            setDraftPhase('failed')
          }
        } catch { /* keep polling on transient errors */ }
      }, 2000)
    } catch (e) {
      setDraftError(e.message)
      setDraftPhase('failed')
    }
  }

  async function handleApprove() {
    setApprovePhase('pending')
    setApproveError(null)
    try {
      await approveFollowupDraft(jobId, editSubject, editBody)
      setApprovePhase('done')
    } catch (e) {
      setApproveError(e.message)
      setApprovePhase('failed')
    }
  }

  return (
    <div className="email-card">
      <div className="email-meta">
        <span className="email-from">To: {parseTo(email.to)}</span>
        <span className="email-date">{formatDate(email.sent_at)}</span>
      </div>
      <div className="email-subject">{email.subject}</div>
      <div style={{ marginTop: 6 }}>
        <span
          className="label-badge"
          style={{ background: email.days_waiting > 3 ? '#ea580c' : '#71717a' }}
        >
          {email.days_waiting} days
        </span>
      </div>

      <div className="email-actions" style={{ marginTop: 10 }}>
        {bodyPhase === null && (
          <button className="btn-draft" onClick={handleShowBody}>Show message</button>
        )}
        {bodyPhase === 'loading' && (
          <span className="draft-status">Loading…</span>
        )}
        {bodyPhase === 'done' && (
          <button className="btn-cancel" onClick={() => { setBodyPhase(null); setBodyText(null) }}>
            Hide message
          </button>
        )}
        {bodyPhase === 'failed' && (
          <span className="draft-error">Failed to load message</span>
        )}

        {draftPhase === null && (
          <button className="btn-draft" onClick={() => setDraftPhase('input')}>
            Draft follow-up
          </button>
        )}
        {draftPhase === 'input' && (
          <>
            <input
              className="draft-instructions"
              placeholder="Instructions (optional)"
              value={instructions}
              onChange={e => setInstructions(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmitDraft()}
              autoFocus
            />
            <button className="btn-draft" onClick={handleSubmitDraft}>Send</button>
            <button className="btn-cancel" onClick={() => setDraftPhase(null)}>Cancel</button>
          </>
        )}
        {draftPhase === 'pending' && (
          <span className="draft-status">Drafting… ({step})</span>
        )}
        {draftPhase === 'failed' && (
          <span className="draft-error">{draftError}</span>
        )}
      </div>

      {bodyPhase === 'done' && (
        <div className="draft-panel" style={{ marginTop: 12 }}>
          <div className="draft-panel-header">
            <strong>Original message</strong>
          </div>
          <div className="draft-body">{bodyText}</div>
        </div>
      )}

      {draftPhase === 'done' && (
        <div className="draft-panel" style={{ marginTop: 12 }}>
          <div className="draft-panel-header">
            <strong>Draft follow-up</strong>
            <button className="draft-panel-close" onClick={() => setDraftPhase(null)}>✕</button>
          </div>
          <div className="draft-panel-body">
            <input
              className="draft-edit-subject"
              value={editSubject}
              onChange={e => setEditSubject(e.target.value)}
              disabled={approvePhase === 'pending' || approvePhase === 'done'}
            />
            <textarea
              className="draft-edit-body"
              value={editBody}
              onChange={e => setEditBody(e.target.value)}
              rows={10}
              disabled={approvePhase === 'pending' || approvePhase === 'done'}
            />
            <div className="draft-approve-row">
              {approvePhase === 'done' ? (
                <span className="draft-saved">Saved to Gmail Drafts</span>
              ) : (
                <>
                  <button
                    className="btn-approve"
                    onClick={handleApprove}
                    disabled={approvePhase === 'pending'}
                  >
                    {approvePhase === 'pending' ? 'Saving…' : 'Approve'}
                  </button>
                  {approvePhase === 'failed' && (
                    <span className="draft-error">{approveError}</span>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function FollowUp() {
  const [phase, setPhase]   = useState('pending')
  const [result, setResult] = useState(null)
  const [error, setError]   = useState(null)
  const pollRef             = useRef(null)

  useEffect(() => {
    run()
    return () => clearInterval(pollRef.current)
  }, [])

  async function run() {
    clearInterval(pollRef.current)
    setPhase('pending')
    setError(null)
    try {
      const job = await startFollowup(30)
      pollRef.current = setInterval(async () => {
        try {
          const data = await getFollowup(job.job_id)
          if (data.status === 'done') {
            clearInterval(pollRef.current)
            setResult(data)
            setPhase('done')
          } else if (data.status === 'failed') {
            clearInterval(pollRef.current)
            setError(data.error || 'Follow-up check failed.')
            setPhase('failed')
          }
        } catch { /* keep polling on transient errors */ }
      }, 2000)
    } catch (e) {
      setError(e.message)
      setPhase('failed')
    }
  }

  const emails = result?.emails ?? []

  return (
    <section>
      <div className="section-header">
        <h2 className="section-title">
          Follow-up
          {result && (
            <span className="inbox-days"> · {result.days}d window</span>
          )}
        </h2>
        <button
          className="btn-run"
          onClick={run}
          disabled={phase === 'pending'}
        >
          {phase === 'pending' ? 'Checking…' : 'Refresh'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {phase === 'pending' && !error && (
        <span className="draft-status">Checking for unanswered emails…</span>
      )}

      {phase === 'done' && emails.length === 0 && (
        <div className="empty">All caught up! No emails waiting for a reply.</div>
      )}

      {phase === 'done' && emails.length > 0 && (
        <>
          <div style={{ fontSize: 17, fontWeight: 600, marginBottom: 16 }}>
            Waiting for reply
            <span className="inbox-days"> · {result.waiting_count} emails</span>
          </div>
          {emails.map(email => (
            <FollowUpCard key={email.id} email={email} />
          ))}
        </>
      )}
    </section>
  )
}
