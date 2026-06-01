# AGENT.md

## Project Architecture Policy

This project is divided into multiple logical layers.

---

## Core Rule

`query_engine/` is the independent core engine.

The core engine MUST NOT depend on:

* `logs/`
* GUI modules
* Viewer-specific modules
* tkinter
* UI helper modules
* logger application modules

Allowed dependency direction:

```text
logs
    ↓
traceql_bridge
    ↓
query_engine
```

Forbidden dependency direction:

```text
query_engine
    ↓
logs
```

---

## Summary Engine Responsibility

The `summary_engine/` package is responsible for:

* aggregation
* statistical summaries
* anomaly summaries
* module ranking
* error ranking
* human-readable summaries
* future insight generation

Example:

```text
Query Result
    ↓
Summary Engine
    ↓
Human Summary
```

The summary layer must remain independent from GUI code.

Allowed dependency direction:

```text
logs
    ↓
traceql_bridge
    ↓
query_engine

logs
    ↓
summary_bridge
    ↓
summary_engine
```

Forbidden dependency direction:

```text
summary_engine
    ↓
logs
```

The summary layer should be reusable for:

* JSON
* CSV
* SQLite
* Log files
* AST analysis
* Security logs
* Future document analysis

---

## query_engine Responsibility

The `query_engine/` package is responsible for:

* parser
* AST
* evaluator
* matcher
* similarity
* adapters
* document abstraction
* generic utilities

The core engine must remain reusable and independent.

It should be possible to publish `query_engine/` as a standalone package.

---

## logs Responsibility

`logs/` is the application/UI layer.

Responsibilities:

* GUI
* LogViewer
* timezone display
* log formatting
* search UI
* application integration

This layer should access `query_engine` through `traceql_bridge.py`.

---

## TraceQL Bridge Layer

Communication between LoggerViewer and TraceQL Core must go through:

```text
traceql_bridge.py
```

Avoid direct imports from UI modules into `query_engine`.

---

## Summary Bridge Layer

Communication between LogViewer and Summary Engine must go through:

```text
summary_bridge.py
```

Allowed direction:

```text
LogViewer
    ↓
summary_bridge
    ↓
summary_engine
```

Avoid direct imports from UI modules into summary_engine.

The bridge layer exists to:

* isolate UI from summary internals
* simplify future refactoring
* prevent dependency leaks
* support future engine replacement

Viewer code should not directly access:

* aggregators
* analyzers
* summary generators

Use bridge functions instead.

---

## Dependency Cleanup Policy

When refactoring imports:

* move generic logic into `query_engine`
* keep UI-specific logic inside `logs`
* avoid circular imports
* avoid cross-layer helper imports
* prefer utility extraction over direct coupling

---

## Search/Text Processing Policy

Generic text processing:

* tokenization
* normalization
* parser helpers
* similarity algorithms

should live in `query_engine`.

UI-specific search behavior should remain in `logs`.

---

## Testing Policy

Tests should follow the same architecture boundaries.

Core tests:

```text
tests/query_engine/
```

UI tests:

```text
tests/logs/
```

Avoid mixing UI and core logic in the same test file.

---

## Long-Term Goal

The project is evolving toward:

* reusable TraceQL core
* independent LogViewer application
* pluggable adapters
* multi-document analysis engine
* scalable query/evaluation backends
* reusable Summary Engine
* Insight generation layer
* human-readable event summaries
* context-driven analytics

Maintain clean dependency direction to support future package separation.
