# Jarvis assistant user guide

Updated 2026-10-14. Jarvis is Ninja's local conversational assistant: ask general questions, continue a conversation, or request supported tools. The companion and one-button voice upgrade are installed; voice validation records checks and measured limits.

## Open and use it

Open **http://127.0.0.1:8000**, refresh the browser and select Home → Jarvis. Connect with your existing Ninja token from .env or data/access-token; no new login is required. Keep Ollama running with qwen3.5:9b selected.

The previous isolated preview is stopped; use the live localhost app above.

Home → Jarvis → **Your message** → **Send message**. Ctrl+Enter also sends. Hinglish is the default for new companion preferences; change **Speech language** for another language.

- “Jarvis, CMS kya hota hai? Simple example do.”
- Follow up: “Ab mere YouTube channels ke liye explain karo.”
- “What are today's tasks? Add a priority to prepare two Shorts.”
- “Check CPU and memory usage.”
- “Open Calculator.”
- “Remember that I prefer concise Hinglish replies.”
- “Remind me tomorrow at 7 PM IST to check my queue.”
- Select a channel, then “List my workflows and run the ClipNet workflow.”

Continue in **Your next message**. The conversation retains recent context and retrieves saved memory from its authorized scope. **New conversation** starts another thread. Choose a different channel before its first message; an existing thread keeps its original channel and approved documents.

General questions use a direct Qwen answer without an extra tool-recovery pass. **Jarvis · writing** is a live draft, not evidence of a completed action. Measured model/first-text timings appear below progress when available. Cold model loading, longer answers and GPU work can still delay replies.

Routine capabilities use the saved switches in Settings → Jarvis memory and permissions. Spending, security changes, unrestricted shell commands and sensitive-data disclosure tools are unavailable. The model cannot grant itself permissions.

Conversations, steps, result evidence and linked jobs survive refresh. **Tool actions and evidence** contains actual receipts; Qwen prose alone does not prove an action happened. Ordinary conversation needs no action receipt. Failed or unverified requested actions are reported. Send another message or expand **Change the next task step** to revise pending work. Jarvis can revise a linked unfinished video workflow through the existing Video Studio revision service. Updates apply to the next uncommitted step; completed actions remain visible and publishing is locked once it has begun.

**Stop task / Stop linked work** stops pending local processing and pending uploads/status jobs. Already dispatched remote effects may finish. Publication schedules already accepted by YouTube need cancellation through the existing YouTube controls.

## Control your PC

Ask in English, Hindi or Hinglish; Jarvis needs Windows unlocked.

- **Apps:** "Open Chrome", "VLC kholo", "Open Bluetooth settings". Any app in your Start menu (classic or Store) and common Settings pages. Shells and admin tools (PowerShell, Command Prompt, Terminal, Registry Editor, WSL) are never opened by voice.
- **Websites:** "Open youtube.com" opens it in your default browser. Only https addresses.
- **Media and volume:** "Gaana pause karo", "Next song", "Volume thoda badhao" (about 2% per step), "Mute".
- **Files:** "Find my Valorant clip" searches file names (not contents) in Desktop, Documents, Downloads, Videos, Pictures and Music, including OneDrive-redirected ones; "open the first one" opens it with its usual app. Only documents, images, audio, video and subtitles open; programs, scripts and shortcuts are always refused.

Switches in Settings → Jarvis memory and permissions: app.open (apps and websites), device.control (media and volume), files.personal (find and open personal files).

## Email (Gmail, read-only)

Ask "any new emails?", "mail aaya kya?" or "did Amazon email me this week?". Jarvis lists unread or matching mail across every connected Gmail account and can read one message in full to summarise it. It cannot send, delete or archive mail.

Connect accounts in **Settings → Jarvis memory and permissions → Gmail accounts**: select **Add a Gmail account**, then **Sign in with Google**, once per address. Gmail uses the same Google OAuth client as YouTube; enable the Gmail API in that Google Cloud project first. The Google app stays in testing mode, so Google expires each sign-in after 7 days. When Jarvis says a sign-in expired, connect that account again.

## WhatsApp (read-only, from notifications)

Ask "any WhatsApp messages?", "Rahul ne WhatsApp pe kya bola?" or "कोई व्हाट्सएप मैसेज आया?". Jarvis reads the Windows notifications WhatsApp Desktop shows. While Ninja runs, it copies new ones every 15 seconds into its own database and keeps them for 7 days, because WhatsApp clears a notification once you read the chat on your phone.

