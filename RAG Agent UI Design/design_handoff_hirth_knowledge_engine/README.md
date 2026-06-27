# Handoff: Hirth Knowledge Engine — RAG Agent UI

## Overview
A full-screen internal RAG (Retrieval-Augmented Generation) agent for Hirth Engines staff. Users ask natural-language questions about two-stroke engine documentation; the system retrieves grounded answers from an internal vector store or the live web, shows citations, flags conflicting web signals, and lets any user propose corrections that get re-embedded into the vector space.

---

## About the Design Files
The files bundled here (`Hirth Knowledge Engine.dc.html`, `support.js`) are **high-fidelity design prototypes** — they run in a browser and show the exact intended look, copy, interactions and transitions. They are **not** production code to copy directly.

Your task is to **recreate these designs in your existing backend-connected stack** (React, Next.js, or whatever framework your backend targets) using your established patterns and libraries. Treat the HTML files as a living spec: open them in a browser alongside your implementation to compare pixel-by-pixel.

The prototype uses **simulated data throughout** — every API call, embedding, and web search is mocked. Your job is to wire the same UI to your real backend endpoints.

---

## Fidelity
**High-fidelity.** Final colors, typography, spacing, shadows, transitions and interaction states are all specified. Recreate pixel-accurately; do not substitute your own design system unless instructed.

---

## Screens / Views

### 1. App Shell

**Layout:** Fixed full-screen (`position: fixed; inset: 0`). Vertical flex column. Top bar (66 px) + body (flex: 1, min-height: 0).

**Background:**
```
background-color: #eef1f7;
background-image:
  radial-gradient(1000px 680px at 82% -12%, rgba(51,88,224,.14), transparent 58%),
  radial-gradient(760px 520px at -5% 112%,  rgba(51,88,224,.09), transparent 60%),
  linear-gradient(rgba(20,40,90,.03) 1px, transparent 1px),
  linear-gradient(90deg, rgba(20,40,90,.03) 1px, transparent 1px);
background-size: auto, auto, 46px 46px, 46px 46px;
```

---

### 2. Top Bar

Height: 66 px. `background: rgba(255,255,255,.72); backdrop-filter: blur(10px); border-bottom: 1px solid #e1e5ed;`

**Left — Hirth Logo:**
- `HIRTH` wordmark: `font: 800 23px 'Space Grotesk'; letter-spacing: .3px; color: #16245e`
- Badge: 40×40 px SVG, `border-radius: 10px`, background `#1f4ba8`, white H-shape inside (skewed −8°)
- `ENGINES` sub-label: `font: 600 9px 'IBM Plex Mono'; letter-spacing: 7px; color: #2456b0`
- Divider: 1 px wide, 26 px tall, `background: #dde2ea`
- `KNOWLEDGE ENGINE` label: `font: 500 11px 'IBM Plex Mono'; color: #98a0ac; letter-spacing: 2px`

**Right — Nav + Status:**
- Segmented control (Ask / Upload): `background: #f3f5f9; border: 1px solid #e4e8ef; border-radius: 11px; padding: 3px`
  - Each button: `border-radius: 8px; padding: 7px 15px; font: 600 12px 'Space Grotesk'`
  - Active state: `background: #fff; color: #3358e0; box-shadow: 0 1px 2px rgba(20,30,60,.10)`
  - Inactive state: `background: transparent; color: #5a626e`
- Vector status: `font: 500 11px 'IBM Plex Mono'; color: #14a08a` with a 7 px green dot
- Avatar: 32×32 px circle, `background: #eef1f7; border: 1px solid #d6dbe4; font: 600 12px 'Space Grotesk'; color: #5a626e`

**API connection:** Fetch document count and vector count from your index metadata endpoint on mount. Display as `{n} docs · {n} vectors`.

---

### 3. Ask View — Explore (landing / empty state)

Shown when no query has been submitted. Centered vertically in the content area. `padding-bottom: 150px` to leave room for the pinned query bar.

