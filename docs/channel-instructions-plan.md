# Channel instructions, metadata defaults and editing references

Status: requirements and implementation plan; not yet implemented or verified.
Extends the delivered [Video Studio usability plan](usability-plan.md).
Modes: A = upload finished files; B = long video to clips; C = idea to video.

## Scope and existing functionality to reuse

Preserve channel/OAuth separation, immutable publication targets, original files, workflow activation, resumable upload ledgers, UTC schedules, saved projects and ClipX. Retain React, FastAPI, SQLite, the existing worker, yt-dlp, safe public retrieval, Ollama, ComfyUI and the current editor/render adapters.

Inspection found:

- Channel records already hold defaults, but the defaults endpoint accepts a whole workflow Definition. Introduce versioned channel settings without changing connection IDs or importing account credentials into defaults.
- GuidedStudio copies defaults only at workflow start. Make inheritance explicit, including when choosing a channel later in the wizard.
- studio.enqueue snapshots a workflow; retain that boundary and include resolved channel-settings revisions.
- studio.prepare_item currently chooses title/description and reads sidecars just before creating an operation. Resolve and freeze those values earlier, show them, and publish exactly the reviewed snapshot.
- video.analyze supports one local reference. video.select applies reference styling only in the custom-edit branch. Both clip and idea plans must consume the reviewed style brief.
- Test runs already cannot prepare publishing operations. Extend that barrier to metadata tests, research and reference analysis.

## 1. Channel Instructions and metadata inheritance

Show a clearly visible **Channel Instructions** area on the selected channel dashboard, with these tabs:

| Tab | Contents |
|---|---|
| Metadata Defaults | General instructions, audience, description, title, tags, hashtags, language, tone, links, calls to action |
| Editing Style | Written brief, saved preset, editable interpretation |
| References & Assets | Separate reference/media/package inputs and research preferences |
| Publishing | Existing account/channel, timezone, cadence, declarations and publishing policy |

Mode A hides Editing Style and editing-template research. Metadata Defaults remains visible in A and B and available in C. Existing editing settings stay stored when the mode changes; hidden settings must not execute in A.

For title and description, distinguish **Fixed text/template** from **Generate from instructions**. Provide optional fixed title prefix/suffix. General audience/tone/language/CTA guidance informs generation but is not silently pasted into the description. Fixed links, CTA text and hashtags appear only where the user chose to include them.

Use this precedence for each field:

    Channel defaults → Workflow overrides → Individual video overrides

An absent override inherits; an explicit empty value clears a field. UI controls must expose Inherit versus Override, rather than treating every empty form input as an override. Lists replace inherited lists when overridden; normalize/deduplicate resolved tags and hashtags while retaining order. Show where each effective value came from. Treat filename/sidecar metadata as per-video inputs; explicit per-video form edits outrank sidecar values.

Support these variables initially:

| Variable | Value |
|---|---|
| {video_title} | Original filename/source title or explicitly entered video title, not the template's own output |
| {topic} | The saved source/topic brief |
| {source_url} | The selected primary source URL |
| {channel_name} | The verified channel display name from the saved channel snapshot |

Validate variable names while saving and again when resolving. Missing required values, unknown variables and malformed braces get field-level errors. Do not permit expression evaluation, attribute/index access, nested substitution, conversions or format specifications. Define literal brace escaping and show it in the UI. User text and researched content remain data.

Render one final title, description, tags and hashtags before publication. Enforce the existing YouTube metadata limits on resolved text; do not silently truncate. Metadata instructions may invoke the configured text model, but Mode A must never invoke transcription, reference-style analysis, captions, effects, editing, ComfyUI or rendering.

Store generated metadata once with its instructions/source revision and reported model usage. Retries reuse that result unless the user explicitly regenerates it. If the configured model is unavailable, offer fixed metadata or Retry; do not silently switch to a paid provider.

## 2. Versioning and already queued videos

Keep channel settings independently keyed by verified channel ID, with revision checks on saves. Workflows store overrides and the channel-settings revision/snapshot reviewed for activation. Pending runs store effective settings; items store their own overrides and resolved metadata/style revisions. The publication approval digest must cover the exact resolved metadata, file, channel and authorized connection.

Changing channel defaults affects new drafts, not existing approved workflows, approved uploads or scheduled videos. Existing workflows show **New channel defaults available**; updating them requires an explicit review and invalidates their previous activation as appropriate.

