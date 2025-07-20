#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
エラーページクリーンアップツール

既存のエラーファイルを検出し、自動削除する機能を提供します。
outputsフォルダとIntegrated_Textフォルダの両方をスキャンし、
config.iniで定義されたエラーパターンに一致するファイルを削除します。
"""

import os
import configparser
import shutil
from datetime import datetime
from pathlib import Path


class ErrorPageCleanup:
    """エラーページファイルのクリーンアップを行うクラス"""
    
    def __init__(self, config_path='config.ini'):
        """
        初期化メソッド
        
        Parameters:
        config_path (str): 設定ファイルのパス
        """
        self.config_path = config_path
        self.error_patterns = []
        self.enabled = True
        self.backup_enabled = True
        self.load_config()
    
    def load_config(self):
        """config.iniからエラーパターンを読み込む"""
        config = configparser.ConfigParser()
        
        try:
            if os.path.exists(self.config_path):
                config.read(self.config_path, encoding='utf-8')
                
                if 'ERROR_PATTERNS' in config:
                    # 機能が有効かチェック
                    self.enabled = config.getboolean('ERROR_PATTERNS', 'enabled', fallback=True)
                    
                    if not self.enabled:
                        print(f"情報: エラーパターンクリーンアップ機能は無効です ({self.config_path})")
                        return
                    
                    # バックアップ設定
                    self.backup_enabled = config.getboolean('ERROR_PATTERNS', 'backup_enabled', fallback=True)
                    
                    # エラーパターンを取得
                    browser_errors = config.get('ERROR_PATTERNS', 'browser_errors', fallback='')
                    custom_patterns = config.get('ERROR_PATTERNS', 'custom_patterns', fallback='')
                    
                    # パターンリストを作成
                    if browser_errors:
                        self.error_patterns.extend([pattern.strip() for pattern in browser_errors.split(',') if pattern.strip()])
                    if custom_patterns:
                        self.error_patterns.extend([pattern.strip() for pattern in custom_patterns.split(',') if pattern.strip()])
                    
                    print(f"読み込み完了: {len(self.error_patterns)} 個のエラーパターン")
                else:
                    print(f"警告: {self.config_path} にERROR_PATTERNSセクションが見つかりません")
            else:
                print(f"警告: 設定ファイルが見つかりません: {self.config_path}")
                
        except (configparser.Error, ValueError) as e:
            print(f"設定ファイル読み込みエラー: {e}")
    
    def backup_file(self, file_path):
        """
        ファイルのバックアップを作成する
        
        Parameters:
        file_path (str): バックアップ対象のファイルパス
        
        Returns:
        str: バックアップファイルのパス (失敗時はNone)
        """
        if not self.backup_enabled:
            return None
            
        if not os.path.exists(file_path):
            return None
        
        # バックアップファイル名を生成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"{file_path}.backup_{timestamp}"
        
        try:
            shutil.copy2(file_path, backup_file)
            print(f"バックアップ作成: {file_path} -> {backup_file}")
            return backup_file
        except Exception as e:
            print(f"バックアップ作成エラー: {e}")
            return None
    
    def contains_error_pattern(self, text):
        """
        テキストにエラーパターンが含まれているかチェック
        
        Parameters:
        text (str): チェック対象のテキスト
        
        Returns:
        tuple: (bool, str) - (エラー検出, 一致したパターン)
        """
        if not text or not self.error_patterns:
            return False, None
        
        for pattern in self.error_patterns:
            if pattern in text:
                return True, pattern
        
        return False, None
    
    def scan_output_files(self, workspace_path):
        """
        outputsフォルダをスキャンしてエラーファイルを検出
        
        Parameters:
        workspace_path (str): ワークスペースのパス
        
        Returns:
        list: エラーファイルのパスリスト
        """
        error_files = []
        outputs_path = os.path.join(workspace_path, 'outputs')
        
        if not os.path.exists(outputs_path):
            print(f"情報: outputsフォルダが存在しません: {outputs_path}")
            return error_files
        
        try:
            for filename in os.listdir(outputs_path):
                if filename.endswith('.txt'):
                    file_path = os.path.join(outputs_path, filename)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        has_error, matched_pattern = self.contains_error_pattern(content)
                        if has_error:
                            error_files.append(file_path)
                            print(f"エラーファイル検出 (outputs): {file_path} - パターン: '{matched_pattern}'")
                    
                    except Exception as e:
                        print(f"ファイル読み込みエラー: {file_path} - {e}")
        
        except Exception as e:
            print(f"outputsフォルダスキャンエラー: {e}")
        
        return error_files
    
    def scan_integrated_files(self, workspace_path):
        """
        Integrated_Textフォルダをスキャンしてエラーファイルを検出
        
        Parameters:
        workspace_path (str): ワークスペースのパス
        
        Returns:
        list: エラーファイルのパスリスト
        """
        error_files = []
        integrated_path = os.path.join(workspace_path, 'Integrated_Text')
        
        if not os.path.exists(integrated_path):
            print(f"情報: Integrated_Textフォルダが存在しません: {integrated_path}")
            return error_files
        
        try:
            for filename in os.listdir(integrated_path):
                if filename.endswith('.txt'):
                    file_path = os.path.join(integrated_path, filename)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        has_error, matched_pattern = self.contains_error_pattern(content)
                        if has_error:
                            error_files.append(file_path)
                            print(f"エラーファイル検出 (Integrated_Text): {file_path} - パターン: '{matched_pattern}'")
                    
                    except Exception as e:
                        print(f"ファイル読み込みエラー: {file_path} - {e}")
        
        except Exception as e:
            print(f"Integrated_Textフォルダスキャンエラー: {e}")
        
        return error_files
    
    def remove_error_files(self, file_list):
        """
        エラーファイルを削除する
        
        Parameters:
        file_list (list): 削除対象ファイルのパスリスト
        
        Returns:
        dict: {'removed': [...], 'failed': [...]} - 削除結果
        """
        results = {'removed': [], 'failed': []}
        
        if not file_list:
            print("削除対象のファイルがありません")
            return results
        
        print(f"削除対象: {len(file_list)} 個のファイル")
        
        for file_path in file_list:
            try:
                # バックアップを作成（設定が有効な場合）
                backup_file = self.backup_file(file_path)
                
                # ファイルを削除
                os.remove(file_path)
                results['removed'].append(file_path)
                print(f"削除完了: {file_path}")
                
                if backup_file:
                    print(f"  バックアップ: {backup_file}")
            
            except Exception as e:
                results['failed'].append((file_path, str(e)))
                print(f"削除失敗: {file_path} - {e}")
        
        return results
    
    def cleanup_workspace(self, workspace_path):
        """
        指定されたワークスペースのエラーファイルをクリーンアップする
        
        Parameters:
        workspace_path (str): ワークスペースのパス
        
        Returns:
        dict: クリーンアップ結果
        """
        if not self.enabled:
            print("クリーンアップ機能は無効です")
            return {'removed': [], 'failed': []}
        
        print(f"ワークスペースクリーンアップ開始: {workspace_path}")
        
        # outputsフォルダをスキャン
        output_errors = self.scan_output_files(workspace_path)
        
        # Integrated_Textフォルダをスキャン
        integrated_errors = self.scan_integrated_files(workspace_path)
        
        # 全てのエラーファイルを統合
        all_error_files = output_errors + integrated_errors
        
        if not all_error_files:
            print(f"エラーファイルは見つかりませんでした: {workspace_path}")
            return {'removed': [], 'failed': []}
        
        # 重複を除去
        unique_error_files = list(set(all_error_files))
        print(f"検出されたエラーファイル: {len(unique_error_files)} 個")
        
        # ファイルを削除
        results = self.remove_error_files(unique_error_files)
        
        print(f"クリーンアップ完了: {workspace_path}")
        print(f"  削除成功: {len(results['removed'])} 個")
        print(f"  削除失敗: {len(results['failed'])} 個")
        
        return results
    
    def cleanup_all_workspaces(self, base_path='.'):
        """
        全てのWebText_extractionワークスペースをクリーンアップする
        
        Parameters:
        base_path (str): ベースパス（デフォルトは現在のディレクトリ）
        
        Returns:
        dict: 全体のクリーンアップ結果
        """
        if not self.enabled:
            print("クリーンアップ機能は無効です")
            return {'total_removed': 0, 'total_failed': 0, 'workspaces': {}}
        
        print("全ワークスペースクリーンアップ開始")
        
        total_results = {'total_removed': 0, 'total_failed': 0, 'workspaces': {}}
        
        # WebText_extractionフォルダを検索
        workspace_patterns = ['WebText_extraction', 'WebText_extraction[0-9]*']
        
        for pattern in workspace_patterns:
            import glob
            workspace_paths = glob.glob(os.path.join(base_path, pattern))
            
            for workspace_path in workspace_paths:
                if os.path.isdir(workspace_path):
                    workspace_name = os.path.basename(workspace_path)
                    print(f"\n--- {workspace_name} の処理開始 ---")
                    
                    results = self.cleanup_workspace(workspace_path)
                    total_results['workspaces'][workspace_name] = results
                    total_results['total_removed'] += len(results['removed'])
                    total_results['total_failed'] += len(results['failed'])
        
        print(f"\n=== 全ワークスペースクリーンアップ完了 ===")
        print(f"処理ワークスペース: {len(total_results['workspaces'])} 個")
        print(f"削除成功ファイル: {total_results['total_removed']} 個")
        print(f"削除失敗ファイル: {total_results['total_failed']} 個")
        
        return total_results


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='エラーページファイルクリーンアップツール')
    parser.add_argument('--workspace', '-w', help='特定のワークスペースのパス')
    parser.add_argument('--all', '-a', action='store_true', help='全ワークスペースをクリーンアップ')
    parser.add_argument('--config', '-c', default='config.ini', help='設定ファイルのパス')
    parser.add_argument('--dry-run', action='store_true', help='実際の削除は行わず、検出のみ実行')
    
    args = parser.parse_args()
    
    # クリーンアップインスタンスを作成
    cleanup = ErrorPageCleanup(config_path=args.config)
    
    if not cleanup.enabled:
        print("エラーパターンクリーンアップ機能が無効です")
        return
    
    # ドライランモードの処理
    if args.dry_run:
        print("=== ドライランモード（実際の削除は行いません） ===")
        # 一時的にbackup_enabledを無効にして削除処理をスキップ
        original_backup = cleanup.backup_enabled
        cleanup.backup_enabled = False
        
        # remove_error_filesをオーバーライド
        def dry_run_remove(file_list):
            print(f"削除対象として検出されたファイル: {len(file_list)} 個")
            for file_path in file_list:
                print(f"  - {file_path}")
            return {'removed': [], 'failed': []}
        
        cleanup.remove_error_files = dry_run_remove
    
    if args.workspace:
        # 特定のワークスペースをクリーンアップ
        if not os.path.exists(args.workspace):
            print(f"エラー: ワークスペースが見つかりません: {args.workspace}")
            return
        
        results = cleanup.cleanup_workspace(args.workspace)
    
    elif args.all:
        # 全ワークスペースをクリーンアップ
        results = cleanup.cleanup_all_workspaces()
    
    else:
        # デフォルト：カレントディレクトリの全ワークスペース
        results = cleanup.cleanup_all_workspaces()


if __name__ == "__main__":
    main()