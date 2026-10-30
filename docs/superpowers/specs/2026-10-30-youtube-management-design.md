# Phase 5: YouTube management — design

Date: 2026-10-30. Status: approved in conversation (sections 1–4); awaiting written-spec review.

## Goal

Jarvis and the YouTube page take three jobs off the owner's hands, in this priority order:

1. **Know how videos do** — per channel: subscribers, views, watch time, which recent video is winning or flopping.
2. **Upload + schedule** — a finished video from a folder (CapCut/Premiere export) or from Ninja's Studio, with Qwen-drafted metadata, one review, one approval.
3. **Handle comments** — sort new comments, draft replies, reply/hide with approval.

All by page and by voice (Hindi, English, Hinglish). Several channels.

## Constraints

- Free: YouTube Data API v3 (10,000 units/day; `videos.insert` and `search.list` have separate 100 calls/day buckets) and YouTube Analytics API. No billing.
  Costs used here: list calls 1 unit; `comments.insert`, `comments.setModerationStatus`, `thumbnails.set` 50 units.
- Every outward action (upload, schedule, reply, hide, publish held comment) needs the owner's explicit approval. Jarvis can never publish without the Allow / Deny card.
- No new GPU load: no new model, no background polling. Qwen (already resident) is used only on demand for comment sorting and upload metadata.
- Reuse the existing pieces: `youtube_auth` (OAuth, DPAPI vault, multi-channel `target`), `youtube.py` upload engine (resumable upload, approvals table, `publishAt`, reconcile), `studio_metadata.generate`, `permissions` confirmation flow (`agent.pause` / `agent.confirm`).
- Google app stays in testing mode: sign-ins expire after 7 days; tools surface "reconnect this channel" instead of failing silently.
- Comment text and other viewers' text is untrusted input (prompt injection): it taints the conversation like email.

## Approach

Plan A — extend the existing YouTube code with focused modules; no separate service.

## 1. Dashboard — `backend/ninja/youtube_insights.py`

- `overview(channel, refresh=False)`:
  - `channels.list part=statistics,contentDetails` → subscribers, total views, video count, uploads playlist id.
  - `playlistItems.list` (uploads playlist, 25) → `videos.list part=snippet,statistics,contentDetails,status` → recent videos: title, published, views, likes, comments, duration, visibility.
  - With the `analytics` scope: YouTube Analytics `reports` (`ids=channel==MINE`): last 28 days by day (views, estimatedMinutesWatched, subscribersGained) and top videos (`dimensions=video`, `sort=-views`, 10).
  - Without the scope: analytics fields are `null` with `"analytics":"not connected"`; never invented.
- Trend marker per recent video: views per day since publish ÷ median of the last 10 videos' views per day. `> 1.5` = up, `< 0.5` = down, else steady. (`ponytail:` age-blind; upgrade to same-age comparison from analytics day data if needed.)
- Cache: table `youtube_insights(channel TEXT, kind TEXT, body TEXT, fetched REAL, PRIMARY KEY(channel,kind))`, TTL 15 min; `refresh=True` bypasses.
- Route: `GET /api/youtube/channels/{id}/overview?refresh=0|1`.
- Removes: per-operation analytics job button and "results appear in Jobs" text.

## 2. Upload + schedule

- Two sources, one engine:
  - **Folder file** (new): upload op params carry `file: {path, size, sha256}` instead of `snapshot`. `validate_bound` gains a branch: the path must be inside `desktop.personal_folders()`, be a video by extension, and match size + sha256. `upload()` and `execute()` are unchanged otherwise.
  - **Studio**: existing content-package path, unchanged.
- `prepare_file(path, channel, when, metadata=None)`:
  - Probe (audio track required, ≤ 4 GB), hash, draft metadata with `studio_metadata.generate` (channel profile + research cache) unless metadata is supplied, validate limits (title no `<>`, description ≤ 5000 bytes, tags ≤ 500 chars).
  - Status: `privacyStatus: private`; if `when` is a time: `publishAt` (timezone-aware, ≥ 2 min ahead) set at insert, so upload + schedule is **one** approval (the separate status op stays only for the Studio path).
  - Category and `selfDeclaredMadeForKids` come from per-channel defaults (replaces hardcoded `categoryId '22'`).
  - Optional thumbnail: an image from the personal folders, applied with `thumbnails.set` after upload; if the channel is not phone-verified, skipped with a clear message.
- The review card shows title, description, tags, channel, time, file; all editable before approval. Editing changes the params and therefore requires the approval of the edited version.
- Not in scope: generated thumbnails, playlists, editing metadata after upload.

## 3. Comments — `backend/ninja/youtube_comments.py`

