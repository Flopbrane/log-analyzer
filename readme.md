# Info Logger

![version](https://img.shields.io/badge/version-v1.0.0--rc1-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![stars](https://img.shields.io/github/stars/Flopbrane/log-analyzer?style=social)

> ⚠ Requires Python 3.9 or higher

🚀 **Info Logger** is a structured logging, analysis, and GUI viewer system that turns logs into **debuggable events**.

> Not just logs — this is a **diagnostic system**.

- Japanese version → [README_jp.md](README_jp.md)

---

## ✨ Current Status: v1.0.0-rc1

`v1.0.0-rc1` is the first release candidate of Info Logger.

The core diagnostic pipeline is now connected:

```text
Structured logging
↓
Log validation
↓
Event analysis
↓
TraceQL / type search
↓
FV recipe execution
↓
Summary engine
↓
GUI detail view
↓
CSV / JSON / investigation report export
```

This release candidate includes:

- Structured JSON Lines logging
- `LogDict` validation and safe normalization
- Event analysis with `Event.type`, `Event.level`, and `message` separation
- Trace jump detection
- System reboot detection
- Repeated error detection
- Japanese / English GUI Viewer
- TraceQL-powered search through a bridge layer
- FV recipe execution
- Summary engine output
- CSV / JSON export
- Investigation report export with metadata
- Timezone-aware display based on UTC records
- SQLite-backed document adapter for large-log search

---

## 🧠 Core Concept

Most loggers only record text.

Info Logger treats logs as structured records and converts them into analyzable events.

```text
LogDict = record
Event   = meaning
```

The most important design rule is:

```text
level   = original log severity
type    = analyzed event classification
message = what happened
```

For example:

```text
level: INFO
type : TRACE_JUMP
message: trace_id changed
```

This makes it possible to distinguish the original log severity from the meaning discovered by analysis.

---

## ✨ What’s Included

- 🔍 **Trace-based tracking**
  - Track execution flow using `trace_id`

- 📍 **Automatic source location**
  - File / line / function are captured automatically

- 🧠 **Event analysis**
  - Trace jumps
  - System reboot detection
  - Repeated error detection
  - ERROR / CRITICAL handling through log levels

- 🖥️ **GUI Viewer**
  - Open single or multiple logs
  - Filter by `type`, `level`, `trace_id`, and text
  - Inspect detailed event information
  - Display raw JSON
  - Japanese / English UI support

- 📘 **Summary engine**
  - Count logs by level
  - Rank modules and messages
  - Summarize numeric context values
  - Generate investigation-friendly text summaries

- 📄 **Investigation report export**
  - Save source logs
  - Save analyzed events
  - Save summary results
  - Save report metadata such as condition, timezone, source files, and format version

- 🔎 **TraceQL bridge**
  - Advanced query matching is routed through `logs/traceql_bridge.py`
  - Logger / Viewer code does not import `query_engine` directly
  - Log records are converted to TraceQL documents at the bridge boundary

- 🧭 **Query error reports**
  - Query syntax errors are preserved as diagnosable events
  - Error reports include query text, caret position, expected syntax, and dictionary-based suggestions

- 🗄️ **SQLite adapter**
  - Store generic TraceQL documents in SQLite
  - Search large log sets in batches
  - Useful when JSONL logs grow to hundreds of MB or several GB

- 🕒 **Timezone handling**
  - Internal logs are recorded in UTC
  - Viewer renders selected local time
  - `logs/.tzdata_ver_reference` records checked `year:tzdata-version`
  - `python -m logs.update_tzdata` can update timezone data explicitly

---

## 🖼️ Screenshots

### Main Window

<img src="docs/image/main_window.png" alt="Log Viewer Main Window" width="900">

### Detail View

<img src="docs/image/sub_window.png" alt="Log Viewer Detail Window" width="600">

---

## ⚡ Quick Start

### 1. Clone

```bash
git clone https://github.com/Flopbrane/log-analyzer.git
cd log-analyzer
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Basic usage

```python
from logs.log_app import get_logger

logger = get_logger()

logger.info("Application started")
logger.warning("Something unusual", context={"value": 42})
logger.error("Something failed", status="failed")
```

### 4. Run Viewer

```bash
python -m logs.log_viewer
```

---

## 🔍 Search Examples

```text
type:TRACE_JUMP
level:ERROR
message:"system_cpu_percent"
trace_id:230b4afdc5cc47349267e9ab954c1a05
```

The Viewer can also load FV recipes and reflect the recipe query into the search box.

Example FV use case:

```text
type:TRACE_JUMP
```

This can display trace jumps, open detail information, generate a summary, and export an investigation report.

---

## 🧱 Architecture

```text
Application
↓
Logger / AppLogger
↓
JSON Lines log file
↓
log_validator
↓
log_searcher / analyzer
↓
Event
↓
traceql_bridge
↓
query_engine / SQLite adapter
↓
summary_engine
↓
log_viewer
↓
CSV / JSON / investigation report
```

---

## 🧠 Design Philosophy

- Logs are structured records, not plain strings
- Events are meanings extracted from logs
- `trace_id` represents an execution session
- Internal time is UTC
- Display time is selected by the Viewer
- Viewer, Logger, Query Engine, and Summary Engine are separated
- Query core access is routed through bridge modules
- Reports should preserve both raw records and analyzed events

| Layer | Role |
| --- | --- |
| Logger | Record |
| Validator | Normalize and protect |
| Searcher / Analyzer | Convert logs into events |
| Bridge | Convert logs to TraceQL documents |
| Query Engine | Query / match / batch search |
| Summary Engine | Summarize filtered logs |
| Viewer | Display and export |

---

## 📂 Project Structure

```text
logs/
├ multi_info_logger.py
├ log_app.py
├ log_storage.py
├ log_validator.py
├ log_searcher.py
├ log_viewer.py
├ display_formatter.py
├ traceql_bridge.py
├ summary_bridge.py
├ log_types.py
├ time_utils.py
└ log_paths.py

summary_engine/
├ summary_engine.py
├ summary_types.py
├ aggregators/
└ analyzers/

query_engine/
├ adapters/
│ ├ logs.py
│ └ sqlite_adapter.py
├ evaluators/
│ ├ memory.py
│ └ sql.py
├ parser.py
└ models.py

fv_engine/
├ fv_parser.py
├ fv_interpreter.py
├ fv_runner.py
├ fv_plan.py
└ example/
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

---

## 📊 Summary Engine

The summary engine creates investigation-friendly summaries from filtered logs.

It can produce:

- Total count
- Level counts
- Module ranking
- Message ranking
- Numeric context statistics
- Human-readable insights

Example output structure:

```text
Search condition
  condition: type:TRACE_JUMP
  count: 4

Level counts
  - INFO: 4

Top modules
  - system_monitor.py: 4

Top messages
  - system_cpu_percent: 4
```

---

## 📄 Investigation Reports

Investigation reports are exported as JSON and preserve:

```text
logs     = original records
events   = analyzed events
summary  = summary result
report   = report metadata
```

Report metadata includes:

```json
{
  "kind": "investigation_report",
  "format_version": "0.1",
  "condition_text": "type:TRACE_JUMP",
  "timezone": "Asia/Tokyo",
  "log_count": 4,
  "event_count": 4,
  "source_files": []
}
```

---

## 🗄️ Large Log Search with SQLite

For very large log files, loading everything into memory is not always practical.

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

## 🕒 Update TimeZoneData

IANA timezone data is released irregularly when timezone or daylight-saving rules change.

```bash
python -m logs.update_tzdata
```

Reference file:

```text
logs/.tzdata_ver_reference
```

Example:

```text
2026:2026.2
```

---

## 📚 Documentation

- Design → `docs/Design.md`
- Usage → `docs/How_To_Use_EN.md`
- Japanese overview → `README_jp.md`
- Japanese usage → `docs_jp/How_To_Use_JP.md`

---

## 🚀 Future Plans

- Real-time monitoring
- Web dashboard
- More storage backends
- Notification integrations
- Larger-scale indexing
- More investigation report formats

---

## 📄 License

MIT License

---

## 🤖 Acknowledgment

Developed with assistance from ChatGPT (OpenAI), with sincere appreciation.

This project is not affiliated with or endorsed by OpenAI.

---

## ⭐ Support

If you find this project helpful, please consider giving it a star on GitHub!
