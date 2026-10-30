# JARVIS Personal Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Availability:** Those Superpowers execution subskills are not currently installed. Do not claim they were used or install them implicitly. This document is an implementation handoff; the same task boundaries can be followed through the native harness when execution is authorized.

**Goal:** Extend Ninja into a local, conversational Jarvis that remembers useful context, executes supported tasks, accepts mid-task changes and starts with push-to-talk.

**Architecture:** Reuse FastAPI, SQLite, the typed tool registry, durable jobs, current task streams and existing media/account adapters. Add a bounded Qwen tool loop, scoped memory and a separate lightweight worker lane; CPU speech ingress remains available while model/media jobs wait for the shared GPU. Prefer API integrations over browser or desktop automation.

**Tech Stack:** React 19/TypeScript, FastAPI/Pydantic, SQLite FTS5, Ollama qwen3.5:9b, installed FFmpeg/SAPI; optional faster-whisper/Silero, Playwright and pywinauto. Semantic embeddings and wake-word components are separate optional slices.

**Spec:** [../../jarvis-spec.md](../../jarvis-spec.md). Research: [../../jarvis-research.md](../../jarvis-research.md).

## Global Constraints

- Working assistant name: Jarvis. Extend Ninja; preserve its projects, channel identities, publishing policies, caption tool and user configuration.
- The user selected push-to-talk first, wake word later.
- Routine permissions should be saved and reused, rather than repeatedly requested.
- No paid cloud service without explicit opt-in and disclosure of shared data.
- Sensitive confirmations are parameter-bound, expire after 10 minutes, consume once and become invalid after relevant task edits.
- The initial agent budget is 8 model turns, 12 tool calls, 180 seconds of active orchestration and 12,000 characters per tool result.
- Initial memory allowance: approximately 1,500 estimated tokens, not a billing claim.
- Capture only during push-to-talk; cap one utterance at 60 seconds and 20 MiB; delete temporary audio after transcription.
- Use Asia/Kolkata by default, store UTC and display timezone.
- Finished-video workflows remain upload-only.
- The model cannot grant itself capabilities. Unsupported intrusions/credential theft/private surveillance are not integrations.

## Implementation progress — 2026-10-13

Native implementation plus independent runtime and Chromium review was used, as selected by the user. The task checklists below remain the full target; a whole task is not marked complete when only its first slice is implemented.

| Task | Implemented and verified | Still required for the full task |
| --- | --- | --- |
| 1–3 | Server-held scoped grants, durable tool steps, bounded Qwen loop, control worker, prompt/progress/revision UI | Additional supported sensitive tools only when requested |
| 4 | Scoped factual FTS memory, correction/forget/export, isolated local private conversation | Protected sensitive records, semantic recall and broader archive extraction |
| 5 | Public research, exact shared-document reads, copy-only small text edits/undo, existing workflow delegation and draft save/open | Broader application targets and cross-task research caching |
| 6 | Existing ClipX CPU transcription, SAPI replies, intentional push-to-talk, browser lifecycle checks | Real microphone and Hindi/Hinglish calibration; no new model downloaded |
| 7 | Allowlisted Notepad/Calculator/Explorer launch, active/unlocked session checks | Named browser/UI Automation targets and real lock/disconnect calibration |
| 8 | Existing first-open priorities plus durable deduplicated local reminders | Quiet hours and additional proactive event policies |
| 9 | Deferred independent extensions | Wake word, named owned devices, disposable software-analysis sandbox |

The verified foundation is installed at http://127.0.0.1:8000. The guarded rollout preserved existing configuration, account files and project/workflow records; final live browser checks passed. See [user guide](../../jarvis-guide.md) and [validation](../../jarvis-validation.md) for evidence and remaining slices. No new dependency or upstream code was copied.

## Review Focus

