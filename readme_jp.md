# Info Logger（日本語版）

![version](https://img.shields.io/badge/version-v0.2.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![stars](https://img.shields.io/github/stars/Flopbrane/log-analyzer?style=social)
>⚠ Python 3.9 以上が必要です

Info Logger は、  
**ログ出力・分析・可視化を一体化したログシステム**です。

---

## メインウインドウ

<img src="docs/image/main_window.png" alt="Log Viewer Main Window" width="900">

## 🔍 詳細ウインドウ

<img src="docs/image/sub_window.png" alt="Log Viewer Sub Window" width="600">

## 🎯 これは何？

一般的なロガーは **「ログを出すだけ」** です。

**Info Logger は違います**：

- ✅ 構造化ログ（JSON Lines）
- ✅ 自動分析（エラー・trace・再起動検出）
- ✅ GUI Viewer による即時確認

👉 ログは単なる出力ではなく  
👉 **「状態変化＝イベント」**として扱います

---

## ✨ 主な特徴

### 🔍 trace_id による追跡

- 処理の流れをセッション単位で追跡可能
- trace_id は、アプリケーションの起動ごとに一意に割り当てられるIDです。

---

### 📍 発生箇所の自動取得

- ファイル / 行 / 関数を自動記録

---

### 🧠 ログ解析機能

- ERROR / CRITICAL 検出
- trace_idの変化（TRACE_JUMP）
- システム再起動検出

---

### 🖥️ GUI Viewer

- ログを即時表示
- フィルタ（type / trace_id）
- JSON詳細表示
- 日本語 / 英語表示に対応

---

### 🕒 時刻管理

- 内部処理：UTC
- 表示：ローカル時間（JST）

---

### 🔎 TraceQL Bridge

- 高度な検索判定は `logs/traceql_bridge.py` を経由
- `logs` 側から `query_engine` を直接 import しない設計
- LogDict を TraceQL 用 Document に変換してから解析

---

### 🗄️ SQLiteアダプター

- 大容量ログを SQLite に保存して検索可能
- 数百MB〜数GB級のログを想定
- `iter_search()` によるバッチ処理に対応
- Logger側から利用する場合も `traceql_bridge.py` 経由を推奨

---

## ⚡ クイックスタート

### ① クローン

```bash
git clone https://github.com/yourname/Info_Logger.git

cd Info_Logger
```

---

### ② 基本的な使い方

```python
from logs.log_app import get_logger

logger = get_logger()

logger.info("処理開始")
logger.warning("異常検知", context={"value": 42})
logger.error("処理失敗", status="failed")
```

---

### ③ ビューアの起動

```bash
python -m logs.log_viewer
```

👉 GUIでログを即時確認

---

## 🧱 アーキテクチャ

アプリケーション  
↓  
Logger（AppLogger）  
↓  
JSON Linesログファイル  
↓  
log_searcher（解析）  
↓  
traceql_bridge（TraceQLとの境界）  
↓  
query_engine / SQLite adapter  
↓  
イベント（LogEvent）  
↓  
log_viewer（GUI表示）  

---

## 🧠 設計思想

- ログは「イベント」である
- LogRecordは不変（immutable）
- trace_idは「セッション単位」
- 責務分離を徹底

|    層    | 役割 |
| -------- | ---- |
| Logger   | 記録 |
| Searcher | 解析 |
| Bridge   | Logger と TraceQL の橋渡し |
| Query Engine | 検索 / 判定 / バッチ処理 |
| Viewer   | 表示 |

---

## 📂 プロジェクト構成

```text
logs/
├ multi_info_logger.py
├ log_storage.py
├ log_searcher.py
├ log_viewer.py
├ traceql_bridge.py
├ log_types.py
├ time_utils.py
└ log_paths.py

query_engine/
├ adapters/
│ ├ logs.py
│ └ sqlite_adapter.py
├ evaluators/
│ ├ memory.py
│ └ sql.py
├ parser.py
└ models.py

# コアロガー: multi_info_logger.py
# I/O層: log_storage.py
# 解析: log_searcher.py
# TraceQL境界: traceql_bridge.py
# 検索コア: query_engine/
# GUI: log_viewer.py
```

---

## 🔎 TraceQL連携ポリシー

Logger側とTraceQL検索コアは、責務分離のため bridge を介して連携します。

```text
logs / viewer
    ↓
logs.traceql_bridge
    ↓
query_engine
```

`logs` パッケージ内で `query_engine` を直接 import してよいのは、原則として `logs/traceql_bridge.py` のみです。
Viewer、表示整形、Logger固有処理を、再利用可能な検索コアから分離するためのルールです。

---

## 🗄️ 大容量ログとSQLite検索

Ver.0.2.0 では、巨大なJSONLログを扱うための SQLite アダプターを追加しています。

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

Logger Viewer から利用する場合は、`logs.traceql_bridge` を通して受け渡す方針です。

## 📚 詳細ドキュメント

- 設計書 → docs/Design.md
- 使い方 → docs/How_to_use.md

---

## 🚀 今後の展開

- リアルタイム監視
- Webダッシュボード
- 通知連携（Discord / Slack）
- AIによる異常検知
- タイムゾーン対応・管理の強化
- 追加ストレージバックエンド対応

---

## 📄 ライセンス

- MIT License

---

## 💬 コンセプト

### これは単なるロガーではありません

#### 👉 プログラムの挙動を理解するための診断システムです

- ログは　**「状態変化＝イベント」**として扱います。
- ログは　**「文字列」ではなく「構造化されたデータ」**です。
- ログは　**「記録」だけでなく「分析・可視化」**も行えます。
- ログは　**「セッション単位」**で追跡できます。
- ログは　**「発生箇所」を自動で記録します。**
- ログは　**「リアルタイムで確認」**できます。
- ログは　**「将来の拡張性」**を考慮して設計されています。
- ログは　**「開発者の理解を深めるためのツール」**です。
- ログは　**「プログラムの挙動を可視化するためのイベント」**です。

## なぜこのLoggerを作成したのか

このLoggerは、通常の運用において発生しがちな  
**「静かに壊れる（Silent Failure）」問題を排除すること**を目的として設計されています。

一般的なログでは、エラーが明示的に出ない限り、問題の発見が遅れたり、原因の追跡が困難になるケースがあります。  
本Loggerではその課題を解決するために、**状態や意図を明示的に記録する設計**を採用しています。  

そのため  

特に、以下の形式で情報を記録できるようにしています。

```python
context: dict[str, Any]  # {変数 / プロパティ : 意図した値}
```

この設計により、

- 「何をしようとしていたのか」
- 「どの値を前提としていたのか」
- 「どこでズレが発生したのか」

を、ログから直接読み取ることが可能になります。  

また、記述のしやすさも重視し、開発者が自然にこの情報を残せるような構造にしています。

---

このLoggerは単なる記録ツールではなく、  
**「状態の透明性」を担保し、問題を早期に検知するための設計ツール**です。

## contextの使用例

以下は、context を使用してログの情報量を高める例です。

コード例

```python
logger.info(
    "ユーザーログイン処理",
    context={
        "user_id": user_id,
        "想定状態": "認証成功",
        "実際状態": auth_result,
    }
)
```

## 出力例

```text
{
  "time": "2026-04-18T10:15:30Z",
  "type": "INFO",
  "message": "ユーザーログイン処理",
  "context": {
    "user_id": "A12345",
    "想定状態": "認証成功",
    "実際状態": "失敗"
  }
}
```

---

## 異常検知例

```python
logger.warning(
    "Unexpected state detected",
    context={
        "state": current_state,
        "expected": "READY",
        "next_action": "recovery triggered"
    }
)
```

### 💡 なぜこれが重要なのか

単に「失敗した」という結果だけでなく、

- 何を想定していたのか
- 実際に何が起きたのか
- どのデータが原因だったのか

を、ログから直接把握することができます。

これにより、デバッグのスピードが大幅に向上し、  
「静かに壊れる（Silent Failure）」状態を見逃さない設計になります。

---

### 🤖 謝辞

本プロジェクトは、ChatGPT（OpenAI）の支援を受けて開発されました。  
ここに深く感謝の意を表します。

なお、本プロジェクトは OpenAI とは関係なく、また公式に承認されたものではありません。

---

### ⭐ サポート

本プロジェクトが役に立ったと感じていただけた場合は、  
GitHubで⭐を付けていただけると励みになります！
