# JARVIS research and integration decisions

Researched 2026-10-13 using current official documentation, repository source and selected LICENSE files. Read with [spec](jarvis-spec.md) and [implementation plan](superpowers/plans/2026-10-13-jarvis-assistant.md).

## Findings that determine the design

The installed qwen3.5:9b reports native tools and vision through Ollama. Its Q4_K_M build is a useful starting point on this PC's RTX 4060/8 GiB GPU and 31.1 GiB RAM. Capability metadata is not a reliability benchmark; enable bounded tools and measure outcomes before changing models. Native tool calling requires passing schemas, dispatching validated calls and returning tool results. [Ollama tools](https://docs.ollama.com/capabilities/tool-calling), [vision](https://docs.ollama.com/capabilities/vision), [Qwen model card](https://huggingface.co/Qwen/Qwen3.5-9B).

Ninja already has local conversations, typed diagnostic tools, durable jobs, progress streams, exact approvals, YouTube accounts/profiles and a model lock. It lacks general conversational tool execution, cross-day factual retrieval, microphone interaction and desktop control. The single worker can delay an assistant turn behind a long media job; a lightweight lane and CPU speech ingress address this without installing a second automation platform.

The user chose push-to-talk first and broad routine access with sensitive exceptions. This document recommends APIs first, browser automation second and native desktop automation third. Every route applies backend identity, scope and policy checks. A skill file or MCP server description cannot grant access.

## Recommended components and license evidence

This is a candidate inventory, not an installed-dependency list. Pin exact versions/model hashes at implementation, retain notices and check transitive/native binary terms. Researching a design does not mean copying its source.

