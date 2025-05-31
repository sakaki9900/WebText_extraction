import os

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
    
    # 5つの改行で内容を結合
    combined_content = google_content + '\n\n\n\n\n' + yahoo_content
    
    # 出力ディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # 結合した内容を出力ファイルに書き込み
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(combined_content)
    
    print("ファイルの統合が完了しました！")

# 関数を実行
if __name__ == "__main__":
    combine_files()