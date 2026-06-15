# Info Logger — How to Use

> Target version: **v1.0.0-rc1**  
> This document describes the current Logger_Project / Info Logger viewer, including Event-based display, TraceQL search, FV recipes, summary output, and investigation report export.

---

## 1. What Info Logger Does

Info Logger is not only a logger.

It is a diagnostic pipeline:

```text
Logger
  ↓
JSON Lines logs
  ↓
LogDict validation
  ↓
Event analysis
  ↓
Viewer display
  ↓
Search / Summary / Export
```

The important idea is:

```text
LogDict = record
Event   = meaning
```

A raw log is a structured record.  
An Event is the result of interpreting that record.

---

## 2. Core Concepts

### 2.1 `level`, `type`, and `message`

The Viewer intentionally separates these three values.

| Field | Meaning | Example |
| --- | --- | --- |
| `level` | Original log severity | `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `type` | Event meaning added by analysis | `TRACE_JUMP`, `REBOOT`, `REPEAT_ERROR` |
| `message` | What happened | `system_cpu_percent`, `trace_id changed` |

Normal logs usually have:

```text
type  = None
level = INFO / WARNING / ERROR / CRITICAL
```

Analysis events usually have:

```text
type  = TRACE_JUMP / REBOOT / REPEAT_ERROR
level = original log level
```

The Viewer Type column follows this rule:

```text
if Event.type exists:
    show Event.type
else:
    show Event.level
```

So a normal INFO log displays `INFO`, while a detected trace jump displays `TRACE_JUMP`.

---

## 3. Get the Logger

```python
from logs.log_app import get_logger

logger = get_logger()
```

Do not instantiate `AppLogger` directly.

```python
# Do not do this
AppLogger()
```

The logger manages:

- `trace_id`
- timestamp normalization to UTC
- source location
- JSON Lines output

---

## 4. Basic Logging

### Simple log

```python
logger.info("Application started")
```

### Log with context

```python
logger.warning(
    "clock_jump_detected",
    context={"diff": 180},
)
```

### Log with intent and actual state

```python
logger.info(
    "User login attempt",
    context={
        "user_id": user_id,
        "expected_status": "authenticated",
        "actual_status": auth_result,
    },
)
```

### Error log

```python
logger.error(
    "database_error",
    action="connect",
    status="failed",
    category="db",
)
```

---

## 5. Log File Format

Info Logger stores logs as JSON Lines.

```text
one line = one JSON object
```

A typical validated log looks like this:

```json
{
  "level": "INFO",
  "time": "2026-06-15T05:21:33+00:00",
  "trace_id": "ecdab2f96d1149639791c4c3cdd0178c",
  "where": {
    "file": "logs/log_viewer.py",
    "line": 993,
    "function": "reload_log"
  },
  "what": {
    "message": "reload_log prepared"
  },
  "context": {
    "raw_count": 12,
    "valid_count": 12
  },
  "output": "both"
}
```

Internally, time is stored and analyzed in UTC.  
The Viewer converts time only for display.

---

## 6. Run the Viewer

```bash
python -m logs.log_viewer
```

The Viewer opens a Tkinter GUI.

If TimeZoneData is being built or checked, the Viewer may show:

```text
現在、最新版のTimeZoneDataに書き換え中です。
```

This means local-time display data is being prepared.

---

## 7. Viewer Layout

The main table contains:

| Column | Meaning |
| --- | --- |
| `type` | Display type: Event type if available, otherwise log level |
| `time` | Local time in the selected timezone |
| `trace_id` | Execution/session identifier |
| `message` | Flattened message text |

The detail window shows:

```text
Type  : TRACE_JUMP
Level : INFO
Time(Local:Asia/Tokyo | JST) : ...
Time(UTC)                    : ...

=== MESSAGE ===
...

--- where ---
File :
Line :
Func :

--- Event ---
from :
to   :

--- Context ---
...
```

This is intentionally more detailed than a normal log viewer.

---

## 8. Loading Logs

The Viewer supports:

- latest log auto-load
- opening one log file
- opening multiple log files
- reloading previous log paths from Viewer config

When new logs are loaded, the Viewer replaces the old dataset and clears its Event cache:

```text
raw_rows      = new validated logs
filtered_rows = []
display_rows  = []
_event_cache  = None
```

The Event cache is rebuilt from the new `raw_rows` only when needed.

---

## 9. Search Basics

The search box supports normal keyword search and TraceQL-style field search.

### Keyword search

```text
cpu
system_cpu_percent
database_error
```

### Date search

```text
2026-04-23
```

### Time search

```text
10:15
```

### Date/time search

```text
2026-04-23 15:00
```

### Range search

Use `..` as the recommended range separator.

```text
2026-04-23..2026-04-24
2026-04-23 15:00:31..2026-04-23 15:00:37
```

Compatible older format:

```text
2026-04-23 - 2026-04-24
```

Because dates contain hyphens, prefer `..`.

---

## 10. Field Search

```text
level:ERROR
level:WARNING
message:system_cpu_percent
function:run_test
file:system_monitor.py
context:cpu_percent
trace_id:fc036f388b7542c48117d55c8ec1728c
```

Common aliases:

| Alias | Target |
| --- | --- |
| `level` | `level` |
| `type` | Viewer/Event display type |
| `message`, `msg` | `what.message` / Event message |
| `function`, `func` | `where.function` |
| `file` | `where.file` |
| `trace`, `trace_id` | `trace_id` |
| `context` | `context` |
| `output` | `output` |

---

## 11. Event Type Search

This Viewer is Event-aware.

You can search analysis events directly:

```text
type:TRACE_JUMP
type:REBOOT
type:REPEAT_ERROR
```

This is different from normal log-level search.

```text
level:ERROR
```

Use `type:` when you want analysis results.  
Use `level:` when you want original log severity.

---

## 12. Query Error Reports

Incomplete or invalid TraceQL input does not crash the Viewer.

Example:

```text
level:
```

The detail view can show a structured report:

```text
QUERY ERROR
Query : level:
Error : Expected field value at position 6.
Expected : field value

