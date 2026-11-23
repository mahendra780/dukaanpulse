
# DukaanPulse: UI/UX Design Brief

|                             |                                                                                                                                                     |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Product**           | DukaanPulse                                                                                                                                         |
| **Document type**     | UI/UX Design Brief: brand, colour, type, spacing, components, screens and behaviour                                                                 |
| **Source files**      | `frontend/src/tokens.css` (all values below), `frontend/src/index.css`, `components/Logo.jsx`                                                 |
| **Related documents** | [PRD](01-PRD.md), [TRD](02-TRD.md), [App Flow](03-APP-FLOW.md), [Backend Schema](05-BACKEND-SCHEMA.md), [Implementation Plan](06-IMPLEMENTATION-PLAN.md) |

> **Rule of this brief.** Every colour, size and spacing in the interface must come from a token in section 3 to 6. If a value is not in this document, it should not be in the code.

---

## 1. Design intent

### 1.1 Who we design for

Wholesale shop owners and their staff. They are busy, often on a phone, and not technical. They read numbers all day and need to trust them.

### 1.2 Personality

**Traditional, trustworthy, warm.** It should feel like a well-kept ledger in a respected shop, not like a flashy startup dashboard.

| We are                             | We are not                            |
| ---------------------------------- | ------------------------------------- |
| Calm and clear                     | Loud or crowded                       |
| Honest about numbers               | Decorative at the cost of readability |
| Warm, with a touch of the old shop | Cold and corporate                    |
| Quick and responsive               | Slow with spinners                    |

### 1.3 The one memorable idea

The **shop awning**. A brass scalloped awning is the signature of the brand. It appears in the logo, hangs along the edges of dark sections on the landing page, and tops the main summary card on Cash & Credit. Use it **sparingly**, only where it marks something important.

### 1.4 Design principles

1. **Answer first.** Lead each screen with the answer in plain words, then the detail.
2. **Plain language.** No jargon on screen. Explain a number next to the number.
3. **One clear action.** Every screen makes the next step obvious.
4. **Never rely on colour alone.** Pair colour with text, icons or shape.
5. **Fast feeling.** Show the shape of the page at once (skeletons), and keep movement short and purposeful.
6. **Consistent.** Same spacing, same radius, same states everywhere.

---

## 2. Logo

### 2.1 The mark

A rounded-square badge in **maroon** (`primary-600`, `#6d1f2c`) containing:

- a **brass scalloped awning** across the top (`#c9a24a`),
- a **white arched doorway** outline below it,
- a **white serif "D"** inside the doorway.

It reads as a shop: awning, door, and the initial of the name.

### 2.2 The wordmark

**Dukaan** in Libre Baskerville **Bold** and **Pulse** in Libre Baskerville **Regular**, set as one word.

| Background             | Wordmark colour                                                 |
| ---------------------- | --------------------------------------------------------------- |
| Light                  | Both parts in `primary-600`                                   |
| Dark (maroon or black) | **Dukaan** in white, **Pulse** in brass `#c9a24a` |

### 2.3 Lockups

- **Horizontal** (default): mark on the left, wordmark on the right, a gap of one space-3 (12 px).
- **Mark only**: for the favicon, small spaces and the phone top bar.
- **Splash**: mark first, the wordmark opens out of it, then folds back.

### 2.4 Rules

| Rule              | Value                                                                                                |
| ----------------- | ---------------------------------------------------------------------------------------------------- |
| Minimum mark size | 20 px (favicon is the mark at 16 to 32 px)                                                           |
| Clear space       | At least half the mark's height on all sides                                                         |
| Do not            | Stretch, rotate, recolour, add shadows or outlines, or put the mark on busy images                   |
| The tagline       | "Wholesale ERP" in tracked capitals is used **only** in the splash. It is not part of the logo |

### 2.5 The mark as code

Used in `components/Logo.jsx`, `Splash.jsx` and `public/favicon.svg` (viewBox `0 0 64 64`):

