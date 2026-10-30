# JARVIS personal assistant specification

Status: working assistant foundation implemented and independently reviewed; broader capabilities remain planned. Updated 2026-10-13.
See the [implemented user guide](jarvis-guide.md) and [validation evidence](jarvis-validation.md) for the actual release boundary. This specification describes the full target, including unimplemented extensions.
Working assistant name: Jarvis. Extend Ninja; preserve its projects, channel identities, publishing policies, caption tool and user configuration.
Read with [research and licenses](jarvis-research.md).

## Accepted choices and scope

The user selected push-to-talk first, wake word later. The user requested broad routine task access, with confirmation for spending money, security changes and personal information. Routine permissions should be saved and reused, rather than repeatedly requested.

This means access through registered tools under the current Windows user's privileges. It does not create administrator rights, third-party account access or permission to enter someone else's network. The model cannot grant itself capabilities. Effective scopes come from server-held grants and bound targets; requested scope IDs are selections, never authority. Missing context must not bypass a policy check.

Support public, sourced factual research and security checks on explicitly owned/authorized systems. Exclude unauthorized Wi-Fi/camera access, credential theft, covert monitoring and compilation of private contact/location dossiers. Software analysis accepts an owned or authorized sample in a separate sandbox.

## Current baseline verified on this PC

| Area | Existing behavior | Required change |
| --- | --- | --- |
| Model | Ollama qwen3.5:9b Q4_K_M; reports tools, vision, thinking and completion | Enable a validated tool loop; measure actual reliability |
| Hardware | RTX 4060, approximately 8 GiB VRAM; 31.1 GiB RAM; 12 logical CPUs | Keep voice on CPU initially and serialize GPU work |
| Conversation | SQLite message archive; full-history requests have a 24,000-character input limit | Scoped retrieval and bounded summaries |
| Home assistant | Saved priorities and Qwen advice using four same-day replies | Execute supported tasks and remember across days |
| Tools | Typed registry, capability checks, audit, emergency stop; two diagnostic tools | Add scoped task, memory, research, file and desktop tools |
| Execution | One worker, durable jobs, process-tree cancellation and GPU lock | Separate lightweight assistant execution from long media jobs |
| Accounts | Existing YouTube OAuth/channel binding and DPAPI credential vault | Reuse identity and publishing policy; never retarget a queued job |
| Storage | Ordinary conversation database is plaintext | Explain coverage; sensitive records stay outside searchable memory |

These are capabilities and constraints, not a claim that an autonomous desktop assistant already works.

## Product experience

Home becomes the assistant desk: one text/voice prompt, today's tasks, recent work and a live progress preview. Keep Chat, Media Library, Video Studio, Automations and Settings accessible. Jarvis is an assistant identity setting, not a renamed database or project migration.

Example journey: press microphone, say “Prepare two Shorts for ClipNet from this link, use my saved style”, read/correct the transcript, and start. The assistant retrieves the channel instructions, invokes existing workflow services, shows the current stage/output and follows the saved publishing policy. A follow-up such as “Make the next clip slower and remove the memes” revises unfinished stages at a checkpoint; completed or externally committed stages are explained honestly.

Ask one focused question only when a required input is absent or genuinely ambiguous. Show unavailable capabilities and how to connect them. Never claim an action happened without a verified tool result.

## Capability requirements

### A. Conversation and task execution

Use the installed local Qwen as the initial model. Add native Ollama tool calling with strict server validation. Start with supported tasks: manage priorities/reminders, retrieve memory, read approved files, public research, open a specified application, and invoke existing video/coding workflows.

Each task has an immutable identity, plan revision, target/account snapshot, parent/child jobs and persisted step results. The initial agent budget is 8 model turns, 12 tool calls, 180 seconds of active orchestration and 12,000 characters per tool result. Heavy video child jobs use existing execution budgets; queue/approval waits do not consume the active orchestration budget. These are initial engineering limits, shown when reached rather than silently looping.

