# 🤖 AI Personal Assistant & Floating Windows Dock

An intelligent Windows personal assistant that runs on your laptop, passively tracks your daily work across **Visual Studio Code, Antigravity IDE, Microsoft Teams, Chrome, Edge**, detects Teams meetings, reminds you of follow-up tasks until completed, generates structured **End-of-Day (EOD)** task summaries using **Google Gemini Pro / Flash**, pushes them directly to **Azure DevOps**, and surfaces contextual tech news and articles based on what you are working on.

---

## ✨ Features

1. **Active Window & Activity Tracking (100% Local & Fast)**
   - Uses native Windows Win32 APIs (`win32gui`, `psutil`) to track active applications and window titles.
   - Automatically tracks time spent on tasks and stores history in a local SQLite database (`assistant.db`).

2. **Microsoft Teams Call Detection & Smart Follow-up Reminders**
   - Automatically detects when a Microsoft Teams meeting or call starts and ends.
   - When a call finishes, a glassmorphic prompt appears asking: *"Did you get any action items from this meeting?"*
   - Sets persistent reminders (every 15m, 30m, or 1h) until you mark the task complete.

3. **End-of-Day (EOD) Task Synthesis with Gemini AI**
   - Aggregates hundreds of noisy window switches into 3 to 6 clean, professional work items.
   - Uses your **Free Gemini API Key** (from Google AI Studio) with `gemini-2.5-flash` or `gemini-1.5-flash`.
   - Includes automatic rule-based grouping if offline or if no API key is added yet.

4. **1-Click Azure DevOps Push**
   - Connects to Azure DevOps REST API via Personal Access Token (PAT).
   - Review, edit, select tasks in the dock, and click **"Push to Azure DevOps"** to create Work Items directly in your sprint backlog.

5. **Context-Aware Tech Radar & News Feed**
   - Automatically detects what tech stack or tools you are currently using (e.g. Python, React, Azure, Docker).
   - Fetches fresh articles, tutorials, and community discussions from Dev.to and Hacker News directly to your dock.

6. **Modern Floating Dock UI (React + Vite + Tailwind CSS)**
   - Frameless, translucent glassmorphism dock always on top of your windows.
   - Draggable anywhere on your screen.

---

## 🚀 How to Run

### Step 1: Launch the Assistant
Simply run:

```bash
python main.py
```

* This automatically starts the background tracker, Teams call detector, API server, and launches the **floating desktop dock**.
* To run in your default web browser instead of a native window, run:
  ```bash
  python main.py --browser
  ```

---

## ⚙️ Configuration (Gemini & Azure DevOps)

Click the **⚙️ Settings icon** on the dock:

1. **Gemini API Key (100% Free):**
   - Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
   - Click **"Create API Key"** and paste it into the settings.
2. **Azure DevOps:**
   - **Organization Name:** e.g. `YourCompany`
   - **Project Name:** e.g. `MyProject`
   - **Personal Access Token (PAT):** Create a PAT in Azure DevOps with `Work Items (Read & Write)` permission.
   - **Work Item Type:** `Task`, `User Story`, or `Issue`.

*(If you haven't entered Azure DevOps credentials yet, the app runs in **Local Mode**, allowing you to test everything without errors).*

---

## 🛠️ Testing Teams Call Flow
You don't need to wait for a real Teams meeting to test the reminder flow!
* Click the **"Simulate Call"** button on the dock to immediately trigger the meeting-ended prompt and test adding reminders!
