# UI Style Guide — AI Incident Triage Agent

> Design language: **calm, premium security operations console** — deep ink, restrained cyan-indigo accent, soft glow only where it carries meaning.  
> Reference: Linear / Vercel / Datadog. Elegant, not neon.

---

## 1. Design Tokens

All tokens live in `web-ui/src/index.css` as CSS custom properties and are mapped into `tailwind.config.js`.

### Backgrounds

| Token             | Value       | Usage                                   |
|------------------|-------------|-----------------------------------------|
| `--bg`            | `#080d1a`   | Deepest page background                 |
| `--surface`       | `#0f172a`   | Card / panel surface                    |
| `--surface-2`     | `#172033`   | Elevated input, table header, secondary |
| `--surface-hover` | `#1a2642`   | Interactive hover state                 |

### Borders

| Token             | Value                      | Usage                        |
|------------------|---------------------------|------------------------------|
| `--border`        | `rgba(255,255,255, 0.07)` | Default 1 px hairline        |
| `--border-strong` | `rgba(255,255,255, 0.14)` | Hover / focus elevated state |

### Text — WCAG AA verified on `--bg`

| Token           | Value     | Contrast on `--bg` | Usage                 |
|----------------|-----------|--------------------|-----------------------|
| `--text`        | `#e2e8f0` | 11.6 : 1           | Primary body / labels |
| `--text-muted`  | `#94a3b8` | 5.3 : 1            | Secondary text        |
| `--text-faint`  | `#475569` | 2.9 : 1            | Placeholder / micro   |

> **Note:** `--text-faint` falls below AA — use only for decorative or non-essential text (placeholder, dividers). Never for meaningful content.

### Accent

| Token               | Value                                     | Usage                              |
|--------------------|-------------------------------------------|------------------------------------|
| `--accent`          | `#22d3ee` (cyan-400)                     | Primary interactive, active tab    |
| `--accent-2`        | `#818cf8` (indigo-400)                   | Secondary highlight, approval      |
| `--accent-gradient` | `linear-gradient(135deg, #0ea5e9, #6366f1)` | CTA button fill                 |
| `--accent-glow`     | `rgba(34,211,238, 0.18)`                 | Focus ring shadow                  |

### Semantic

| Token           | Value     | Tint (`/10`)                     | Usage                |
|----------------|-----------|----------------------------------|----------------------|
| `--success`     | `#34d399` | `rgba(52,211,153, 0.10)`        | Healthy, completed   |
| `--warning`     | `#fbbf24` | `rgba(251,191,36, 0.10)`        | Suspect, mutating    |
| `--danger`      | `#f87171` | `rgba(248,113,113, 0.10)`       | Error, blocked       |
| `--info`        | `#60a5fa` | `rgba(96,165,250, 0.10)`        | LLM turn, info       |

### Radius Scale

| Token          | Value  | Usage                    |
|---------------|--------|--------------------------|
| `--radius-sm` | `4px`  | Badges, `kbd` keys       |
| `--radius-md` | `8px`  | Inner items              |
| `--radius-lg` | `12px` | Buttons, chips           |
| `--radius-xl` | `16px` | Cards, main panels       |

### Shadow Scale

| Name              | Value                              | Usage                     |
|------------------|-------------------------------------|---------------------------|
| `--shadow-sm`     | `0 1px 2px rgba(0,0,0,0.5)`       | Default card elevation    |
| `--shadow-md`     | `0 4px 12px rgba(0,0,0,0.4)`      | Hover card, modal         |
| `--shadow-lg`     | `0 8px 24px rgba(0,0,0,0.5)`      | Floating elements         |
| `--shadow-glow`   | `0 0 16px rgba(34,211,238,0.14)`  | Accent glow, logo         |

---

## 2. Typography

### Fonts