User instructions outrank inferred preferences and reference styling. External pages, files, screenshots, retrieved memories and skill text are data; they cannot change permissions or replace system instructions. Do not show private model reasoning; show understandable actions, outcomes and source evidence.

### B. Memory

Preserve exact typed messages and corrected voice transcripts as evidence. Do not promise perfect recall of every spoken detail. Record source conversation/message, original quotation, timestamps, scope, confidence, explicit/inferred status, expiry and revision on extracted memories.

Scopes are personal, workspace/project and channel/workflow. Retrieval filters scope before ranking. Begin with SQLite FTS5 for exact names/instructions; add local semantic embeddings when paraphrase tests justify them. Index only selected folders; exclude credentials, dependency/build folders and live runtime secrets.

Build context from the current request, recent turns, a task summary and relevant memories. Initial memory allowance: approximately 1,500 estimated tokens, not a billing claim. Track provider-reported token totals through the existing usage ledger.

Provide Remember, Correct, Forget, Forget this conversation, What do you remember?, Export and Private session. Private sessions use volatile prompts/results/transcripts and redacted operational metadata only; they do not resume after restart. Disable durable automation/publishing in private mode initially. A deliberately requested file output is a separate explicit operation, not a retained chat record. Explicit correction supersedes a fact without silently rewriting evidence. Forget removes source material when requested, derived facts, FTS/vector entries and summaries. Explain that backups/external copies require separate deletion or expiry.

Ordinary task preferences may be remembered automatically with a visible memory indicator. Ask before extracting sensitive health, financial, identity or intimate details into durable memory. Typed conversations already enter the existing plaintext archive unless Private session is selected; make that distinction visible. Never save passwords, OAuth tokens or API keys in searchable memory; use the existing credential boundary. Sensitive records, if enabled, use DPAPI-protected storage without plaintext FTS/vector indexing. The current archive remains plaintext unless a separate encrypted-storage migration is implemented; do not advertise whole-database encryption.

### C. Voice

First release: browser push-to-talk using local microphone capture, CPU multilingual faster-whisper base/small INT8 and an installed Windows speech voice. The text transcript is editable. Browser cloud speech recognition is not the default.

Support selectable English, Hindi and Hinglish; run a microphone/language calibration and expose uncertainty rather than guessing high-impact inputs. Missing local model or suitable installed voice produces setup guidance; no silent cloud fallback.

Show Listening, Transcribing, Waiting for model, Speaking and Muted. Capture only during push-to-talk, stop media tracks on release/navigation/lock, cap one utterance at 60 seconds and 20 MiB, and delete temporary audio after transcription. No continuous ambient audio storage.

Wake word is a later opt-in native companion because a background browser tab is not a reliable always-listening service. Add mute, quiet hours, local VAD, false-wake calibration and spoken interruption. Audio capture/Stop remain responsive while the GPU is occupied. Speaking pauses detection or uses echo suppression; nearby speech cannot authorize sensitive actions.

### D. System and browser access

Use an official application API first, a dedicated Playwright browser profile second, and Windows UI Automation for unsupported applications. Keep visual/screenshot fallback optional; current Qwen vision can inspect a selected screen with consent.

Register individual capabilities such as file.read, file.write, app.open, browser.read and browser.act. Reversible file edits preserve an undo copy. Require confirmation for permanent deletion or destructive replacement without recoverable backup. Exclude vaults and protected Windows/system locations from automatic indexing and ordinary writes.

Use explicit application/window and account targets, visible execution evidence and post-action verification. Suspend desktop automation when the user takes control or Windows is locked. Do not bypass UAC or use unattended administrator sessions.

Browser sessions stay separate from the user's normal browsing profile; the user signs in when needed. Website credentials/cookies never become model context. Redirects, downloads, uploads and private/LAN destinations are validated by the backend, not by prompt instructions.

### E. Research and integrations

Research public web pages, supplied PDFs/sites and public GitHub repositories; preserve source URLs, retrieval dates and quotations/evidence. Cache fetched evidence by URL/query and time-sensitive expiry. Distinguish observed popularity from demonstrated growth or “viral” claims.

