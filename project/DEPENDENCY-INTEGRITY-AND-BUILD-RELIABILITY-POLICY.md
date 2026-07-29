# 🛡️ ContextVault — Dependency Integrity & Build Reliability Policy

> **Version:** 1.0 (Frozen)

এই নীতিমালা ContextVault-এর সকল Development, GitHub Actions Build এবং Release Pipeline-এর জন্য বাধ্যতামূলক।

এর প্রধান উদ্দেশ্য হলো প্রতিটি Build যেন একই Dependency, একই Version এবং একই Build Configuration ব্যবহার করে নির্ভরযোগ্যভাবে সম্পন্ন হয়।

---

# 🎯 Primary Objective

Project-এর প্রতিটি Release অবশ্যই হতে হবে—

* Reproducible
* Stable
* Predictable
* Portable
* Production Ready

একই Source Code থেকে Local Build এবং GitHub Actions Build-এর ফলাফল যতটা সম্ভব একই হতে হবে।

---

# 🔒 Rule 1 — Official Dependencies Only

শুধুমাত্র Official Freeze করা Dependency ব্যবহার করা যাবে।

বর্তমান Official Third-party Package List—

* CustomTkinter
* Playwright
* Pillow
* BeautifulSoup4
* Markdownify
* Pydantic
* Tenacity

এই তালিকার বাইরে Dependency যোগ করা যাবে না, অনুমোদিত Specification Update ছাড়া।

---

# 🔒 Rule 2 — Locked Versions

GitHub Actions Release Build সর্বদা `requirements.lock` ব্যবহার করবে।

Development Environment `requirements.txt` ব্যবহার করতে পারে, কিন্তু Release Build কখনো Minimum Version Specification থেকে Install করবে না।

---

# 🔒 Rule 3 — Single Source of Truth

Dependency Version-এর Official Source হবে—

* requirements.lock
* pyproject.toml (Project Metadata)
* nuitka.toml (Build Configuration)

GitHub Workflow এই Configuration-গুলোর সাথে সামঞ্জস্য রেখে চলবে।

---

# 🔒 Rule 4 — Version Synchronization

নিচের Version-গুলো পরস্পরের সাথে সামঞ্জস্যপূর্ণ থাকতে হবে—

* Python Version
* Playwright Version
* CustomTkinter Version
* Nuitka Version
* GitHub Actions Python Version
* requirements.lock

Version পরিবর্তন করলে সংশ্লিষ্ট Configuration-ও Update করতে হবে।

---

# 🔒 Rule 5 — Deterministic Builds

একই Git Commit থেকে Build করলে—

* একই Dependency Version
* একই Compiler Configuration
* একই Output Structure

পাওয়া উচিত।

---

# 🔒 Rule 6 — CI Before Release

GitHub Release তৈরি হওয়ার আগে Pipeline সফলভাবে সম্পন্ন করবে—

* Source Checkout
* Python Setup
* Dependency Installation
* Dependency Validation
* Playwright Installation
* Chrome Availability Check (যদি Build Logic-এর অংশ হয়)
* Static Analysis (যদি সক্রিয় থাকে)
* Unit Tests (যদি উপস্থিত থাকে)
* Build
* Packaging
* ZIP Validation

কোনো ধাপে ব্যর্থ হলে Release প্রকাশ করা যাবে না।

---

# 🔒 Rule 7 — Dependency Validation

Build শুরু হওয়ার আগে যাচাই করতে হবে—

* সব Required Package Install হয়েছে।
* Version Lock মিলে।
* Missing Dependency নেই।
* Conflicting Dependency নেই।

---

# 🔒 Rule 8 — Runtime Integrity

OneDir Package-এর Runtime এমনভাবে তৈরি করতে হবে যাতে—

* কোনো Required Module অনুপস্থিত না থাকে।
* Required Resource Include হয়।
* Required Configuration Include হয়।
* Required Asset Include হয়।

Release Package Extract করার পর অতিরিক্ত Dependency Install করতে হবে না।

---

# 🔒 Rule 9 — GitHub Actions Reliability

GitHub Actions Workflow এমনভাবে তৈরি করতে হবে যাতে—

* নির্দিষ্ট Python Version ব্যবহার করে।
* Dependency Cache নিরাপদভাবে ব্যবহার করে।
* Lock File অনুযায়ী Install করে।
* Build Log সংরক্ষণ করে।
* Failure স্পষ্টভাবে Report করে।
* Partial Release তৈরি না করে।

---

# 🔒 Rule 10 — No Floating Release

Release Pipeline-এ Unpinned Dependency ব্যবহার করা যাবে না।

Release Build সর্বদা Locked Version ব্যবহার করবে।

---

# 🔒 Rule 11 — Compatibility First

নতুন Dependency অথবা Version Upgrade করার আগে নিশ্চিত করতে হবে—

* Windows Compatibility
* Nuitka Compatibility
* Playwright Compatibility
* CustomTkinter Compatibility
* GitHub Actions Compatibility

---

# 🔒 Rule 12 — Build Configuration Freeze

নিচের File-গুলো Release-এর সময় Official Configuration হিসেবে বিবেচিত হবে—

* requirements.lock
* pyproject.toml
* nuitka.toml
* GitHub Actions Workflow
* vibproject.ygit

Build System এই File-গুলোর সাথে অসামঞ্জস্যপূর্ণ Configuration ব্যবহার করবে না।

---

# 🔒 Rule 13 — No Hidden Downloads

Application Runtime চলাকালীন অতিরিক্ত Package Download করা যাবে না।

সমস্ত Required Runtime Component Build Package-এর অংশ হতে হবে অথবা Project Specification অনুযায়ী ব্যবহার করতে হবে।

---

# 🔒 Rule 14 — Release Verification

Release তৈরি হওয়ার পর অন্তত নিম্নলিখিত বিষয়গুলো যাচাই করতে হবে—

* ZIP Extract হয়।
* `ContextVault.exe` চালু হয়।
* UI Open হয়।
* Runtime Folder সঠিকভাবে Load হয়।
* Browser Automation Initialize হয়।
* কোনো Missing Module Error আসে না।
* কোনো Missing DLL বা Resource Error আসে না।

---

# 🔒 Rule 15 — Zero Build Error Policy

AI এমন Code লিখবে যাতে—

* GitHub Actions-এ Build Error না আসে।
* Dependency Conflict না হয়।
* Import Error না হয়।
* Version Mismatch না হয়।
* Missing Resource Error না হয়।
* Packaging Error না হয়।
* Release Failure না হয়।

যদি কোনো পরিবর্তনের ফলে Build Reliability ক্ষতিগ্রস্ত হওয়ার সম্ভাবনা থাকে, AI তা আগে স্পষ্টভাবে উল্লেখ করবে এবং সংশ্লিষ্ট Configuration Update ছাড়া পরিবর্তন বাস্তবায়ন করবে না।

---

# 🏁 Final Policy

ContextVault-এর প্রতিটি Commit, Pull Request এবং Release-এর লক্ষ্য হবে একটি **Reproducible, Deterministic এবং Production-ready Build** তৈরি করা।

কোনো Code, Dependency বা Configuration এমনভাবে পরিবর্তন করা যাবে না যাতে GitHub Actions Pipeline, Nuitka Build, Portable OneDir Distribution বা Release Package-এর স্থায়িত্ব ও নির্ভরযোগ্যতা ক্ষতিগ্রস্ত হয়।
