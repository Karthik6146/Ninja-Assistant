---
name: Ninja
description: A private, local assistant workshop with Jarvis at its centre.
colors:
  ground: "#0a1017"
  rail: "#0d151e"
  surface: "#111a24"
  surface-raised: "#172230"
  surface-high: "#1e2b3b"
  line: "#213042"
  line-strong: "#2d4157"
  text: "#e4edf5"
  text-soft: "#c9d6e3"
  muted: "#93a3b6"
  faint: "#7a8ba0"
  arc-cyan: "#3ccff2"
  arc-cyan-strong: "#86e6fb"
  arc-cyan-soft: "#3ccff21f"
  arc-cyan-line: "#3ccff259"
  arc-ink: "#03222c"
  receipt-gold: "#e5b452"
  receipt-gold-soft: "#e5b4521f"
  gold-ink: "#241a05"
  ok: "#5ed39b"
  danger: "#ff8a8a"
  danger-soft: "#ff8a8a1c"
typography:
  display:
    fontFamily: "Segoe UI Variable Display, Segoe UI, Nirmala UI, system-ui, sans-serif"
    fontSize: "30px"
    fontWeight: 650
    letterSpacing: "-0.6px"
  headline:
    fontFamily: "Segoe UI Variable Display, Segoe UI, Nirmala UI, system-ui, sans-serif"
    fontSize: "22px"
    fontWeight: 650
    letterSpacing: "-0.4px"
  title:
    fontFamily: "Segoe UI Variable Display, Segoe UI, Nirmala UI, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 600
  body-conversation:
    fontFamily: "Segoe UI Variable Text, Segoe UI, Nirmala UI, system-ui, sans-serif"
    fontSize: "15px"
    lineHeight: 1.65
  body:
    fontFamily: "Segoe UI Variable Text, Segoe UI, Nirmala UI, system-ui, sans-serif"
    fontSize: "13px"
    lineHeight: 1.75
  label:
    fontFamily: "Segoe UI Variable Text, Segoe UI, Nirmala UI, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 500
rounded:
  sm: "8px"
  md: "10px"
  lg: "12px"
  xl: "14px"
  bubble: "18px"
  composer: "24px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "14px"
  lg: "22px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.arc-cyan}"
    textColor: "{colors.arc-ink}"
    rounded: "{rounded.md}"
    padding: "10px 14px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.arc-cyan-strong}"
  button-default:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    padding: "10px 14px"
    height: "40px"
  button-default-hover:
    backgroundColor: "{colors.surface-high}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.md}"
  button-danger:
    backgroundColor: "{colors.danger-soft}"
    textColor: "{colors.danger}"
    rounded: "{rounded.md}"
  input:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "10px 12px"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.xl}"
    padding: "24px"
  rail-item:
    backgroundColor: "transparent"
    textColor: "{colors.faint}"
    typography: "{typography.label}"
    rounded: "{rounded.lg}"
    height: "58px"
  rail-item-current:
    backgroundColor: "{colors.arc-cyan-soft}"
    textColor: "{colors.arc-cyan-strong}"
  suggestion-chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-soft}"
    rounded: "{rounded.pill}"
    padding: "8px 14px"
    height: "36px"
  count-badge:
    backgroundColor: "{colors.receipt-gold}"
    textColor: "{colors.gold-ink}"
    rounded: "{rounded.sm}"
    height: "16px"
  composer:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.composer}"
    padding: "6px 6px 6px 16px"
---

# Design System: Ninja

## Overview

**Creative North Star: "The Night Workshop"**

Ninja is one calm, dark workshop built around a single companion. The rooms are navy, not grey: five stepped tones from ground to raised surface carry all structure, separated by thin cool lines. Light in the room comes from one source, the arc-reactor cyan that marks Jarvis and the next obvious action, and from one secondary lamp, a warm gold that only ever counts things or proves that something happened.

Density is Operate-mode: a fixed labelled rail, a slim top bar, and a centred conversation column with nothing competing for the eye. Surfaces are flat and crisp. Glow is rationed: it lives in the voice-mode orb, the Jarvis empty-state mark, focus and active rings, and the connection dot. Everything else is edge, tone and type.

Type is Windows-native Segoe UI Variable with Nirmala UI behind it, so Devanagari and Latin share one line comfortably. Conversation text runs larger and at full contrast than interface text, because reading Jarvis is the main job.

**Key Characteristics:**
- Navy tonal layering, five steps, no grey.
- One accent (arc cyan) for Jarvis and primary actions only; gold for counts, reminders and receipts only.
- Labelled icon rail that becomes a bottom tab bar on phones.
- One authored line-icon set, 1.75 stroke, recoloured by state.
- Native `<dialog>` drawers for secondary places (History, Today).
- The arc-reactor orb is the single signature element.

## Colors

A night-navy room lit by one cyan source and one warm gold lamp.

