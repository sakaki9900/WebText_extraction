import os
import configparser
import subprocess
import sys
import glob

# Check if psutil is installed, if not use fallback mode
try:
    # Try to import psutil directly if already installed
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    print("psutilライブラリがインストールされていません。CPU制限機能を無効化して続行します...")
    PSUTIL_AVAILABLE = False

def find_urls_in_file(filepath):
    """指定されたファイルからGoogleとYahooの検索結果URLを抽出する"""
    google_url = None
    yahoo_url = None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                if not line: # 空行はスキップ
                    continue
                # Google URLの判定
                if not google_url and ("google.com/search" in line or "google.co.jp/search" in line) and line.startswith(("http://", "https://")):
                    google_url = line
                # Yahoo URLの判定
                elif not yahoo_url and ("search.yahoo.co.jp/search" in line or "search.yahoo.com/search" in line) and line.startswith(("http://", "https://")):
                    yahoo_url = line
                
                if google_url and yahoo_url: # 両方見つかったら終了
                    break
        return google_url, yahoo_url
    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません: {filepath}", file=sys.stderr)
        return None, None
    except Exception as e:
        print(f"エラー: ファイル '{filepath}' の読み込み中にエラーが発生しました: {e}", file=sys.stderr)
        return None, None

def get_urls_from_keyword_in_delivery_folder():
    """ユーザーから検索キーワードを取得し、delivery_folderから対応するファイルのURLを取得する"""
    received_keyword = None
    if len(sys.argv) > 1:
        received_keyword = sys.argv[1]
        print(f"コマンドライン引数からキーワード '{received_keyword}' を受け取りました。")

    if received_keyword:
        keyword = received_keyword.strip()
    else:
        keyword = input("検索キーワードを入力してください: ").strip()
    
    if not keyword:
        print("エラー: キーワードが入力されていません。", file=sys.stderr)
        sys.exit(1)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    # start.pyから見て1つ上の階層のdelivery_folderを指定
    delivery_folder = os.path.join(script_dir, "..", "delivery_folder")

    if not os.path.isdir(delivery_folder):
        print(f"エラー: '{delivery_folder}' フォルダが見つかりません。スクリプトと同じ階層に作成してください。", file=sys.stderr)
        sys.exit(1)

    found_file_path = None

    for filename in os.listdir(delivery_folder):
        name_without_ext, ext = os.path.splitext(filename)
        if keyword == name_without_ext and ext.lower() == ".txt":
            found_file_path = os.path.join(delivery_folder, filename)
            break
    
    if not found_file_path:
        print(f"エラー: キーワード '{keyword}' に一致するテキストファイルが '{delivery_folder}' フォルダ内に見つかりません。", file=sys.stderr)
        print(f"（例: キーワードが 'example' の場合、'{os.path.join(delivery_folder, 'example.txt')}' というファイルを探します）", file=sys.stderr)
        sys.exit(1)

    print(f"ファイル '{found_file_path}' からURLを読み込みます...")
    google_url, yahoo_url = find_urls_in_file(found_file_path)

    if not google_url or not yahoo_url:
        print(f"エラー: ファイル '{found_file_path}' 内からGoogle検索結果URLまたはYahoo検索結果URL、あるいはその両方が見つかりませんでした。", file=sys.stderr)
        print("ファイル内容を確認し、URLが正しく記載されているか確認してください。各URLは独立した行にある必要があります。", file=sys.stderr)
        print("期待されるURLの形式例:", file=sys.stderr)
        print("  https://www.google.com/search?q=your_query", file=sys.stderr)
        print("  https://search.yahoo.co.jp/search?p=your_query", file=sys.stderr)
        sys.exit(1)
    
    print(f"Google URL: {google_url}")
    print(f"Yahoo URL: {yahoo_url}")
    return google_url, yahoo_url, keyword