1. Paths with spaces, Unicode and Windows junctions must remain inside the granted root (Task 5).
2. A crash after an external side effect but before saving its result must reconcile instead of replaying (Tasks 1-2).
3. Locked/disconnected Windows sessions and user input must pause desktop actions (Task 7).
4. Hindi/Hinglish names, background speech and microphone removal must not cause silent actions (Task 6).
5. Backup copies and private-session data must not reintroduce forgotten memory (Task 4).

## File map and implementation discipline

Existing files to extend: backend/ninja/{db.py,tools.py,adapters.py,worker.py,workspace.py,assistant_desk.py,api.py,usage.py}; frontend/src/{AssistantHome.tsx,ChatWorkspace.tsx,TaskPanel.tsx,Settings.tsx,main.tsx,assistant.css}; scripts/start.ps1 and scripts/narrate.ps1.

New focused files: backend/ninja/{agent_models.py,permissions.py,agent.py,assistant_routes.py,memory.py,voice.py,desktop.py,assistant_events.py}; frontend/src/{AssistantConsole.tsx,MemoryPanel.tsx,VoiceControls.tsx}; tests named per task below. Optional companion/semantic/device modules are created only when their slice is selected.

Before execution, preserve a source/config fingerprint and consistent SQLite backup under data/backups/jarvis-<timestamp>. Use an isolated source snapshot at data/development/jarvis-worktree following the existing development pattern; the live root has no Git repository. Never copy live credentials to fixtures. Initialize/use Git only in that development checkout, review each task diff and commit its explicit files there. Apply validated changes through a backed-up deployment script, preserving user edits.

Each task follows red -> green -> focused review. Commands below run in the isolated checkout with its configured Python/Node environment. Do not claim tests are passing from this planning document.

## Task 1: Persist scoped permissions and step records

**Files:** Create agent_models.py, permissions.py; modify db.py, tools.py; test tests/test_agent_permissions.py.

**Interfaces:** Pydantic models in agent_models.py: Scope(kind: personal|workspace|channel, id: str), ToolContext(task_id: str, scopes: list[Scope], plan_revision: int, idempotency_key: str, approval_id: str|None, private: bool = False), ToolCall(id: str, name: str, arguments: dict), ToolResult(call_id: str, value: dict, verified: bool, reconciliation: Literal['confirmed','not_applied','unknown'], receipt: dict|None). Effect = routine|external|financial|security|privacy|destructive. PolicyDecision = allow|confirm|deny.
permissions.decide(name: str, arguments: dict, context: ToolContext) -> PolicyDecision.
Extend tools.invoke(name, args, granted, *, context: ToolContext|None = None), preserving legacy callers.

- [ ] Write tests: test_routine_scope_reused, test_sensitive_digest_expires_and_consumes_once, test_revision_invalidates_confirmation, test_unknown_tool_denied, test_model_cannot_change_grants, test_forged_scope_id_denied, test_legacy_context_does_not_bypass_restricted_tool and test_channel_target_immutable. Assert confirmation age >600 seconds fails and changed target cannot consume the old approval.
- [ ] Run .venv/Scripts/python.exe -m pytest tests/test_agent_permissions.py -q; expect missing interface failures.
- [ ] Add additive SQLite tables for agent tasks/step records and scoped policies. Store step identity, kind, input digest, state, result, usage, external receipt and revision; unique (task_id, step_id) prevents duplicate claims. No destructive migration of jobs/accounts.
- [ ] Classify existing tools explicitly; apply requested routine defaults only to supported tool scopes. Derive effective scopes from server-held grants and immutable targets; never trust client-supplied scopes. Legacy context=None supports only already-authorized diagnostic callers, and never bypasses new restricted tools. Reject invalid parameters/unknown capabilities before execution. Reuse current exact approval mechanism with expiry and redacted audit; never log secret values.
- [ ] Re-run focused tests and existing tests/test_core.py and tests/test_youtube.py; review callers using rg, then commit this slice.

## Task 2: Qwen tool loop and lightweight worker lane

**Files:** Create agent.py; modify adapters.py, db.py, worker.py, usage.py, scripts/start.ps1; test tests/test_agent.py and tests/test_worker_lanes.py.

