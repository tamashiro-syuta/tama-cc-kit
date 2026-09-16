# tama-cc-devflow

Claude Code 向けの、タスクの重さに応じて流れを変えるマルチ Agent 開発フロー。図解付きの詳細は [docs/tama-cc-devflow.md](../../docs/tama-cc-devflow.md)。

- タスクを **Small** / **Large** に振り分ける。Router は「実装者が暗黙に置くことになる仮定」を列挙し、影響の大きい仮定が 1 つでもあれば Large に倒す。迷ったら Large。人間に聞くべき質問は grill-me 形式(1 問ずつ、推奨回答付き)でヒアリングする。
- **Large**: design Agent(疑問があれば grill-me 形式で人間にヒアリング) -> design reviewer(最大 3 ラウンド。レビュアーの質問に design が答えられなければヒアリング) -> 人間の承認 -> task planner(明示的な `depends_on` / `write_scope`) -> Wave 単位の並列実装(同時 3 件まで)とタスクごとの reviewer ループ(最大 3 ラウンド) -> 統合レビュー -> 人間レビューガイド -> PR。
- **Small**: implementer 1 人、レビュー 1 往復、コミット、人間の確認、PR。
- 状態は `.tama-cc-devflow/<session>/` 配下のファイル(git 管理外)に置く。Agent は必要なファイルだけ読む。実行は `status.json` から再開できる。
- `PreToolUse` hook が、実装中はタスクの `write_scope` 外の編集を、それ以外の phase ではソースへの編集をすべてブロックする。

## コマンド

| コマンド | 用途 |
|---|---|
| `/tama-cc-devflow:run <依頼>` | 実行を開始する。自由文。GitHub / Notion / Slack のリンクは `context.md` に取り込まれる |
| `/tama-cc-devflow:resume [session-id]` | 中断した実行をチェックポイントから続行する |
| `/tama-cc-devflow:status [session-id]` | phase、Wave ごとのタスク、人間の判断待ち事項を表示する |

## Agent とモデル

| Agent | 役割 | モデル |
|---|---|---|
| router | Small / Large 分類、仮定の強制列挙 | sonnet |
| explore | 他 Agent 向けの読み取り専用コード調査 | sonnet |
| design | 設計書、決定事項 | fable |
| design-reviewer | 明文化した条件に対する設計の合否判定 | opus |
| task-planner | `plan.json` + `tasks/<id>.md`、Wave 計画の実行 | opus |
| implementer | write_scope 内でタスク 1 件を実装 | sonnet |
| impl-reviewer | タスクごとの合否判定、design break の分類 | opus |
| integration-reviewer | 変更全体の整合性、チェック実行、人間レビューガイド | opus |
| pr-writer | push と `gh pr create` | sonnet |

fable は白紙から構造を作る `design` のみ。明文化された基準に照合するレビュー系は opus、調査・実装・定型作業は sonnet。

## 構成

```
skills/run, resume, status      ユーザーが起動する入口
skills/workboard                ホワイトボードの Schema と規約(Agent 専用)
skills/clarify                  grill-me 形式ヒアリング(1 問ずつ、推奨回答付き。Agent 専用)
skills/small-flow, large-flow   オーケストレーション手順(Agent 専用、再入可能)
agents/*.md                     Sub Agent 定義
hooks/hooks.json                write_scope guard
scripts/init-session.sh         セッションディレクトリの作成
scripts/status.py               status.json の読み書き、実行可能タスクの列挙
scripts/plan-waves.py           plan.json の検証、write_scope 競合の検出、Wave 割当
scripts/guard-write-scope.py    PreToolUse hook
```

## 必要なもの

`git`、`gh`(認証済み)、`python3`。

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