```svg
<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <rect width="64" height="64" rx="12" fill="#6d1f2c"/>
  <path d="M13 10H51V16A6.33 6.33 0 0 1 38.33 16A6.33 6.33 0 0 1 25.67 16A6.33 6.33 0 0 1 13 16Z" fill="#c9a24a"/>
  <path d="M20 55V38A12 12 0 0 1 44 38V55" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>
  <path fill="#fff" fill-rule="evenodd" d="M24.5 36H31.5C37.3 36 40 39.3 40 43C40 46.7 37.3 50 31.5 50H24.5V48.9L26.2 48.5V37.5L24.5 37.1ZM29 37.8H31.4C34.2 37.8 35.4 40 35.4 43C35.4 46 34.2 48.2 31.4 48.2H29Z"/>
</svg>
```

The "D" is a drawn shape (not a font), so it looks the same everywhere.

---

## 3. Colour system

Colours work like a **paint-shop shade card**: one family with steps from **50 (lightest) to 900 (darkest)**. Each step has a job.

### 3.1 Primary: logo maroon

The brand colour for actions. **Step 600 is exactly the logo colour.**

| Step          | 50          | 100         | 200         | 300         | 400         | 500         | 600         | 700         | 800         | 900         |
| ------------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- |
| **Hex** | `#f9f0f2` | `#f4e1e4` | `#eac8ce` | `#db9ea8` | `#c65366` | `#7e2634` | `#6d1f2c` | `#501620` | `#3b1218` | `#260d11` |

| Step          | Job                                    |
| ------------- | -------------------------------------- |
| **500** | Buttons, links, selected state         |
| **600** | Button hover. The exact logo colour    |
| **700** | Button pressed                         |
| **100** | Tinted backgrounds, selected table row |
| **50**  | Row hover, very light wash             |
| **900** | Sidebar and dark sections              |
| **800** | Raised surfaces on dark (menus)        |

### 3.2 Neutral: warm grey

For text, lines and backgrounds. A faint red-brown tint keeps it friendly next to maroon.

| Step          | 50          | 100         | 200         | 300         | 400         | 500         | 600         | 700         | 800         | 900         |
| ------------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- |
| **Hex** | `#f9f8f8` | `#f3f2f1` | `#e5e2e1` | `#cfcac9` | `#ada6a4` | `#867c79` | `#675e5b` | `#4f4745` | `#342f2d` | `#1f1b19` |

| Step          | Job                                     |
| ------------- | --------------------------------------- |
| **900** | Main text                               |
| **600** | Muted text (6:1 contrast on white)      |
| **500** | Input borders (4:1 on white)            |
| **300** | Stronger lines, secondary button border |
| **200** | Borders and dividers                    |
| **100** | Page background                         |
| **50**  | Table headers, sunken panels            |

### 3.3 Status colours

**Success (green)**

| Step          | 50          | 100         | 200         | 300         | 400         | 500         | 600         | 700         | 800         | 900         |
| ------------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- |
| **Hex** | `#effbf5` | `#d7f4e6` | `#b3e6ce` | `#7fd2ab` | `#36ba7c` | `#189158` | `#137c4b` | `#0e673e` | `#0a5230` | `#063720` |

**Warning (yellow)**

| Step          | 50          | 100         | 200         | 300         | 400         | 500         | 600         | 700         | 800         | 900         |
| ------------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- |
| **Hex** | `#fff9e5` | `#fff2c7` | `#fee490` | `#fcd555` | `#f8c725` | `#e7b308` | `#ba8208` | `#915d08` | `#693d07` | `#472606` |

**Error (red)**

| Step          | 50          | 100         | 200         | 300         | 400         | 500         | 600         | 700         | 800         | 900         |
| ------------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- | ----------- |
| **Hex** | `#fef2f0` | `#fde1de` | `#f9c4be` | `#f39b91` | `#e86354` | `#ca3221` | `#ad291a` | `#902014` | `#6a1910` | `#45120c` |

| Use                                 | Success             | Warning             | Error               |
| ----------------------------------- | ------------------- | ------------------- | ------------------- |
| Solid mark, left bar, chart         | **500**       | **500**       | **500**       |
| Soft background                     | **50 or 100** | **50 or 100** | **50 or 100** |
| Border on a soft background         | **200**       | **200**       | **200**       |
| Text and icons on a soft background | **700**       | **700**       | **700**       |