**Hero text:**
- Eyebrow: `font: 500 11px 'IBM Plex Mono'; color: #3358e0; letter-spacing: 3px` → `HIRTH KNOWLEDGE ENGINE`
- Headline: `font: 400 52px/1.1 'Newsreader', serif; color: #14181f; max-width: 760px; letter-spacing: -0.5px`  
  Text: `Ask anything about Hirth` + italic blue `two-stroke` + ` engines.`  
  Italic span: `font-style: italic; color: #3358e0`
- Sub: `font: 400 15px/1.6 'Space Grotesk'; color: #5a626e; max-width: 520px`

**Topic chips** (8 chips, flex-wrap, centered):
- Chip: `background: rgba(255,255,255,.85); border: 1px solid #e1e5ed; border-radius: 30px; padding: 9px 15px`
- Hover: `border-color: #3358e0; background: #fff`
- Colored dot (9 px, domain color) + `font: 500 13px 'Space Grotesk'; color: #14181f`
- Topics: Expansion Chamber (blue), Carburetor (cyan), Ignition Timing (amber), Port Timing (blue), Premix & Lubrication (slate), Cooling (teal), Detonation (amber), Reed Valve (cyan)

Clicking a chip pre-fills and submits the query for that domain.

---

### 4. Ask View — Answer state

Triggered on query submit. Two-column layout filling the content area (`padding: 18px; gap: 16px; padding-bottom: 96px` to clear the query bar).

#### 4a. Answer Panel (left, 57% width)
White card: `background: #fff; border: 1px solid #e1e5ed; border-radius: 16px; box-shadow: 0 1px 3px rgba(20,30,60,.05), 0 18px 40px -24px rgba(20,30,60,.18); animation: hk-rise .4s ease`

**Header section** (`padding: 18px 24px 14px; border-bottom: 1px solid #eef0f4`):
- "You asked" label: `font: 500 10px 'IBM Plex Mono'; color: #aab2be; letter-spacing: 1px`
- Query echo: `font: 400 13px 'IBM Plex Mono'; color: #5a626e; overflow: hidden; text-overflow: ellipsis; white-space: nowrap`
- **Latency pill:** `font: 500 11px 'IBM Plex Mono'; color: #5a626e; background: #f3f5f9; border: 1px solid #e4e8ef; padding: 4px 9px; border-radius: 7px` — lightning bolt `↯` in `#3358e0` + `{Xs} latency`
- **Cost pill:** same style — `$` in `#14a08a` + `{$X.XXXX} cost`
- **Mode badge:** same style but dynamic color — Knowledge base = teal `#14a08a` / Web = blue `#3358e0`, with matching bg/border
- **"Review & update" button** (top-right): `background: #f3f5f9; border: 1px solid #d6dbe4; font: 600 12px 'Space Grotesk'; padding: 8px 14px; border-radius: 9px`; hover: `border-color: #3358e0; color: #3358e0`

**API connections for header:** Your backend should return `latency_ms`, `cost_usd`, `source` (`knowledge_base` | `web`) per query response.

**Body** (scrollable, `padding: 20px 24px`):
- Domain dot (9 px) + `font: 600 10px 'IBM Plex Mono'; letter-spacing: 1px; text-transform: uppercase` in domain color
- Updated date: `font: 500 11px 'IBM Plex Mono'; color: #aab2be`
- **Answer headline:** `font: 500 32px/1.18 'Newsreader', serif; color: #14181f; letter-spacing: -0.3px`
- **Source banner** (tinted box): teal bg `#f4faf8` / blue bg `#f6f8fe` with matching border and icon
- **Confidence bar:** `height: 6px; background: #e9ecf2; border-radius: 4px`; fill: `linear-gradient(90deg, #3358e0, #4a6cf0)`. Label: `font: 600 12px 'IBM Plex Mono'; color: #14181f`
- **Answer body text:** `font: 400 15.5px/1.72 'Newsreader', serif; color: #39414e`
- **Sources section label:** `font: 600 10px 'IBM Plex Mono'; color: #aab2be; letter-spacing: 1px`
- **Doc source row:** `background: #f7f8fb; border: 1px solid #e4e8ef; border-radius: 10px; padding: 11px 13px` — PDF badge + doc name + page ref
- **Web source row** (Web mode): `background: #f4f7fd; border: 1px solid #d9e2f7; border-radius: 10px` — WEB badge (blue) + title + "open ↗" link

