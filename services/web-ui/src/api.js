const BASE = '/api'

async function request(path, options = {}) {
  const r = await fetch(`${BASE}${path}`, options)
  if (!r.ok) {
    const body = await r.json().catch(() => ({}))
    throw new Error(body.detail || `HTTP ${r.status}`)
  }
  return r.json()
}

export const startRun = (days = 1) =>
  request('/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ days }),
  })

export const getRun = jobId => request(`/run/${jobId}`)

export const getEmails = (days = 7, label = null) => {
  const params = new URLSearchParams({ days })
  if (label) params.set('label', label)
  return request(`/emails?${params}`)
}

export const getLatestBriefing = () => request('/briefs/latest')

export const startBrief = (days = 1) =>
  request('/brief', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ days }),
  })

export const getBrief = jobId => request(`/brief/${jobId}`)

export const startDraft = (emailId, instructions = '') =>
  request('/draft', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email_id: emailId, instructions }),
  })

export const getDraft = jobId => request(`/draft/${jobId}`)

export const approveDraft = (jobId, subject, body) =>
  request(`/approve/${jobId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subject, body }),
  })
