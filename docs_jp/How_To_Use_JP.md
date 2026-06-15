# Info Logger — 使い方

> 対象バージョン: **v1.0.0-rc1**  
> この文書は、現在の Logger_Project / Info Logger Viewer の使い方を説明します。  
> 特に、Eventベース表示、TraceQL検索、FVレシピ、summary_engine、調査レポート出力を含みます。

---

## 1. Info Logger とは

Info Logger は、単なるロガーではありません。

ログを次の流れで扱う診断パイプラインです。

```text
Logger
  ↓
JSON Lines ログ
  ↓
LogDict 検証
  ↓
Event 解析
  ↓
Viewer 表示
  ↓
検索 / 要約 / 出力
```

一番大事な考え方はこれです。

```text
LogDict = 記録
Event   = 意味
```

生ログは「記録」です。  
Event は、その記録を解析して得られた「意味」です。

---

## 2. 重要概念

### 2.1 `level`, `type`, `message`

Viewer では、この3つを明確に分けます。

| 項目 | 意味 | 例 |
| --- | --- | --- |
| `level` | 元ログの重要度 | `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `type` | 解析によって付いた意味 | `TRACE_JUMP`, `REBOOT`, `REPEAT_ERROR` |
| `message` | 実際に起きた内容 | `system_cpu_percent`, `trace_id changed` |

通常ログは基本的にこうです。

```text
type  = None
level = INFO / WARNING / ERROR / CRITICAL
```

解析イベントはこうです。

```text
type  = TRACE_JUMP / REBOOT / REPEAT_ERROR
level = 元ログの level
```

Viewer の Type 欄は次のルールで表示します。

```text
Event.type がある
    → Event.type を表示

Event.type がない
    → Event.level を表示
```

そのため、通常の INFO ログは `INFO`、trace_id の変化は `TRACE_JUMP` と表示されます。

---

## 3. Logger の取得

```python
from logs.log_app import get_logger

logger = get_logger()
```

`AppLogger` を直接作成しないでください。

```python
# NG
AppLogger()
```

Logger が自動で管理するもの:

- `trace_id`
- UTC時刻への正規化
- 発生箇所
- JSON Lines 出力

---

## 4. 基本的なログ出力

### 通常ログ

```python
logger.info("処理開始")
```

### context付きログ

```python
logger.warning(
    "clock_jump_detected",
    context={"diff": 180},
)
```

### 意図と実際の状態を残すログ

```python
logger.info(
    "ユーザーログイン処理",
    context={
        "user_id": user_id,
        "想定状態": "認証成功",
        "実際状態": auth_result,
    },
)
```

### エラーログ

```python
logger.error(
    "database_error",
    action="connect",
    status="failed",
    category="db",
)
```

---

## 5. ログファイル形式

Info Logger は JSON Lines 形式でログを保存します。

```text
1行 = 1つの JSON オブジェクト
```

検証後のログ例:

```json
{
  "level": "INFO",
  "time": "2026-06-15T05:21:33+00:00",
  "trace_id": "ecdab2f96d1149639791c4c3cdd0178c",
  "where": {
    "file": "logs/log_viewer.py",
    "line": 993,
    "function": "reload_log"
  },
  "what": {
    "message": "reload_log prepared"
  },
  "context": {
    "raw_count": 12,
    "valid_count": 12
  },
  "output": "both"
}
```

内部の保存・解析基準は UTC です。  
Viewer だけが、表示用にローカル時間へ変換します。

---

## 6. Viewer の起動

```bash
python -m logs.log_viewer
```

Tkinter GUI が起動します。

TimeZoneData の構築・確認中には、次の表示が出る場合があります。

```text
現在、最新版のTimeZoneDataに書き換え中です。
```

これは、ローカル時刻表示に必要な TimeZoneData を準備している状態です。

---

## 7. Viewer の画面構成

メイン一覧には次の列があります。

| 列 | 内容 |
| --- | --- |
| `type` | Event.type があればそれを表示。なければ level を表示 |
| `time` | 選択中タイムゾーンのローカル時刻 |
| `trace_id` | 起動セッションID |
| `message` | 平文化された message |

詳細ウインドウでは、次のように表示されます。

```text
Type  : TRACE_JUMP
Level : INFO
Time(Local:Asia/Tokyo | JST) : ...
Time(UTC)                    : ...