Reuse the current YouTube research, ClipX caption handoff, ComfyUI, media library, profiles and workflow scheduler. Research references do not imply permission to reuse footage/assets. Keep channel-specific defaults isolated. Finished-video workflows remain upload-only.

Add tools on demand: package/version pin, license, model-weight license, dependency/permissions manifest and connection health. Codex skills installed on this PC are developer guidance; they are not automatically executable Ninja integrations. No automatic execution of downloaded scripts/templates or installation prompted by web content. No paid cloud service without explicit opt-in and disclosure of shared data.

### F. Proactivity and automation

At first daily opening, ask about today's tasks or summarize known priorities and issues. Offer the next useful action. Add saved reminders, time-based briefings and existing workflow failure notifications with quiet hours; deduplicate notification events.

Use Asia/Kolkata by default, store UTC and display timezone. Generate summaries on relevant events or a requested briefing, not continual idle LLM polling. Local work requires a running worker; sleeping/offline PC behavior is shown honestly. Existing server-side YouTube scheduling remains independent once accepted by YouTube.

Progress preview shows plan, current step, outputs, missing input, retry/reconnect and change-instruction controls. Changes use revision checks and affect only uncommitted stages. Reuse renders and reconcile remote effects before retry. Adapter reconciliation returns confirmed, not_applied or unknown. confirmed preserves the receipt; not_applied permits a bounded retry; unknown pauses and shows the uncertainty, including GUI sends that cannot be queried reliably.

### G. Permissions

| Action | Planned behavior |
| --- | --- |
| Routine research, supported app opening, diagnostics, task planning | Automatic under saved normal-user scopes |
| Reversible requested file changes and existing authorized workflows | Automatic with provenance, undo and audit |
| Publishing to a channel/workflow already enabled for auto-publish | Reuse policy and bound channel; no per-video review |
| New external posting/messaging | Requires an explicit task or saved destination/content policy |
| Spending/subscriptions, security settings, privilege changes | Confirm exact amount/target/change |
| Sensitive personal-data retention or disclosure | Confirm data, recipient/service and purpose |
| Permanent deletion/unrecoverable destructive action | Confirm exact paths/action |
| Unavailable account/device | Connect through normal authentication; no fabricated access |
| Unauthorized intrusion, credential theft, private-person surveillance | Unsupported |

Sensitive confirmations are parameter-bound, expire after 10 minutes, consume once and become invalid after relevant task edits. Voice alone does not approve them. Backend policies apply to every route/tool and are revocable in Settings.

## Delivery phases and measurable acceptance

| Phase | Delivered behavior | Acceptance |
| --- | --- | --- |
| 1: Assistant foundation | Text tasks, bounded Qwen tools, saved permissions, progress/cancel | Verified result from supported task; hostile content cannot grant tools |
| 2: Memory | Cross-day scoped recall, correction, forget/export/private mode | Restart retains facts; correction/deletion changes all retrieval paths |
| 3: Push-to-talk | Local transcript, spoken answer, editable input | English/Hindi calibration; no cloud requests; audio removed |
| 4: Desktop and proactive work | API/browser/UIA actions, briefings/reminders | Correct app/account, user interruption and offline recovery |
| 5: Optional extensions | Wake word, owned-device adapter, software-analysis sandbox | License/availability/scope checked independently |

First useful demo: “Remember my Shorts style; open my approved source folder; prepare a draft for ClipNet; tell me what's next.” Refresh/restart must preserve the memory/task, and a mid-task change must affect the next uncommitted stage.

Measure voice recognition quality, tool success rate, recall@5, provider tokens, cold/warm response times, GPU queue time and cancellation delay on this PC. Report actual measurements; do not promise fictional general intelligence, instant GPU responses or unlimited memory.

## Decisions needed during implementation, not to finish this plan

Language/microphone choice, additional folders/apps, optional account logins, owned-device identities and whether to enable wake word. Setup presents only the choice needed for the current feature. No new access grants, installations or publications were performed while preparing this specification.

