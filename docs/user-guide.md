# Ninja user guide

Ninja is a private assistant for Windows. Everything runs on your PC: the language model, speech recognition and Jarvis's voice. This guide covers installing it, the setup wizard and each screen. For what you can ask Jarvis, see the [Jarvis guide](jarvis-guide.md).

## Install

1. Download the latest **Ninja-x.y.z.zip** from [Releases](https://github.com/Karthik6146/Ninja-Assistant/releases/latest).
2. Unzip it somewhere permanent, for example `Documents\Ninja`. Ninja runs from this folder, so don't leave it in Downloads if you clean that folder.
3. Double-click **Install Ninja**. A window shows three steps:
   - **Python 3.11:** installed with winget if your PC doesn't have it.
   - **Ninja:** its Python packages are installed (a few minutes the first time).
   - **Shortcuts:** a **Ninja** shortcut is added to the Desktop and Start menu.
4. Ninja opens by itself and shows the setup wizard.

You need Windows 10 or 11 with winget, which current Windows includes. If the installer stops, it says why; fix that and run **Install Ninja** again. Finished steps are skipped.

## Setup wizard

The wizard opens on first start, and any time Ollama or a model is missing. Open it again from **Settings → AI model → Check PC and models**.

1. **Your PC** shows your processor, memory, graphics card and VRAM, and free disk space.
2. **Ollama, the model runner.** Press **Install Ollama** (or **Start Ollama** if it's installed but stopped). Ninja installs it with winget, which accepts Ollama's license for you.
3. **Choose a model.** Each model is rated for your PC:
   - **Fast:** fits entirely in your GPU's memory.
   - **Slow:** spills onto the CPU and RAM. It works, but replies take longer.
   - **Too big:** not enough memory or disk.

   The **Recommended** model is the largest one that runs fast. Press **Download** to install it; a progress bar shows the download, and the model is selected for Jarvis when it finishes.
4. **Voice (optional).** Press **Set up voice** to download about 1.5 GB of speech models: speech recognition, Jarvis's voice and the "Hey Jarvis" wake word.
5. Press **Start using Jarvis**. **Skip for now** closes the wizard without finishing.

| Your PC | Model the wizard picks |
|---|---|
| NVIDIA GPU, 8 GB or more | `qwen3.5:9b`, the model Ninja is tuned on |
| NVIDIA GPU, 6 GB | `qwen3.5:4b` |
| No dedicated GPU, 16 GB RAM | `qwen3.5:4b`, on the CPU |
| No dedicated GPU, 8 GB RAM | `qwen3.5:2b` |

## The tray icon

Ninja lives in the Windows notification area (the icons next to the clock).

- **Click** the icon to open the Ninja window, or bring it to the front.
- **Close the window** and Ninja keeps running in the background. Reminders and typed tasks still run; voice and the wake word need the window open.
- **Right-click** for the menu:
  - the server status and current model;
  - a GPU line: temperature, load, VRAM used and writing speed;
  - **Free GPU memory** unloads the model, for example before a game. The next message loads it again;
  - **Restart server** (shown when the tray started the server);
  - **Start with Windows** starts Ninja hidden in the tray when you sign in;
  - **Open data folder**;
  - **Quit Ninja** stops Ninja.

Opening the **Ninja** shortcut again while it runs just brings the window forward. The window signs in by itself; you never need the access token.

## Jarvis

The main screen is a conversation with Jarvis.

- **Type** in the box at the bottom and press **Enter** (Shift+Enter for a new line), or press the **microphone** to talk.
- **History** (top left) lists earlier conversations by day. **New conversation** starts a fresh one. **Private** starts a conversation that isn't saved, uses no tools and keeps no memory.
- **Today** (top right) is your task list for the day, with reminders.
- **Tokens** shows how much the model has read and written, per day, month and model.

The bar under the message box shows:

- the **model picker**: choose a model on this PC (with its VRAM use, and **Unload** for loaded ones) or a cloud model if you set one up;
- the **i** button: the model's size, quantization, context, memory use and measured speed, plus live GPU load and temperature;
- the **GPU chip**: temperature, load, VRAM and writing speed, refreshed every few seconds. It turns gold from 70 °C and red from 80 °C.

When Jarvis wants to do something risky, an **Allow once / Deny** card appears. Each action he takes shows a receipt of the tool that actually ran.

## Activity

**Activity** lists everything Jarvis has worked on, grouped by day, with filters: **All**, **Working**, **Done**, **Failed** and **Stopped**. Select a task to see what was asked, each step, how long it took and the result. **Saved files** lists reports and other files Jarvis created.

The **Activity** button on other screens opens the same details in a side panel.

## Settings

- **Setup and status:** one line each for local AI, cloud AI and file access, with **Refresh** and **Lock dashboard**.
- **AI model:** the model Jarvis uses, its live info card, **Check PC and models**, and how to add a cloud model.
- **What Jarvis may do:** switch each capability to **Allowed**, **Ask me first** or **Off**: checking the PC, opening apps, controlling media, finding files, reading email and messages, searching the web and more.
- **Memory:** facts Jarvis remembers. Add, correct or forget them.
- **Gmail accounts:** connect accounts for Jarvis to read (read-only).
- **System:** approved folders and advanced details (tools, audit log).
- **Workspaces:** a separate memory scope, for example one per client or project.

### Optional setup

- **Folders Jarvis may read and write:** set `NINJA_ROOTS` in the `.env` file in the Ninja folder (semicolon-separated), then restart from the tray.
- **Gmail:** create a Google Cloud project, enable the Gmail API, and add its OAuth Desktop client in **Settings → Gmail accounts**. In Google's testing mode, sign-ins expire after 7 days.
- **WhatsApp:** install WhatsApp Desktop from the Microsoft Store, link it to your phone and keep its notifications on with previews.
- **Cloud model:** set `CLOUD_ENABLED=true`, `CLOUD_URL`, `CLOUD_MODEL` and `CLOUD_API_KEY` in `.env`. Off by default; each run asks before sharing.

## Privacy

- Conversations, memory and settings are stored in the `data` folder inside the Ninja folder.
- Nothing you say or type goes to a cloud AI unless you set one up yourself.
- The internet is used for web research, weather, Gmail and downloads during setup.
- **Emergency stop** (bottom of the left rail) blocks new tasks and cancels running ones.

## Troubleshooting

| Problem | Fix |
|---|---|
| The installer says winget is missing | Install Python 3.11 from python.org, then run **Install Ninja** again |
| The wizard can't install Ollama | Install it from [ollama.com/download](https://ollama.com/download), then press **Start Ollama** |
| Replies are very slow | Pick a smaller model in the wizard, or check the **i** card: a model rated Slow runs partly on the CPU |
| "The model is busy" | Another reply is running; wait for it to finish |
| A game needs the GPU | Tray → **Free GPU memory** |
| The window shows a sign-in page | Open Ninja from its shortcut or tray icon, which signs in automatically |
| Something else | Tray → **Restart server**. Logs are in the `data` folder |

## Uninstall

1. Tray icon → **Quit Ninja**.
2. Turn off **Start with Windows** first if you turned it on, or delete `Ninja.lnk` from your Startup folder.
3. Delete the **Ninja** shortcuts from the Desktop and Start menu.
4. Delete the Ninja folder. This also deletes your conversations and memory.
5. Optionally uninstall Ollama and Python from **Windows Settings → Apps**.

## Creator tools

Studio (video editing, clip workflows, automations) and YouTube publishing are off in the public build. To turn them on, set `NINJA_CREATOR=1` in `.env` and restart. They are documented in the [workspace guide](workspace-guide.md), [Video Studio guide](video-guide.md) and [YouTube setup](youtube-automation.md).