def create_config_ini(cpu_ratio, google_url, yahoo_url):
    """config.iniファイルを作成または更新する"""
    # interpolation=None を指定して % の補間を無効にする
    config = configparser.ConfigParser(interpolation=None)
    config_path = 'config.ini'

    # 既存の設定を読み込む（存在する場合）
    if os.path.exists(config_path):
        try:
            config.read(config_path, encoding='utf-8')
        except configparser.Error as e:
            print(f"警告: 既存の {config_path} の読み込みに失敗しました: {e}")
            config = configparser.ConfigParser(interpolation=None) # エラーの場合は新しい設定を作成

    # Settingsセクションがなければ追加
    if 'Settings' not in config:
        config['Settings'] = {}
    # URLsセクションがなければ追加
    if 'URLs' not in config:
        config['URLs'] = {}

    # cpu_ratioを設定
    config['Settings']['cpu_ratio'] = str(cpu_ratio)
    # URLを設定
    config['URLs']['google_search_url'] = google_url
    config['URLs']['yahoo_search_url'] = yahoo_url

    # ファイルに書き込む
    try:
        with open(config_path, 'w', encoding='utf-8') as configfile:
            config.write(configfile)
        print(f"{config_path} にCPU使用率とURLを保存しました。")
    except IOError as e:
        print(f"エラー: {config_path} の書き込みに失敗しました: {e}")
        sys.exit(1) # エラーで終了

def run_script(script_name, *args):
    """指定されたPythonスクリプトを引数付きで実行する汎用関数"""
    # 共通スクリプトのパスを取得
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, script_name)
    
    if not os.path.exists(script_path):
        print(f"エラー: 実行するスクリプト {script_path} が見つかりません。", file=sys.stderr)
        return False # 失敗を示すためにFalseを返す

    command = [sys.executable, script_path] + list(args)
    print(f"\n--- {script_name} を実行します ---")
    print(f"コマンド: {' '.join(command)}") # 実行コマンドを表示

    try:
        # stderr/stdout をパイプしないように変更 (stdout=None, stderr=None と同等)
        # text=True はそのままにし、check=True も通常は有用
        # 現在のワーキングディレクトリ（各WebText_extractionフォルダ）で実行
        current_cwd = os.getcwd()
        process = subprocess.run(command, check=True, text=True, encoding='utf-8', errors='replace', cwd=current_cwd)
        # 出力は直接表示されるため、ここでの print は不要になる
        print(f"\n--- {script_name} の実行が完了しました ---")
        return True
    except FileNotFoundError:
         print(f"エラー: Pythonインタープリタ '{sys.executable}' が見つかりません。", file=sys.stderr)
         return False
    except subprocess.CalledProcessError as e:
        print(f"エラー: {script_name} の実行中にエラーが発生しました (終了コード: {e.returncode})。", file=sys.stderr)
        if e.stdout:
            print("--- 標準出力 (エラー時) ---", file=sys.stderr)
            print(e.stdout, file=sys.stderr)
        if e.stderr:
            print("--- 標準エラー出力 (エラー時) ---", file=sys.stderr)
            print(e.stderr, file=sys.stderr)
        return False
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}", file=sys.stderr)
        return False

def run_google_search_script(config):
    """config.iniからURLを読み込み、google_url_serch.pyを実行する"""
    try:
        google_url = config.get('URLs', 'google_search_url')
    except (configparser.NoSectionError, configparser.NoOptionError):
        print("エラー: config.ini に [URLs] セクションまたは google_search_url が見つかりません。", file=sys.stderr)
        return False
    return run_script('google_url_serch.py', google_url)

def run_yahoo_search_script(config):
    """config.iniからURLを読み込み、yahoo_url_search.pyを実行する"""
    try:
        yahoo_url = config.get('URLs', 'yahoo_search_url')
    except (configparser.NoSectionError, configparser.NoOptionError):
        print("エラー: config.ini に [URLs] セクションまたは yahoo_search_url が見つかりません。", file=sys.stderr)
        return False
    return run_script('yahoo_url_search.py', yahoo_url)

def run_extractor_script():
    """web_text_extractor_ver1.5.pyを実行する"""
    return run_script('web_text_extractor_ver1.5.py')

def run_integrated_script():
    """integrated.pyを実行する"""
    return run_script('integrated.py')

