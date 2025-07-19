import subprocess
import os
import time
import sys

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

# スクリプト自身のディレクトリを取得
script_directory = os.path.dirname(os.path.abspath(__file__))
delivery_folder_path = os.path.join(script_directory, "delivery_folder")

if not os.path.isdir(delivery_folder_path):
    print(f"エラー: delivery_folder が見つかりません: {delivery_folder_path}")
    exit() # フォルダが見つからない場合は終了

# delivery_folder内のtxtファイルを取得し、名前順にソートする
try:
    # まず全ての.txtファイルを取得
    txt_files_all = sorted([f for f in os.listdir(delivery_folder_path) if f.endswith(".txt")])
except FileNotFoundError:
    # このケースは上のisdirでチェック済みだが念のため
    print(f"エラー: delivery_folder が見つかりません: {delivery_folder_path}")
    exit()
except Exception as e:
    print(f"エラー: delivery_folder の読み取り中に問題が発生しました: {e}")
    exit()

# txtファイルの数をチェックし、利用可能なファイル数に応じて動作を調整する
if len(txt_files_all) == 0:
    print(f"エラー: delivery_folder 内にテキストファイルが見つかりませんでした。")
    print("少なくとも1個のテキストファイルが必要です。処理を中断します。")
    exit()
elif len(txt_files_all) > len(work_directories):
    print(f"情報: delivery_folder 内に {len(txt_files_all)} 個のテキストファイルが見つかりました。")
    print(f"最初の {len(work_directories)} 個のファイルのみをキーワードとして使用します。")
    txt_files = txt_files_all[:len(work_directories)] # work_directoriesの数だけ取得
else:
    # txtファイルがwork_directoriesの数以下の場合
    print(f"情報: delivery_folder 内に {len(txt_files_all)} 個のテキストファイルが見つかりました。")
    print(f"利用可能な {len(txt_files_all)} 個のフォルダーで処理を実行します。")
    txt_files = txt_files_all # 全てのtxtファイルを使用

# キーワードリストを作成 (ファイル名から拡張子を除いたもの)
keywords = [os.path.splitext(f)[0] for f in txt_files]

# work_directoriesをキーワードの数に合わせて調整
if len(keywords) < len(work_directories):
    # キーワードの数がwork_directoriesの数より少ない場合、work_directoriesを切り詰める
    work_directories = work_directories[:len(keywords)]
    print(f"work_directoriesを {len(keywords)} 個に調整しました。")
elif len(keywords) > len(work_directories):
    # この場合は上のロジックで既にtxt_filesが調整されているはずなので、基本的には発生しない
    print(f"警告: 予期しない状況です。キーワード数({len(keywords)})がwork_directories数({len(work_directories)})より多くなっています。")
    keywords = keywords[:len(work_directories)]

processes = []
commands_to_run = [] # 起動するコマンドと引数、作業ディレクトリを保存するリスト

print("delivery_folder からキーワードを自動取得し、フォルダーに割り当てます...")

# 共通のstart.pyのパス
common_start_script = os.path.join(script_directory, "common_scripts", "start.py")

if not os.path.exists(common_start_script):
    print(f"エラー: 共通のstart.pyが見つかりません: {common_start_script}")
    exit()

for i, work_dir_name in enumerate(work_directories):
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

for command_info in commands_to_run:
    try:
        # 共通のstart.pyを各WebText_extractionフォルダーをワーキングディレクトリとして実行
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
print("各スクリプトの出力はそれぞれのコンソールウィンドウで確認してください（もしあれば）。")

# 必要に応じて、すべての子プロセスが終了するのを待つ場合は以下のコメントを解除
# for p in processes:
# p.wait()
# print("すべての子プロセスが終了しました。")
