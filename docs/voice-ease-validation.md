# Voice conversation repair validation — 14 October 2026

Implemented in an isolated snapshot/worktree of the installed assistant. Original accounts, project files and configuration are outside the change. Backup/restart deployment is guarded by source hashes, database backup, idle-job checks and preservation hashes.

## Verified

- Frontend production build passes; 17 frontend tests pass.
- Full final backend suite: 193 tests passed, including rejecting unexpected tools in an informational voice turn.
- Seven Chromium journey groups pass with no page errors: one-click recording, automatic silence turn-end, automatic follow-up, migration of old preferences, uncertainty/retry, cancellation during recognition and permission prompts, context-switch cleanup, 390px layout/keyboard, and ordered sentence playback with prefetch. Microphone and browser audio are mocked in this lifecycle suite.
- Real locally installed Kokoro CPU runtime produced Hindi/English WAV audio. Real existing ClipX adapter with Whisper small transcribed it. Real Qwen answered the recognized CMS question and neural speech produced the first spoken sentence.
- Real silence and deterministic low-level noise returned no usable speech and never became a task.
- Browser screenshots are [desktop](screenshots/voice-ease-desktop.png) and [mobile](screenshots/voice-ease-mobile.png). These show a controlled fixture conversation, not a recording of the user.

## Measured limits

The final synthetic 3.75-second Hindi/English question took **6.704 seconds from completed recording to first sentence audio**: recognition was 3.532s on first load and 2.796s warm; first-sentence speech synthesis was 1.063s. This measurement excludes browser/network/worker polling and the approximately 1.1-second pause used to detect the end of speech. Other short neural samples synthesized in 0.5–1.7s warm. First model loading and GPU work can add delay.

Mixed-language recognition still misspelled some terms (including “छोटा” in one sample). The revised informational conversation path answered the CMS question rather than dwelling on that spelling. This is an improvement, not an accuracy guarantee. Native-script Hindi speech sounds more appropriate than reading Roman Hindi as English; Qwen can still choose imperfect wording. The user should judge voice preference with their own speakers/headphones.

Not physically calibrated: the user's microphone, room acoustics, accent, live Hinglish code-switching and perceived voice quality. No wake word or simultaneous listening while Jarvis speaks; Interrupt is explicit. Source/token permissions, confirmations and external publishing behavior remain in the existing bounded tools. No publishing or paid services were tested or used.

The separate review agents were unavailable due to the tool's usage limit. Source review, regression tests, real local model checks and Chromium lifecycle tests were completed directly instead.

## Evidence

Detailed local results and audio samples: `data/development/voice-ease-worktree/data/checks/voice-roundtrip.json`, `neural-benchmark.json`, `voice-browser.json`, `roundtrip-question.wav`, and `roundtrip-reply.wav`. Dependency pins: `scripts/voice-requirements.lock`. Download sources and recorded hashes: `docs/voice-model-sources.json`.

## Rollout status

Installed into the live assistant on 2026-10-14 after explicit authorization. Backup: `data/backups/voice-ease-20261014-005926-153d59`. All 19 preserved database tables and eight protected configuration/account files matched their pre-restart hashes. The five projects, existing channel and workflows remain intact.

Live Chromium checks passed: authenticated Home and neural voice defaults, Qwen/channel settings, all main navigation, unsaved draft restoration, keyboard access and 390px layout; no page or API errors. Live speech endpoints returned valid 24kHz neural audio and recognized “नमस्ते मैं सुन रहा हूँ” with no uncertainty. These checks used generated speech, not the user's physical microphone.

Live screenshots: [Home](screenshots/voice-ease-live-home.png), [mobile](screenshots/voice-ease-live-mobile.png). Rollout and runtime reports remain in `data/development/voice-ease-worktree/data/checks`.