def run_update_delivery_script(keyword):
    """update_delivery_file.py をキーワード引数付きで実行する"""
    if not keyword:
        print("エラー: update_delivery_file.py の実行に必要なキーワードがありません。", file=sys.stderr)
        return False
    return run_script('update_delivery_file.py', keyword)

def cleanup_previous_files():
    """前回の処理で残った出力ファイルをクリーンアップする"""
    cleanup_folders = ['outputs', 'urls', 'Integrated_Text']
    total_deleted = 0
    
    print("前回の処理ファイルのクリーンアップを開始します...")
    
    for folder in cleanup_folders:
        if not os.path.exists(folder):
            print(f"  フォルダー '{folder}' が存在しないため、スキップします。")
            continue
            
        # フォルダー内の.txtファイルを検索
        txt_files = glob.glob(os.path.join(folder, "*.txt"))
        
        if not txt_files:
            print(f"  フォルダー '{folder}' 内に.txtファイルが見つかりません。")
            continue
            
        # ファイルを削除
        deleted_count = 0
        for file_path in txt_files:
            try:
                os.remove(file_path)
                print(f"    削除: {file_path}")
                deleted_count += 1
            except OSError as e:
                print(f"    警告: ファイル '{file_path}' の削除に失敗しました: {e}", file=sys.stderr)
        
        total_deleted += deleted_count
        print(f"  フォルダー '{folder}' から {deleted_count} 個のファイルを削除しました。")
    
    print(f"クリーンアップ完了: 合計 {total_deleted} 個のファイルを削除しました。")
    return True

def run_script_with_cpu_limit(script_name, cpu_percent_ratio):
    """
    Run a Python script with limited CPU usage.
    
    Args:
        script_name: Name of the Python script to run (in common_scripts)
        cpu_percent_ratio: Percentage of CPU cores to use (0.0 to 1.0)
    """
    # 共通スクリプトのパスを取得
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, script_name)
    
    # Check if script exists
    if not os.path.isfile(script_path):
        print(f"エラー: スクリプト '{script_path}' が見つかりません。", file=sys.stderr)
        return False
    
    # If psutil is not available, use regular run_script
    if not PSUTIL_AVAILABLE:
        print(f"psutilが利用できないため、CPU制限なしで {script_name} を実行します。")
        return run_script(script_name)
    
    # Calculate number of CPUs to use
    num_cpus_total = psutil.cpu_count(logical=True)
    if num_cpus_total is None:
        print("警告: 利用可能なCPU数を取得できませんでした。CPU制限なしでスクリプトを実行します。", file=sys.stderr)
        return run_script(script_path)


    cpus_to_use_calculated = max(1, int(num_cpus_total * cpu_percent_ratio))
    
    # Create CPU affinity list (which CPUs to use)
    cpu_list = list(range(min(cpus_to_use_calculated, num_cpus_total)))

    if not cpu_list: # Should not happen if num_cpus_total is valid and > 0
        print("警告: CPUリストが空のため、CPU制限なしで実行します。", file=sys.stderr)
        return run_script(script_name)
    
    print(f"実行中: {script_name} を {len(cpu_list)}/{num_cpus_total} CPU(s) を使用して実行 (指定CPU割合: {cpu_percent_ratio*100:.0f}%)")
    
    process = None
    try:
        # Start the process
        # 現在のワーキングディレクトリ（各WebText_extractionフォルダ）で実行
        current_cwd = os.getcwd()
        process = subprocess.Popen([sys.executable, script_path], cwd=current_cwd)
        
        # Get process handle and set affinity
        try:
            p = psutil.Process(process.pid)
            p.cpu_affinity(cpu_list)
        except psutil.NoSuchProcess:
            # This can happen if the process finishes very quickly
            print(f"警告: プロセス {process.pid} はCPUアフィニティ設定前に終了したか、存在しませんでした。CPU制限は適用されなかった可能性があります。", file=sys.stderr)
        except psutil.AccessDenied:
            print(f"警告: プロセス {process.pid} のCPUアフィニティ設定が拒否されました。権限を確認してください。CPU制限は適用されません。", file=sys.stderr)
        except Exception as e_psutil: # Catch other psutil-related errors
            print(f"警告: プロセス {process.pid} のCPUアフィニティ設定中にエラー: {e_psutil}。CPU制限は適用されない可能性があります。", file=sys.stderr)


        # Wait for process to complete
        process.wait()
        
        if process.returncode == 0:
            print(f"{script_name} の実行に成功しました。")
            return True
        else:
            print(f"{script_name} の実行中にエラーが発生しました。リターンコード: {process.returncode}", file=sys.stderr)
            return False
    except Exception as e_popen: # Catch Popen errors or other issues
        pid_info = process.pid if process else "(不明)"
        print(f"プロセス {pid_info} の実行または待機中に予期せぬエラーが発生しました: {e_popen}", file=sys.stderr)
        return False

