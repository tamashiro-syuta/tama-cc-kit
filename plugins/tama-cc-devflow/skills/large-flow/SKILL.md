---
name: large-flow
description: devflow の Large フロー。設計と有限回のレビューループ、人間の設計承認、依存関係を考慮したタスク分解、Wave 単位の並列実装とタスクごとの有限回レビューループ、統合レビュー、人間レビュー、PR。devflow の run / resume Skill から呼ばれる。直接使用するものではない。
user-invocable: false
---

# Large フロー

前提: `status.py get size` が `"large"`。この Skill は再入可能。最初に `status.py summary` を読み、記録された phase から続行し、完了済みの作業は飛ばす。Agent の呼び出しには必ず `SESSION_DIR`、`PLUGIN_ROOT`、セッション id を渡す。詳細は workboard Skill を参照。

## A. 設計(phase: design / design_review)

設計中に人間の判断が必要な疑問が出たら、その場で grill-me 形式のヒアリング(Skill `tama-cc-devflow:clarify`)を行う。設計レビュー後にレビュアーから出た質問も、まず design Agent が答え、答えられないものや人間の判断が必要とされたものをヒアリングする。

1. `status.py set phase '"design"'`。`tama-cc-devflow:design` を呼ぶ。
2. design の返答の `open_questions_for_human > 0` の場合: Skill `tama-cc-devflow:clarify` を `design/design.md` の Open questions(人間の判断が必要なもの)を入力として実行する。全問解消後、ステップ 1 に戻って design に改訂させる(design は context.md の Clarifications と decisions.md を読む)。`open_questions_for_human == 0` になるまで繰り返す。
3. `status.py set phase '"design_review"'`。`N = review_rounds.design + 1` とし、`status.py set review_rounds.design N`。`tama-cc-devflow:design-reviewer` を `ROUND=N` で呼ぶ。
4. レビュアーが `human_decision_required: yes` を返した場合(PASS / FAIL を問わず): ステップ 1 に戻り、design にレビューの質問へ回答させる。design は自分で答えられるものは設計書に反映し、答えられないものを Open questions に残す。以降はステップ 2 のルールでヒアリングし、改訂後にステップ 3 でレビューし直す。この経路の再レビューは FAIL ループではないため `review_rounds.design` を増やさない(ステップ 3 の加算を省く)。
5. `verdict: FAIL` かつ `N < 3`: ステップ 1 へ戻る(design が `reviews/design-r<N>.md` を読む)。
6. `verdict: FAIL` かつ `N == 3`: ループを止める。`reviews/design-r3.md` の未解決 blocking 指摘と設計者・レビュアーの争点を、Skill `tama-cc-devflow:clarify` で 1 問ずつ人間に確認する(各争点に推奨する落とし所を付ける)。解消した内容を `design/human-feedback.md` に書き、`review_rounds.design` を 0 に戻してステップ 1 へ。争点がヒアリングで解消しない場合のみ、現状の設計を受け入れるか中止するかを尋ねる。待つ。
7. `verdict: PASS` かつ `human_decision_required: no` で B へ進む。

## B. 人間の設計承認(phase: design_approval)

`status.py set phase '"design_approval"'`。人間にコンパクトに提示する:

- 採用した設計の要約と却下案(各 1 行)
- インターフェース / データの変更
- 異常系とロールバックの方針
- タスク分解案と依存関係
- 残っている Open questions(通常は A で解消済みのため空)
- 全文の場所: `SESSION_DIR/design/design.md`

approve / request changes / abort を尋ね、待つ。「request changes」の場合、フィードバックを `design/human-feedback.md` に書き、人間が下した決定を `decisions.md` に記録し、A.1 へ戻る。approve の場合、`decisions.md` に `## Dn: Design approved` を日付付きで記録する。

## C. 計画(phase: planning)

1. `status.py set phase '"planning"'`。`tama-cc-devflow:task-planner` を呼ぶ。`plan.json`、`tasks/*.md` を書き、`plan-waves.py` を実行する。
2. 返答を読む。plan-waves がタスクを直列化した、または plan が不適切に見える(あるタスクの write_scope が無関係なモジュールにまたがる、依存関係が設計と矛盾する)場合、懸念を `SESSION_DIR/plan-feedback.md` に書き、planner をもう一度呼ぶ。planner は最大 2 ラウンド。その後は plan を人間に提示して判断を仰ぐ。
3. Wave(`status.py summary`)を「実行可能なタスク群」として人間に見せる。直列化や統合が起きていなければ待たずに進む。起きていれば 1 行の確認を求める。
4. ブランチを作る: `git checkout -b devflow/<slug>`。`status.py set branch '"devflow/<slug>"'`。

## D. 実装(phase: implementation)

`status.py set phase '"implementation"'`。以下をループする:

1. `ready=$(status.py ready)`。空で、かつ `running` / `review` のタスクがない場合: 全タスクが `done` なら E へ。`blocked` または `failed` があればステップ 6 へ。
2. `ready` の各 id について `status.py task <id> running`。id ごとに `tama-cc-devflow:implementer` を **1 つのメッセージで** 呼び、並列実行させる。各 implementer には自身の `TASK_ID` とラウンド番号(`review_rounds + 1`)を渡す。
3. implementer が返るたびに `status.py task <id> review` にし、`tama-cc-devflow:impl-reviewer` を `TASK_ID` と `ROUND = review_rounds`(`review` 遷移で既に +1 済み)で呼ぶ。異なるタスクのレビューも並列でよい。
4. タスクごとに reviewer の返答を読む:
   - `PASS` かつ `design_break: none` -> `status.py task <id> done`。そのタスクのファイルをコミット: `git add -- <write_scope paths>` の後、リポジトリの規約に従い、タスク名を含めたメッセージで `git commit`。`.tama-cc-devflow/` は絶対にコミットしない。
   - `FAIL` かつ `review_rounds < 3` -> `status.py task <id> running` にし、implementer を再度呼ぶ(再作業ラウンド)。その後ステップ 3 へ。
   - `FAIL` かつ `review_rounds == 3` -> `status.py task <id> blocked`。未解決の blocking 指摘の要約を `human_decisions_required` に追加する。
   - `design_break: continue` -> PASS/FAIL として通常通り扱う。逸脱を `decisions.md` に記録する。
   - `design_break: partial-redesign` -> `status.py set tasks.<id>.design_break '"partial-redesign"'`、`status.py task <id> blocked`。依存タスクは開始しない。独立した他のタスクは続行し、その後ステップ 6 へ。
   - `design_break: full-redesign` -> タスクを `blocked` にし、`design_break` を設定し、実行中のタスクが返り次第ステップ 6 へ。
5. ステップ 1 へ。
6. 停止条件。人間に尋ねる前に、状況を `decisions.md` または `abort.md` に記録する。判断材料が不足している争点(なぜ blocking が解消しないか、どの前提が崩れたか)は、選択肢を提示する前に Skill `tama-cc-devflow:clarify` で 1 問ずつ確認する。その上で:
   - レビュー上限による block: 未解決の指摘、blocking / non-blocking、リスク、推奨アクションを提示する。選択肢: 人間が直して done にする(人間の宣言後に `status.py task <id> done`)、implementer に具体的な指示を与える(`tasks/<id>.md` の「Human feedback」に書き、`status.py set tasks.<id>.review_rounds 0` でそのタスクの `review_rounds` を 0 に戻し、pending にする)、中止。待つ。
   - 部分再設計: reviewer の assessment で名指しされたセクションだけを改訂するよう明示して `tama-cc-devflow:design` を呼び、`design-reviewer` を 1 ラウンド、その後人間が差分を承認する(B の差分版)。次に `plan-feedback.md` に再計画すべきタスクを書いて `task-planner` を呼ぶ。write_scope が影響を受けない `done` のタスクは `done` のまま。D を再開する。
   - 全体再設計: phase を `design` にし、理由を `decisions.md` に書き、人間に説明する。現在のブランチ上で A をやり直す(完了済みの作業はコミット済みのまま先行作業になる)か、中止するかを尋ねる。待つ。

## E. 統合(phase: integration)

1. `status.py set phase '"integration"'`。`tama-cc-devflow:integration-reviewer` を `BASE_BRANCH` 付きで呼ぶ。
2. `FAIL` の場合: blocking issue ごとにどのタスクが担当かを決め、そのタスクファイルの「Integration findings」に書き、タスクを `pending` にして `review_rounds` を 0 に戻し、phase を `implementation` にして該当タスクだけ D を再実行する。統合の再作業サイクルは最大 1 回。その後は人間にエスカレーションする。
3. `PASS` なら続行。

## F. 人間レビュー(phase: human_review)

`status.py set phase '"human_review"'`。`reviews/integration.md` の人間レビューガイドを提示する: must-read files、risk hotspots、運用と異常系の論点、推奨する手動検証、non-blocking 指摘。approve / request changes / abort を尋ね、待つ。「request changes」の場合、各依頼を担当タスクファイルの「Human feedback」に書き、そのタスクを `pending`、`review_rounds` 0 に戻し、phase を `implementation` にして D を再実行し、E を再実行してからここに戻る。

## G. PR(phase: pr)

`status.py set phase '"pr"'`。`tama-cc-devflow:pr-writer` を `BRANCH`、`BASE_BRANCH` 付きで呼ぶ。`status.py set pr_url '"<url>"'`、`status.py set phase '"done"'`。

人間への最終報告: PR の URL、実行したタスクと Wave、使ったレビューラウンド数、人間が解決した block、フォローアップに残した non-blocking 指摘、ホワイトボードの場所。
