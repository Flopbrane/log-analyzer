# FV Specification v0.1

## Overview

FV (Filtering & Summary Recipe) は、検索・要約・出力を定義するための調査レシピファイルである。

FV はプログラミング言語ではない。

FV の目的は、ユーザーがメモ帳等のテキストエディタで調査手順を記述し、同じ調査を再利用可能にすることである。

---

## Basic Structure

FV ファイルは UTF-8 テキストとして保存する。

拡張子:

```text
*.fv
```

基本構造:

```text
TITLE:
...

QUERY:
...

SUMMARY:
...

EXPORT:
...
```

---

## Reserved Words

v0.1 で使用可能な予約語

```text
TITLE
QUERY
SUMMARY
EXPORT
```

---

## TITLE

調査名を記述する。

例:

```text
TITLE:
認証障害調査
```

---

## QUERY

検索条件を記述する。

QUERY の内容は query_engine へ委譲する。

例:

```text
QUERY:
level:ERROR
```

複数行記述可能。

例:

```text
QUERY:
level:ERROR
and module:auth
```

---

## SUMMARY

要約実行の有無を指定する。

使用可能な値:

```text
ON
OFF
```

例:

```text
SUMMARY:
ON
```

---

## EXPORT

出力形式を指定する。

使用可能な値:

```text
CSV
JSON
NONE
```

例:

```text
EXPORT:
CSV
```

---

## Example

```text
TITLE:
認証エラー調査

QUERY:
level:ERROR
and module:auth

SUMMARY:
ON

EXPORT:
CSV
```

---

## Processing Flow

```text
FV File
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
    ↓
query_engine
    ↓
summary_engine
    ↓
result_exporter
```

---

## Responsibilities

QUERY:
query_engine へ委譲

SUMMARY:
summary_engine へ委譲

EXPORT:
result_exporter へ委譲

fv_engine は検索処理を実装しない。

fv_engine は要約処理を実装しない。

fv_engine は出力処理を実装しない。

fv_engine は orchestration のみを担当する。

---

## Future Extensions

将来的に追加を検討する項目

```text
SOURCE
SQL
PURPOSE
TOP_MESSAGE
TOP_MODULE
TOP_IP
REPORT
```

これらは v0.1 の対象外とする。

---

## Version

Current Version:

```text
FV Specification v0.1
```
