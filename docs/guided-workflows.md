# Ninja guided workflows

Start Ninja from the project folder:

    powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1

Open http://127.0.0.1:8000 with your existing local token. Keep the server and worker running for imports, editing, generation and folder monitoring. YouTube runs confirmed server-side publication schedules even when Ninja is off.

## Navigation

- **Home:** quick starts; existing coding, content, conversation organization and file tools remain under expandable sections.
- **Chat:** existing conversations and usage tracking.
- **Recordings:** imported video media, not agent sessions. Import/drop files, search, preview, then choose clips, editing or finished upload. Batch selection supports editing and finished upload.
- **Video Studio:** Upload finished videos / Create clips / Create from an idea / Edit my footage.
- **Automations:** guided video, research and system-diagnostics templates. Existing preparation tools remain available.
- **Settings:** Google connections, authorized server folders and existing integrations.

**Import media** copies a media file into Ninja. **Save project** saves workflow settings. **Open project** restores them. **Export video** renders an approved edit. **Upload to YouTube** is separate. Browser draft fields and unsaved trim/plan edits restore after navigation or refresh; saved definitions and runs live in SQLite. Newer saved revisions take precedence over stale local edits.

## Connect each YouTube channel

Your existing Desktop OAuth client is preserved. In Settings choose **Connect another YouTube channel**, open Google sign-in, select the intended account/channel identity and grant permissions. Return and refresh channels. Repeat for other accounts or identities; there is no five-channel cap.

Enable YouTube Data API v3 in the client's Google project. If its consent screen is in Testing, add your account as a test user. Callback: http://127.0.0.1:8000/oauth/youtube/callback. A client JSON configures the application; it does not sign in. Google must return exactly one authorized channel identity per connection. A typed channel ID cannot grant access.

Queued runs and operations retain their exact channel and connection. Changing dashboards never retargets them. Disconnecting stops credential use; reconnect and create a newly reviewed run if an old connection is no longer authorized. Access tokens refresh when needed; revoked refresh tokens require sign-in again. Google testing-mode expiration, quotas, permissions and unverified-project private-only restrictions still apply.

## Upload finished videos

1. Choose a channel, then imported files or an authorized **server** folder.
2. Choose a batch size. Files are inspected and copied unchanged; editing, captions and rendering are skipped.
3. Set metadata, audience/synthetic-content declarations, trigger, timezone and publication policy.
4. Save, test locally, review and activate. Manual workflows wait for **Run now**.

Blank title uses the filename. A matching video.json sidecar may contain title and description strings (16 KB maximum). Sources stay intact. Browser folder selection does not grant a durable server path.

Folder monitoring requires two unchanged size/mtime observations at least 30 seconds apart and a file at least 30 seconds old. Temporary .part files are ignored. Changing files are rejected during inspection. This cannot prove an external copier paused for over 30 seconds is done: write a temporary extension and rename when complete.

Duplicates are tracked by channel, workflow and file hash. Resume pending/failed reservations from their original run; later runs skip them. Use the explicit manual re-upload override only when another upload is intended.

Review policy leaves a separate private-upload approval. Other policies authorize their exact saved definition on activation. Uploads begin privately; public/scheduled policies change visibility only after verification. Unchanged saves retain activation; changed definitions pause it.

## Clips and editing

Supply an authorized YouTube URL or local footage. Ninja reuses yt-dlp, sampled evidence, ClipX transcripts and the existing editor. Review ranked candidates/reasons, adjust trim points, inspect previews, approve and export. Clip mode keeps outputs within 30–180 seconds.

Open **Review candidates and edit / export** from history. Back returns to the guided project. After export, **Collect approved final exports for publishing** applies the reviewed publication policy; review policy leaves private-upload approval pending.

Captions come from your existing ClipX installation. Ninja does not replace caption generation. Advanced plans support framing, speed, fades, contrast, gentle zoom, supplied music and timed audio cues. Supply licensed meme footage yourself; automatic meme sourcing and arbitrary editor effects are not provided. No viral performance is promised.

## Create from an idea

Enter a brief and optional public research URLs. Select a Windows narration voice and supplied recordings or configured ComfyUI images/video. Check dependencies. Ninja retrieves sources, creates a cited storyboard with Ollama, narrates locally, assembles scenes and imports ClipX captions. Preview/export through the existing editor.

No paid cloud fallback. Runtime is labeled unknown. Citations/storyboard remain in the run and data/studio-ideas/RUN_ID/storyboard.json; publishing collection adds them to the final bundle. Requested thumbnails remain in that run folder. Review factual claims and asset permissions yourself.

This version creates short narrated scene sequences. ComfyUI needs the configured local models; the standalone editor is optional for the supported FFmpeg export subset.

## Scheduling and recovery

Default timezone: **Asia/Kolkata**. Daily triggers use the selected IANA timezone; stored run and YouTube publication timestamps use UTC. Cadence separates videos within a batch. A missed daily trigger runs once when the worker resumes; it does not backfill every missed day.

Tests cannot prepare publishing. Activation requires review of the exact channel, inputs, actions and policy. Pause stops future runs and new automatic publication authorizations; it does not cancel videos already scheduled on YouTube. Use YouTube Studio or prepare a private visibility change.

History shows stage, error, outputs and retry. Retry reuses successful production artifacts. Upload recovery uses resumable sessions and reconciliation rather than another post. For uncertain completion, inspect YouTube Studio and reconcile the matching video.

The worker serializes GPU work. This machine currently has an Ollama model-manifest symlink error preventing model unloading for CUDA captions/generation. Model files were not modified. CPU ClipX validation succeeded. To explicitly select CPU captions for a session:

    $env:CAPTION_TOOL_DEVICE='cpu'
    powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1

Stop the existing Ninja server/worker before changing its process environment. Windows narration needs desktop speech access; restricted sandbox access can fail. Fix the reported dependency, then retry.

## Validation and references

See [implementation plan and reference licenses](usability-plan.md). No upstream automation-platform code was copied. Existing local services remain separate.

Public upload checks use six mocked identities. Actual Google sign-in, quotas, scheduling and publication still require connected accounts. No external video was posted during validation.

See [Automatic Shorts](automatic-shorts.md) for Qwen metadata, YouTube research and per-workflow automatic publishing.

The default Video Studio now opens the [Content CMS dashboard](cms-guide.md). The guided wizard remains available in advanced setup.
