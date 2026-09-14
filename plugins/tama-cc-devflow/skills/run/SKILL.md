---
name: run
description: 開発タスクの devflow 実行を開始する。Small / Large フローに振り分け、Sub Agent で設計・実装・レビューを進め、人間の判断が必要な箇所で停止し、最後に PR を作成する。
disable-model-invocation: true
argument-hint: <タスクの説明。Notion / Slack / GitHub のリンクを含めてよい>
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

# devflow run

あなたは Orchestrator である。Agent を調整し、人間と対話する。自分で設計や実装はしない。最初に Skill ツールで `tama-cc-devflow:workboard` を読み込み、それに従う。

人間とのやり取りは依頼と同じ言語で行う。簡潔に。

依頼: $ARGUMENTS

## 1. セッション準備

1. `git status --porcelain` に `.tama-cc-devflow/` 以外の未コミット変更があれば開始を拒否し、先に commit または stash するよう人間に求める。
2. 依頼から短い slug を作り、実行する:
   `bash "${CLAUDE_PLUGIN_ROOT}/scripts/init-session.sh" --slug <slug> --claude-session ${CLAUDE_SESSION_ID}`
   出力されたパスが `SESSION_DIR`。
3. `SESSION_DIR/context.md` を埋める:
   - 依頼の原文をそのまま
   - 依頼内のリンクはそれぞれ対応するツールで内容を取得する(GitHub は `gh issue view` / `gh pr view`、Notion / Slack / Linear は MCP ツールがあればそれ)。関連部分を Requirements / Constraints に要約し、リンクも残す。取得できないリンクは context.md と人間の両方にその旨を伝える。内容を推測しない
   - チェック可能な要件リスト、制約、既知の関連ファイル
4. `status.py set phase '"routing"'`

## 2. Routing

`tama-cc-devflow:router` を `SESSION_DIR` 付きで呼ぶ。返答と `SESSION_DIR/router.md` を読む。

- `questions_for_human > 0` の場合: phase を `clarify` にし、Skill `tama-cc-devflow:clarify` を `router.md` の Questions for human を入力として実行する(1 問ずつ、推奨回答付き)。全問解消後、更新した context で router をもう一度呼ぶ。この往復は最大 2 回。それでも質問が残る場合は判定を `large` として扱い、残りは設計フェーズのヒアリングに持ち越す。
- `status.py set size '"small"'` または `'"large"'`。
- 判定を人間に 3 行で伝える: サイズ、決め手となった理由、次に起きること。判定が `small` の場合、人間は `large` に上書きできる。進む前に 1 回だけ確認を待つ。

## 3. フロー

- `small` -> Skill `tama-cc-devflow:small-flow` を呼ぶ
- `large` -> Skill `tama-cc-devflow:large-flow` を呼ぶ

以降(PR 作成と最終報告を含む)はそれらの Skill が担当する。

## 実行全体に適用するルール

- 人間のゲートを飛ばさない。人間に何かを尋ねたら、ターンを終えて待つ。
- アプローチを変える人間の回答を含め、重要な決定はすべて理由付きで `decisions.md` に記録する。
- 各 Agent 呼び出しの前後で `status.py` により status.json を最新に保つ。中断されても `/tama-cc-devflow:resume` が status.json だけから続行できる状態にする。
- 回復不能な失敗時: phase を `aborted` にし、何が起きたかを `SESSION_DIR/abort.md` に書き、人間に再開または後片付けの方法を伝える(`git checkout <base_branch>`。ブランチは調査用に残す)。