Offer **Apply updated defaults to selected queued videos**:

1. Select eligible unapproved items and show a before/after metadata/style diff.
2. Preserve explicit workflow/video overrides; offer a separate, clearly labeled reset-to-inherit control.
3. Update with compare-and-swap revision checks and invalidate affected pending reviews/previews.
4. Retain successful source downloads, analysis and renders when only metadata changed.
5. Block items already authorized, uploading, uploaded or scheduled; show why. Do not alter remote schedules through this bulk action.
6. If a worker claims an item while this review is open, reject the stale change rather than racing it. Supersede only unapproved operations through the existing approval/ledger flow; never introduce a new upload as a side effect of changing defaults.

An explicit edit to an already published/scheduled video's remote metadata is outside this bulk-default operation and requires a separate concrete review.

## 3. “How should Ninja edit this?”

Modes B and C, plus the retained Edit my footage flow, offer a plain-language brief with written instructions, multiple reference-video URLs, uploaded reference media/assets, and a saved preset. These inputs may be combined.

Cover pacing, hooks, cut timing, framing, captions, typography, zooms, transitions, memes, music, sound effects, color and mood. Store briefs and references per channel and workflow, with per-video overrides.

**Analyze references** is a separate bounded preparation step. It may inspect transcript/timing, sampled frames and supported audio evidence; it must not render the final video. Show an editable **What Ninja understood** summary before Test/Run:

- Proposed hook, pacing/cut rhythm and framing.
- Caption/typography treatment through ClipX-compatible settings.
- Zoom/transition/color choices.
- Music/sound-effect and meme placement suggestions.
- Evidence/source for inferred choices, uncertainty and unsupported requests.

Explicit user instructions override inferred reference styling. A reviewed user-edited summary overrides the model's earlier interpretation. Mark conflicts clearly; do not let a later inference overwrite a locked explicit choice. Translate the accepted brief into the existing validated edit contract. If the current editor cannot implement a requested effect, report that limitation and offer a supported choice; never claim it was applied.

Apply the accepted brief to clip plans as well as custom/idea plans. A reference is style-only by default and is excluded from the final source/segment list. Reusing its footage/audio requires a separate asset selection and reuse-rights confirmation.

Changing an editing brief after preview increments the edit revision and requires a fresh affected preview. Metadata-only changes do not rerender. Existing ClipX remains the sole caption-generation integration.

## 4. References, assets and optional research

Provide distinct URL/upload fields and record roles:

| Input | Default use | Validation / next step |
|---|---|---|
| Reference video | Style evidence only | Supported public video or managed local recording; unsupported provider → supply a supported URL or upload an authorized copy |
| Meme/media asset | Candidate footage, image or audio | Probe supported type, enforce size/path limits, record attribution/license and require explicit selection/rights before inclusion |
| Template/effect/transition package | Compatibility inspection only | Validate a supported data-only package/schema; executable or unsupported package → explain required editor/dependency, do not install or execute |

Use the existing public-address/redirect checks for external requests. Reject local/private network destinations, credential-bearing URLs, unsafe paths and oversized responses/uploads. Distinguish unsupported, inaccessible, deleted and login-required links. Never import browser cookies or bypass access controls automatically. A web page's text is not proof of analysis of the underlying video.

Research choices:

- Use only my supplied references/assets.
- Find relevant popular editing references.
- Find meme/effect/transition/motion-graphics templates.
- Combine supplied references with researched suggestions.

Match topic, audience, platform and language through available public sources/integrations. If a provider is unavailable or needs configuration, show that condition and retain supplied-only operation. The research action returns suggestions; it does not automatically import footage or install packages.

For every result store source URL, retrieval timestamp, source/provider identity, relevance rationale and observed evidence. Popularity evidence records the metric, value, observation date and source when available. Missing metrics are **unavailable**, not estimated. A large lifetime view count does not establish “currently viral”; that label requires dated trend evidence and its stated time window.

Research editing patterns as well as assets: hook, cut rhythm, caption treatment, framing, audio and meme timing, with traceable examples and caveats.

Each asset/template card includes:

- Preview where available, source URL, creator and attribution text.
- License/usage conditions, license source and verification status.
- Compatible editor/version and required fonts, plugins, models or other dependencies.
- Local availability, compatibility check and installation status.
- Role: style reference versus asset permitted for reuse.

Unknown license or compatibility is explicit and blocks automatic reuse, not saving a style reference. Preserve original attribution/license documents and package hashes in project/export manifests. Do not infer permission from popularity or a public URL.