**API connections:** `GET /api/query` → `{ answer, domain, confidence, latency_ms, cost_usd, source, body, sources: [{type, title, page?, url?}], updated }`

---

#### 4b. Right Column (flex: 1)

**Related Domains card:**
- White card, `border-radius: 16px`, standard border/shadow
- Header: `padding: 13px 16px; border-bottom: 1px solid #eef0f4`; "Related domains" `font: 600 12px 'Space Grotesk'; color: #14181f`
- Each row: full-width button, `padding: 9px 10px; border-radius: 9px`; hover `background: #f3f5f9`
  - Domain color dot + label (`font: 500 13px 'Space Grotesk'`) + confidence (`font: 500 10px 'IBM Plex Mono'; color: #aab2be`) + `→` arrow
  - Clicking a related domain re-queries the agent for that topic

**Around the Web card** (flex: 1, scrollable):
- Same card style
- Header chip (top-right): amber `3 NEED REVIEW` or blue `PRIMARY SOURCE` depending on web mode
- Each web item: `background: #f7f8fb; border: 1px solid #e4e8ef; border-left: 2px solid {domain-color}; border-radius: 10px; padding: 11px 13px`
  - Tag badge: `font: 600 9px 'IBM Plex Mono'; letter-spacing: .5px` in signal color
  - Source + date: `font: 400 10px 'IBM Plex Mono'; color: #aab2be`
  - Title: `font: 500 13px/1.4 'Space Grotesk'; color: #14181f`
  - Relevance: `font: 500 10px 'IBM Plex Mono'; color: #98a0ac`
  - "open ↗": `font: 600 11px 'Space Grotesk'; color: #3358e0` — opens URL in new tab
  - Hover: `border-color: #cfd5df; background: #f1f4f9`

**API connections:** `GET /api/web-signals?topic={id}` → `[{ url, source, date, tag, color, title, relevance }]`

---

### 5. Query Bar (pinned bottom, Ask view)

`position: absolute; bottom: 0; left: 0; right: 0; z-index: 30; padding: 0 18px 22px`

Centered max-width 740 px pill:
`background: #fff; border: 1px solid {barBorder}; border-radius: 14px; padding: 8px 8px 8px 12px; box-shadow: 0 18px 50px -20px rgba(20,30,60,.30), {ringIfWebOn}`

**Web-mode-on ring:** `box-shadow: …, 0 0 0 3px rgba(51,88,224,.10)` + border becomes `#3358e0`

**+ button** (left): 38×38 px, `background: #f3f5f9; border: 1px solid #d6dbe4; border-radius: 10px; color: #5a626e; font-size: 22px`; hover: `border-color: #3358e0; color: #3358e0`. Navigates to Upload view.

**Web toggle button**: `height: 38px; padding: 0 12px; border-radius: 10px` — globe SVG (circle + lat/long lines, 17×17 px, stroke-width 1.6) + label
- Off: `background: #f3f5f9; border: 1px solid #d6dbe4; color: #5a626e` / label `Web`
- On: `background: #3358e0; border: #3358e0; color: #fff` / label `Web · on`

**Text input:** `font: 400 15px 'Space Grotesk'; color: #14181f; placeholder-color: #aab2be`

**Submit →** button: 38×38 px, `background: #3358e0; border-radius: 10px; color: #fff; font: 600 17px 'IBM Plex Mono'`; hover: `background: #4a6cf0`

**Clear** button (only in answer state): `background: #f3f5f9; border: 1px solid #d6dbe4; height: 38px; padding: 0 13px; font: 500 12px 'Space Grotesk'; color: #5a626e`

**API connection:** On submit → `POST /api/query` with `{ query: string, mode: "knowledge_base" | "web" }`. Stream or await JSON response. Show answer panel on success.

---

### 6. Review & Update Overlay