Setup: install WhatsApp Desktop from the Microsoft Store and link it to your phone. Keep its notifications on (WhatsApp → Settings → Notifications, and Windows Settings → System → Notifications → WhatsApp) with message previews shown.

Limits: Jarvis only knows what a notification showed. There is no older history, no media, nothing from muted chats, and nothing that arrived while Ninja was closed. It cannot send messages. Message text is treated like email, so later actions in that conversation ask first. Turn it off with **messages.read → Off** in Settings.

## Confirmations

Email and web pages are written by other people and can contain instructions aimed at Jarvis. Once Jarvis has read email, WhatsApp, web text or a document you shared in a conversation, every action in that conversation (open an app, set a reminder, change a file…) waits for an **Allow once / Deny** card. Reading tools stay free. You can also set any capability to **Ask me first** or **Off** under **What Jarvis may do**. Speaking a new request instead of answering the card declines it.

## Research, weather and YouTube search

Jarvis can look things up for you (read-only, nothing is posted):

- **Weather:** "Noida ka mausam kaisa hai?", "Will it rain in Delhi tomorrow?" uses Open-Meteo for the current conditions and a three-day forecast.
- **Research:** "GTA 6 ki latest news kya hai? internet pe check karo" searches the web (Bing, or Bing News for recent topics), reads up to three pages and answers with numbered sources [1] [2]. Pages it cannot read are listed, never cited.
- **YouTube search:** "Find popular YouTube videos about Valorant tips" uses your connected channel's read-only access. If Google reports an expired sign-in, reconnect the channel on the YouTube page.
- Reddit is not available: Reddit blocks anonymous access, and its official API needs an app you would register yourself.

Turn research off under Settings → Jarvis memory and permissions (research.read). `scripts/eval-tools.py` measures how reliably Jarvis picks the right tool on 36 real Hindi, English and Hinglish requests.

## Video projects and channel profiles

Select the exact channel before asking Jarvis to use its workflows. Jarvis cannot change an existing job's authorized channel.

Existing activated workflows keep their publishing policy, including previously enabled automatic publishing. A new idea/source produces a proposed video draft with source permission questions, understood style and missing dependencies. **Save and open in Video Studio** saves an independent inactive project with review policy. Existing workflow defaults and scheduled videos are preserved. A changed instruction invalidates an older unsaved plan. Saved and unsaved editor changes survive refresh. After opening a different Jarvis/CMS proposal, **Restore previous editor draft** restores the editor draft you left.

Video Studio continues to handle footage import, clips, renders and publishing. Captions and voice transcription reuse the existing standalone ClipX tool. Ninja does not install a second caption engine.

## Memory and privacy

Settings → **Memory scope** selects Personal, a Workspace or a connected Channel. Add, correct, forget or export facts in that scope. Retrieval is scoped before ranking; corrected facts replace obsolete text in future model context.

Automatic memory accepts only defined language, tone and editing preferences. Add other non-sensitive facts manually after review. Ordinary task/chat history, selected-file edit receipts and saved ordinary facts are plaintext. Sensitive-memory encryption and unrestricted automatic extraction are not enabled.

**Forget this conversation** removes that assistant request, its steps/jobs and facts derived from it. Stop/finish running or linked work first. Manual facts, requested files, video outputs, existing Chat conversations and backups are separate records.

Home → **Private conversation** uses local Qwen without saved conversation/history, tool execution, memory retrieval or usage-ledger entries. Refresh, Clear or Leave removes the browser-held conversation. Voice audio is temporarily processed locally and deleted after transcription. OS memory and separately configured Ollama logs are outside Ninja's history guarantee. **Stop waiting** ignores a late response; the local model may finish its current request.

## Approved documents and file editing

Configure narrow non-sensitive folders with `NINJA_ROOTS` in the real assistant's .env. Select **Share a text document**, supply an exact server-side path and confirm that it contains no secrets or sensitive personal information. Only that selected document becomes readable to the task. Credentials and protected paths remain blocked.

Small .txt/.md edits create an exclusively named `.jarvis-...` edited copy beside the selected source. Originals remain intact, including concurrent editor saves. Source files are limited to 10,000 bytes and proposed text to 2,000 characters. Ask Jarvis to undo the edit to archive the generated copy. A changed copy is retained and requires inspection. Receipts do not authorize another task to edit/undo it.

## Talk with Jarvis

Refresh with **Ctrl+F5**, open Home, and press **Talk to Jarvis** once. Allow the microphone when your browser asks. The microphone then stays open for the whole conversation and streams to a local listener, which decides when you have finished a thought (Silero voice detection plus the Smart Turn model). Short pauses mid-sentence are tolerated; a finished sentence is answered about a quarter of a second after you stop. Jarvis starts speaking with a short opener such as “Of course, sir.” while the rest of the reply is still being written. Pressing Talk preloads Qwen, recognition, the voice and the listener.

