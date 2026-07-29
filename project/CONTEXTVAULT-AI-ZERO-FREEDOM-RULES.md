# 🚨 ContextVault — AI Zero Freedom Rules

> **Version:** 1.0 (Frozen)

এই নীতিমালা ContextVault Project-এ কাজ করা সকল AI Coding Assistant-এর জন্য বাধ্যতামূলক।

এর উদ্দেশ্য হলো Project-এর অনুমোদিত Architecture, Technology এবং Scope অপরিবর্তিত রেখে Implementation সম্পন্ন করা।

---

# 🔒 Rule 1 — Architecture Is Frozen

AI কখনো Project Architecture পরিবর্তন করবে না।

পরিবর্তন করা যাবে না—

* Folder Structure
* Module Structure
* Build Pipeline
* Runtime Layout
* Archive Format
* UI Architecture
* Browser Architecture

---

# 🔒 Rule 2 — Technology Stack Is Frozen

AI পরিবর্তন করবে না—

* Python
* CustomTkinter
* Playwright
* Google Chrome
* Nuitka
* Official Dependency List

অন্য Framework বা Library-তে Migration করা যাবে না।

---

# 🔒 Rule 3 — Feature Freeze

AI—

* Feature Remove করবে না।
* Feature Rename করবে না।
* Feature Merge করবে না।
* Feature Split করবে না।
* অনুমোদন ছাড়া নতুন Feature যোগ করবে না।

শুধুমাত্র Freeze Specification অনুযায়ী Feature বাস্তবায়ন করবে।

---

# 🔒 Rule 4 — No Scope Expansion

AI Project-কে অন্য দিকে নিয়ে যাবে না।

যেমন—

* Web Version
* Mobile Version
* Cloud Version
* SaaS Version

যদি এগুলো v1 Scope-এর অংশ না হয়, তাহলে বাস্তবায়ন করবে না।

---

# 🔒 Rule 5 — No Framework Replacement

AI কখনো Suggest বা Implement করবে না—

* PyQt
* PySide
* Electron
* Kivy
* Selenium
* Puppeteer

Official Stack অপরিবর্তিত থাকবে।

---

# 🔒 Rule 6 — No Dependency Expansion

Official Dependency List-এর বাইরে নতুন Third-party Library যোগ করা যাবে না।

যদি সত্যিই প্রয়োজন হয়—

AI কারণ ব্যাখ্যা করবে এবং Recommendation হিসেবে উল্লেখ করবে, কিন্তু নিজে থেকে যুক্ত করবে না।

---

# 🔒 Rule 7 — Preserve Existing Behavior

Bug Fix করার সময়—

* বিদ্যমান Feature নষ্ট করা যাবে না।
* UI পরিবর্তন করা যাবে না।
* Existing Workflow ভাঙা যাবে না।

---

# 🔒 Rule 8 — Respect Background Architecture

Heavy Task কখনো UI Thread-এ চলবে না।

Background Worker Architecture বাধ্যতামূলক।

---

# 🔒 Rule 9 — Respect Documentation

নিচের Document-গুলো Source of Truth—

* PROJECT-OVERVIEW.md
* FEATURE-FREEZE-SPECIFICATION.md
* ARCHIVE-FORMAT-FREEZE-SPECIFICATION.md
* UI Technology Freeze
* Browser Technology Freeze
* Modules & Dependencies Freeze
* Build & Release Freeze

Code সবসময় এগুলোর সাথে সামঞ্জস্যপূর্ণ হতে হবে।

---

# 🔒 Rule 10 — No Silent Assumptions

Documentation-এ তথ্য না থাকলে—

* অনুমান করে Feature যোগ করা যাবে না।
* অনুমান করে Behavior পরিবর্তন করা যাবে না।

প্রয়োজনে Placeholder, `Not Implemented`, অথবা স্পষ্ট Recommendation ব্যবহার করা হবে।

---

# 🔒 Rule 11 — Production Quality Only

Generated Code হতে হবে—

* Production Ready
* Maintainable
* Modular
* Readable
* Thread Safe
* Portable
* Nuitka Compatible

---

# 🔒 Rule 12 — Preserve Portability

AI এমন Code লিখবে না যা—

* Portable Build নষ্ট করে।
* Windows Compatibility নষ্ট করে।
* GitHub Actions Build নষ্ট করে।
* OneDir Distribution নষ্ট করে।

---

# 🔒 Rule 13 — No Hidden Changes

AI কোনো Hidden Behavior যোগ করবে না।

যেমন—

* Background Service
* Telemetry
* Analytics
* Auto Update
* Network Call

যদি Specification-এ উল্লেখ না থাকে।

---

# 🔒 Rule 14 — Explain Before Breaking Rules

যদি কোনো পরিবর্তন Project-এর Freeze Rule ভাঙতে বাধ্য করে—

AI অবশ্যই—

1. কোন Rule ভাঙছে তা উল্লেখ করবে।
2. কেন ভাঙতে হচ্ছে তা ব্যাখ্যা করবে।
3. সম্ভাব্য প্রভাব জানাবে।
4. বিকল্প সমাধান থাকলে সেটিও প্রস্তাব করবে।

অনুমোদন ছাড়া সেই পরিবর্তন বাস্তবায়ন করবে না।

---

# 🔒 Rule 15 — Implementation Freedom Only

AI-এর স্বাধীনতা সীমাবদ্ধ থাকবে—

* Function Organization
* Internal Class Design
* Helper Methods
* Naming Convention
* Error Handling
* Code Optimization

যতক্ষণ পর্যন্ত এগুলো Freeze Specification-এর সাথে সাংঘর্ষিক না হয়।

---

# 🏁 Final Policy

ContextVault Project-এ AI-এর ভূমিকা হলো—

**Approved Specification বাস্তবায়ন করা।**

AI-এর ভূমিকা নয়—

* Project পুনরায় ডিজাইন করা।
* অনুমতি ছাড়া Scope পরিবর্তন করা।
* অনুমতি ছাড়া Technology পরিবর্তন করা।
* অনুমতি ছাড়া Architecture পরিবর্তন করা।

**Implementation-এ নমনীয়তা থাকবে, কিন্তু Architecture, Technology এবং Scope-এ নয়।**
