# Fasthome UI — Design Context

## Product
Fasthome is a trusted housing workflow for RDC: search/matching, verified listings, visits, dossiers, contracts and rent follow-up. The interface must feel more like a professional housing desk than a classifieds marketplace.

## Audience
Locataires, bailleurs and Fasthome agents. The primary job is to reduce uncertainty and make the next action obvious.

## Visual direction
A **quiet institutional premium**: deep blue for trust and structure, warm brass for verified moments and progress, mineral backgrounds, generous whitespace, and strong editorial headings. The signature is a thin brass "house-line" motif used sparingly in headers and key cards.

## Tokens
- `--fh-ink: #10263A` — primary text / navigation
- `--fh-blue: #174C78` — action / interactive brand
- `--fh-brass: #C99A3E` — verification / premium accent
- `--fh-paper: #F5F7F9` — page background
- `--fh-surface: #FFFFFF` — cards and forms
- `--fh-line: #DCE4EB` — borders and dividers
- `--fh-muted: #667789` — secondary text
- `--fh-success: #28724B` — completed states
- `--fh-danger: #B83B43` — destructive/security states

## Typography
Display: Georgia, Times New Roman, serif — restrained, only for page/hero headings.
Body: Inter, ui-sans-serif, system-ui — navigation, forms and operational content.
Data: ui-monospace, SFMono-Regular, Consolas — IDs, reference numbers and audit-like values.

## Layout
Desktop content max-width: 1240px. Mobile gutters: 12–16px. Cards use 16–20px radius; controls use 10–12px. Avoid excessive rounded pills except statuses and compact filters.

## Motion
One calm entrance/reveal language. Hover lift is <=2px. Respect `prefers-reduced-motion`.

## Accessibility
WCAG 2.2 AA baseline. Visible focus, native semantics, keyboard access, text alternatives and no color-only meaning.

## Signature rule
Brass is a signal, not decoration: use it for verification, active progress, or a deliberate divider — never as the default color of every CTA.
