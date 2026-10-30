# Video Automation Implementation Plan

Goal: extend Ninja with durable URL/custom-footage ingestion, evidence-based highlight proposals, external ClipX captions, editable exports, reviewed YouTube publishing and optional local generation.

Spec: user attachment d882603d-c8f5-4652-9257-a19c56034534 (2026-10-06).
Execution: isolated `data/development/video-worktree`, inline phases, tests before completion. Preserve live data/config; announce application. No cloud generation, login bypass, new ASR or competing full editor. Skills advise; user requirements control execution.

## Observed capabilities and gaps
React/FastAPI/SQLite plus a separate worker; cancellable child processes, exact edit review and preview guards. Existing single-source FFmpeg renderer supports trim/crop/audio/caption burn. Existing YouTube OAuth uses backend credential storage, channel checks, resumable upload/reconciliation and private/future scheduling. Chat usage is reported, but no media job usage ledger, media workflow, source download, multi-source plan, reference analysis, external editor or ComfyUI adapter exists. The existing ClipX installation has an offline Python transcription CLI with word timestamps and cached models; HTTP upload starts an unrelated whole pipeline, so reuse the CLI instead. No caption UI/ASR duplication.

Recheck available hardware and disk space before model downloads.

## Architecture and interfaces
- `video_models.py`: finite validated source/timeline edit-plan schema and preset definitions. Strict supported effect vocabulary, no model shell commands.
- `video_sources.py`: canonical YouTube IDs, yt_dlp.YoutubeDL progress/retries, stable cached downloads, manifests; ClipX adapter validates word timestamps and caches transcripts; FFmpeg scene/audio/frame evidence; bounded candidate summaries for local model ranking.
- `video.py`: SQLite workflow records on existing jobs; stage checkpoints, versioned plans, independent preview/final requests, safe output bundles, multi-asset assembly with captions remapped for speed/trims. Final renders registered into existing project/content publishing pipeline.
- `video_editor.py` and `video_generation.py`: loopback-only OpenChatCut MCP discovery/session calls and separately tested CLI export; ComfyUI HTTP queue, scoped cancellation and output collection. Health distinguishes configured/reachable/tested.
- `video_routes.py`, `VideoStudio.tsx`: YouTube Clips, Custom Edit, Review, Publishing handoff and Integrations. Reuse TaskPanel and existing upload/OAuth review UI.
- `scripts/` setup/start helpers and generation workflows; weights and services remain under ignored data/services or external model directories.

## Phases and acceptance gates
1. [x] Audit schemas, references, skill availability, hardware and caption path. Create this plan before implementation.
2. [x] Ingest one user-provided YouTube URL, or selected local uploaded assets/folder; stable cache IDs, manifest, size/duration/disk limits, progress and cancellation. Tests reject arbitrary URLs, playlists without explicit item selection, traversal and absent rights. Validate provided URL v9QtM6qnG50 without cookies.
3. [x] Reuse ClipX CLI word timestamps; cache by content/config. Extract scene/audio/frame evidence; rank bounded nonoverlapping 30-180s candidates, with explanations and honest confidence. Validate duration and word boundaries; manual trim edits; no viral claims. Speechless footage remains editable without fabricated captions.
4. [x] Validate common multi-track plan; use OpenChatCut isolated draft/review where operational. Export through separately verified `occ render`; keep explicit reduced-fidelity FFmpeg export for the supported subset. Low-res preview before final; write manifest, plans, captions, editable project and verified MP4 into a unique subfolder of selected destination. Test actual samples, speed sync, version changes, restart and failed stage rerun.
5. [x] Reuse OAuth/resumable ledger; create content packages from outputs. Test private upload/schedule/recovery via mocks first. Only ask connection when local export works. Explicit publish policy must bind channel/workflow and metadata; no public test posts. Display IST, persist UTC, reject ambiguous/past time.
6. [x] Optional ComfyUI: separate service and pinned selected Z-Image-Turbo Q4_K_M / Wan2.2 TI2V-5B offload workflows, encoder/VAE dependencies. Sequential GPU jobs coordinated with Ollama. Verify real generation, or record exact missing resources/failure, never mock a generated output as real.
7. [x] Full regression/build/browser verification, documented evidence and limitations, guarded application with backup, graph refresh.

## Editor and export limitations
OpenChatCut 0.2.15 requires Node24. MCP `/api/external-mcp/mcp` supports isolated edit sessions and explicit review; generation/export remain excluded. Its `occ render` uses the supported saved-project rendering layer separately. Offline isolated draft operations were verified without an open browser editor. Validate exact discovered schema and local auth before calls. FFmpeg fallback supports only enumerated trims, crop, speed, titles, gain, fades/zooms and caption burn; do not claim identical WebGL/MG/LUT fidelity. Hypit ideas inform compact reference summaries and reusable plans only; do not embed a second editing engine. Subject-aware tracking depends on editor capabilities; manual normalized crop is always available.

