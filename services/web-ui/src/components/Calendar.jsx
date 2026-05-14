import { useState, useEffect } from 'react'
import { getCalendarEvents } from '../api'

function localDateKey(dt) {
  return [
    dt.getFullYear(),
    String(dt.getMonth() + 1).padStart(2, '0'),
    String(dt.getDate()).padStart(2, '0'),
  ].join('-')
}

function formatTime(iso) {
  const d = new Date(iso)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function eventTimeLabel(event) {
  if (event.all_day) return 'All day'
  return `${formatTime(event.start)} – ${formatTime(event.end)}`
}

function dayLabel(dateStr) {
  const today = new Date()
  const tomorrow = new Date(today)
  tomorrow.setDate(today.getDate() + 1)
  if (dateStr === localDateKey(today)) return 'Today'
  if (dateStr === localDateKey(tomorrow)) return 'Tomorrow'
  return new Date(`${dateStr}T12:00:00`).toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric',
  })
}

export default function Calendar() {
  const [phase, setPhase] = useState('loading') // loading | done | failed
  const [data, setData]   = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => { load() }, [])

  async function load() {
    setPhase('loading')
    setError(null)
    try {
      setData(await getCalendarEvents())
      setPhase('done')
    } catch (e) {
      setError(e.message)
      setPhase('failed')
    }
  }

  const events = data?.events ?? []

  const dayGroups = events.reduce((map, event) => {
    const key = event.start.slice(0, 10)
    if (!map.has(key)) map.set(key, [])
    map.get(key).push(event)
    return map
  }, new Map())

  return (
    <section>
      <div className="section-header">
        <h2 className="section-title">
          Calendar
          {data && <span className="inbox-days"> · {data.week}</span>}
        </h2>
        <button className="btn-draft" onClick={load} disabled={phase === 'loading'}>
          {phase === 'loading' ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {phase === 'done' && events.length === 0 && (
        <div className="empty">No events this week.</div>
      )}

      {[...dayGroups.entries()].map(([dateStr, dayEvents]) => (
        <div key={dateStr} className="label-group">
          <div className="cal-day-header">{dayLabel(dateStr)}</div>
          {dayEvents.map(event => {
            const meta = [
              event.organizer,
              event.attendees.length > 0
                ? `${event.attendees.length} attendee${event.attendees.length !== 1 ? 's' : ''}`
                : null,
            ].filter(Boolean).join(' · ')

            return (
              <div key={event.id} className="email-card">
                <div className="cal-card-row">
                  <span className="cal-time">{eventTimeLabel(event)}</span>
                  <div className="cal-body">
                    <div className="cal-title">{event.title}</div>
                    {meta && <div className="cal-meta">{meta}</div>}
                    {event.description && (
                      <div className="cal-description">{event.description}</div>
                    )}
                    {event.meet_link && (
                      <div className="email-actions">
                        <a
                          href={event.meet_link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-draft"
                        >
                          Join Meet ↗
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      ))}
    </section>
  )
}
