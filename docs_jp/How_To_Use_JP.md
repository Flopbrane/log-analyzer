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

Log Viewer の検索テキストボックスには、
ログの文字列だけでなく、

- 日付・時刻
- 期間
- 項目指定
- フレーズ完全一致
- 正規表現検索
- 類似検索
- 数値比較
- AND/OR条件
- ignore条件
- 並び替え・上位N件検索
- 集計検索を入力できます。

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

### 🔵 ⑨ 除外検索

先頭に `-` を付けると、その単語を含むログを除外できます。

```text
cpu -gpu
message:system -gpu
```

---

### 🔵 ⑩ フレーズ完全一致検索

`"` で囲むと、その文字列をひとまとまりのフレーズとして検索します。
スペースや `:` を含む文字列をそのまま探したい場合に便利です。

```text
"invalid log: missing trace_id"
"system cpu"
```

---

### 🔵 ⑪ AND / OR 検索

複数の条件を並べると、基本的には AND 条件として扱われます。
明示的に `AND`、`OR`、括弧も使えます。

```text
level:WARNING message:system_cpu_percent
level:ERROR OR level:CRITICAL
(level:ERROR OR level:WARNING) -debug
```

---

### 🔵 ⑫ 数値比較検索

`context` 内の数値などに対して、比較条件を指定できます。

```text
context.cpu_percent >=20
context.gpu_mem_total_mb>1000
context.cpu_percent <80
```

使用できる演算子：

```text
< <= > >= == !=
```

---

### 🔵 ⑬ ignore 条件

`(ignore: 条件)` を付けると、通常検索で拾った候補から、指定条件に一致するログを除外できます。

```text
cpu (ignore: context.cpu_percent <80)
system (ignore: gpu)
```

---

### 🔵 ⑭ 正規表現検索

`regex` を使うと、正規表現で検索できます。
ログ全体を対象にすることも、特定フィールドだけを対象にすることもできます。

```text
regex "^system_.*"
regex message "^system_.*_status$"
regex context "gpu_.*_mb"
```

正しくない正規表現は、どのログにも一致しません。

---

### 🔵 ⑮ 類似検索

`similar` を使うと、完全なキーワード一致ではなく、近い内容のログを検索できます。

```text
similar "GPU memory pressure"
similar "reboot or clock jump symptoms"
similar "GPU memory pressure" 0.12
```

現在の実装は、API Keyなしで動く TF-IDF 風の軽量特徴量 + 文字n-gram による近似検索です。
OpenAI embeddings を使う本格的な意味検索は将来差し替え予定として、コード内にコメントアウトで残しています。

引用符の後ろに数値を付けると、類似度しきい値を変更できます。
数値を大きくすると厳しめ、小さくすると広めに拾います。
明示的な `sort by` を付けない場合、近いログから順に表示されます。

---

### 🔵 ⑯ 並び替え・上位N件検索

`sort by` を使うと検索結果を並び替えできます。
`top N by` を使うと、指定フィールドの上位N件だけを表示できます。

```text
level:error sort by time desc
message:system sort by context.cpu_percent desc
top 3 by context.cpu_percent
top 10 by time desc where level:error
```

並び替え対象のフィールドを持たないログは、フィールドを持つログの後ろに表示されます。

---

### 🔵 ⑰ 集計検索・統計検索

検索窓から、ログの件数や数値の最大値・最小値・平均値・中央値・最頻値を確認できます。
集計検索を使うと、集計対象になったログだけが一覧に表示され、検索欄の右側に集計結果が表示されます。

基本形式：

```text
集計関数 対象フィールド where 条件
```

`where 条件` は省略できます。
`where` の後ろには、通常検索と同じ構文を使えます。
日付範囲や数値比較も指定できます。

使用できる集計関数：

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

#### 件数を数える

```text
count * where level:error
count * where 2026-04-23..2026-04-23
```

`count *` は、条件に一致したログ行数を数えます。

#### 最大値・最小値

```text
max context.cpu_percent
max context.cpu_percent where 2026-04-23..2026-04-23
min context.cpu_percent where context.cpu_percent >=20
```

#### 平均値

```text
avg context.cpu_percent
ave context.cpu_percent
mean context.cpu_percent
```

`avg`、`ave`、`mean` は平均値として扱われます。

#### 中央値

```text
median context.cpu_percent
```

#### 最頻値

```text
mode level
group by level count *
group by message avg context.cpu_percent
```

`mode` は `level` のような文字列項目にも使用できます。

#### グループ別集計

```text
group by level count *
group by message avg context.cpu_percent
```

`group by` を使うと、指定したフィールドごとに集計結果を分けて表示できます。

#### 集計検索の注意

- `max`、`min`、`avg`、`ave`、`mean`、`median` は数値に対して使用します。
- `mode` は文字列にも使用できます。
- `group by フィールド 集計関数 対象フィールド` でグループ別集計できます。
- 対象フィールドが存在しないログは、集計対象から外れます。
- 集計検索時も、一覧には集計に使われたログが表示されます。

---

### 🔵 ⑱ よく使う検索例

```text
2026-04-23
2026-04-23..2026-04-24
10:15
level:ERROR
message:test_error
context:cpu_percent
file:system_monitor.py
cpu -gpu
"invalid log: missing trace_id"
regex message "^system_.*_status$"
similar "GPU memory pressure"
context.cpu_percent >=20
level:ERROR OR level:CRITICAL
top 3 by context.cpu_percent
count * where level:error
avg context.cpu_percent
group by level count *
```

---

### 💡 検索入力の考え方

- 単語だけなら通常検索
- `level:` や `message:` が付くと項目指定検索
- `..` が含まれると期間検索
- ` - ` は互換用の期間検索
- `-gpu` のように `-` が先頭に付くと除外検索
- `"..."` で囲むとフレーズ完全一致検索
- `AND` / `OR` / 括弧で条件検索
- `regex` で始まると正規表現検索
- `similar` で始まると類似検索
- `context.cpu_percent >=20` のように書くと数値比較検索
- `sort by` / `top N by` で並び替え・上位N件検索
- `count`、`max`、`avg` などで始まると集計検索
- `group by` でグループ別集計検索
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

として設計されています。
