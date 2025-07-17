import os
import re

def combine_files():
    # ファイルパスを定義
    google_file = os.path.join("outputs", "google_urls_extracted.txt")
    yahoo_file = os.path.join("outputs", "yahoo_urls_extracted.txt")
    output_file = os.path.join("Integrated_Text", "Integrated_Text.txt")
    
    # Googleファイルの内容を読み込み
    with open(google_file, 'r', encoding='utf-8') as f:
        google_content = f.read()
    
    # Yahooファイルの内容を読み込み
    with open(yahoo_file, 'r', encoding='utf-8') as f:
        yahoo_content = f.read()
    
    # タイムアウトURLの検出
    timeout_urls = []
    timeout_pattern = r'（テキスト抽出タイムアウト）'
    
    # Googleファイルからタイムアウトを検出
    for line in google_content.split('\n'):
        if timeout_pattern in line:
            # 前の行がURLの可能性があるので確認
            lines = google_content.split('\n')
            for i, current_line in enumerate(lines):
                if timeout_pattern in current_line and i > 0:
                    prev_line = lines[i-1]
                    if prev_line.startswith('http'):
                        timeout_urls.append(prev_line.strip())
    
    # Yahooファイルからタイムアウトを検出
    for line in yahoo_content.split('\n'):
        if timeout_pattern in line:
            # 前の行がURLの可能性があるので確認
            lines = yahoo_content.split('\n')
            for i, current_line in enumerate(lines):
                if timeout_pattern in current_line and i > 0:
                    prev_line = lines[i-1]
                    if prev_line.startswith('http'):
                        timeout_urls.append(prev_line.strip())
    
    # 5つの改行で内容を結合
    combined_content = google_content + '\n\n\n\n\n' + yahoo_content
    
    # タイムアウトURLがある場合は警告メッセージを先頭に追加
    if timeout_urls:
        warning_message = "テキスト抽出タイムアウトページあり（該当URL表示）\n"
        warning_message += "\n".join(timeout_urls) + "\n\n\n"
        combined_content = warning_message + combined_content
    
    # 出力ディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # BOM付きUTF-8で結合した内容を出力ファイルに書き込み
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        f.write(combined_content)
    
    if timeout_urls:
        print(f"ファイルの統合が完了しました！（タイムアウトURL: {len(timeout_urls)}件）")
    else:
        print("ファイルの統合が完了しました！")

# 関数を実行
if __name__ == "__main__":
    combine_files()