level:
     ^

Did you mean:
- level:ERROR
- level:WARNING
- level:INFO
```

Typo suggestions are dictionary-based and do not require AI.

---

## 13. Boolean / Exclude / Phrase Search

### Exclude search

```text
cpu -gpu
message:system -gpu
```

### Exact phrase search

```text
"invalid log: missing trace_id"
"system cpu"
```

### Boolean search

```text
level:ERROR OR level:CRITICAL
(level:ERROR OR level:WARNING) -debug
level:WARNING message:system_cpu_percent
```

---

## 14. Numeric Comparison

Numeric fields in context can be compared.

```text
context.cpu_percent >=20
context.gpu_mem_total_mb>1000
context.cpu_percent <80
```

Supported operators:

```text
< <= > >= == !=
```

---

## 15. Regular Expression Search

```text
regex "^system_.*"
regex message "^system_.*_status$"
regex context "gpu_.*_mb"
```

Invalid regular expressions simply match no rows.

---

## 16. Similarity Search

```text
similar "GPU memory pressure"
similar "reboot or clock jump symptoms"
similar "GPU memory pressure" 0.12
```

The current implementation is offline and lightweight.  
It does not require an API key.

---

## 17. Sort and Top-N Search

```text
level:error sort by time desc
message:system sort by context.cpu_percent desc
top 3 by context.cpu_percent
top 10 by time desc where level:error
```

---

## 18. Aggregate / Statistical Search

Format:

```text
function field where condition
```

Examples:

```text
count * where level:error
count * where 2026-04-23..2026-04-23
max context.cpu_percent
min context.cpu_percent where context.cpu_percent >=20
avg context.cpu_percent
median context.cpu_percent
mode level
group by level count *
group by message avg context.cpu_percent
```

Supported functions:

```text
count
max
min
avg
ave
mean
median
mode
```

---

## 19. FV Recipes

FV recipes are saved search/report instructions.

A recipe can define:

```text
TITLE
QUERY
SUMMARY
EXPORT
OUTPUT
```

Example concept:

```text
TITLE: Trace Jump Analysis
QUERY: type:TRACE_JUMP
SUMMARY: on
EXPORT: json
OUTPUT: result_trace_jump.json
```

When the Viewer opens an FV recipe:

1. The recipe is parsed.
2. An execution plan is built.
3. The query is copied into the search box.
4. The Viewer applies the filter.
5. If the query uses Event type search, the Viewer builds the result from `display_rows`.
6. Summary and export are generated.

This is important because `TRACE_JUMP`, `REBOOT`, and `REPEAT_ERROR` are analysis events, not raw log strings.

---

## 20. Summary Engine

The summary engine creates a `SummaryResult`.

It can include:

- total count
- condition text
- level counts
- module ranking
- message ranking
- numeric context statistics
- insights
- formatted summary text

Example summary:

```text
Search condition
  Condition: type:TRACE_JUMP
  Count: 4

Level counts
  - INFO: 4

Top modules
  - system_monitor.py: 4

Top messages
  - system_cpu_percent: 4
```

---

## 21. Export

The Viewer supports:

- filtered Event CSV
- JSON bundle
- investigation report JSON
- summary CSV
- summary JSON

### JSON bundle structure

```json
{
  "exported_at": "...",
  "logs": [],
  "events": [],
  "summary": {},
  "report": null
}
```

### Investigation report structure

```json
{
  "exported_at": "...",
  "logs": [],
  "events": [],
  "summary": {},
  "report": {
    "kind": "investigation_report",
    "format_version": "0.1",
    "condition_text": "type:TRACE_JUMP",
    "timezone": "Asia/Tokyo",
    "log_count": 4,
    "event_count": 4,
    "source_files": []
  }
}
```

---

## 22. Large Logs and SQLite

For large logs, a SQLite document adapter is available through the query engine.

```python
from query_engine.adapters.sqlite_adapter import SQLiteDocumentStore

with SQLiteDocumentStore("logs.sqlite") as store:
    store.add_documents(documents)
    results = store.search("level:ERROR", limit=100)
```

For large result sets:

```python
for batch in store.iter_search("context.cpu_percent >= 80", batch_size=1000):
    for result in batch.results:
        handle(result.document)
```

When using this from the Logger side, route data through `logs.traceql_bridge`.

---

## 23. TimeZoneData Update

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

## 24. Recommended Test Checklist

Before tagging a release:

```text
□ Open one log file
□ Open multiple log files
□ Load another log and confirm old cache is cleared
□ Search type:TRACE_JUMP
□ Search type:REBOOT
□ Search level:ERROR
□ Open detail window
□ Export JSON bundle
□ Export investigation report
□ Run FV recipe
□ Confirm SummaryWindow opens
```

---

## 25. Summary

Info Logger is a structured logging, Event analysis, and diagnostic Viewer system.

It is designed to make program behavior visible:

```text
record → analyze → inspect → summarize → report
```
