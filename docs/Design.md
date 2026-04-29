# Logging System — Design & Specifications

---

## 🎯 Overview

This system is designed as a structured logging and analysis pipeline:

Log Generation → Log Storage → Log Analysis → Visualization

---

## 🧭 Architecture

```text
[System / Application]  
↓  
[AppLogger]  
↓  
[JSON Lines Log File]  
↓  
[log_searcher]  
↓  
[LogEvent]  
↓  
[log_viewer]  
```

---

## 🧩 Module Responsibilities

### 🔹 log_app.py

- Provides logger instance (Singleton)
- `get_logger()` ensures a shared instance across the application

---

### 🔹 multi_info_logger.py (AppLogger)

#### Core Responsibilities

- Log record creation (`_build_record`)
- Output control (`_emit`)
- JSON Lines format storage
- Recognizes `.log` and `.jsonl` as log files

#### Precautions for use

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logs.multi_info_logger import AppLogger

logger: "AppLogger" = get_logger()
```

---

#### ⚠️ Critical Internal Constraints

- Logging methods (`debug`, `info`, `warning`, `error`) must NOT be called inside Logger internals

Especially forbidden during:

- `_log` (central logging pipeline)
- `_build_log_record` (record construction)
- `_safe` (JSON serialization)
- `_emit` (output process)

Violating this causes recursive logging → infinite loop / stack overflow

---

- Time-only values cannot be normalized to UTC → must not be logged
- Internal warnings must use `print()` or dedicated internal handling (NOT logger)

---

#### Log Structure

```json
{
  "level": "INFO",
  "time": "2026-04-08T10:00:00",
  "trace_id": "xxxx",
  "where": {...},
  "what": {...},
  "context": {...},
  "output": "both"
}
```

---

### 🔹 Additional Modules

#### 🔹 system_monitor.py

- Monitors system state
- Emits events to logger

Examples:

- reboot
- CPU usage
- clock_jump

#### 🔹 log_searcher.py

**Responsibilities**  

- Load logs
- Merge multiple logs
- Sort by time
- Apply time range filtering

#### 🔹 Input

```python
list[LogRecord]
```

#### 🔹 Output

```python
list[LogEvent]
```

#### 🔹 log_viewer.py

- GUI interface (Tkinter)
- Event list display
- Detailed view

---

### 🧠 Logging Design Philosophy

#### 🔥 1. Logs are Events

Logs represent state transitions, not just output messages.

#### 🔥 2. LogRecord is Immutable

Once created, it must not be modified  
Treated as a snapshot of system state  

#### 🔥 3. trace_id = Session Scope

Unique per application startup  
Used for reboot detection and flow tracking  

#### 🔥 4. Separation of Concerns

| Layer    | Role    |
|----------|---------|
| Logger   | Record  |
| Searcher | Analyze |
| Viewer   | Display |

#### 🔥 5. Unified Time Standard

Internal system operates in UTC  
multi_info_logger.py normalizes all input time to UTC  
All storage and analysis are based on UTC  
log_viewer.py converts to local time ONLY for display  

---

### 🧩 LogEvent Structure

```python
class LogEvent(TypedDict):
    type: str
    message: str
    timestamp: str | None
    trace_id: str | None
    data: dict[str, Any]
```

### 🔍 Event Types

| Type        | Description              |
|-------------|--------------------------|
| TRACE_JUMP  | trace_id change detected |
| ERROR       | error occurrence         |
| CRITICAL    | critical error           |
| CLOCK_JUMP  | abnormal time shift      |
| REBOOT      | system reboot            |

### 🚀 Extensibility

- Database integration (SQLite / PostgreSQL)
- API integration
- Analytics dashboards
- Real-time monitoring

### 📌 Future Improvements

- Automatic Log rotation (date / size)
- Event severity levels
- Trace-based grouping
- GUI filtering enhancements

### 💬 Notes

This system is designed not as a logging tool, but as a:

👉 An observation and diagnostic system

The true time reference is UTC.

Local time conversion must be handled ONLY at the presentation layer (Viewer).
