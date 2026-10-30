# Voice conversation repair — 14 October 2026

1. Replace multi-button voice turns with one Talk to Jarvis session: speech detection, automatic submission, spoken response, resume listening. Pause capture during playback; retain keyboard/manual fallback in settings.
2. Replace tiny automatic multilingual recognition with an installed multilingual small CPU model, reused through the existing standalone caption adapter. Reject script drift/repetition, judge utterance confidence instead of one word. Preserve caption generation externally.
3. Install a bounded persistent local Kokoro ONNX neural voice, default male Hindi/English; use native Hindi script for Hinglish speech. Keep dependencies isolated from Ninja and caption tool.
4. Migrate obsolete console mode/default settings without deleting history or drafts. Exclude old internal correction prompts from companion context.
5. Verify noise/silence, short mixed-language samples, voice lifecycle, real Qwen, narrow UI and existing tools. Back up and install guarded changes; report measured timings and physical microphone limits.

Scope: VoiceControls/AssistantConsole and callers, assistant request model/routes, agent history, voice.py/resident adapters, new neural speech helper/setup, focused tests, guides/licenses. No account/data deletion, cloud speech service, voice cloning, new automation framework or unrestricted shell tool.
