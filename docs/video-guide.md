# Video Studio

Open Ninja at http://127.0.0.1:8000, connect with your existing local token, then choose **Projects → Video Studio**. This uses your existing settings, jobs, ClipX tool and YouTube connection.

## YouTube clips
1. Choose **YouTube Clips**. Paste individual video URLs you own or have permission to reuse. Playlist links require selecting individual items.
2. Choose clip count, target length (30–180 seconds), preset, output format and an optional approved destination folder. Confirm source rights.
3. **Build edit and preview** downloads, analyzes scenes/audio/frames, asks ClipX for word timestamps, selects candidates and prepares previews. Leave the worker running. First-time transcription can take a while on CPU; completed results are cached.
4. In **Review**, inspect every clip. Adjust in/out, speed and normalized crop coordinates. Save edits to rebuild previews. A new edit invalidates the old preview approval.
5. **Approve previews and save final files** creates verified MP4 files and an editable bundle. This does not upload anything.

Highlight ranks are suggestions with evidence and confidence, not predictions of viral performance. Model ranking uses the local Ollama model; unsupported vision or invalid JSON produces a visible warning and deterministic candidates for manual review. Reported token counts are actual provider counts; missing counts are not estimated.

## Custom footage and conversational editing
Choose **Custom Edit** and upload one or several videos, select recordings already imported in Ninja, or select a folder under `NINJA_ROOTS`. Give editing instructions and optionally select an imported reference. Enable local-model analysis for natural-language instructions. Reference analysis uses sampled frames, scene boundaries and speech-resumption timing; it marks properties it cannot establish. It does not copy reference footage/music.

The shared plan supports ordered clips, speed 0.5–2×, manual crop, zoom, gain, an opening title, restrained fade/contrast/slow-zoom effects, supplied music and ClipX captions. Use the advanced JSON plan to reorder segments or set `audio_project` to an existing recording with uploaded licensed music. Effects outside this supported set are rejected.

Caption generation stays in your configured **ClipX** installation. Ninja invokes its existing `transcribe-local.py` using its existing `.venv-whisper` and cached model. Hinglish uses ClipX's existing `romanizeHindi` function. Ninja only imports, retimes and renders captions. There is no second ASR installation or caption editor.

On this machine, ClipX CUDA is verified using the CUDA DLLs already supplied with Ollama. If that installation changes, set `CAPTION_CUDA_DLL_PATH` or explicitly choose `CAPTION_TOOL_DEVICE=cpu` before starting Ninja. Word timestamps come from ClipX's native ASR alignment; review them against the preview before publishing.

For a licensed sound effect, upload its audio using the existing recording's music upload, then add an advanced-plan cue such as `"sound_effects":[{"project":"YOUR_32_CHARACTER_PROJECT_ID","start":2,"source_start":0,"duration":1,"volume":0.4}]`. `start` is the output timeline time; `source_start` trims the uploaded audio. Cues must fit both the audio source and the edit. Audio files and an ID-to-file manifest are included in the portable bundle.

## Editable projects and exports
When OpenChatCut is running, Ninja creates separate projects, imports media into an isolated draft, applies supported edits, reviews/commits the draft and confirms `applied`. Its link appears in Review. No existing editor project is overwritten. JSON snapshots are retained per revision.

OpenChatCut's editable copy uses centered cover framing and text overlays. Its text positioning, manual crop, music and advanced effects may differ from Ninja's preview. The **Ninja MP4 uses the exact validated plan through FFmpeg**, at 720×1280 vertical, 1280×720 horizontal or 720×720 square; preview dimensions are halved. Every output is probed and fully decoded before completion. OpenChatCut's separate `occ render` was tested and failed because its Remotion renderer reached another service on localhost:3000; external MCP does not expose MP4 export. That service was not stopped.