**Interfaces:** adapters.agent_turn(messages: list[dict], schemas: list[dict], *, job: str) -> AgentTurn, with AgentTurn(text: str, calls: list[ToolCall], usage: dict) in agent_models.py.
agent.execute(task_id: str, job_id: str) -> dict.
db.claim(lane: Literal['heavy','control'] = 'heavy') -> dict|None; default excludes new control job kinds.
worker.main(lane: str = 'heavy'); agent continuation kind = agent_turn.

- [ ] Write tests: test_valid_tool_then_verified_reply, test_budget_stops_loop, test_external_write_receipt_reconciles, test_crash_after_remote_write_unknown_pauses, test_not_applied_may_retry_once, test_cancel_before_next_tool, test_gpu_busy_is_waiting, test_worker_lanes_do_not_double_claim and test_usage_aggregates_once. Assert 9th model turn/13th tool call never executes; duplicate recovery does not double provider tokens.
- [ ] Run focused files; expect failures before implementation.
- [ ] Implement native Ollama tool calls with strict schemas, actual usage, finite budgets and persisted step results. Unknown/invalid calls return a clear tool error without executing. Persist a pending external write before dispatch. Reconciliation is confirmed with a verified receipt, not_applied with evidence allowing a bounded retry, or unknown which pauses automatic retry. GUI sends without a queryable receipt remain unknown after an interrupted write.
- [ ] Add one control worker using a separate process lock and atomic lane-filtered claims/recovery; existing video/coding/publishing work remains in the heavy lane. Release claims at child-job/approval/model waits; resume through durable continuations instead of occupying a worker in a long wait.
- [ ] Keep GPU ownership under existing model.lock. Validate limits/errors and make model waits cancellable; never launch concurrent Qwen/ComfyUI sessions to force responsiveness. Stop/status endpoints stay outside the queue. Launch both workers hidden; close only their owned processes on shutdown.
- [ ] Register system.monitor plus today's task read/update operations reusing assistant_desk data validation. Run tests and existing chat/worker checks; verify a queued media job cannot block Stop. Review and commit.

## Task 3: One assistant console with editable progress

**Files:** Create assistant_routes.py, AssistantConsole.tsx; modify api.py, AssistantHome.tsx, ChatWorkspace.tsx, TaskPanel.tsx, Settings.tsx, main.tsx and assistant.css; test tests/test_agent_routes.py and frontend/src/AssistantConsole.test.tsx.

**Interfaces:** POST /api/assistant/tasks accepts {conversation, text, scopes, private, request_key}; scopes select among server-held grants, never grant authority. Returns {task, job}; private execution uses volatile task state/redacted job metadata rather than a content-bearing durable payload. GET /api/assistant/tasks/{id} returns state, revision, plan, steps, outputs and missing_input. POST /api/assistant/tasks/{id}/instructions accepts {text, expected_revision, request_key}; cancel uses existing cancellation paths. Reuse /api/tasks/{job}/stream.

- [ ] Test authenticated routes, mutation-token/origin enforcement, duplicate request keys, stale revision rejection, and test_instruction_change_preserves_committed_stage_and_target. Frontend checks: draft survives refresh; progress shows waiting/error; keyboard can stop/edit/retry.
- [ ] Run new backend/frontend tests; confirm missing console/route failures.
- [ ] Implement prompt-first console, compact task preview and a one-question missing-input card. Route existing Home advice to supported execution only when the user requests a task. Assistant identity setting defaults Jarvis in testing without renaming existing records.
- [ ] Persist instruction revisions and preserve committed results; invalidate only changed future steps. Keep advanced logs collapsed and live status readable to assistive technology; respect reduced motion.
- [ ] Run focused tests, npm test and npm run build from frontend; capture desktop/narrow-screen UI evidence. Review and commit.

## Task 4: Scoped factual memory and bounded conversation context