- **UI font:** [Inter](https://rsms.me/inter/) — headings, body, buttons, chips, nav labels.  
- **Code font:** [JetBrains Mono](https://www.jetbrains.com/lp/mono/) — **only** for: tool names, JSON payloads, IDs, commit hashes, timestamps, trace data.

Both are loaded via Google Fonts with `font-display: swap` to prevent layout shift.

### Type Scale (utility classes in `index.css`)

| Class               | Size       | Weight | Usage                                       |
|--------------------|------------|--------|---------------------------------------------|
| `.text-page-title`  | 1.5 rem    | 700    | Rare page-level headings                    |
| `.text-section-title` | 1 rem    | 600    | Tab-panel headings (History, Benchmarks…)   |
| `.text-card-title`  | 0.875 rem  | 600    | Card header label                           |
| `.text-body`        | 0.875 rem  | 400    | General body text                           |
| `.text-caption`     | 0.75 rem   | 400    | Helper text, tooltips                       |
| `.text-micro`       | 0.6875 rem | 600    | ALL-CAPS section labels (MCP INFRASTRUCTURE)|

> Use `.tabular-nums` on counters, durations, timestamps so digits don't reflow.

---

## 3. Layout and Spacing

- **Max width:** `1360px` (`max-w-content`), centered, 24 px (`px-6`) gutters.
- **Card padding:** `1rem` (16 px) standard, `1.25 rem` (20 px) for dense panels.
- **Card gap:** `1.25 rem` (20 px) between sibling cards.
- **Spacing grid:** 4 px base. Use multiples: 4, 8, 12, 16, 20, 24, 32, 48 px.

### Investigate page grid

```
┌─ header (sticky, 56px, blur) ───────────────────────────────────┐
│ logo·title   Investigate  History  Benchmarks  Traces   13 tools│
└─────────────────────────────────────────────────────────────────┘
┌─ rail (340px sticky) ──────┬─ main (fluid) ────────────────────┐
│ HealthPanel                │ QueryBar (48px input + gradient btn)│
│  └ ServerRow × 2           │ Run status bar                      │
│  └ footer: count + status  │ EventTimeline (overflow scroll)     │
│ RunHistory                 │  └ EmptyState / LiveTimeline rows   │
│  └ HistoryRow × n          │                                     │
└────────────────────────────┴─────────────────────────────────────┘
```

**Responsive breakpoints:**
- `< 1024px`: rail stacks above main content.
- `< 640px`: tabs become a horizontally scrollable row; chips wrap.

---

## 4. Component Catalogue

### `Card` (`src/components/ui.tsx`)
```tsx
<Card>                        // --surface bg, hairline border, --radius-xl
<Card hoverable>              // adds card-hover: border lifts on hover
<Card raised>                 // --surface-2 bg, --border-strong, --shadow-md
```

### `SectionHeader`
```tsx
<SectionHeader icon={<Server />} label="MCP INFRASTRUCTURE" action={<RefreshButton />} />
```
Renders an ALL-CAPS micro-label with optional icon, count pill, and right-aligned action slot.

### `Badge` (`src/components/Badge.tsx`)
```tsx
<Badge variant="green" dot>HEALTHY</Badge>
<Badge variant="amber" pulseDot>mutating</Badge>
```
Variants: `default | cyan | green | red | amber | orange | slate | violet`  
Has optional `dot` (static) or `pulseDot` (animated via `pulse-live`).

### `Chip` (`src/components/ui.tsx`)
```tsx
<Chip icon={<AlertTriangle />} iconColor="text-red-400" label="Payments Root Cause" onClick={fn} />
```
Used for quick-action prompt shortcuts. Quiet surface fill, hover lifts border.

### `IconButton`
```tsx
<IconButton title="Refresh" spinning={isRefreshing}>
  <RefreshCw className="h-3.5 w-3.5" />
</IconButton>
```
7×7 (28 px) touch target, `spin` class applied while `spinning`.

### `RunStatusIcon` / `ToolStatusIcon`
Maps `RunState` / `ToolStatus` → icon + color. `running` state auto-spins.

### `relativeTime(iso: string)`
Returns `"2m ago"`, `"1h ago"`, etc. Full ISO timestamp is in a `title` attribute for hover.

---

## 5. Interactive Patterns

### Primary button (Investigate)
```css
.btn-primary { background: var(--accent-gradient); color: #fff; border-radius: var(--radius-lg); }
```
- **Hover:** `opacity: 0.92` + 20px cyan glow.
- **Active:** `scale(0.97)`.
- **Loading:** replaces icon with `<Loader2 spin />`, label becomes "Investigating…".
- **Disabled:** `opacity: 0.35`.

### Stop / Cancel button
```css
.btn-danger { background: rgba(248,113,113,0.15); border: 1px solid rgba(248,113,113,0.3); }
```
Appears only while `isRunning`. Hover deepens tint.

### Input focus
```
border: 1px solid var(--accent);
box-shadow: 0 0 0 3px var(--accent-glow);
```

### Focus rings (keyboard nav)
All focusable elements use `.focus-ring` → `outline: 2px solid var(--accent); outline-offset: 2px` on `:focus-visible`.

---

## 6. Motion

All animations respect `prefers-reduced-motion: reduce` — the CSS block at the bottom of `index.css` disables them.

| Animation        | Duration  | Usage                                       |
|-----------------|-----------|---------------------------------------------|
| `.fade-slide-in` | 180 ms    | Each new timeline event appearing           |
| `.pulse-live`    | 2.4 s     | Healthy server dot, pending approval dot    |
| `.spin`          | 1.2 s     | Icon spinner (Loader2, RefreshCw)           |
| `.skeleton`      | 1.4 s     | Shimmer placeholder while loading           |
| Hover lift       | 150 ms    | `card-hover`: border + shadow transition    |
| Button press     | 100 ms    | `scale(0.97)` on `:active`                  |

> Use glow shadows (`--shadow-glow`, `.glow-violet`, etc.) sparingly — only for elements that actively demand attention: running state, approval card, security banners.

---

## 7. Status Color Reference

| State / Status        | Color       | Tailwind class       |
|-----------------------|-------------|----------------------|
| completed / ok        | emerald-400 | `text-emerald-400`   |
| running               | cyan-400    | `text-cyan-400`      |
| awaiting_approval     | violet-400  | `text-violet-400`    |
| failed / error        | red-400     | `text-red-400`       |
| cancelled             | slate-500   | `text-slate-500`     |
| blocked               | red-400     | `text-red-400`       |
| rejected              | amber-400   | `text-amber-400`     |
| injection detected    | red-400     | SecurityBanner/red   |

> **Rule:** never color alone — always pair with an icon (`RunStatusIcon`, `ToolStatusIcon`, or `ShieldAlert`).

---

## 8. Security Rendering Rules (unchanged, do not weaken)

- Tool output, logs, file contents → `<pre>` / `<code>` as plain text, never HTML.
- Final answers → sanitizing Markdown renderer inside a `<pre>` block.
- `dangerouslySetInnerHTML` is **never** used on untrusted content.
- No remote images; all images are local (`/logo.png`, etc.).
- `SecurityBanner` renders injection and path-traversal warnings in visually prominent red/amber banners with quoted, monospace text for the offending content.

---

## 9. Accessibility

- WCAG AA contrast for all meaningful text (`--text` and `--text-muted` on `--surface`/`--bg`).
- Every icon button has `title` + `aria-label`.
- Timeline has `aria-live="polite"` for screen-reader streaming.
- Approval card's Reject button has `autoFocus` (most conservative default action).
- Tab nav uses `role="tab"` / `aria-selected`.
- History rows use `role="button"` + keyboard handler (`Enter` / `Space`).

---

## 10. File Map

```
web-ui/
├── index.html                  ← font preconnects + preload links
├── tailwind.config.js          ← token colors, font families, shadows, animations
└── src/
    ├── index.css               ← CSS custom properties (single source of truth)
    ├── App.tsx                 ← page layout, header, tabs, all tab content
    ├── utils.ts                ← cn(), formatMs(), formatTimestamp(), status helpers
    ├── components/
    │   ├── ui.tsx              ← Card, SectionHeader, IconButton, Chip, RunStatusIcon,
    │   │                          ToolStatusIcon, relativeTime
    │   ├── Badge.tsx           ← polymorphic Badge with dot/pulseDot variants
    │   ├── HealthPanel.tsx     ← MCP server cards, skeleton loading, status footer
    │   ├── RunHistory.tsx      ← clickable history rows, relative timestamps
    │   ├── QueryBar.tsx        ← 48px input, gradient CTA, Try: chips
    │   ├── EventTimeline.tsx   ← EmptyState, timeline line, all event row types
    │   ├── ApprovalCard.tsx    ← violet-tinted approval panel, Reject-focused
    │   └── SecurityBanner.tsx  ← injection / blocked / rejection banners
    └── hooks/                  ← useHealth, useRunStream (unchanged)
```
