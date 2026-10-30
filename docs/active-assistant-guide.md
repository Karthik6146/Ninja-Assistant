# Your active Ninja assistant

Open http://127.0.0.1:8000 and refresh after this update. Existing channels, workflows, media, token and configuration are retained.

## Start with a prompt

**Video Studio opens on Create.** Select a channel or Local workspace, describe your goal, then click **Plan with Ninja**. Choose **Create from an idea**, **Edit my footage**, **Create clips**, or let Ninja choose. Select existing media or upload footage directly. Editing uses local files; YouTube source links use Create clips. For an idea, a YouTube inspiration link guides the brief and is not downloaded as footage.

Ninja uses Qwen to interpret the brief and asks about missing source inputs or permissions. The plan displays the target and publishing policy. Answer questions under task settings and click Check answers. Test locally never publishes; Start task uses the displayed policy. Original ideas automatically choose an installed local voice; change voice/visuals if needed. Qwen writes metadata when configured, using the existing channel instructions and research.

Use **Suggest content ideas** with a connected channel and a topic. Ninja researches related recent and regional popular YouTube examples, then proposes original ideas. Evidence links, observed counts and retrieval time are retained. These observations do not establish current virality or permission to reuse content. Use this idea fills the prompt; it does not execute a task.

Open Content > Progress & preview to watch stages and outputs. Send revised instructions before publishing starts; Ninja stops the old version and continues a revision. Queued jobs retain their original channel/connection/policy. Publishing locks that version against changes.

## Editable YouTube automation profiles

**Automations opens on Profiles.** New YouTube profile creates a named workflow bound to a verified connected channel. A channel can have multiple profiles, with independent instructions, media, task mode, trigger, timezone and publishing policy. Connect additional channel identities through Settings; entering an arbitrary channel ID cannot grant access.

Save profile draft persists without activation. Save & activate uses the displayed schedule and publishing policy. Manual profiles run when clicked; daily profiles run at their saved time; finished-video folder profiles monitor an authorized server folder. An explicitly enabled public policy can publish without per-video review. Source permission and audience/synthetic-content declarations must be configured before publishing.

Use as this channel's default for multi-channel tasks links the profile to its channel card. The first profile for an unconfigured channel offers this option by default; an existing default is preserved unless explicitly selected. Choose channel cards, give a shared instruction, and use Test selected locally or Start selected profiles. GPU-heavy work runs in the existing single-worker queue. Each task has Progress & preview.

Edit profile changes instructions or schedule and pauses the previous activation until activated again. Existing queued jobs retain their saved settings and target. Channel instructions configures audience/general guidance and the default workflow used for batches.

## Your daily assistant

Home greets you and asks about today's tasks. Add, complete or remove priorities; they persist in SQLite per Asia/Kolkata date and restore after refresh. Ask Ninja or Help me choose the next step runs local Qwen advice on the worker, remembers recent daily conversation, and asks a focused follow-up question. Plan in Video Studio hands the suggestion to the prompt. Open full chat is available for other requests.

The greeting itself does not start a workflow or publish. This is an in-app assistant: it does not listen to your microphone or send background desktop notifications. Advice can cover other tasks, but account/tool actions require supported integrations rather than unrestricted model shell access.

## What must be running

No new model, paid service or automation platform was added. Your installed Qwen model is `qwen3.5:9b` through Ollama. Keep Ninja's server/worker running for advice, generation, downloads and folder monitoring. Queue state and output projects survive restart.

Idea generation uses your existing ComfyUI adapters, installed local Windows narration voices and the standalone ClipX caption tool. ComfyUI was started and verified during this update. Start it again after restarting Windows if using original generated visuals:

```powershell
Set-Location -LiteralPath 'C:\path\to\Ninja-Assistant'
powershell -ExecutionPolicy Bypass -File .\scripts\start-video-service.ps1 -Service ComfyUI
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

Preflight displays missing voice, caption-tool or generation dependencies. Use supplied visuals to avoid ComfyUI image generation. Finished-video uploads never invoke editing, captions or rendering. Runtime depends on GPU, footage and model/cache; no fixed completion promise. Public search may be unavailable; add accessible research source links in advanced setup and retry.

## Validation for this update

109 backend tests, 8 frontend tests and a production build passed. Isolated browser checks covered prompt modes, footage selection, research-to-prompt handoff, saved daily tasks, named profile creation/activation/editing, keyboard modal navigation and a 390px screen. Existing tests cover six independent channels and immutable publishing targets.

Real local Qwen advice, a ready idea plan and two evidence-backed content suggestions were verified. A real original Moon-phases video rendered to a playable 34.6-second captioned MP4 using local narration, ComfyUI and retrieved NASA/Wikipedia sources. No public upload was made by these tests. UI planner/research responses were replayed from those real results to keep browser tests deterministic.

Screenshots and run reports are under data/development/assistant-*.png and assistant-*.json. Existing third-party deprecation warnings and the roughly 547KB frontend bundle warning remain.
