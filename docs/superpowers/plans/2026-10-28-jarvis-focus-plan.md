# Jarvis focus plan: remove video, make voice real-time, simplify UI

Date: 2026-10-28. Owner focus: Jarvis voice assistant, agent workability, YouTube management. Video generation, image generation and video editing are removed now and can be restored from the backup later.

Sources: delete inventory (read-only code audit), real-time voice research, UI research, and the owner's GitHub stars (github.com/Karthik6146?tab=stars).

## Measured starting point

| Stage | Today |
|---|---|
| End-of-speech wait | 700 ms energy pause |
| Speech recognition (Whisper small, CPU, Hinglish) | ~2 s (two encoder passes of ~0.9 s) |
| Worker pickup + runner start | ~0.1 s + 0.3 s |
| Qwen first text / full reply (warm) | ~1.0 s / ~2.5 s |
| Browser polling | 250 ms |
| Kokoro first sentence (warm) | 0.3–0.4 s |
| Wake word | transcribe every phrase (~2 s CPU each) |

Voice-to-voice today is roughly 3.5–4 s. Industry target is ~0.8–1.5 s.

## Phase 0 decisions (owner, 2026-10-28)

- Delete: ComfyUI video/image generation and the image tool, Chat tab, Coding studio, all of `data/projects`, `data/services/comfyui`, unused files and dead code.
- Keep: Jarvis, Video Studio automation and the OpenChatCut editor (YouTube automation), YouTube upload path, Automations reports, Settings.
- The steps below that delete Studio/editing modules are superseded by this list.

**Phase 0 status: done (2026-10-28).** Backup `data/backups/pre-focus-20261028.zip` (34 MB, code + database). 39.2 GB freed. Backend 190 tests, frontend 22 tests, typecheck and build pass; live app checked (Jarvis, Studio, YouTube, integrations). Removed routes return 404. Knowledge graph flagged for `/graphify . --update`.

## Phase 0: Backup and removal

Goal: smaller, faster project with only Jarvis, agent tools, YouTube and settings.

1. Backup first (no git here): zip all code, scripts, docs, tests, frontend source, requirements and the SQLite database into `data/backups/pre-focus-20261028.zip`. Model folders (ComfyUI ~30 GB, OpenChatCut) are not backed up; their setup scripts are inside the zip so they can be re-installed.
2. Move the pieces keep-code still needs out of modules being deleted:
   - `caption_config()` (video_sources) and `voices()` (studio_idea) into `voice.py`.
   - Multi-channel connect/disconnect routes (studio_routes :8-32) into `youtube_routes.py`.
   - YouTube search `research()` (studio_metadata) into `youtube.py`.
3. Cut the links: agent.py image/draft/children code and prompts, assistant_tools image/workflow tools, assistant_desk studio calls, worker video job kinds, api.py project/render/encoder routes and video routers, youtube.py studio SQL lookup, permissions grants.
4. Keep a minimal "finished video file -> YouTube upload" intake (import file, probe, package, upload) so YouTube publishing still works.
5. Delete: `video*.py`, `studio*.py` (after moves), `workflow.py`, `media_library.py`, video/CMS/guided/library frontend files and CSS, video scripts, video tests and docs, `VIDEO_AUTOMATION_PLAN.md`; drop `langgraph`, `langgraph-checkpoint-sqlite`, `yt-dlp`.
6. Delete data: `data/services/comfyui` (≥30 GB), `data/services/openchatcut`, `data/video-sources`, `data/video-analysis`, `data/video-workflows`, `data/generation`, `data/smoke`, `data/development`, video render outputs, `data/checkpoints.sqlite`, samples. Keep `data/projects` (media behind already-uploaded YouTube videos), `data/services/jarvis-voice`, `data/youtube-secrets`.
7. Navigation becomes: Jarvis, YouTube, Activity, Settings.

Done when: backend and frontend tests pass, app starts, Jarvis answers, YouTube page lists channels, freed disk space reported.

## Phase 1: Voice quick wins (target ~1.5–2 s)

1. Stream replies to the browser over Server-Sent Events instead of 250 ms polling.
2. Ollama `keep_alive: -1`, thinking off (already off).
3. Speech recognition: with ComfyUI gone the GPU has room. Option A: Whisper on GPU (needs ~1 GB NVIDIA cuBLAS/cuDNN download into the ClipX environment). Option B: reuse the previous turn's language to skip the second CPU pass.
4. Keep the durable job queue for tool actions, but measure whether plain conversation can skip it.

