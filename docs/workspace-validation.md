# Workspace validation

Validation date: 2026-10-05. Development and browser testing used the isolated worktree and port 8001 with separate test data. No Google publication, paid provider call or external message was sent.

## Evidence

- Python regression suite covers media validation, approvals, isolated coding, YouTube operation deduplication/recovery, durable chat, consent, streaming reconstruction, cancellation, templates, citation rejection, compatibility exports and migration. Final totals are recorded below.
- Frontend TypeScript/Vite build and Vitest pass. Built assets: approximately 251.73 KB JavaScript / 17.71 KB CSS before compression. No new frontend dependency.
- A deliberate inversion of the cloud-consent condition made its test fail; the original source was restored. This confirms that guard is exercised rather than merely executed.
- Real Chromium: local Ollama response; reload during execution; persisted conversation and search; saved diagnostics template and rerun; report download; caption-tool link; imported video, real preview, exact-revision approval and final rendering; mobile layout without horizontal overflow. No page JavaScript exceptions.
- Failure Chromium run: a real missing Ollama model produced HTTP 404 guidance and Retry safely; cancelling a running chat reached cancelled and survived reload; Files listed original media; Emergency stop remained visible on mobile. No page JavaScript exceptions.
- Real public-source research and YouTube preparation used Python's official JSON documentation and local qwen3.5:9b. Both completed with downloaded Markdown and valid source IDs. Repeated identical submission keys reused the original task. The first YouTube run failed output validation; Ollama's [documented JSON schema format](https://docs.ollama.com/capabilities/structured-outputs) was added and both workflows rerun successfully. Invalid output remains a visible failure rather than an accepted draft.
- Separate-worker smoke: actual FFmpeg source inspection, existing-caption edit, preview, review, final H.264/AAC render and HTTP download; 6-second final, 720×1280, 766,571 downloaded bytes.

## Artifacts

- Before screenshots and navigation audit: `data/development/ui-before/`.
- After screenshots and browser results: `data/development/ui-after/` (including provider-failure, cancelled, mobile-files and workflow-checks).
- Browser runners: `data/development/audit-ui.cjs`, `verify-ui.cjs`, `verify-failures.cjs`; use the existing Playwright installation in the supplied ClipX repository. These are local validation artifacts, not runtime dependencies or portable CI configuration.
- Public-source workflow runner: `data/development/verify-workflows.py`.
- Smoke outputs: `data/development/improvement-worktree/data/smoke-report.json` and its isolated project files.
- Reference snapshots: `data/development/reference-review/`.
- Reviewable source patch and deployment manifest: recorded below at application time.

## Cleanup accounting

Removed only the obsolete generation path, its redundant UI/mutations and the unused generic publication-reservation helper. Retained shared FFmpeg, caption validation/remapping/export and existing publication guards. Dependency analysis found 12 packages exclusively reachable from faster-whisper and no retained installed-package consumers: av, ctranslate2, faster-whisper, flatbuffers, fsspec, hf-xet, huggingface-hub, numpy, onnxruntime, protobuf, tokenizers and tqdm. Manifests retain all other existing pins. Actual before/after installed bytes are recorded below; file-size claims exclude untouched model caches and user media. New requested functionality increases application source size, so this is not presented as a net source-line reduction.

## Limits

ClipX was inspected but is a separate application and was offline during validation; no caption-generation success is claimed for it. The configured integration opens its UI only. Browser/MCP extensions remain Not configured. Cloud inference and live Google OAuth/upload/publishing were not exercised because no account/key was configured; their existing mocked regression coverage is retained. Citation validation checks IDs, not the truth of every sentence. Workflows require supplied public HTTPS HTML/text sources, not automatic search. Templates are manually run, not scheduled recurring jobs.

Conversation search scans stored JSON and returns up to 200 results; this is suitable for personal use, not a large hosted deployment. Current task history lists the existing bounded recent-job window. The dashboard is intended for this localhost computer. Native reviewed coding checks are not an OS sandbox. Existing dependency deprecation warnings remain visible; they did not prevent startup or tests. No coverage threshold was lowered and no test was skipped.

## Applied result

- Applied to the normal project and restarted at http://127.0.0.1:8000. The live worker completed a read-only deployment diagnostics task. Default local model: qwen3.5:9b. ClipX path and http://127.0.0.1:3000 saved; currently offline/not recognized.
- **59 Python tests passed after uninstall**, one frontend test passed, TypeScript/Vite build passed, and `pip check` reported no broken requirements.
- Python environment: **348,237,513 bytes before; 79,713,145 bytes after; 268,524,368 bytes (256.08 MiB) removed**. All 55 retained lockfile pins are unchanged; 12 retired pins removed. No user media/model cache counted or deleted.
- Backup: `data/development/workspace-backup-20261005/`; manifest covers 39 source/build paths. Reviewable patch: `data/development/workspace-update.patch`. Backup includes private configuration and SQLite snapshots; do not publish it.
- Verified exact hashes of `.env` and all five pre-existing project files; the original project JSON is unchanged. The old review state was migrated.

Final live Chromium walkthrough passed all five sections, preserved recording/export controls, Coding/Content/Organization and the YouTube screen with zero page exceptions. Files automatically refreshed when a real diagnostics task completed. The temporary preview was then stopped; normal port 8000 remains running.

Application code footprint (backend, frontend/src and scripts; excluding docs/tests/builds/backups): 177,558 bytes before, 226,281 after. Requested features increase source size; the 256.08 MiB reduction is measured installed dependency removal, not an invented code-reduction claim.