Triggered by "Review & update" button. Full-screen overlay: `background: rgba(20,30,60,.30); backdrop-filter: blur(3px)`.

Modal: `max-width: 1100px; max-height: 680px; background: #fff; border-radius: 18px; border: 1px solid #e1e5ed; box-shadow: 0 40px 100px -30px rgba(20,30,60,.45); animation: hk-rise .25s ease`

**Header:** "Review & update answer" (`font: 600 14px 'Space Grotesk'`) + subtitle + ✕ close button

**Left pane** (50%, scrollable): Current answer read-only view. Same typography as answer panel. Confidence + version badges at bottom.

**Right pane** (50%): `YOUR UPDATE` label in `#3358e0`.
- Instructional copy in `#5a626e`
- Textarea: `background: #f7f8fb; border: 1px solid #d6dbe4; border-radius: 11px; padding: 13px 14px; font: 400 14px/1.6 'Space Grotesk'; color: #14181f`
- Action chips: Cite source / Attach document / Link web signal
- **"Update vector space" button:** `background: #3358e0; height: 44px; border-radius: 11px; font: 600 13px 'Space Grotesk'; color: #fff`; hover `#4a6cf0`
- **Cancel:** `background: #f3f5f9; border: 1px solid #d6dbe4`

**Success state** (after submission):
- Teal check circle (64 px, `border: 1px solid #14a08a; background: rgba(20,160,138,.10)`)
- "Vector space updated" in `font: 500 20px 'Newsreader', serif`
- Sub-copy with new confidence in `#14a08a`
- Auto-closes modal after ~2 s

**API connection:** `POST /api/answers/{id}/update` with `{ text: string, citations?: string[] }` → re-embeds and returns new confidence + version. On success show the success state, then close.

---

### 7. Upload View

Replaces the content area when "Upload" is active.

**Stats row** (3 equal cards): `background: #fff; border: 1px solid #e1e5ed; border-radius: 12px; padding: 18px`
- Documents count (black), Vectors count (blue `#3358e0`), Fresh indexed (teal `#14a08a`)

**Drop zone:** `height: 180px; border: 1.5px dashed #cfd5df; border-radius: 14px; background: #f7f8fb`; hover: `border-color: #3358e0; background: #f1f5fd`
- Upload icon: 52×52 px, `border-radius: 13px; background: #fff; border: 1px solid #d6dbe4; color: #3358e0; font-size: 28px`
- Accepted: PDF · DOCX · XLSX · TXT

**Document list:** Each row `background: #fff; border: 1px solid #e1e5ed; border-radius: 11px; padding: 13px 15px`
- File-type badge (34×34 px) + filename + size + progress bar (4 px, teal when indexed / blue when embedding)
- Status badge: `INDEXED` (teal) / `EMBEDDING` (blue)

**API connections:**
- `GET /api/documents` → list of indexed docs with status
- `POST /api/documents/upload` (multipart) → streams embedding progress
- `GET /api/index/stats` → `{ doc_count, vector_count, fresh_count }`

---

## Interactions & Behavior

| Interaction | Behavior |
|---|---|
| Click topic chip | Pre-fills query + submits immediately → answer state |
| Press Enter in query bar | Submits query |
| Click + | Navigates to Upload view |
| Click Web toggle | Switches mode; bar border turns blue with ring; placeholder changes |
| Click Clear | Returns to explore state, clears query |
| Click related domain row | Re-submits query for that domain |
| Click ⟳ Review & update | Opens review overlay |
| Submit update in overlay | Shows success state for 1.9 s → auto-closes |
| Drop files on drop zone | Starts upload → progress bar fills → badge flips to INDEXED |

**Animations:**
- `hk-rise`: `from { opacity:0; transform:translateY(10px) } to { opacity:1; transform:translateY(0) }` — duration `.4s ease`
- `hk-fade`: `from { opacity:0 } to { opacity:1 }` — duration `.4s ease`
- Answer panel entrance: `animation: hk-rise .4s ease`
- Right column entrance: `animation: hk-rise .5s ease`
- Review overlay entrance: `animation: hk-rise .25s ease`