**Phase 1 status: done (2026-10-28).** Measured live (simulated voice turn through the running app, median of 5):
first sound after you stop talking ≈ 3.5 s (was ≈ 4.8–6 s). Recognition 2.2 s → 0.25 s (Whisper on GPU, CPU fallback; +350 MB VRAM),
Qwen prompt 0.9 s → 0.3 s (stable prompt prefix for Ollama's cache), push stream replaces 250 ms polling, `keep_alive:-1`,
short butler opener + clause splitting so speech starts on the first words. Remaining cost, for Phase 2: 0.7 s end-of-speech pause,
~0.45 s job queue + runner process per turn, 0.27 s ffmpeg decode of the uploaded clip, ~0.3 s draft save/stream hops, ~0.5–0.8 s first TTS.

## Phase 2: Real conversation turn-taking (target ~1–1.3 s)

1. One WebSocket carrying 16 kHz audio from an AudioWorklet (replaces MediaRecorder uploads).
2. Silero VAD (~200 ms) + Smart Turn v3.2 (BSD-2, Hindi supported, 10–65 ms CPU) instead of the fixed 700 ms pause.
3. openWakeWord `hey_jarvis` (code Apache-2.0, model CC BY-NC-SA: personal use only) replacing transcribe-and-check.
4. Proper barge-in: speech ≥250 ms during playback cancels LLM and TTS, flushes playback, and trims history to what was actually spoken.

**Phase 2 status: done (2026-10-28).** Live WebSocket audio (AudioWorklet, 16 kHz int16) -> listener resident in the jarvis-voice
environment (Silero VAD v6, Smart Turn v3.2, openWakeWord hey_jarvis; numpy + onnxruntime, ~0.15 s CPU per second of audio) ->
native WAV straight into GPU Whisper (no ffmpeg) -> transcript pushed back. Barge-in on listener speech events, optional mic mute while
Jarvis talks, pre-started runner per assistant turn, all helpers warmed on Talk. Measured real-time over the running app with synthetic
speech: end of speech -> text 0.4–0.8 s; -> first sound ≈ 2.5 s median (was ≈ 3.5 s; ≈ 4.8–6 s before Phase 1). Not yet verified with a
real microphone, room echo or real (non-synthetic) Hinglish speech.

## Phase 3: UI redesign

1. Slim icon rail: Jarvis, YouTube, Activity, Settings (bottom tabs on mobile). Home, Chat and the collapsible stacks are removed.
2. Jarvis text mode: one centered 720 px column, conversation history in a slide-out drawer, one composer with mic and send.
3. Voice mode: full-screen overlay with an audio-reactive orb (Web Audio, no dependency) showing idle / listening / thinking / speaking / standby, last 1–2 caption lines, and mute / interrupt / end buttons.
4. Tool actions as collapsed cards ("Ran 3 steps ✓ 2.1 s"), expanding on click or error; full log in Activity.
5. Settings grouped: Voice, Models, YouTube account, Appearance. Voice settings leave the Jarvis screen.
6. Built with the installed design skills (impeccable, emil-design-eng). Optional small libraries: `lucide-react` icons, `sonner` toasts.

**Phase 3 status: built (2026-10-28), awaiting the owner's look in the real app.** Labelled icon rail (Jarvis, Studio[Video Studio, Automations,
Media Library, Content], YouTube, Activity, Settings, Stop) that becomes a bottom tab bar on phones; navy/cyan/gold tokens in shell.css; authored
SVG icons; Jarvis screen (greeting + real-capability suggestions, centred column, one collapsible action card, composer with mic, History and
Today drawers); full-screen voice mode with the audio-driven arc-reactor orb, captions, Mute / Interrupt / End, settings gear, minimise to a
floating orb. Removed: the stacked Home sections, the duplicate "Talk to Ninja" box, decorative eyebrow labels, the "Record one message"
dictation button. Checked: 31 frontend tests, typecheck, design detector clean, preview renders at desktop and phone width.
Not yet done: Settings regrouping (Voice, Models, Memory, Accounts); Studio/YouTube internals still use older component styling.

## Phase 4: Agent workability

1. Tool reliability: clearer tool descriptions and a regression set of real Hindi/English/Hinglish requests that must call the right tool.
2. Agent-Reach (starred) style read-only research tools: YouTube, Reddit, web search.
3. Broader desktop control (browser-use / CLI-Anything, starred) as a separately approved slice.
4. Memory upgrade toward semantic recall (agentmemory as reference).

