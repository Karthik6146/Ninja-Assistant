# JARVIS Companion and Voice Upgrade Implementation Plan

> For agentic workers: REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans where installed. These execution subskills are unavailable here; implement natively in the isolated worktree with independent review, as previously selected. Steps use checkbox (- [x]) syntax.

Goal: Make Jarvis converse naturally in Hinglish, answer general questions promptly, execute available routine tools, and accept spoken turns without separate Send and Read clicks in an explicitly enabled voice conversation.

Architecture: Reuse the bounded Qwen agent, SQLite task/history, permission checks, CPU ClipX transcription, SAPI and existing ComfyUI job queue. Stream provisional answer text, keep speech recognition warm, retain follow-up context, and expose image artifacts through authenticated existing routes. Do not install another automation or voice platform.

Tech stack: Existing React/TypeScript, FastAPI/Pydantic, SQLite, Ollama qwen3.5:9b, ClipX/faster-whisper CPU INT8, Windows speech, ComfyUI.

Spec: docs/jarvis-spec.md plus the user's 2026-10-13 companion request and preferred Hinglish.

## Constraints and review focus

- Preserve existing projects, accounts, queued work, publishing policies, user edits and configuration. Canonical source fingerprints live in data/development/companion-source-manifest.json.
- Develop only in data/development/companion-worktree on feature/jarvis-companion. Announce a backed-up rollout after validation.
- No unrestricted shell or model-controlled permissions, secrets, credentials, executable templates or paid cloud fallback.
- Private conversation stays unsaved and tool-free.
- Voice conversation is explicitly started and clearly indicated; hidden/unmounted pages release the microphone. Push-to-talk and review mode remain available.
- Keep transcript confidence/errors visible. Silence must not create an action. Starting a fresh turn fences older transcription and speech.
- Stop speaking and cancel task are distinct. Already completed effects retain their receipts; later task edits cannot rewrite them.
- Streamed prose is provisional; tool arguments must be complete and validated before execution. Native usage counts and cancellation are retained.
- Use only installed local models/presets. Report missing image/voice dependencies before promising output.
- Do not claim a person, perfect memory, guaranteed latency, or successful action without evidence. Ordinary factual replies need no failed-action banner.
- Measure cold/warm transcription and Qwen first text/total timings; physical microphone, noise and Hinglish need user calibration.

## Task 1: Conversational replies, context and streaming

Files: backend/ninja/agent_models.py, agent.py, adapters.py; tests/test_agent.py and focused streaming tests.

Interfaces:
- Request gains response_mode (assistant/companion) and language (auto/en/hi/hinglish); older clients retain assistant behavior.
- Instruction may override response_mode/language without changing existing scope/account bindings.
- AgentTurn gains timing data. adapters.agent_turn accepts optional on_text and max_tokens; defaults preserve old callers.
- Companion turns expose provisional preview text and measured timings in existing GET tasks; follow-ups use existing revision endpoint and history.
- A direct factual companion question finishes after one native Qwen answer. Explicit supported action requests retain bounded recovery and verified/failed receipts.

Steps:
- [x] Add meaningful regressions for general question, requested action recovery, two-turn context, stale stream cancellation and incomplete tool calls.
- [x] Stream bounded Ollama NDJSON with think:false; accumulate content/tool calls, retain final usage and timings.
- [x] Update companion system instructions and guarded preview persistence; preserve model-lock, lease and revision fences.
- [x] Run focused backend checks and real local general-question/follow-up benchmarks.

## Task 2: Faster local speech recognition

Files: backend/ninja/voice.py, existing assistant voice routes, minimal scripts helper if necessary; tests/test_voice.py.

Interfaces:
- Existing voice transcribe endpoint keeps text/language/duration/uncertain; adds measured timing and warm/cold indicator.
- Reuse the standalone caption tool's installed engine and model; keep a bounded persistent process instead of importing/loading for every utterance.
- Worker/helper communication uses validated exact temporary audio paths and bounded local-only requests; output logs contain no transcripts.
- Model/config changes restart only the owned helper; process shutdown and concurrent requests are fenced.

Steps:
- [x] Inspect standalone caption code and reuse its transcription entry point; do not rebuild caption generation.
- [x] Prove cold/warm reuse, size limits, timeout/recovery, silence and configuration changes with tests.
- [x] Measure synthetic English cold/warm reuse with the existing beam-size-5 decoder. Physical Hinglish calibration remains pending.
- [x] Keep missing ClipX/model errors actionable; no implicit downloads.

## Task 3: Voice companion interface

Files: frontend/src/VoiceControls.tsx, AssistantConsole.tsx, assistant.css; frontend tests.

Interfaces:
- VoiceControls gains optional onUtterance(text), replyKey, thinking and onInterrupt callbacks. PrivateConversation uses unchanged review behavior.
- Conversation mode automatically submits an accepted transcript and reads each new completed reply once; follow-up stays in the selected conversation.
- Use explicit Talk/Push-to-talk controls with active microphone state. A new utterance interrupts audio; End voice conversation stops acquisition, upload/playback and auto-send.
- Silence-based end-of-turn remains deferred pending physical microphone calibration; uncertain speech stays in review.
- AssistantConsole shows conversation turns, provisional text, timings and expandable tool outcomes. New conversation is explicit; queued work/progress stays visible.

Steps:
- [x] Add lifecycle checks for auto-send once, no duplicate playback, uncertain transcript, permission race, late reply, hidden page and context switching.
- [x] Implement Hinglish preference, short voice replies, auto-submit/read and clear conversational progress.
- [x] Verify actual Chromium at wide/narrow widths and keyboard focus with mocked speech/media plus real Qwen.
- [x] Preserve private clearing, existing drafts, channel bindings and follow-up revision controls.

## Task 4: Spoken image requests and release

Files: backend/ninja/assistant_tools.py, permissions.py, agent.py; frontend artifact UI; tests/test_agent_tools.py; docs/jarvis-guide.md and validation.

Interfaces:
- image.generate uses typed prompt/dimensions and existing video_generation.Generate/health/enqueue, with immutable task ownership and durable request key.
- Queue heavy generation; do not block the assistant control lane. Return queue receipt immediately; subsequent polling resolves authenticated image output/status.
- Cancel stops pending owned image work; retry reconciles existing successful prompt/output. No arbitrary ComfyUI workflow input.
- Existing /video/generation artifact routes are reused where available.

Steps:
- [x] Prove missing dependencies, replay-safe enqueue, task cancellation, ready image preview and artifact path containment with mocks.
- [x] Execute a real local image only if installed ComfyUI dependencies are ready; otherwise demonstrate the actionable error.
- [x] Cache official research, licenses and measured latency; run appropriate full backend/frontend checks and independent review.
- [x] Produce reviewable diff and before/after screenshots.
- [x] Back up/apply guarded source changes and restart only when existing work is idle and live rollout is authorized.
- [x] Inspect existing source fingerprints and SQLite integrity; document remaining limitations.
- [x] Verify live accounts/history after the authorized rollout.

Research: Native Ollama streaming/tool-calling and turn-taking patterns from Pipecat/LiveKit; details and primary-source links will be cached in docs/jarvis-companion-research.md. No upstream code reuse planned.


Rollout status: installed 2026-10-14 after explicit user authorization. The database and changed files were backed up, the idle live assistant was restarted once, and all eight protected account/configuration files and nineteen checked data tables were preserved. Live browser and authenticated service checks passed. The isolated preview is now stopped.