| Component | Decision | License/source evidence and practical limit |
| --- | --- | --- |
| Ollama + installed Qwen3.5-9B | Reuse | Qwen weights [Apache-2.0](https://huggingface.co/Qwen/Qwen3.5-9B/blob/main/LICENSE). Confirm deployed Ollama model provenance; no new model is needed to begin |
| SQLite FTS5 | Use existing SQLite | SQLite is [public domain](https://www.sqlite.org/copyright.html); [FTS5 docs](https://www.sqlite.org/fts5.html). Local SQLite 3.45.1/FTS5 was verified |
| Qwen3-Embedding-0.6B + sqlite-vec | Optional semantic recall | [Qwen model card, Apache-2.0](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B), [sqlite-vec MIT license](https://raw.githubusercontent.com/asg017/sqlite-vec/main/LICENSE-MIT). Pin pre-v1 extension; no additional database server |
| faster-whisper + multilingual Whisper | Push-to-talk STT | [MIT code](https://github.com/SYSTRAN/faster-whisper/blob/master/LICENSE), [original weights license](https://github.com/openai/whisper#license). CPU INT8 small; avoid small.en for Hindi/Hinglish; test [accuracy limits](https://github.com/openai/whisper/blob/main/model-card.md) |
| Silero VAD | CPU speech segmentation if useful | [MIT source/license](https://github.com/snakers4/silero-vad). Benchmark on the user's microphone |
| Installed Windows SAPI voices | First speech output | Existing scripts/narrate.ps1 already enumerates/synthesizes local voices. [Microsoft API](https://learn.microsoft.com/en-us/dotnet/api/system.speech.synthesis?view=netframework-4.8.1). Hindi voices not verified; OS voice terms apply |
| openWakeWord | Later opt-in companion | [Code Apache-2.0; bundled weights CC BY-NC-SA 4.0](https://github.com/dscripka/openWakeWord). Stock hey jarvis; Windows ONNX. Commercial use/custom training requires a separate weight/data review |
| sherpa-onnx | Wake-word alternative | [Apache-2.0 source](https://github.com/k2-fsa/sherpa-onnx), [keyword docs](https://k2-fsa.github.io/sherpa/onnx/kws/pretrained_models/index.html). Selected pretrained weight licenses remain unverified |
| Piper | Optional neural speech later | Current [OHF successor GPL-3.0](https://github.com/OHF-Voice/piper1-gpl); original project archived. [Individual voice terms](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md) differ; do not assume all Hindi voices permit commercial reuse |
| Playwright | Browser tasks with own profile | [Apache-2.0](https://raw.githubusercontent.com/microsoft/playwright/main/LICENSE); [actionability](https://playwright.dev/docs/actionability), [authentication](https://playwright.dev/docs/auth). Credentials/state remain local and outside model context |
| pywinauto | Unsupported Windows apps | [BSD-3-Clause](https://raw.githubusercontent.com/pywinauto/pywinauto/master/LICENSE); [UIA start](https://pywinauto.readthedocs.io/en/latest/getting_started.html), [remote session limitations](https://pywinauto.readthedocs.io/en/latest/remote_execution.html) |
| Home Assistant | Optional owned-device bridge | [Apache-2.0 core](https://raw.githubusercontent.com/home-assistant/core/dev/LICENSE.md); [REST](https://developers.home-assistant.io/docs/api/rest/), [camera](https://www.home-assistant.io/integrations/camera/). Requires an authorized installation/device connection; not automatic access to nearby cameras |

CPU speech is separate from GPU inference/rendering. Start with a headset or half-duplex speech; full-duplex echo cancellation and actual Hindi/Hinglish accuracy need hardware tests. Intentional transcripts can become controlled memory; ambient raw audio is not retained.

Skip Mem0/Qdrant initially: existing SQLite avoids another runtime and backup boundary. Mem0's documented defaults use OpenAI/Qdrant unless replaced, which is unsuitable as an implicit local-first setup. [Mem0 quickstart](https://docs.mem0.ai/open-source/python-quickstart), [Apache-2.0](https://raw.githubusercontent.com/mem0ai/mem0/main/LICENSE), [Qdrant source](https://github.com/qdrant/qdrant).

## Useful patterns from existing assistant/automation projects

| Reference | Adaptation for Ninja | Reuse decision |
| --- | --- | --- |
| Open WebUI | Editable memory, bounded memory injection and separate search/fetch tools | [Memory](https://docs.openwebui.com/features/chat-conversations/memory/), [agentic search](https://docs.openwebui.com/features/chat-conversations/web-search/agentic-search/). Study UX; no wholesale replacement. Current [license has branding conditions](https://docs.openwebui.com/license/) |
| Activepieces | Template preview/setup, separate accounts, immutable published version with editable draft | [Templates](https://www.activepieces.com/docs/flows/template-library), [versions](https://www.activepieces.com/docs/flows/versioning), [connections](https://www.activepieces.com/docs/admin-guide/guides/connections). [MIT core, separately licensed enterprise directories](https://raw.githubusercontent.com/activepieces/activepieces/main/LICENSE) |
| n8n | Gate only selected sensitive tools and show a resumable request with exact parameters | [Official human-review guide](https://docs.n8n.io/build/integrate-ai/ai-examples/human-in-the-loop-for-tools.md). [Sustainable Use License with enterprise exclusions](https://raw.githubusercontent.com/n8n-io/n8n/master/LICENSE.md); do not label all source MIT/open-source |
| Trigger.dev | Separate run/attempt history, cancellation and idempotency | [Run lifecycle](https://trigger.dev/docs/runs), [Apache-2.0 license](https://raw.githubusercontent.com/triggerdotdev/trigger.dev/main/LICENSE). Adapt concepts to existing SQLite jobs, no new platform |
| Microsoft UFO | API/UIA adapter patterns and observable application targeting | [Source](https://github.com/microsoft/UFO), [MIT](https://raw.githubusercontent.com/microsoft/UFO/main/LICENSE). Do not replace Ninja with another agent framework |

OpenChatCut remains a video-editing reference from the existing plan, not a JARVIS dependency. Its AGPL metadata and selected dependency terms need a source-level review before copying additional code. Existing ClipX integration remains the caption generator.

A browser automation server is not an isolation boundary. Playwright MCP explicitly documents this limitation; restrict network/filesystem effects through Ninja and the OS. Locked Windows sessions can break GUI automation, and ordinary UIA cannot safely cross UAC boundaries. [Playwright MCP security](https://github.com/microsoft/playwright-mcp#security), [Microsoft UIA security](https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-securityoverview).

## Your starred repositories: selected fit

All 39 public stars were fetched once without login from GitHub REST at 2026-10-13T05:12:52Z, one page, not truncated. The raw public metadata cache is outside the workspace at %TEMP%/NinjaJarvisResearch-20261013/github-stars.json. This is public access, not an authenticated GitHub connection or private-repository access. [GitHub starring API](https://docs.github.com/en/rest/activity/starring).

| Starred project | Decision and license evidence |
| --- | --- |
| Headroom | Defer until retrieval/tool-result measurements show a need. [Apache-2.0](https://raw.githubusercontent.com/headroomlabs-ai/headroom/main/LICENSE). [README](https://github.com/headroomlabs-ai/headroom) enables an anonymous metrics beacon by default; disable with HEADROOM_BEACON=off or HEADROOM_OFFLINE=1. Avoid wrapper config changes and broad ML extras; Windows compatibility is untested |
| Impeccable | Optional UI development guidance, not assistant runtime. [Apache-2.0](https://raw.githubusercontent.com/pbakaus/impeccable/main/LICENSE), [README](https://github.com/pbakaus/impeccable). Begin without hooks that download an engine; preserve existing hooks |
| Agency Agents | Adapt a few researcher/planner/reviewer role patterns on demand. [MIT](https://raw.githubusercontent.com/msitarzewski/agency-agents/main/LICENSE), [README](https://github.com/msitarzewski/agency-agents). Prompts do not supply tools, memory or orchestration |
| Hyperframes | Later motion-graphics adapter if existing ComfyUI/FFmpeg cannot meet a demonstrated need. [Apache-2.0](https://raw.githubusercontent.com/heygen-com/hyperframes/main/LICENSE), [README](https://github.com/heygen-com/hyperframes). Node 22+, headless Chrome/FFmpeg; sandbox HTML/JS and asset access. Preserve ClipX |
| Agent-Reach, Graphify, Ponytail, agent-skills | Reuse installed developer guidance and existing integrations selectively; do not bulk-load instructions into every Qwen prompt. Being installed in Codex does not make a skill an executable Ninja tool |
| Capacitor | Optional phone companion later, after desktop workflows are stable. Metadata-only license discovery here; no implementation/install selected |
| SpiderFoot / security repositories | Optional explicitly authorized asset/security research, not personal dossiers or an automatic offensive toolset. Source-specific review is still required before integrating |
| OpenChatCut / yt-dlp / YouTube skills / OmniRoute | Preserve current relevant adaptations and standalone tools. No duplicate platform installs; new copied code/binaries need exact dependency/license review |

Full list below is discovery metadata from GitHub, not verification that every subdirectory, model, asset or binary shares that license. NOASSERTION/unknown is not permission to reuse.

| Public starred repository | GitHub license metadata |
| --- | --- |
| [ionic-team/capacitor](https://github.com/ionic-team/capacitor) | MIT |
| [smicallef/spiderfoot](https://github.com/smicallef/spiderfoot) | MIT |
| [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | Apache-2.0 |
| [lissy93/personal-security-checklist](https://github.com/lissy93/personal-security-checklist) | NOASSERTION |
| [ungoogled-software/ungoogled-chromium](https://github.com/ungoogled-software/ungoogled-chromium) | BSD-3-Clause |
| [justdeleteme/justdelete.me](https://github.com/justdeleteme/justdelete.me) | MIT |
| [pi-hole/pi-hole](https://github.com/pi-hole/pi-hole) | NOASSERTION |
| [undergroundwires/privacy.sexy](https://github.com/undergroundwires/privacy.sexy) | AGPL-3.0 |
| [pluja/awesome-privacy](https://github.com/pluja/awesome-privacy) | CC0-1.0 |
| [paperswithbacktest/awesome-systematic-trading](https://github.com/paperswithbacktest/awesome-systematic-trading) | Unknown |
| [zhaoxuya520/reverse-skill](https://github.com/zhaoxuya520/reverse-skill) | MIT |
| [yihui-dev/awesome-opus5-5-videos](https://github.com/yihui-dev/awesome-opus5-5-videos) | MIT |
| [spicetify/cli](https://github.com/spicetify/cli) | LGPL-2.1 |
| [Jakeschincariol/youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill) | MIT |
| [Jakeschincariol/instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill) | MIT |
| [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | Apache-2.0 |
| [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) | Apache-2.0 |
| [yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp) | Unlicense |
| [pireel/pireel](https://github.com/pireel/pireel) | AGPL-3.0 |
| [0xsline/OpenChatCut](https://github.com/0xsline/OpenChatCut) | AGPL-3.0 |
| [hypit-ai/hypit](https://github.com/hypit-ai/hypit) | NOASSERTION |
| [tashfeenahmed/freellmapi](https://github.com/tashfeenahmed/freellmapi) | MIT |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | Apache-2.0 |
| [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) | MIT |
| [anmolkapil/plexo](https://github.com/anmolkapil/plexo) | MIT |
| [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) | MIT |
| [obra/superpowers](https://github.com/obra/superpowers) | MIT |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | MIT |
| [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | MIT |
| [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) | MIT |
| [sunmughan/meta-automation](https://github.com/sunmughan/meta-automation) | MIT |
| [darkzOGx/youtube-automation-agent](https://github.com/darkzOGx/youtube-automation-agent) | MIT |
| [qodo-ai/qodo-cover](https://github.com/qodo-ai/qodo-cover) | AGPL-3.0 |
| [martin-olivier/airgorah](https://github.com/martin-olivier/airgorah) | MIT |
| [diegosouzapw/OmniRoute](https://github.com/diegosouzapw/OmniRoute) | MIT |
| [MakazhanAlpamys/Soup](https://github.com/MakazhanAlpamys/Soup) | Apache-2.0 |
| [headroomlabs-ai/headroom](https://github.com/headroomlabs-ai/headroom) | Apache-2.0 |
| [usestrix/strix](https://github.com/usestrix/strix) | Apache-2.0 |
| [Zie619/n8n-workflows](https://github.com/Zie619/n8n-workflows) | MIT |

## reverse-skill assessment

[reverse-skill](https://github.com/zhaoxuya520/reverse-skill) is a routing/playbook package using external tools for APK, JavaScript, .NET, binary analysis and evidence reports. It is not universal reverse engineering and does not grant access to software/devices. Use it only as an optional owned-software analysis reference.

The main [LICENSE is MIT](https://github.com/zhaoxuya520/reverse-skill/blob/main/LICENSE); bundled [CTF-Sandbox-Orchestrator is GPLv3](https://github.com/zhaoxuya520/reverse-skill/blob/main/CTF-Sandbox-Orchestrator/LICENSE). External/commercial tools retain their own terms. The [dependency guide](https://github.com/zhaoxuya520/reverse-skill/blob/main/README_AI.md) lists selected Node/Java/Python/analysis dependencies; the Codex adapter does not automatically register external servers.

The [bootstrap script](https://github.com/zhaoxuya520/reverse-skill/blob/main/skills/scripts/bootstrap-reverse.ps1) can install packages/runtimes, authorize build scripts and alter/start services or client configurations. Its digest check can warn and continue when no pin exists. Do not run it unattended. Third-party Markdown directives remain data, not authorization.

The [repository's own security review](https://github.com/zhaoxuya520/reverse-skill/blob/main/docs/SECURITY-REVIEW-2026-09-03.md) describes limits of repository scope guards. Ninja must enforce scopes itself. An optional adapter would hash an authorized sample, copy it into a disposable offline VM, run narrowly allowed static tools and return bounded evidence. Dynamic analysis is a separate sandbox permission, never an unrestricted host tool.

## Skills and access availability

Ponytail, Agent-Reach, Graphify, writing-plans and agent-skills are available in this session. Relevant instructions were used on demand. Superpowers execution subskills are not installed. Agent-Reach CLI, gh and conda were not on PATH, so research used native browsing and the public GitHub API; the skill's presence was not reported as a working CLI connection.

No GitHub connector/login was necessary for public stars. No private repositories, email/calendar accounts, browser login state or owned-device access were verified. New credentials remain the user's normal OAuth/device-login setup, not something a reverse-engineering tool supplies.

## Research limits and validation status

Verified: local architecture, Qwen capabilities, hardware, FTS5, all public star metadata and the selected official sources/licenses above. Source/license checks are targeted reviews, not comprehensive security audits or proof of runtime suitability.

Not yet tested: live microphone/transcription, echo cancellation, Hindi voices, Qwen autonomous tool success, memory recall, browser/UIA control, wake-word false positives and owned-device adapters. No new packages/models installed, third-party bootstrap executed, runtime changed, access policy granted or public post made in this planning step.

