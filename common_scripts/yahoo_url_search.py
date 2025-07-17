from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os
import re
import argparse # argparse をインポート

# URLを保存するためのディレクトリを確認・作成
# base_dir = r"C:\Users\morim\Desktop\WebText_extraction\urls" # 元の絶対パス指定をコメントアウトまたは削除
base_dir = os.path.join(".", "urls") # 相対パス指定に変更
os.makedirs(base_dir, exist_ok=True)

def ensure_directories_exist():
    return base_dir

def is_excluded_url(url):
    """除外対象のURLかどうかを判定する"""
    exclude_patterns = [
        # 検索エンジン関連
        r'search\.yahoo\.co\.jp/search',  # Yahoo検索結果ページ
        # r'search\.yahoo\.co\.jp/image',   # Yahoo画像検索
        r'search\.yahoo\.co\.jp/video',   # Yahoo動画検索
        # r'search\.yahoo\.co\.jp/news',    # Yahooニュース検索
        r'support\.yahoo\.co\.jp',        # Yahooサポートページ
        r'accounts\.yahoo\.co\.jp',       # Yahooアカウントページ
        r'search\.yahoo\.co\.jp/.*\?rs=4',  # 「他の人はこちらも質問」のURL
        r'search\.yahoo\.co\.jp/.*\?sqs=1',  # 関連検索クエリパラメータ
        
        # 広告・ショッピング
        r'ads\.yahoo\.co\.jp',            # Yahoo広告
        r'shopping\.yahoo\.co\.jp',       # Yahooショッピング
        
        # ツール・サービス
        r'map\.yahoo\.co\.jp',            # Yahoo地図
        r'translate\.yahoo\.co\.jp',      # Yahoo翻訳
        r'auctions\.yahoo\.co\.jp',       # ヤフオク
        # r'detail\.chiebukuro\.yahoo\.co\.jp', # Yahoo知恵袋質問詳細 (除外しない)
        r'chiebukuro\.yahoo\.co\.jp/search', # Yahoo知恵袋検索結果ページ
        
        # 利用規約・プライバシー
        r'privacy\.yahoo\.co\.jp',        # Yahooプライバシー
        r'terms\.yahoo\.co\.jp',          # Yahoo利用規約
        
        # 一般的な除外
        r'yahoo\.co\.jp/preferences',     # Yahoo設定
        r'b\.hatena\.ne\.jp/entry',       # はてなブックマークエントリー
        r'.*\.(css|js|xml|ico)$'          # リソースファイル (末尾に追加)
    ]
    
    for pattern in exclude_patterns:
        if re.search(pattern, url):
            return True
    
    return False

def is_navigation_text(text):
    """ナビゲーションメニューやUI要素のテキストかどうかを判定する"""
    nav_patterns = [
        '設定', '検索設定', 'ログイン', '画像', '動画', '地図', 'ニュース', 
        '一覧', 'メニュー', 'トップ', '今すぐ', '使い方', '条件指定',
        'アクティビティ', '日本語のみ', 'リアルタイム', 'ウェブ', 'アカウント', 'ヘルプ',
        'プライバシー', '規約', 'メールアドレス', 'ホーム', 'ショッピング', 
        'マップ', 'カレンダー', 'ブラウザ', 'アプリ', 'アカウント', '最近の検索', 
        'メール', 'ファイナンス', 'ブックマーク', '設定する'
    ]
    
    # テキストがナビゲーションパターンのいずれかに一致するか
    for pattern in nav_patterns:
        if pattern in text:
            return True
    
    # テキストが短すぎないか（1~2文字は通常関連キーワードではない）
    if len(text) <= 2:
        return True
    
    return False