**Files:** Create memory.py, MemoryPanel.tsx; modify db.py, workspace.py, assistant_desk.py, assistant_routes.py, Settings.tsx and agent.py; test tests/test_memory.py and frontend/src/MemoryPanel.test.tsx.

**Interfaces:** In agent_models.py define Memory(id, scope: Scope, text, source_conversation, source_message, quotation, confidence, explicit, created, updated, expires, revision, superseded).
memory.remember(value: Memory) -> Memory; memory.search(query: str, scopes: list[Scope], limit: int = 5) -> list[Memory]; memory.correct(id: str, text: str, expected_revision: int) -> Memory; memory.forget(id: str, *, delete_source: bool = False) -> dict; memory.context(query: str, scopes: list[Scope], budget: int = 1500) -> list[dict].
Routes under /api/assistant/memory provide list/search/add/correct/delete/export.

- [ ] Test cross-day restart recall, pre-ranking scope isolation, correction/supersession/conflict, full derived-index deletion, private-session zero content persistence across job payloads, step results, summaries, audit and speech artifacts after cancel/crash/restart, secret exclusion and token-budget bounds. Assert deleted text is absent from FTS, cached summary and rebuilt indexes. Assert backup restore respects deletion tombstones or explicitly requires reapplying them.
- [ ] Run memory tests and confirm expected failures.
- [ ] Add factual/provenance records plus FTS5 over permitted archive chunks. Keep exact source archive; extraction only follows selected conversations/settings. Scope retrieval before ranking; unresolved conflicts are shown, not confidently selected.
- [ ] Add memory controls and private-session handling before message/audio/model-result persistence. Carry ToolContext.private through every adapter. Private tasks execute in an API-owned bounded transient runner with volatile inputs/results, cancellation and the same GPU lock; only redacted operational IDs/state may persist. They cannot resume after restart. Private voice uses in-memory decode/playback; disable durable automation/publishing and content-bearing child jobs in private mode initially. Clear relevant indexes/summaries when forgetting; document retention of existing backups. Sensitive opted-in records use DPAPI outside plaintext search; explain that ordinary existing chat archives remain plaintext.
- [ ] Replace full-history context with recent turns + bounded summary + retrieved evidence; archive remains accessible. Show estimated retrieval budget separately from provider-reported usage.
- [ ] Run memory and existing workspace/usage tests; review and commit. Optional follow-on: pin qwen3-embedding:0.6b/sqlite-vec after paraphrase-recall benchmarks, with model/version-aware reindexing and identical scope/deletion tests.

## Task 5: Public research and reversible file/workflow actions

**Files:** Modify tools.py, adapters.py, agent.py; reuse config.py approved_path, studio_metadata.py, studio_profiles.py, coding.py and media_library.py; test tests/test_agent_tools.py.

**Interfaces:** Register research.search(query,count<=5), research.fetch(url), memory.search/remember, file.list(root,limit<=200), file.read(path,max_bytes<=1048576), file.write(path,text,expected_hash), app.open(app_id) and workflow.start(workflow_id,inputs,request_key). All consume ToolContext; returned evidence includes URL/source, retrieved UTC, truncation and verification status.

- [ ] Test malicious page instructions, redirects/DNS/private-address SSRF, invalid media links, Unicode/spaced paths, symlink/junction escape, changed-file conflict, undo restoration, unknown application and finished_mode_calls_no_editor. Source data cannot request new tools/grants.
- [ ] Run tests; confirm new registered tools are missing.
- [ ] Use existing extraction/address checks and YouTube evidence cache. Add provider interface only where public search is missing; expose “Search not configured” until a local/public provider is configured. No silent paid fallback, private session/cookie scraping or “viral” certainty.
- [ ] Add bounded folder/text reads, atomic scoped writes with undo copy and explicit verified app IDs. Revalidate path immediately before file operations. Do not offer arbitrary shell commands or index all disks.
- [ ] Delegate workflow execution to current handlers with immutable channel/connection/policy snapshots. Existing auto-publish stays enabled; dry runs remain local. Coding changes use the existing isolated candidate/check flow.
- [ ] Run focused tests plus existing studio/coding/media tests. Demonstrate research -> sourced answer and reversible file -> verified result. Review and commit.