> **Warning 500 is a bright yellow and fails contrast with white text.** On a warning button or chip, use **dark text** (neutral 900). Use warning **700** for any warning text or icon.
> **Error red is deliberately more orange than the maroon primary**, so a delete or error is never confused with a normal action. **Primary is never used for destructive actions.**

### 3.4 Accent

**Brass** `#c9a24a` (token `--brass`). The awning colour. Used for: the logo awning, the active-link bar in the sidebar, the avatar, "Pulse" on dark backgrounds, and the overdue bar on the Cash & Credit summary. **Never used as a status colour.**

### 3.5 Role tokens (use these in CSS)

| Token                | Points to   | Use                         |
| -------------------- | ----------- | --------------------------- |
| `--action`         | primary-500 | Buttons, links              |
| `--action-hover`   | primary-600 | Hover                       |
| `--action-pressed` | primary-700 | Pressed                     |
| `--action-soft`    | primary-100 | Tinted background           |
| `--action-faint`   | primary-50  | Row hover                   |
| `--page`           | neutral-100 | Page background             |
| `--surface`        | `#ffffff` | Cards, tables, inputs       |
| `--surface-sunken` | neutral-50  | Table header, detail panels |
| `--line`           | neutral-200 | Borders                     |
| `--line-strong`    | neutral-300 | Stronger borders            |
| `--input-line`     | neutral-500 | Input borders               |
| `--text`           | neutral-900 | Text                        |
| `--text-muted`     | neutral-600 | Secondary text              |
| `--nav`            | primary-900 | Sidebar and dark bands      |
| `--nav-text`       | neutral-300 | Text on dark                |

### 3.6 Colour rules

1. Text must meet **4.5:1** contrast, large text and icons **3:1**.
2. **Maroon primary on a maroon background is invisible.** On dark sections use the **brass** button (brass fill, `primary-900` text) and the **outline** button (white outline).
3. Status is always shown with **words or an icon as well as colour**.
4. Shadows use a warm black (`rgba(31, 27, 25, …)`), never pure black.

---

## 4. Typography

### 4.1 Fonts

| Role                                | Font                        | Weights                       |
| ----------------------------------- | --------------------------- | ----------------------------- |
| **Titles** (page and section) | **Libre Baskerville** | 700 (and 400 in the wordmark) |
| **Everything else**           | **IBM Plex Sans**     | 400, 500, 600                 |

Fallbacks: Georgia for the serif; Segoe UI, Roboto, Arial for the sans. Fonts load from Google Fonts. If a font is slow, the page uses the fallback and nothing breaks.

**Why two fonts:** the serif links the screens to the logo and gives a trustworthy feel; the sans keeps small numbers and tables easy to read. **Never set tables, forms or money in the serif.**

### 4.2 Scale

| Level         | Font              | Size / line height | Weight | Used for                         |
| ------------- | ----------------- | ------------------ | ------ | -------------------------------- |
| Page title    | Libre Baskerville | 26 / 32            | 700    | One per screen                   |
| Section title | Libre Baskerville | 20 / 28            | 700    | Modal titles, login title        |
| Panel title   | IBM Plex Sans     | 16 / 24            | 600    | Card and panel headings          |
| Body          | IBM Plex Sans     | 14 / 22            | 400    | Normal text, table cells         |
| Button        | IBM Plex Sans     | 14                 | 500    | Buttons                          |
| Label         | IBM Plex Sans     | 13 / 20            | 500    | Form labels, table headers (600) |
| Caption       | IBM Plex Sans     | 12 / 16            | 400    | Helper text, small notes         |
| Big number    | IBM Plex Sans     | 28 / 34            | 600    | Stat values                      |
| Landing hero  | Libre Baskerville | 34 to 58 (fluid)   | 700    | Landing headline only            |

Tokens: `--text-xs/sm/base/md/lg/xl/stat` with matching `--leading-*`.

### 4.3 Rules

- **Sentence case** everywhere ("Who needs attention", not "WHO NEEDS ATTENTION"). The only tracked capitals are the splash tagline.
- Money and numbers use **tabular figures** (`font-variant-numeric: tabular-nums`) so digits line up.
- Indian number grouping: **₹12,48,500**.
- Line length for reading text: about 60 to 75 characters.
- One page title per screen.

