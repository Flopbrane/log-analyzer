# 設計および仕様 — エージェント向けメモ

> 対象バージョン: **v1.0.0-rc1**  
> この文書は、Logger_Project / Info Logger に関わる将来の保守担当者、アシスタント、コード編集エージェント向けのメモです。

---

## 1. プロジェクトの位置付け

Info Logger は、単なるログ出力ユーティリティではありません。

これは、構造化ロギング、Event 解析、TraceQL 検索、FV レシピ、要約、調査レポート出力までを含むシステムです。

中心となるルールは次のとおりです。

```text
LogDict = 記録
Event   = 意味
```

この区別を崩してはいけません。

---

## 2. 現在のリリース基準

現在の基準バージョンは次のとおりです。

```text
v1.0.0-rc1
```

このバージョンでは、以下の中核パイプラインが動作していることを前提とします。

```text
ログを読み込む
  ↓
LogDict に検証・正規化する
  ↓
Event に要約・解析する
  ↓
Viewer に表示する
  ↓
TraceQL / Event-aware 検索を行う
  ↓
summary_engine に渡す
  ↓
CSV / JSON / 調査レポートとして出力する
```

---

## 3. 絶対に守るべきデータモデル規則

### 3.1 `level`

`level` は、logger が元ログとして記録した本来の重要度です。

例:

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
REBOOT
```

### 3.2 `type`

`type` は、解析によって付与された意味です。

例:

```text
TRACE_JUMP
REBOOT
REPEAT_ERROR
```

通常ログでは、`type` は `None` になる場合があります。

### 3.3 `message`

`message` は、実際に起きた内容です。

例:

```text
system_cpu_percent
reload_log prepared
trace_id changed
```

任意の message 文字列を `type` に入れてはいけません。

message から type への正規化を行う場合でも、既知の `EventType` または `LogLevel` の name/value に一致するものだけを返してください。未知の message は必ず `None` を返す必要があります。

---

## 4. Viewer の表示規則

Type 列は、次のルールに従う必要があります。

```python
if event.type is not None:
    display_type = event.type.name
else:
    display_type = event.level.name
```

コード内で `normalize_message_type_name()` を使う場合でも、既知の値だけを受け入れ、最終的には `event.level.name` にフォールバックしなければなりません。

---

## 5. Viewer 状態の責務

Viewer の状態は、必ず分離して管理してください。

```text
raw_rows
    検証済みの元 LogDict 行すべて

filtered_rows
    表示中の Events に対応する LogDict 行

display_rows
    Treeview、詳細表示、CSV、JSON、レポート出力で使う唯一の Event リスト

_event_cache
    summarize(raw_rows) のキャッシュ結果
```

元ログが差し替えられた場合は、次のようにする必要があります。

```python
self.raw_rows = logs
self.filtered_rows = []
self.display_rows = []
self._event_cache = None
```

キャッシュ無効化を迂回する変更は危険です。

---

## 6. Event キャッシュ規則

必要がない限り、Viewer の複数箇所から `summarize(self.raw_rows)` を繰り返し呼び出してはいけません。

以下を使ってください。

```python
self._get_event_cache()
```

期待される挙動:

```text
初回使用:
    キャッシュを再構築する

同じログ:
    キャッシュを再利用する

新しいログ:
    キャッシュをクリアして再構築する
```

---

## 7. Event-aware 検索規則

`type:TRACE_JUMP` は、生ログではなく Events を検索しなければなりません。

理由:

```text
TRACE_JUMP は解析によって生成されます。
LogDict の生テキスト内に存在しない場合があります。
```

同じことは以下にも当てはまります。

```text
type:REBOOT
type:REPEAT_ERROR
```

元ログの重要度を検索する場合は、次を使ってください。

```text
level:ERROR
```

---

## 8. FV レシピ規則

FV レシピの実行では、Event-aware クエリを尊重する必要があります。

推奨フロー:

```text
parse_fv_text()
  ↓
build_execution_plan()
  ↓
Viewer の search_var に設定
  ↓
apply_filter()
  ↓
if query uses Event type:
      display_rows から FVResult を作る
   else:
      raw_rows に対して通常の execution_plan を実行する
