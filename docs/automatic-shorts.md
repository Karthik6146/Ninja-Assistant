# Automatic Shorts

In Video Studio or Automations, open **ClipNet Workflow**. Its saved channel, source URL, editing brief, caption tool and content declarations remain in place. Automatic export, local-model metadata, YouTube research and public publication are enabled for new runs. Click **Run workflow** on the saved workflow card. Keep Ninja and its worker running until processing and uploading finish.

Ninja prepares candidates using the existing editing and standalone caption integration, exports final clips, researches YouTube, asks the configured local Qwen model for clip-specific titles/descriptions/tags, then queues upload and publication to the workflow's bound channel. No per-video review or manual metadata is required. Change the source URL and workflow brief by opening the project, saving and activating the new revision. Title and description fields are optional guidance when model metadata is enabled.

Automatic publishing is scoped to the saved channel/workflow revision. Other workflows and old review runs retain their policies. Pausing or editing a workflow stops new publication authorization; it does not undo an already executing upload/publication. Use Activity / cancel for pending work. Test run renders and generates metadata locally but never creates publishing operations.

Execution history shows agent-written metadata and downloadable outputs. Failed runs offer Retry failed steps; saved renders and successful metadata are reused. Upload recovery uses the existing immutable channel/connection binding and ledger. Finished-video mode still skips editing, captions and rendering, even when model metadata is enabled.

## Research and model access

Research uses read-only YouTube API calls through the existing OAuth connection. Credentials are never sent to Qwen. Ninja records source URLs, retrieval dates, public counts and the query, cached for 24 hours. It searches recent short-duration videos relevant to the source and reads the regional mostPopular chart (India by default). These are not a dedicated Shorts trending feed or proof that a video is viral. Research informs wording; the actual clip transcript supplies content facts.

No new Google login was required for ClipNet's read access. A failed/expired connection or quota error stops the run with an error instead of silently skipping research or switching to a paid provider. YouTube API project restrictions can still prevent public visibility; inspect publishing status and recovery if the API rejects publication.

References: [YouTube search.list](https://developers.google.com/youtube/v3/docs/search/list), [videos.list](https://developers.google.com/youtube/v3/docs/videos/list), [Ollama structured output](https://docs.ollama.com/capabilities/structured-outputs). Checked 2026-10-08. No upstream code copied.

## Validation

80 backend tests and 2 frontend tests passed; production frontend build passed. Coverage includes six independent channel configurations, automatic export/metadata/upload queueing, local-test isolation, retry deduplication, public-status queueing, and finished-file metadata without editing. A real local test exported two final clips and generated valid Qwen metadata with zero publishing operations. Real read-only ClipNet YouTube research returned 12 source/related/popular results. Public publishing was mocked for validation; no test footage was posted.
