---
name: status
description: 現在の(または指定した)devflow セッションの状態を表示する。サイズ、phase、Wave ごとのタスクと状態・レビューラウンド、人間の判断待ち事項。
disable-model-invocation: true
argument-hint: "[session-id]"
allowed-tools:
  - Bash(python3 *scripts/status.py*)
  - Bash(ls *)
  - Read
---

`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/status.py" $ARGUMENTS summary` を実行し(id が指定された場合は `--session <id>` を前に付ける)、出力をコードブロックでそのまま示す。その後 5 行以内で、次のステップと、それを続行するコマンド(`/tama-cc-devflow:resume`)を伝える。

セッションが存在しない場合は `.tama-cc-devflow/` を一覧し、`/tama-cc-devflow:run` で開始できると伝える。
