> Historical baseline document. For the current workspace behavior, see [workspace guide](workspace-guide.md), migration and validation. Built-in caption generation has been retired.

# Official documentation checked

Read during implementation on 2026-10-02. APIs were implemented against pinned versions and then tested locally; a newer documentation version alone is not proof of runtime compatibility.

- [FastAPI file uploads](https://fastapi.tiangolo.com/tutorial/request-files/): spooled UploadFile and multipart integration.
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence): SQLite checkpoint threads and durable state.
- [faster-whisper upstream](https://github.com/SYSTRAN/faster-whisper): lazy segment iteration, CPU int8 and word timestamps.
- [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html): trim/concat, crop, subtitles and audio mixing.
- [React](https://react.dev/learn), [Tailwind Vite integration](https://tailwindcss.com/docs/installation/using-vite): components/state and Vite CSS plugin.
- [Ollama chat API](https://docs.ollama.com/api/chat): configurable chat model, nonstreamed responses and token counts.
- [pytest](https://docs.pytest.org/en/stable/), [pytest-cov reporting](https://pytest-cov.readthedocs.io/en/latest/reporting.html): tests, branch coverage and JSON reports.
- [Git worktree](https://git-scm.com/docs/git-worktree): separate branches and linked working trees.

The cloud adapter supports the common chat-completions shape only. It does not claim every provider supports that protocol. Select an HTTPS provider endpoint/model deliberately and verify its documentation before enabling cloud sharing. Provider-specific adapters, costs and supported capabilities are later work.

YouTube external APIs are implemented as documented in [YouTube automation](youtube-automation.md), with official Google documentation checked on 2026-10-04. Instagram/Threads external API adapters are not implemented. Their OAuth, scopes, quota costs, account eligibility and app-review rules must be checked in current official platform documentation when those features are implemented. No numerical quota/restriction claims are displayed in the current UI.


The JARVIS foundation uses native Ollama tool calls, existing standalone ClipX CPU transcription and Windows SAPI. Public discovery uses Wikipedia with Bing RSS fallback; source fetches retain the existing pinned-IP HTTPS boundary. No browser-cloud voice, paid provider, new library or downloaded model is enabled. See [Jarvis guide](jarvis-guide.md) and research/license inventory.
