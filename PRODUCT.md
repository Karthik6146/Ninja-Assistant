# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

One owner: a YouTube creator on a Windows 11 PC (RTX 4060), using Ninja every day on localhost. Speaks Hindi, English and Hinglish, often mixed in one sentence, and prefers English or Hinglish replies. Uses Jarvis by voice (hands-free, wake word) and by text, and manages his YouTube channels from the same app.

## Product Purpose

Ninja is a private, fully local personal assistant. Its centre is Jarvis, modelled on Iron Man's JARVIS: a calm British-butler companion that holds natural, human-like conversation, tells the owner things, researches any information he asks for, and carries out real tasks on his PC and devices with verified receipts. Studio automates video clips, editing and YouTube publishing. Success: talking to Jarvis feels like a fast, real conversation, and asked-for work actually happens.

Owner's goals for Jarvis, not all built yet (2026-10-28): general conversation and information; research on any topic; reading and summarising his emails and messages; managing and operating his system and devices; YouTube management.

## Positioning

Everything runs offline on the owner's PC (Qwen via Ollama, Whisper, Kokoro, local listener models); no cloud or paid service by default. Jarvis never claims an action without a tool receipt.

## Capabilities and Constraints

- Built today: voice and text conversation with Hindi/English/Hinglish understanding and spoken language switching; wake word "Hey Jarvis"; barge-in; local tools (tasks, reminders, memory, approved files, web research, opening Notepad/Calculator/Explorer, Studio workflows); Studio (Video Studio, Automations, Media Library, OpenChatCut editor); YouTube channels, uploads, scheduling and analytics.
- Not built yet: email and messaging access, broad device/system control. Do not show or claim them in the UI until they exist.
- Removed on 2026-10-28: image/video generation, the separate Chat tab, the Coding studio.
- Local web app at http://127.0.0.1:8000 with a local access token. React + TypeScript with plain CSS; no new UI libraries without a reason.

## Brand Commitments

- Name: Ninja (app); Jarvis (assistant), addressed persona "sir".
- Dark interface. Jarvis surfaces use an Iron Man arc-reactor cyan accent (owner's choice).
- Must not look AI-generated or generic, and navigation must be easy. Not plain.

## Evidence on Hand

No screenshots, logos or brand assets beyond the existing app. No testimonials or metrics; do not invent any.

## Product Principles

1. Conversation first: Jarvis is a companion to talk with, and tasks happen inside that conversation.
2. Honest by default: show what actually ran; never imply an action that has no receipt.
3. Private and local: nothing leaves the PC unless the owner explicitly allows it.
4. Fast and calm: speed and clarity over spectacle; one obvious next action per screen.
5. Bilingual: Hindi (Devanagari), English and Hinglish read and sound natural everywhere.

## Accessibility & Inclusion

Mixed Devanagari and Latin text must stay legible at comfortable sizes. Respect reduced motion. Keyboard access and visible focus on every control.
