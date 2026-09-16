---
name: resume
description: 中断した devflow の実行をチェックポイント(status.json)から再開する。記録された phase から Small / Large フローを続行する。完了済みタスクは保持し、中断したタスクはやり直す。
disable-model-invocation: true
argument-hint: "[session-id]  (省略時: 最新のセッション)"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - AskUserQuestion
  - Skill
  - Agent(tama-cc-devflow:router, tama-cc-devflow:explore, tama-cc-devflow:design, tama-cc-devflow:design-reviewer, tama-cc-devflow:task-planner, tama-cc-devflow:implementer, tama-cc-devflow:impl-reviewer, tama-cc-devflow:integration-reviewer, tama-cc-devflow:pr-writer)
---

# devflow resume

最初に Skill ツールで `tama-cc-devflow:workboard` を読み込む。

セッション: $ARGUMENTS(空なら `.tama-cc-devflow/current`)。セッション id が指定された場合、スクリプトと write guard がそれを使うよう `.tama-cc-devflow/current` に書き込む。`SESSION_DIR` は `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/status.py" path` で得る。

## 手順

1. `status.py summary`。phase が `done` ならその旨を伝えて終了。`aborted` なら `SESSION_DIR/abort.md` を見せ、それでも続行するか尋ねる。
2. `CLAUDE_SESSION_ID=${CLAUDE_SESSION_ID} python3 "${CLAUDE_PLUGIN_ROOT}/scripts/status.py" reset-running` を実行し、中断したタスクをやり直し可能にし、この Claude セッションが実行を所有するようにする。
3. 作業ツリーを確認: `git status --porcelain` と `git branch --show-current`。`status.json.branch` が設定済みで checkout されていなければ `git checkout <branch>`。タスクの変更は pr phase まで未コミットのまま作業ツリーに残る設計なので、`done` / `running` / `review` だったタスクの write_scope 内にある未コミット変更は保持する。implementer は現在のファイルから続きを行う。write_scope 外の未コミット変更があれば停止して人間に尋ねる。
4. どこで止まったか、次に何が起きるかを 5 行で人間に伝える。ステップ 3 で質問が生じていなければ待たずに進む。
5. `size` に応じて Skill `tama-cc-devflow:small-flow` または `tama-cc-devflow:large-flow` を呼ぶ。これらは再入可能で、記録された phase から続行する。