=== MESSAGE ===
...

--- where ---
File :
Line :
Func :

--- Event ---
from :
to   :

--- Context ---
...
```

通常のログビューアよりも、調査向けに情報を多く出す設計です。

---

## 8. ログの読み込み

Viewer は次に対応しています。

- 最新ログの自動読み込み
- 単一ログファイルを開く
- 複数ログファイルを開く
- 前回開いたログファイルの復元

新しいログを読み込むと、古い表示とキャッシュは破棄されます。

```text
raw_rows      = 新しく読み込んだ LogDict
filtered_rows = []
display_rows  = []
_event_cache  = None
```

Eventキャッシュは、必要になった時だけ新しい `raw_rows` から再生成されます。

---

## 9. 基本検索

検索窓では、通常キーワード検索と TraceQL風の項目検索ができます。

### キーワード検索

```text
cpu
system_cpu_percent
database_error
```

### 日付検索

```text
2026-04-23
```

### 時刻検索

```text
10:15
```

### 日時検索

```text
2026-04-23 15:00
```

### 期間検索

標準の区切りは `..` です。

```text
2026-04-23..2026-04-24
2026-04-23 15:00:31..2026-04-23 15:00:37
```

互換形式として ` - ` も使えます。

```text
2026-04-23 - 2026-04-24
```

日付自体に `-` が含まれるため、基本的には `..` 推奨です。

---

## 10. 項目指定検索

```text
level:ERROR
level:WARNING
message:system_cpu_percent
function:run_test
file:system_monitor.py
context:cpu_percent
trace_id:fc036f388b7542c48117d55c8ec1728c
```

主なエイリアス:

| エイリアス | 対象 |
| --- | --- |
| `level` | 元ログの level |
| `type` | Viewer / Event の表示 type |
| `message`, `msg` | `what.message` / Event message |
| `function`, `func` | `where.function` |
| `file` | `where.file` |
| `trace`, `trace_id` | `trace_id` |
| `context` | `context` |
| `output` | `output` |

---

## 11. Event type 検索

この Viewer は Event を理解します。

解析イベントを直接検索できます。

```text
type:TRACE_JUMP
type:REBOOT
type:REPEAT_ERROR
```

これは通常の level 検索とは別です。

```text
level:ERROR
```

解析結果を探すなら `type:`。  
元ログの重要度を探すなら `level:` です。

---

## 12. Query Error レポート

未完成または不正な TraceQL 入力でも Viewer は落ちません。

例:

```text
level:
```

詳細表示では次のようなレポートになります。

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

typo の候補表示は辞書ベースで、AIは不要です。

---

## 13. Boolean / 除外 / フレーズ検索

### 除外検索

```text
cpu -gpu
message:system -gpu
```

### フレーズ完全一致

```text
"invalid log: missing trace_id"
"system cpu"
```

### AND / OR 検索

```text
level:ERROR OR level:CRITICAL
(level:ERROR OR level:WARNING) -debug
level:WARNING message:system_cpu_percent
```

---

## 14. 数値比較検索

context 内の数値を比較できます。

```text
context.cpu_percent >=20
context.gpu_mem_total_mb>1000
context.cpu_percent <80
```

使用できる演算子:

```text
< <= > >= == !=
```

---

## 15. 正規表現検索

```text
regex "^system_.*"
regex message "^system_.*_status$"
regex context "gpu_.*_mb"
```

不正な正規表現は、どの行にも一致しません。

---

## 16. 類似検索

```text
similar "GPU memory pressure"
similar "reboot or clock jump symptoms"
similar "GPU memory pressure" 0.12
```

現在の実装は、API Keyなしで動く軽量なオフライン近似検索です。

---

## 17. 並び替え / 上位N件検索

```text
level:error sort by time desc
message:system sort by context.cpu_percent desc
top 3 by context.cpu_percent
top 10 by time desc where level:error
```

---

## 18. 集計 / 統計検索

基本形:

```text
集計関数 対象フィールド where 条件
```

例:

```text
count * where level:error
count * where 2026-04-23..2026-04-23
max context.cpu_percent
min context.cpu_percent where context.cpu_percent >=20
avg context.cpu_percent
median context.cpu_percent
mode level
group by level count *
group by message avg context.cpu_percent
```

使用できる関数:

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

---

## 19. FVレシピ

FVレシピは、検索・要約・出力を保存しておくためのレシピファイルです。

レシピでは、次のような要素を定義できます。

```text
TITLE
QUERY
SUMMARY
EXPORT
OUTPUT
```

例:

```text
TITLE: Trace Jump Analysis
QUERY: type:TRACE_JUMP
SUMMARY: on
EXPORT: json
OUTPUT: result_trace_jump.json
```

Viewer で FV レシピを開くと、次の流れになります。

1. レシピを parse する
2. ExecutionPlan を作る
3. Query を検索窓に反映する
4. Viewer が検索を実行する
5. `type:` 系検索なら `display_rows` から FVResult を作る
6. Summary と Export を実行する

`TRACE_JUMP`, `REBOOT`, `REPEAT_ERROR` は生ログ文字列ではなく解析イベントなので、この流れが重要です。

---

## 20. summary_engine

summary_engine は `SummaryResult` を生成します。

含まれる主な情報:

- 件数
- 検索条件
- level別件数
- moduleランキング
- messageランキング
- 数値context統計
- 所見
- 表示用テキスト

例:

```text
検索条件
  条件: type:TRACE_JUMP
  件数: 4