def main():
    # 1. CPU使用率を1.0に固定
    cpu_ratio = 1.0
    print(f"CPU使用率を {cpu_ratio*100:.0f}% に設定します。")
    
    # 2. キーワードからURLを取得
    google_url, yahoo_url, keyword = get_urls_from_keyword_in_delivery_folder()

    # 2.5. 前回の処理ファイルをクリーンアップ
    cleanup_previous_files()

    # 3. config.ini を作成/更新
    create_config_ini(cpu_ratio, google_url, yahoo_url)

    # --- スクリプト実行フロー --- 
    # interpolation=None を指定して % の補間を無効にする
    config = configparser.ConfigParser(interpolation=None)
    try:
        config.read('config.ini', encoding='utf-8')
    except configparser.Error as e:
        print(f"エラー: config.ini の読み込みに失敗しました: {e}", file=sys.stderr)
        sys.exit(1)
    
    # web_text_extractor_ver1.5.py をCPU制限付きで実行するための準備
    try:
        cpu_limit_ratio_for_extractor = config.getfloat('Settings', 'cpu_ratio')
    except (configparser.NoSectionError, configparser.NoOptionError, ValueError) as e:
        print(f"警告: config.iniからcpu_ratioの読み込みに失敗 ({e})。mainで設定された値 ({cpu_ratio}) を使用します。", file=sys.stderr)
        cpu_limit_ratio_for_extractor = cpu_ratio # Fallback to the hardcoded cpu_ratio


    # スクリプト実行のシーケンス
    print("="*50)
    if not run_google_search_script(config):
        print(f"エラー: Google検索スクリプトの実行に失敗しました。処理を中断します。", file=sys.stderr)
        sys.exit(1)
    print("="*50 + "\n")

    print("="*50)
    if not run_yahoo_search_script(config):
        print(f"エラー: Yahoo検索スクリプトの実行に失敗しました。処理を中断します。", file=sys.stderr)
        sys.exit(1)
    print("="*50 + "\n")

    print("="*50)
    extractor_script_name = 'web_text_extractor_ver1.5.py'
    print(f"\n--- {extractor_script_name} をCPU制限付きで実行します ---")
    if not run_script_with_cpu_limit(extractor_script_name, cpu_limit_ratio_for_extractor):
        print(f"エラー: {extractor_script_name} の実行に失敗しました。処理を中断します。", file=sys.stderr)
        sys.exit(1)
    # Completion message is in run_script_with_cpu_limit
    print("="*50 + "\n")

    print("="*50)
    if not run_integrated_script(): # integrated.py takes no arguments
        print(f"エラー: 統合スクリプトの実行に失敗しました。処理を中断します。", file=sys.stderr)
        sys.exit(1)
    print("="*50 + "\n")

    print("="*50)
    print(f"\n--- update_delivery_file.py を実行します ---")
    if not run_update_delivery_script(keyword):
        print(f"エラー: update_delivery_file.py の実行に失敗しました。", file=sys.stderr)
    else:
        print(f"--- update_delivery_file.py の実行が完了しました ---")
    print("="*50 + "\n")

    print("\n全ての処理が正常に完了しました。")
    # input("何かキーを押すと終了します...") # 自動終了

if __name__ == "__main__":
    main()