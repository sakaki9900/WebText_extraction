import os
import sys
import shutil

def get_keyword_and_filepath():
    """ユーザーから検索キーワードを取得し、対応するファイルのパスを構築する"""
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
    # update_delivery_file.py から見て1つ上の階層の delivery_folder を指定
    delivery_folder = os.path.join(script_dir, "..", "delivery_folder")
    
    # このスクリプト (update_delivery_file.py) が WebText_extraction フォルダ直下にあると仮定
    # Integrated_Text.txt へのパス
    integrated_text_path = os.path.join(script_dir, "Integrated_Text", "Integrated_Text.txt")


    if not os.path.isdir(delivery_folder):
        print(f"エラー: '{delivery_folder}' フォルダが見つかりません。適切な場所に作成してください。", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.isfile(integrated_text_path):
        print(f"エラー: '{integrated_text_path}' ファイルが見つかりません。", file=sys.stderr)
        sys.exit(1)

    target_filename = f"{keyword}.txt"
    target_filepath = os.path.join(delivery_folder, target_filename)

    # delivery_folder 内にキーワード名のファイルが存在するかチェック
    if not os.path.exists(target_filepath):
        print(f"エラー: キーワード '{keyword}' に一致するテキストファイルが '{delivery_folder}' フォルダ内に見つかりません。", file=sys.stderr)
        print(f"（例: キーワードが 'example' の場合、'{target_filepath}' というファイルを探します）", file=sys.stderr)
        sys.exit(1)
        
    return target_filepath, integrated_text_path, delivery_folder

def main():
    target_filepath, integrated_text_path, delivery_folder = get_keyword_and_filepath()
    print(f"対象ファイル: {target_filepath}")
    print(f"統合テキストファイル: {integrated_text_path}")

    try:
        # 1. 同じファイル名のテキストを全消去 (ファイルを開いてすぐに閉じることで空にする)
        print(f"'{target_filepath}' の内容をクリアしています...")
        with open(target_filepath, 'w', encoding='utf-8') as f_target:
            pass # ファイルを 'w' モードで開くだけで内容はクリアされる
        print(f"'{target_filepath}' の内容をクリアしました。")

        # 2. Integrated_Text.txt にあるテキストを読み込む
        print(f"'{integrated_text_path}' からテキストを読み込んでいます...")
        with open(integrated_text_path, 'r', encoding='utf-8') as f_source:
            content_to_copy = f_source.read()
        print(f"'{integrated_text_path}' からテキストを読み込みました。")

        # 3. 読み込んだテキストをキーワードと同じファイル名のテキストファイルに書き込む
        print(f"'{target_filepath}' にテキストを書き込んでいます...")
        with open(target_filepath, 'w', encoding='utf-8') as f_target:
            f_target.write(content_to_copy)
        print(f"'{target_filepath}' にテキストを書き込みました。")
        
        # 4. 処理済みファイルを completed_folder に移動
        completed_folder_path = os.path.join(delivery_folder, "completed_folder")
        if not os.path.exists(completed_folder_path):
            os.makedirs(completed_folder_path)
            print(f"'{completed_folder_path}' を作成しました。")

        destination_filepath = os.path.join(completed_folder_path, os.path.basename(target_filepath))
        
        # 移動先に同名ファイルが存在する場合の処理（上書きなど）をここに追加することも可能
        # 今回はshutil.moveが上書きするので、特に処理は追加しない
        shutil.move(target_filepath, destination_filepath)
        print(f"'{target_filepath}' を '{destination_filepath}' に移動しました。")
        
        print(f"\n処理が正常に完了しました。'{os.path.basename(target_filepath)}' は '{integrated_text_path}' の内容で更新され、'{completed_folder_path}' に移動されました。")

    except FileNotFoundError as e:
        print(f"エラー: ファイルが見つかりません: {e}", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"エラー: ファイルの読み書き中にエラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 