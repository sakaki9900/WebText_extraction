# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Key Rules
- Actively use Context7 
- Separate client/common code
- Please respond in Japanese every time
- Please generate the coding plan in Japanese.
- Please actively conduct web searches as needed.
- Please absolutely avoid hallucinations. If something is difficult to achieve, please clearly state that it is difficult to achieve. Absolutely avoid proceeding under the assumption that you can do things that cannot be done.

## システム概要

このコードベースは、キーワードベースのWebテキスト収集と処理を行う自動化システムです。Google/Yahoo検索結果からURLを抽出し、各ページのテキストコンテンツを並列処理で収集・統合します。

### アーキテクチャ構成

1. **並列実行フレームワーク**: 複数のWebText_extractionインスタンス（WebText_extraction～WebText_extraction10）で並列処理
2. **マルチステップパイプライン**: URL収集→テキスト抽出→統合→ファイル管理の段階的処理
3. **キーワード駆動型**: delivery_folder内のテキストファイル名をキーワードとして自動処理

### 主要コンポーネント

- **run_all_starts.py**: 複数インスタンスの統合制御（エントリーポイント）
- **start.py**: 単一キーワードの全工程実行（各WebText_extractionディレクトリ内）
- **URL収集**: google_url_serch.py / yahoo_url_search.py
- **テキスト抽出**: web_text_extractor_ver1.5.py（並列処理・CPU制限機能付き）
- **データ統合**: integrated.py
- **ファイル管理**: update_delivery_file.py
- **ファイル生成**: delivery_folder/create_file.py

## 開発・実行コマンド

### セットアップ
```bash
# 依存関係のインストール
cd WebText_extraction
pip install -r requirements.txt

# ChromeDriverの設定確認
# chromedriver-win64/chromedriver.exe が存在することを確認
```

### 基本実行
```bash
# 新しいキーワードファイルの作成
cd delivery_folder
python create_file.py

# 単一キーワードの処理
cd WebText_extraction
python start.py

# 複数キーワードの並列処理（推奨）
python run_all_starts.py
```

### CPU使用率制御
```bash
# config.iniでCPU使用率を調整
# [Settings]
# cpu_ratio = 0.7  # 70%に制限
```

### デバッグ・個別実行
```bash
# URL収集のみ
python google_url_serch.py <keyword>
python yahoo_url_search.py <keyword>

# テキスト抽出のみ
python web_text_extractor_ver1.5.py

# 統合処理のみ
python integrated.py

# ファイル更新のみ
python update_delivery_file.py <keyword>
```

## 設定ファイル構造

### config.ini
- **cpu_ratio**: web_text_extractor_ver1.5.pyのCPU使用率制限（0.1-1.0）
- **google_search_url / yahoo_search_url**: 自動生成される検索URL

### requirements.txt
主要依存関係:
- selenium==4.18.1
- beautifulsoup4==4.12.3
- requests==2.31.0
- PyPDF2==3.0.1
- webdriver-manager==4.0.1

## ディレクトリ構造

```
WebText_extraction_folder/
├── run_all_starts.py              # メイン実行スクリプト
├── config.ini                     # グローバル設定
├── WebText_extraction[1-10]/       # 並列処理インスタンス
│   ├── start.py                   # 単一キーワード処理
│   ├── google_url_serch.py        # Google URL収集
│   ├── yahoo_url_search.py        # Yahoo URL収集
│   ├── web_text_extractor_ver1.5.py # テキスト抽出
│   ├── integrated.py              # テキスト統合
│   ├── update_delivery_file.py    # ファイル更新
│   ├── urls/                      # 収集URL格納
│   ├── outputs/                   # 抽出テキスト格納
│   ├── Integrated_Text/           # 統合結果格納
│   └── chromedriver-win64/        # WebDriver
├── delivery_folder/               # キーワードファイル管理
│   ├── create_file.py            # ファイル作成ツール
│   ├── completed_folder/         # 処理済みファイル
│   └── *.txt                     # 処理対象ファイル
└── outputs/                      # 全体出力
```

## 開発時の注意事項

### Seleniumドライバー管理
- ChromeDriverのバージョンとChromeブラウザのバージョンを一致させる
- webdriver-managerによる自動管理も利用可能

### 並列処理の制御
- CPU使用率はconfig.iniのcpu_ratioで制御
- 同時実行数はrun_all_starts.pyで自動調整

### エラーハンドリング
- 各スクリプトは独立して実行可能
- 中断された処理は該当ステップから再開可能

### ファイル命名規則
- キーワードファイル: `<キーワード>.txt`
- 出力ファイル: `google_urls_extracted.txt`, `yahoo_urls_extracted.txt`
- 統合ファイル: `Integrated_Text.txt`（BOM付きUTF-8）

## パフォーマンス最適化

### 並列処理の効率化
- WebText_extraction1～10の負荷分散
- CPU制限によるシステム安定性確保
- Seleniumの並列実行制御

### メモリ管理
- 大容量テキストファイルの段階的処理
- 一時ファイルの自動クリーンアップ
