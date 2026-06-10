# A案の問題

全部

```text
{
    "type": "...",
    "value": ...
}
```

で包むと、

例えば

```text
{
    "load_file_path": {
        "type": "str",
        "value": "sample.csv",
    }
}
```

になります。

さらに

context_for_adapter(...)

みたいな便利関数が増えると、

保存されるJSONが

```json
{
  "adapter_name": {
    "type": "str",
    "value": "csv"
  },
  "record_count": {
    "type": "int",
    "value": 123
  }
}
```

になってしまう。

先生も当時、

人間が読みにくい

と思っていました😊

## B案への変更

(B案では型指定を廃止して、値だけ保存することにしました)

ところが、

途中までA案だったので、

display_formatter.py

には

```python
if isinstance(v, dict) and "type" in v and "value" in v:
```

という

A案対応コード

が残っているんです。

一方で

context_builder.py

には

plain_context()

も存在する。

つまり今は

旧A案
新B案

が混在しています。

先生なら今後どうする？

今回は

ContextValue

を復活させたので、

Viewerは動きます👍

でも将来的には、

第1段階

wrap_context()

利用箇所を調査

第2段階

本当に使われているか確認

第3段階

使われていなければ

wrap_context()
wrap_context_value()
detect_context_type()

を削除

第4段階

display_formatter.py

の

```python
if "type" in v and "value" in v:
```

ブロックも削除

これで完全B案になります😊

先生の見立て

今の Logger_Project は

A案 → B案

への移行途中です。

今回の ImportError は、

その移行中に

ContextValue

だけ先に消えた結果ですね😊

だから今回の修正は応急処置として正しいです👍

ただし、

将来的には

ContextValue復活
↓
安心

ではなく、

旧A案コードを整理
↓
ContextValue不要

が最終形だと思います🚀

なので先生なら、

今すぐ消す必要はありませんが、

AGENT.md の TODO に、以下を記述しておきます。

```text
Contextシステム整理
A案(type/value形式)の完全廃止を検討
```

## まとめ

Context System

現在:
type/value形式

利用箇所:

- multi_info_logger.py
- log_viewer.py
- display_formatter.py

将来:
plain context形式への移行を検討

移行時は
wrap_context系と
unwrap_context系を同時に削除すること
