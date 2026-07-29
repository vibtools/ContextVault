
---

# 🖥️ ContextVault v1.0 — UI Design Freeze

## 🎯 Design Philosophy

ContextVault-এর UI হবে—

* Minimal
* Professional
* Responsive
* Fast
* Keyboard Friendly
* One Window
* One Click Workflow
* Non-Blocking
* Background Processing

---

# Window Size

Default

```text
Width : 1180 px

Height : 760 px
```

Minimum

```text
1000 × 680
```

Responsive হবে।

Window Resize করলে Layout Adjust হবে।

---

# Theme

Dark Only (v1)

```text
Background

#0F1117

Card

#161B22

Border

#242938

Primary

#3B82F6

Success

#22C55E

Warning

#F59E0B

Danger

#EF4444

Text

#F8FAFC

Muted

#94A3B8
```

---

# Layout

```text
┌─────────────────────────────────────────────────────────────┐
│ Toolbar                                                     │
├───────────────┬─────────────────────────────────────────────┤
│               │                                             │
│ Sidebar       │             Main Workspace                  │
│               │                                             │
│               │                                             │
│               │                                             │
├───────────────┼─────────────────────────────────────────────┤
│ Status        │ Progress / Logs                             │
└───────────────┴─────────────────────────────────────────────┘
```

---

# Sidebar

শুধু Navigation থাকবে।

```text
🏠 Dashboard

💬 Conversations

📦 Archives

📜 Export History

⚙ Settings

📋 Logs

ℹ About
```

---

# Dashboard

খুললেই Dashboard।

এখানে থাকবে

```text
Browser

Chrome

Status

Logged In

Conversations

285

Archive

190

Last Export

Today

Queue

2
```

---

# Conversation Page

সবচেয়ে গুরুত্বপূর্ণ Page।

```text
┌────────────────────────────────────┐

🔍 Search Conversation

────────────────────────────────────

☐ Python

☐ Playwright

☐ Docker

☐ Cloudflare

☐ n8n

☐ RAG

☐ ...

────────────────────────────────────

Export Selected

Export All

Refresh

└────────────────────────────────────┘
```

---

ডান পাশে

Conversation Preview

```text
Title

URL

Messages

Images

Code

Attachments

Estimated Size

Export
```

---

# Export Window

Export শুরু হলে

Popup হবে না।

বরং

Bottom Panel

```text
Exporting...

██████████░░░░░

55 %

Messages

120 / 240

Images

20 / 50

Files

5 / 12
```

সব Background Thread-এ চলবে।

---

# Archive Manager

```text
Playwright

View

Open Folder

Delete

Rebuild Summary
```

---

# Logs

```text
09:30

Conversation Loaded

09:31

Messages Extracted

09:32

Image Saved

09:33

Export Completed
```

---

# Settings

সব Control UI থেকেই।

---

## Browser

```text
Browser

Chrome

Edge

Brave

Opera

Firefox
```

---

## Browser Profile

```text
Select Folder

Open Folder

Reset Profile
```

---

## Export

```text
Default Folder

Archive Name

Auto Create Folder

Overwrite

Compress

Verify Export
```

---

## Assets

Checkbox

```text
☑ Images

☑ Code

☑ Tables

☑ Attachments

☑ Markdown

☑ JSON

☑ Summary

☑ Statistics

☑ Search Index
```

---

## Performance

```text
Worker Threads

1

2

4

8
```

---

Delay

```text
Auto

Fast

Normal

Safe
```

---

Memory

```text
Low

Balanced

High
```

---

# Status Bar

সবসময় Visible

```text
Browser

Connected

Worker

4

CPU

18 %

Memory

320 MB

Queue

3

Current

Exporting
```

---

# Thread Model

UI Thread

↓

Never Block

Worker Thread

↓

Export

↓

Worker Thread

↓

Images

↓

Worker Thread

↓

Files

↓

Worker Thread

↓

Summary

সব আলাদা Background Worker-এ চলবে।

UI কখনো Freeze করবে না।

---

# Notification

Top Right

```text
✔ Export Completed

✔ Images Downloaded

✔ Archive Created

⚠ Retry Required
```

---

# Right Click Menu

Conversation-এর উপর

```text
Export

Open

Copy URL

View Metadata

Refresh

Delete Archive
```

---

# Drag & Drop

Support থাকবে

Archive

↓

Drag

↓

Window

↓

Open

---

# Keyboard Shortcut

```text
Ctrl + F

Search

Ctrl + E

Export

Ctrl + A

Select All

Ctrl + R

Refresh

Ctrl + ,

Settings

F5

Reload

Esc

Cancel
```

---

# Performance Rules (Frozen)

* UI Thread কখনো I/O বা Browser Automation চালাবে না।
* Browser Automation, Parsing, Asset Download, Summary Generation এবং Archive Writing—সব Worker Thread-এ চলবে।
* UI শুধুমাত্র Progress, Status এবং User Interaction পরিচালনা করবে।
* Export চলাকালীন Window Drag, Resize, Scroll এবং Navigation স্বাভাবিক থাকবে।
* বড় Conversation (হাজারের বেশি Message) হলেও UI Responsive থাকবে।
* Progress Bar, Speed, ETA এবং বর্তমান Task Real-time Update হবে।

---

# 🏆 Final UI Philosophy

ContextVault-এর UI **"Small Window, Big Control"** নীতিতে তৈরি হবে।

এর মূল বৈশিষ্ট্য হবে:

* **একটি ছোট কিন্তু শক্তিশালী Desktop Window**
* **সব Feature UI থেকেই নিয়ন্ত্রণযোগ্য**
* **Background Threading-এর মাধ্যমে Zero UI Freeze**
* **Professional Developer Tool-এর মতো পরিষ্কার Layout**
* **নতুন ব্যবহারকারী ১–২ মিনিটের মধ্যেই ব্যবহার শুরু করতে পারবেন, আবার Power User-ও Advanced Control পাবেন কোনো অতিরিক্ত জটিলতা ছাড়াই।**
