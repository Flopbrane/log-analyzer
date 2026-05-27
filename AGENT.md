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

This layer may import from `query_engine`.

---

## Bridge Layer

Communication between LoggerViewer and TraceQL Core must go through:

```text
traceql_bridge.py
```

Avoid direct imports from UI modules into `query_engine`.

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

Maintain clean dependency direction to support future package separation.
