# Web Design Skill — Mailroom UI

Conventions extracted from `services/web-ui/src/`. Every new component must
feel like it was built at the same time as the existing ones — same weight,
same restraint, same vocabulary.

---

## Design philosophy

- **Calm, not clever.** This is a productivity tool. No gradients, no illustrations,
  no decorative motion. The interface should disappear behind the content.
- **Inline over modal.** Panels expand in place; nothing overlays the page.
- **Text over icons.** Status, actions, and labels use words. No icon libraries.
- **Density without clutter.** Cards are compact (14px/16px padding) but never
  feel crowded — whitespace between groups does the breathing.
- **One interaction at a time.** Phase-based state machines prevent ambiguous UI.
  A card is in exactly one state; transitions between states are instant.

---

## Color system

The palette is **Zinc** (cool gray) for neutrals and a fixed set of semantic
colors. Never introduce a new hue without a clear semantic reason.

### Neutrals

| Token (approximate) | Hex       | Role                                              |
|---------------------|-----------|---------------------------------------------------|
| zinc-900            | `#18181b` | Primary text · primary button bg · `<h1>`         |
| zinc-700            | `#3f3f46` | Secondary body copy · `<h3>` · draft body text    |
| zinc-600            | `#52525b` | Tertiary text (email reason)                      |
| zinc-500            | `#71717a` | Muted text (sender, count, status, cancel label)  |
| zinc-400            | `#a1a1aa` | Very muted (date · input focus border)            |
| zinc-300            | `#d4d4d8` | Input border · secondary button border            |
| zinc-200            | `#e4e4e7` | Ghost button border · panel inner border          |
| zinc-100            | `#f4f4f5` | Page background · button hover fill               |
| zinc-50             | `#fafafa` | Card sub-header background (draft panel header)   |
| white               | `#ffffff` | Card/panel background · primary button text       |

### Semantic

| Situation | Background  | Text      |
|-----------|-------------|-----------|
| Error     | `#fee2e2`   | `#b91c1c` |

Never add warning/success/info variants speculatively. Add them only when a
real state requires them, following the same bg-100/text-700 pattern.

### Label colors

Used exclusively for `.label-badge` backgrounds. Always white text on top.

```js
const LABEL_COLORS = {
  urgent:        '#dc2626',  // red-600
  action_needed: '#ea580c',  // orange-600
  calendar:      '#2563eb',  // blue-600
  fyi:           '#6b7280',  // gray-500
  newsletter:    '#0d9488',  // teal-600
  promo:         '#7c3aed',  // violet-600
  spam:          '#52525b',  // zinc-600
}
```

Apply via inline style only (`style={{ background: LABEL_COLORS[label] }}`),
never via generated class names. The lookup object lives in the component that
renders the badge, not in CSS.

---

## Typography

Font stack: `system-ui, -apple-system, sans-serif` — set once on `body`, never
overridden except for `font-family: inherit` on inputs and `<pre>` elements.

### Scale

| Size  | Weight | Usage                                          |
|-------|--------|------------------------------------------------|
| 22px  | 700    | App title `<h1>` — letter-spacing: -0.3px      |
| 19px  | 600    | Briefing section title (`h1` inside markdown)  |
| 17px  | 600    | Section heading ("Inbox")                      |
| 15px  | 600    | Email subject                                  |
| 15px  | 400    | Briefing `h2` labels                           |
| 14px  | 500    | Primary button label                           |
| 14px  | 600    | Briefing `h2` · draft panel subject            |
| 14px  | 400    | Briefing body copy · list items                |
| 13px  | 400    | Secondary button · input · status text · reason|
| 12px  | 600    | Label badge (+ `text-transform: capitalize`)   |
| 12px  | 400    | Email sender · email date                      |

Rules:
- Use **600** for anything that needs emphasis within body copy.
- Use **700** only for the top-level `<h1>`.
- Use **500** only for primary button labels.
- Never use 400 weight for anything smaller than 13px.
- Apply `letter-spacing: -0.3px` only on the app `<h1>`.
- `text-transform: capitalize` on label badges and live status strings only.
- `line-height: 1.5` on body; do not override per-element.

---

## Spacing & layout

### Page

```css
.app {
  max-width: 860px;
  margin: 0 auto;
  padding: 24px 16px 64px;  /* extra bottom so content breathes above fold end */
}
```

### Spacing scale (use these values only)

`3 · 4 · 6 · 8 · 10 · 12 · 14 · 16 · 20 · 24 · 28 · 56 · 64`

Common assignments:
- Between sibling cards: **6px** margin-bottom
- Between groups / sections: **24–28px**
- Card internal padding: **14px 16px** (compact) or **24px 28px** (panel)
- Action row gap: **8px**
- Header row gap: **12px**
- Sub-label gap: **8px**

### Layout

Everything is either `display: block` or `display: flex`. No CSS Grid.