---

## 5. Spacing, shape, elevation, motion

### 5.1 Spacing (steps of 4)

| Token          | Value |
| -------------- | ----- |
| `--space-1`  | 4 px  |
| `--space-2`  | 8 px  |
| `--space-3`  | 12 px |
| `--space-4`  | 16 px |
| `--space-5`  | 20 px |
| `--space-6`  | 24 px |
| `--space-8`  | 32 px |
| `--space-10` | 40 px |
| `--space-12` | 48 px |
| `--space-16` | 64 px |

No in-between values (no 10, 14 or 18).

### 5.2 Radius

| Token             | Value  | Used for                        |
| ----------------- | ------ | ------------------------------- |
| `--radius-sm`   | 6 px   | Chips, small marks              |
| `--radius`      | 8 px   | Buttons, inputs, menu items     |
| `--radius-lg`   | 12 px  | Cards, tables, panels           |
| `--radius-xl`   | 16 px  | Modals, login card, hero card   |
| `--radius-full` | 999 px | Status pills, avatars, switches |

### 5.3 Elevation: only three levels

| Level             | Token                | Used for                      |
| ----------------- | -------------------- | ----------------------------- |
| **Flat**    | none (border only)   | Cards, tables, panels         |
| **Raised**  | `--shadow-raised`  | Toasts, menus, hover on cards |
| **Overlay** | `--shadow-overlay` | Modals, login card            |

### 5.4 Control sizes

| Token              | Value | Used for                            |
| ------------------ | ----- | ----------------------------------- |
| `--control-h`    | 40 px | Buttons, inputs, selects, nav links |
| `--control-h-sm` | 32 px | Buttons inside tables               |
| `--row-h`        | 44 px | Table rows                          |

### 5.5 Motion

| Token          | Value                              |
| -------------- | ---------------------------------- |
| `--ease-out` | `cubic-bezier(0.22, 1, 0.36, 1)` |
| `--dur-fast` | 120 ms (colour changes)            |
| `--dur`      | 200 ms (hover, small moves)        |
| `--dur-slow` | 350 ms (entrances)                 |

Animate **only `opacity` and `transform`**, except the short colour and shadow changes above. Everything stops for people who prefer reduced motion.

---

## 6. Layout

### 6.1 App shell

- **Desktop:** two columns, a **240 px fixed sidebar** and the page area. Page padding 32 px top, 40 px sides, 64 px bottom.
- **Under 900 px:** one column. A **56 px top bar** (menu button and logo) sits on top, the sidebar becomes a slide-in drawer of 280 px (max 85% of the screen width), page padding becomes 20 / 16 / 48.
- Page header: serif title on the left, optional one-line description below, actions on the right. It wraps on small screens.

### 6.2 Breakpoints

| Width      | What changes                                                   |
| ---------- | -------------------------------------------------------------- |
| ≤ 1100 px | Five-week cash cards go from 5 to 3 per row                    |
| ≤ 1000 px | Three-column grids become two                                  |
| ≤ 900 px  | Sidebar becomes a drawer; hero and two-column sections stack   |
| ≤ 640 px  | One-column grids; dialogs become bottom sheets; toolbars stack |
| ≤ 480 px  | Toasts span the width; the logo name hides in the landing nav  |

### 6.3 Sidebar

- Dark (`primary-900`), logo at the top, grouped menu (Sell, Buy, Stock, Insights, Admin; group labels are 12 px, sentence case, `neutral-400`).
- Link: 40 px tall, 8 px radius, icon 16 px. **Hover:** faint white wash and the icon moves 2 px. **Active:** stronger wash, white bold text and a **3 px brass bar** that grows in on the left edge.
- Only the menu scrolls if it is long; the logo and account menu stay fixed.
- **Account menu** at the bottom: one 48 px line (32 px brass avatar with the first letter, name, role, chevron). It opens a menu **upward** with name and business, a workspace list (if more than one, tick on the current), Change password and Logout.

---

## 7. Components

### 7.1 Buttons