- `refresh(channel)`: `commentThreads.list allThreadsRelatedToChannelId, order=time, maxResults=50, textFormat=plainText` plus `moderationStatus=heldForReview`. New comments go into table `youtube_comments(id TEXT PRIMARY KEY, channel, video, video_title, author, text, published REAL, held INTEGER, category, needs_reply INTEGER, draft TEXT, state TEXT)`. State: `new | replied | hidden | published | skipped`.
- Sorting: Qwen, one call per ≤ 20 comments, at most 50 per refresh, structured output (Ollama `format` JSON schema): `category ∈ question, praise, feedback, spam, hate, other`, `needs_reply`, `reply` (comment's language, channel tone; no links, no promises, no personal details; empty when unsure). Output failing the schema is discarded (comment stays uncategorised).
- Actions (each needs approval; batch = one approval over the exact list):
  - reply → `comments.insert` with `parentId`;
  - hide → `setModerationStatus rejected` (card warns it cannot be undone; `banAuthor` is a separate tick box, default off);
  - publish held → `setModerationStatus published`.
- Not in scope: automatic replies, delete, ban by voice.
- Quota errors (403 `quotaExceeded`) become "YouTube's daily limit is reached; it resets tomorrow".

## 4. Jarvis, page, cleanup, load

### Jarvis tools (permission `youtube.read` read-only; `youtube.publish` actions)

| Tool | Kind | Notes |
|---|---|---|
| `youtube.stats(channel?, video?)` | read | from cache; "how did my last video do", "kitne subs" |
| `youtube.comments(channel?, filter?)` | read, untrusted | counts + top questions; taints the conversation |
| `youtube.prepare_upload(path, channel?, when?)` | creates a review op | no upload yet |
| `youtube.approve(operation)` | always confirm | card shows real title, channel, time |
| `youtube.respond(comment, action, text?)` | always confirm | action `reply` or `hide`; card shows comment + reply. Publishing held comments and `banAuthor` stay page-only. |

`youtube.approve` and `youtube.respond` always need the card (tool effect sensitive). The card summary is built from the operation / comment, not from the model's arguments. Channel is optional; with one connected channel it is implied, otherwise the tool lists the channels.

Eval: about 10 new cases (English, Hinglish, Hindi) in `tests/evals/jarvis_tools.jsonl`.

### Context budget

Measured 2026-10-30: 28 tools ≈ 3,000 of Qwen's 8,192 context tokens (3,823 with the spoken system prompt).

- Slim schemas in `agent.tool_schema`: drop auto `title` keys and redundant defaults. Report the measured saving.
- Remove from Jarvis: `research.search` (superseded by `research.deep`) and `system.large_files` (needs an exact configured root; no eval case). The eval must not drop.
- Cap tool results sent to the model (today 12,000 chars) so one large result cannot crowd out the conversation; target ≤ 6,000 chars with a truncation note.

### YouTube page

One page, four tabs: **Overview** (dashboard) · **Upload** (pick → review → queue/status) · **Comments** (filters: Needs reply, Questions, Spam/Hate, Held, All) · **Channels** (connect/reconnect with Analytics + Manage, per-channel profile and defaults).

### Cleanup

- Remove `YouTubeStudio` legacy sections replaced by the tabs: single-channel connect, global profile form, content-package prepare form, analytics job button.
- Merge the global `youtube_profile` preference into per-channel profiles (`studio_profiles`).
- Fix disconnect to work per connection (today it only clears the legacy token).
- Keep `OperationCard` (used by ContentCMS and GuidedStudio).

### Load

No polling, no new model or library. Measure before/after: GPU VRAM, CPU, RAM of Ninja processes, prompt tokens per Jarvis turn.

## Testing

- Unit (fake Google responses): overview parsing; trend rule; cache TTL; missing analytics → `null`, not invented; folder upload refuses files outside personal folders and changed files; `publishAt` future + private; one approval covers upload + schedule; comment schema validation; injection comment causes no action; hide warning; batch approval binds the exact list; quotaExceeded message; Jarvis cannot upload/reply/hide without the card; every tool accepts invoke's keywords (existing guard).
- Eval: tool choice must not drop; new YouTube cases pass.
- Live, after the owner reconnects a channel with Analytics + Manage: dashboard numbers match YouTube Studio; one private test upload; one comment reply. Each real action with the owner's OK.

## Done means

All tests pass, eval holds, live checks done, graphify rebuilt, `docs/jarvis-guide.md` and the focus plan updated, load before/after reported.

## Owner actions

Reconnect each channel with **Analytics** and **Manage** ticked (the current sign-in expired).
