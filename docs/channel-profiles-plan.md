# Channel profiles and shared progress

Goal: one place to manage channel-specific instructions and reusable workflows, submit one brief to multiple profiles, and steer individual running tasks.

Implementation:
- [x] Persist per-channel label, audience, instructions and default workflow with revision checks; retain through OAuth refresh/reconnection. No limit on profile count in storage.
- [x] Queue a durable multi-profile planning job using existing worker/jobs. Snapshot channel, connection, policy and profile per target. Per-target failures and retries cannot duplicate child runs. Production requires existing activated policy; tests cannot publish.
- [x] Add Profiles navigation, select-many cards and shared brief. A read-only all-profile content view makes every task visible without changing publishing targets.
- [x] Dedicated accessible progress/preview window follows revised tasks, shows stages and generated previews, and accepts mid-task instructions. Existing cancel/revise pipeline retained and prioritized ahead of queued production.
- [x] Test six isolated channels, cross-channel rejection, reconnect persistence, retries and partial failure, preview routing, live user journeys, narrow screens and keyboard focus. Use mocked publishing.

Research 2026-10-10: Buffer channel groups and All Channels, Metricool brands/settings, n8n all-executions. Adopt profile identity + unified task visibility + status filters; keep advanced controls separate. No external source code reused or new automation service installed.
https://support.buffer.com/articles/using-channel-groups-in-buffer-vtEPrhAiNr
https://support.buffer.com/en-us/articles/how-to-use-the-all-channels-view-in-buffer-oqqE4Sdf3T
https://help.metricool.com/how-to-setup-a-brand-rqv8d
https://docs.n8n.io/build/understand-workflows/understand-executions/view-all-executions.md

Profiles do not grant Google access. Each real account/channel still needs its own authorized OAuth connection. GPU tasks remain serialized by the existing worker; batch start means queue all selected channels, not run unlimited renders simultaneously.
