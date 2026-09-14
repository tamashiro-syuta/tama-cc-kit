---
name: workboard
description: tama-cc-devflow の共有ホワイトボード規約。セッションディレクトリ構成、status.json の Schema、phase、タスク状態、各 Agent がどのファイルを読み書きするか。devflow のオーケストレーション Skill から読み込まれる。直接使用するものではない。
user-invocable: false
---

# devflow ホワイトボード

すべての状態は `<project>/.tama-cc-devflow/<session-id>/` 配下のファイルに置く(git 管理外)。Agent は会話履歴を受け取らず、これらのファイルを読む。以下 `SESSION_DIR` はこのディレクトリを指す。`.tama-cc-devflow/current` に最新セッションの id が入る。

```
SESSION_DIR/
  status.json          機械的に扱う状態(phase、tasks、rounds)
  context.md           依頼内容、要件、制約、関連ファイル、人間への確認結果
  decisions.md         重要な決定だけ: "## Dn: title" / "- Decision:" / "- Reason:"
  router.md            Router の判定、仮定一覧、Task draft(Small)
  design/design.md     設計書(Large)
  design/human-feedback.md   設計に対する人間の修正依頼(Large、任意)
  plan.json            タスクのメタデータ(Large)
  plan-feedback.md     Orchestrator から task-planner へのフィードバック(Large、任意)
  tasks/<id>.md        タスク定義
  tasks/<id>.result.md タスクごとの implementer の結果
  reviews/design-r<N>.md      設計レビュー N ラウンド目
  reviews/<id>-r<N>.md        タスク id の実装レビュー N ラウンド目
  reviews/integration.md      統合レビュー + 人間レビューガイド
  pr-body.md           PR 本文
```

## status.json

```json
{
  "session_id": "20260915-013000-add-export",
  "claude_session_id": "<この実行を所有する Claude Code の session id>",
  "created_at": "...", "updated_at": "...",
  "size": null | "small" | "large",
  "phase": "init|routing|clarify|design|design_review|design_approval|planning|implementation|integration|human_review|pr|done|aborted",
  "branch": "devflow/add-export", "base_branch": "main",
  "review_rounds": { "design": 0 },
  "tasks": {
    "T1": { "title": "...", "status": "pending|running|review|done|failed|blocked",
            "depends_on": [], "write_scope": ["src/x.ts"], "wave": 1,
            "review_rounds": 0, "design_break": null }
  },
  "human_decisions_required": ["..."],
  "pr_url": null
}
```

status.json を手で編集しない。必ずスクリプトを使う。

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/status.py" summary
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/status.py" get phase
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/status.py" set phase '"design"'
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/status.py" set review_rounds.design 2
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/status.py" set tasks.T1.design_break '"partial-redesign"'
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/status.py" task T1 running     # "review" への遷移で review_rounds が +1 される
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/status.py" ready               # 今実行可能なタスク id。同時 3 件まで
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/status.py" reset-running       # クラッシュ後の復旧
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/plan-waves.py"                 # plan.json の検証と Wave 割当
```

`set` の値は JSON。文字列は引用符が必要。各スクリプトはコマンドの前に `--session <id>` を受け付ける。省略時は `current`。

## 上限

- 設計レビュー: 3 ラウンド。タスクごとの実装レビュー: 3 ラウンド。Small フロー: 1 ラウンド。
- 同時実行する implementer: 3。
- 人間へのヒアリング(clarify Skill)には回数上限を設けない。上限があるのは Agent 同士のループだけ。
- 上限に達したらループを続けない。未解決の指摘、blocking / non-blocking の区別、残存リスク、推奨する次のアクションをまとめ、タスクを `blocked` にする(または `human_decisions_required` に追加する)。判断は人間に渡す。

## Write guard

PreToolUse hook が、この Claude セッションが所有するセッションが guard 対象の phase にある間、ホワイトボード外への Edit/Write をブロックする。`implementation` 中は `running` / `review` 状態のタスクの `write_scope` 内のファイルだけ編集できる。phase を正直に設定し、implementer を呼ぶ前にタスクを `running` にすること。さもないと編集がブロックされる。

## Agent の呼び出し

Agent のプロンプトには必ず絶対パスの `SESSION_DIR`、`PLUGIN_ROOT`(`${CLAUDE_PLUGIN_ROOT}`)、セッション id を渡す。加えて、その Agent に必要な id だけを渡す(`TASK_ID`、`ROUND`、`BRANCH`、`BASE_BRANCH`)。ファイルの内容をプロンプトに貼らない。Agent が自分で読む。独立した implementer は 1 つのメッセージでまとめて呼び、並列実行させる。
