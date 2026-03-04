# Layout and Chrome (Cyberpunk) — Spec

**JTBD:** The frontend presents a cyberpunk aesthetic (neon-noir, retro-tech, hardware-deck vibe) so the app feels like a custom deck rather than generic SaaS.
**Scope (one sentence, no "and"):** The frontend layout and UI chrome (panels, borders, frames) evoke a terminal or hardware-deck aesthetic.
**Status:** Draft

<scope>
## Topic Boundary

This spec covers: overall page structure, panel framing, borders, and visual “chrome” (headers, dividers, frames) that suggest a deck or terminal rather than a generic card-based UI. It does not cover color/typography (visual-theme.md), motion (motion-and-feedback.md), or the styling of content as readouts (content-and-readouts.md).
</scope>

<requirements>
## Requirements

### Structure
- Layout clearly separates: control area (e.g. load, query input, run), progress/status area, and result/readout area, with a structure that suggests “instrument panel” or “deck” (e.g. labeled sections, framed blocks).
- Panels or sections have visible boundaries (borders, subtle background difference) so the “deck” feel is recognizable.

### Chrome
- Headers, labels, or section titles are present and styled to fit the aesthetic (e.g. small caps, monospace, or accent underline).
- Dividers or frame lines may use the accent color or a muted variant to reinforce the theme.

### Responsiveness
- Layout remains usable on typical desktop viewports; behavior on small screens is at implementer’s discretion for v1 (e.g. stack sections, preserve hierarchy).

### Claude's Discretion
- Exact grid vs flex layout and breakpoints.
- Whether to use literal “terminal” frame (e.g. window border with title bar) or a more abstract panel style.
- Density (compact vs spacious) of controls and sections.
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- The main areas (controls, progress, result) are visually distinct and framed so the UI reads as a coherent “deck” or panel layout.
- Section boundaries (borders or background) are visible and consistent with the cyberpunk theme.
- A first-time viewer can identify where to act (controls) and where to read (progress, answer) without confusion.
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Color and typography → visual-theme.md
- Motion and feedback → motion-and-feedback.md
- Readout-style content presentation → content-and-readouts.md
- Accessibility of layout (focus order, zoom) → accessibility-within-aesthetic.md
</boundaries>

---
*Topic: layout-and-chrome*
*Spec created: 2026-03-04*
