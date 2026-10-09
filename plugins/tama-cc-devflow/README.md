# tama-cc-devflow

Claude Code 向けの、タスクの重さに応じて流れを変えるマルチ Agent 開発フロー。図解付きの詳細は [docs/tama-cc-devflow.md](../../docs/tama-cc-devflow.md)。

- タスクを **Small** / **Medium** / **Large** に振り分ける。Large は「既存のものを壊すか、戻せるか」(既存の呼び出し元がある API の破壊的変更、既存テーブルの挙動変更、認証・認可、不可逆な副作用)で grep により決める。Small は既存パターンの踏襲で 1 人が閉じられるもの。Router は「実装者が暗黙に置くことになる仮定」を列挙し、影響の大きい仮定があれば grill-me 形式(重い質問は 1 問ずつ、軽い質問はまとめて。推奨回答付き)で人間にヒアリングする。
- **Large**: design Agent(fable、13 セクション) -> design reviewer(最大 3 ラウンド) -> 人間の承認 -> task planner(明示的な `depends_on` / `write_scope`) -> Wave 単位の並列実装(同時 3 件まで)とタスクごとの reviewer ループ(最大 3 ラウンド) -> 統合レビュー -> E2E 検証 -> 人間レビューガイド -> PR。
- **Medium**: design Agent(opus、6 セクションの軽量版、タスク 4 件以内。超えたら分割案を人間に提示) -> design reviewer(1 往復) -> 人間の承認 -> task planner -> Wave 単位の並列実装とタスクごとの reviewer(1 往復) -> 統合レビュー -> E2E 検証 -> 人間レビューガイド -> PR。design break は分類せず人間に聞く。
- **Small**: implementer 1 人、レビュー 1 往復、E2E 検証、人間の確認、コミット、PR。
- **E2E 検証**(全サイズ): verifier が作業ツリー(git worktree を含む)で開発サーバーを起動し、設計時に決めた Verification scenarios を実行する。API は `curl` の実リクエスト、UI は Playwright スクリプトでの操作とスクリーンショット。起動方法は CLAUDE.md / `package.json` / `docker-compose.yml` などから推測し、使用中のポートは env で空きポートに逃がす。逃がせない場合は他のプロセスを止めず BLOCKED として人間に返す。
- 状態は `.tama-cc-devflow/<session>/` 配下のファイル(git 管理外)に置く。Agent は必要なファイルだけ読む。実行は `status.json` から再開できる。
- `PreToolUse` hook が、実装中はタスクの `write_scope` 外の編集を、それ以外の phase ではソースへの編集をすべてブロックする。
- 人間へのメッセージは `[<label>] <size> / <phase> / <task>` のヘッダで始まる固定形式にそろえ、並列実行中でもどのフローの話か分かるようにする。Orca のターミナルではタブのタイトルを `<label> | <size> | <phase>` に更新する。

## コマンド

| コマンド | 用途 |
|---|---|
| `/tama-cc-devflow:run <依頼>` | 実行を開始する。自由文。GitHub / Notion / Slack のリンクは `context.md` に取り込まれる |
| `/tama-cc-devflow:resume [session-id]` | 中断した実行をチェックポイントから続行する |
| `/tama-cc-devflow:status [session-id]` | phase、Wave ごとのタスク、人間の判断待ち事項を表示する |

## Agent とモデル

| Agent | 役割 | モデル |
|---|---|---|
| router | Small / Medium / Large 分類、仮定の強制列挙 | sonnet |
| explore | 他 Agent 向けの読み取り専用コード調査 | sonnet |
| design | 設計書、決定事項 | fable(Large)/ opus(Medium) |
| design-reviewer | 明文化した条件に対する設計の合否判定 | opus |
| task-planner | `plan.json` + `tasks/<id>.md`、Wave 計画の実行 | opus |
| implementer | write_scope 内でタスク 1 件を実装 | sonnet |
| impl-reviewer | タスクごとの合否判定、design break の分類 | opus |
| integration-reviewer | 変更全体の整合性、チェック実行、人間レビューガイド | opus |
| verifier | 開発サーバーを起動しての E2E 検証 | sonnet |
| pr-writer | push と `gh pr create` | sonnet |

fable は白紙から構造を作る Large の `design` のみ。明文化された基準に照合するレビュー系は opus、調査・実装・定型作業は sonnet。

## 構成

```
skills/run, resume, status                   ユーザーが起動する入口
skills/workboard                             ホワイトボードの Schema と規約(Agent 専用)
skills/clarify                               grill-me 形式ヒアリング(重い質問は 1 問ずつ、軽い質問はまとめて。推奨回答付き。Agent 専用)
skills/small-flow, medium-flow, large-flow   オーケストレーション手順(Agent 専用、再入可能)
agents/*.md                                  Sub Agent 定義
hooks/hooks.json                             write_scope guard
scripts/init-session.sh                      セッションディレクトリの作成
scripts/status.py                            status.json の読み書き、実行可能タスクの列挙
scripts/plan-waves.py                        plan.json の検証、write_scope 競合の検出、Wave 割当
scripts/guard-write-scope.py                 PreToolUse hook
```

## 必要なもの

`git`、`gh`(認証済み)、`python3`。UI の E2E 検証には対象リポジトリの依存に `playwright` が必要。

## セットアップ

プラグインは対象プロジェクトの `.gitignore` に手を加えない。`.tama-cc-devflow/` を global gitignore で無視する。

```
git config --global core.excludesFile ~/.gitignore_global   # 未設定の場合
echo '**/.tama-cc-devflow/' >> ~/.gitignore_global
```

## ローカル開発

```
claude --plugin-dir ./plugins/tama-cc-devflow
claude plugin validate ./plugins/tama-cc-devflow --strict
```
