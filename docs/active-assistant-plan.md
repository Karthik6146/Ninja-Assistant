# Active assistant and prompt-first studio plan

Goal: create/edit videos from a brief in Video Studio, manage editable YouTube automation profiles in Automations, and provide a local Qwen daily assistant with grounded content suggestions.

- [x] Studio planner: explicit create/edit/clip/upload modes, local media selection and uploads, automatic installed-voice selection, visible missing inputs/dependencies and follow-up questions. Keep credentials/policy outside model authority and avoid forcing idea/reference URLs into clipping.
- [x] Navigation: Video Studio opens on Create with a visible prompt; Automations opens on YouTube Profiles. Friendly named automation profile create/edit form reuses existing workflow persistence and activation, preserves advanced controls, and never retargets queued jobs.
- [x] Daily assistant: persisted Asia/Kolkata priorities, completion state, conversational Qwen advice and suggested next actions; greet/ask in app, never start uploads from an unsolicited greeting. Queue model work on the existing single worker.
- [x] Research ideas: reuse authenticated YouTube research, store references/counts/retrieval time, validate Qwen evidence IDs, and label suggestions without guaranteed/current virality claims.
- [x] Verify backend boundaries and persistence, real Qwen advice/plans, read-only account research, UI flows, profiles, keyboard/mobile, local service dependencies and a playable local idea assembly where resources permit. Preserve credentials/configuration/media; back up and deliver guarded diff.

No new package/platform or paid cloud inference. Existing captions remain in ClipX. ComfyUI is already installed and is started locally. Additional real YouTube channels require a distinct authorized OAuth identity.

References read 13 October 2026: https://docs.ollama.com/capabilities/structured-outputs and https://developers.google.com/youtube/v3/docs/videos/list. JSON schema responses are validated; regional mostPopular is an observation, not a growth/virality guarantee.