| Pattern                    | Flex properties                                          |
|----------------------------|----------------------------------------------------------|
| Header (title + actions)   | `justify-content: space-between; align-items: center`    |
| Action row (buttons)       | `align-items: center; gap: 8px; flex-wrap: wrap`         |
| Meta row (sender vs date)  | `justify-content: space-between; align-items: baseline`  |
| Group header (badge+count) | `align-items: center; gap: 8px`                          |
| Header-right cluster       | `align-items: center; gap: 12px`                         |

Use `align-items: baseline` when two text elements of different sizes share a
row — it keeps their text baselines aligned rather than their boxes.

---

## Elevation & borders

Two shadow levels, used consistently:

```css
/* Card — list items, small surfaces */
box-shadow: 0 1px 2px rgba(0,0,0,0.05);

/* Panel — prominent content areas, section containers */
box-shadow: 0 1px 3px rgba(0,0,0,0.08);
```

Never use `box-shadow` for focus rings, hover effects, or decorative purposes.
If you need a third level of elevation, use a border instead of a stronger shadow.

Sub-panels and drawers that expand *inside* a card use a border (`1px solid #e4e4e7`)
with no shadow — they are contained by the parent card's elevation.

### Border radius

```
20px  — pill badges only
10px  — prominent panels (briefing section)
9px   — email cards
8px   — error banners, sub-panels
7px   — primary buttons
6px   — secondary/ghost buttons, inputs, small panels
```

The gradient is intentional: outer containers are slightly more rounded than
nested or smaller elements. Never exceed 10px on a container.

---

## Components

### Buttons

Three variants; choose by the weight of the action:

**Primary** — for the one most important action on the page.
```css
padding: 8px 20px;
background: #18181b;
color: #fff;
border: none;
border-radius: 7px;
font-size: 14px;
font-weight: 500;
transition: opacity 0.15s;
/* hover */ opacity: 0.85;
/* disabled */ opacity: 0.45; cursor: not-allowed;
```

**Secondary** — for contextual actions attached to content (e.g., "Draft reply").
```css
padding: 5px 13px;
background: #fff;
color: #18181b;
border: 1px solid #d4d4d8;
border-radius: 6px;
font-size: 13px;
transition: background 0.1s;
/* hover */ background: #f4f4f5;
```

**Ghost / muted** — for cancel, dismiss, low-priority actions.
```css
padding: 5px 13px;
background: transparent;
color: #71717a;
border: 1px solid #e4e4e7;
border-radius: 6px;
font-size: 13px;
/* hover */ background: #f4f4f5;
```

**Inverse-small** — a primary-weight button at secondary size. Use when a
result action (e.g., "View draft") needs emphasis without the full page-level
weight of the primary button.
```css
padding: 5px 13px;
background: #18181b;
color: #fff;
border: none;
border-radius: 6px;
font-size: 13px;
/* hover */ opacity: 0.85;
```

