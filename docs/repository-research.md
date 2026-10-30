# Repository research

Inspected 2026-10-02. Shallow source snapshots are in ignored `research/`; no upstream installs, lifecycle hooks, authentication, test suites or publishing scripts were executed. Source inspection verifies code paths, not production operation. No upstream source code is copied into Ninja Assistant. No upstream performance or reliability claims are adopted.

| Repository | Inspected commit | Latest commit timestamp in snapshot | License inspected |
|---|---|---|---|
| [Ponytail](https://github.com/DietrichGebert/ponytail) | `e3ba2aa6f1e6f0bc4d69eb09c9f0d0a93af56156` | 2026-09-14 | MIT, copyright 2026 DietrichGebert |
| [Qodo Cover](https://github.com/qodo-ai/qodo-cover) | `adcf55baba40e8fbf8a84e68b70d08bef1e2b9c9` | 2025-06-23 | root LICENSE is AGPL-3.0; pyproject metadata inconsistently says Apache 2.0 |
| [Meta Automation](https://github.com/sunmughan/meta-automation) | `439c3bfaacb1caabef25a7d67c3f204916a5a168` | 2026-09-29 | MIT, copyright 2026 Sunmughan Swamy (CodeAir Software Solutions) |
| [AgentTube](https://github.com/darkzOGx/youtube-automation-agent) | `e26792ae00dc1ec2434faf32632896609396dfad` | 2026-10-01 | MIT, copyright 2025 YouTube Automation Agent Contributors |

Recent commit timestamps alone do not establish active maintenance quality. Inspection scope is the README, root license, dependency manifest, named relevant files and representative tests below, rather than every line of each project.

## Ponytail

Inspected `README.md`, `AGENTS.md`, `package.json`, `ponytail-mcp/package.json`, `ponytail-mcp/index.js`, representative behaviour tests and the available skills/hooks file inventory. Root v4.10.0 package exposes agent-specific instruction adapters; the MCP component serves instructions through stdio prompts/tools with MCP SDK and Zod. Root test commands use Node's built-in test runner and run extension/MCP suites. This is instruction delivery, not model training. README benchmark figures are documentation claims and are not a predicted Ninja outcome.

Selected reuse: independently written development guidance in root AGENTS.md prioritizing necessity, code understanding, existing functionality, standard library and security. No upstream adapter installed. Compatibility: principles are language independent; Node instruction plugins are unnecessary for the FastAPI coordinator. Future copied material must preserve MIT notices.

## Qodo Cover

Inspected README, LICENSE, pyproject, `cover_agent/unit_test_validator.py`, source/test inventory. README's June 15, 2025 notice explicitly declares the repository unmaintained. Validator source tracks coverage, generation attempts, test commands, validation context and reports. Dependencies include LiteLLM, multiple cloud SDKs, WandB, Docker, SQLAlchemy, tree-sitter and diff-cover; Python range is >=3.9.17,<3.14. CLI entry points include cover-agent and cover-agent-full-repo. Representative unit/integration files exercise generators, validators, runner and coverage processor; tests were not run here.

Selected reuse: conceptual baseline → focused candidate → execute → behavioural review workflow, implemented later with this project's pytest-cov/Vitest rather than importing upstream. Optional Qodo integration is disabled and not installed. Pinned snapshot above is an inspection revision, not a compatibility certification. Root AGPL-3.0 license governs the licensing assessment; conflicting package metadata is not permission to treat it as Apache. Any actual integration needs specific licensing review; running a separate process alone does not resolve obligations.

## Meta Automation

Inspected README, LICENSE, package.json, `src/platforms/threads/threads-poster.js`, `src/platforms/instagram/instagram-actions.js`, `src/browser/browser-manager.js`, `src/safety/duplicate-guard.js`, and `tests/execution-mode.test.js`. Node >=18, CommonJS, puppeteer-core and pdf-parse. CLI includes onboard/auth/scan/analyze/approve plus broader job automation. Threads source uses browser typing/uploads with pillar rotation and carousel selection. Instagram actions cover comment/DM operations with dry-run/approval/rate/duplicate gates. Browser manager connects to existing authenticated Brave via CDP; this conflicts with Ninja's dedicated-profile requirement. Test inventory includes execution-mode and platform tests; source has simulated action paths, which must not be mistaken for confirmed publication.

No verified official Instagram Reels publishing interface was established from the inspected modules. README broad automation claims do not establish account eligibility, API support or production readiness. Selected reuse: conceptual review, duplicate protection and platform capability separation only. No browser reuse, bulk engagement or DM automation is imported. Official Meta adapters will be independently implemented after current documentation verification.

## AgentTube

Inspected README, LICENSE, package.json, `agents/production-management-agent.js`, `agents/publishing-scheduling-agent.js`, `agents/analytics-optimization-agent.js`, `utils/scene-repair-service.js`, and `test.js`. Node >=18 with googleapis, multiple generation providers, SQLite, node-cron, Playwright, Sharp and optional ffmpeg-static. Root CLI/dashboard/scheduler architecture is substantially different from one Python coordinator.

Publishing source calls official videos.insert, supports future publishAt/private metadata, records upload attempts/remote IDs and has reconciliation-required error handling plus videos.list reconciliation. This does not prove full persisted resumable-upload recovery; inspected insert calls use googleapis streaming upload. Scene-repair source operates on scene manifests, locks approved/scheduled productions, stores provider task IDs and assembles repaired outputs. Analytics source initializes official YouTube Analytics v2 and Data API v3, queries history and retention with unavailable/simulated checks. Upstream test.js is a custom test entry point; no tests or external jobs were executed here.

Selected reuse: persistent scene revisions, stale review invalidation and ambiguous upload reconciliation as design guidance. No Node components imported; a second scheduler and larger credential surface would add complexity. A future reusable Node component would require a versioned local protocol and preserved MIT notices. Ninja currently has local render preflight and publication reservation foundations; it does not claim upstream production or analytics capabilities.

## Attribution / decision

All four projects are acknowledged through the links and exact revisions above. The implementation is independent. Keep snapshots for reproducible review, but do not ship whole cloned repositories or run their setup scripts automatically. Any later copied code requires the applicable notices and a new compatibility/security review.


## AgentTube implementation update, 2026-10-04

Rechecked origin master at `e26792ae00dc1ec2434faf32632896609396dfad`. Independently implemented the workflows and explicit limits listed in [YouTube automation](youtube-automation.md), within the existing Python coordinator. In particular, simulated analytics fallbacks were not adopted. Upstream dependencies and hooks were not executed. The upstream MIT notice is preserved in THIRD_PARTY_NOTICES.md.
