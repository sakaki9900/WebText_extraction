#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebTextExtraction プロジェクト用テキストファイル一括削除プログラム
トークン数節約のため、各ワークスペースから指定ファイルを一括削除します。
"""

import os
import sys
import glob
from pathlib import Path

# Windows環境での文字化け対策
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)


def get_target_files():
    """削除対象ファイルのリストを定義"""
    return [
        'Integrated_Text/Integrated_Text.txt',
        'outputs/google_urls_extracted.txt', 
        'outputs/yahoo_urls_extracted.txt',
        'urls/google_urls.txt',
        'urls/yahoo_urls.txt'
    ]


def find_workspace_folders():
    """WebText_extraction* フォルダを検出"""
    pattern = 'WebText_extraction*'
    folders = glob.glob(pattern)
    # WebText_extraction フォルダも含める（番号なし）
    base_folder = 'WebText_extraction'
    if os.path.exists(base_folder) and base_folder not in folders:
        folders.append(base_folder)
    
    folders.sort()  # ソートして処理順序を安定化
    return folders


def delete_files_in_workspace(workspace_folder, target_files):
    """指定ワークスペース内の対象ファイルを削除"""
    deleted_count = 0
    not_found_count = 0
    error_count = 0
    
    print(f"\n[フォルダ] {workspace_folder} を処理中...")
    
    for file_path in target_files:
        full_path = os.path.join(workspace_folder, file_path)
        
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                print(f"  [OK] 削除: {file_path}")
                deleted_count += 1
            except Exception as e:
                print(f"  [エラー] {file_path} - {e}")
                error_count += 1
        else:
            print(f"  [未存在] {file_path}")
            not_found_count += 1
    
    return deleted_count, not_found_count, error_count


def confirm_deletion(workspace_folders, target_files):
    """削除実行前の確認"""
    print("=" * 60)
    print("WebTextExtraction テキストファイル一括削除ツール")
    print("=" * 60)
    
    print(f"\n検出されたワークスペース: {len(workspace_folders)}個")
    for folder in workspace_folders:
        print(f"  - {folder}")
    
    print(f"\n削除対象ファイル: {len(target_files)}種類")
    for file_path in target_files:
        print(f"  - {file_path}")
    
    total_potential_files = len(workspace_folders) * len(target_files)
    print(f"\n最大削除可能ファイル数: {total_potential_files}個")
    
    print("\n[警告] この操作は元に戻せません。続行しますか？")
    response = input("削除を実行する場合は 'yes' と入力してください: ").strip().lower()
    
    return response == 'yes'


def main():
    """メイン処理"""
    # 現在のディレクトリがプロジェクトルートかチェック
    if not os.path.exists('run_all_starts.py'):
        print("[エラー] プロジェクトルートディレクトリで実行してください。")
        return
    
    # ワークスペースフォルダを検出
    workspace_folders = find_workspace_folders()
    if not workspace_folders:
        print("[エラー] WebText_extraction* フォルダが見つかりません。")
        return
    
    # 削除対象ファイルを取得
    target_files = get_target_files()
    
    # ユーザー確認
    if not confirm_deletion(workspace_folders, target_files):
        print("\n削除処理がキャンセルされました。")
        return
    
    # 削除実行
    print("\n" + "=" * 40)
    print("削除処理を開始します...")
    print("=" * 40)
    
    total_deleted = 0
    total_not_found = 0
    total_errors = 0
    
    for workspace in workspace_folders:
        deleted, not_found, errors = delete_files_in_workspace(workspace, target_files)
        total_deleted += deleted
        total_not_found += not_found
        total_errors += errors
    
    # 結果サマリー
    print("\n" + "=" * 40)
    print("削除処理完了 - 結果サマリー")
    print("=" * 40)
    print(f"削除成功: {total_deleted}個")
    print(f"ファイル未存在: {total_not_found}個")
    print(f"エラー発生: {total_errors}個")
    print(f"処理ワークスペース: {len(workspace_folders)}個")
    
    if total_errors == 0:
        print("\nすべての削除処理が正常に完了しました！")
    else:
        print(f"\n{total_errors}個のエラーが発生しました。詳細は上記をご確認ください。")


if __name__ == "__main__":
    main()