レベル別件数
  - INFO: 4

モジュール上位
  - system_monitor.py: 4

メッセージ上位
  - system_cpu_percent: 4
```

---

## 21. 出力

Viewer は次の出力に対応します。

- 検索結果 Event CSV
- JSON bundle
- 調査レポート JSON
- Summary CSV
- Summary JSON

### JSON bundle 形式

```json
{
  "exported_at": "...",
  "logs": [],
  "events": [],
  "summary": {},
  "report": null
}
```

### 調査レポート形式

```json
{
  "exported_at": "...",
  "logs": [],
  "events": [],
  "summary": {},
  "report": {
    "kind": "investigation_report",
    "format_version": "0.1",
    "condition_text": "type:TRACE_JUMP",
    "timezone": "Asia/Tokyo",
    "log_count": 4,
    "event_count": 4,
    "source_files": []
  }
}
```

---

## 22. 大容量ログとSQLite

大容量ログ向けに、query_engine の SQLite adapter を利用できます。

```python
from query_engine.adapters.sqlite_adapter import SQLiteDocumentStore

with SQLiteDocumentStore("logs.sqlite") as store:
    store.add_documents(documents)
    results = store.search("level:ERROR", limit=100)
```

大量結果の場合:

```python
for batch in store.iter_search("context.cpu_percent >= 80", batch_size=1000):
    for result in batch.results:
        handle(result.document)
```

Logger側から使う場合は `logs.traceql_bridge` を通す方針です。

---

## 23. TimeZoneData 更新

```bash
python -m logs.update_tzdata
```

基準ファイル:

```text
logs/.tzdata_ver_reference
```

例:

```text
2026:2026.2
```

---

## 24. リリース前チェック

```text
□ 単一ログを開く
□ 複数ログを開く
□ 別ログ読み込み時に古いキャッシュが消える
□ type:TRACE_JUMP が検索できる
□ type:REBOOT が検索できる
□ level:ERROR が検索できる
□ 詳細ウインドウが開く
□ JSON bundle が出力できる
□ 調査レポートが出力できる
□ FVレシピが実行できる
□ SummaryWindow が開く
```

---

## 25. まとめ

Info Logger は、構造化ログ、Event解析、診断用Viewerを一体化したシステムです。

```text
記録 → 解析 → 表示 → 要約 → 調査レポート
```

という流れで、プログラムの挙動を可視化します。
