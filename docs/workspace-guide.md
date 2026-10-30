Prompt-first Video Studio, editable YouTube profiles and daily Qwen assistant: [active assistant guide](active-assistant-guide.md).

Current navigation and video workflows: [guided workflow guide](guided-workflows.md).

# Ninja workspace guide

Home → Jarvis supports general conversation in Hinglish, local Qwen tools, editable progress, scoped memory and local image requests. Start voice conversation → Talk → Finish speaking sends clear speech and reads replies automatically; uncertain speech stays in review. See the [Jarvis guide](jarvis-guide.md) for setup, permissions and current voice limits.

## Access and start

Set the project path below to your local Ninja Assistant folder, then run:

```powershell
Set-Location -LiteralPath 'C:\path\to\Ninja-Assistant'
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

Open **http://127.0.0.1:8000**. No Ninja username or online account is required. Copy your private local token:

```powershell
Get-Content -LiteralPath .\data\access-token -Raw | Set-Clipboard
```

Paste into Local access token and Connect. If `.env` has a nonblank `NINJA_TOKEN`, that value takes precedence. Keep the terminal open; Ctrl+C stops the launcher. An already-running Ninja is detected without starting duplicates. Never stop an unrelated process merely because it occupies port 8000.

## Chat and projects

Keep Ollama running. Your verified installed model is **qwen3.5:9b**. In Settings, refresh connections, choose an installed model and save the default. Model health checks the actual local service and installed model list. No model download is automatic.

Chat saves conversations and visible replies in local SQLite. Search saved messages, create a conversation, or group conversations through Projects → Organization. Attach up to three plain text files, 8 KB each. A request accepts 12,000 characters; accumulated model context is bounded to 24,000 characters. Start a new conversation when the context limit is reached. The model has no unrestricted shell or tool access.

The primary sections are Home, Chat, Media Library, Video Studio, Automations and Settings. Collapse navigation to gain space. Show activity opens the optional Plan / Activity / Outputs panel. Activity shows observable steps, elapsed time and visible answer text, never private model reasoning. Reloading the browser restores the selected conversation and task.

## Task status and recovery

Queued tasks need the separate worker. Running tasks expose their current step. Unknown progress remains indeterminate. Completion means the result was saved; failed tasks show an error. Waiting for approval requires review in the relevant project or publishing screen.

Cancel task stops the job's process tree. Emergency stop cancels work and prevents new mutations until Resume execution. It cannot revoke publications already scheduled on YouTube. Retry safely is offered only for supported local work; external publishing uses its existing recovery controls. A new explicit rerun creates a new task. Repeating the same API submission key reuses its task and rejects conflicting inputs.

Chat and preparation workflows have a 15-minute outer timeout, 120-second provider read timeout and bounded output. Interrupted model jobs are not silently replayed. Probe/render/system scans have bounded lease recovery. Closing the browser does not cancel a job; closing the server does not erase it. Reconnect reconstructs state from SQLite.

## Automations

The default view is editable YouTube channel profiles with independent instructions, sources and schedules. See [active assistant guide](active-assistant-guide.md). Existing preparation tools remain under the collapsed workspace tools.

- **Research:** enter a question and one to five public HTTPS HTML/text source URLs. Run to retrieve excerpts, draft a cited report and download Markdown. Search-provider discovery is not configured. Citation IDs are validated against retrieved sources; factual support still needs your review.
- **YouTube preparation:** enter a topic and source URLs. The draft includes a script, three title options, description and tags. This workflow does not publish.
- **System diagnostics:** choose system, tools and/or provider checks. The report contains findings and proposed fixes. It does not delete files, terminate applications or install software.

Edit the fields, Save template, then rerun from the saved template. Completed reports appear in Outputs and Files. Failure to fetch sources or validate model output produces an error rather than a fabricated report.

## Media Library and captions

Open **Media Library** to import, preview and organise videos, then choose Create clips, Edit in Video Studio or Upload as finished. Video Studio has a prompt-first start and saved projects. The advanced trim editor still supports Save edits, Generate preview, review and Render final for the same revision. Originals remain preserved. Existing captions still support editing, styling and SRT/VTT/JSON export; saved suggestions remain accessible.

New caption generation belongs to your **ClipX** project. Set the path below to your local ClipX folder:

```powershell
Set-Location -LiteralPath 'C:\path\to\ClipX'
npm run dev
```

ClipX must have its own dependencies and configuration installed. Its root command starts the web application and worker; its default web address is **http://127.0.0.1:3000**. Settings → Caption tool stores this URL and project path. **Open Caption Tool** opens ClipX at its configured URL. Video workflows call the existing standalone ClipX CLI for transcription/caption import; Ninja does not rebuild caption generation. Settings shows actionable errors when its configured path or dependencies are missing. The inspected ClipX build uses its own demo-user session; Ninja provides no separate ClipX account or password.

Built-in Whisper generation, caption presets and Hinglish-variant creation were removed. Stored transcripts, caption variants, presets and exports are retained. Old WHISPER settings in your existing `.env` are inert and are not erased.

## YouTube login and other existing tools

Open **Settings > channel connections** for OAuth setup and **Automations > Profiles** for workflows. Advanced publishing and recovery remain available in the existing YouTube panel. Import your own Google Cloud Desktop OAuth client JSON and follow Google sign-in. Confirm the connected channel before preparing uploads. Never enter your Google password into Ninja. See [the detailed YouTube guide](youtube-automation.md) for client creation, exact-action approvals, private uploads, publishing, scheduling and recovery. No Google credentials were created or connected by this update.

Projects → Coding retains approved-repository inspection, isolated worktrees, generated candidates, reviewed native checks and patch downloads. Configure exact paths with `NINJA_REPOS` in `.env`; live Ninja source remains excluded. Projects → Content retains Instagram/Threads preparation and manual handoff. Those accounts are not connected. Files includes managed outputs, original media, caption exports, historical research notebooks and approved-folder/log inspection.

## Privacy, setup and troubleshooting

Inference defaults to loopback Ollama. Optional cloud requires backend `.env` configuration (`CLOUD_ENABLED`, HTTPS `CLOUD_URL`, `CLOUD_MODEL`, `CLOUD_API_KEY`) and explicit sharing consent in the request. Chat consent covers the conversation and attachments; workflow consent covers its question, preferences and retrieved excerpts. Provider billing may apply. Secrets are not shown in Settings or streamed to the browser. Browser automation and MCP show Not configured; no framework runtime is installed.

For a clean Windows setup install Python 3.11, Node 22+, FFmpeg/ffprobe and Git for coding, then run `scripts/setup.ps1`. Ollama and ClipX are separate applications. `.env` changes require restarting Ninja. `NINJA_ROOTS` allows exact approved folders for local imports and inspection; empty disables path-based access while upload still works.

If tasks stay queued, check Emergency stop and `data/worker.err.log`. For model errors, start Ollama and refresh Settings, then explicitly retry. For disabled final rendering, save, preview and approve the same revision. For source errors, use public HTTPS text/HTML URLs without redirects. Lock dashboard clears the current tab's stored token; it does not stop jobs.

Back up `data` and `.env` privately. Do not share tokens, OAuth storage or model keys. See [migration notes](workspace-migration.md), [reference mapping](improvement-references.md) and [validation report](workspace-validation.md).


For multi-channel work, open **Automations > Profiles**. Create/edit named YouTube profiles there; **Video Studio > Create** opens the prompt. See [Channel profiles](channel-profiles-guide.md) for shared briefs, saved channel instructions and the live progress/preview window.


Moved folder setup and validation: [Project relocation ? 12 October 2026](relocation-20261012.md).


Recordings is now **Media Library**. See [Media library guide](media-library-guide.md) for thumbnails, organisation, filters, archive and video workflows.
