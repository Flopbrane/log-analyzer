# Info Logger — Design & Specifications

> Target version: **v1.0.0-rc1**

---

## 1. Overview

Info Logger is a structured logging and diagnostic system.

It is designed around this pipeline:

```text
Log generation
  ↓
Log storage
  ↓
Validation
  ↓
Event analysis
  ↓
Search / summary
  ↓
Viewer / export
```

The project is not only a logger.  
It is a diagnostic system for understanding program behavior.

---

## 2. Core Principle

```text
LogDict = record
Event   = meaning
```

A `LogDict` is a validated record.  
An `Event` is an interpreted result produced from one or more records.

This separation is the foundation of the Viewer.

---

## 3. Main Architecture

```text
[Application]
    ↓
[AppLogger]
    ↓
[JSON Lines log files]
    ↓
[log_storage / file_adapter]
    ↓
[log_validator]
    ↓
[LogDict]
    ↓
[log_searcher / analyzers]
    ↓
[Event]
    ↓
[log_viewer]
    ↓
[summary_engine / export / FV]
```

TraceQL / query flow:

```text
logs / viewer
    ↓
logs.traceql_bridge
    ↓
query_engine
```

The `logs` layer should not freely import `query_engine`.  
The bridge boundary keeps application-specific logging code separated from the reusable query core.

---

## 4. Responsibilities by Layer

| Layer | Responsibility |
| --- | --- |
| `multi_info_logger.py` | Create structured log records |
| `log_storage.py` | Load JSONL / log files |
| `file_adapter/` | Read non-standard or external file formats |
| `log_validator.py` | Convert unstable raw dicts into stable `LogDict` |
| `log_searcher.py` | Build normal Events and analysis Events |
| `query_engine/` | Parse and evaluate TraceQL-like queries |
| `traceql_bridge.py` | Convert logs into query documents |
| `summary_engine/` | Build summaries and rankings |
| `fv_engine/` | Parse and run saved filter/view recipes |
| `log_viewer.py` | Display, search, inspect, and export |
| `result_exporter.py` | Save CSV / JSON / investigation reports |

---

## 5. Data Model

### 5.1 Raw Log Record

Raw records are unstable dictionaries loaded from files.

They may be incomplete or malformed.

### 5.2 LogDict

`LogDict` is the validated stable record.

Conceptual structure:

```python
class LogDict(TypedDict):
    level: str
    time: str
    trace_id: str
    where: LogWhere
    what: LogWhat
    context: dict[str, Any]
    output: str
```

### 5.3 Event

`Event` is the analysis result.

```python
@dataclass(slots=True)
class Event:
    type: EventType | None
    level: LogLevel
    time: str
    detected_at: str
    trace_id: TraceId
    message: str
    data: dict[str, Any]
    raw: LogDict
```

The `raw` field is intentionally preserved.  
It allows the Viewer, detail window, export, and reports to refer back to the original record.

---

## 6. `level`, `type`, and `message`

These fields must remain separated.

| Field | Owner | Meaning |
| --- | --- | --- |
| `level` | Original log | Severity recorded by logger |
| `type` | Analysis layer | Meaning detected after analysis |
| `message` | Logger / analyzer | Human-readable event content |

Examples:

```text
Normal log:
    type  = None
    level = INFO
    message = system_cpu_percent

Trace jump:
    type  = TRACE_JUMP
    level = INFO
    message = trace_id changed
```

Viewer display rule:

```text
if Event.type is not None:
    Type column = Event.type.name
else:
    Type column = Event.level.name
```

`message` must not freely become `type`.  
Only values explicitly matching known `EventType` or `LogLevel` names/values may be normalized as type candidates.

---

## 7. Event Types

| EventType | Meaning |
| --- | --- |
| `TRACE_JUMP` | `trace_id` changed between adjacent logs |
| `REBOOT` | reboot-like record detected |
| `REPEAT_ERROR` | repeated ERROR / CRITICAL message detected |
| `ERROR` | optional analysis event for error occurrence |
| `CRITICAL` | optional analysis event for critical occurrence |

For current Viewer behavior, ordinary ERROR / CRITICAL logs are primarily represented by `level`.  
`type` is reserved for analysis meaning.

---

## 8. Time Policy

The true internal time basis is UTC.

Rules:

- Logger stores time in UTC.
- Analysis compares time in UTC.
- Viewer converts time only for display.
- Timezone selection affects display and search interpretation, not stored records.

The Viewer may check or update TimeZoneData through:

```bash
python -m logs.update_tzdata
```

Reference file:

```text
logs/.tzdata_ver_reference
```

---

## 9. Logger Constraints

Logger internals must not call normal logging methods.

Do not call:

```text
debug / info / warning / error / critical
```

inside:

