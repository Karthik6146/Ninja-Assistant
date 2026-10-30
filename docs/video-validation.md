# Video Studio validation — 2026-10-06

Source changes were developed in `data/development/video-worktree`. The reviewable patch is `data/development/video-update.patch`; guarded delivery backs up affected files and SQLite to `data/backups/video-20261006`. Configuration and original media are checked by hash.

## Completed checks

- Full backend suite: **70 passed**, including existing YouTube mocks, new policy/channel/revision guards, cache invalidation, generation cancellation and real FFmpeg multi-segment/audio-cue rendering. Three existing dependency warnings remain.
- Production frontend build: passed, 300 modules. Real Chromium checks: input permission guard, custom-edit controls, saved workflow recovery, no page errors or horizontal overflow at 1440, 1024, 768 and 320 pixels.
- Supplied YouTube URL: real download, ClipX CUDA transcription, local-model ranking, editable OpenChatCut projects and captioned previews/finals. Two final clips: **35.100 and 34.968 seconds, 720×1280**. ClipX's existing large-v3-turbo installation produced 3,592 words. Hinglish reused its existing romanizer.
- Multi-video/reference instructions: model generated two five-second segments in the requested order, with captions and gentle fades. Final **10.000-second, 1280×720 MP4** decoded successfully. OpenChatCut project `fadc663f-f8bf-4903-b96f-62b83f5df87c` confirmed its isolated draft as applied. Three actual Ollama calls reported 7,764 total tokens.
- Generation: real Z-Image Q4_K_M 512×512 PNG; ComfyUI execution **26.18 seconds**. Real Wan2.2 TI2V-5B 256×256, 17 frames at 16 fps MP4; **62.92 seconds** including retrieval. Selected model files verified by SHA256. GPU: RTX4060 8188MiB; CPU text encoding and memory offloading enabled. These are small smoke tests, not larger-output performance claims.
- Generation recovery: an output-validator failure was fixed, and the same saved prompt retrieved the existing image without resubmission. Cancellation tests verify that another client's running prompt is never interrupted.
- Restart/failure handling: completed workflow stages and persisted previews survive process/browser restart; killed-worker state is surfaced from the job ledger. Failed custom selection resumed using existing ingestion/transcript caches after the isolated test's missing model setting was supplied.
- Publication safety: mutation of the current-preview approval check made the policy regression test fail, as intended. Real uploads remain gated by reviewed metadata, exact channel, rendered-file validation and existing resumable ledger.

## Local sample artifacts

Under `data/development/video-preview/`:

- `outputs/ninja-4c169b574cf24e77b63335e0d7cd0101-v0/`: two YouTube clip bundles.
- `outputs/ninja-9f5b41c6bdbb44b1a55215f41d498a14-v0/`: custom two-source edit bundle.
- `generation/511c17c6ab5642728ab69be5d9d8aefe/1.png`: generated image.
- `generation/f5ec3a26db7143e48aaf91355469f86b/1.mp4`: generated video.

Development records are isolated from the live assistant's database. Open the sample files directly; new live workflows appear in Video Studio.

## Remaining account checks and limits

The user has not configured a Google OAuth Desktop client. Live channel identification, private upload, processing and future scheduling remain pending that connection. No public test video was posted. Follow [the sign-in steps](video-guide.md#first-time-youtube-sign-in).

OpenChatCut's separate `occ render` failed because its Remotion renderer reached an unrelated service on port 3000. Ninja uses its verified FFmpeg subset for final MP4 delivery. Editable OpenChatCut copies may differ in text placement, manual crop and audio treatment. Subject tracking and effects outside the validated set are unavailable; manual framing is exposed. Review native ASR word timing and content/context before publishing.

Optional services must be running for their respective integrations. Model weights/services remain under ignored `data/services`; no cloud generation or unrestricted model shell was added.
