# Security

Ninja Assistant is a single-user app that runs on your own Windows PC. It is not built to be exposed to a network.

## Reporting a vulnerability

Please open a private security advisory on this repository (GitHub → Security → Report a vulnerability). Do not file public issues for security problems.

## Security model

- **Loopback only.** `scripts/start.ps1` binds the server to `127.0.0.1:8000`, and the Host header must be `127.0.0.1` or `localhost`, which blocks DNS rebinding. Don't expose port 8000 to other machines.
- **Access token.** Every `/api` request needs the token from `NINJA_TOKEN` or `data/access-token`. Every change (any non-GET request) also needs it in the `X-Ninja-Token` header. The browser's cookie holds a random session id, never the token. Locking the app revokes the session.
- **Origins.** By default only `http://127.0.0.1:8000` and `http://localhost:8000` are trusted. Add `http://127.0.0.1:5173` to `NINJA_ORIGINS` only while you run the Vite dev server.
- **Credentials.** Google sign-ins are stored in `data/youtube-secrets`, encrypted with Windows DPAPI for your user. Gmail access is read-only.
- **Jarvis actions.** Tools are typed and checked against a permission grant (Allowed, Ask first, or Off). Once email, WhatsApp, web or shared-document text is in a conversation, every action needs an **Allow once / Deny** click. Approvals are single-use, tied to the exact arguments, and expire after 10 minutes.
- **Publishing.** Uploads need an approval tied to the exact file and metadata. Studio's automatic workflows never publish AI-written titles or descriptions publicly without your approval, and AI-written metadata may not contain links.
- **Web fetches.** Research fetches use HTTPS on port 443 only. They connect to the public IP that was checked, never a private one, and do not follow redirects.

## Same-user boundary

Any program running as your Windows user can read `data/` and the token. Keep `data/`, `.env` and the access token private. They are excluded by `.gitignore`.

## Known limits

- The bundled video editor (OpenChatCut, a separate open-source project) trusts any program on your PC that connects to it. Ninja limits what it can import to `data/video-sources` and `data/projects`.
- Jarvis runs on a small local model. Prompt-injected text can still change what it *says*; the confirmation gate is what stops it from *acting*.
