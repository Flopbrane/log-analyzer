# Info Logger

![version](https://img.shields.io/badge/version-v0.9.9-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![stars](https://img.shields.io/github/stars/Flopbrane/log-analyzer?style=social)
> ⚠ Requires Python 3.9 or higher

🚀 A powerful logging system that turns logs into **debuggable events**

> Not just logs — this is a **diagnostic system**.

---

## ✨ Current Status: Ver.0.9.9

Ver.0.9.9 is a near-complete pre-1.0 release.

- `query_engine/` is now treated as the independent TraceQL/query core inside this project.
- Logger/UI code reaches the query core only through `logs/traceql_bridge.py`.
- Query syntax errors are preserved as diagnosable events instead of crashing the Viewer.
- `QUERY ERROR` reports include query text, caret position, expected syntax, and dictionary-based suggestions.
- Timezone display uses UTC internally and local-time rendering in the Viewer, with `tzdata` version tracking.
- Runtime log files and local editor files are excluded from Git tracking.

---

## ✨ What’s Included

- Structured Logging
- Event Analysis
- Japanese / English GUI Viewer
- TraceQL-powered search bridge
- SQLite-backed document adapter for large logs
- Query error suggestions without requiring AI
- tzdata update helper for local-time display accuracy

---

<img src="docs/image/main_window.png" alt="Log Viewer Main Window" width="900">

## 🔍 Detail View

<img src="docs/image/sub_window.png" alt="Log Viewer Sub Window" width="600">

Info Logger is a **structured logging + analysis + GUI viewer tool**  
designed to make debugging faster, clearer, and more intuitive.  

- For Japanese version → README_jp.md

---

## 🚀 What is this?

Designed to make debugging faster, clearer, and more intuitive.

Most loggers only *record logs*.

Info Logger goes further by:

- ✅ Recording logs as structured data (JSON Lines)
- ✅ Converting logs into analyzable events
- ✅ Providing a GUI for instant inspection

👉 Logs are not just outputs — they are **system events**.

---

## 💡 Why Info Logger?

### 🚀 What makes this different?

⭐ Most loggers:  

- ❌ Only record logs

⭐ Info Logger:

- ⭕ Treats logs as structured data (JSON Lines)
- ⭕ Turns logs into **debuggable events**
- ⭕ Reveals **intent vs actual results**
- ⭕ Detects **hidden and silent failures**

## ✨ Features

- 🔍 **Trace-based tracking**
  - Track execution flow using `trace_id`

- 📍 **Automatic location detection**
  - File / line / function captured automatically

- 🧠 **Event analysis**
  - ERROR / CRITICAL detection
  - Trace jumps
  - System reboot detection

- 🖥️ **GUI Viewer**
  - View logs instantly
  - Filter by type / trace_id
  - Inspect raw JSON
  - Japanese / English display support

- 🕒 **Timezone handling**
  - Internal: UTC
  - Display: Local time selected in the Viewer
  - `logs/.tzdata_ver_reference` records the checked `year:tzdata-version`
  - `python -m logs.update_tzdata` can update timezone data explicitly

- 🔎 **TraceQL bridge**
  - Advanced query matching is routed through `logs/traceql_bridge.py`
  - Logger/UI code does not import `query_engine` directly
  - Log records are converted to TraceQL documents at the bridge boundary

- 🧭 **Query error reports**
  - Syntax errors are shown as `QUERY ERROR` reports
  - Caret position is displayed when available
  - Dictionary-based suggestions are generated from `logs/error_response_dict.py`

- 🗄️ **SQLite adapter**
  - Store generic TraceQL documents in SQLite
  - Search large log sets in batches
  - Useful when JSONL logs grow to hundreds of MB or several GB

---

## ⚡ Quick Start

### 1. Install (local)

```bash
git clone https://github.com/Flopbrane/log-analyzer.git

cd log-analyzer
```

---

### 2. Basic Usage

```python
from logs.log_app import get_logger

logger = get_logger()

logger.info("Application started")
logger.warning("Something unusual", context={"value": 42})
logger.error("Something failed", status="failed")
```

---

### 3. Run Viewer

```bash
python -m logs.log_viewer
```

👉 Logs will be displayed instantly in GUI

---

## 🧱 Architecture

Application  
↓  
Logger (AppLogger)  
↓  
JSON Lines Log File  
↓  
log_searcher (analysis)  
↓  
traceql_bridge (TraceQL boundary)  
↓  
query_engine / SQLite adapter  
↓  
log_viewer (GUI)  

---

## 🧠 Design Philosophy

- Logs are events, not strings
- LogRecord is immutable
- trace_id represents a unique execution session
- Strict separation of responsibilities

| Layer    | Role    |
| -------- | ------- |
| Logger   | Record  |
| Searcher | Analyze |
| Bridge   | Convert logs to TraceQL documents |
| Query Engine | Query / match / batch-search |
| Viewer   | Display |

---

## 📂 Project Structure

```text
logs/
├ multi_info_logger.py
├ log_storage.py
├ log_searcher.py
├ log_viewer.py
├ traceql_bridge.py
├ log_types.py
├ time_utils.py
└ log_paths.py

query_engine/
├ adapters/
│ ├ logs.py
│ └ sqlite_adapter.py
├ evaluators/
│ ├ memory.py
│ └ sql.py
├ parser.py
└ models.py

# Core logger: multi_info_logger.py
# I/O layer: log_storage.py
# Analysis: log_searcher.py
# TraceQL boundary: traceql_bridge.py
# Query core: query_engine/
# GUI: log_viewer.py
```

---

## 🔎 TraceQL Integration Policy

The Logger application layer and TraceQL core are separated by a bridge.

```text
logs / viewer
    ↓
logs.traceql_bridge
    ↓
query_engine
```

Only `logs/traceql_bridge.py` should import `query_engine` from the `logs` package.
This keeps the viewer, log formatting, and application-specific behavior independent from the reusable query core.

The `query_engine/` folder in this repository is independent from any external `traceql_project`.
Changes made under another project, such as `traceql/logger_window/query_engine/`, must not be assumed to update this repository.

---

## 🗄️ Large Log Search with SQLite

For very large log files, loading everything into memory is not always practical.
Version 0.9.9 includes a SQLite document adapter:

```python
from query_engine.adapters.sqlite_adapter import SQLiteDocumentStore

with SQLiteDocumentStore("logs.sqlite") as store:
    store.add_documents(documents)
    results = store.search("level:ERROR", limit=100)
```

For large result sets, use batch iteration:

```python
for batch in store.iter_search("context.cpu_percent >= 80", batch_size=1000):
    for result in batch.results:
        handle(result.document)
```

When this is used from the Logger viewer side, route data through `logs.traceql_bridge`.

---

### Install dependencies

```bash
pip install -r requirements.txt
```

### Update TimeZoneData

IANA timezone data is released irregularly when timezone or daylight-saving rules change.
Run this helper to check PyPI's latest `tzdata` package and update the local environment when needed:

```bash
python -m logs.update_tzdata
```

The reference file is:

```text
logs/.tzdata_ver_reference
```

It stores `year:tzdata-version`, for example:

```text
2026:2026.2
```

---

## 📚 Documentation

- Design → docs/Design.md
- Usage → docs/How_To_Use_EN.md

---

### 🇯🇵 Japanese Documentation

For Japanese users:

- Overview → readme_jp.md
- Design → docs/Design.md
- Usage → docs_jp/How_To_Use_JP.md

---

### 🚀 Future Plans

- Real-time monitoring
- Web dashboard
- More storage backends

### 📄 License

- MIT License

### 💬 Concept

#### Why this Logger was created

This Logger was designed to eliminate **"silent failures"** that can occur during normal operation.

In many systems, issues do not always raise explicit errors.

As a result, problems may go unnoticed or become difficult to trace.

To address this, this Logger adopts a design that explicitly records **state and intent**.

In particular, it introduces a structured logging format:

```python
context: dict {variable / property : intended value}
```

This makes it possible to clearly understand:

- What the system was trying to do
- What values were expected
- Where deviations occurred

Additionally, the structure is designed to be easy to write,

so developers can naturally include this information without friction.

---

This Logger is not just a logging tool.

It is a **design tool for ensuring state transparency and early detection of issues**.

This is not just a logger.

👉 It is a diagnostic system for understanding program behavior.

## Example: context usage

Below is an example of how the `context` field is used to make logs more informative.

### Code Example

```python
logger.info(
    "User login attempt",
    context={
        "user_id": user_id,
        "expected_status": "authenticated",
        "actual_status": auth_result,
    }
)
```

### Output Example

```json
{
  "type": "INFO",
  "time": "2026-04-18T10:15:30Z",
  "message": "User login attempt",
  "context": {
    "user_id": "A12345",
    "expected_status": "authenticated",
    "actual_status": "failed"
  }
}
```

### 💡 Why this matters

Instead of simply seeing that something failed, you can immediately understand:

- What was expected
- What actually happened
- Which data caused the deviation

This significantly speeds up debugging and helps prevent silent failures from going unnoticed.

---

### 🤖 Acknowledgment

Developed with assistance from ChatGPT (OpenAI), with sincere appreciation.

This project is not affiliated with or endorsed by OpenAI.

---

### ⭐ Support

If you find this project helpful,

**please consider giving it a star on GitHub!**