---

## State Management

```
{
  view: 'graph' | 'upload',          // which top-level tab is active
  mode: 'explore' | 'answer',        // ask view sub-state
  query: string,                     // live input value
  submittedQuery: string,            // last submitted query
  selectedDomain: string,            // domain id for the current answer
  webMode: boolean,                  // web toggle on/off
  reviewOpen: boolean,
  reviewDone: boolean,
  reviewText: string,
  toast: string | null,
  docs: Document[],                  // upload view list
}
```

---

## Design Tokens

### Colors
| Token | Value | Usage |
|---|---|---|
| `brand-navy` | `#16245e` | HIRTH wordmark |
| `brand-blue` | `#1f4ba8` | Logo badge bg |
| `accent` | `#3358e0` | Primary CTA, active states, links |
| `accent-hover` | `#4a6cf0` | Button hover |
| `bg-base` | `#eef1f7` | App background |
| `bg-panel` | `#fff` | Cards |
| `bg-raised` | `#f3f5f9` | Secondary buttons, inputs |
| `bg-sunken` | `#f7f8fb` | Source rows |
| `border` | `#e1e5ed` | Card borders |
| `border-inner` | `#eef0f4` | Internal dividers |
| `text-primary` | `#14181f` | Body, headlines |
| `text-secondary` | `#39414e` | Answer body prose |
| `text-muted` | `#5a626e` | Labels, secondary |
| `text-faint` | `#98a0ac` | Timestamps, meta |
| `text-placeholder` | `#aab2be` | Input placeholders |
| `green` | `#14a08a` | Knowledge base mode, indexed, success |
| `amber` | `#d98a1f` | Ignition / regulation signals |
| `cyan` | `#1f9bd1` | Fuel / forum signals |
| `slate` | `#6b7384` | Lubrication domain |
| `domain-combustion` | `#3358e0` | |
| `domain-fuel` | `#1f9bd1` | |
| `domain-ignition` | `#d98a1f` | |
| `domain-cooling` | `#18a08a` | |
| `domain-oil` | `#6b7384` | |

### Typography
| Face | Weights | Usage |
|---|---|---|
| `Newsreader` (serif) | 400, 500, 600 | Answer headlines, body prose, modal headings |
| `Space Grotesk` (sans) | 400, 500, 600, 700 | All UI labels, buttons, nav |
| `IBM Plex Mono` (mono) | 400, 500, 600 | Meta labels, stats, badges, query input |

### Spacing / Radius
- Card radius: `16px` (main), `11–12px` (smaller cards), `9–10px` (rows), `7–8px` (chips/buttons)
- Standard card shadow: `0 1px 3px rgba(20,30,60,.05), 0 18px 40px -24px rgba(20,30,60,.18)`
- Content area padding: `18px` with `16px` gap between columns

---

## Backend API Summary

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/query` | POST | Submit a query; returns answer, sources, latency, cost, confidence |
| `/api/web-signals` | GET | Live web signals for a topic |
| `/api/answers/:id/update` | POST | Submit a correction; re-embeds into vector space |
| `/api/documents` | GET | List indexed documents |
| `/api/documents/upload` | POST | Upload + embed new documents |
| `/api/index/stats` | GET | Total docs, vectors, fresh count |

Your backend is already working — wire these endpoints to the UI state described above. The prototype mocks all of them with static data you can use as fixture/response shapes.

---

## Assets
- **Hirth logo** — recreated as inline SVG in the prototype; use the real SVG/PNG from your brand assets if available
- **Fonts** — loaded from Google Fonts (`Newsreader`, `Space Grotesk`, `IBM Plex Mono`); self-host in production

---

## Files in This Bundle
| File | Description |
|---|---|
| `Hirth Knowledge Engine.dc.html` | Main prototype — open in any browser to reference |
| `support.js` | Runtime required to run the prototype locally |
| `README.md` | This document |

Open `Hirth Knowledge Engine.dc.html` locally (needs `support.js` in the same folder) to interact with the full prototype as you build.
