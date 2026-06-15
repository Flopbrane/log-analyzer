# Info Logger（日本語版）

![version](https://img.shields.io/badge/version-v1.0.0--rc1-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![stars](https://img.shields.io/github/stars/Flopbrane/log-analyzer?style=social)

> ⚠ Python 3.9 以上が必要です

**Info Logger** は、構造化ログ・分析・GUI表示・要約・調査レポート出力を一体化したログ診断システムです。

> これは単なるロガーではありません。  
> **プログラムの挙動を理解するための診断システム**です。

- English version → [README.md](README.md)

---

## ✨ 現在の状態: v1.0.0-rc1

`v1.0.0-rc1` は、Info Logger の最初のリリース候補版です。

現在、以下の診断パイプラインが接続されています。

```text
構造化ログ出力
↓
LogDict 検証
↓
Event 解析
↓
TraceQL / type 検索
↓
FV レシピ実行
↓
summary_engine 要約
↓
GUI 詳細表示
↓
CSV / JSON / 調査レポート保存
```

このリリース候補には、以下が含まれます。

- JSON Lines による構造化ログ
- `LogDict` の検証と正規化
- `Event.type`, `Event.level`, `message` の分離
- Trace jump 検出
- システム再起動検出
- 繰り返しエラー検出
- 日本語 / 英語 GUI Viewer
- TraceQL bridge 経由の検索
- FV レシピ実行
- Summary engine による要約
- CSV / JSON 出力
- 調査レポート出力
- UTC記録 + Viewer側ローカル時刻表示
- 大容量ログ向け SQLite アダプター

---

## 🧠 基本コンセプト

一般的なロガーは、文字列としてログを記録するだけです。

Info Logger は、ログを構造化された記録として扱い、さらに解析によって意味のあるイベントへ変換します。

```text
LogDict = 記録
Event   = 意味
```

特に重要な設計ルールは次の3つです。

```text
level   = 元ログの重要度
type    = 解析によって付与された分類
message = 実際に起きた内容
```

例:

```text
level: INFO
type : TRACE_JUMP
message: trace_id changed
```

これにより、元ログの重要度と、解析によって発見された意味を分離して扱えます。

---

## ✨ 主な機能

### 🔍 trace_id による追跡

- 処理の流れをセッション単位で追跡
- アプリケーション起動やログ切り替わりを追いやすくする

### 📍 発生箇所の自動記録

- ファイル
- 行番号
- 関数名
- モジュール

を自動で記録します。

### 🧠 Event 解析

- Trace jump
- システム再起動
- 繰り返しエラー
- ERROR / CRITICAL の重要度管理

### 🖥️ GUI Viewer

- 単一ログ / 複数ログを読み込み
- `type`, `level`, `trace_id`, テキストによる検索
- Event 詳細表示
- RAW JSON 表示
- 日本語 / 英語 UI 切り替え

### 📘 Summary Engine

検索・フィルタ後のログから、調査しやすい要約を生成します。

- レベル別件数
- モジュールランキング
- メッセージランキング
- 数値 context の統計
- 所見テキスト

### 📄 調査レポート出力

調査レポートは JSON として保存され、以下を保持します。

```text
logs     = 元ログ
events   = 解析イベント
summary  = 要約結果
report   = 調査メタ情報
```

### 🔎 TraceQL Bridge

高度な検索判定は `logs/traceql_bridge.py` を経由します。

```text
logs / viewer
    ↓
logs.traceql_bridge
    ↓
query_engine
```

Viewer や Logger 固有処理が、検索コアに直接依存しないようにするための設計です。

### 🧭 Query Error レポート

検索構文エラーで Viewer を落とさず、`QUERY ERROR` として表示します。

例:

```text
level:
     ^

Did you mean:
- level:ERROR
- level:WARNING
- level:INFO
```

### 🗄️ SQLite アダプター

大容量ログを SQLite に保存し、バッチ検索できます。

- 数百MB〜数GB級ログを想定
- `iter_search()` による分割処理
- Viewer側では `traceql_bridge.py` 経由で扱う方針

### 🕒 Timezone 対応

- 内部記録は UTC
- Viewer 表示は選択したローカルタイムゾーン
- `logs/.tzdata_ver_reference` に確認済み tzdata を記録
- `python -m logs.update_tzdata` で明示更新可能

---

## 🖼️ スクリーンショット

### メインウインドウ

<img src="docs/image/main_window.png" alt="Log Viewer Main Window" width="900">

### 詳細ウインドウ

<img src="docs/image/sub_window.png" alt="Log Viewer Detail Window" width="600">

---

## ⚡ クイックスタート

### 1. クローン

```bash
git clone https://github.com/Flopbrane/log-analyzer.git
cd log-analyzer
```

### 2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 3. 基本的な使い方

```python
from logs.log_app import get_logger

logger = get_logger()

logger.info("処理開始")
logger.warning("異常検知", context={"value": 42})
logger.error("処理失敗", status="failed")
```

### 4. Viewer 起動

```bash
python -m logs.log_viewer
```

---

## 🔍 検索例

```text
type:TRACE_JUMP
level:ERROR
message:"system_cpu_percent"
trace_id:230b4afdc5cc47349267e9ab954c1a05
```

FV レシピを読み込むと、レシピ内の検索条件を Viewer に反映し、要約やレポート出力まで実行できます。

例:

```text
type:TRACE_JUMP
```

---

## 🧱 アーキテクチャ

```text
Application
↓
Logger / AppLogger
↓
JSON Lines log file
↓
log_validator
↓
log_searcher / analyzer
↓
Event
↓
traceql_bridge
↓
query_engine / SQLite adapter
↓
summary_engine
↓
log_viewer
↓
CSV / JSON / investigation report
```

---

## 🧠 設計思想

- ログは単なる文字列ではなく、構造化された記録
- Event はログから抽出された意味
- `trace_id` は実行セッションを表す
- 内部時刻は UTC
- 表示時刻は Viewer 側で選択
- Viewer / Logger / Query Engine / Summary Engine を分離
- Query Engine への入口は bridge に集約
- レポートには元ログと解析イベントの両方を残す

| 層 | 役割 |
| --- | --- |
| Logger | 記録 |
| Validator | 正規化・保護 |
| Searcher / Analyzer | ログを Event に変換 |
| Bridge | LogDict を TraceQL Document に変換 |
| Query Engine | 検索 / 判定 / バッチ処理 |
| Summary Engine | フィルタ後ログの要約 |
| Viewer | 表示・出力 |

---

## 📂 プロジェクト構成

```text
logs/
├ multi_info_logger.py
├ log_app.py
├ log_storage.py
├ log_validator.py
├ log_searcher.py
├ log_viewer.py
├ display_formatter.py
├ traceql_bridge.py
├ summary_bridge.py
├ log_types.py
├ time_utils.py
└ log_paths.py

summary_engine/
├ summary_engine.py
├ summary_types.py
├ aggregators/
└ analyzers/

query_engine/
├ adapters/
│ ├ logs.py
│ └ sqlite_adapter.py
├ evaluators/
│ ├ memory.py
│ └ sql.py
├ parser.py
└ models.py

fv_engine/
├ fv_parser.py
├ fv_interpreter.py
├ fv_runner.py
├ fv_plan.py
└ example/
```

---

## 📊 Summary Engine

Summary Engine は、検索・フィルタ後のログを調査しやすい形に要約します。

出力例:

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

## 📄 調査レポート

調査レポートには、以下の情報が保存されます。

```json
{
  "kind": "investigation_report",
  "format_version": "0.1",
  "condition_text": "type:TRACE_JUMP",
  "timezone": "Asia/Tokyo",
  "log_count": 4,
  "event_count": 4,
  "source_files": []
}
```

これにより、後から

- どの条件で調査したか
- どのタイムゾーンで表示したか
- どのログファイルを対象にしたか
- 元ログと解析イベントがどう対応しているか

を確認できます。

---

## 🗄️ 大容量ログと SQLite 検索

巨大な JSONL ログを全件メモリに読み込むのが難しい場合、SQLite アダプターを使用できます。

```python
from query_engine.adapters.sqlite_adapter import SQLiteDocumentStore

with SQLiteDocumentStore("logs.sqlite") as store:
    store.add_documents(documents)
    results = store.search("level:ERROR", limit=100)
```

大量の検索結果は、バッチ単位で順次処理できます。

```python
for batch in store.iter_search("context.cpu_percent >= 80", batch_size=1000):
    for result in batch.results:
        handle(result.document)
```

---

## 🕒 TimeZoneData 更新

IANA tzdata は、サマータイムや政治的なタイムゾーン変更により不定期で更新されます。

```bash
python -m logs.update_tzdata
```

基準ファイル:

```text
logs/.tzdata_ver_reference
```

形式例:

```text
2026:2026.2
```

---

## 📚 ドキュメント

- 設計書 → `docs/Design.md`
- 使い方 → `docs_jp/How_To_Use_JP.md`
- English overview → `README.md`

---

## 🚀 今後の展開

- リアルタイム監視
- Web ダッシュボード
- 通知連携
- 大規模インデックス
- 追加ストレージバックエンド
- 調査レポート形式の拡張

---

## 📄 ライセンス

MIT License

---

## 🤖 謝辞

本プロジェクトは、ChatGPT（OpenAI）の支援を受けて開発されました。  
ここに深く感謝の意を表します。

なお、本プロジェクトは OpenAI とは関係なく、また公式に承認されたものではありません。

---

## ⭐ サポート

本プロジェクトが役に立ったと感じていただけた場合は、GitHubで ⭐ を付けていただけると励みになります。
