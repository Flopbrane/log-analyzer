# Logging System — How to Use

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

The Viewer search text box supports simple keyword search, field-specific search, and date/time range search.

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

---

### 🚀 Advanced Ideas

- Event filtering
- Trace-based analysis
- Graph visualization

### 💬 Summary

This system is not just a logger.

👉 It is a state monitoring and analysis tool.
