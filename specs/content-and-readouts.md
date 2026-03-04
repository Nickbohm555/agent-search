# Content and Readouts (Cyberpunk) — Spec

**JTBD:** The frontend presents a cyberpunk aesthetic (neon-noir, retro-tech, hardware-deck vibe) so the app feels like a custom deck rather than generic SaaS.
**Scope (one sentence, no "and"):** Key content (status, answers, progress) is presented in a way that suggests readouts or terminal output where appropriate.
**Status:** Draft

<scope>
## Topic Boundary

This spec covers: how status messages, the final answer, sub-queries, progress steps, and errors are visually presented so they feel like “readouts” or terminal output (e.g. monospace blocks, label-value pairs, or line-by-line progress). It does not cover the global color/typography (visual-theme.md), layout structure (layout-and-chrome.md), or motion (motion-and-feedback.md).
</scope>

<requirements>
## Requirements

### Status and feedback text
- Load and run status (success, error, counts) are presented in a style that fits the readout aesthetic (e.g. labeled lines, monospace values, or compact blocks).
- Error messages remain readable and actionable; styling supports rather than obscures the message.

### Final answer and progress
- The synthesized answer is clearly the primary readout: easy to find and read, with styling (e.g. font, spacing, optional subtle border) that fits the deck/terminal vibe.
- Sub-queries and progress steps (timeline or list) are visually distinct as “system” output (e.g. list with step labels, optional timestamps or icons) so the user can scan progression.

### Consistency
- Readout-style treatment is applied consistently to status, progress, and answer so the whole result area feels like one coherent “output” surface.

### Claude's Discretion
- Whether to use a literal terminal-style block (e.g. black box with green text) or a softer “readout” style (e.g. monospace in themed panel).
- Exact formatting of sub-query list and progress (icons, bullets, indentation).
</requirements>

<acceptance_criteria>
## Acceptance Criteria

- Load and run outcomes (success/error and any counts) are visible and styled in a way that fits the readout/deck aesthetic.
- The final answer is the dominant content in the result area and is readable at a glance.
- Sub-queries and progress steps are presented in an ordered, scannable form (e.g. list or timeline) that fits the theme.
- A user can distinguish “what I asked” from “what the system did” (progress) and “what the system answered” (final answer) from layout and styling alone.
</acceptance_criteria>

<boundaries>
## Out of Scope (Other Specs)

- Global theme (color, typography) → visual-theme.md
- Layout and panel structure → layout-and-chrome.md
- Motion and loading indicators → motion-and-feedback.md
- Accessibility of content (contrast, focus) → accessibility-within-aesthetic.md
</boundaries>

---
*Topic: content-and-readouts*
*Spec created: 2026-03-04*
