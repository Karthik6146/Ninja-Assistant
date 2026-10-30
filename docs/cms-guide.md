# Content dashboard

Open Video Studio or Automations after refreshing Ninja. The default view is a content dashboard; the existing wizard and editor remain under **Import files / advanced setup**.

## Start with a brief

1. Select your channel and a saved workflow whose defaults you want. ClipNet retains its automatic publishing policy.
2. Describe the content and paste the source YouTube URL. For example: "Create two 45 second Shorts with calm podcast styling and clear captions. Keep each moment understandable on its own."
3. Add optional references. Choose YouTube reference, website/style, or tool documentation. These links are separate from footage.
4. **Plan with Ninja** uses local Qwen to choose supported clip count, duration, format, captions and preset. The plan names limitations and shows the inherited channel and publishing policy. **Start task** starts processing; **Test locally** cannot publish. No per-video title/description review is added to automatic workflows.

A new channel still needs actual permission, audience and synthetic-content declarations. Those controls are in Adjust task settings. Paid/cloud services are never chosen automatically. Local file import, supplied media, narration, generation and detailed scheduling remain in advanced setup. Opening it from a plan carries your planned settings into the form.

## Manage content

Content has search and status filters. Expand one task to see its current step, output players, generated metadata, reference evidence, Activity / stop and retry. Publishing failures are surfaced as Needs attention. Public status is based on the saved YouTube response, never on render completion. Schedule lists confirmed scheduled uploads and upcoming workflow runs; every time has a timezone. It is a list view, not a drag-and-drop calendar. Automations holds reusable workflows, Run now, Pause and defaults.

Briefs, planned settings and unsent task instructions restore after refresh. Page navigation has short transitions that respect reduced motion. Background job updates no longer scroll the page back to the top.

## Change instructions mid-task

Expand a content card and use **Tell Ninja what to change**. Ninja requests cancellation of the current job, waits for the existing single worker to stop it, and queues a revised task. Qwen translates the latest instruction into supported settings. Channel, credentials, publishing policy, rights and content declarations cannot be changed by the model. Existing clip-source analysis is reused; changed edits and metadata are regenerated. The old run remains in history as Revised.

Once a publishing operation exists, that version is locked. Start a new task for further changes; this feature cannot retract a public upload. Pending changes appear in Activity, and duplicate instruction requests are idempotent. Failed stages can be retried. Old superseded tasks cannot be restarted. Finished-file tasks remain upload-only and transfer only their unpublished reservation to the revised task.

## What references can do

Public HTTPS websites and tool documentation are read as text through Ninja's existing SSRF-protected fetcher. Login-required, redirected or unsupported pages fail clearly; use a directly accessible text page or remove the reference. YouTube reference links use the existing account's read-only API for title/description context. They do not provide visual/audio style analysis. For that, choose an uploaded reference recording in the advanced editor. Reference footage and music are never silently reused. Nothing installs a linked tool or runs instructions found on a page.

Evidence is saved per run and reused on retry/revision. Actual captions still come from the standalone ClipX integration. Supported local edit presets remain education, gaming, podcast and cinematic; unsupported effects and arbitrary templates are reported rather than silently installed.

## Research and verification

The [reviewed YouTube skill](https://github.com/Jakeschincariol/youtube-agent-skill) is MIT-licensed and does not publish. Ninja adapts its concepts of self-contained clip selection, early concrete title wording and useful opening description sentences. No upstream source was copied or skill installed. Title-length notes are advisory, not performance predictions.

Dashboard references: [Buffer content planner](https://buffer.com/features/social-media-content-planner), [OpusClip scheduler](https://www.opus.pro/calendar), [Descript conversational editing](https://www.descript.com/blog/article/underlord-ai-video-editor-primer). Research checked 2026-10-09 and cached in cms-plan.md. Agent-Reach CLI was unavailable; official web sources were used.

Validation: 89 backend tests, 4 frontend tests, TypeScript and production build; isolated Chromium flow covers restored drafts, planning, local test start, sending changes, schedule/automation views, narrow screen, keyboard access and reduced motion. A real Qwen brief produced two 45-second podcast clips in its structured plan. A real local revision rendered one captioned 30-second clip using saved analysis and generated metadata. Zero publishing operations were created by the real local tests; public publishing remains mocked.
