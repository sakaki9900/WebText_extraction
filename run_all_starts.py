import subprocess
import os
import time

# 起動するstart.pyのパスのリスト
# WebText_extraction_folder からの相対パスで指定
start_scripts = [
    os.path.join("WebText_extraction", "start.py"),
    os.path.join("WebText_extraction2", "start.py"),
    os.path.join("WebText_extraction3", "start.py"),
    os.path.join("WebText_extraction4", "start.py"),
    os.path.join("WebText_extraction5", "start.py"),
    os.path.join("WebText_extraction6", "start.py"),
    os.path.join("WebText_extraction7", "start.py"),
    os.path.join("WebText_extraction8", "start.py"),
    os.path.join("WebText_extraction9", "start.py"),
    os.path.join("WebText_extraction10", "start.py"),
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
elif len(txt_files_all) > len(start_scripts):
    print(f"情報: delivery_folder 内に {len(txt_files_all)} 個のテキストファイルが見つかりました。")
    print(f"最初の {len(start_scripts)} 個のファイルのみをキーワードとして使用します。")
    txt_files = txt_files_all[:len(start_scripts)] # start_scriptsの数だけ取得
else:
    # txtファイルがstart_scriptsの数以下の場合
    print(f"情報: delivery_folder 内に {len(txt_files_all)} 個のテキストファイルが見つかりました。")
    print(f"利用可能な {len(txt_files_all)} 個のstart.pyを実行します。")
    txt_files = txt_files_all # 全てのtxtファイルを使用

# キーワードリストを作成 (ファイル名から拡張子を除いたもの)
keywords = [os.path.splitext(f)[0] for f in txt_files]

# start_scriptsをキーワードの数に合わせて調整
if len(keywords) < len(start_scripts):
    # キーワードの数がstart_scriptsの数より少ない場合、start_scriptsを切り詰める
    start_scripts = start_scripts[:len(keywords)]
    print(f"start_scriptsを {len(keywords)} 個に調整しました。")
elif len(keywords) > len(start_scripts):
    # この場合は上のロジックで既にtxt_filesが調整されているはずなので、基本的には発生しない
    print(f"警告: 予期しない状況です。キーワード数({len(keywords)})がstart_scripts数({len(start_scripts)})より多くなっています。")
    keywords = keywords[:len(start_scripts)]

processes = []
commands_to_run = [] # 起動するコマンドと引数、作業ディレクトリを保存するリスト

print("delivery_folder からキーワードを自動取得し、スクリプトに割り当てます...")

for i, script_path_str in enumerate(start_scripts):
    # start_scriptsのパスが絶対パスでない場合、スクリプトのディレクトリからの相対パスとして解決
    absolute_script_path = os.path.join(script_directory, script_path_str)

    if not os.path.exists(absolute_script_path):
        print(f"エラー: {absolute_script_path} が見つかりません。スキップします。")
        continue

    # WebText_extractionX フォルダをCWDとするため、その親フォルダからの相対パスを再構築
    script_dir_name = os.path.dirname(script_path_str) # "WebText_extractionX"
    script_dir_abs_path = os.path.join(script_directory, script_dir_name) # 絶対パス
    script_filename = os.path.basename(script_path_str) # "start.py"

    keyword = keywords[i]
    commands_to_run.append({'dir': script_dir_abs_path, 'script': script_filename, 'keyword': keyword, 'full_path': absolute_script_path})
    print(f"'{script_dir_name}' の '{script_filename}' にキーワード '{keyword}' を割り当てました。")

print("\nキーワードの割り当てが完了しました。スクリプトを起動します...")

for command_info in commands_to_run:
    try:
        # Pythonインタープリタでスクリプトを実行し、キーワードを引数として渡す
        # (Windowsの場合、python がpython.exeを指すことを想定)
        process = subprocess.Popen(
            ['python', command_info['script'], command_info['keyword']],
            cwd=command_info['dir'],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        processes.append(process)
        print(f"{command_info['full_path']} をキーワード '{command_info['keyword']}' で起動しました。")
        time.sleep(5)  # 5秒待機
    except FileNotFoundError:
        print(f"エラー: Pythonインタープリタが見つからないか、{command_info['full_path']} (作業ディレクトリ: {command_info['dir']}) の実行に失敗しました。")
    except Exception as e:
        print(f"エラー: {command_info['full_path']} の起動中に問題が発生しました: {e}")


print("\nすべてのスクリプトの起動を試みました。")
print("各スクリプトの出力はそれぞれのコンソールウィンドウで確認してください（もしあれば）。")

# 必要に応じて、すべての子プロセスが終了するのを待つ場合は以下のコメントを解除
# for p in processes:
# p.wait()
# print("すべての子プロセスが終了しました。")
