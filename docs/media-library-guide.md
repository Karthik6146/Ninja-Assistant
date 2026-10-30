# Media library

Open **Media Library** in the left navigation (formerly Recordings). Existing `#recordings` bookmarks still open it.

- **Import media** or drag files into the drop area. Ninja preserves originals and inspects each file. Transfer progress is real; cancel stops the active upload. Supported video formats and the existing 4 GB limit remain.
- **All media / Imports / Renders / Favourites / Archive** organise the view. Renders contains Video Studio outputs registered as managed projects. Existing trim-editor exports are available in their source video's details through Preview version and Download export.
- Search names, labels and notes; filter by label/status; sort by name, date or duration. Publishing status uses saved operation records, not a new remote account sync or invented analytics. Scheduled and public are distinct from private uploads. Dates show Asia/Kolkata.
- Switch between **List** and **Grid**. Each page has 20 items. **Select this page** selects only visible rows. Bulk actions use the explicit selected set, including selections retained across pages; changing filters clears selection. Up to 100 items per organisation request.
- Select rows to edit footage or upload finished videos through the existing Video Studio flow, add a label, favourite or archive. Bulk labels retain other labels. Missing/uninspected files cannot start edit/upload handoffs.
- **Details** opens a video preview and media properties. Save a library name, labels, notes and favourite/archive state. Up to 20 labels (32 characters each) and 2,000-character notes. Draft edits survive closing the panel and refreshing. **Discard draft / reload** loads saved details; concurrent edits are rejected until you reload.
- **Archive** hides a video from the main library. It preserves files, render plans, existing workflows and already scheduled publication. Open Archive, select media, and **Restore** to bring it back. It is not deletion or a workflow pause.
- In Details, use **Create clips / Edit in Video Studio / Upload as finished / Open trim editor**, or download source media/exports. Library names and notes do not change approved YouTube titles or descriptions. Your existing workflow policy still controls publication.

Thumbnails are locally generated JPEG caches using installed FFmpeg. Original video bytes stay unchanged. Thumbnails load as rows become visible. If thumbnail generation is unavailable, the preview remains accessible in Details. Missing files show an explicit status; re-import the source if it is gone.

Validation (13 October 2026): 101 backend tests, 8 frontend tests, production build and browser journeys with 23 generated-media fixtures. Verified real thumbnails/cache/playback, save/reload, unsaved drafts, bulk labels, pagination, archive/restore, missing-file controls, old bookmarks, each Video Studio handoff, the trim editor, real import, keyboard focus/Escape, mobile layouts and reduced motion. No public test uploads.

Navigation reference: [YouTube's official bulk content management guide](https://support.google.com/youtube/answer/6249768?hl=en). Adapted thumbnail/row, checkbox and bulk-action patterns; no external source code copied.

Backup and reviewable diff: `data/backups/media-library-20261013` and `data/development/media-library-update.patch`. Historical test builds remain outside the live data/configuration. Existing Python deprecation warnings and a 525 KB frontend chunk warning remain.
