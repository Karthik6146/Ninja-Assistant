# Ninja usability and workflow implementation plan

Goal: make importing, opening, editing and publishing media a guided, durable journey while preserving existing data and integrations.

Architecture: retain React, FastAPI, SQLite and the single worker. Extend the existing OAuth vault and upload ledger; add versioned workflow definitions and atomic run claims. Reuse video stages, ClipX and ComfyUI. No additional automation platform or upstream source copied.

## Next extension: channel instructions and reference-guided editing

The [channel instructions, metadata and editing-reference plan](channel-instructions-plan.md) adds channel → workflow → individual-video overrides, validated metadata variables, immutable approval snapshots, editable style briefs, optional evidence-backed research, safe asset/template inspection and one-video tests. These requirements are planned; the completed checklist below describes the earlier usability release.

## Audit findings
- Recordings are imported video projects, not agent sessions. Existing EDL preview/render works through separate review steps; no recording-to-studio handoff exists.
- Navigation nests unrelated tools under Projects; component unmounts discard unsaved forms. Video uploads do not refresh the shared project list and saved workflow selection is lost.
- Finished media cannot enter publishing without a render job. This must become a validated original-file path, not a fake render.
- OAuth is configured but not connected. Current vault and channel checks are single-account; operation credentials must be bound independently of the visible channel.
- Approved local roots are empty. Folder actions must explain authorization and support a deliberate server-folder grant.
- Optional editor/model processes may not survive restarts; preflight must show reachability before work begins.

## Ordered implementation
1. [x] Reproduce browser/API import, existing-project open, save/reload, preview/export; record before screenshots. Add focused regression checks for the broken paths.
2. [x] Extend `youtube_auth.py` with distinct encrypted connections and verified channel records. Preserve legacy tokens. Bind `youtube.py` upload/status/recovery operations to immutable connection/channel pairs; test six independent channels and switching attacks.
3. [x] Add `studio.py`, `studio_routes.py` and `studio_models.py`: saved channel defaults/workflows, drafts, finished-file inspection, queue review, explicit policies, per-channel/workflow hash ledger. No edit/caption/render in finished mode. Atomic schedule claims and stable-file folder observation.
4. [x] Add six primary sections, searchable Recordings, direct handoff, four-action studio wizard, real browser upload progress, draft restoration and guided channel setup. Retain existing editing/publishing tools under clear advanced panels.
5. [x] Wire clipping/editing to existing durable stages. Add idea research/storyboard/assembly through existing safe retrieval, Ollama, ComfyUI and ClipX; preflight missing narration/media, retain citations/provenance, never use paid cloud implicitly.
6. [x] Add template-first automation setup, natural-language structured drafts, manual/daily/folder triggers, dry tests, activate/pause/run/retry and execution history. Persist UTC with explicit IANA timezone and immutable run snapshots.
7. [x] Run backend/frontend checks and real browser journeys, verify local rendered outputs and service failures, capture after screenshots. Public publishing uses mocks until account-dependent authorization. Apply guarded source/build diff with backup; verify originals/config/vault unchanged and refresh Graphify.

## Acceptance boundaries
Every visible action must work or identify the missing dependency and next step. Tests never publish. Channel selection never changes a queued operation. Retries reuse successful stages and reconcile uncertain uploads. Unsaved drafts survive navigation/refresh. Folder monitoring requires the worker, stable size/mtime observations, and approved server paths. Existing source files stay intact.

## Reference decisions
- Open WebUI features: reusable presets, explicit integration setup and durable conversations; existing local UI patterns retained. Open WebUI license includes branding conditions; no code copied. https://docs.openwebui.com/features/ and https://github.com/open-webui/open-webui/blob/main/LICENSE
- Activepieces: guided trigger/action configuration and connection reuse; MIT core with enterprise exceptions. https://github.com/activepieces/activepieces/blob/main/LICENSE
- n8n: separate manual/test and production executions with history/retry; Sustainable Use License with enterprise exclusions. No runtime installed. https://docs.n8n.io/workflows/executions/ and https://github.com/n8n-io/n8n/blob/master/LICENSE.md
- Trigger.dev: stable run keys do not alone deduplicate external side effects; retain the existing resumable upload reconciliation ledger. Apache-2.0. https://trigger.dev/docs/idempotency and https://github.com/triggerdotdev/trigger.dev/blob/main/LICENSE
- OpenChatCut: preserve isolated draft lifecycle and clear fallback export limits; separate AGPL-3.0-or-later service, Remotion license separate. https://github.com/0xsline/OpenChatCut

Skills: installed Ponytail, Caveman, Graphify and standalone Superpowers planning/debugging/verification skills used. Full Superpowers namespace is not installed. Agent-Reach skill is installed; its CLI and gh are unavailable, so official web access is used for this audit. No unrelated platform installed.

Validation details: [usability-validation.md](usability-validation.md). Applied with backup data/backups/usability-20261008; live APIs verified and graph refreshed (659 nodes / 1233 edges).
