# Media library implementation plan

Goal: replace the recording-card list with a compact, thumbnail-led media management screen, keeping import, playback, editing and publishing handoffs intact.

Architecture: reuse managed projects and file routes. Store library-only names/labels/notes/favourites/archive flags in preferences, independently of project edit plans and approved publishing metadata. Build cached thumbnails with the installed FFmpeg. Report publishing state from existing operation records only.

- [x] Backend: authenticated inventory, atomic revision-checked single/bulk organisation, confined cached thumbnail route; preserve originals, EDLs and publishing snapshots. Verify partial batch failure rolls back, stale edits reject, and unsupported paths stay blocked.
- [x] Frontend: dense content table and optional grid, thumbnail/duration, Imported/Rendered/Favourites/Archive views, search/label/status filters, sorting, pagination, visible-page selection, explicit bulk actions and preview/details dialog. Persist view settings and unfinished detail edits; preserve Video Studio IDs and standalone trim editor.
- [x] Verify real cached thumbnails and playback, metadata save/reload, archive/restore and bulk selection, keyboard/Escape focus, narrow screens/reduced motion, import and each existing handoff. Public publishing remains behind the existing workflow policy.
- [x] Deliver guarded backup/update, user guide, screenshots and graph refresh.

Design: a quiet dark content table, mint import/action accents and compact status chips; use rows for desktop density and media cards on narrow screens. Preview/details opens in a native modal with a stable selection and focus containment. Archive hides media from the library's default view without deleting it or cancelling existing workflows. Library names/notes do not edit approved YouTube titles/descriptions.

Reference: YouTube's official Content management documentation uses checkbox selection and bulk changes: https://support.google.com/youtube/answer/6249768?hl=en (read 13 October 2026). Navigation pattern adapted; no third-party code copied.
