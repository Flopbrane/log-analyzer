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

---

## Architecture Principles

### Long-Term Vision

This project is evolving from a structured logger into a multi-format document analysis platform.

Future architecture:

```text
File
    ↓
Adapter
    ↓
RawRecord
    ↓
Normalizer
    ↓
UnifiedDocument
    ↓
QueryEngine
    ↓
SummaryEngine
    ↓
Viewer
```

The final goal is to support multiple document and log formats while providing a unified search, analysis, and summarization experience.

---

### Layer Responsibilities

#### Adapter Layer

The adapter layer is responsible for:

* reading source files
* detecting file formats
* extracting raw records

The adapter layer must NOT:

* normalize data
* search data
* summarize data
* format UI output

Adapter output should be:

```python
list[RawRecord]
```

#### Normalizer Layer

The normalizer layer is responsible for:

* normalizing field names
* normalizing timestamps
* normalizing common values
* converting source-specific records into common structures

Example:

```text
client_ip
remote_addr
ip_address
    ↓
ip
```

The normalizer layer must NOT:

* search data
* summarize data
* render UI

Normalizer output should be:

```python
NormalizedRecord
```

#### Unified Document Layer

The unified document layer provides a common internal document model regardless of source format.

All downstream systems should operate on unified documents or normalized records rather than source-specific file formats.

#### Query Engine

The query engine is responsible for:

* parsing query expressions
* building query plans
* filtering document collections

The query engine must NOT:

* render UI
* summarize results
* read files directly

#### Summary Engine

The summary engine is responsible for:

* aggregating results
* generating statistical summaries
* detecting trends and anomalies

The summary engine must NOT:

* parse queries
* read files
* render UI

#### Viewer

The viewer is responsible for:

* displaying information
* accepting user input
* triggering search and summary actions

The viewer must NOT:

* perform analysis logic
* parse source file formats
* implement query language logic

---

### Dependency Rules

Allowed dependency direction:

```text
Viewer
    ↓
Bridge / Controller
    ↓
QueryEngine / SummaryEngine
    ↓
Normalizer
    ↓
Adapter
```

Avoid dependency direction:

```text
Adapter → Viewer
SummaryEngine → Adapter
QueryEngine → Viewer
Viewer → Adapter internals
```

Cross-layer dependencies should be minimized. When a layer boundary is needed, use a bridge or controller module rather than importing internals directly.

---

### Context System

Context helpers are shared infrastructure.

Examples:

```python
context_for_program()
context_for_exception()
context_for_loader()
context_for_saver()
```

Context generation should remain independent of:

* Viewer
* Query Engine
* Summary Engine

---

### Future Recipe System

The future system may support user-defined diagnostic recipes.

Example:

```text
Purpose: Check HTTP 500 errors
Filter: status >= 500
Group By: ip
Summary: enabled
```

Recipe files should be translated into internal query plans rather than directly executed.

---

### Design Philosophy

Prefer:

* simple interfaces
* explicit responsibilities
* layer isolation
* human-friendly workflows

Do not optimize for creating a complex query language.

Optimize for helping users quickly understand large amounts of information with minimal technical knowledge.

Core principle:

```text
Adapters do not search.
Normalizers do not summarize.
Query engines do not render.
Summary engines do not search.
Viewers do not analyze.
```

### directory structure

```text
*.fv (Filter & Summary Script)

目的:
検索・要約・出力を自動化するDSL

将来的にMulti Documents Viewerの共通調査言語とする
```
