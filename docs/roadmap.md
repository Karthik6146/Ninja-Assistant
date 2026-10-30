> Historical baseline document. For the current workspace behavior, see [workspace guide](workspace-guide.md), migration and validation. Built-in caption generation has been retired.

# Current YouTube update (2026-10-04)

The [YouTube automation guide](youtube-automation.md) supersedes the older YouTube disconnection/milestone notes below. OAuth, reviewed resumable private uploads, approved visibility/scheduling, real analytics and Ollama scene proposals are implemented. Live account verification and the documented parity gaps remain.

# Capability status and remaining stages

The original requirements and extension remain the target. This implementation completes the first video workflow and adds isolated coding and local content preparation. Model providers need configuration; external publication and analytics remain disconnected.

## Working

- Local upload or approved-root import, preserved originals, queued ffprobe inspection.
- Separate single-worker faster-whisper English/Hindi transcription with word timings, original transcript preservation, transcript-only clip suggestions.
- Editable ordered clip list, caption text and timings; saved revisioned EDL, three aspect ratios, crop position, source/music volume, user music upload.
- Caption style controls, optional karaoke highlighting for unchanged timed words; editable JSON/SRT/VTT export.
- Low-resolution preview, review checkpoint and final FFmpeg render with CPU fallback; real progress, errors and cancellation; output viewing/downloading.
- Durable queued/running/waiting-review/completed/failed/cancelled jobs, heartbeats, bounded recovery, emergency stop, audit records.
- Ollama/configurable cloud text chat (disconnected until configured), supplied-URL extraction with source dates/excerpts and Markdown export, CPU/RAM/disk/process inspection.
- All requested navigation screens. Later features explicitly disclose their unavailable state.
- Upstream repository inspection, local coding guidance, foundational approvals and publication reservation tests.
- Named editable caption presets and separate manual Romanized Hinglish variants, preserving segment timestamps and the original transcript.
- Coding repository inspection, user-approved scope, isolated worktrees/branches, selected-source model candidates, read-only explanations, diffs/patch export, approval-bound pytest/Vitest checks and editable reviewed memory. Source changes are restricted to selected small non-sensitive files; the live assistant is excluded.
- Python test-generation baseline with branch coverage/uncovered context, candidate-only test changes, preservation of existing assertions, two candidate check runs, bounded attempts/runtime and numeric coverage deltas. Model adapters are tested with fixtures; real model generation needs a configured provider.
- YouTube/Instagram/Threads local platform drafts, linked recording/captions/final renders, rights and source provenance, per-platform reviews, exportable schedule drafts in Asia/Kolkata and content-package JSON export.
- Persistent editable scene manifests with script/assets/timing/source/rights/provider/task/revisions; changing a scene clears stale narration/timing and invalidates reviews. Scene generation, regeneration and scene assembly are pending.

## Partial / limitations within the video milestone

- Hinglish conversion is manual and separate; automatic model transliteration remains pending. Variant exports preserve segment timestamps but clear obsolete word timings.
- Encoder discovery reports compiled encoders, not guaranteed hardware availability. CPU fallback is tested by the software path; GPU paths need actual hardware validation.
- Native jobs run in cancellable child processes; polling kills process descendants, including Whisper inference and FFmpeg. Native Windows process behavior beyond tested local paths still needs wider validation.
- Named presets are stored locally. Highlighting is karaoke, not a configurable active-word colour editor.
- Uploads stream chunks from FastAPI's spooled UploadFile; global multipart/body ingress limits need further hardening.
- API smoke tests cover real transcription/rendering and output download. Automated browser interaction/accessibility and Hindi speech accuracy need additional verification.

## Later implementation stages

1. Coding Assistant: stronger secret detection, isolated OS execution sandbox, multi-step agent reasoning, atomic multi-file candidate staging, merge/push/install approvals and self-improvement via separately reviewed branches. Current scope is small selected files; no merge/push/install/destructive APIs exist. Tests run trusted repository code natively only after exact approval; worktrees are Git isolation, not an OS sandbox.
2. Test generation: frontend coverage collection and numeric deltas, richer behavioural review and flakiness detection. Python coverage is recorded; two passing runs do not prove non-flakiness. Qodo Cover remains disabled and unintegrated.
3. Research: configurable search provider, multi-source verification/inference report generation and fuller citations. Current output is an excerpt notebook only.
4. YouTube: channel profiles, evidence-based topic plans, narration/visual providers and per-scene rendering/repair; minimum-scope OAuth via OS credential storage, resumable private uploads with persistent session recovery and ambiguous outcome reconciliation; exact channel/media/metadata/privacy/schedule reviews; live quota/restriction diagnostics and official analytics. Current production desk saves drafts and scene outlines for manual handoff.
5. Social Studio: account capability/eligibility/token/app-review diagnostics from current Meta docs, official supported publishing/insights/replies adapters. Reel media is currently prepared in the local editor; Threads copy is manually drafted. No everyday browser reuse, CAPTCHA bypass, engagement farming or unsolicited messaging.
6. Content packages: automated cross-platform clip preparation, visual calendar UI, schedule execution, remote IDs and publication states. Current schedule fields are exportable plans, not executing schedules. One platform's draft edit does not invalidate another's review; source/scene edits invalidate affected reviews.
7. System management: previewable cleanup plans, exact approval-bound recycle-bin deletion/termination/install/configuration actions. Read-only bounded large-file scans and log tails in approved roots are implemented. No unrestricted model shell.

External adapters must be verified against current official platform docs when implemented. No OAuth tokens, accounts, paid generation or publishing are required by local tests. No external actions were performed during verification.