| Variant                                    | Look                             | Used for                               |
| ------------------------------------------ | -------------------------------- | -------------------------------------- |
| **Primary**                          | primary-500 fill, white text     | The main action of a screen or dialog  |
| **Secondary**                        | White, neutral-300 border        | Other actions                          |
| **Ghost**                            | No border, muted text            | Small or tertiary actions              |
| **Danger**                           | error-500 fill, white text       | Delete or cancel that cannot be undone |
| **Brass** (dark backgrounds)         | Brass fill, `primary-900` text | Main action on dark sections           |
| **Outline light** (dark backgrounds) | White outline and text           | Second action on dark sections         |

States: **hover** (primary and danger lift 1 px and gain a soft shadow; secondary border turns maroon), **pressed** (scale to 97%, primary-700), **focus** (visible ring), **disabled** (50% opacity, no pointer), **loading** (text changes to "Saving…" and the button is disabled). One primary button per screen area.

### 7.2 Form controls

- Inputs, selects: **40 px** tall, 8 px radius, `neutral-500` border, white fill.
- **Focus:** maroon border plus a soft 3 px maroon ring that fades in.
- Labels sit above the field: 13 px, weight 500, muted colour. Helper text below is 12 px.
- Required or invalid fields explain the problem in a sentence under the field or in the form banner.
- **Switch** (for example "Be cautious"): 40 × 24 pill, thumb slides, maroon when on, and a visible focus ring. It is a real checkbox with `role="switch"`.
- **Filter chips**: 36 px pills with a count, filled maroon when active, with `aria-pressed`.
- Money fields accept numbers only and show ₹ in the label or placeholder.

### 7.3 Badges (status pills)

Pill, 12 px text, weight 500, soft background with 700 text.

| Meaning                   | Colour      | Examples                             |
| ------------------------- | ----------- | ------------------------------------ |
| Good or done              | Green       | Paid, Delivered, Received, Reliable  |
| Waiting or partial        | Yellow      | Partially paid, Pending, Keep an eye |
| Problem                   | Red         | Unpaid, Overdue, Failed, High risk   |
| Neutral or ended          | Grey        | Cancelled, Inactive, Too new to rate |
| Selected or informational | Maroon tint | Confirmed                            |

Rating badges also carry a small icon (shield, question mark, warning triangle, info) so colour is never the only signal.

### 7.4 Cards and panels

- **Panel:** white, 1 px `line` border, 12 px radius, 20 × 24 padding. Title (panel title style) and an optional one-line plain-language description under it.
- **Stat card:** small muted label, big number (28 px, tabular). On hover it lifts 2 px with a faint maroon border. Numbers **count up** the first time they appear.
- Cards are **flat** (no shadow) until hovered.

### 7.5 Tables

- White, 1 px border, 12 px radius, horizontal scroll inside the card on small screens.
- Header: 40 px, `neutral-50` background, 13 px weight 600 muted text, stronger bottom border.
- Rows: **44 px**, 14 px text, 1 px divider, hover `primary-50`. Money columns are right-aligned with tabular figures.
- Buttons inside a table row are the small 32 px size.
- Expandable detail rows sit directly under their row on a sunken background.
- Always include a visually hidden caption and a hidden label for icon-only columns.

### 7.6 Dialogs, menus, toasts

- **Modal:** centred, 640 px max, 16 px radius, overlay shadow, dim maroon backdrop. It **pops in** (fade, rise 8 px, scale 97% to 100%). On phones it becomes a **bottom sheet** that slides up. Escape and a Close button always work; focus is trapped inside.
- **Menu (popover):** `primary-800` surface, 12 px radius, 40 px items, arrow keys move focus, Escape closes and returns focus.
- **Toast:** bottom right, slides in from the right, 4 px coloured left edge (green, red, yellow, maroon), icon, short message, dismiss button.
- **Form banner:** soft red background, red left edge, error icon, one sentence. It is announced to screen readers.

### 7.7 Loading, empty, error

- **Skeletons** replace spinners: grey blocks with a slow shimmer, in the shape of the real page (table, dashboard cards, page header). Full-page skeletons for first loads; a table-shaped skeleton while a list loads under an existing header.
- **Empty state:** a centred sentence in muted text, with a next step if one exists.
- **Error panel:** short sentence, and a Try again button.

