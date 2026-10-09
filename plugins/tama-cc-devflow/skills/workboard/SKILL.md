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
  design/design.md     設計書(Medium は 6 セクションの軽量版、Large は 13 セクション。先頭行 "Template: medium|large")
  design/human-feedback.md   設計に対する人間の修正依頼(Medium / Large、任意)
  plan.json            タスクのメタデータ(Medium / Large)
  plan-feedback.md     Orchestrator から task-planner へのフィードバック(Medium / Large、任意)
  tasks/<id>.md        タスク定義
  tasks/<id>.result.md タスクごとの implementer の結果
  reviews/design-r<N>.md      設計レビュー N ラウンド目
  reviews/<id>-r<N>.md        タスク id の実装レビュー N ラウンド目
  reviews/integration.md      統合レビュー + 人間レビューガイド
  verify/report-r<N>.md       E2E 検証 N ラウンド目(verify/report.md は最新のコピー)
  verify/requests/, screenshots/, logs/   検証の証跡(curl の出力、スクリーンショット、サーバーログ)
  verify/<id>.spec.mjs, pids  verifier が書く Playwright スクリプトと、起動したサーバーの PID
  pr-body.md           PR 本文
```

## status.json

```json
{
  "session_id": "20260915-013000-add-export",
  "claude_session_id": "<この実行を所有する Claude Code の session id>",
  "created_at": "...", "updated_at": "...",
  "size": null | "small" | "medium" | "large",
  "phase": "init|routing|clarify|design|design_review|design_approval|planning|implementation|integration|verification|human_review|pr|done|aborted",
  "branch": "devflow/add-export", "base_branch": "main",
  "review_rounds": { "design": 0, "verification": 0 },
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

- Large: 設計レビュー 3 ラウンド、タスクごとの実装レビュー 3 ラウンド、planner 差し戻し 2 回。
- Medium: 設計レビュー 2 ラウンド、タスクごとの実装レビュー 2 ラウンド、planner 差し戻し 1 回。タスク分解は 4 件以内(超えたら人間に分割を提示)。
- Small: 実装レビュー 2 ラウンド(再作業 1 回)。
- 全サイズ: E2E 検証 2 ラウンド(FAIL 後の再作業 1 回)。BLOCKED(環境起因)はラウンドに数えない。
- 同時実行する implementer: 3。
- 上限に達したときの選択肢に「上位サイズへ昇格」を含める(Small -> Medium、Medium -> Large)。
- 人間へのヒアリング(clarify Skill)には回数上限を設けない。上限があるのは Agent 同士のループだけ。
- 上限に達したらループを続けない。未解決の指摘、blocking / non-blocking の区別、残存リスク、推奨する次のアクションをまとめ、タスクを `blocked` にする(または `human_decisions_required` に追加する)。判断は人間に渡す。

## Write guard

PreToolUse hook が、この Claude セッションが所有するセッションが guard 対象の phase にある間、ホワイトボード外への Edit/Write をブロックする。`implementation` 中は `running` / `review` 状態のタスクの `write_scope` 内のファイルだけ編集できる。phase を正直に設定し、implementer を呼ぶ前にタスクを `running` にすること。さもないと編集がブロックされる。

## 人間向けメッセージ

人間は複数の devflow を並列で動かしており、メッセージを読む時点でこのセッションの文脈を覚えていない前提で書く。人間に何かを示す・尋ねるメッセージ(判定の報告、質問、承認依頼、停止時のエスカレーション、最終報告)はすべてこの形式に従う。

```
[<label>] <size> / <phase> / <task id: タスク名>(タスクに紐づく場合のみ)
状況: 何が起きたか 1 行
論点: 何を決めてほしいか 1 行
選択肢: (推奨) A — 影響 / B — 影響 / C — 影響
詳細: <SESSION_DIR からの相対パス>
```

- `<label>` は session id から日時プレフィックス(`YYYYMMDD-HHMMSS-`)を除いた slug。AskUserQuestion の `header` にも同じ label を入れる(12 文字を超える場合は先頭 12 文字)。
- 単独で読める文にする。`T2`、`D3`、`r2 の指摘` のような内部 id だけで済ませず、ファイル名・関数名・挙動など具体物で書く。
- 状況には「なぜ今聞くのか」を含める。どの成果物から出た話か(design-reviewer の指摘、verifier の FAIL など)を書く。
- 本文は 5 行程度に収める。根拠や全文は「詳細」のパスに逃がし、本文に貼らない。
- 質問でない報告(判定の報告、最終報告)は「論点」「選択肢」を省いてよい。1 行目のヘッダは省かない。
- 各 Skill が「提示する」と列挙している項目は、この形式の「状況」と「詳細」の間に箇条書きで入れる。

## Agent の呼び出し

Agent のプロンプトには必ず絶対パスの `SESSION_DIR`、`PLUGIN_ROOT`(`${CLAUDE_PLUGIN_ROOT}`)、セッション id を渡す。加えて、その Agent に必要な id だけを渡す(`TASK_ID`、`ROUND`、`BRANCH`、`BASE_BRANCH`、design / design-reviewer には `TEMPLATE`)。Medium フローでは design を `model: opus` で呼ぶ(fable は Large のみ)。ファイルの内容をプロンプトに貼らない。Agent が自分で読む。独立した implementer は 1 つのメッセージでまとめて呼び、並列実行させる。