Final output folder: `data/outputs/ninja-<workflow>-v<revision>/` unless you chose another approved folder. Each bundle includes MP4, SRT/VTT/ASS, source manifest with relative paths, copied source media, edit plans, and available OpenChatCut snapshots. Originals are preserved. JSON plans are the editable source of truth; use their asset IDs with the manifest paths when reopening elsewhere. Existing output files are never silently overwritten.

## Publish or schedule
Final clips are registered automatically in Ninja's existing content packages. **Publishing** offers the existing Google OAuth flow and upload ledger:

### First-time YouTube sign-in

1. Open [Google Cloud Console](https://console.cloud.google.com/) and create/select your own project. In **APIs & Services → Library**, enable **YouTube Data API v3**. Enable **YouTube Analytics API** only if you want reports.
2. Open **Google Auth Platform**. Complete **Branding** with an app name and your support/contact email. In **Audience**, choose External if needed, keep Testing, and add the Google account that owns your channel as a test user.
3. In **Clients → Create client**, choose **Desktop app**. Download the client JSON. Keep this file private; an API key or Web application client will not work here.
4. In Ninja, open **Projects → Video Studio → Publishing**. Use **Import downloaded Desktop client JSON**. Choose the optional visibility/scheduling permission if you want publishing; analytics is optional.
5. Click **Prepare Google sign-in**, then **Sign in with Google**. Keep Ninja running at `http://127.0.0.1:8000`. Choose your intended Google account/channel and approve the requested permissions.
6. Return to Ninja, select **Refresh YouTube**, and check the displayed channel name and channel ID before preparing any upload.

Ninja never needs your Google password in chat. The downloaded client and tokens are stored on the backend using Windows DPAPI. Use **Disconnect locally** to remove local credentials; revoke remote access in [Google account connections](https://myaccount.google.com/connections). Follow Google's [desktop OAuth guidance](https://developers.google.com/youtube/v3/guides/auth/installed-apps) if the consent screen reports a configuration error. Testing-mode grants may require reconnecting. Some unaudited API projects are [restricted to private uploads](https://developers.google.com/youtube/v3/docs/videos/insert).

### Review and publish

1. Follow [YouTube setup](youtube-automation.md) to import a Desktop OAuth client and sign in in your browser. Never provide passwords, cookies or tokens in chat.
2. Verify the displayed channel name and channel ID. Save title, description, rights, final file and exact channel in its package; review metadata.
3. Prepare and approve a private upload. Inspect processing/remote status before choosing public visibility or a future schedule.
4. A schedule uses the reviewed future date with an explicit timezone. Asia/Kolkata is `+05:30`; UTC is stored and YouTube performs server-side publication. Your computer is needed to upload and confirm the schedule, not at publication time.

Optional **publishing policy** authorizes one action for one selected workflow and exact connected channel, only for reviewed final files/metadata. Enable it using the explicit checkbox. Preparing a reviewed package then applies that authorization without another approval prompt. Future-dated scheduling still requires the date in each reviewed draft. Disable the policy to stop future authorizations; cancel already queued operations or remote schedules separately. Save-only is the default.

Interrupted uploads retain the existing resumable ledger keyed by channel/render hash. Reconcile uncertain uploads before retrying; never create another upload to guess whether the first succeeded. API-project restrictions may keep uploads private. Account-dependent validation remains pending until you connect a channel; no public test posts are made.

## Start optional services
Keep the existing Ninja startup command:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

In separate terminals, after service setup:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-video-service.ps1
```

Reproducible editor setup:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-video-services.ps1
```

OpenChatCut is pinned at `297b3279`. Local ComfyUI image/video generation was removed on 2026-10-28; its setup is preserved in `data/backups/pre-focus-20261028.zip`.

## Recovery
For editing, use **Continue / retry preparation** after fixing the cause of a failure. Completed stages and per-source caches are reused. Cancellation uses the existing Activity panel. A worker interrupted during a stage exposes its durable failure and allows a manual retry. Start services, then refresh Integrations to diagnose connections. The global emergency stop blocks new actions; it cannot undo YouTube schedules already accepted remotely.
