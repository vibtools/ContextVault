# 📦 ContextVault v1.0 — Archive Format Freeze Specification

> **Version:** 1.0 (Frozen)
>
> এই ডকুমেন্টে ContextVault-এর Archive Format, File Structure, Data Format এবং Storage Standard চূড়ান্তভাবে নির্ধারণ করা হয়েছে। ভবিষ্যতে যেকোনো LLM (ChatGPT, Gemini, Claude, DeepSeek, Grok, Local LLM ইত্যাদি) যেন সহজেই Archive বুঝতে পারে এবং একই Archive ভবিষ্যতে RAG Dataset হিসেবেও ব্যবহার করা যায়—সেই লক্ষ্যেই এই Format ডিজাইন করা হয়েছে।

---

# 🎯 মূল লক্ষ্য

ContextVault-এর Export Format এমন হবে যাতে—

* একটি Conversation-এর কোনো তথ্য হারিয়ে না যায়।
* AI সহজেই Conversation-এর Context বুঝতে পারে।
* ভবিষ্যতে যেকোনো LLM-এ ব্যবহার করা যায়।
* RAG Dataset হিসেবে সরাসরি ব্যবহার করা যায়।
* Human Readable হয়।
* Machine Readable হয়।
* Long-term Archive হিসেবে সংরক্ষণ করা যায়।

---

# 📁 Archive Structure (Frozen)

```text
ContextVault_Export/

│
├── manifest.json
├── metadata.json
├── conversation.json
├── conversation.md
├── summary.json
├── search-index.json
├── statistics.json
│
├── assets/
│   ├── code/
│   ├── images/
│   ├── attachments/
│   ├── tables/
│   └── citations/
│
├── rag/
│   ├── chunks.json
│   ├── documents.json
│   ├── keywords.json
│   └── chunk-map.json
│
└── logs/
    ├── export.log
    └── validation.log
```

---

# 📄 File 01 — manifest.json

## উদ্দেশ্য

এটি Archive-এর মূল Entry Point।

যেকোনো Software বা LLM প্রথমে এই File পড়বে।

এখানে থাকবে—

* Archive Version
* Archive Format Version
* Export Date
* Conversation ID
* Conversation Title
* File Mapping
* Folder Mapping
* Hash Information
* Validation Status

---

# 📄 File 02 — metadata.json

## উদ্দেশ্য

Conversation সম্পর্কিত সকল Metadata।

সংরক্ষণ করা হবে—

* Conversation Title
* Conversation URL
* Conversation ID
* Platform Name
* Export Date
* Created Date (যদি পাওয়া যায়)
* Language
* Total Messages
* User Messages
* Assistant Messages
* Character Count
* Word Count
* Estimated Token Count

---

# 📄 File 03 — conversation.json

## উদ্দেশ্য

এটি ContextVault-এর সবচেয়ে গুরুত্বপূর্ণ File।

Conversation-এর প্রতিটি Message এখানে সম্পূর্ণভাবে সংরক্ষণ করা হবে।

প্রতিটি Message-এর জন্য থাকবে—

* Message ID
* Parent Message ID
* Child Message ID (যদি থাকে)
* Sequence Number
* Role
* Plain Text
* Markdown
* HTML
* Code Reference
* Image Reference
* Attachment Reference
* Table Reference
* Citation Reference
* Timestamp (যদি পাওয়া যায়)
* Character Count
* Word Count

এই File হবে **Lossless Conversation Data**।

---

# 📄 File 04 — conversation.md

## উদ্দেশ্য

LLM-দের দ্রুত পড়ার জন্য একটি Human Friendly Markdown Version।

এখানে Conversation থাকবে ধারাবাহিকভাবে—

```text
User

↓

Assistant

↓

User

↓

Assistant
```

কোনো JSON Structure থাকবে না।

শুধু Conversation Flow থাকবে।

এটি ChatGPT, Gemini, Claude সহ অন্যান্য LLM-এর জন্য Context বুঝতে সবচেয়ে সহজ Format।

---

# 📄 File 05 — summary.json

Automation শেষে তৈরি হবে—

* Short Summary
* Long Summary
* Main Topics
* Keywords
* Important Decisions
* TODO List
* Mentioned Technologies
* Mentioned Libraries
* Mentioned URLs
* Mentioned Files

---

# 📄 File 06 — search-index.json

Conversation Search-এর জন্য—

* Keywords
* Topics
* Important Terms
* Entity Mapping
* Message Mapping

---

# 📄 File 07 — statistics.json

Conversation Statistics—

* Total Messages
* User Messages
* Assistant Messages
* Images
* Attachments
* Code Blocks
* Tables
* Citations
* Total Characters
* Total Words
* Estimated Tokens

---

# 📂 assets/

Conversation-এর সকল Asset এখানে সংরক্ষণ হবে।

---

