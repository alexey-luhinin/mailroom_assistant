const SECTION_COLORS = {
  urgent:        '#dc2626',
  action_needed: '#ea580c',
}

const SECTION_LABELS = {
  urgent:        'Urgent',
  action_needed: 'Action needed',
}

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

function renderBold(text) {
  const parts = text.split(/(\*\*[^*]+\*\*)/)
  return parts.map((part, i) =>
    part.startsWith('**') && part.endsWith('**')
      ? <strong key={i}>{part.slice(2, -2)}</strong>
      : part
  )
}

function parse(content) {
  const paragraphs = content.split(/\n\n+/).map(p => p.trim()).filter(Boolean)
  const result = { opening: '', sections: [], body: [], closing: '' }

  if (!paragraphs.length) return result
  result.opening = paragraphs[0]

  let current = null
  for (let i = 1; i < paragraphs.length; i++) {
    const p = paragraphs[i]
    if (p === 'Urgent:') {
      current = { label: 'urgent', entries: [] }
      result.sections.push(current)
    } else if (p === 'Action needed:') {
      current = { label: 'action_needed', entries: [] }
      result.sections.push(current)
    } else if (current) {
      current.entries.push(p)
    } else {
      result.body.push(p)
    }
  }

  // Detect trailing "FYI · newsletters · promos" closing line
  const lastEntries = result.sections.length
    ? result.sections[result.sections.length - 1].entries
    : result.body
  if (lastEntries.length) {
    const last = lastEntries[lastEntries.length - 1]
    if (last.includes('·')) result.closing = lastEntries.pop()
  }

  return result
}

export default function Briefing({ briefing }) {
  const s = briefing.summary || {}
  const { opening, sections, body, closing } = parse(briefing.content || '')
  const activeStats = LABEL_ORDER.filter(k => (s[k] || 0) > 0)

  return (
    <section className="briefing">
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

      {opening && <p className="brief-opening">{opening}</p>}

      {sections.map((sec, i) => (
        <div key={i} className="brief-section-block">
          <span
            className="brief-section-tag"
            style={{ color: SECTION_COLORS[sec.label] }}
          >
            {SECTION_LABELS[sec.label] || sec.label}
          </span>
          {sec.entries.map((entry, j) => (
            <p key={j} className="brief-entry">{renderBold(entry)}</p>
          ))}
        </div>
      ))}

      {body.map((p, i) => (
        <p key={i} className="brief-body">{p}</p>
      ))}

      {closing && <p className="brief-closing">{closing}</p>}
    </section>
  )
}
