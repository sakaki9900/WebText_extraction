import os
import sys
from urllib.parse import quote_plus

def get_keywords():
    # コマンドライン引数があれば利用
    args = sys.argv[1:]
    if args:
        return args
    # 引数がなければインタラクティブ入力（空行で終了）
    print("キーワードを1行ずつ入力し、空行で終了してください:")
    keywords = []
    while True:
        try:
            line = input()
        except EOFError:
            # Ctrl+D などで終了
            break
        word = line.strip()
        # 空行で入力終了
        if word == "":
            break
        keywords.append(word)
    return keywords


def sanitize(name):
    # Windowsでファイル名に使用できない文字を置換
    for c in '<>:"/\\|?*':
        name = name.replace(c, '_')
    return name


def generate_search_urls(keyword):
    """キーワードをもとにGoogle検索とYahoo検索のURLを生成"""
    encoded_keyword = quote_plus(keyword)
    google_url = f"https://www.google.com/search?q={encoded_keyword}"
    yahoo_url = f"https://search.yahoo.co.jp/search?p={encoded_keyword}"
    return google_url, yahoo_url


def create_files(keywords, target_dir):
    os.makedirs(target_dir, exist_ok=True)
    created = []
    for kw in keywords:
        safe_name = sanitize(kw)
        filename = f"{safe_name}.txt"
        filepath = os.path.join(target_dir, filename)
        
        # Google検索とYahoo検索のURLを生成
        google_url, yahoo_url = generate_search_urls(kw)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"{google_url}\n")
            f.write(f"{yahoo_url}\n")
        
        created.append(filepath)
    return created


def main():
    target_dir = os.path.dirname(os.path.abspath(__file__))
    keywords = get_keywords()
    if not keywords:
        print("キーワードが入力されませんでした。処理を終了します。")
        sys.exit(1)

    for path in create_files(keywords, target_dir):
        print(f"Created: {path}")


def _test_sanitize():
    # 不正文字置換テスト
    original = 'a<b>c?:"/\\|?*d'
    expected = 'a_b_c___\\_\_\_d'
    result = sanitize(original)
    assert all(c not in '<>:"/\\|?*' for c in result), f"sanitize に不正文字が残っています: {result}"
    print("sanitize tests passed")

if __name__ == "__main__":
    # --test オプションでテスト実行
    if len(sys.argv) == 2 and sys.argv[1] == '--test':
        _test_sanitize()
        sys.exit(0)
    main()
