# Purpose

- "*.fv"を調査レシピとして扱う

## Rules

- Viewer依存禁止

- 既存のquery_engineを書き換えない

## Responsibilities

- *.fv を解析する
- QUERY を query_engine へ委譲する
- SUMMARY を summary_engine へ委譲する
- EXPORT を result_exporter へ委譲する
- 実行結果を統合する

fv_parser
*.fv → FVRecipe

fv_interpreter
FVRecipe → ExecutionPlan

fv_runner
ExecutionPlan 実行

query_engine
検索担当

summary_engine
要約担当

result_exporter
出力担当

FVRecipe
    レシピ定義

ExecutionPlan
    実行計画

FVResult
    実行結果

---

## Data Flow 1 (Main data flow diagram)

```text
*.fv(text_file)
 ↓
fv_parser
 ↓
FVRecipe
 ↓
fv_interpreter
 ↓
ExecutionPlan
 ↓
fv_runner
 ├─ query_engine
 │    ↓
 │  QueryResult
 │
 ├─ summary_engine
 │    ↓
 │  SummaryResult
 │
 └─ result_exporter
      ↓
    CSV / JSON
 ↓
FVResult
```

## Data Flow 2 (Simplified diagram)

```text
FV Text
 ↓
FVRecipe
 ↓
ExecutionPlan
 ↓
FVResult
```

---

## Dependency Flow

```text
fv_engine
 │
 ├─ query_engine
 ├─ summary_engine
 └─ result_exporter
```

### Forbidden Dependency

```text
query_engine
    ↓
fv_engine

summary_engine
    ↓
fv_engine

result_exporter
    ↓
fv_engine
```

**逆方向の依存は禁止。**

---

## Recommendation: When using SummaryEngine

- fv_engine は検索エンジンではない。

- fv_engine は調査レシピエンジンである。

---

## Important matters

QUERY: は query_engine へ委譲すること。

SUMMARY: は summary_engine へ委譲すること。

EXPORT: は result_exporter へ委譲すること。

fv_engine 自身は検索処理・要約処理を実装しない。

**役割は orchestration のみ。**

---

## Prohibitions

- query_engine を再実装しない
- summary_engine を再実装しない
- result_exporter を再実装しない
- GUIへ依存しない
- Viewerへ依存しない

---

### example

SummaryEngineの出力: "このレシピは、材料Aと材料Bを使用して、手順1、手順2、手順3で作成されます。"  

### Recommendation

fv_engine は Orchestrator である。

検索処理:
    query_engine

要約処理:
    summary_engine

出力処理:
    result_exporter

へ委譲すること。

## Forbidden

- 検索処理を実装しない
- 要約処理を実装しない
- Export処理を実装しない
- GUI処理を実装しない
- query_engineへ依存を逆流させない
- summary_engineへ依存を逆流させない
- result_exporterへ依存を逆流させない
- Viewerへ依存を逆流させない

---

## Scope (v0.1)

実装対象

- TITLE
- QUERY
- SUMMARY
- EXPORT

未実装

- SOURCE
- SQL
- PURPOSE
- REPORT

---

## Future Vision

**予約語を追加する時は必ず,fv_spec_v0_1.md と fv_engine/AGENT.md を同時に更新すること。**

fv_engine は将来的に  
調査レシピ言語 (*.fv) の実行基盤となる。  

現在は Logger_Project を対象とするが、  
将来的には Multi Documents Viewer に対応する。  

対象例:

- JSON
- CSV
- SQLite
- Apache Log
- Nginx Log
- Markdown
- Text
- PDF
- Excel
- Word
- Access
- PowerPoint
- HTML
- XML
- YAML
- Source Code
- その他、様々なドキュメント形式
- さらに、APIやWebサービスなどの外部データソースも対象とする可能性がある。