def extract_yahoo_urls(driver):
    """Yahoo検索結果からメインのURLを抽出する"""
    ordered_urls = []
    
    try:
        print("Yahoo検索結果の抽出を開始します...")
        
        # 十分に待機してページが完全に読み込まれるようにする
        time.sleep(3)
        
        # スクロールしてすべてのコンテンツをロード
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
            time.sleep(0.5)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)
        
        # JavaScriptを使用して検索結果URLを抽出
        js_ordered_urls = driver.execute_script("""
            var orderedUrls = [];
            
            // メインコンテンツエリアを特定
            var contentArea = document.querySelector('#contents__wrap');
            if (!contentArea) {
                contentArea = document.body;
            }
            
            // 検索結果カードを取得 (.sw-Card.Algo)
            var resultCards = contentArea.querySelectorAll('.sw-Card.Algo');
            
            for (var i = 0; i < resultCards.length; i++) {
                var card = resultCards[i];
                
                // 「他の人はこちらも質問」セクションをスキップ
                if (card.closest('.AnswerRelatedQuestions') || 
                    card.closest('.SouthUnitItem') || 
                    card.classList.contains('AnswerRelatedQuestions')) {
                    continue;
                }
                
                // タイトルリンクを取得 (.sw-Card__titleInner)
                var titleLink = card.querySelector('.sw-Card__titleInner');
                
                if (titleLink && titleLink.href) {
                    var url = titleLink.href;
                    // pingパラメータが含まれているリンクの処理
                    if (url.includes('/*-')) {
                        var matches = url.match(/.*?\/\*-(.*)/);
                        if (matches && matches[1]) {
                            url = decodeURIComponent(matches[1]);
                        }
                    }
                    
                    // 基本的なフィルタリング
                    if (url && 
                        url.startsWith('http') && 
                        !url.includes('search.yahoo.co.jp/search') &&
                        !url.includes('search.yahoo.co.jp/image') &&
                        !url.includes('support.yahoo.co.jp') &&
                        !url.includes('?rs=4') &&
                        !url.includes('?sqs=1') &&
                        !orderedUrls.includes(url)) {
                        
                        orderedUrls.push(url);
                    }
                }
            }
            
            return orderedUrls;
        """)
        
        if js_ordered_urls:
            print(f"JavaScriptによる抽出で {len(js_ordered_urls)} 件のURLを見つけました")
            ordered_urls = js_ordered_urls
        
        # JS抽出がうまくいかない場合のバックアップ方法
        if not ordered_urls:
            print("バックアップ手法でURLを抽出します...")
            
            # 検索結果カードを取得
            result_cards = driver.find_elements(By.CSS_SELECTOR, ".sw-Card.Algo")
            print(f"{len(result_cards)} 件の検索結果カードを発見")

            for card in result_cards:
                try:
                    # 「他の人はこちらも質問」セクションをスキップ
                    parent_answer_related = card.find_elements(By.XPATH, "./ancestor::div[contains(@class, 'AnswerRelatedQuestions')]")
                    if parent_answer_related:
                        continue
                        
                    # 「他の人はこちらも検索」セクションをスキップ
                    parent_south_unit = card.find_elements(By.XPATH, "./ancestor::div[contains(@class, 'AnswerExploreUniversal')]")
                    if parent_south_unit:
                        continue
                    
                    # タイトルリンクを取得
                    title_link = card.find_element(By.CSS_SELECTOR, ".sw-Card__titleInner")
                    url = title_link.get_attribute('href')
                    
                    # pingパラメータが含まれているリンクの処理
                    if url and "/*-" in url:
                        match = re.search(r'.*?\/\*-(.*)', url)
                        if match:
                            url = match.group(1)
                            url = url.replace("https%3A//", "https://")
                    
                    if url and url.startswith('http') and not is_excluded_url(url) and url not in ordered_urls:
                        ordered_urls.append(url)
                        print(f"  URL{len(ordered_urls)}: {url}")
                except NoSuchElementException:
                    print(f"  検索結果カードにタイトルリンクが見つかりませんでした")
                except Exception as e:
                    print(f"  検索結果カードの処理中にエラー: {e}")

        print(f"Yahoo検索から {len(ordered_urls)} 件のURLを抽出しました")
        
        # デバッグ出力
        print("\nYahoo検索から抽出したURL:")
        for i, url in enumerate(ordered_urls[:10]):
            print(f"{i+1}. {url}")
        if len(ordered_urls) > 10:
            print(f"...他 {len(ordered_urls)-10} 件")
    
    except Exception as e:
        print(f"Yahoo検索結果の抽出中に予期せぬエラーが発生しました: {e}")
    
    return ordered_urls