Jarvis speaks as a calm British butler and addresses you as "sir". The default voice, **Jarvis · British male (Hindi voice for Hindi)**, reads English sentences in the British Kokoro voice and Hindi sentences in the Hindi male voice. You can speak Hindi, English or Hinglish freely within a sentence. To change the reply language, say so: "Speak in English", "Hindi mein bolo" or "Hinglish mein baat karo". The **Reply language** selector follows the change for the rest of the conversation.

**Interrupt by talking** (on by default): start speaking while Jarvis talks and he stops at once. This relies on your browser's echo cancellation; if your speakers make Jarvis interrupt himself, turn the checkbox off (the microphone is then muted while he speaks) or use headphones. Say "that's all", "thank you" or "बस" to finish. **End conversation** stops audio and releases the microphone.

**Wake word mode** (checkbox under the Talk button): press **Start standby** once and say **“Hey Jarvis …”**, for example "Hey Jarvis, open Calculator". The wake word is detected locally by openWakeWord; phrases without it are discarded by the listener without being transcribed, shown or saved. Saying "that's all" or 25 seconds without speech returns to standby. In this mode the microphone stays on when the tab is hidden; in normal mode hiding the tab releases it. The hey_jarvis model is licensed for personal, non-commercial use only.

The **Last turn** line shows measured timing for your microphone. If live listening is not installed, Ninja falls back to the earlier record-and-pause mode.

Uncertain speech asks you to repeat; it is not sent as a task. Silence, unrelated scripts in Hinglish and obvious repeated hallucinations are rejected. No recognizer is perfect: check names/numbers and correct a mistaken turn by speaking or typing again. Conversations/channel selection and detailed task controls are collapsed by default.

Speech recognition still uses your existing standalone ClipX adapter, now with a local **Whisper small multilingual** model on your GPU (about 0.25 s per turn; it falls back to CPU automatically, or set `JARVIS_VOICE_DEVICE=cpu`). Neural speech uses **Kokoro v1.0 on CPU** in an isolated Python environment under `data/services/jarvis-voice`. Models remain resident between turns. There are no cloud speech calls, paid fallbacks or new caption-generation implementation. Temporary recordings and generated reply WAV files are removed after processing.

For a fresh installation, from the project directory run:

```powershell
& '.\.venv\Scripts\python.exe' '.\scripts\setup-local-voice.py' --project (Get-Location).Path
```

This explicitly downloads the fixed local models and pinned speech packages; normal conversations do not download anything. `JARVIS_VOICE_HOME` optionally points to the installed speech folder, and an explicit `JARVIS_VOICE_MODEL` still overrides the recognition model. Restart Ninja after setup. Model sources/licenses are recorded in `docs/voice-model-sources.json` and `THIRD_PARTY_NOTICES.md`.

Voice quality and accuracy depend on the microphone, room and pronunciation. Hindi in Devanagari is pronounced more reliably than Roman Hindi; spoken requests ask Qwen for native-script Hindi plus English terms, but generated wording can vary. First use loads models and is slower. Headphones help with echo and room noise.

## Workers and setup

The revised `scripts/start.ps1` starts the existing media worker plus a separate assistant control worker. Both must run for durable assistant tasks; local processing/reminders wait while the PC is off. GPU-heavy model/media work keeps the existing model lock.

Start the live assistant with `scripts/start.ps1`; it starts both worker lanes. A backup taken before the 2026-10-28 cleanup (video/image generation, Chat tab and Coding studio removed) is at `data/backups/pre-focus-20261028.zip`.

## Validation and remaining capability boundaries

Backend regressions, frontend build/tests and independent runtime/browser review cover scope binding, revision checks, replay, cancellation, memory correction, consent, private clearing, narrow screens and voice lifecycle. Public publishing is mocked in tests; no test video was published.

Real Qwen successfully invoked the task tool; real local SAPI audio → browser-style WebM → ClipX returned the expected English sentence. Timing measurements and screenshots are in validation. Companion design choices, source links and voice limitations are cached in companion research.

Supported desktop launchers are Notepad, Calculator and Explorer under an active unlocked Windows session. Full browser/UI Automation control, wake word, device integrations, sensitive-memory storage, semantic recall and arbitrary software analysis are later slices requiring named targets and separate verification. Source fetching supports bounded public HTTPS text/HTML; redirects, login-required content and arbitrary downloads/executables are not followed.

