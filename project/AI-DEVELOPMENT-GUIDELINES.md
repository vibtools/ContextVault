# 🤖 ContextVault — AI Development Guidelines

> **Version:** 1.0 (Frozen)

এই ডকুমেন্টটি ContextVault Project-এ কাজ করা সকল AI Coding Assistant-এর জন্য বাধ্যতামূলক Development Guideline।

এটি ChatGPT, Codex, Claude, Gemini, DeepSeek, GitHub Copilot বা অন্য যেকোনো AI Coding Tool-এর ক্ষেত্রে সমানভাবে প্রযোজ্য।

---

# 🎯 Primary Objective

AI-এর প্রধান দায়িত্ব হলো ContextVault-এর বিদ্যমান Architecture অনুসরণ করে Production-ready Code তৈরি করা।

AI নতুন Architecture তৈরি করবে না।

AI Project-এর Scope পরিবর্তন করবে না।

AI অনুমান করে Feature যোগ করবে না।

---

# 🧩 Architecture First

Code লেখার আগে AI অবশ্যই Project Documentation পড়বে।

অন্তত নিচের Document-গুলোকে Source of Truth হিসেবে বিবেচনা করবে—

* PROJECT-OVERVIEW.md
* FEATURE-FREEZE-SPECIFICATION.md
* ARCHIVE-FORMAT-FREEZE-SPECIFICATION.md
* CONTEXTVAULT-OFFICIAL-UI-TECHNOLOGY-FREEZE.md
* CONTEXTVAULT-BROWSER-AUTOMATION-TECHNOLOGY-FREEZE.md
* CONTEXTVAULT-OFFICIAL-MODULES-AND-DEPENDENCIES-FREEZE.md
* CONTEXTVAULT-BUILD-AND-RELEASE-PIPELINE-FREEZE.md

---

# 🔒 Respect Frozen Decisions

AI কখনো—

* UI Framework পরিবর্তন করবে না।
* Browser Engine পরিবর্তন করবে না।
* Build System পরিবর্তন করবে না।
* Module পরিবর্তন করবে না।
* Archive Format পরিবর্তন করবে না।
* Folder Structure পরিবর্তন করবে না।

যদি কোনো পরিবর্তন প্রয়োজন হয়, সেটি Recommendation হিসেবে উল্লেখ করবে, সরাসরি বাস্তবায়ন করবে না।

---

# 🧱 Development Philosophy

AI সর্বদা—

* Production-ready Code লিখবে।
* Readable Code লিখবে।
* Maintainable Code লিখবে।
* Modular Code লিখবে।
* Reusable Code লিখবে।
* Testable Code লিখবে।

---

# 🐍 Python Standards

* Python 3.12+ Target করতে হবে।
* Type Hint ব্যবহার করতে হবে।
* Dataclass অথবা Pydantic Model ব্যবহার করতে হবে যেখানে উপযুক্ত।
* Magic Number এড়াতে হবে।
* Hardcoded Path ব্যবহার করা যাবে না।
* pathlib ব্যবহার করতে হবে।

---

# 🖥 UI Standards

Official UI

* CustomTkinter

AI কখনো—

* PyQt Suggest করবে না।
* PySide Suggest করবে না।
* Kivy Suggest করবে না।
* Electron Suggest করবে না।

UI Thread-এ Heavy Task রাখা যাবে না।

---

# ⚙ Background Processing

Heavy Task সর্বদা Worker-এ চলবে।

Official Technology

* threading
* ThreadPoolExecutor
* asyncio
* queue

UI Thread শুধুমাত্র—

* Screen Update
* User Interaction
* Progress
* Notification

পরিচালনা করবে।

---

# 🌐 Browser Automation

Official Browser Automation

* Playwright

Official Browser

* Google Chrome Stable

AI কখনো—