def extract_related_search_urls(driver):
    """Yahooの関連検索セクションからURLを抽出する"""
    related_urls = []
    
    try:
        print("Yahooの関連検索キーワードを抽出しています...")
        
        # スクロールして関連検索セクションを表示させる
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.9);")
        time.sleep(2)
        
        # 「他の人はこちらもこちらも検索」セクションのリンクを取得
        # 修正: CSSセレクタを実際のHTML構造に合わせる
        # related_links = driver.find_elements(By.CSS_SELECTOR, ".AnswerExploreUniversal__queryList .SouthUnitItem__inner")
        # related_links = driver.find_elements(By.CSS_SELECTOR, ".Unit--south .SouthUnitItem__inner") # 元のセレクタ

        # 両方の可能性のあるセレクタで検索
        related_links_south = driver.find_elements(By.CSS_SELECTOR, ".Unit--south .SouthUnitItem__inner")
        related_links_explore = driver.find_elements(By.CSS_SELECTOR, ".AnswerExploreUniversal__queryList .SouthUnitItem__inner")
        
        # 結果を結合（重複要素はfind_elementsの性質上、通常は発生しない）
        related_links = related_links_south + related_links_explore
        
        if related_links:
            print(f"{len(related_links)} 件の関連検索キーワードを発見しました")
            
            for i, link in enumerate(related_links):
                try:
                    # キーワード取得
                    link_text = link.find_element(By.CSS_SELECTOR, ".SouthUnitItem__text").text.strip()
                    print(f"関連キーワード {i+1}: {link_text}")
                    
                    # リンクURLを取得
                    search_url = link.get_attribute('href')
                    
                    if search_url and search_url.startswith('http') and "search.yahoo.co.jp" in search_url and search_url not in related_urls:
                        related_urls.append(search_url)
                        print(f"関連検索URL: {search_url}")
                except Exception as e:
                    print(f"  関連検索リンクの処理中にエラー: {e}")
        else:
            print("関連検索キーワードが見つかりませんでした。")
            
            # バックアップとして他の関連検索セクションを探す
            # 修正: 提供されたHTMLに該当箇所がないためコメントアウト
            # try:
            #     other_related_sections = driver.find_elements(By.CSS_SELECTOR, ".RelatedTerms__item")
            #     for item in other_related_sections:
            #         link = item.find_element(By.TAG_NAME, "a")
            #         search_url = link.get_attribute('href')
            #         if search_url and search_url.startswith('http') and "search.yahoo.co.jp" in search_url and search_url not in related_urls:
            #             related_urls.append(search_url)
            #             print(f"関連検索URL (その他): {search_url}")
            # except Exception as e:
            #     print(f"代替関連検索セクションの抽出中にエラー: {e}")

        print(f"Yahooから合計 {len(related_urls)} 件の関連検索URLを抽出しました")

    except Exception as e:
        print(f"Yahooの関連検索URL抽出中にエラーが発生しました: {e}")
        
    return related_urls

