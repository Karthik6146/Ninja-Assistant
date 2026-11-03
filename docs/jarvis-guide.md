# Jarvis guide

Jarvis is Ninja's assistant: a calm British butler with a dry wit who calls you "sir". Ask him anything, or ask him to do something on your PC. He understands English, Hindi and Hinglish, even mixed in one sentence. Installing and the screens are covered in the [user guide](user-guide.md).

## Talking to Jarvis

**Type** in the message box and press **Enter**, or press the **microphone** to talk.

General questions get a direct answer. When a request needs a tool, Jarvis runs it and the reply shows a receipt of what actually ran, for example "✓ Opened VLC". A reply without a receipt did not do anything on your PC. If a requested action failed or couldn't be verified, the reply says so.

- **Follow-ups** keep the context: "What is an API?", then "give me a simple example".
- **New conversation** in **History** starts fresh. Earlier conversations are listed by day.
- **Private** starts a conversation that isn't saved, uses no tools and doesn't read memory.
- **Reply language:** say "Speak in English", "Hindi mein bolo" or "Hinglish mein baat karo". The choice holds for the rest of the conversation.

## Your PC

Windows must be unlocked.

| Say | What happens |
|---|---|
| "Open Chrome", "VLC kholo", "Open Bluetooth settings" | Opens any Start-menu app or a Settings page |
| "Open github.com" | Opens the site in your default browser (https only) |
| "Pause the music", "Next song", "Volume thoda badhao", "Mute" | Media and volume (about 2% per step) |
| "Find my Valorant clip", then "open the first one" | Searches file names in Desktop, Documents, Downloads, Videos, Pictures and Music, including OneDrive |
| "Check CPU and memory" | Live CPU, memory and disk use |
| "What's on my screen?", "Read this error" | Looks at your screen and answers about it |
| "Summarise what I copied", "Copy that" | Reads or sets the clipboard |

Jarvis never opens shells or admin tools (PowerShell, Command Prompt, Terminal, Registry Editor, WSL), and never opens programs, scripts or shortcuts as files: only documents, images, audio, video and subtitles.

## Research and weather

- **Weather:** "Noida ka mausam kaisa hai?", "Will it rain in Delhi tomorrow?" Current conditions and a three-day forecast from Open-Meteo.
- **Research:** "Research the best microphones under ₹5000", "GTA 6 ki latest news kya hai?" Jarvis searches the web, reads up to three pages and answers with numbered sources [1] [2]. Pages he couldn't read are listed, never cited.
- **Web pages:** "Read this article: https://…" reads a page you give him. He only opens links that you or a search result provided; if he would invent an address, he searches instead.
- **Videos:** "Watch this video and summarise it" with a YouTube link or a file Jarvis found. This needs FFmpeg installed and on PATH (for example `winget install Gyan.FFmpeg`), plus voice set up for what is said in the video.

## Email and WhatsApp (read-only)

- **Gmail:** "Any new emails?", "mail aaya kya?", "Did Amazon email me this week?" Jarvis lists unread or matching mail across your connected accounts and can read one message to summarise it. He can't send, delete or archive mail. Connect accounts in **Settings → Gmail accounts**; in Google's testing mode, sign-ins expire after 7 days, and Jarvis tells you when to reconnect.
- **WhatsApp:** "Any WhatsApp messages?", "Rahul ne kya bola?" Jarvis reads the notifications WhatsApp Desktop shows. While Ninja runs it keeps new ones for 7 days, because WhatsApp clears a notification once you read the chat on your phone. He only knows what a notification showed: no older history, no media, nothing from muted chats or from when Ninja was closed. He can't send messages.

## Reminders, tasks, notes and memory

- **Reminders:** "Remind me tomorrow at 7 PM to call mom." When one falls due you get a Windows notification, and Jarvis shows it in the chat and says it aloud.
- **Today list:** "What are today's tasks?", "Add a task to pay the electricity bill." Also in the **Today** drawer.
- **Notes:** "Note down that the wifi password is on the router", then later "What did I note about the wifi?"
- **Memory:** "Remember that I prefer short answers." "What do you remember about my work?" Manage memories in **Settings → Memory**: add, correct, forget or export them. Corrected facts replace the old ones.

## Files in approved folders

Jarvis can read, list and edit text files only inside folders you approve with `NINJA_ROOTS` in `.env`. Small `.txt` and `.md` edits are written as a separate `.jarvis-…` copy beside the original, which stays untouched; ask him to undo an edit to remove the copy. "Find the largest files in my Downloads" works inside approved folders too.

## Permissions and confirmations

**Settings → What Jarvis may do** has a switch for each capability: **Allowed**, **Ask me first** or **Off**. Jarvis can't grant himself permissions. Spending money, security changes and unrestricted shell commands aren't available at all.

Emails, web pages and messages are written by other people and can contain instructions aimed at Jarvis. So once he has read email, WhatsApp, web text or a document in a conversation, every action in that conversation (open an app, set a reminder, change a file…) waits for an **Allow once / Deny** card. Reading stays free. Saying a new request instead of answering the card declines it.

## Voice

Set up voice once in the setup wizard (**Settings → AI model → Check PC and models → Set up voice**). Then press the **microphone** in the message box and allow microphone access.

- **Just talk.** A local listener decides when you've finished a sentence, so short pauses are fine. Jarvis starts speaking with a short opener, such as "Of course, sir.", while the rest of the reply is still being written.
- **Talk over him.** What you say while he speaks is kept and answered when he finishes. "Stop", "ruko" or "bas karo" interrupt him at once; so does the **Interrupt** button.
- **"Hey Jarvis".** Turn on **Wake word** in **Voice settings**. Jarvis then waits for "Hey Jarvis …", for example "Hey Jarvis, open Calculator". Speech without the wake word is discarded on your PC, never transcribed or saved. After 25 seconds of silence he returns to standby.
- **Voice settings** also choose Jarvis's voice and the reply language. **Read the last reply again** repeats it.
- Say "that's all", "thank you" or "bas" to end the conversation.

Recognition runs on your GPU and falls back to the CPU. Jarvis's voice is Kokoro (British English, with a Hindi voice for Hindi sentences). Recordings are processed locally and deleted. Headphones help if Jarvis hears himself through your speakers. Uncertain speech is not sent: Jarvis asks you to repeat. Check names and numbers in what he heard, and correct him by speaking or typing again.

The "Hey Jarvis" wake-word model is licensed for personal, non-commercial use only.

## Speed

The first reply after starting loads the model and is slower; later replies reuse it. The **i** button next to the model picker shows the model's measured speed, and the GPU chip shows live writing speed. On an RTX 4060 the recommended `qwen3.5:9b` writes about 38 tokens a second and a voice reply starts about 2.5 s after you stop talking. Smaller models are faster but make more mistakes picking tools.

## Limits

- A local model makes mistakes, more so the smaller ones. Trust the receipts, not the wording.
- Jarvis can't work while your PC is off or asleep; reminders due then are announced when Ninja runs again.
- Reddit isn't available: it blocks anonymous access.
- In the creator build (`NINJA_CREATOR=1`), Jarvis can also list, start and change Studio video workflows.