Initially accept only explicitly supported non-executable preset data mapped to Ninja's existing edit contract. Other editor packages may be researched/catalogued but must fail use/import clearly. No arbitrary JavaScript, plugins, installers, shell commands or executable archive contents. Supported installation, if later needed, must be a separate reviewed action with known provenance and dependencies.

## 5. Persistence, caching and one-video test

Persist settings, overrides, accepted briefs, selected reference IDs, compatibility results and research preferences through navigation, refresh and restart. Store reusable results by query inputs, source IDs/content hashes, provider and analyzer version. Show when research was retrieved; allow explicit Refresh. Invalidate only relevant cached steps when topic/language/reference/instructions change. Never present stale popularity evidence as current.

**Test on one video** uses exactly one chosen input and produces:

- Resolved metadata with field origin and validation.
- Editable, understood style brief for B/C.
- Selected references/assets/templates, evidence, licensing and compatibility.
- A rendered preview for editing modes after the brief is accepted.
- For A, original-file preview plus metadata only; no render.

Test runs cannot queue uploads, change visibility or activate publication policies. Use existing local worker progress/cancellation/retry behavior and preserve completed intermediate work. Test overrides do not silently rewrite channel defaults.

## Implementation sequence and touchpoints

1. [ ] Add versioned channel metadata/style/reference settings and validated overrides in studio_models.py. Extend existing channel JSON and workflow/run snapshots; preserve legacy fields and accounts. Add a dedicated resolver only if its shared use warrants a separate module.
2. [ ] Implement safe variable expansion, fixed versus generated text, precedence and resolved-metadata snapshots. Wire save/test/review/prepare_item through the same resolver. Preserve exact approval digests and upload-ledger identity.
3. [ ] Add Channel Instructions tabs and effective-value previews using StudioConnections, GuidedStudio and StudioForm. Wire channel changes, explicit inheritance, video overrides and the queued-item update review.
4. [ ] Extend reference inputs/roles and a cached analysis job using existing safe retrieval, yt-dlp, evidence sampling and local model calls. Store an editable brief; consume it in both clip and idea/custom paths.
5. [ ] Add optional research and a traceable reference/asset catalogue. Validate supported data-only templates, dependency status and usage rights before use; preserve manifests in exports.
6. [ ] Wire one-video test and narrowly scoped invalidation/retry. Retain Mode A's upload-only branch and the external ClipX boundary.
7. [ ] Run the acceptance checks below, capture UI evidence and update the user guide. Apply a reviewable backed-up diff only after checks; preserve live accounts/configuration and rebuild Graphify after code changes.

## Verification matrix

| Check | Required evidence |
|---|---|
| Channel isolation | Six channel settings survive save/reload independently; no cross-channel metadata or credentials |
| Precedence | Channel → workflow → item, explicit clearing, inherited lists, sidecar versus form, and later channel selection |
| Variable safety | All four variables, missing/unknown values, literal braces, rejected expressions and resolved size limits |
| Fixed versus instructions | Literal text remains literal; generation occurs only when selected and its resolved output is reviewed |
| Frozen approvals | Updating defaults leaves approved/scheduled metadata and target unchanged; stale bulk edits fail atomically |
| Queue update | Selected eligible items only; explicit overrides retained, old review invalidated, no duplicate upload |
| Mode A boundary | Tests fail if metadata/test/run calls any editing, caption, reference-analysis or rendering service |
| Reference effect | Changing an analyzed style reference changes the reviewed brief and supported B/C edit choices; reference media stays out of final footage |
| User priority | Explicit written/per-video choices defeat conflicting inferred styling; accepted summary survives retry |
| Research traceability | Every result has URL/date; popularity claims match captured evidence; missing license/metrics shown honestly |
| Template safety | Unsupported/incompatible/executable packages rejected with a useful next step; nothing installed automatically |
| Cache behavior | Repeated unchanged clips reuse research/analysis; explicit refresh or relevant changes invalidate only affected results |
| Test safety | One-video test shows metadata/brief/selections/preview; no publication operations and no silent defaults change |
| Recovery/UI | Draft restoration, restart/retry, unavailable services, narrow screens, keyboard focus and actionable errors |
| Caption integration | Caption generation calls the existing standalone tool; no second caption implementation |

These are required acceptance checks for implementation, not claims that the current application already passes them.
