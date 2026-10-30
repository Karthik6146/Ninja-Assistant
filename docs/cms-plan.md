# Content CMS implementation plan

Goal: replace the default workflow wizard with a content dashboard and prompt-first task creation, retaining all existing controls under advanced settings.
Architecture: reuse saved definitions, immutable run snapshots, SQLite jobs, local Qwen, existing YouTube OAuth and ClipX. Add bounded assistant planning and an interrupt/revise worker action. No new dependencies or cloud services.

- [x] Add schema-constrained brief planning and typed source/reference links; preserve account/publishing decisions outside model output.
- [x] Add interrupt/revise with immutable target, cancellation, restart-safe replacement and refusal once publishing begins.
- [x] Introduce CMS overview, queue filters, schedule list, reusable automations, prompt composer and per-task instructions; retain advanced editor and publishing recovery.
- [x] Improve transcript selection/metadata guidance from reviewed skill concepts; cache public reference evidence and show limitations.
- [x] Test boundaries, retries, reference fetching, actual local model and responsive browser. Deliver guarded diff, backup and update live app only after checks.

Research checked 2026-10-09: Jakeschincariol/youtube-agent-skill README, MIT LICENSE, yt-seo, yt-shorts and title.py. Adapt concepts only, do not copy upstream source. The package does not upload and its hook scores are heuristics, not predictions. Adopt self-contained opening/payoff checks and concrete search descriptions; do not add unsupported retention analytics, comment posting or invented virality scores.

Official references: https://github.com/Jakeschincariol/youtube-agent-skill ; https://buffer.com/features/social-media-content-planner ; https://www.opus.pro/calendar ; https://www.descript.com/blog/article/underlord-ai-video-editor-primer . Queue/draft organization, separate schedule view and instruction-based editing inform the design. Agent-Reach CLI unavailable; official web sources used. No remote skills installed or their instructions executed.

Review focus: account/policy injection, reference SSRF, stop-versus-publish race, retry duplication, refresh restoration, reduced motion and narrow viewport. Test publishing with mocks only. Keep finished mode free of editing services and preserve standalone captions.
