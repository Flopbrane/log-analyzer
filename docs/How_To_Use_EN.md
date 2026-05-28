# Logging System — How to Use

---

## Version Scope

This document describes Logger_project Ver.0.9.9.

The local `query_engine/` directory is the TraceQL/query core bundled with this project.
It is independent from any external `traceql_project` copy.
Logger/UI code should access it through `logs.traceql_bridge`.

---

## 🎯 Basic Flow

Logger → Logging → Analysis → Visualization

---

## 🟢 1. Get Logger

```python
from logs.log_app import get_logger

logger = get_logger()
```

> 💡 For type-safe usage (optional), see Design.md

## 🟢 2. Logging

### 🔵 Basic

```python
logger.info("Process started")
```

### 🔵 With Context

```python
logger.warning(
    "clock_jump_detected",
    context={"diff": 180}
)
```

### 🔵 With Metadata

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

```python
logger.error(
    "database_error",
    action="connect",
    status="failed",
    category="db"
)
```

## 🟢 3. Log File

### 🔵 Structure

```text
logs/
  └ app_YYYY-MM-DD.log
```

### 🔵 Log Format

- One line = one JSON record (JSON Lines)
- Input datetime (JST or local) is normalized to UTC
- All storage and analysis are performed in UTC
- Local time conversion is handled only in the Viewer

### 🟢 4. Log Analysis

#### basic

```python
from logs.log_searcher import search_logs
from pathlib import Path

events = search_logs(Path("logs"))

for e in events:
    print(e)
```

#### 🔹 Advanced Usage

For internal architecture and detailed flow,  
please refer to Design.md

### 🟢 5. Run Viewer

```bash
python -m logs.log_viewer
```

👉 Opens GUI for real-time log inspection

When the Viewer builds TimeZoneData, it may show:

```text
現在、最新版のTimeZoneDataに書き換え中です。
```

This means the Viewer is checking/updating the Python `tzdata` package used for local-time display.

#### 🟢 Display Fields

| Field    | Description        |
| -------- | ------------------ |
| time     | Timestamp          |
| type     | Event type         |
| trace_id | Session identifier |
| message  | Content            |

#### 🟢 Interaction

Click a row → View detailed JSON

#### 🔍 Search Text Box

The Viewer search text box supports:

- Basic keyword search,
- Exact phrase search,
- Date search,
- Time search,
- Date/time range search,
- Field-specific search,
- Regular expression search,
- Similarity search,
- Numeric comparison,
- Boolean expressions,
- Ignore rules,
- Sort / top-N search,
- Aggregate/statistical search.

##### ✅ Basic Search

Type any keyword to search across visible log fields such as `message`, `level`, `trace_id`, `where`, and `context`.

```text
test_error
system_cpu_percent
run_test
```

##### ✅ Date Search

Search logs by date.

```text
2026-04-23
```

This matches logs displayed on that date in the Viewer timezone.

##### ✅ Time Search

Search logs by hour and minute.

```text
10:15
10:16
```

##### ✅ Date + Time Search

Search logs that match a specific date/time prefix.

```text
2026-04-24 10:16
```

##### ✅ Date / Time Range Search

Use `..` as the standard range separator.

```text
2026-04-23..2026-04-24
2026-04-23 14:49..2026-04-23 14:49
2026-04-23 15:00:31..2026-04-23 15:00:37
```

The Viewer also supports the older compatible format using ` - ` with spaces.

```text
2026-04-23 - 2026-04-24
```

> Recommended format: `start..end`  
> Compatible format: `start - end`

##### ✅ Field-Specific Search

You can search by specific log fields using `key:value`.

```text
level:ERROR
level:WARNING
message:test_error
message:system_cpu_percent
function:run_test
file:system_monitor.py
context:cpu_percent
context:gpu_mem_total_mb
trace_id:fc036f388b7542c48117d55c8ec1728c
```

Supported field aliases include:

| Alias | Target |
| ----- | ------ |
| `level` | `level` |
| `message`, `msg` | `what.message` |
| `function`, `func` | `where.function` |
| `file` | `where.file` |
| `trace`, `trace_id` | `trace_id` |
| `output` | `output` |
| `context` | `context` |

##### ✅ Query Error Suggestions

Incomplete or invalid TraceQL input is reported as a structured query error instead of crashing the Viewer.

Example:

```text
level:
```

The detail view can show:

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

Typo correction is dictionary-based and does not require AI.

```text
levle:ERROR
```

can suggest:

```text
level:ERROR
```

##### ✅ Exclude Search

Prefix a term with `-` to hide logs that contain that term.

```text
cpu -gpu
message:system -gpu
```

##### ✅ Exact Phrase Search

Wrap text in double quotes to search for that exact phrase as one continuous string.

```text
"invalid log: missing trace_id"
"system cpu"
```

##### ✅ Boolean Search

Multiple terms are treated as `AND`. You can also use explicit `AND`, `OR`, and parentheses.

```text
level:WARNING message:system_cpu_percent
level:ERROR OR level:CRITICAL
(level:ERROR OR level:WARNING) -debug
```

##### ✅ Numeric Comparison Search

Use comparison operators for numeric fields, especially values inside `context`.

