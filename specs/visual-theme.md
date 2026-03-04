# Visual Theme (Cyberpunk) — Spec

**JTBD:** The frontend presents a cyberpunk aesthetic (neon-noir, retro-tech, hardware-deck vibe) so the app feels like a custom deck rather than generic SaaS.
**Scope (one sentence, no "and"):** The frontend applies a cyberpunk-inspired color palette, typography, and contrast across the UI.
**Status:** Draft

<scope>
## Topic Boundary

This spec covers: global color palette (backgrounds, surfaces, accents), typography (fonts, weights, hierarchy), and contrast levels that together create a neon-noir / retro-tech feel. It does not cover layout structure (layout-and-chrome.md), motion (motion-and-feedback.md), or how specific content blocks are styled as readouts (content-and-readouts.md).
</scope>

<requirements>
## Requirements

### Color palette
- Dark or very dark base (noir) with at least one neon accent (e.g. cyan, magenta, green, or amber) used consistently for focus and highlights.
- Surfaces/panels distinguishable from background (e.g. slightly lighter or bordered) so hierarchy is clear.
- Accent color(s) used for interactive emphasis (focus, hover, active) and key status (success, error, progress) in a way that fits the palette.

### Typography
- Font choice evokes retro-tech or terminal readability (monospace or tech-inspired sans); avoid generic “SaaS” system stacks unless they support the vibe.
- Clear hierarchy (e.g. titles vs body vs readouts) via size and/or weight.
- Sufficient readability on dark backgrounds (see accessibility-within-aesthetic.md).

### Contrast
- Overall contrast supports the “neon in the dark” feel without making body text or UI labels hard to read.
- Decorative elements (borders, glows) may be subtle; interactive and informational text must remain legible.

### Claude's Discretion
- Exact hex values and number of accent colors.
- Whether to support a single theme or a toggle (e.g. high-contrast) in v1.
- Specific font family (e.g. JetBrains Mono, Orbitron, or similar) and fallback stack.
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- On load, the UI consistently uses a dark base with at least one neon accent applied to interactive and status elements.
- Text hierarchy is visible (e.g. headings vs body vs small readouts) and body text is readable on the chosen background.
- Panels/surfaces are visually distinct from the page background (e.g. border or fill difference).
- A reviewer can describe the look as “cyberpunk” or “neon-noir” without contradicting the implemented theme.
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Layout and panel/chrome structure → layout-and-chrome.md
- Motion and micro-interactions → motion-and-feedback.md
- Readout-style content presentation → content-and-readouts.md
- Accessibility constraints (contrast, focus) → accessibility-within-aesthetic.md
</boundaries>

---
*Topic: visual-theme*
*Spec created: 2026-03-04*
