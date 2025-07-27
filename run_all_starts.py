import subprocess
import os
import time
import sys
import math

# 処理対象のWebText_extractionフォルダーのリスト
work_directories = [
    "WebText_extraction",
    "WebText_extraction2",
    "WebText_extraction3",
    "WebText_extraction4",
    "WebText_extraction5",
    "WebText_extraction6",
    "WebText_extraction7",
    "WebText_extraction8",
    "WebText_extraction9",
    "WebText_extraction10",
]

def get_remaining_txt_files(delivery_folder_path):
    """処理されていないテキストファイルのみを取得"""
    try:
        # delivery_folder内のすべての.txtファイルを取得
        all_txt_files = sorted([f for f in os.listdir(delivery_folder_path) if f.endswith(".txt")])
        
        # completed_folder内のファイルを取得（処理済みファイル）
        completed_folder_path = os.path.join(delivery_folder_path, "completed_folder")
        completed_files = []
        if os.path.exists(completed_folder_path):
            completed_files = [f for f in os.listdir(completed_folder_path) if f.endswith(".txt")]
        
        # 処理されていないファイルのみを返す
        remaining_files = [f for f in all_txt_files if f not in completed_files]
        return remaining_files
        
    except FileNotFoundError:
        print(f"エラー: delivery_folder が見つかりません: {delivery_folder_path}")
        return []
    except Exception as e:
        print(f"エラー: delivery_folder の読み取り中に問題が発生しました: {e}")
        return []

def process_batch(txt_files, batch_number, total_files, processed_files):
    """バッチ処理を実行する"""
    batch_size = len(txt_files)
    remaining_files = total_files - processed_files
    
    print(f"\n===== バッチ {batch_number} を処理中 =====")
    print(f"総ファイル数: {total_files}")
    print(f"処理済み: {processed_files}")
    print(f"今回処理: {batch_size}")
    print(f"残り: {remaining_files - batch_size}")
    print("=" * 50)
    
    # キーワードリストを作成 (ファイル名から拡張子を除いたもの)
    keywords = [os.path.splitext(f)[0] for f in txt_files]
    
    # work_directoriesをキーワードの数に合わせて調整
    current_work_directories = work_directories[:len(keywords)]
    
    processes = []
    commands_to_run = []
    
    print("delivery_folder からキーワードを自動取得し、フォルダーに割り当てます...")
    
    # 共通のstart.pyのパス
    common_start_script = os.path.join(script_directory, "common_scripts", "start.py")
    
    if not os.path.exists(common_start_script):
        print(f"エラー: 共通のstart.pyが見つかりません: {common_start_script}")
        return False
    
    for i, work_dir_name in enumerate(current_work_directories):
        # 作業ディレクトリの絶対パス
        work_dir_abs_path = os.path.join(script_directory, work_dir_name)
        
        if not os.path.exists(work_dir_abs_path):
            print(f"エラー: {work_dir_abs_path} が見つかりません。スキップします。")
            continue
        
        keyword = keywords[i]
        commands_to_run.append({
            'dir': work_dir_abs_path, 
            'script_path': common_start_script, 
            'keyword': keyword, 
            'work_dir_name': work_dir_name
        })
        print(f"'{work_dir_name}' フォルダーにキーワード '{keyword}' を割り当てました。")
    
    print("\nキーワードの割り当てが完了しました。スクリプトを起動します...")
    
    # プロセス起動
    for command_info in commands_to_run:
        try:
            process = subprocess.Popen(
                [sys.executable, command_info['script_path'], command_info['keyword']],
                cwd=command_info['dir'],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            processes.append(process)
            print(f"{command_info['work_dir_name']} フォルダーで共通start.pyをキーワード '{command_info['keyword']}' で起動しました。")
            time.sleep(5)  # 5秒待機
        except FileNotFoundError:
            print(f"エラー: Pythonインタープリタが見つからないか、{command_info['script_path']} (作業ディレクトリ: {command_info['dir']}) の実行に失敗しました。")
        except Exception as e:
            print(f"エラー: {command_info['work_dir_name']} での起動中に問題が発生しました: {e}")
    
    print("\nすべてのスクリプトの起動を試みました。")
    print("プロセスの完了を待機中...")
    
    # すべての子プロセスが終了するのを待つ
    for i, p in enumerate(processes):
        print(f"プロセス {i+1}/{len(processes)} の完了を待機中...")
        p.wait()
    
    print(f"バッチ {batch_number} の処理が完了しました。")
    return True

# スクリプト自身のディレクトリを取得
script_directory = os.path.dirname(os.path.abspath(__file__))
delivery_folder_path = os.path.join(script_directory, "delivery_folder")

if not os.path.isdir(delivery_folder_path):
    print(f"エラー: delivery_folder が見つかりません: {delivery_folder_path}")
    exit() # フォルダが見つからない場合は終了

def main():
    """メイン処理：バッチ処理ループを実行"""
    batch_number = 0
    total_files_processed = 0
    
    print("=" * 60)
    print("自動バッチ処理システムを開始します")
    print("=" * 60)
    
    # 初回の全ファイル数を取得（進捗表示用）
    initial_files = get_remaining_txt_files(delivery_folder_path)
    total_initial_files = len(initial_files)
    
    if total_initial_files == 0:
        print("処理対象のテキストファイルが見つかりません。")
        print("delivery_folder内にテキストファイルを配置してから実行してください。")
        return
    
    print(f"処理対象ファイル数: {total_initial_files}")
    total_batches = math.ceil(total_initial_files / len(work_directories))
    print(f"予想バッチ数: {total_batches}")
    print()
    
    while True:
        batch_number += 1
        
        # 残りのテキストファイルを取得
        remaining_txt_files = get_remaining_txt_files(delivery_folder_path)
        
        # 処理するファイルがない場合は終了
        if not remaining_txt_files:
            print("\n" + "=" * 60)
            print("🎉 すべてのファイルの処理が完了しました！")
            print(f"総処理ファイル数: {total_files_processed}")
            print(f"実行バッチ数: {batch_number - 1}")
            print("=" * 60)
            break
        
        # 現在のバッチで処理するファイル数を決定
        batch_size = min(len(remaining_txt_files), len(work_directories))
        current_batch_files = remaining_txt_files[:batch_size]
        
        # バッチ処理を実行
        success = process_batch(
            current_batch_files, 
            batch_number, 
            total_initial_files, 
            total_files_processed
        )
        
        if not success:
            print(f"⚠️ バッチ {batch_number} の処理中にエラーが発生しました。")
            print("処理を継続しますが、結果を確認してください。")
        
        total_files_processed += batch_size
        
        # バッチ間の待機時間
        if len(get_remaining_txt_files(delivery_folder_path)) > 0:
            print(f"\n次のバッチまで10秒待機します...")
            time.sleep(10)

# メイン処理を実行
if __name__ == "__main__":
    main()