def extract_top_urls_from_search_url(driver, search_url, num_urls=3):
    """指定されたYahoo検索結果URLから上位のURLを抽出する"""
    urls = []
    
    try:
        print(f"検索結果URL '{search_url}' から上位URLを抽出します...")
        
        # 新しいタブを開く
        current_handles = driver.window_handles
        driver.execute_script("window.open('');")
        time.sleep(1)
        
        # 新しいタブに切り替え
        new_tab = None
        for handle in driver.window_handles:
            if handle not in current_handles:
                new_tab = handle
                break
        
        if new_tab:
            driver.switch_to.window(new_tab)
        else:
            print("新しいタブを開けませんでした。")
            return urls
        
        # 検索エンジンのURLに直接アクセス
        print(f"アクセス中: {search_url}")
        driver.get(search_url)
        
        time.sleep(3)  # ページ読み込みのための待機
        
        # CAPTCHAチェックを確認
        if "通常と異なるトラフィックが検出されました" in driver.page_source or "ロボットではありません" in driver.page_source:
            print("⚠️ CAPTCHAが検出されました。")
            print("手動でCAPTCHAを解決してください。")
            input("完了したらEnterキーを押してください...")
        
        # JavaScriptを使用して検索結果URLを抽出
        js_ordered_urls = driver.execute_script("""
            var orderedUrls = [];
            
            // メインコンテンツエリアを特定
            var contentArea = document.querySelector('#contents__wrap');
            if (!contentArea) {
                contentArea = document.body;
            }
            
            // 検索結果カードを取得 (.sw-Card.Algo)
            var resultCards = contentArea.querySelectorAll('.sw-Card.Algo');
            
            for (var i = 0; i < resultCards.length; i++) {
                var card = resultCards[i];
                
                // 「他の人はこちらも質問」セクションをスキップ
                if (card.closest('.AnswerRelatedQuestions') || 
                    card.closest('.SouthUnitItem') || 
                    card.classList.contains('AnswerRelatedQuestions')) {
                    continue;
                }
                
                // タイトルリンクを取得 (.sw-Card__titleInner)
                var titleLink = card.querySelector('.sw-Card__titleInner');
                
                if (titleLink && titleLink.href) {
                    var url = titleLink.href;
                    // pingパラメータが含まれているリンクの処理
                    if (url.includes('/*-')) {
                        var matches = url.match(/.*?\/\*-(.*)/);
                        if (matches && matches[1]) {
                            url = decodeURIComponent(matches[1]);
                        }
                    }
                    
                    // 基本的なフィルタリング
                    if (url && 
                        url.startsWith('http') && 
                        !url.includes('search.yahoo.co.jp/search') &&
                        !url.includes('search.yahoo.co.jp/image') &&
                        !url.includes('support.yahoo.co.jp') &&
                        !url.includes('?rs=4') &&
                        !url.includes('?sqs=1') &&
                        !orderedUrls.includes(url)) {
                        
                        orderedUrls.push(url);
                        if (orderedUrls.length >= 3) {
                            break; // 上位3件を取得したら終了
                        }
                    }
                }
            }
            
            return orderedUrls;
        """)
        
        if js_ordered_urls:
            print(f"JavaScriptによる抽出で {len(js_ordered_urls)} 件のURLを見つけました")
            urls = js_ordered_urls
        
        # JS抽出がうまくいかない場合のバックアップ方法
        if len(urls) < num_urls:
            print("バックアップ手法で追加のURLを抽出します...")
            
            # 検索結果カードを取得
            result_cards = driver.find_elements(By.CSS_SELECTOR, ".sw-Card.Algo")
            print(f"{len(result_cards)} 件の検索結果カードを発見")

            for card in result_cards:
                if len(urls) >= num_urls:
                    break
                    
                try:
                    # 「他の人はこちらも質問」セクションをスキップ
                    parent_answer_related = card.find_elements(By.XPATH, "./ancestor::div[contains(@class, 'AnswerRelatedQuestions')]")
                    if parent_answer_related:
                        continue
                        
                    # 「他の人はこちらも検索」セクションをスキップ
                    parent_south_unit = card.find_elements(By.XPATH, "./ancestor::div[contains(@class, 'AnswerExploreUniversal')]")
                    if parent_south_unit:
                        continue
                    
                    # タイトルリンクを取得
                    title_link = card.find_element(By.CSS_SELECTOR, ".sw-Card__titleInner")
                    url = title_link.get_attribute('href')
                    
                    # pingパラメータが含まれているリンクの処理
                    if url and "/*-" in url:
                        match = re.search(r'.*?\/\*-(.*)', url)
                        if match:
                            url = match.group(1)
                            url = url.replace("https%3A//", "https://")
                    
                    if url and url.startswith('http') and not is_excluded_url(url) and url not in urls:
                        urls.append(url)
                        print(f"  URL{len(urls)}: {url}")
                except NoSuchElementException:
                    print(f"  検索結果カードにタイトルリンクが見つかりませんでした")
                except Exception as e:
                    print(f"  検索結果カードの処理中にエラー: {e}")

        print(f"検索結果URL '{search_url}' から {len(urls)} 件の上位URLを抽出しました")
        
        # タブを閉じる
        driver.close()
        
        # 元のタブに戻る
        driver.switch_to.window(current_handles[0])
        
    except Exception as e:
        print(f"検索結果URL '{search_url}' の処理中にエラーが発生しました: {e}")
        # エラーが発生しても元のタブに戻る試み
        try:
            # 現在のタブを閉じる
            driver.close()
            # 元のタブに戻る
            driver.switch_to.window(current_handles[0])
        except:
            pass # 元のタブに戻れなくても処理は続行
    
    # 念のため最後にnum_urlsでスライス
    return urls[:num_urls]

