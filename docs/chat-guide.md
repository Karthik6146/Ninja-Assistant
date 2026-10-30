# Chat and token usage

Open http://127.0.0.1:8000 and connect with your existing local token. Refresh the browser after an update.

- **Send:** Enter sends; Shift+Enter inserts a line break. The square stop button cancels the active response. Attach up to three text files, 8 KB each. Cloud sharing still requires explicit consent.
- **History:** Search titles and saved messages, or press Ctrl+K. Chats are grouped by date; click the pencil beside the title to rename. Project selection beneath the composer files a chat. On smaller screens use History to open the list.
- **Scrolling:** Messages and history scroll separately. The composer remains visible. Scrolling up pauses automatic following; Latest message returns to the response. Markdown headings, lists, tables and code render in replies. Wide code and tables scroll horizontally. Copy answer copies the original Markdown.
- **Session tokens:** The pill beside the conversation title totals provider-reported input and output for this saved conversation, including earlier turns. Click it to open the usage widget.
- **Usage widget:** Today, this week (Monday onward), this month, all time, and this session show input/output totals and request counts. The chart and daily table cover the last 30 days. Model totals are all time. Dates use Asia/Kolkata and each request's submission time.

Counts are stored locally in SQLite's `chat_usage` table, one row per chat job. Ollama reports `prompt_eval_count` and `eval_count`; compatible cloud providers report streaming `usage`. The cloud endpoint must support `stream_options.include_usage`. Reports are saved as they arrive, including when a later step fails. Repeated reports overwrite the same request, so they do not double-count.

Input tokens include earlier conversation context sent with each request. Counts appear after the provider reports them, usually at the end of generation. An asterisk means some requests have incomplete or unknown counts. Old chats cannot be backfilled accurately; cancelled or interrupted requests may also lack counts. These are not treated as zero usage. This ledger covers chat only, not automation or coding tool calls; it does not estimate prices or billing.

Raw HTML and automatic remote image loading are disabled in replies. Links open separately and must use HTTP or HTTPS. Model replies remain untrusted content.

Validated with the backend suite, frontend tests/build, actual local Ollama responses, and isolated Chromium checks at desktop and 390px mobile widths. Browser checks cover history search/rename, keyboard sending, saved usage after reload, modal dismissal, scrolling during generation, stopping, and jumping to the latest message.

Implementation: `backend/ninja/adapters.py`, `workspace.py`, `usage.py`, `workspace_routes.py`; `frontend/src/ChatWorkspace.tsx`, `ChatMarkdown.tsx`, `ChatUsage.tsx`, `chat.css`. Tests: `tests/test_chat_usage.py`, `frontend/src/ChatMarkdown.test.tsx`.