* Selenium-এ Migration করবে না।
* Playwright Chromium-এ Switch করবে না।
* Firefox ভিত্তিক Solution দেবে না।
* Edge ভিত্তিক Solution দেবে না।

Automation সর্বদা Existing Chrome Profile ব্যবহার করবে।

---

# 📦 Dependency Rules

AI নতুন Third-party Library যোগ করবে না।

Official Library List-এর বাইরে Dependency যোগ করার আগে কারণ ব্যাখ্যা করবে।

Python Standard Library অগ্রাধিকার পাবে।

---

# 📂 Folder Rules

AI নতুন Folder তৈরি করবে না যদি বর্তমান Structure যথেষ্ট হয়।

File অবশ্যই সঠিক Module অনুযায়ী থাকবে।

---

# 📝 Documentation

নতুন Feature যুক্ত হলে Documentation Update করতে হবে।

যদি কোনো Public API পরিবর্তন হয়—

README

Docs

Example

সব Update করতে হবে।

---

# 🧪 Error Handling

AI কখনো Silent Exception লিখবে না।

সব Exception—

* Logged হবে।
* User Friendly Message থাকবে।
* Debug Information থাকবে (যেখানে উপযুক্ত)।

---

# 🚫 Code Quality

AI কখনো—

* Duplicate Code লিখবে না।
* Dead Code রেখে যাবে না।
* Unused Import রাখবে না।
* Temporary Hack রেখে যাবে না।
* TODO লিখে Feature অসম্পূর্ণ রাখবে না।

---

# ⚡ Performance

Code হতে হবে—

* Fast
* Memory Efficient
* Responsive

Large Conversation Support বাধ্যতামূলক।

---

# 🔄 Thread Safety

সব Shared State Thread-safe হতে হবে।

UI Update শুধুমাত্র UI Thread থেকে করা যাবে।

---

# 📦 Build Compatibility

Code অবশ্যই—

* Nuitka Compatible
* Portable Compatible
* Windows Compatible

হতে হবে।

---

# 🧩 Coding Style

AI ব্যবহার করবে—

* Meaningful Function Name
* Meaningful Variable Name
* Small Function
* Single Responsibility Principle
* Clear Separation of Concerns

---

# 🧠 AI Decision Rules

AI যদি Documentation এবং User Request-এর মধ্যে দ্বন্দ্ব দেখে—

Documentation-কে অগ্রাধিকার দেবে।

যদি Documentation অসম্পূর্ণ হয়—

AI অনুমান না করে Clarification চাইবে অথবা সীমাবদ্ধতা উল্লেখ করবে।

---

# 🔍 Before Writing Code

AI নিজেকে অন্তত এই প্রশ্নগুলো করবে—

* এটি কি Freeze Specification অনুসরণ করছে?
* এটি কি বর্তমান Architecture ভাঙছে?
* এটি কি নতুন Dependency যোগ করছে?
* এটি কি UI Freeze করতে পারে?
* এটি কি Portable Build নষ্ট করতে পারে?
* এটি কি ভবিষ্যৎ Maintenance কঠিন করবে?

যদি কোনো প্রশ্নের উত্তর "হ্যাঁ" হয়, তাহলে AI আগে সতর্ক করবে।

---

# ❌ Never Do

AI কখনো—

* Architecture Rewrite করবে না।
* Framework Replace করবে না।
* Project Scope পরিবর্তন করবে না।
* Unapproved Feature যোগ করবে না।
* Existing Feature Remove করবে না।
* Frozen Decision উপেক্ষা করবে না।

---

# 🏁 Final Development Rule

ContextVault-এর সকল Development **Specification-driven Development** অনুসরণ করবে।

AI-এর কাজ হলো Project Specification বাস্তবায়ন করা—Project Specification পুনর্নির্ধারণ করা নয়।

Project-এর প্রতিটি Code, Module এবং Feature বিদ্যমান Freeze Specification-এর সাথে সামঞ্জস্যপূর্ণ হতে হবে।