Rules:
- Always use `<button>` — never `<div onClick>` or `<a>`.
- Never mix variants in the same action row (e.g., don't put a primary next to a secondary).
- One primary button per view, maximum.
- Disabled state: `opacity: 0.45` + `cursor: not-allowed`. Never hide the button.

### Cards

The fundamental list-item container. White background, compact padding, subtle shadow.

```css
background: #fff;
border-radius: 9px;
padding: 14px 16px;
margin-bottom: 6px;
box-shadow: 0 1px 2px rgba(0,0,0,0.05);
```

Never add a border to a card — shadow provides the separation.

### Panels

For larger content areas (briefing section, settings, any prominent surface).

```css
background: #fff;
border-radius: 10px;
padding: 24px 28px;
margin-bottom: 28px;
box-shadow: 0 1px 3px rgba(0,0,0,0.08);
```

### Sub-panels (inline drawers)

Expand inside a card when a secondary result needs to be shown (e.g., draft
reply preview). Never use a modal overlay.

```css
margin-top: 12px;
border: 1px solid #e4e4e7;
border-radius: 8px;
overflow: hidden;
```

Sub-panel header bar:
```css
display: flex;
justify-content: space-between;
align-items: center;
padding: 10px 14px;
background: #fafafa;
border-bottom: 1px solid #e4e4e7;
```

Close button inside the header is a bare `<button>` — `background: none; border: none`
— with the `✕` character (U+2715). Font size 16px, color `#71717a`.

### Inputs

```css
padding: 5px 10px;
border: 1px solid #d4d4d8;
border-radius: 6px;
font-size: 13px;
font-family: inherit;
outline: none;
/* focus */ border-color: #a1a1aa;
```

- Always `font-family: inherit` — browsers default inputs to monospace.
- `outline: none` with border-color change on focus (no box-shadow ring).
- `autoFocus` when an input appears dynamically (e.g., expanding instruction field).
- Support `onKeyDown` Enter to submit alongside the submit button.

### Label badges

```jsx
<span
  className="label-badge"
  style={{ background: LABEL_COLORS[label] }}
>
  {label.replace('_', ' ')}
</span>
```

```css
padding: 2px 10px;
border-radius: 20px;
color: #fff;
font-size: 12px;
font-weight: 600;
text-transform: capitalize;
```

Inline style for color — never generate class names. The badge always appears
next to a count in muted text (`#71717a`, 13px, 400).

### Status text

Inline `<span>` with a semantic color class. No container, no icon, no spinner.

```css
.draft-status { font-size: 13px; color: #71717a; text-transform: capitalize; }
.draft-error  { font-size: 13px; color: #b91c1c; }
```

For in-progress states, append the current step name: `"Drafting… (reviewing)"`.
Steps are always lowercase, always followed by the ellipsis character `…` (U+2026),
never `...`.

### Error banners

Full-width block. No icon. Appears above the content it relates to.

```css
background: #fee2e2;
color: #b91c1c;
padding: 12px 16px;
border-radius: 8px;
font-size: 14px;
margin-bottom: 20px;
```

### Empty states

Centered text, generous vertical padding. The call-to-action is `<strong>` inline.
No illustration, no button — tell the user what to do with words.

```css
text-align: center;
padding: 56px 16px;
color: #71717a;
font-size: 15px;
```

---

## Animation & transitions

**Two transitions exist in the codebase. No others.**

```css
transition: opacity 0.15s;      /* primary buttons — hover + disabled */
transition: background 0.1s;    /* secondary/ghost buttons — hover */
```

Rules:
- Do not add `transform`, `scale`, `translate`, or `keyframe` animations.
- Do not animate height, max-height, or display for expand/collapse — React
  conditionally renders the element instead (instant mount/unmount).
- Do not add `transition` to borders, shadows, colors, or sizes.
- If you feel a component needs animation to communicate a state change, reconsider
  the state — it should be obvious from layout and text alone.
- Loading states use text (`"Running…"`, `"Drafting…"`) not spinners.

---

## Accessibility

- Use semantic HTML elements: `<button>`, `<header>`, `<section>`, `<h1>`–`<h3>`,
  `<strong>`, `<pre>`. Never use `<div onClick>`.
- `disabled` attribute on buttons that cannot be activated — not just `opacity`.
- Every input that appears dynamically gets `autoFocus`.
- Color is never the only signal: status text always accompanies a color change,
  label badges always show the label name, error banners always include the message.
- `cursor: not-allowed` on disabled buttons (in addition to `opacity: 0.45`).
- `white-space: pre-wrap` on `<pre>` so long lines wrap instead of causing
  horizontal scroll.
- Sufficient contrast: all text on white backgrounds is `#52525b` or darker.
  Muted text (`#71717a`) at 13px+ meets WCAG AA for normal text.

---

## React patterns

### Phase state machines

For any UI that has more than two states (idle → active → done), use a named
phase string rather than multiple booleans.

```js
// correct
const [phase, setPhase] = useState(null)
// null | 'input' | 'pending' | 'done' | 'failed'

// wrong
const [loading, setLoading] = useState(false)
const [success, setSuccess] = useState(false)
const [error, setError] = useState(false)
```

Render conditionally per phase with `{phase === 'input' && ...}` blocks.
Transitions between phases are synchronous and instant — no animation needed.

### Polling

```js
const pollRef = useRef(null)

// start
pollRef.current = setInterval(async () => {
  const result = await poll()
  if (result.status === 'done' || result.status === 'failed') {
    clearInterval(pollRef.current)
    // update phase
  }
}, 2000)

// cleanup (always)
useEffect(() => () => clearInterval(pollRef.current), [])
```

- Always 2000ms interval.
- Always clear on terminal states (`done`, `failed`).
- Always clean up in `useEffect` return — handles unmount during pending state.
- Swallow errors inside the interval (`catch {}`) — keep polling on transient failures.

### Inline styles

Use inline style **only** for values that come from data (e.g., label color from
a lookup map). All other styles go in `index.css`. Never generate class names
dynamically.

```jsx
// correct — data-driven color
<span style={{ background: LABEL_COLORS[label] }} />

// wrong — dynamic class
<span className={`badge badge-${label}`} />
```

### Component ownership

Each component owns its own async state. `App` owns the run job. `EmailCard`
owns its draft job. Don't hoist draft state into `App` — it would require
threading state and callbacks through props with no benefit.

---

## What NOT to do

- No CSS custom properties / variables. All values are written directly.
- No CSS framework (Tailwind, Bootstrap, etc.).
- No icon library. Use text and the `✕` character.
- No modal/overlay. Expand inline.
- No loading spinners. Use status text.
- No animation beyond the two existing transitions.
- No dark mode.
- No `!important`.
- No generated or dynamic class names.
- No new colors outside the Zinc scale and the label color map.
- No `<div>` as an interactive element.
- No inline `style` for anything that isn't data-driven.
