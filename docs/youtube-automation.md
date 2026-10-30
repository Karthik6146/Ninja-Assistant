# YouTube automation: setup and daily workflow

This feature adapts workflows from [darkzOGx/youtube-automation-agent](https://github.com/darkzOGx/youtube-automation-agent/tree/e26792ae00dc1ec2434faf32632896609396dfad), inspected at commit `e26792ae00dc1ec2434faf32632896609396dfad` on 2026-10-04. Ninja implements them in its existing Python worker; upstream Node agents and dependencies are not installed. This is a focused integration, not full upstream feature parity.

## Access and Google login

1. Start Ninja using `powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1` from the project folder. Keep the terminal open. Open <http://127.0.0.1:8000> and connect using your local `data/access-token` (or configured `NINJA_TOKEN`).
2. In [Google Cloud](https://console.cloud.google.com/), create/select your own project. Enable **YouTube Data API v3**. Enable **YouTube Analytics API** if you want date-range reports.
3. Configure Google Auth Platform's consent screen. For an external app in Testing, add your Google account as a test user. Create an OAuth client with application type **Desktop app** and download its JSON. An API key or web-client JSON cannot replace this file.
4. Open **Projects → Video Studio → Publishing → Import downloaded Desktop client JSON**. Ninja stores only the required client fields encrypted with Windows DPAPI for your Windows account. Do not put passwords, cookies or tokens in Chat.
5. Select optional visibility/scheduling and analytics permissions. Click **Prepare Google sign-in**, then **Sign in with Google**. Choose the Google account/channel you intend to use and grant the requested permissions. The callback uses `http://127.0.0.1:8000/oauth/youtube/callback`; keep Ninja running on port 8000.
6. Return to Ninja and click **Refresh YouTube**. Confirm the displayed channel name and ID. Use that exact ID in the YouTube draft's account field.

The login follows Google's [desktop OAuth flow](https://developers.google.com/identity/protocols/oauth2/native-app) with PKCE, an expiring single-use state, and offline token refresh. OAuth clients and tokens belong to you; Ninja does not provide a shared YouTube login. Google may require reconnecting after grants expire or are revoked. **Disconnect locally** forgets local tokens; revoke Google-side access through your [Google account connections](https://myaccount.google.com/connections) when desired. DPAPI data is tied to your Windows identity; reconnect when moving to another Windows account/computer.

## Plan and produce

1. Import a recording, transcribe/edit, generate a preview, approve the exact revision and render the final MP4 in Video Editor.
2. Create a content package in the YouTube content desk. Click **Refresh YouTube** and select that package in the automation panel.
3. Save your audience, language, content pillars and tone. Enter a topic/format brief and source notes with citations. **Generate review draft with Ollama** queues a local model job. Current setup uses the model configured in `.env`; no Google login is needed for drafting.
4. After the job finishes, refresh the panel, inspect the proposed title, description, tags, thumbnail brief and scene scripts, then apply the proposal. A new outline replaces the package's scene list. To repair only one scene, select that scene before generating. Repairs preserve other scenes and invalidate that scene's narration/timing and platform reviews.
5. Refresh the selected package in the content desk. Check facts, edit copy, record rights for every scene and the recording/music, select the completed final render and save/review the exact draft. Text proposals do not generate or modify the rendered video; use your own licensed visuals/audio and existing editor workflow.

Source notes and transcripts are untrusted evidence, not verified facts or model instructions. The model has no shell access. Malformed/oversized responses fail visibly; shorten the brief and retry. No paid asset-generation service is connected.

## Private upload, publication and scheduling

1. Explicitly choose the made-for-kids and altered/synthetic-content declarations. Click **Check video & prepare exact upload review**.
2. Wait in Jobs, then refresh YouTube. Review the precise channel, title, description/chapters, tags, audience declarations, file hash, size and source revision. Preparing does not upload.
3. Click **Approve this exact PRIVATE upload**. The worker transfers the reviewed render using Google's resumable-upload protocol. A private result is labelled `private`, never `published`. Open the confirmed video in YouTube Studio to inspect it and its processing status.
4. To publish, choose **Public now** or **Unlisted** and prepare a separate review. To schedule, keep visibility **Private** and supply an ISO timestamp with timezone, for example `2026-10-10T18:00:00+05:30`. Review and approve that exact status change. The draft calendar field in the content desk alone does nothing remotely.
5. To cancel a scheduled release, choose **Private / cancel existing schedule**, leave the time blank, then prepare and approve the review. This remains possible if the local content was subsequently edited.

Google's [video insertion rules](https://developers.google.com/youtube/v3/docs/videos/insert) restrict uploads from certain unverified API projects to private visibility until the project passes an audit. Scheduling requires a private video that has never been published; Google enforces eligibility. Ninja preserves writable status fields when changing visibility, following [videos.update](https://developers.google.com/youtube/v3/docs/videos/update).

Schedules execute on Google's servers even if Ninja is closed. **Ninja's emergency stop does not cancel schedules already accepted by Google.** Cancel them explicitly in Ninja after resuming, or directly in YouTube Studio. Google controls quotas and processing times; check your project's quota page rather than assuming a fixed available allowance.

## Recovery and real reports

- If transfer fails, use **Resume / verify existing operation**. Ninja queries the persisted session offset before sending remaining bytes. It never silently creates another upload when the previous initiation/completion is uncertain. Sessions are encrypted locally. See Google's [resumable upload protocol](https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol).
- For `reconciliation_required`, inspect YouTube Studio. If the matching video exists, verify its content and enter its 11-character video ID, then confirm reconciliation. Ninja checks the channel and title; Google does not expose a hash matching your local file. If no matching video can be established, the operation remains blocked rather than risking a duplicate. There is currently no automatic reset of an expired ambiguous upload.
- Editing approved content or switching channels blocks stale upload/publication approval. An unapproved review can be superseded by preparing again; a started upload retains its duplicate guard.
- Choose report dates and **Retrieve real analytics**. Open the completed Jobs card's **Job result**. Data API statistics are returned as supplied; Analytics reports require the optional analytics grant. Empty/missing data remains unavailable, never simulated. See [Analytics reports.query](https://developers.google.com/youtube/analytics/reference/reports/query).

## Feature correspondence and limits

| Upstream workflow | Ninja implementation |
|---|---|
| Channel profile and production brief | Saved local profile plus Ollama proposals |
| Scripts, SEO metadata, thumbnail planning | Reviewed title, description, tags, thumbnail brief and scene scripts; no performance guarantees |
| Scene repair | Selected-scene text proposal, explicit apply, stale narration/timing/review invalidation |
| Media production | Existing local transcription, clip/caption editing, previews and reviewed final renders from user-provided media |
| Account connection | Google Desktop OAuth, PKCE, DPAPI storage, channel verification |
| Upload/recovery | Exact private-upload approval, persisted resumable session, fingerprint duplicate guard and manual reconciliation |
| Publishing/scheduling | Separate exact status-change approval; Google server-side scheduling and cancellation |
| Analytics | Actual video statistics and optional date-range Analytics reports |
| Automated topic discovery/trends | Not connected; use supplied source notes and Research excerpts |
| Paid narration, image/video providers, scene assembly | Not connected |
| Autonomous daily production, strategy learning, A/B tests, advanced SEO experiments | Not implemented |
| Multi-channel profiles and recurring calendar | One connected channel and one local profile; no recurring scheduler |

Verification uses mocked Google responses, real Windows DPAPI and local project tests. A live consent flow, upload, publication and Analytics report still require your Google client/channel and have not been exercised with your account. No video was uploaded or published during development.