### Primary
- **Arc-Reactor Cyan** (arc-cyan): Jarvis identity (rail mark, empty-state mark, avatar ring, typing dots, caret, mic icon), primary buttons, focus outlines, selection, checkbox and range accents, the orb. Text on it uses **Arc Ink**.
- **Arc Glow** (arc-cyan-strong): primary hover, current rail item text, links, inline code, voice-state line.
- **Arc Haze** (arc-cyan-soft) and **Arc Edge** (arc-cyan-line): selected and current fills, mic-on ring, composer focus ring and border, running state chip.

### Secondary
- **Receipt Gold** (receipt-gold): count badges on the rail and top bar, the tool-receipt icon, the waiting-for-approval state, and due reminders (on **Gold Haze** with warm text `#f3d79a`). Text on solid gold uses **Gold Ink**.

### Tertiary
- **Verified Green** (ok): completed state, connected dot.
- **Alarm Rose** (danger, on danger-soft): failed state, errors, the Stop control when engaged, destructive buttons. The idle Stop label is a dimmed rose (`#c98a8a`).

### Neutral
- **Night Ground** (ground): page background and input fields.
- **Rail Navy** (rail): rail, drawers, task panel, floating voice settings, mini orb.
- **Workshop Surface** (surface): cards, assistant bubbles, composer, tool cards, tab track, suggestion chips.
- **Raised Navy** (surface-raised): default buttons, mic button, hovered chips.
- **High Navy** (surface-high): button hover, selected tab, neutral badges and state chips.
- **Cool Line** (line) and **Strong Line** (line-strong): dividers and card edges; button and input borders.
- **Moonlight** (text), **Mist** (text-soft), **Slate** (muted), **Dusk** (faint): primary text, secondary labels and chip text, paragraph and ghost text, idle rail labels and timings.

### Named Rules
**The One Light Source Rule.** Cyan appears only on Jarvis and on the one primary action of a view. A second cyan button on a screen means one of them is wrong.

**The Gold Means Proof Rule.** Gold marks a number, a due reminder or a verified receipt. It is never decoration and never a second accent.

## Typography

**Display Font:** Segoe UI Variable Display (with Segoe UI, Nirmala UI, system-ui)
**Body Font:** Segoe UI Variable Text (with Segoe UI, Nirmala UI, system-ui)

**Character:** The operating system's own voice, tuned with optical sizes; Nirmala UI keeps Hindi in Devanagari at the same weight and rhythm as English.

### Hierarchy
- **Display** (650, 30px, -0.6px): the Jarvis greeting in the empty conversation. Login heading uses 26px.
- **Headline** (650, 22px, -0.4px): page title in the top bar.
- **Title** (600, 17px): drawer headings; card headings inherit the older 21px / 16px h2-h3 sizes.
- **Body, conversation** (15px, 1.65, full-contrast text): chat bubbles. Voice-mode captions use 21px / 1.45 (18px on phones).
- **Body** (13px, 1.75, muted): interface paragraphs, buttons, chips, tool-card summaries.
- **Label** (500, 11px): rail labels, small print, hints.

### Named Rules
**The Read-Jarvis-First Rule.** Conversation text is always larger (15px) and brighter than interface text (13px muted). Never shrink a reply to fit chrome.

## Layout

A fixed 84px rail on the left, main content beside it with 18px / 32px / 40px padding, and an optional 360px task panel on the right that pushes main inward with a 0.25s ease. The top bar holds the page title, Studio tabs when relevant, and right-aligned ghost actions plus the connection status, divided from content by a single line.

The Jarvis screen is one centred 780px column: title bar (History, conversation title, New), due reminders, transcript, receipt card, composer, hint line. The empty state centres a greeting and up to four wrap-centred suggestion chips (max 640px).

At 760px and below the rail becomes a 64px bottom tab bar (rail mark hidden, Stop pinned at the end), main padding drops to 14px / 16px with 84px bottom clearance, the task panel goes full width above the tab bar, and Studio tabs scroll horizontally on their own row. Spacing steps observed: 4, 8, 14, 22, 32px.

## Elevation & Depth

Depth is tonal first: ground, rail, surface, raised, high. Shadows are soft, dark and unlit, used to lift whole planes off the ground rather than to decorate. Light (glow) is a separate vocabulary reserved for Jarvis.

### Shadow Vocabulary
- **Card settle** (`box-shadow: 0 12px 32px -20px #000d`): cards resting on the ground.
- **Tab lift** (`box-shadow: 0 1px 3px #0007`): the selected Studio tab inside its track.
- **Panel edge** (`box-shadow: -24px 0 48px -28px #000`): the docked task panel.
- **Overlay** (`box-shadow: 0 0 60px #000c`, `0 20px 50px #000c`, `0 10px 30px #000a`): drawers, voice settings, mini orb.
- **Focus ring** (`box-shadow: 0 0 0 3px` arc-cyan-soft): composer focus and mic-on.

### Named Rules
**The Rationed Glow Rule.** Glow is allowed on the orb, the empty-state mark, focus and active rings, and the connection dot halo. Cards, buttons, text and borders never glow.

## Shapes

