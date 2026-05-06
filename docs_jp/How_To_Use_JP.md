# ログシステム 使い方

---

## 🎯 基本の流れ

- logger取得 → ログ出力 → ログ解析 → 表示

---

## 🟢 ① ロガー取得

```python
from log_app import get_logger

logger = get_logger()
```

---

## 🟢 ② ログ出力

### 基本

```python
logger.info("処理開始")
```

---

### 詳細付き

```python
logger.warning(
    "clock_jump_detected",
    context={"diff": 180}
)
```

---

### カテゴリ付き

```python
logger.error(
    "database_error",
    action="connect",
    status="failed",
    category="db"
)
```

---

## 🟢 ③ ログファイル

保存形式：

- ファイル構造
logs/
  └ app_YYYY-MM-DD.log

- 形式：1行 = 1JSON(JSONL)

- 外部入力が JST の `datetime` でも、保存時には UTC に正規化される
- `logs` フォルダ内の時刻比較・解析基準は UTC
- `log_viewer.py` では表示時のみ JST に変換して扱う

---

## 🟢 ④ ログ解析

```python
from log_searcher import load_logs, analyze_logs
from pathlib import Path

logs = load_logs(Path("logs/app_2026-04-08.log"))
events = analyze_logs(logs)

for e in events:
    print(e)
```

---

## 🟢 ⑤ GUI表示

```bash
python -m logs.log_viewer
# あるいは
python run_viewer.py
```

---

## 🟢 表示内容

|    項目      |     内容     |
| ------------ | ------------ |
|     time     |      時刻    |
|     type     | イベント種別 |
|   trace_id   |  セッション  |
|   message    |     内容     |

---

## 🟢 クリック機能

- 行クリックで詳細JSON表示

---

## 🟢 検索テキストボックスの使い方

Log Viewer の検索テキストボックスには、文字列だけでなく、日付・時刻・期間・項目指定を入力できます。

---

### 🔵 ① 空欄検索

検索欄を空にすると、読み込んだログをすべて表示します。

```text
空欄
```

---

### 🔵 ② 通常のキーワード検索

message、where、context などに含まれる文字列を検索できます。

```text
cpu
error
system_monitor
clock_jump
```

---

### 🔵 ③ 年月日検索

指定した日付のログを表示します。

```text
2026-04-23
2026-04-24
```

---

### 🔵 ④ 時刻検索

指定した時刻を含むログを表示します。

```text
10:15
10:16
```

---

### 🔵 ⑤ 日時検索

年月日と時刻を組み合わせて検索できます。

```text
2026-04-24 10:16
```

秒まで指定する場合：

```text
2026-04-23 15:00:31
```

---

### 🔵 ⑥ 期間検索

期間検索では、`..` を標準の区切りとして使います。

```text
2026-04-23..2026-04-24
```

同じ日を期間形式で指定することもできます。

```text
2026-04-23..2026-04-23
```

時刻まで含めた期間検索も可能です。

```text
2026-04-23 14:49..2026-04-23 14:49
2026-04-23 15:00:31..2026-04-23 15:00:37
```

---

### 🔵 ⑦ 互換形式の期間検索

過去の入力形式との互換として、` - ` も使用できます。

```text
2026-04-23 - 2026-04-24
2026-04-23 15:00:31 - 2026-04-23 15:00:37
```

ただし、日付そのものに `-` が含まれるため、区切りとして使う場合は、前後に半角スペースを入れてください。

```text
OK:
2026-04-23 - 2026-04-24

非推奨:
2026-04-23-2026-04-24
```

基本的には `..` を使うのがおすすめです。

---

### 🔵 ⑧ 項目指定検索

特定の項目を指定して検索できます。

#### level 指定

```text
level:ERROR
level:WARNING
level:INFO
```

#### message 指定

```text
message:test_error
message:system_cpu_percent
message:system_gpu_status
```

#### where.function 指定

```text
function:run_test
```

#### where.file 指定

```text
file:system_monitor.py
```

#### context キー指定

```text
context:cpu_percent
context:gpu_mem_total_mb
```

#### trace_id 指定

```text
trace_id:fc036f388b7542c48117d55c8ec1728c
```

---

### 🔵 ⑨ よく使う検索例

```text
2026-04-23
2026-04-23..2026-04-24
10:15
level:ERROR
message:test_error
context:cpu_percent
file:system_monitor.py
```

---

### 💡 検索入力の考え方

- 単語だけなら通常検索
- `level:` や `message:` が付くと項目指定検索
- `..` が含まれると期間検索
- ` - ` は互換用の期間検索
- 空欄にすると全件表示

---

## ⚠️ 注意点

### ❌ loggerを直接生成しない

```python
AppLogger()  # NG
```

---

### ✔ 必ずこれ

```python
get_logger()
```

---

### ❌ trace_idを自分で作らない

- trace_idは「起動に対して一意のID」と定義しているため

---

### ✔ loggerに任せる

- whereは自動取得
- trace_idも自動生成
- JST の `datetime` を渡しても logger 側で UTC に変換される
- 各ファイルのトラップでは、必要な情報を記述・取得するだけで良い

---

## 💡 よくある使い方

### デバッグ

```python
logger.debug("変数確認", context={"value": x})
```

---

### フィルタ機能

- trace_idで絞り込み可能
- typeで絞り込み可能
- Resetで解除

---

### エラー検知

```python
logger.error("処理失敗", status="failed")
```

---

### システム監視

```python
logger.info("cpu_usage", context={"cpu": 30})
```

---

### 過去ログ読み込み

- 過去ログ読み込み

---

### 日付範囲選択

- カレンダーで期間指定
- 存在する日のみ選択可能

---

## 🚀 発展

- イベントフィルタ
- trace単位分析
- グラフ化

---

## 💬 まとめ

このログシステムは

- 出力ツールではなく
- 状態監視・解析ツール

として設計されている。
