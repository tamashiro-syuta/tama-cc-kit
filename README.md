# tama-cc-kit

Claude Code plugin の marketplace。

| Plugin | 説明 |
|---|---|
| [tama-cc-devflow](plugins/tama-cc-devflow/README.md) | タスクの重さに応じて流れを変えるマルチ Agent 開発フロー(Small / Large ルーティング、設計・実装のレビューループ、Wave 単位の並列タスク、チェックポイントからの再開)。詳細は [docs/tama-cc-devflow.md](docs/tama-cc-devflow.md) |

## インストール

```
/plugin marketplace add tamashiro-syuta/tama-cc-kit
/plugin install tama-cc-devflow@tama-cc-kit
```

## 開発

```
claude --plugin-dir ./plugins/tama-cc-devflow
claude plugin validate ./plugins/tama-cc-devflow --strict
claude plugin validate . --strict
```
