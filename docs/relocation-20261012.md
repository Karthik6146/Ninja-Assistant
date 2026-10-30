# Project relocation — 12 October 2026

The working project is now in your chosen Ninja Assistant folder. Start it with:

```powershell
Set-Location -LiteralPath 'C:\path\to\Ninja-Assistant'
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

Ninja is running at http://127.0.0.1:8000. Open this new folder in VS Code and reload the window. Start a new Codex/Claude session from the new folder so that workspace permissions, skill discovery and working-directory context are refreshed; an already-open session can retain its old workspace root.

Repairs applied:

- Rebuilt 52 Python command launchers in Ninja and ComfyUI using their existing installed packages. Corrected activation scripts and environment metadata. No package or model reinstall.
- Repaired both sides of nine development Git worktree links and seven frontend dependency junctions. Preserved worktree source changes.
- Migrated saved video source/output paths in SQLite, the source manifest, ComfyUI's six-model manifest and Graphify's local runtime/worktree metadata. Original media was not moved again or rewritten.
- Updated Claude's project-scoped Ponytail and Superpowers registrations and its project configuration key. Codex's globally installed Ponytail and Agent Skills remained enabled and required no reinstall. All registered Claude plugin installation directories exist.
- Updated the standalone caption tool to the moved sibling `Development Porjects\Omniroute`. Its root URL redirects to `/app`; saved `http://127.0.0.1:3000/app` so the existing health check correctly reports Ready.
- Made 17 development browser helpers locate sibling Omniroute/Playwright relative to their own file rather than an absolute parent path.
- Updated the workspace guide's startup path.

Validation:

- 96 backend tests and 4 frontend tests passed; production frontend build passed.
- `pip`, `pytest`, `uvicorn`, `yt-dlp` and ComfyUI's `pip` execute from their new locations.
- All nine Git worktrees resolve; all six model file sizes match the manifest; Graphify query and portable checks pass.
- Ponytail and Superpowers activation hooks run successfully from the new folder.
- Live browser check: ClipNet profile/default workflow preserved, saved captioned video plays, advanced tools and mobile layout work. No upload or new content task was started.
- Caption environment imports and its web connection reports Ready.
- Projects, saved workflows/runs, channels, publishing records, packages and conversations match the pre-repair database backup.
- Rerunning the repair audit reports zero remaining file, launcher, junction or stored-path changes.

Backups: `data/backups/relocation-20261012-141953` (initial snapshot) and `data/backups/relocation-20261012-142014` (completed repair, launcher/junction inventory and database). Check the actual backup folder listing if restoring: restore the earliest file copy for the original state, and only restore databases while Ninja is stopped. The initial repair encountered Windows hidden-file handling on Git pointer files; in-place writes preserved their attributes and the resumed repair completed.

Repair audit: `.\.venv\Scripts\python.exe .\data\development\repair-relocation-20261012.py` (read-only by default). Its old path is intentionally retained as the migration source. Historical backups, logs and prior validation fixtures may also contain the old path and are retained as records, not active configuration.

Not tested: a new full GPU render or public upload. Existing Python deprecation warnings and the frontend 511 KB chunk warning remain. This repair does not relocate unrelated sibling projects or rewrite their global editor history.
