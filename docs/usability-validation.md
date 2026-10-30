# Usability upgrade validation — 8 October 2026

## Verified

- Backend: 75 tests passed. Frontend: TypeScript/Vite build and 2 tests passed.
- Real Chromium: media import and playable source, saved workflow reload/open, Recordings → Studio handoff, draft retained across Settings navigation, 390px viewport without horizontal overflow, no JavaScript page errors.
- Real local finished-file run: managed original copy, no edit/caption/render invocation. Regression test asserts byte identity and fails if editing is called.
- Real idea run: retrieved public source, Ollama storyboard, Windows narration, supplied footage, ClipX CPU captions, playable preview and final export. Successful stages reused after service failures.
- Real 75-second local footage: two 30–180-second candidates and two captioned previews. Model ranking failed with Ollama HTTP 500; the existing evidence ranking remained visible with a warning.
- Six independent mock Google connections/workflows; switching the ambient account did not change a queued upload's credentials. Unauthorized channel mismatch rejected.
- Test runs created no publishing operations. Production requires exact-revision activation. Unchanged saves retain activation; changed drafts pause it.
- Stable folder observations ignore temporary/changing files; hash ledger skips duplicates; atomic run keys prevent duplicate claims. Repeated manual review returns the same operation.
- Existing YouTube resumable upload, reconciliation, approval and schedule tests remain passing.

## Evidence

Evidence is local, excluded from the repository graph and source snapshot:

- Before: ../data/development/usability-evidence/before-recordings.png and before-studio.png.
- After: ../data/development/usability-evidence/after-recordings.png, after-studio.png and after-mobile.png.
- Machine-readable local journey results: ../data/development/usability-evidence/journeys.json.
- Runnable journeys: data/development/check-usability.cjs, run-usability-journeys.py, resume-usability-journeys.py and check-clips.py.

## Remaining limits

No Google account is connected in the live app; the Desktop client configuration exists. Real account sign-in, uploads, channel identities, quota/private-only restrictions and server-side scheduling remain unverified. No external video was posted.

Ollama currently rejects its linked Qwen manifest as an untrusted mount point. This can block fresh inference and GPU unloading. Automatic approval review rejected replacing that external model-store link without explicit authorization. The link/model files remain unchanged. CPU ClipX worked in the isolated test worker; live configuration was not silently switched.

Idea generation through ComfyUI adapters is wired and preflighted; the complete new idea journey was verified with supplied footage, not newly generated visuals. Existing adapter tests still pass. Windows narration requires desktop speech access.

No unrestricted visual node editor or external automation platform was added. Existing tools and advanced edit JSON remain available. Automatic meme sourcing is not implemented; supplied licensed footage/music and supported effects are preserved. Folder stability relies on size/mtime observations; use temporary-extension then rename for reliable producer handoff.

## References and reuse

Official source/license notes and implementation order are cached in [the plan](usability-plan.md). No upstream platform code was copied. The Ollama chat API documents keep_alive for model retention/unloading: https://docs.ollama.com/api/chat.