---

## 8. Screens

### 8.1 Logo intro (splash)

Full screen `primary-900`. **4.4 seconds**, once per browser-tab session.

| Time         | What happens                                                                                      |
| ------------ | ------------------------------------------------------------------------------------------------- |
| 0 to 1.1 s   | The mark builds: badge pops in, the brass awning drops, the arch line draws, the D rises          |
| 1.1 to 2.0 s | The name **opens out** of the mark in brass serif, with the tagline "Wholesale ERP" beneath |
| 2.0 to 2.8 s | Holds                                                                                             |
| 2.8 to 3.7 s | The name **folds back** into the mark                                                       |
| 3.8 to 4.4 s | Screen fades away                                                                                 |

A **Skip** button appears after 1 s. The page underneath is already loading, and the landing page's entrance animations wait until the intro ends.

### 8.2 Landing page

Dark hero, light content, dark Cash & Credit band, dark closing band.

| Section                   | Content and treatment                                                                                                                                                                                                                                                            |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Nav**             | Fixed, transparent over the hero, turns solid maroon with a blur after scrolling. Logo, links, **Login** (outline) and **Get started** (brass)                                                                                                                       |
| **Hero**            | `primary-900`, serif headline "Run your wholesale business from **one place.**" ("one place" in brass), Hinglish line "Dukaan ka poora hisaab, ek jagah.", two buttons, and a sample dashboard window with bars that grow and two floating cards. Labelled "Sample data" |
| **Problems**        | Three cards: credit scattered, stock mismatch, no idea who will pay                                                                                                                                                                                                              |
| **How it works**    | Four steps with icons joined by a line that draws in: Buy, Stock, Sell, Collect                                                                                                                                                                                                  |
| **Features**        | Six cards in a grid; icon tile turns maroon on hover                                                                                                                                                                                                                             |
| **Cash and credit** | Dark band with a checklist and a sample risk table and 5-week cash chart (risk scores **0 to 100, lower is safer**)                                                                                                                                                        |
| **Security**        | Three cards                                                                                                                                                                                                                                                                      |
| **Closing**         | Brass serif headline, two buttons                                                                                                                                                                                                                                                |
| **Footer**          | Logo, links, copyright                                                                                                                                                                                                                                                           |

A brass **awning edge** hangs below the hero and the Cash and credit band. Content blocks rise in as they scroll into view. No invented testimonials, customer logos or statistics.

### 8.3 Login, signup, verification, reset, invitation

A centred white card (max 420 px, 16 px radius, overlay shadow) on a `primary-900` page, with the logo on top and the serif title. The card pops in. Forms use the standard controls; the main button is full width. Links ("Back to sign in") sit under the form in maroon.

### 8.4 Dashboard

Page title and subtitle, a grid of stat cards (count up, stagger in), the monthly sales and purchases chart (sales in maroon, purchases in grey), then low-stock and payment summary panels. Chart axes use `neutral-600` text and `neutral-200` lines.

### 8.5 List screens (Customers, Orders, Invoices and similar)

Page header with the primary action ("New …"), a toolbar (search, filters), then a table. Row actions are small buttons. Create and edit happen in a modal (bottom sheet on phones).

### 8.6 Invoice detail

Header with number, status badge and actions; items table; payments; deliveries; returns; customer credit balance with **Apply credit**.

### 8.7 Cash & Credit

The most important screen to keep plain. Fixed order:

1. **Summary card** (dark, brass awning on top): "Customers owe you ₹X" (large serif number that counts up), a sentence and thin bar for the overdue share, and two side facts: customers needing attention and what you owe customers.
2. **Who needs attention:** up to five cards with a coloured left edge by risk, a plain sentence, a bold suggested action, the overdue amount and a **See why** button. If nobody needs attention: a green "No one needs chasing right now" note.
3. **How late is the money?** Five bars from "Not due yet" (green) to "More than 90 days late" (red), each with a hint, amount and share.
4. **All customers:** filter chips with counts, sort menu, and a table with Rating, a **risk meter** (0 to 100, lower is safer), Payment habit (Paying faster, Paying slower, About the same), Owes you, Overdue and a **Why?** button. The expanded row shows the four score parts as bars, the customer's numbers and the suggested credit limit.
5. **Will you have enough cash?** One headline sentence, the opening-balance field and the **Be cautious** switch, a chart (money in green, money out red, running total in maroon), then five week cards. A week with a shortage is tinted red and flagged.
6. **How these numbers are worked out:** collapsed; plain bullets first, formulas hidden behind "Technical details".

