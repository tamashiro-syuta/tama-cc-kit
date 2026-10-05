---
name: medium-flow
description: devflow の Medium フロー。軽量設計書(6 セクション、タスク 4 件以内)と設計レビュー 1 往復、タスク 5 件以上なら人間への分割提示、人間の設計承認、タスク分解、Wave 単位の並列実装とタスクごとのレビュー 1 往復、統合レビュー、開発サーバーでの E2E 検証、人間レビュー、PR。devflow の run / resume Skill から呼ばれる。直接使用するものではない。
user-invocable: false
---

# Medium フロー

前提: `status.py get size` が `"medium"`。この Skill は再入可能。最初に `status.py summary` を読み、記録された phase から続行し、完了済みの作業は飛ばす。Agent の呼び出しには必ず `SESSION_DIR`、`PLUGIN_ROOT`、セッション id を渡す。詳細は workboard Skill を参照。

Medium は「設計判断は要るが、既存のものは壊さない」変更のためのフロー。Large との違いは、設計書が軽量テンプレートであること、Agent 同士のループが各 1 往復であること、design break の分類をせず人間に聞くこと、タスクが 4 件を超えたら分割を人間に提示すること。

## Large への昇格

このフローのどの停止点でも、人間が「Large へ昇格」を選べる。手順: `status.py set size '"large"'`、`status.py set phase '"design"'`、理由を `decisions.md` に記録し、Skill `tama-cc-devflow:large-flow` を呼ぶ。design Agent は既存の `design.md`(medium テンプレート)と作業ツリーの未コミット変更を先行作業として読み、Large テンプレートで書き直す。

## A. 設計(phase: design / design_review)

設計中に人間の判断が必要な疑問が出たら、その場で grill-me 形式のヒアリング(Skill `tama-cc-devflow:clarify`)を行う。

1. `status.py set phase '"design"'`。`tama-cc-devflow:design` を **`model: opus`、`TEMPLATE=medium`** で呼ぶ(fable は使わない)。
2. 返答の `open_questions_for_human > 0` の場合: Skill `tama-cc-devflow:clarify` を `design/design.md` の Open questions を入力として実行する。全問解消後、ステップ 1 に戻って design に改訂させる。`open_questions_for_human == 0` になるまで繰り返す。
3. 返答の `task_count > 4` の場合: `design.md` の Split proposal を人間に提示し、AskUserQuestion で 3 択を尋ねる。待つ。
   - **分割する(推奨)**: Split proposal の「残り」を `context.md` の `## Follow-ups` に書き(スライスごとに 1 行、次の run の依頼文に使える粒度)、`decisions.md` に分割の決定を記録し、ステップ 1 に戻って design に 1 スライス目だけで改訂させる。
   - **Large へ昇格**: 上記の手順で large-flow へ。
   - **このまま Medium で進む**: 人間の上書きとして `decisions.md` に記録し、ステップ 4 へ。以降 `task_count` の確認はしない。
4. `status.py set phase '"design_review"'`。`N = review_rounds.design + 1` とし、`status.py set review_rounds.design N`。`tama-cc-devflow:design-reviewer` を `ROUND=N`、`TEMPLATE=medium` で呼ぶ。
5. レビュアーが `human_decision_required: yes` を返した場合(PASS / FAIL を問わず): ステップ 1 に戻り、design にレビューの質問へ回答させる。答えられないものはステップ 2 のルールでヒアリングし、改訂後にステップ 4 でレビューし直す。この経路の再レビューは `review_rounds.design` を増やさない。
6. `verdict: FAIL` かつ `N == 1`: ステップ 1 へ戻る(design が `reviews/design-r1.md` を読む)。
7. `verdict: FAIL` かつ `N == 2`: ループを止める。未解決の blocking 指摘を B の提示に添える。
8. `verdict: PASS` かつ `human_decision_required: no`、またはステップ 7 を経て B へ進む。

## B. 人間の設計承認(phase: design_approval)

`status.py set phase '"design_approval"'`。人間にコンパクトに提示する:

- 採用した設計の要約
- インターフェース / データの変更
- タスク分解案と依存関係
- 残っている Open questions(通常は A で解消済みのため空)
- 設計レビューが 2 回目も FAIL だった場合、その未解決の blocking 指摘と推奨する落とし所
- 全文の場所: `SESSION_DIR/design/design.md`

approve / request changes / abort を尋ね、待つ。「request changes」の場合、フィードバックを `design/human-feedback.md` に書き、人間が下した決定を `decisions.md` に記録し、`review_rounds.design` を 0 に戻して A.1 へ戻る。approve の場合、`decisions.md` に `## Dn: Design approved` を日付付きで記録する。

## C. 計画(phase: planning)

1. `status.py set phase '"planning"'`。`tama-cc-devflow:task-planner` を呼ぶ。`plan.json`、`tasks/*.md` を書き、`plan-waves.py` を実行する。
2. plan-waves がタスクを直列化した、タスクが 5 件以上になった、または plan が設計と矛盾する場合、懸念を `SESSION_DIR/plan-feedback.md` に書き、planner をもう一度呼ぶ。差し戻しは 1 回のみ。その後は plan を人間に提示して判断を仰ぐ。
3. Wave(`status.py summary`)を「実行可能なタスク群」として人間に見せる。直列化や統合が起きていなければ待たずに進む。起きていれば 1 行の確認を求める。
4. ブランチを作る: `git checkout -b devflow/<slug>`。`status.py set branch '"devflow/<slug>"'`。

## D. 実装(phase: implementation)

`status.py set phase '"implementation"'`。以下をループする:

