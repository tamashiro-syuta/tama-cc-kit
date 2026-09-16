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

## 更新

marketplace の更新と plugin の更新は別。main に push した後、両方を順に実行する。

```
/plugin marketplace update tama-cc-kit
/plugin update tama-cc-devflow@tama-cc-kit
```

ターミナルからは同じ操作を `claude plugin` で行える。

```
claude plugin marketplace update tama-cc-kit
claude plugin update tama-cc-devflow@tama-cc-kit
```

## その他の操作

```
/plugin list                                  # インストール済み plugin の一覧
/plugin disable tama-cc-devflow@tama-cc-kit   # 無効化(設定は残る)
/plugin enable tama-cc-devflow@tama-cc-kit
/plugin uninstall tama-cc-devflow@tama-cc-kit
/plugin marketplace remove tama-cc-kit
```

## 開発

```
claude --plugin-dir ./plugins/tama-cc-devflow
claude plugin validate ./plugins/tama-cc-devflow --strict
claude plugin validate . --strict
```
