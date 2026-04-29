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
