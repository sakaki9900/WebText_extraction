# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

このプロジェクトは、検索キーワードに基づいてGoogle・YahooからWebテキストを自動抽出・統合するシステムです。

## 基本ワークフロー

1. **キーワード作成**: `delivery_folder/create_file.py`でキーワードファイル(.txt)を作成
2. **自動実行**: `run_all_starts.py`を実行すると、`common_scripts/`内のプログラムが順次自動実行
3. **最終出力**: 結果は`delivery_folder/completed_folder/`にまとめて出力

## 主要コマンド

### 基本実行
```bash
# キーワードファイル作成
python delivery_folder/create_file.py

# 全自動実行
python run_all_starts.py
```

### 依存関係インストール
```bash
pip install -r requirements.txt
```

## アーキテクチャ

### 並列処理システム
- **並列ワークスペース**: `WebText_extraction[1-10]/` - 最大10並列処理
- **共通処理スクリプト**: `common_scripts/` - 全ワークスペースで共有
- **統合配信**: `delivery_folder/` - キーワード管理と最終出力

### 処理フロー
各ワークスペースで以下が順次実行されます：
1. `google_url_serch.py` - Google検索URL抽出
2. `yahoo_url_search.py` - Yahoo検索URL抽出  
3. `web_text_extractor_ver1.5.py` - Webテキスト抽出（CPU制限・タイムアウト機能付き）
4. `integrated.py` - Google・Yahoo結果統合
5. `update_delivery_file.py` - 最終配信

### 重要な設定ファイル

#### `config.ini`
各WebText_extractionフォルダ内の設定：
- `cpu_ratio`: CPU使用率制限（0.0-1.0）
- Google・Yahoo検索URL設定

#### `requirements.txt`
- **beautifulsoup4**: HTML解析
- **selenium**: Webブラウザ自動化
- **webdriver-manager**: ChromeDriver管理
- **PyPDF2**: PDF処理

## フォルダ構造

### 処理ワークスペース
```
WebText_extraction*/
├── config.ini          # 設定ファイル
├── urls/               # 抽出URL一覧
├── outputs/            # サイト別抽出テキスト
├── Integrated_Text/    # 統合最終テキスト
└── chromedriver-win64/ # Seleniumドライバー
```

### 配信フォルダ
```
delivery_folder/
├── create_file.py      # キーワードファイル作成
├── [keyword].txt       # 検索キーワードファイル
└── completed_folder/   # 最終統合結果
```

## 主要機能

### テキスト抽出機能
- 動的コンテンツ対応（Selenium使用）
- PDF文書からのテキスト抽出
- 10分タイムアウト処理
- CPU使用率制限機能

### エラーハンドリング
- ファイル名サニタイゼーション（Windows非対応文字処理）
- 前回処理ファイルの自動クリーンアップ
- タイムアウトURL自動検出・報告
- 包括的なエラーログ出力

## 開発・保守時の注意点

### 共通スクリプト変更
`common_scripts/`内のファイルを変更すると、全ワークスペースに影響するため注意が必要

### 並列処理数調整
WebText_extractionフォルダの数を増減することで並列処理数を調整可能

### 設定変更
各ワークスペースの`config.ini`は独立しているため、統一的な変更が必要な場合は全フォルダを更新

### ChromeDriver
`chromedriver-win64/`はSelenium動作に必須。更新時は全ワークスペースで同期が必要