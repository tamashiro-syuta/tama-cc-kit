---
name: small-flow
description: devflow の Small フロー。Router が small と判定したタスクを、implementer 1 人・レビュー 1 往復・開発サーバーでの E2E 検証・人間の確認・コミット・PR で完了させる。devflow の run / resume Skill から呼ばれる。直接使用するものではない。
user-invocable: false
---

# Small フロー

前提: `status.py get size` が `"small"` で、`SESSION_DIR/router.md` に Task draft がある。`status.py get phase` を確認し、完了済みのステップは飛ばす(この Skill は resume のために再入可能)。

## 1. タスクファイル(phase: planning)

1. `status.py set phase '"planning"'`
2. Router の Task draft から `SESSION_DIR/tasks/T1.md` を、task-planner Agent のタスクファイル構成(Goal、Steps、Interface changes = none、Acceptance criteria、Test plan、Rollback notes、Out of scope)に `Verification scenarios`(draft の verification_scenarios をそのまま転記)を加えて書く。Router が draft していないスコープを足さない。
3. `SESSION_DIR/plan.json` に単一タスク(`id` T1、`depends_on` []、`write_scope` と `read_scope` は draft から、変更フラグはすべて false)を書き、`plan-waves.py` を実行する。
4. ブランチを作る: ベースブランチから `git checkout -b devflow/<slug>`。`status.py set branch '"devflow/<slug>"'`。

## 2. 実装とレビュー(phase: implementation)

1. `status.py set phase '"implementation"'`、次に `status.py task T1 running`。
2. `tama-cc-devflow:implementer` を `SESSION_DIR`、`TASK_ID=T1`、round 1 で呼ぶ。
3. `status.py task T1 review`。`tama-cc-devflow:impl-reviewer` を `SESSION_DIR`、`TASK_ID=T1`、`ROUND=1` で呼ぶ。
4. `verdict: FAIL` で blocking の指摘がある場合: `status.py task T1 running` にし、`reviews/T1-r1.md` を指して implementer をもう一度(round 2)呼び、その後 reviewer を `ROUND=2` で呼ぶ。Small フローの再作業はこの 1 回のみ。
5. それでも FAIL、または implementer が `design_break: yes` を報告、または status が `blocked` の場合: `status.py task T1 blocked` にし、未解決の blocking 指摘と残存リスクを人間にまとめ、次のどれにするか尋ねる。(a) 現状から Medium フローへ昇格する(size を `medium`、phase を `design` にして `tama-cc-devflow:medium-flow` を呼ぶ。design Agent は現在の diff を先行作業として扱う。Router が Large 条件の該当を記録していれば Large へ)、(b) 人間が手で直す、(c) 中止。待つ。
6. PASS の場合: `status.py task T1 done`。この段階ではコミットしない。変更は作業ツリーに残し、コミットは人間の確認後に pr-writer が行う。

## 3. E2E 検証(phase: verification)

`tasks/T1.md` の Verification scenarios が `none: <理由>` ならこの節を飛ばし、節 4 で理由を人間に示す。

1. `status.py set phase '"verification"'`。`N = review_rounds.verification + 1` とし、`status.py set review_rounds.verification N`。`tama-cc-devflow:verifier` を `ROUND=N` で呼ぶ。
2. `PASS` -> 節 4 へ。
3. `FAIL` かつ `N == 1`: `verify/report.md` の Failures を `tasks/T1.md` の「Verification findings」見出しの下に書き、`status.py set tasks.T1.review_rounds 0`、`status.py set phase '"implementation"'`、`status.py task T1 running` にして、implementer(次のラウンド番号)-> impl-reviewer を 1 往復回し、PASS ならこの節の 1 へ戻る。FAIL なら節 2 のステップ 5 と同じ扱い。
4. `FAIL` かつ `N == 2`: 未解決の Failures を人間に示し、節 2 のステップ 5 と同じ選択肢を尋ねる。待つ。
5. `BLOCKED`: `Blocked reason` を人間に示し、(a) 人間が環境を整えて再実行する(ステップ 1 の加算を省き、同じ `ROUND` で verifier を呼び直す)、(b) 検証を省略する(理由を `decisions.md` に記録して節 4 へ)、(c) 中止、を尋ねる。待つ。

## 4. 人間の確認(phase: human_review)

`status.py set phase '"human_review"'`。人間に示す: 変更ファイル、reviewer の non-blocking 指摘と残存リスク、実行したテストコマンド、E2E 検証の結果(`verify/report.md` のシナリオ表、スクリーンショットとリクエストログのパス。省略した場合はその理由)。コミットと PR 作成の承認を求め、待つ。修正依頼があれば `SESSION_DIR/tasks/T1.md` の「Human feedback」見出しの下に書き、次のラウンド番号で節 2 に戻り、節 3 の検証もやり直す(`review_rounds.verification` を 0 に戻す)。これは許容ラウンド 1 回分として数える。

## 5. PR(phase: pr)

`status.py set phase '"pr"'`。`tama-cc-devflow:pr-writer` を `SESSION_DIR`、`BRANCH`、`BASE_BRANCH` で呼ぶ。pr-writer が T1 の変更を 1 コミットにし、push し、PR を作る。URL を保存: `status.py set pr_url '"<url>"'`、次に `status.py set phase '"done"'`。

人間に報告する: PR の URL、変更ファイル、実行したテスト、E2E 検証の結果、フォローアップに残した non-blocking 指摘。
