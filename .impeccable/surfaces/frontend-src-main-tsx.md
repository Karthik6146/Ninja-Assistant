---
version: 1
slug: "frontend-src-main-tsx"
primary_target: "frontend/src/main.tsx"
related_targets: ["frontend/src/AssistantConsole.tsx","frontend/src/VoiceControls.tsx"]
---

## Scope

App shell (rail navigation, top bar, drawers) and the Jarvis screen with its voice mode. Mode: Operate. Studio, YouTube, Activity and Settings pages keep their internals and inherit the shell and tokens.

## Direction contract

seed: none (direction pinned by the owner: dark, Iron Man arc-reactor cyan, approved layout)

THESIS: Jarvis is a companion first; the app is one calm workshop around him. Refuses the generic chat-app grey with a lavender accent and the stack-of-collapsibles home page.

OWN-WORLD: night-workshop navy grounds (#0a1017, #0d151e rail, #111a24 surfaces), arc-reactor cyan (#3ccff2) only for Jarvis and primary actions, gold (#e5b452) for counts, reminders and verified receipts. Segoe UI Variable with Nirmala UI for Devanagari. One authored 1.75-stroke SVG icon set.

STORY: open the app, Jarvis greets you; type or press the mic; replies stream in; actions collapse into one receipt card; History and Today live in drawers.

FIRST VIEWPORT: 84px labelled icon rail (Jarvis, Studio, YouTube, Activity, Settings, Stop at the foot); top bar with page title and Today / Activity / connection; centred 780px column with greeting, four real-capability suggestions, composer with mic and send.

SIGNATURE: the arc-reactor orb in voice mode, segmented outer ring, inner ring and glowing core driven live by mic or Jarvis audio level; minimises to a floating mini orb.

RISKS: neon-on-dark cliché; glow is confined to the orb and focus rings, everything else stays crisp and flat.

## Unresolved

Studio, YouTube and Settings internals still use the older component layouts; regroup Settings (Voice, Models, Memory, Accounts) in a later pass.