## Task 6: Local push-to-talk and speech response

**Files:** Create voice.py, VoiceControls.tsx; modify assistant_routes.py, AssistantConsole.tsx, Settings.tsx, requirements files; reuse scripts/narrate.ps1 and studio_idea.py voices(); test tests/test_voice.py and frontend/src/VoiceControls.test.tsx.

**Interfaces:** voice.transcribe(path: Path, language: str) -> dict{text, language, segments, uncertainty}; voice.speak(text: str, voice: str, job: str, *, private: bool = False) -> Path|bytes. POST /api/assistant/voice/transcribe accepts bounded audio upload/language; returns transcript only. Starting a task is a distinct explicit user event. normal speech output is a protected local artifact; private speech is volatile audio bytes.

- [ ] Test content/size/duration limits, decode failure, temp cleanup on success/cancel/crash, missing model/voice, microphone removal and English/Hindi/Hinglish transcript correction. Assert nothing executes merely from receiving audio; no cloud call occurs.
- [ ] Run tests before implementation.
- [ ] Pin faster-whisper with multilingual small CPU INT8; calibrate before enabling base fallback. Use Silero CPU VAD if timing tests need it. Check package/model licenses and model download size before setup; missing dependencies get actionable guidance.
- [ ] Reuse existing FFmpeg and SAPI rather than shell-interpolated text. Keep current file-based narration compatible; add in-memory SAPI stream output for private speech without storing plaintext transcript/audio. Run STT in a bounded CPU subprocess/executor outside the GPU/agent waiting loop, allowing only one transcription at once. Temporary audio is removed and abandoned files cleaned on startup. Ordinary voice submission is a deliberate UI event (such as push-to-talk release), not authorization embedded in an uploaded audio file.
- [ ] Add accessible microphone toggle, editable transcript and separate Stop speaking/Cancel task. Release microphone tracks on stop/navigation/lock; do not use browser cloud SpeechRecognition.
- [ ] Run tests/build and actual microphone calibration with consent: ten English and ten Hindi/Hinglish utterances including names/numbers, silence and interrupted speech. Measure CPU use and cold/warm times while a media job runs. Keep uncertain sensitive requests unexecuted. Review and commit.

## Task 7: Scoped browser and native desktop adapters

**Files:** Create desktop.py; modify tools.py, Settings.tsx and assistant_routes.py; test tests/test_desktop.py. Add Playwright/pywinauto only when this slice is selected.

**Interfaces:** desktop.browser(action: dict, context: ToolContext) -> dict and desktop.windows(action: dict, context: ToolContext) -> dict. Actions use typed allowlisted schemas and explicit profile/app/window IDs, never arbitrary executable strings.

- [ ] Test wrong window/account, locked session, user input takeover, expired login, redirect escape, secret-field redaction, cancel, download quarantine and retry-after-uncertain-click. Assert lock/user takeover pauses before another action.
- [ ] Run mock tests before adapters.
- [ ] Use official APIs for supported apps, otherwise dedicated Playwright profile with normal user login. Backend restricts targets/navigation/downloads; Playwright origin settings are not a sandbox.
- [ ] Use pywinauto UIA for a specified ordinary Windows application; require observable postconditions. Desktop actions pause on lock/disconnect/user takeover; no UAC bypass. Screenshots are opt-in per task and bounded.
- [ ] Mock purchases/security changes/public sends. Real demo only opens a chosen app, reads a page or creates an undoable text file. Run tests, verify session behavior on this PC, review and commit.

## Task 8: Event-based daily briefings and reminders

**Files:** Create assistant_events.py; modify assistant_desk.py, db.py, worker.py, AssistantHome.tsx and Settings.tsx; test tests/test_assistant_events.py.

