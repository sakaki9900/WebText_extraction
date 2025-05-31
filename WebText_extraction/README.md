# WebText Extractor

URLリストからWebページのメインコンテンツを抽出するツールです。

## 機能

- URLリストからWebページのメインコンテンツのみを抽出
- 異なるサイト（X/Twitter、Instagram、Yahoo知恵袋、YouTubeなど）に対応した特殊処理
- 指定されたCPUコア数による並列処理
- 「その他の回答をもっと見る」や「さらに返信を表示」などの隠れたコンテンツの取得

## 必要環境

- Python 3.6以上
- Chrome ブラウザ
- インターネット接続

## インストール

必要なパッケージをインストールします：

```bash
pip install -r requirements.txt
```

## 使い方

1. `urls/sample_urls.txt` にURLのリストを記述します（1行に1つのURL）
2. 以下のコマンドを実行します：

```bash
python web_text_extractor.py
```

オプション：

```bash
python web_text_extractor.py --urls=URLリストファイルパス --output=出力先ファイルパス --workers=並列処理数
```

- `--urls`: URLリストのファイルパス（デフォルト：`urls/sample_urls.txt`）
- `--output`: 抽出結果の出力先（デフォルト：`outputs/extracted_texts.txt`）
- `--workers`: 並列処理に使用するワーカー数（指定なしの場合はCPUコア数）

## 出力形式

出力ファイルは以下の形式になります：

```
(webページのurl)
(webページの本文)


(webページのurl)
(webページの本文)


...
```

## 注意事項

- 一部のWebサイトは自動スクレイピングを制限している場合があります
- InstagramやXなどのSNSは認証が必要な場合があり、完全な抽出ができないことがあります
- 抽出の精度はWebサイトの構造によって異なります
- 大量のURLを一度に処理すると、IPアドレスが一時的にブロックされる可能性があります