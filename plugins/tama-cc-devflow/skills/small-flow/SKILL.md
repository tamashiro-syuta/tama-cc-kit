---
name: small-flow
description: devflow の Small フロー。Router が small と判定したタスクを、implementer 1 人・レビュー 1 往復・コミット・PR で完了させる。devflow の run / resume Skill から呼ばれる。直接使用するものではない。
user-invocable: false
---

# Small フロー

前提: `status.py get size` が `"small"` で、`SESSION_DIR/router.md` に Task draft がある。`status.py get phase` を確認し、完了済みのステップは飛ばす(この Skill は resume のために再入可能)。

## 1. タスクファイル(phase: planning)

1. `status.py set phase '"planning"'`
2. Router の Task draft から `SESSION_DIR/tasks/T1.md` を、task-planner Agent のタスクファイル構成(Goal、Steps、Interface changes = none、Acceptance criteria、Test plan、Rollback notes、Out of scope)で書く。Router が draft していないスコープを足さない。
3. `SESSION_DIR/plan.json` に単一タスク(`id` T1、`depends_on` []、`write_scope` と `read_scope` は draft から、変更フラグはすべて false)を書き、`plan-waves.py` を実行する。
4. ブランチを作る: ベースブランチから `git checkout -b devflow/<slug>`。`status.py set branch '"devflow/<slug>"'`。

## 2. 実装とレビュー(phase: implementation)

1. `status.py set phase '"implementation"'`、次に `status.py task T1 running`。
2. `tama-cc-devflow:implementer` を `SESSION_DIR`、`TASK_ID=T1`、round 1 で呼ぶ。
3. `status.py task T1 review`。`tama-cc-devflow:impl-reviewer` を `SESSION_DIR`、`TASK_ID=T1`、`ROUND=1` で呼ぶ。
4. `verdict: FAIL` で blocking の指摘がある場合: `status.py task T1 running` にし、`reviews/T1-r1.md` を指して implementer をもう一度(round 2)呼び、その後 reviewer を `ROUND=2` で呼ぶ。Small フローの再作業はこの 1 回のみ。
5. それでも FAIL、または implementer が `design_break: yes` を報告、または status が `blocked` の場合: `status.py task T1 blocked` にし、未解決の blocking 指摘と残存リスクを人間にまとめ、次のどれにするか尋ねる。(a) 現状から Large フローへ昇格する(size を `large`、phase を `design` にして `tama-cc-devflow:large-flow` を呼ぶ。design Agent は現在の diff を先行作業として扱う)、(b) 人間が手で直す、(c) 中止。待つ。
6. PASS の場合: `status.py task T1 done`。タスクのファイルをコミットする: `git add -- <write_scope paths>` の後 `git commit`。リポジトリのコミットメッセージ規約(CLAUDE.md)に従い、タスクのタイトルを含める。`.tama-cc-devflow/` 配下はコミットしない。

## 3. 人間の確認(phase: human_review)

`status.py set phase '"human_review"'`。人間に示す: 変更ファイル、reviewer の non-blocking 指摘と残存リスク、実行したテストコマンド。PR 作成の承認を求め、待つ。修正依頼があれば `SESSION_DIR/tasks/T1.md` の「Human feedback」見出しの下に書き、次のラウンド番号でステップ 2 に戻る。これは許容ラウンド 1 回分として数える。

## 4. PR(phase: pr)

`status.py set phase '"pr"'`。`tama-cc-devflow:pr-writer` を `SESSION_DIR`、`BRANCH`、`BASE_BRANCH` で呼ぶ。URL を保存: `status.py set pr_url '"<url>"'`、次に `status.py set phase '"done"'`。

人間に報告する: PR の URL、変更ファイル、実行したテスト、フォローアップに残した non-blocking 指摘。
