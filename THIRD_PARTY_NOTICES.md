# Third-party acknowledgments

YouTube workflows reference darkzOGx/youtube-automation-agent (AgentTube), https://github.com/darkzOGx/youtube-automation-agent, commit e26792ae00dc1ec2434faf32632896609396dfad. Ninja uses independently written Python/React integration rather than importing the Node agent runtime. The upstream notice is reproduced for attribution.

MIT License

Copyright (c) 2025 YouTube Automation Agent Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Local neural conversation voice (2026-10-14)

Optional isolated runtime: kokoro-onnx 0.6.1 (MIT), ONNX Runtime (MIT), Kokoro-82M v1.0 model/voices (Apache-2.0), phonemizer (GPL-3.0), bundled eSpeak NG (GPL-3.0). The setup installs upstream packages; no upstream source is copied into Ninja. Preserve the installed package licenses and model notices if redistributing. Kokoro Hindi voices hm_omega / hf_alpha have limited training coverage; pronunciation is not guaranteed.

Speech recognition continues through the existing standalone caption tool and faster-whisper (MIT), with Systran/faster-whisper-small weights converted from OpenAI Whisper (MIT). Captions remain the standalone tool's responsibility.

Primary sources: https://github.com/thewh1teagle/kokoro-onnx ; https://huggingface.co/hexgrad/Kokoro-82M ; https://github.com/bootphon/phonemizer ; https://github.com/espeak-ng/espeak-ng ; https://github.com/SYSTRAN/faster-whisper ; https://huggingface.co/Systran/faster-whisper-small . Exact downloaded URLs, lengths and locally recorded SHA-256 hashes are in docs/voice-model-sources.json. These hashes record the installation; they are not a claim of an independent upstream signature.


Live listener models (downloaded by scripts/setup-local-voice.py into data/services/jarvis-voice/models/listener; nothing is copied into Ninja's source):
- Silero VAD v6 ONNX as shipped with faster-whisper v1.2.1 (MIT): https://github.com/SYSTRAN/faster-whisper , https://github.com/snakers4/silero-vad
- Smart Turn v3.2 CPU model (BSD 2-Clause), Daily/Pipecat: https://github.com/pipecat-ai/smart-turn , https://huggingface.co/pipecat-ai/smart-turn-v3
- openWakeWord v0.5.1 melspectrogram, embedding and hey_jarvis_v0.1 models: code Apache-2.0, pre-trained models CC BY-NC-SA 4.0 (non-commercial use only): https://github.com/dscripka/openWakeWord
Ninja's listener re-implements the inference steps with numpy (openWakeWord streaming pipeline; Whisper log-mel features, whose Slaney mel filterbank is adapted from faster-whisper's MIT-licensed feature extractor, Copyright (c) 2023 SYSTRAN).