## code/

প্রতিটি Code Block আলাদা File হিসেবে সংরক্ষণ হবে।

যেমন—

```text
code/

001.py

002.js

003.html

004.json
```

Conversation File শুধুমাত্র Reference রাখবে।

---

## images/

Conversation-এর সকল Image।

```text
images/

0001.webp

0002.png

0003.jpg
```

---

## attachments/

Conversation-এর সকল File।

```text
attachments/

manual.pdf

source.zip

data.csv
```

---

## tables/

Conversation-এর Table

* HTML
* Markdown
* JSON

---

## citations/

Conversation-এ ব্যবহৃত Reference বা Citation-এর Structured Copy।

---

# 📂 rag/

এই Folder ভবিষ্যতের RAG-এর জন্য সংরক্ষিত থাকবে।

---

## chunks.json

Conversation Logical Chunk-এ ভাগ করা হবে।

প্রতিটি Chunk—

* Context অনুযায়ী
* Topic অনুযায়ী
* Message অনুযায়ী

---

## documents.json

RAG-এর Document Structure।

---

## keywords.json

Conversation থেকে তৈরি Keyword Index।

---

## chunk-map.json

কোন Message কোন Chunk-এ আছে তার Mapping।

---

# 📂 logs/

Automation সম্পর্কিত Log।

* Export Log
* Validation Log

---

# 📌 Conversation Storage Standard

Conversation কখনো একটি বড় Text হিসেবে সংরক্ষণ করা হবে না।

বরং—

```text
Conversation

    │

    ├── Metadata

    ├── Messages

    ├── Assets

    ├── References

    ├── Summary

    ├── Search Index

    ├── Statistics

    └── RAG Structure
```

---

# 📌 Message Storage Standard

প্রতিটি Message হবে একটি Self-Contained Object।

প্রতিটি Message নিজের সাথে নিজের সমস্ত তথ্য বহন করবে।

অর্থাৎ—

* Text
* Markdown
* HTML
* Code
* Images
* Attachments
* Tables
* Metadata
* Statistics

সব একই Message-এর সাথে সংযুক্ত থাকবে।

---

# 📌 Archive Quality Standard

প্রতিটি Export অবশ্যই হবে—

* Lossless
* Portable
* Human Readable
* Machine Readable
* LLM Readable
* RAG Ready
* Version Controlled
* Future Compatible

---

# 📌 LLM Compatibility Standard

Archive এমনভাবে তৈরি করা হবে যাতে ভবিষ্যতে—

* ChatGPT
* Gemini
* Claude
* Grok
* DeepSeek
* OpenRouter
* Ollama
* Local LLM

সহ যেকোনো আধুনিক LLM সহজেই Conversation-এর সম্পূর্ণ Context বুঝতে পারে।

এজন্য Archive-এ থাকবে—

* Structured JSON
* Human Friendly Markdown
* Metadata
* Summary
* Asset Reference
* Conversation Flow
* Search Index
* Topic Information

---

# 📌 RAG Compatibility Standard

ContextVault Export ভবিষ্যতে কোনো অতিরিক্ত Conversion ছাড়াই RAG Pipeline-এ ব্যবহার করা যাবে।

Archive-এ পূর্ব থেকেই থাকবে—

* Document Structure
* Chunk Structure
* Metadata
* Search Index
* Topic Mapping
* Keyword Mapping
* Conversation Mapping

ফলে Embedding তৈরি করা এবং Vector Database-এ Import করা অনেক সহজ হবে।

---

# 🔒 Archive Format Freeze Rules

ContextVault v1.0-এ—

* Archive Folder Structure পরিবর্তন করা হবে না।
* File Name পরিবর্তন করা হবে না।
* JSON Schema ভাঙা হবে না।
* Manifest বাধ্যতামূলক থাকবে।
* Conversation.md বাধ্যতামূলক থাকবে।
* Raw JSON এবং Markdown—দুই ধরনের Export-ই থাকবে।
* সকল Asset Conversation-এর বাইরে আলাদা Folder-এ সংরক্ষণ হবে এবং Conversation File শুধুমাত্র তাদের Reference বহন করবে।

---

# 🏁 Final Freeze Statement

**ContextVault v1.0 Archive Format Freeze কার্যকর।**

এই Archive Format-এর মূল উদ্দেশ্য হলো একটি AI Conversation-কে এমনভাবে সংরক্ষণ করা, যাতে সেটি শুধুমাত্র Backup হিসেবে নয়, বরং ভবিষ্যতের যেকোনো LLM-এর জন্য একটি পূর্ণাঙ্গ Context Package এবং RAG-Ready Knowledge Archive হিসেবে ব্যবহার করা যায়।

এই Format-ই ContextVault v1.0-এর একমাত্র অফিসিয়াল Export Standard হিসেবে বিবেচিত হবে।
