import { useState, useRef, useEffect } from 'react'
import { startDraft, getDraft, approveDraft } from '../api'

function parseName(from) {
  const m = from.match(/^"?([^"<]+?)"?\s*</)
  return m ? m[1].trim() : from
}

function formatDate(dateStr) {
  const d = new Date(dateStr)
  const diffDays = Math.floor((Date.now() - d) / 86400000)
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return d.toLocaleDateString('en-US', { weekday: 'short' })
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export default function EmailCard({ email }) {
  const [phase, setPhase]               = useState(null) // null | 'input' | 'pending' | 'done' | 'failed'
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

  async function handleSubmit() {
    setPhase('pending')
    setStep('researching')
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
            setPhase('done')
          } else if (result.status === 'failed') {
            clearInterval(pollRef.current)
            setDraftError(result.error || 'Draft failed.')
            setPhase('failed')
          }
        } catch { /* keep polling on transient errors */ }
      }, 2000)
    } catch (e) {
      setDraftError(e.message)
      setPhase('failed')
    }
  }

  async function handleApprove() {
    setApprovePhase('pending')
    setApproveError(null)
    try {
      await approveDraft(jobId, editSubject, editBody)
      setApprovePhase('done')
    } catch (e) {
      setApproveError(e.message)
      setApprovePhase('failed')
    }
  }

  return (
    <div className="email-card">
      <div className="email-meta">
        <span className="email-from">{parseName(email.from)}</span>
        <span className="email-date">{formatDate(email.date)}</span>
      </div>
      <div className="email-subject">{email.subject}</div>
      <div className="email-reason">{email.reason}</div>

      <div className="email-actions">
        {phase === null && (
          <button className="btn-draft" onClick={() => setPhase('input')}>
            Draft reply
          </button>
        )}

        {phase === 'input' && (
          <>
            <input
              className="draft-instructions"
              placeholder="Instructions (optional)"
              value={instructions}
              onChange={e => setInstructions(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              autoFocus
            />
            <button className="btn-draft" onClick={handleSubmit}>Send</button>
            <button className="btn-cancel" onClick={() => setPhase(null)}>Cancel</button>
          </>
        )}

        {phase === 'pending' && (
          <span className="draft-status">Drafting… ({step})</span>
        )}

        {phase === 'failed' && (
          <span className="draft-error">{draftError}</span>
        )}
      </div>

      {phase === 'done' && (
        <div className="draft-panel">
          <div className="draft-panel-header">
            <strong>Draft reply</strong>
            <button className="draft-panel-close" onClick={() => setPhase(null)}>✕</button>
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