**Interfaces:** assistant_events.tick(now_utc: float) -> list[str] enqueues due events atomically; assistant_events.briefing(event_id: str) -> dict. Event key combines rule/version and scheduled slot; store timezone, quiet hours and delivered status.

- [ ] Test duplicate scheduler ticks/restart, timezone conversion, quiet hours, PC offline, repeated failed-service events and exactly-one daily greeting. No unsolicited outside-app messages or idle model polling.
- [ ] Run tests before implementation.
- [ ] Extend existing priorities/scheduling data for first-open briefing, reminders and relevant failure notifications. Use factual state and retrieval; Qwen summarizes once per requested/due event, with cached output and a next-action question.
- [ ] Display worker/offline dependency and actual upcoming times. Retry only failed stages; no auto-publication beyond existing scoped policy.
- [ ] Run focused scheduler tests and real local due-reminder test; review and commit.

## Task 9: Optional wake word, owned devices and software analysis

These are independent extensions, not prerequisites for the first working assistant. Prepare a separate small implementation plan when selected.

- [ ] Wake word: create backend/ninja/companion.py only after push-to-talk calibration. Use reviewed Windows-compatible model with its own license (openWakeWord code Apache-2.0; stock weights CC BY-NC-SA 4.0). Add local mute, quiet hours, visible listening, session-lock shutdown and interruption tests. No voice-only sensitive approvals.
- [ ] Owned devices: create backend/ninja/device_tools.py for named authorized Home Assistant entities or a supplied router API, using a vault-held connection and exact device allowlist. Test wrong device/credential, privacy-sensitive snapshot request and unavailable connection. No automatic intrusion or unrestricted LAN scans.
- [ ] Software analysis: create backend/ninja/analysis_tools.py only for an explicitly supplied owned/authorized sample in a disposable offline VM. Hash originals; run allowlisted read-only static tools with bounded evidence. Test host-path/network/secret isolation and malicious sample instructions. Do not install/execute the whole reverse-skill bootstrap.
- [ ] Optional improvements after measurements: local semantic recall, licensed neural voices, compression, motion-graphics renderer or mobile access. Each gets dependency/license/telemetry checks and a demonstrated need; no platform bundle installation.

## Task 10: Preserve live data and demonstrate end-to-end behavior

**Files:** Update docs/jarvis-guide.md, docs/integrations.md, docs/workspace-guide.md, THIRD_PARTY_NOTICES.md and .env.example only for implemented features; add tests/test_jarvis_journeys.py and guarded data/development/apply-jarvis.py.

- [ ] Verify one text/voice -> memory -> reversible action -> progress -> changed instruction -> restart journey, and one existing video workflow using mocks for public writes. Validate private mode and sensitive confirmation replay/expiry.
- [ ] Run focused new tests, then existing backend suite once; run frontend tests/build and real-browser narrow-screen/keyboard/microphone/console/network checks. Keep public publishing mocked unless its specific live test is authorized.
- [ ] Record actual recognition/recall/task-success/token/latency/cancel metrics, screenshots and reproducible commands; disclose untested devices/accounts.
- [ ] Apply reviewed source/build with backup and drift checks. Confirm existing .env/vault hashes, account-channel bindings, source files, project rows and scheduled target identities unchanged.
- [ ] Restart only Ninja's owned processes when required, verify health and representative journeys, then refresh Graphify for changed source files. Do not treat graph heuristics as validation.

## Self-review and handoff

Coverage: A -> Tasks 1-3; B -> Task 4; C -> Task 6 then optional 9; D -> Tasks 1/5/7; E -> Task 5 and research inventory; F -> Tasks 2/3/8; G -> Task 1 plus adapter enforcement. Five Review Focus items have explicit tests in their owning tasks. Shared types live in agent_models.py; existing callers remain compatible until migrated.

Recommendation: implement Tasks 1-3 as the first native slice, with an independent review of permission/recovery boundaries before enabling new actions. Then memory and push-to-talk. No runtime feature, installation or live permission was changed while writing this plan.

