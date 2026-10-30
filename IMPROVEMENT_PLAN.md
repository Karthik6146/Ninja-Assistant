# Ninja Assistant improvement plan

Audit date: 2026-10-05 (Asia/Kolkata). Work happens in an isolated Git worktree; source hashes are checked before application. User configuration, databases, recordings, caption files and render outputs are preserved.

## Architecture observed

React 19 / TypeScript / Vite 6 / Tailwind 4 frontend. FastAPI 0.115.12, Python 3.11, SQLite JSON records and a separate single-process worker with cancellable subprocess jobs. FFmpeg handles media. LangGraph SQLite checkpoints bind media review to revisions. Ollama and an explicitly enabled cloud chat-completions adapter provide text. YouTube uses official OAuth/Data/Analytics APIs and encrypted Windows DPAPI credentials. Startup is PowerShell, served on localhost:8000. There is no frontend-framework migration.

The documented start command was run; it correctly identified the already-running server. Playwright inspected all eleven main screens and saved before screenshots under data/development/ui-before. Source paths and executable flows were traced, including import/render, chat, research, worker recovery, coding approvals and YouTube publishing. Live OAuth/publication is excluded from verification.

## Observed issues and reproduction

| Priority | Reproduction / observed issue | Affected files | Repair |
|---|---|---|---|
| P0 | Chat stores messages only in React state; reload loses the conversation and an in-flight answer | frontend/src/main.tsx, api.py, adapters.py | Durable conversations and queued streaming chat jobs |
| P0 | Source defines chat/research as blocking API calls outside the cancellable job worker | api.py, worker.py | Shared lifecycle and worker execution for interactive flows |
| P1 | Eleven primary tabs separate projects, editor, jobs and approvals; editor first opens without selected project | main.tsx, style.css | Five primary areas; persistent selection and contextual activity |
| P1 | Settings presents raw configuration JSON; Ollama says configured even without a health check | api.py, main.tsx | Provider discovery/health, model selection and setup cards |
| P1 | Jobs show percentages but no elapsed time, current step or durable activity stream | db.py, worker.py, main.tsx | Timestamps, events, resumable SSE snapshots, structured failures |
| P1 | Research has URLs but no question or synthesized cited report; no reusable automation forms | api.py, adapters.py | Source-grounded research and saved workflow templates |
| P1 | Built-in Whisper duplicates the user's separate ClipX generator | media.py, api.py, CaptionExtras.tsx, requirements* | Remove generation; connect to inspected standalone UI |
| P2 | Caption presets and Hinglish conversion duplicate ClipX controls | api.py, CaptionExtras.tsx | Remove UI/routes; preserve saved preferences and outputs |
| P2 | Generic worker recovery can replay steps without classifying side effects | db.py | Allowlisted recovery and explicit safe retry; retain YouTube's own recovery |
| P2 | No Files view for completed artifacts; logs/JSON dominate secondary workflows | frontend | Managed downloads and advanced-only technical details |

Screens inspected: Chat, Projects, Jobs, Video Editor, Research, YouTube, System, Approvals, Coding, Social Studio, Settings, plus mobile layout. No page JavaScript exceptions appeared in the initial screen-navigation audit. Some task behavior findings above come from traced code, not a claim of having executed every provider or destructive action.

## Navigation and journeys

- **Chat:** searchable saved conversations, project grouping, text attachments, model/provider controls, durable streamed answers and contextual tasks.
- **Projects:** recordings and generic workspaces; video trimming/preview/review/render, existing-caption editing/export, isolated coding and content preparation.
- **Automations:** guided Research, YouTube preparation and System diagnostics; editable inputs, saved templates, run history; publishing in a separate explicit-review section.
- **Files:** completed managed videos/reports, preserved captions and originals; no arbitrary host file browser.
- **Settings:** actual provider health, local model selection, ClipX connection, tools/integration capabilities, configuration guidance; audit records only in an advanced disclosure.

Collapsible sidebar, central work area, optional Plan / Activity / Outputs panel. Keyboard-accessible native controls, responsive layouts and visible connection/reconnect states. No private chain-of-thought is shown.

## Phases and acceptance criteria

1. Audit and reference research: capture before UI, source/license mapping, caption dependency inventory and baseline file sizes.
2. Reliability: additive SQLite migration; canonical queued/running/waiting_for_approval/completed/failed/cancelled states; persisted job events, reconnectable SSE, cancellation of child processes, bounded requests, guarded retries and idempotent submissions. No generic paused state.
3. UI: preserve React stack and working media/coding/YouTube modules behind the five-area shell; chat survives reload; missing provider and worker states are actionable.
4. Automations: saved input templates; research requires supplied public HTTPS sources and produces referenced Markdown; YouTube preparation produces drafts only; diagnostics produce findings/proposed fixes without modifying the host. Reruns cannot publish.
5. Caption separation and cleanup: inspect ClipX, remove Ninja's ASR generation and redundant caption helpers/dependencies, retain compatibility utilities used by existing media and packages; measure removed bytes and installed dependency footprint separately from net feature growth.
6. Validate and apply: regression tests, frontend build, real browser before/after, provider failure, streaming reload, cancellation, media preview/download and duplicate submissions. Review patch and verify original hashes; back up modified files/SQLite; announce controlled restart.

## Caption integration decision

User supplied a local ClipX project path. Inspected its project docs, npm workspace manifests, Next.js upload route and session helper. Actual product is ClipX; web dev command uses port 3000. Caption generation is owned there. POST /api/upload creates a project/video/job on every call and uses demo-user auth in current source; there is no safe idempotent cross-app submission contract. Ninja therefore links to its existing browser UI and never silently uploads files or starts that separate app. At audit time port 3000 did not respond. A configurable loopback URL and project path show configured/offline/not-configured accurately. ClipX source, secrets and dependencies are not changed.

Retained: caption schema/validation, source-time remapping, SRT/VTT/JSON export, existing-caption editing and ASS burn support because existing render/package flows use them. Removed: Whisper inference, transcription route/worker dispatch, duplicate Hinglish/preset UI and mutation routes. Legacy transcription jobs become explicit failed or waiting_for_approval records; completed assets are retained.

## Integration and migration policy

Reference frameworks are design inspiration only unless explicitly documented otherwise in docs/improvement-references.md. Keep existing tool registry as the small validated adapter boundary. Optional browser/MCP capabilities are declared unavailable until an actual adapter is configured; no arbitrary shell or model-selected URL execution is added. Explicit cloud consent is required for sending messages/attachments externally. YouTube publication retains its exact-action approval and resumable duplicate guard.

SQLite changes are additive and idempotent; the old waiting-review label is normalized. Existing media checkpoints, preferences, captions and .env remain intact. Historical browser-only chat cannot be recovered because it was never persisted. Safe local tasks may retry; ambiguous external actions use their existing reconciliation workflow. Validation evidence and measured cleanup results will be recorded in docs/workspace-validation.md.

## Completion

All six implementation phases are complete and applied to the normal project. See docs/workspace-validation.md for measured cleanup, test/browser evidence, backup paths and explicit limitations. Optional browser/MCP runtimes and automatic ClipX transfer remain deliberately unconfigured; no upstream framework source was copied.
