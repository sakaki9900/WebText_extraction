#!/usr/bin/env python3
import os
import sys
import subprocess

def main():
    """
    共通スクリプトのstart.pyを現在のディレクトリをワーキングディレクトリとして実行する
    """
    # 現在のスクリプトのディレクトリ（WebText_extractionフォルダー）を取得
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 共通スクリプトのパスを取得
    common_scripts_dir = os.path.join(current_dir, "..", "common_scripts")
    start_script_path = os.path.join(common_scripts_dir, "start.py")
    
    # 共通スクリプトが存在するかチェック
    if not os.path.exists(start_script_path):
        print(f"エラー: 共通スクリプト '{start_script_path}' が見つかりません。", file=sys.stderr)
        sys.exit(1)
    
    # 現在のディレクトリをワーキングディレクトリとして共通スクリプトを実行
    try:
        # コマンドライン引数をそのまま渡す
        command = [sys.executable, start_script_path] + sys.argv[1:]
        
        # 現在のディレクトリで実行
        result = subprocess.run(command, cwd=current_dir)
        
        # 終了コードを引き継ぐ
        sys.exit(result.returncode)
        
    except Exception as e:
        print(f"エラー: スクリプト実行中に例外が発生しました: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()