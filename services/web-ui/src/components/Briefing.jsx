import { useState } from 'react'

const LABEL_COLORS = {
  urgent:        '#dc2626',
  action_needed: '#ea580c',
  calendar:      '#2563eb',
  fyi:           '#6b7280',
  newsletter:    '#0d9488',
  promo:         '#7c3aed',
  spam:          '#52525b',
}

const LABEL_ORDER = ['urgent', 'action_needed', 'calendar', 'fyi', 'newsletter', 'promo', 'spam']

function parse(content) {
  const lines = content.split('\n')
  const title = (lines.find(l => l.startsWith('# ')) || '').slice(2).trim()
  const sections = []
  let sec = null, grp = null, em = null

  for (const line of lines) {
    if (line.startsWith('## ')) {
      const t = line.slice(3).trim()
      if (t.startsWith('Summary')) { sec = null; continue }
      sec = { title: t, groups: [] }
      sections.push(sec)
      grp = null; em = null
    } else if (line.startsWith('### ') && sec) {
      grp = { label: line.slice(4).trim().toLowerCase(), emails: [] }
      sec.groups.push(grp)
      em = null
    } else if (line.startsWith('- ') && grp) {
      const rest = line.slice(2)
      const m = rest.match(/^\*\*(.+?)\*\*\s*(.*)$/)
      const rawMeta = m ? m[2] : ''
      em = {
        subject: m ? m[1] : rest,
        from: rawMeta.replace(/^from\s+/i, '').replace(/\s*\(.*?\)\s*$/, '').trim(),
        summary: '',
      }
      grp.emails.push(em)
    } else if (/^ {2,}/.test(line) && em) {
      const t = line.trim()
      if (t) em.summary = em.summary ? em.summary + ' ' + t : t
    }
  }

  return {
    title,
    sections: sections.filter(s => s.groups.some(g => g.emails.length > 0)),
  }
}

function EmailItem({ email }) {
  return (
    <div className="brief-email">
      <div className="brief-email-top">
        <span className="brief-email-subject">{email.subject}</span>
        {email.from && <span className="brief-email-from">{email.from}</span>}
      </div>
      {email.summary && <div className="brief-email-summary">{email.summary}</div>}
    </div>
  )
}

function LabelGroup({ group }) {
  const color = LABEL_COLORS[group.label] || '#6b7280'
  return (
    <div className="brief-group">
      <div className="brief-group-hdr">
        <span className="label-badge" style={{ background: color }}>
          {group.label.replace('_', ' ')}
        </span>
        <span className="brief-group-count">{group.emails.length}</span>
      </div>
      {group.emails.map((e, i) => <EmailItem key={i} email={e} />)}
    </div>
  )
}

function BriefSection({ section, showTitle }) {
  const [collapsed, setCollapsed] = useState(
    section.title.toLowerCase().startsWith('unresolved')
  )
  const groups = section.groups.filter(g => g.emails.length > 0)
  if (!groups.length) return null
  return (
    <div className="brief-section">
      {showTitle && (
        <button className="brief-section-hdr" onClick={() => setCollapsed(c => !c)}>
          <span className="brief-section-label">{section.title}</span>
          <span className="brief-section-arrow">{collapsed ? '▸' : '▾'}</span>
        </button>
      )}
      {!collapsed && groups.map((g, i) => <LabelGroup key={i} group={g} />)}
    </div>
  )
}

export default function Briefing({ briefing }) {
  const s = briefing.summary || {}
  const { title, sections } = parse(briefing.content)
  const activeStats = LABEL_ORDER.filter(k => (s[k] || 0) > 0)

  return (
    <section className="briefing">
      <div className="brief-header">
        <span className="brief-title">{title}</span>
        {activeStats.length > 0 && (
          <div className="brief-stats">
            {activeStats.map(k => (
              <span key={k} className="brief-stat">
                <span className="label-badge" style={{ background: LABEL_COLORS[k] }}>
                  {k.replace('_', ' ')}
                </span>
                <span className="brief-stat-count">{s[k]}</span>
              </span>
            ))}
          </div>
        )}
      </div>
      {sections.map((sec, i) => (
        <BriefSection key={i} section={sec} showTitle={sections.length > 1} />
      ))}
    </section>
  )
}