```text
context.cpu_percent >=20
context.gpu_mem_total_mb>1000
context.cpu_percent <80
```

Supported operators:

```text
< <= > >= == !=
```

##### ✅ Ignore Rules

Use `(ignore: ...)` to remove logs matching an ignore condition after the main search has selected candidates.

```text
cpu (ignore: context.cpu_percent <80)
system (ignore: gpu)
```

##### ✅ Regular Expression Search

Use `regex` for regular expression matching. You can search the whole flattened log, or one field.

```text
regex "^system_.*"
regex message "^system_.*_status$"
regex context "gpu_.*_mb"
```

Invalid regular expressions simply match no rows.

##### ✅ Similarity Search

Use `similar` to find logs whose text is close to the phrase, even when the words are not an exact keyword match.

```text
similar "GPU memory pressure"
similar "reboot or clock jump symptoms"
similar "GPU memory pressure" 0.12
```

This is an offline approximate search based on lightweight TF-IDF-style text features and character n-grams. It does not require an API key. Matching logs are displayed in similarity-score order unless you also specify an explicit `sort by`.

The optional number after the phrase is the similarity threshold. Higher values are stricter.

##### ✅ Sort / Top-N Search

Use `sort by` to sort matching logs, or `top N by` to show only the highest N rows for a field.

```text
level:error sort by time desc
message:system sort by context.cpu_percent desc
top 3 by context.cpu_percent
top 10 by time desc where level:error
```

If a log does not have the sort field, it is placed after logs that do.

##### ✅ Aggregate / Statistical Search

Aggregate search filters the log list to the rows used for the calculation, then displays the result next to the search box.

Format:

```text
function field where condition
```

`where condition` is optional. It can use the same search syntax as normal searches, including date ranges and comparisons.

Supported aggregate functions:

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

Examples:

```text
count * where level:error
count * where 2026-04-23..2026-04-23
max context.cpu_percent
max context.cpu_percent where 2026-04-23..2026-04-23
min context.cpu_percent where context.cpu_percent >=20
avg context.cpu_percent
ave context.cpu_percent
mean context.cpu_percent
median context.cpu_percent
mode level
group by level count *
group by message avg context.cpu_percent
```

Notes:

- `count *` counts matching logs.
- `count field_name` counts values found in that field.
- `max`, `min`, `avg`, `ave`, `mean`, and `median` require numeric values.
- `mode` can be used with text fields such as `level`.
- `group by field function target` calculates aggregate values per group.
- When a field does not exist in a log, that log is not included in the aggregate result for that field.

##### ✅ Search Examples

| Query | Meaning |
| ----- | ------- |
| `2026-04-23` | Logs on 2026-04-23 |
| `2026-04-23..2026-04-24` | Logs from 2026-04-23 to 2026-04-24 |
| `2026-04-23 15:00:31..2026-04-23 15:00:37` | Logs within a precise time range |
| `10:15` | Logs whose displayed local time starts with 10:15 |
| `level:ERROR` | Error logs only |
| `message:test_error` | Logs whose message contains `test_error` |
| `context:cpu_percent` | Logs that contain `cpu_percent` in context |
| `trace_id:...` | Logs for a specific session |
| `cpu -gpu` | Logs that contain `cpu` but do not contain `gpu` |
| `"invalid log: missing trace_id"` | Logs that contain that exact phrase |
| `regex message "^system_.*_status$"` | Logs whose message matches the regular expression |
| `similar "GPU memory pressure"` | Logs that are approximately similar to that phrase |
| `context.cpu_percent >=20` | Logs whose CPU percent is 20 or higher |
| `level:ERROR OR level:CRITICAL` | Error or critical logs |
| `top 3 by context.cpu_percent` | Top 3 logs by CPU percent |
| `count * where level:error` | Count error logs and show those rows |
| `avg context.cpu_percent` | Average CPU percent and show logs that contain that field |
| `group by level count *` | Count logs per level |

##### ⚠️ Range Separator Notes

Because dates already contain hyphens, avoid using a plain `-` without spaces.

```text
2026-04-23-2026-04-24  # Not recommended
```

Use this instead:

```text
2026-04-23..2026-04-24
```

#### ⚠️ Important Notes

❌ Do NOT instantiate logger directly  

```python
AppLogger()  # NG
```

✔ Always use

```python
logger = get_logger()
```

❌ Do NOT create trace_id manually  
trace_id is automatically generated per session  

✔ Let Logger handle everything

- where → auto-detected
- trace_id → auto-generated
- datetime → normalized to UTC

### 💡 Common Use Cases

Debugging

```python
logger.debug("Check value", context={"value": x})
```

Error Detection

```python
logger.error("Process failed", status="failed")
```

System Monitoring

```python
logger.info("cpu_usage", context={"cpu": 30})
```

### TimeZoneData Update

IANA timezone data is released irregularly when timezone or daylight-saving rules change.
To explicitly check and update the local Python `tzdata` package:

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

### 🚀 Advanced Ideas

- Event filtering
- Trace-based analysis
- Graph visualization

### 💬 Summary

This system is not just a logger.

👉 It is a state monitoring and analysis tool.
