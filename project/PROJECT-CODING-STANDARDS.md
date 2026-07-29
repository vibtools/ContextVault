# 📐 ContextVault — Project Coding Standards

> **Version:** 1.0 (Frozen)

This document defines the official coding standards for the ContextVault project.

Every source file, module, class, function and commit must follow these standards.

These rules apply equally to:

* Human Developers
* AI Coding Assistants
* GitHub Copilot
* ChatGPT
* Codex
* Claude
* Gemini
* DeepSeek

---

# 🎯 Primary Goal

Write code that is

* Production Ready
* Readable
* Predictable
* Maintainable
* Testable
* Reusable
* Thread Safe
* Portable

Code should optimize for long-term maintenance instead of short-term convenience.

---

# 🐍 Python Version

Official Version

```text
Python 3.12+
```

Never write code targeting an older Python version.

---

# 📁 Project Structure

Every file must remain inside the approved project structure.

Never create random folders.

Never duplicate modules.

Always place code in the correct package.

---

# 📂 File Naming

Use lowercase.

Use snake_case.

Examples

```text
browser_manager.py

archive_writer.py

thread_manager.py

conversation_parser.py

settings_manager.py
```

Avoid

```text
Browser.py

MyFile.py

ParserFINAL.py

temp.py

newfile.py
```

---

# 🏛 Class Naming

Use PascalCase.

Examples

```python
class BrowserManager:

class ArchiveWriter:

class ThreadManager:

class ConversationParser:
```

Never use

```python
class browser:

class manager:

class helper:
```

---

# 🔧 Function Naming

Use snake_case.

Functions should describe exactly what they do.

Examples

```python
load_browser_profile()

export_conversation()

create_archive()

parse_messages()

download_images()

save_metadata()
```

Avoid

```python
run()

go()

work()

test()

new()

temp()
```

---

# 📦 Variable Naming

Variable names must be meaningful.

Good

```python
conversation_count

archive_path

browser_profile

export_queue

current_progress
```

Bad

```python
x

temp

obj

abc

value1
```

---

# 🔒 Constants

Never hardcode values.

Store constants in dedicated modules.

Example

```python
DEFAULT_TIMEOUT

MAX_EXPORT_THREADS

SUPPORTED_IMAGE_TYPES

APPLICATION_NAME
```

---

# 📄 Type Hints

Public functions must include type hints.

Example

```python
def export_archive(
    conversation: Conversation
) -> Path:
```

Avoid untyped public APIs.

---

# 🧩 Dataclasses & Models

Use

* dataclass
* Pydantic

for structured data.

Avoid passing large dictionaries between modules.

---

# 📚 Imports

Standard Library

↓

Third-party Libraries

↓

Project Modules

Example

```python
from pathlib import Path
import logging

from playwright.async_api import async_playwright

from src.core.browser import BrowserManager
```

Never use wildcard imports.

Reject

```python
from module import *
```

---

# 📏 Function Size

One function should perform one responsibility.

Recommended

20–40 lines

Acceptable

Up to 75 lines

If larger

Split into smaller functions.

---

# 🏛 Class Size

One class should represent one responsibility.

Avoid "God Classes".

Large classes should be divided into focused components.

---

# 🔄 Duplicate Code

Do not duplicate logic.

If logic appears twice,

extract it into a reusable function.

---

# 🧱 Separation of Concerns

Never mix

* UI
* Business Logic
* Browser Automation
* Archive Logic
* File Operations

inside one class.

Every layer has a single responsibility.

---

# ⚙ UI Rules

UI code must

* update widgets
* collect user input
* display progress

UI must never

* parse conversations
* download files
* perform browser automation
* execute heavy processing

---

# 🧵 Threading Rules

Heavy work belongs only in Worker Threads.

UI Thread must remain responsive.

Never block the UI.

Use the approved architecture.

UI

↓

Queue

↓

ThreadPoolExecutor

↓

Worker

↓

Playwright

---

# 🌐 Browser Rules

Browser logic belongs only inside browser modules.

Never spread Playwright calls throughout the project.

Use centralized browser management.

---

# 📂 File System

Always use

```python
pathlib.Path
```

Never build paths manually.

Avoid

```python
"C:\\Users\\..."
```

Always use relative project paths.

---

# 📝 Logging

Never use print() for production code.

Use

```python
logging
```

Every important operation should be logged.

Log levels

* DEBUG
* INFO
* WARNING
* ERROR
* CRITICAL

---

# ❌ Exception Handling

Never write

```python
except:
    pass
```

Always catch specific exceptions.

Log failures.

Return meaningful errors.

---

# 🔁 Retry Logic

Never implement manual retry loops.

Use

Tenacity

for approved retry behavior.

---

# 📦 Dependencies

Use only officially approved libraries.

Never introduce unofficial dependencies.

Prefer the Python Standard Library whenever practical.

---

# 🔐 Security

Never hardcode

* passwords
* API keys
* tokens
* secrets

Never trust user input.

Validate all external data.

---

# ⚡ Performance

Avoid

* unnecessary loops
* duplicate parsing
* repeated file reads
* repeated browser launches

Reuse existing objects where appropriate.

---

# 🧠 Memory

Release resources promptly.

Close

* files
* browser contexts
* pages
* streams

Avoid retaining large objects unnecessarily.

---

# 📖 Documentation

Every public

* class
* function
* module

should have concise documentation when the purpose is not obvious.

Keep comments focused on *why*, not *what*.

---

# 🧪 Testing

Every new feature should be testable.

Avoid tightly coupled code.

Design modules with testing in mind.

---

# 🏗 Build Compatibility

Generated code must remain compatible with

* GitHub Actions
* Nuitka
* Portable OneDir Distribution

Never rely on

* developer-specific paths
* local configuration
* manually installed runtime files

---

# 📋 Code Review Checklist

Before submitting code verify

* Naming follows standards
* Imports are clean
* Type hints exist
* No duplicate code
* No dead code
* No wildcard imports
* No silent exceptions
* Thread safety preserved
* UI remains responsive
* Build compatibility preserved

---

# 🚫 Never Do

Never

* commit commented-out production code
* leave TODOs for required functionality
* bypass architecture
* bypass threading rules
* hardcode file paths
* hardcode secrets
* suppress exceptions silently
* introduce unnecessary abstractions
* introduce unnecessary dependencies

---

# 🤖 AI Requirements

AI-generated code must

* follow all frozen specifications
* respect project architecture
* preserve build reliability
* preserve runtime compatibility
* preserve GitHub Actions compatibility
* preserve Nuitka compatibility

AI must optimize implementation—not redesign the project.

---

# 🏁 Final Standard

Every line of code added to ContextVault must improve one or more of the following without reducing any other:

* Reliability
* Readability
* Maintainability
* Performance
* Portability
* Build Stability
* Long-term Sustainability

If a proposed change conflicts with these standards or any frozen project specification, the change must not be merged until it is corrected.