```

`type:TRACE_JUMP` が生ログ内に存在しないという理由だけで、結果 0 件になってはいけません。

---

## 9. Summary 規則

`summary_engine` は GUI 非依存のままにしてください。

Viewer は、次のような bridge / helper を通して選択ログを渡すべきです。

```text
summary_bridge
```

Summary result には、次のような情報が含まれる場合があります。

```text
total_count
condition_text
level_counts
module_ranking
message_ranking
context_numeric_stats
insights
text
```

---

## 10. Export 規則

Export では、記録と解析結果の両方を保持する必要があります。

JSON bundle / 調査レポートには、以下を含めてください。

```json
{
  "logs": [],
  "events": [],
  "summary": {},
  "report": {}
}
```

調査レポートのメタデータには、少なくとも以下を含めてください。

```json
{
  "kind": "investigation_report",
  "format_version": "0.1",
  "condition_text": "...",
  "timezone": "...",
  "log_count": 0,
  "event_count": 0,
  "source_files": []
}
```

---

## 11. Logger 内部の安全規則

logger 内部では、通常の logger メソッドを呼んではいけません。

禁止箇所の例:

```text
_log
_build_log_record
_safe
_emit
```

再帰的な logging は無限ループを引き起こす可能性があります。

logger 内部の警告には、`print()` または専用の内部処理を使ってください。

---

## 12. 時刻規則

UTC が内部の正です。

```text
記録: UTC
保存: UTC
解析: UTC
表示: 選択されたローカルタイムゾーン
```

Viewer のタイムゾーン変更によって、保存済みログを変更してはいけません。

---

## 13. TraceQL 境界規則

Logger / UI コードが `query_engine` に直接依存してはいけません。

以下を使ってください。

```text
logs.traceql_bridge
```

境界は次の形です。

```text
logs / viewer
  ↓
logs.traceql_bridge
  ↓
query_engine
```

---

## 14. Query Error 規則

不正な TraceQL によって Viewer がクラッシュしてはいけません。

次の情報を持つ、診断可能な query error report に変換してください。

```text
query text
error message
caret position
expected syntax
dictionary-based suggestions
```

クエリ候補の提案に AI は必須ではありません。

---

## 15. File Adapter 規則

外部ログ形式は、メイン解析に入る前に `LogDict` へ正規化してください。

外部形式を Viewer 固有コードに漏らしてはいけません。

推奨フロー:

```text
external file
  ↓
file_adapter
  ↓
list[dict]
  ↓
log_validator
  ↓
list[LogDict]
```

---

## 16. 大容量ログ規則

現在の Viewer は、正確性優先です。

大容量ログについては、将来的に以下で対応することを優先してください。

```text
SQLite adapter
batch search
paging
indexed search
lazy Event generation
```

速度のために Event の正確性を早まって壊してはいけません。

---

## 17. ドキュメント更新規則

以下の概念に関わるコードを変更した場合は、ドキュメントも更新してください。

```text
level/type/message
Event structure
Viewer state model
FV recipe flow
summary_engine output
investigation report schema
TraceQL bridge boundary
```

---

## 18. 推奨 commit スタイル

簡潔な conventional-style のメッセージを使ってください。

例:

```text
docs: update usage docs for v1.0.0-rc1
docs: document event-aware viewer pipeline
feat: add investigation report metadata
fix: clear event cache when logs are replaced
refactor: separate display rows from raw rows
```

---

## 19. リリースチェックリスト

stable release に tag を付ける前に、以下を確認してください。

```text
□ 単一ログを開く
□ 複数ログを開く
□ 別ログを再読み込みし、キャッシュがクリアされることを確認する
□ type:TRACE_JUMP を検索する
□ type:REBOOT を検索する
□ level:ERROR を検索する
□ 詳細ウインドウを開く
□ FV レシピを実行する
□ SummaryWindow を表示する
□ JSON bundle を出力する
□ 調査レポートを出力する
□ source_files と report metadata を検証する
```

---

## 20. 保守上の警告

Type 列に任意の message 文字列を表示させるような「手早い修正」は避けてください。

これは過去に発生した失敗パターンです。

次のモデルを守ってください。

```text
level   = original severity
type    = analysis meaning
message = what happened
```

これが現在の Viewer の核心です。
