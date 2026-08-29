# Fasthome UX Contract

## Navigation
- Global navigation is stable across authenticated pages.
- Logo always returns to home.
- Account actions stay under the account menu; notifications use the same icon/action everywhere.
- Successful create/edit returns to the owning list while preserving relevant search/filter state.

## States
Every async operation has idle, busy, success and recoverable failure states. Busy controls retain their dimensions and become non-repeatable until completion.

## Search and matching
- Search/matching uses 300ms debounce for remote requests and cancels/ignores stale responses.
- A non-empty search has an explicit clear button.
- Committed search, filters, sort and page are URL-addressable unless a flow is explicitly transient.
- Empty results explain what to change rather than presenting a dead end.

## Forms
- Labels are always associated with controls.
- Validation is owned by the app, preserves entered values, shows inline correction guidance and focuses the first invalid field on submit.
- Selects use the established project primitive where popup geometry matters.
- No duplicate submissions.

## Destructive actions
Destructive, irreversible, privacy-sensitive or permission-changing actions require an accessible app-owned confirmation dialog. The final action uses the actual verb (for example `Supprimer`).

## Feedback
Use one toast/status system with stable placement and accessible live regions. Critical correction guidance remains inline and is never toast-only.

## Housing privacy
Public property cards do not expose exact addresses or rent. Visit workflow keeps requester identity masked from the bailleur until the business process permits disclosure. No payment UI is presented as an online payment flow.

## Responsive
Desktop uses a two-level hierarchy (global navigation + page content). Mobile prioritizes the primary action, keeps touch targets >=44px, and lets long tables scroll horizontally inside their own surface rather than locking the page.

## Accessibility
WCAG 2.2 AA baseline; visible keyboard focus; semantic buttons/links; reduced-motion support; icon-only controls have accessible names; contrast never relies on color alone.