1. `ready=$(status.py ready)`。空で、かつ `running` / `review` のタスクがない場合: 全タスクが `done` なら E へ。`blocked` または `failed` があればステップ 6 へ。
2. `ready` の各 id について `status.py task <id> running`。id ごとに `tama-cc-devflow:implementer` を **1 つのメッセージで** 呼び、並列実行させる。各 implementer には自身の `TASK_ID` とラウンド番号(`review_rounds + 1`)を渡す。
3. implementer が返るたびに `status.py task <id> review` にし、`tama-cc-devflow:impl-reviewer` を `TASK_ID` と `ROUND = review_rounds` で呼ぶ。異なるタスクのレビューも並列でよい。
4. タスクごとに reviewer の返答を読む:
   - `PASS` かつ `design_break: none` -> `status.py task <id> done`。コミットしない。変更は作業ツリーに残し、F の人間承認後に G でまとめて積む。
   - `FAIL` かつ `review_rounds == 1` -> `status.py task <id> running` にし、implementer を再度呼ぶ(再作業はこの 1 回のみ)。その後ステップ 3 へ。
   - `FAIL` かつ `review_rounds == 2` -> `status.py task <id> blocked`。未解決の blocking 指摘の要約を `human_decisions_required` に追加する。
   - `design_break` が `none` 以外 -> 分類に関わらず `status.py set tasks.<id>.design_break '"<分類>"'`、`status.py task <id> blocked`。依存タスクは開始しない。独立した他のタスクは続行し、その後ステップ 6 へ。部分再設計・全体再設計の機構は使わない。
5. ステップ 1 へ。
6. 停止条件。人間に尋ねる前に、状況を `decisions.md` または `abort.md` に記録する。判断材料が不足している争点は、選択肢を提示する前に Skill `tama-cc-devflow:clarify` で 1 問ずつ確認する。その上で、未解決の指摘(または design break の内容と reviewer の assessment)、リスク、推奨アクションを提示し、選択肢を尋ねる。待つ。
   - 人間が直して done にする(人間の宣言後に `status.py task <id> done`)
   - implementer に具体的な指示を与える(`tasks/<id>.md` の「Human feedback」に書き、`status.py set tasks.<id>.review_rounds 0`、`status.py set tasks.<id>.design_break null`、pending にする)
   - design break を設計の変更として受け入れる(逸脱を `decisions.md` に記録し、`design.md` の該当箇所を Orchestrator が追記で更新し、上と同じ手順でタスクを pending にする)
   - Large へ昇格
   - 中止

## E. 統合(phase: integration)

1. `status.py set phase '"integration"'`。`tama-cc-devflow:integration-reviewer` を `BASE_BRANCH` 付きで呼ぶ。
2. `FAIL` の場合: blocking issue ごとにどのタスクが担当かを決め、そのタスクファイルの「Integration findings」に書き、タスクを `pending` にして `review_rounds` を 0 に戻し、phase を `implementation` にして該当タスクだけ D を再実行する。統合の再作業サイクルは最大 1 回。その後は人間にエスカレーションする。
3. `PASS` なら E2 へ。

## E2. E2E 検証(phase: verification)

`design/design.md` の Verification scenarios が `none: <理由>` ならこの節を飛ばし、F で理由を人間に示す。

1. `status.py set phase '"verification"'`。`N = review_rounds.verification + 1` とし、`status.py set review_rounds.verification N`。`tama-cc-devflow:verifier` を `ROUND=N` で呼ぶ。
2. `PASS` -> F へ。
3. `FAIL` かつ `N == 1`: `verify/report.md` の Failures ごとに担当タスクを決め(report の推定を確認し、違えば Orchestrator が決める)、そのタスクファイルの「Verification findings」に書き、タスクを `pending`、`review_rounds` 0 に戻し、phase を `implementation` にして該当タスクだけ D を再実行し、E を再実行してからこの節の 1 へ戻る。
4. `FAIL` かつ `N == 2`: ループを止める。未解決の Failures、原因と思われる箇所、推奨アクションを人間に示し、人間が直す / implementer に具体的な指示を与える(D.6 と同じ手順) / Large へ昇格/ 中止、を尋ねる。待つ。
5. `BLOCKED`: `Blocked reason` を人間に示し、(a) 人間が環境を整えて再実行する(ステップ 1 の加算を省き、同じ `ROUND` で verifier を呼び直す)、(b) 検証を省略する(理由を `decisions.md` に記録して F へ)、(c) 中止、を尋ねる。待つ。

## F. 人間レビュー(phase: human_review)

`status.py set phase '"human_review"'`。`reviews/integration.md` の人間レビューガイドを提示する: must-read files、risk hotspots、運用と異常系の論点、推奨する手動検証、non-blocking 指摘。加えて E2E 検証の結果(`verify/report.md` のシナリオ表、スクリーンショットとリクエストログのパス。省略した場合はその理由)を示す。`context.md` に Follow-ups があればそれも示す。approve / request changes / abort を尋ね、待つ。「request changes」の場合、各依頼を担当タスクファイルの「Human feedback」に書き、そのタスクを `pending`、`review_rounds` 0 に戻し、phase を `implementation` にして D を再実行し、`review_rounds.verification` を 0 に戻して E と E2 を再実行してからここに戻る。

## G. PR(phase: pr)

`status.py set phase '"pr"'`。`tama-cc-devflow:pr-writer` を `BRANCH`、`BASE_BRANCH` 付きで呼ぶ。pr-writer が `plan.json` の Wave 順・タスク順にタスク単位のコミットを積み、push し、PR を作る。`status.py set pr_url '"<url>"'`、`status.py set phase '"done"'`。

人間への最終報告: PR の URL、実行したタスクと Wave、使ったレビューラウンド数、人間が解決した block、フォローアップに残した non-blocking 指摘と `context.md` の Follow-ups(次の run の依頼文として使える形で)、ホワイトボードの場所。
