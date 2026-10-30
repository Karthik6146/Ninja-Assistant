# Workspace migration and rollback

## Preserved state

The update was developed in `data/development/improvement-worktree` against a committed snapshot in `improvement-baseline`, because the live folder was not a Git repository. Original file hashes were recorded before editing. Applying the update checks those hashes and refuses to overwrite intervening user changes.

Before application, the deployment snapshot contains changed source files, frontend build, a manifest of newly added/deleted files, private `.env` and SQLite backups, plus hashes of existing project media. Keep this backup private. User media, transcripts, caption variants, caption presets, OAuth files and model caches are not deleted. The standalone ClipX repository is untouched.

SQLite initialization adds conversations, workspaces, templates and job events plus nullable job lifecycle fields and an idempotency index. Existing `waiting-review` states become `waiting_for_approval`. Pending/running removed transcription jobs fail clearly with `CAPTION_TOOL_REQUIRED`; completed assets are retained. This migration is repeatable. Old in-memory-only chat cannot be recovered because it was never stored.

## Removed paths and replacements

| Removed code | Replacement / preservation |
|---|---|
| Whisper worker, transcription endpoint and generation UI | Open Caption Tool launches the separately configured ClipX page; no automatic transfer |
| CaptionExtras, Hinglish mutation and preset creation endpoints | Standalone caption tool; all stored variants/presets remain on disk |
| Blocking POST `/api/chat` | Create a conversation, POST its messages with `request_key`, observe `/api/tasks/{id}/stream` |
| Blocking POST `/api/research` | POST `/api/automations/run`; completed reports download through task output routes; old notebook downloads remain supported |
| Unused generic `reserve_publication` helper | Existing YouTube-specific transaction, approval and resumable-upload guards remain authoritative; historical publications table retained |
| faster-whisper and exclusive transitive packages | Existing FFmpeg render/caption-export utilities retained; no new dependency |

All repository consumers and the smoke script were updated. Obsolete tests of removed creation paths were replaced with preserved-export/data tests; no tests were skipped, assertions weakened or thresholds reduced. Existing YouTube duplicate-prevention tests remain.

New API submissions require a stable caller-generated key of 8–100 word/hyphen characters. Duplicate keys with identical inputs reuse the job; conflicting inputs fail. Generic retries intentionally exclude publishing/coding actions that have dedicated approval/recovery flows.

## Rollback procedure

Use the exact deployment backup path recorded in `workspace-validation.md` and its `manifest.json`.

1. Stop Ninja's API and worker after cancelling or waiting for active work. Do not stop Ollama, ClipX or unrelated Python applications.
2. Back up the **current** `data` folder and `.env` separately before rollback; this protects conversations and outputs created since the update.
3. Restore backed-up source and `frontend/dist` files. Remove only source/build paths listed as newly added in the deployment manifest. Never recursively delete the data folder.
4. Restore `ninja.sqlite` using SQLite's backup API while Ninja is stopped. Restore any other SQLite snapshots listed in the backup. Do not blindly copy a live WAL database. This returns application records to the deployment snapshot and therefore omits post-update records; keep the step-2 backup for recovery.
5. Restore the old dependency lock from the source snapshot, then reinstall it with `.venv\Scripts\python.exe -m pip install -r requirements-lock.txt`. Retired ASR dependencies may require network access. Existing `.env` needs no rollback because deployment does not edit it.
6. Start `scripts/start.ps1` and verify the original recording and caption exports before resuming work.

The SQLite backup/restore down path is exercised in `test_migration_snapshot_can_be_restored`; the live deployment also records pre/post data hashes. A complete application rollback is not performed on your live instance. Additive schema changes retain legacy fields, but running old and new workers together is unsupported.
