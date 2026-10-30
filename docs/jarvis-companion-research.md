# JARVIS companion: cached research and decisions

Researched 2026-10-13 (Asia/Kolkata). Scope: natural local conversation, lower voice latency, bounded tool use and image requests. Reuse Ninja's existing runtime; no upstream source copied, additional framework installed, paid fallback enabled or model weights downloaded.

## Decisions applied

| Need | Source evidence | Ninja decision |
| --- | --- | --- |
| Faster ordinary replies | Ollama supports streamed chat, native tool calls and disabling supported model thinking. [Streaming](https://docs.ollama.com/capabilities/streaming), [tool calling](https://docs.ollama.com/capabilities/tool-calling), [thinking](https://docs.ollama.com/capabilities/thinking), [chat API](https://docs.ollama.com/api/chat) | General companion questions finish after one answer. Stream provisional text with think:false; validate complete tool arguments before dispatch. Retain actual usage and first-text/model timings. A requested action still needs a receipt. |
| Follow-up conversation | The chat API accepts message history. [Ollama chat API](https://docs.ollama.com/api/chat) | Reuse task revisions and bounded conversation history with scoped memory. Prefer short natural Hinglish replies, without claiming human feelings or perfect recall. |
| Lower transcription startup cost | faster-whisper supports CPU INT8; its segment generator starts inference when consumed. [Official source and documentation](https://github.com/SYSTRAN/faster-whisper) | Keep a bounded pipe-only process around the existing ClipX transcription entry point and cached model. Reuse caption-tool code; do not build another caption generator. Warm reuse is not live streaming audio recognition. |
| Predictable voice turns | Speech detection, end-of-turn and interruptions are separate concerns. [LiveKit turn handling](https://docs.livekit.io/agents/logic/turns/), [Pipecat speech input](https://docs.pipecat.ai/pipecat/learn/speech-input) | Explicit push-to-talk conversation removes separate Send and Read clicks. Keep uncertain speech for review, fence late results and interrupt playback when a new utterance starts. Do not enable uncalibrated always-open microphone/VAD. |
| Spoken image requests | ComfyUI exposes prompt, queue, history and view routes. [Official server routes](https://docs.comfy.org/development/comfyui-server/comms_routes) | Add a typed tool around the existing fixed local image workflow, durable job key and worker. Return queued status promptly; expose only verified authenticated outputs. No arbitrary graphs, custom-node installation or cloud switching. |

## Voice options considered, not installed

| Option | License evidence and fit |
| --- | --- |
| Pipecat | [BSD-2-Clause](https://raw.githubusercontent.com/pipecat-ai/pipecat/main/LICENSE). Useful turn-taking patterns; a second orchestration runtime is unnecessary for this slice. |
| LiveKit Agents | [Apache-2.0](https://raw.githubusercontent.com/livekit/agents/main/LICENSE). Useful interruption/turn models; defer its realtime stack until full duplex or remote clients demonstrate a need. |
| OpenVoiceOS | [Project and Apache-2.0 core](https://github.com/OpenVoiceOS/ovos-core). A broader assistant stack, not a replacement for Ninja's existing tools and worker. |
| Kokoro | [Code license: Apache-2.0](https://raw.githubusercontent.com/hexgrad/kokoro/main/LICENSE); [model card](https://huggingface.co/hexgrad/Kokoro-82M) and [voice evidence](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md). Potential later local neural TTS. Hindi voices have limited training evidence and need physical Hinglish pronunciation/latency tests before choosing one. |
| Piper | [GPL-3.0 project](https://github.com/OHF-Voice/piper1-gpl). Voice models have separate license terms; inspect the exact selected voice before distributing or installing it. |

These targeted license checks are not a supply-chain audit and do not transfer permission for third-party voices, footage or assets. Windows SAPI remains the current local speech output. The installed David/Zira voices can sound robotic and mispronounce Hindi; neural TTS is still a separate measured upgrade.

## Measurements and remaining checks

The existing ordinary CMS question took 6.718 seconds and two model calls in the isolated baseline. The extra recovery pass is removed for ordinary companion conversation. Updated first-text and total measurements belong in the validation report; model loading and GPU contention prevent a fixed response-time promise.

A generated five-second English speech sample transcribed locally in approximately 0.750 seconds cold and 0.484–0.516 seconds warm; browser-style WebM measured approximately 0.468 seconds. The previous fresh CLI recognition alone took approximately 1.016 seconds. These are specific synthetic samples and different measured stages, not a universal speedup or a physical Hinglish test.

Physical microphone, background noise, code switching, names/numbers, echo and installed voice pronunciation need calibration. Push-to-talk intentionally supplies the end-of-turn signal. No wake word, continuous listening, full duplex, arbitrary desktop control or perfect lifetime memory is claimed.

Agent-Reach instructions were used, but its CLI was unavailable; official browsing/source inspection supplied the research. This cache avoids repeating platform scans. Installed development skills are not automatically executable Ninja tools.

Use [the Jarvis guide](jarvis-guide.md) for controls and [the validation report](jarvis-validation.md) for verified behavior, screenshots and release status.


## Superseding voice repair — 2026-10-14

The user's physical-use feedback invalidated the earlier decision to keep manual PTT and SAPI as the main experience. The current implementation uses one-click half-duplex automatic turn-taking, local Kokoro ONNX 0.6.1 neural speech (CPU), fixed v1.0 model/voices and Whisper small recognition through the existing ClipX adapter. Sentence-by-sentence playback reduces time before audio starts. No additional automation platform or cloud speech service was installed.

Primary implementation/source checks: [kokoro-onnx source](https://github.com/thewh1teagle/kokoro-onnx), [Kokoro voice evidence](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md), [faster-whisper](https://github.com/SYSTRAN/faster-whisper). The voice card describes limited Hindi training and weaker non-English support; neural voice does not imply perfect Hinglish pronunciation. The selected runtime bundles Windows eSpeak NG for phonemization. Its model loads through ONNX and voices through NumPy without pickle loading. Runtime requests are bounded pipe messages and use only fixed local model/output paths.

See [current measured validation](voice-ease-validation.md), [setup/usage](jarvis-guide.md) and THIRD_PARTY_NOTICES.md. Installed models and packages are isolated under data/services/jarvis-voice; all normal speech requests run offline.