def integrated_yahoo_search(yahoo_url):
    driver = None # driver変数を初期化
    try:
        # ディレクトリの確認
        base_dir = ensure_directories_exist()
        
        # 保存先ファイルパスの設定
        output_file_path = os.path.join(base_dir, "yahoo_urls.txt")
        
        # Chromeドライバーのセットアップ
        options = Options()
        options.add_experimental_option("detach", True)  # ブラウザを自動的に閉じないように設定
        
        # ボットらしい特徴を軽減するための設定
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # ウィンドウサイズを設定
        options.add_argument("--start-maximized")
        
        # ChromeDriverManagerを使わずに直接Chromeを起動
        driver = webdriver.Chrome(options=options)
        
        # JavaScriptを実行してWebDriverの痕跡を消す
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Yahoo検索結果ページにアクセス
        print(f"Yahoo検索結果ページにアクセス中...")
        driver.get(yahoo_url)
        time.sleep(5)  # ページ読み込みのための十分な待機時間
        
        # CAPTCHAチェックを確認
        if "通常と異なるトラフィックが検出されました" in driver.page_source or "ロボットではありません" in driver.page_source:
            print("\n⚠️ Yahoo CAPTCHAが検出されました。")
            print("手動でCAPTCHAを解決してください。")
            # input("完了したらEnterキーを押してください...") # 自動化のためコメントアウト
            # CAPTCHA対応について上記Googleスクリプトと同様の注意点
            print("CAPTCHAが表示されたため、処理を続行しますが、失敗する可能性があります。")

        # 1. 最初のYahoo検索結果からURLを抽出
        direct_urls = extract_yahoo_urls(driver)
        
        # 2. Yahooの関連検索URLを抽出
        related_search_urls = extract_related_search_urls(driver)
        
        # 3. 関連検索URLにアクセスし、それぞれから上位の記事URLを取得
        related_article_urls = []
        if related_search_urls:
            print("\n関連検索URLから上位記事URLの取得を開始します...")
            for search_url in related_search_urls:
                # 関連検索URLから上位3件の記事URLを取得
                top_urls = extract_top_urls_from_search_url(driver, search_url, num_urls=3)
                related_article_urls.extend(top_urls)
                time.sleep(1) # 連続アクセスを避けるための短い待機
            
            # 重複を削除
            related_article_urls = list(dict.fromkeys(related_article_urls))
            print(f"\n合計 {len(related_article_urls)} 件の関連検索からの上位記事URLを取得しました")
        else:
            print("\n関連検索URLが見つからなかったため、関連検索からの上位記事URLは取得されません。")
        
        # 結合して最終的なURLリストを作成 (重複排除)
        all_urls = list(dict.fromkeys(direct_urls + related_article_urls))

        # 出力: URLを保存
        print("\n--- 最終的に取得したユニークURL一覧 ---")
        if all_urls:
            # all_urls を直接使うように修正
            filtered_urls = [url for url in all_urls if not is_excluded_url(url)]
            for i, url in enumerate(filtered_urls):
                 print(f"{i+1}. {url}")
        else:
            print("取得されたURLはありませんでした。")
        print("------------------------------------")

        with open(output_file_path, 'w', encoding='utf-8') as f:
             # all_urls を直接使うように修正し、書き込み前チェックも維持
            filtered_urls_for_file = [url for url in all_urls if not is_excluded_url(url)]
            for url in filtered_urls_for_file:
                 f.write(f"{url}\n")
        
        print(f"\n合計 {len(filtered_urls_for_file)} 件のユニークなURLを {output_file_path} に保存しました") # 保存件数をfiltered_urls_for_fileの長さに合わせる
        print("処理が完了しました。") # メッセージ変更
        # print("閉じる準備ができたらEnterキーを押してください...") # 削除
        # input() # 削除
        
        # ブラウザは閉じない（ユーザーが操作できるようにするため） # 変更: 自動で閉じる
        # print("ブラウザは開いたままになっています。手動で閉じることができます。") # 削除
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        # 可能であればドライバーを閉じる試み (エラー時も)
        # try:
        #     if driver:
        #         driver.quit()
        # except:
        #     pass
        print("以下の手順を試してください:")
        print("1. Chromeブラウザが最新バージョンであることを確認")
        print("2. 必要なライブラリが正しくインストールされていることを確認:")
        print("   pip install selenium")
    finally:
        # 正常終了時もエラー発生時も必ずブラウザを閉じる
        if driver:
            print("ブラウザを閉じています...")
            driver.quit()

if __name__ == "__main__":
    # コマンドライン引数のパーサーを作成
    parser = argparse.ArgumentParser(description='Yahoo検索結果ページからURLを抽出します。')
    parser.add_argument('yahoo_url', type=str, help='Yahoo検索結果ページのURL')

    # 引数を解析
    args = parser.parse_args()
    
    # print("Yahoo検索結果ページのURLを指定してください") # 削除
    # yahoo_url = input("Yahoo検索結果ページのURL: ") # 削除
    yahoo_url = args.yahoo_url # 引数からURLを取得
    
    if not yahoo_url:
        print("URLを指定してください")
    else:
        integrated_yahoo_search(yahoo_url)