**Phase 4a status: done (2026-10-28).** Tool-choice eval (tests/evals/jarvis_tools.jsonl, scripts/eval-tools.py, 36 real requests):
33% -> 100% voice / 97% typed. Root causes fixed: persona "acknowledge first" lines made Qwen narrate instead of calling tools; an empty
"documents: []" note on the first message suppressed tool calls; the no-tools speed shortcut caught personal questions; 14 of 18 tools had no
description. New read-only tools: weather.now (Open-Meteo), research.deep (Bing / Bing News, reads up to 3 pages, cites [n]), youtube.search.
Reddit dropped (anonymous access blocked; official API needs an owner-registered app). Live check: weather, Calculator, Notepad, reminder,
CPU and news research all used real tools. Known: the owner's YouTube sign-in token has expired and must be reconnected.
Next: 4b PC control, 4c Gmail, 4d WhatsApp (notification-based, read-only, recommended).

**Phase 4b status: done (2026-10-28).** app.open (any Start-menu app via Get-StartApps + shell:AppsFolder, Settings pages; shells/admin tools
blocked), web.open (https only), media.control (media keys), file.find (names in the six known folders, bounded walk), file.open (allowlisted
document/media types inside personal folders only). Honesty net widened: device/research verbs and claimed completions ("badha diya", "I have
paused") trigger the tool retry. Eval 45 cases: voice 45/45 first try, typed 42/45.

## Phase 5: YouTube management

1. Channel dashboard: channels, recent videos, analytics.
2. Upload a finished video: title/description/tags drafted by Qwen, reviewed, scheduled.
3. Comment triage and replies (methods from the installed yt-* skills).
4. Jarvis tools for YouTube: "how did my last video do", "schedule this upload".

## Phase 6 (only if needed): Pipecat

If Phases 1–2 still feel slow, move the real-time loop (not the whole backend) to Pipecat (BSD-2, most active framework), keeping the job queue as the tool backend. Target ~1.0–1.2 s.

## Order and gates

Phase 0 -> 1 -> 2 -> 3 -> 4 -> 5. Each phase gets a short design approval before code, tests before claims, and a live measurement after.

**Phase 4c status: done (2026-10-28).** gmail.list / gmail.read (gmail.readonly, several accounts, DPAPI vault, shared Desktop OAuth client, testing mode, weekly reconnect). Generic confirmation: grants accept True / 'ask' / False; a conversation that has read email or web text (task.tainted) needs Allow once / Deny for every non-read tool; pause() stores task.pending and confirm() resumes on a new job with a parameter-bound approval. Fixed a 4b bug: device tool callbacks took positional (p,t,c) while tools.invoke passes timeout=/context= by keyword, so every device tool failed at run time; a signature guard test now covers every registered tool. Eval: typed 47/49, voice 49/49. Backend 255 tests.

**Phase 4d status: done (2026-10-29).** whatsapp.recent reads WhatsApp Desktop toasts from %LOCALAPPDATA%/Microsoft/Windows/Notifications/wpndatabase.db (read-only SQLite URI); an API-lifespan thread copies them every 15 s into whatsapp_messages (7-day retention), because WhatsApp clears toasts once read on the phone. Permission messages.read (untrusted, taints the conversation). WhatsApp Web automation was declined (ToS and ban risk). Added "yaad dilana" remind intent. Eval: typed 50/52, voice 52/52. Backend 257 tests.


**Security audit (2026-10-30).** Cloudflare security-audit skill, standard profile, 35/35 agents, source-only (no Windows sandbox). 0 confirmed, 7 needs-validation leads, all fixed: session cookie is a revocable random id (not the master token); default origins only :8000; shared-document text taints Jarvis turns; OpenChatCut import roots limited to data/video-sources and data/projects; AI-written YouTube metadata cannot contain links and is never auto-published publicly; edit-plan burned-in title is never model-written; no hardcoded caption-tool fallback. Hardening: security headers, empty-token refusal, NAT64/6to4 SSRF block, model download hash verification, http(s)-only third-party links, WhatsApp retention, gitignore .env.*. Deferred (budget): langgraph checkpoint + yt-dlp node JS runtime review. Report: ~/security-audit-skill/ninja-assistant/run-1/REPORT.md. 271 backend tests.
