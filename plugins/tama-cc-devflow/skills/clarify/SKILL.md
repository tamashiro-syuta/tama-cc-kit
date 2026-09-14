---
name: clarify
description: devflow の grill-me 形式ヒアリング。未決事項を依存関係順に 1 問ずつ、推奨回答付きで人間に確認し、決定ツリーの各枝が解消するまで続ける。回答は context.md と decisions.md に記録する。devflow のオーケストレーション Skill から呼ばれる。直接使用するものではない。
user-invocable: false
---

# clarify(grill-me 形式ヒアリング)

入力: 呼び出し元が指定する未決事項のリスト(`router.md` の Questions for human、`design/design.md` の Open questions、レビューの Human decision required、上限到達時の争点など)と `SESSION_DIR`。

## 手順

1. **コードベースで答えが出る質問は人間に聞かない。** `tama-cc-devflow:explore` で調べて答えを確定し、`context.md` の Clarifications に「調査で確定」と明記して記録する。
2. 残った質問を依存関係順に並べる。ある回答が他の質問の前提になるものを先に聞く。
3. **1 問ずつ聞く。** 各質問に必ず推奨回答とその理由を付ける。選択肢が離散的なら AskUserQuestion を使い、推奨案を先頭に置いて「(推奨)」と付ける。1 問ごとにターンを終えて回答を待つ。
4. 回答を得たら即座に記録する。事実や仕様の確定は `context.md` の Clarifications に、方針を決める回答は `decisions.md` に `## Dn:` として理由付きで書く。回答が新しい疑問を生んだらリストに追加し、依存関係順を保って続ける。
5. 「任せる」と言われたら推奨回答を採用し、人間が委任した旨を記録する。
6. すべての枝が解消したら、確定事項の一覧を 1 回だけ人間に示して終了する。呼び出し元に「解消した質問数」と「decisions.md に追加した id」を返す。

## ルール

- まとめて聞かない。1 問ずつ。
- 質問は具体的に。「どうしますか」ではなく、選択肢とそれぞれの影響を示す。
- 質問数に上限は設けない。ただし同じ論点を言い換えて再質問しない。
- ヒアリング中に phase は変えない。呼び出し元のフェーズのまま進める(Router 段階だけは `run` Skill が phase を `clarify` にする)。
- ヒアリングの結果として設計や計画を自分で書き換えない。記録だけ行い、改訂は呼び出し元が該当 Agent に依頼する。