Gently rounded, never sharp and never blobby. Controls use 10px corners, inputs and tab buttons 8px, rail items, tool cards and reminders 12px, cards and floating panels 14px. Conversation uses softer forms: 18px bubbles with a 6px tail corner on the speaker's side, a 24px pill composer, round mic and send controls, and full pills for suggestions and voice actions. Circles belong to Jarvis: the avatar ring, empty-state mark, mic and orb. Borders are 1px cool lines; the provisional (streaming) bubble switches to a dashed edge.

## Components

### Buttons
Quiet and tactile; one press of 1px down on active.
- **Shape:** gently rounded (10px), 40px tall, 10px / 14px padding, icon plus word with an 8px gap.
- **Primary:** arc cyan with arc ink text at weight 600; hover brightens to arc glow.
- **Default:** raised navy with a strong-line border; hover to high navy.
- **Ghost:** transparent, slate text; hover fills raised navy and brightens text. Used for top-bar and title-bar actions.
- **Icon button:** 36px square, transparent, slate icon (drawer close).
- **Danger:** rose haze fill, rose text, rose edge at 25% opacity.
- **Focus:** 2px arc cyan outline, 2px offset, on every interactive element.
- **Transitions:** 0.15s colour changes on `cubic-bezier(.22,1,.36,1)`; removed under reduced motion.

### Chips
- **Suggestion chips:** workshop-surface pill, mist text at 13px, cool-line border; hover raises to raised navy with an arc-edge border.
- **State chips:** 11px on high navy by default; completed green, failed rose, running cyan, waiting-for-approval gold, each on its own 12% tint.
- **Count badge:** solid gold with gold ink, 16px tall, 10-11px numerals.

### Cards / Containers
- **Corner Style:** 14px.
- **Background:** workshop surface on night ground.
- **Shadow Strategy:** card settle (see Elevation).
- **Border:** 1px cool line.
- **Internal Padding:** 24px (18px on phones).
- **Receipt card:** a collapsible 12px-corner card under the transcript. Summary row shows a gold check (or rose alert when failed, auto-opened), the action count, model seconds and a chevron that rotates 90 degrees when open. Running state swaps the icon for a cyan spinner.

### Inputs / Fields
- **Style:** night-ground fill, strong-line border, 8px corners, 10px / 12px padding, cyan caret.
- **Focus:** border shifts to arc edge plus the global cyan outline.
- **Composer:** a 24px pill on workshop surface holding the textarea, a round 40px mic button and a primary send button; focus-within adds a 3px arc-haze ring.

### Navigation
- **Rail:** rail navy, 84px wide, right edge cool line. Each item stacks a 22px icon over an 11px word in a 58px-tall, 12px-corner cell. Idle dusk, hover workshop surface with moonlight text, current item arc haze with arc glow text. Activity carries a gold running count. Stop sits at the foot in dimmed rose and turns full rose on haze when engaged.
- **Mobile:** the same items as a 64px bottom tab bar.
- **Studio tabs:** segmented track on workshop surface (11px corners, 3px padding); selected tab is high navy with tab lift.
- **Drawers:** native modal `<dialog>`, rail navy, up to 420px wide, sliding 28px in from its side over 0.28s with a dark translucent backdrop.

### Arc-Reactor Orb (signature)
The one signature element, used only in voice mode. A full-screen deep-navy radial field holds a 260px orb (52vw on phones): a segmented outer ring of cyan arcs (21 degrees on, 9 off) turning once every 28s, an inner hairline ring, and a glowing white-to-cyan core. A live `--level` (mic or Jarvis audio) scales the core, swells its glow and lifts the inner ring. Thinking speeds the ring to 2.6s and makes the core breathe; standby dims to 50%; muted goes greyscale; idle sits at 70%. Minimised, it becomes a 40px mini orb in a rail-navy pill with an arc-edge border, floating bottom-right. All orb motion stops under reduced motion.

## Do's and Don'ts

### Do:
- **Do** keep every surface on the navy ramp (ground, rail, surface, surface-raised, surface-high) and separate planes with 1px cool lines.
- **Do** reserve arc cyan for Jarvis and the one primary action per view.
- **Do** use receipt gold only for counts, due reminders and verified receipts.
- **Do** draw icons from the single authored set: 24px grid, 1.75 stroke, round caps and joins, `currentColor`.
- **Do** set conversation text at 15px / 1.65 in full-contrast text so mixed Devanagari and English stay legible.
- **Do** give every control the 2px cyan focus outline and honour reduced motion.
- **Do** open secondary places (history, today) in native dialog drawers rather than new pages.

### Don't:
- **Don't** reintroduce the legacy lavender accent (`#d1c6ff` family) or neutral greys on new surfaces.
- **Don't** add glow to cards, buttons, text or borders; glow belongs to the orb, the Jarvis mark, focus and active rings and the status dot.
- **Don't** use gold as decoration or as a second accent.
- **Don't** create a second signature element; the orb is the only one.
- **Don't** use letter glyphs, emoji or text arrows as icons; use the authored SVG set.