## Inputs and policy
User supplied https://www.youtube.com/watch?v=v9QtM6qnG50 for testing in response to ownership/permission request. Default save-only; no publishing authorization implied. Output defaults to managed workflow bundle until user chooses another local destination. ClipX path known. Account/client config and final schedule are account-dependent inputs, requested only after file pipeline validation.

## Dependencies and licenses
Core Ninja reuses stdlib, httpx, filelock, Pydantic, FFmpeg and existing worker. Add yt-dlp[default] pinned to tested release; Node is the explicit JS runtime and packaged yt-dlp-ejs solver, no remote solver execution or cookie scraping. FFmpeg licensing depends on installed build (record `ffmpeg -version`). Skills installed individually, without proxy/token-saving services; next Codex turn discovers them. Agent-Reach YouTube backend is yt-dlp; no fallback ASR/cloud/cookie extraction.

| Reference | Inspected revision | License / role |
|---|---|---|
| [agent-reach](https://github.com/Panniantong/Agent-Reach) | `a19a171fa980a0785849596492e0af4db800c82f` | MIT |
| [caveman](https://github.com/JuliusBrussee/caveman) | `6571943370f7c9d4de1946481177ee7b306cd8e8` | Apache-2.0 |
| [comfyui](https://github.com/Comfy-Org/ComfyUI) | `5c460d8172fe30761ff67c0df3d5643bb74e0d70` | GPL-3.0 |
| [hypit](https://github.com/hypit-ai/hypit) | `7f730abf72fa1e4a543eed8cd1807319d9f18196` | NOASSERTION |
| [shotcut](https://github.com/matrodrigs/shotcut-mcp) | `f1b78d350a9992296f0b7f11a55c04819ea25730` | MIT |
| [superpowers](https://github.com/obra/superpowers) | `8ca22dba9a94f28898bbce59f2537ff4d87c747d` | MIT |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | `51bab8a0116f4d8004c315706d809782607d5847` | Unlicense |
| [OpenChatCut](https://github.com/0xsline/OpenChatCut) | `297b3279e8f34bd8cb984a64634efdd8db3cb858` | AGPL-3.0-or-later, separate service; Remotion license applies separately |

Hypit has additional license conditions (not plain Apache); no source copied. ComfyUI GPL-3.0; model licenses must be recorded per selected model repository, independent from engine license. No cloud credentials configured by this task.

## Progress / evidence ledger
- Audit and skill/repository snapshots saved under data/development/video-reference. Fresh isolated source baseline created.

## Verified implementation (2026-10-06)
- Supplied URL downloaded without cookies. ClipX CUDA transcript: 3,592 words. Real ranked outputs: 35.100 and 34.968 seconds, 720x1280; both fully decoded.
- Custom two-source prompt/reference edit: 10 seconds, 1280x720. Real reference analysis, validated model plan, OpenChatCut isolated draft committed as applied, final MP4 decoded. Model calls recorded actual usage.
- OpenChatCut MCP discovery and draft lifecycle verified. Separate occ render failed at an unrelated localhost:3000 service; the documented FFmpeg subset is the delivery renderer.
- Selected models and their encoder/VAE files downloaded and hash-verified. Z-Image: real 512x512 image, 26.18 seconds Comfy execution. Wan: real 256x256, 17-frame/16fps MP4, about 63 seconds end to end. RTX4060 8GB with CPU text encoding and memory offloading. No cloud fallback.
- Automated coverage includes source boundaries, cache invalidation, timing/speed, real multi-segment FFmpeg render, licensed sound cues, stale approval, exact policy/channel binding, scoped generation cancellation and idempotent output registration. Existing mocked YouTube upload/resume/schedule tests retained.
- User has no OAuth client yet and requested setup steps; see docs/video-guide.md. Real channel identification, private upload and schedule remain pending account connection. No public test posts.
- Local image recovery reused the saved Comfy prompt after an output-verification failure; no duplicate generation was submitted.
- Backend: 69 tests passed before the final cache regression was added; final results are recorded in docs/video-validation.md. Frontend build and real browser at 1440/1024/768/320 passed.
- Remaining fidelity limits: manual crop (no subject tracking), native ASR timestamps require review, supported effects only, OpenChatCut text/crop/audio layout may differ from the Ninja FFmpeg preview. Audio cues use user-supplied licensed audio. Reference audio properties remain unknown when frames cannot establish them.
- Selected model repositories (unsloth/Z-Image-Turbo-GGUF, Comfy-Org/z_image_turbo, Comfy-Org/Wan_2.2_ComfyUI_Repackaged) declare Apache-2.0. Engine/service licenses remain separate. Exact revisions and LFS SHA256 values are in selected-models.json and the download script. Weights are excluded from Ninja source.

Delivery verified: 34 guarded source/build paths applied with backup; live video API authenticated on port 8000; ClipX/editor/FFmpeg/ComfyUI ready. Original settings/project records/media unchanged. Graph refreshed (556 nodes, 991 edges), wiki/studio exported, portable check passed. PowerShell AST support missing for five files and 18 invalid-edge warnings limit graph coverage; direct script review remains necessary. OAuth account checks remain pending.