Copy rules for this screen: say **"risk score 0 to 100, lower is safer"** wherever a score appears. Use the band names Reliable, Keep an eye, High risk, Too new to rate. Always say that suggestions are not automatic.

### 8.8 Users

Table of members with role and status, an Invite button (shows a one-time link), role and status changes, and a password reset for single-business members.

---

## 9. Responsive behaviour

- Design **mobile first**, then widen.
- Tables scroll sideways inside their card instead of squashing.
- Tap targets are at least **40 px**.
- Two-column areas stack in the order: summary first, detail after.
- The phone top bar shows only the logo mark and name, and the menu button.

---

## 10. Accessibility

- **Contrast:** text 4.5:1 (checked for primary-500 on white at 9.5:1, neutral-900 on page at 15:1, muted on white at 6:1).
- **Focus:** every control has a visible focus style (maroon ring, brass on dark backgrounds).
- **Keyboard:** all functions work without a mouse; the account menu supports arrow keys, Home, End and Escape; dialogs trap focus.
- **Names and roles:** icon-only buttons have labels; tables have captions; the loading, error and toast messages use live regions; the charts have text descriptions and the same facts appear in text or cards.
- **Colour:** never the only signal.
- **Motion:** respects the reduced-motion setting, which turns animations and transitions off.
- **Language:** `lang="en"` on the page; plain wording.

---

## 11. Content and voice

- Write for a shop owner, not an engineer. Short sentences. Active voice.
- **Say the thing, then explain it.** "Customers owe you ₹4,12,000. ₹1,60,000 of it is overdue."
- Use these words: *owe*, *overdue*, *pays late*, *credit limit*, *stock*. Avoid: *aging buckets*, *utilisation*, *lateness points*, *cumulative net*.
- Buttons are verbs: Save invoice, Record payment, Get started.
- Errors say what to do: "Payment is more than the unpaid amount. Enter ₹8,400 or less."
- One touch of Hinglish is allowed on brand moments only: "Dukaan ka poora hisaab, ek jagah."
- Currency: ₹ with Indian grouping. Dates: "18 Nov 2026".

| Technical term           | Say this on screen                     |
| ------------------------ | -------------------------------------- |
| Receivables              | Money customers owe you                |
| Aging                    | How late is the money                  |
| Insufficient history     | Too new to rate                        |
| WATCH / RISKY / RELIABLE | Keep an eye / High risk / Reliable     |
| Utilisation              | How much of their credit limit is used |
| Conservative projection  | Be cautious                            |
| Net movement             | Left over / Short by                   |

---

## 12. Assets and files

| Asset                      | File                                                          |
| -------------------------- | ------------------------------------------------------------- |
| All design tokens          | `frontend/src/tokens.css`                                   |
| Global component styles    | `frontend/src/index.css`                                    |
| Landing styles             | `frontend/src/pages/Landing.css`                            |
| Cash & Credit styles       | `frontend/src/pages/CashCredit.css`                         |
| Logo component and favicon | `components/Logo.jsx`, `public/favicon.svg`               |
| Logo intro                 | `components/Splash.jsx`, `Splash.css`, `SplashGate.jsx` |
| Loading skeletons          | `components/Skeleton.jsx`                                   |
| Fonts                      | Google Fonts link in `frontend/index.html`                  |

---

## 13. Design review checklist

- [ ] Every colour, space and radius is a token.
- [ ] Only one serif title per screen, and no serif in tables or forms.
- [ ] The screen leads with its answer in plain words.
- [ ] Status is shown with words or an icon as well as colour.
- [ ] Contrast checked; focus is visible; keyboard works.
- [ ] The loading state is a skeleton, and empty and error states exist.
- [ ] It works at 360 px wide.
- [ ] Animations are short and stop under reduced motion.
- [ ] No invented data on public pages.