```text
_log
_build_log_record
_safe
_emit
```

Doing so can cause recursive logging.

Internal logger warnings should use `print()` or dedicated internal handling.

---

## 10. Context Design

`context` is used to record state, intent, and actual values.

Example:

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

This makes silent failures easier to detect because the log stores both the expected state and the observed state.

Typed context values may use the structure:

```json
{
  "type": "int",
  "value": 12
}
```

The Viewer unwraps these values for display and statistics.

---

## 11. Message Flattening

`what.message` can be a string or a structured value in older or external logs.

The analysis layer flattens it into a stable string:

```text
flatten_message_text(value) -> str
```

This is used for:

- Viewer message display
- search
- summary ranking
- repeat error detection
- normalized type candidate checks

Message-derived type candidates must be limited to known `EventType` / `LogLevel` values.

---

## 12. Viewer State Model

The Viewer state is intentionally separated.

```text
raw_rows
    Validated original logs.

filtered_rows
    Raw logs corresponding to currently displayed Events.

display_rows
    The only Event list used by Treeview, detail window, CSV/JSON export, and report output.

_event_cache
    Cached summarize(raw_rows) result.
```

When logs are replaced:

```text
raw_rows      = new logs
filtered_rows = []
display_rows  = []
_event_cache  = None
```

This prevents stale Event data after loading another file.

---

## 13. Event Cache

`summarize(raw_rows)` can be expensive for larger logs.

Therefore, the Viewer can cache the Event list.

```text
first use:
    _event_cache is None
    → summarize(raw_rows)
    → store result

later use:
    reuse _event_cache

new logs:
    _event_cache = None
```

This keeps repeated filtering fast while preserving correctness.

---

## 14. Search Design

The Viewer supports both raw-log search and Event-aware search.

Examples:

```text
level:ERROR
message:system_cpu_percent
context.cpu_percent >=20
type:TRACE_JUMP
```

Important distinction:

```text
level:ERROR
    searches original log severity

type:TRACE_JUMP
    searches analysis Event meaning
```

`TRACE_JUMP`, `REBOOT`, and `REPEAT_ERROR` do not have to exist as literal strings in the raw logs.  
They are produced by analysis.

---

## 15. FV Engine

FV means Filter & View.

It allows saved recipes that combine:

- query
- summary
- export format
- output path

Pipeline:

```text
FV file
  ↓
parse_fv_text()
  ↓
build_execution_plan()
  ↓
Viewer applies query
  ↓
run_execution_plan() or Viewer Event result builder
  ↓
FVResult
```

When the query uses `type:...`, the Viewer must use `display_rows`, because Event type is generated by analysis.

---

## 16. Summary Engine

`summary_engine` produces `SummaryResult`.

Typical fields:

```python
SummaryResult(
    total_count=...,
    condition_text=...,
    level_counts=...,
    module_ranking=...,
    message_ranking=...,
    context_numeric_stats=...,
    insights=...,
    text=...,
)
```

Summary is intentionally independent of the GUI.

The Viewer passes the selected logs and condition text through `summary_bridge`.

---

## 17. Export Design

The export layer can save:

- Event CSV
- JSON bundle
- investigation report JSON
- Summary CSV
- Summary JSON

Bundle concept:

```json
{
  "exported_at": "...",
  "logs": [],
  "events": [],
  "summary": {},
  "report": null
}
```

Investigation report concept:

```json
{
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

This keeps the original records, analysis results, summary, and report metadata together.

---

## 18. Query Error Design

TraceQL syntax errors are not fatal GUI errors.

They are converted into diagnosable reports.

A query like:

```text
level:
```

can become:

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

Suggestions are dictionary-based and do not require AI.

---

## 19. Large Log Strategy

For small and medium logs, in-memory Event lists are acceptable.

For large logs:

- use SQLite document adapter
- search in batches
- avoid loading all large results into the GUI at once
- keep Event generation and display paging as future extension points

The current Viewer is correct-first.  
Database-backed scalability can be expanded later.

---

## 20. Release Boundary for v1.0.0-rc1

The v1.0.0-rc1 baseline includes:

```text
□ structured JSONL logging
□ UTC-based time handling
□ LogDict validation
□ Event generation
□ type / level / message separation
□ Event-aware Viewer
□ TraceQL search bridge
□ query error reports
□ FV recipe execution
□ summary_engine output
□ JSON / CSV export
□ investigation report export
```

---

## 21. Future Work

- real-time monitoring
- Web dashboard
- storage backends
- paging for very large logs
- richer report format
- optional AI-assisted anomaly explanation
- trace timeline visualization

---

## 22. Summary

Info Logger is designed as:

```text
record → analyze → inspect → summarize → report
```

It is a diagnostic system for making program behavior visible.
