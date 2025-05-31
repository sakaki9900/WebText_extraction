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
def ensure_directories_exist():
    # base_dir = r"C:\Users\morim\Desktop\WebText_extraction\urls" # 元の絶対パス指定をコメントアウトまたは削除
    base_dir = os.path.join(".", "urls") # 相対パス指定に変更
    os.makedirs(base_dir, exist_ok=True)
    return base_dir

def is_excluded_url(url):
    """除外対象のURLかどうかを判定する"""
    exclude_patterns = [
        # 検索エンジン関連
        r'google\.com/search',  # Google検索結果ページ
        r'support\.google\.com',  # Googleサポートページ
        r'accounts\.google\.com',  # Googleアカウントページ
        
        # 広告・ショッピング
        r'ads\.google\.com',  # Google広告
        
        # ツール・サービス
        r'translate\.google\.com',  # Google翻訳
        r'maps\.google\.com',  # Googleマップ
        r'google\.com/maps',  # Googleマップ
        r'google\.com/travel',  # Google Travel
        r'google\.co\.jp/intl',  # Google製品ページ
        r'google\.com/advanced_search',  # Google詳細検索
        
        # 利用規約・プライバシー
        r'policies\.google\.com',  # Googleポリシー
        r'privacy',  # プライバシーポリシー
        r'terms',  # 利用規約
        
        # 一般的な除外
        r'google\.com/preferences',  # Google設定
        r'google\.com/webhp',  # Google Web History
        r'chrome\.google\.com',  # Chrome
        r'.*\.(css|js|xml|ico)$',  # リソースファイル
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

def extract_google_urls(driver):
    """Google検索結果からh3タグに関連するURLのみを抽出する"""
    ordered_urls = []
    
    try:
        print("Google検索結果の抽出を開始します...")
        
        # 十分に待機してページが完全に読み込まれるようにする
        time.sleep(3)
        
        # スクロールしてすべてのコンテンツをロード
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
            time.sleep(0.5)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)
        
        # h3タグに関連するURLのみを取得するJavaScript
        js_ordered_urls = driver.execute_script("""
            var orderedUrls = [];
            
            // メインコンテンツエリアを特定
            var mainContentAreas = [
                document.getElementById('search'),
                document.getElementById('center_col'),
                document.getElementById('rso'),
                document.getElementById('main'),
                document.querySelector('.v7W49e') // 検索結果コンテナの可能性
            ].filter(el => el !== null);
            
            if (mainContentAreas.length === 0) {
                mainContentAreas = [document.body]; 
            }
            
            // h3タグを探して、その親または祖先にあるaタグを取得
            for (var a = 0; a < mainContentAreas.length; a++) {
                var mainArea = mainContentAreas[a];
                var h3Elements = mainArea.querySelectorAll('h3');
                
                for (var i = 0; i < h3Elements.length; i++) {
                    var h3 = h3Elements[i];
                    
                    // --- 関連する質問セクションかどうかのチェックを追加 ---
                    if (h3.closest('.related-question-pair')) {
                        // console.log('Skipping h3 inside related question:', h3.textContent.substring(0, 30));
                        continue; // 関連する質問内のh3はスキップ
                    }
                    // --- ここまで ---

                    // このh3がフッターやナビゲーションの一部でないことを確認
                    var isFooterOrNav = false;
                    var parent = h3;
                    while (parent && parent !== document.body) {
                        if (parent.id && (
                            parent.id.includes('footer') || 
                            parent.id === 'botstuff' || 
                            parent.id === 'appbar' || 
                            parent.id === 'hdtb'
                        )) {
                            isFooterOrNav = true;
                            break;
                        }
                        if (parent.className && typeof parent.className === 'string' && ( // typeof check for safety
                            parent.className.includes('footer') || 
                            parent.className.includes('navcnt') || 
                            parent.className.includes('NKcBbd') // 追加: ヘッダーナビゲーションクラス
                        )) {
                            isFooterOrNav = true;
                            break;
                        }
                        parent = parent.parentElement;
                    }
                    
                    if (isFooterOrNav) {
                        // console.log('Skipping footer/nav h3:', h3.textContent.substring(0, 30));
                        continue; // このh3はスキップ
                    }
                    
                    // h3の親要素にaタグがあるか探す
                    var foundLink = null;
                    
                    // 1. h3自身または直接の親がaタグかチェック
                    if (h3.tagName === 'A') {
                        foundLink = h3;
                    } else {
                        var directParent = h3.parentElement;
                        if (directParent && directParent.tagName === 'A') {
                            foundLink = directParent;
                        }
                    }
                    
                    // 2. 祖先要素にaタグがあるか探す (より一般的な検索結果コンテナを優先)
                    if (!foundLink) {
                        var commonContainer = h3.closest('div.g, div.kvH3mc, div.srKDX'); // 一般的なコンテナクラス
                        if (commonContainer) {
                            // コンテナ内の最初のリンクを取得 (h3テキストと関連性が高いと仮定)
                             var linkInContainer = commonContainer.querySelector('a');
                             if (linkInContainer) {
                                 foundLink = linkInContainer;
                             }
                        }
                    }

                    // 3. それでも見つからない場合、さらに祖先をたどる
                    if (!foundLink) {
                        var current = h3;
                        while (current && current !== document.body) {
                            if (current.tagName === 'A') {
                                foundLink = current;
                                break;
                            }
                            current = current.parentElement;
                        }
                    }
                    
                    // リンクが見つかった場合、URLを保存
                    if (foundLink) {
                        // --- リンクが関連する質問セクション内にないか再確認 ---
                        if (foundLink.closest('.related-question-pair')) {
                             // console.log('Skipping link inside related question:', foundLink.href);
                            continue; 
                        }
                        // --- ここまで ---
                        
                        var url = foundLink.href;
                        
                        // URL検証 (is_excluded_url相当の基本的なチェックもJS側に入れる)
                        if (url && url.startsWith('http') && // http/httpsで始まるもののみ
                            !url.includes('google.com/search') &&
                            !url.includes('google.com/travel') &&
                            !url.includes('google.com/maps') &&
                            !url.includes('google.co.jp/intl') &&
                            !url.includes('support.google.com') &&
                            !url.includes('policies.google.com') &&
                            !url.includes('accounts.google.com') &&
                            !url.includes('google.com/preferences') &&
                            !url.includes('google.com/advanced_search') &&
                            !orderedUrls.includes(url)) {
                            
                            orderedUrls.push(url);
                        } else {
                            // console.log('Skipping excluded/duplicate URL:', url);
                        }
                    } else {
                         // console.log('No link found for h3:', h3.textContent.substring(0, 30));
                    }
                }
            }
            
            return orderedUrls;
        """)
        
        if js_ordered_urls:
            print(f"JavaScriptによる抽出で {len(js_ordered_urls)} 件のh3関連URLを見つけました")
            ordered_urls = js_ordered_urls
        
        # JS抽出がうまくいかない場合のバックアップ方法 (より堅牢に)
        if not ordered_urls:
            print("バックアップ手法でURLを抽出します...")
            
            # h3タグを持つ要素を探す (関連する質問セクション以外)
            # 注意: SeleniumのXPathで 'not(ancestor::...)' を使うのは効率が悪い場合がある
            #       ので、取得後にチェックする方が安全
            all_h3_elements = driver.find_elements(By.TAG_NAME, "h3")
            print(f"{len(all_h3_elements)} 件のh3タグを発見")

            processed_links = set() # 処理済みのリンクを追跡

            for h3 in all_h3_elements:
                try:
                    # --- 関連する質問セクション内のh3かチェック ---
                    try:
                        # h3自身が関連する質問内にあるか
                        h3.find_element(By.XPATH, "./ancestor::div[contains(@class, 'related-question-pair')]")
                        # print(f"  Skipping h3 in related question: {h3.text[:30]}...")
                        continue # 見つかったらこのh3はスキップ
                    except NoSuchElementException:
                        pass # 関連質問内でなければOK
                    
                    # h3に関連する最も近いリンクを探す (いくつかの戦略)
                    found_link_element = None
                    url = None

                    # 戦略1: h3の祖先にあるリンク (最も一般的)
                    try:
                        # 主要なコンテナを探し、その中の最初のリンクを取得
                        container = h3.find_element(By.XPATH, "./ancestor::div[contains(@class, 'g') or contains(@class, 'kvH3mc') or contains(@class, 'srKDX') or @data-hveid][1]")
                        link_element = container.find_element(By.TAG_NAME, "a")
                        url = link_element.get_attribute('href')
                        # --- リンクが関連する質問内にないか再確認 ---
                        try:
                            link_element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'related-question-pair')]")
                            url = None # 関連質問内なら無効化
                        except NoSuchElementException:
                            pass
                    except NoSuchElementException:
                        pass # コンテナが見つからない場合
                    except Exception as e_cont:
                         print(f"  Container search error: {e_cont}")


                    # 戦略2: h3の直接の親または祖先がリンクの場合
                    if not url:
                        try:
                            link_element = h3.find_element(By.XPATH, "./ancestor-or-self::a")
                            url = link_element.get_attribute('href')
                            # --- リンクが関連する質問内にないか再確認 ---
                            try:
                                link_element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'related-question-pair')]")
                                url = None # 関連質問内なら無効化
                            except NoSuchElementException:
                                pass
                        except NoSuchElementException:
                            pass

                    # URLが見つかり、有効で、未追加の場合
                    if url and url.startswith('http') and not is_excluded_url(url) and url not in ordered_urls and url not in processed_links:
                        ordered_urls.append(url)
                        processed_links.add(url) # 重複追加を防ぐ
                        print(f"  URL{len(ordered_urls)}: {url}")

                except NoSuchElementException:
                     print(f"  h3タグ '{h3.text[:30]}...' に関連する適切なリンクが見つかりませんでした")
                except Exception as e:
                    print(f"  h3タグ '{h3.text[:30]}...' の処理中にエラー: {e}")

        print(f"Google検索から {len(ordered_urls)} 件のh3関連URLを抽出しました")
        
        # デバッグ出力
        print("\nGoogle検索から抽出したURL (h3関連):")
        for i, url in enumerate(ordered_urls[:10]):
            print(f"{i+1}. {url}")
        if len(ordered_urls) > 10:
            print(f"...他 {len(ordered_urls)-10} 件")
    
    except Exception as e:
        print(f"Google検索結果の抽出中に予期せぬエラーが発生しました: {e}")
    
    return ordered_urls

def extract_related_search_urls(driver):
    """Googleの関連検索セクションからURLを抽出する (class="ngTNl ggLgoc")"""
    related_urls = []
    
    try:
        print("Googleの関連検索URLを抽出しています...")
        
        # スクロールして関連検索セクションを表示させる可能性がある
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.9);")
        time.sleep(2)
        
        # 指定されたクラスを持つaタグを探す
        # class="ngTNl ggLgoc" を持つ a タグは、通常「他の人はこちらも検索」や「関連性の高い検索」などのリンク
        related_links = driver.find_elements(By.CSS_SELECTOR, "a.ngTNl.ggLgoc")
        
        if related_links:
            print(f"{len(related_links)} 件の関連検索リンクを発見しました")
            for i, link in enumerate(related_links):
                url = link.get_attribute('href')
                link_text = link.text.strip()

                # --- 追加デバッグプリント ---
                print(f"--- Link {i+1} ---")
                print(f"  Text: '{link_text}'")
                print(f"  URL: {url}")
                if url:
                    print(f"  Starts with http?: {url.startswith('http')}")
                    print(f"  Is excluded?: {is_excluded_url(url)}")
                else:
                    print(f"  URL is None or empty.")
                # --- ここまで ---

                if url and url.startswith('http') and url not in related_urls:
                    print(f"DEBUG: related_urlsに追加予定 (ngTNl ggLgoc): {url}")
                    related_urls.append(url)
                    print(f"関連検索URL: {url}")
                else:
                    # --- 条件に一致しなかった理由を表示 ---
                    print(f"  => このURLはリストに追加されません。")
        else:
            print("指定されたクラス 'ngTNl ggLgoc' を持つ関連検索リンクが見つかりませんでした。")
            
            # バックアップとして、他の可能性のある関連検索セクションを探す (例: #botstuff)
            print("バックアップとして #botstuff 内のリンクを探します...")
            try:
                footer_links = driver.find_elements(By.CSS_SELECTOR, "#botstuff a")
                for link in footer_links:
                    url = link.get_attribute('href')
                    text = link.text.strip()
                    if url and url.startswith('http') and 'google.com/search' in url and url not in related_urls and not is_navigation_text(text):
                        print(f"DEBUG: related_urlsに追加予定 (botstuff): {url}")
                        related_urls.append(url)
                        print(f"関連検索URL (botstuff): {url}")
            except Exception as e:
                print(f"#botstuff からの抽出中にエラー: {e}")


        print(f"Googleから合計 {len(related_urls)} 件の関連検索URLを抽出しました")

    except Exception as e:
        print(f"Googleの関連検索URL抽出中にエラーが発生しました: {e}")
        
    final_urls = list(dict.fromkeys(related_urls))
    print(f"DEBUG: extract_related_search_urls が返すリスト: {final_urls}")
    return final_urls

def extract_top_urls_from_search_url(driver, search_url, num_urls=3):
    """指定されたGoogle検索結果URLからh3タグを持つ上位のURLのみを抽出する"""
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
        driver.get(search_url) # 与えられたURLに直接アクセス
        
        time.sleep(3)  # ページ読み込みのための待機
        
        # CAPTCHAチェックを確認
        if "通常と異なるトラフィックが検出されました" in driver.page_source or "I'm not a robot" in driver.page_source or "私はロボットではありません" in driver.page_source:
            print("⚠️ CAPTCHAが検出されました。")
            print("手動でCAPTCHAを解決してください。")
            input("完了したらEnterキーを押してください...")
        
        extracted_count = 0
        
        # h3タグに関連するURLのみを取得するJavaScript (num_urls制限付き)
        # 注意: JavaScript内での厳密な num_urls 制限は複雑になるため、
        # Python側で取得後に制限するのが簡単で確実です。
        # ここではまずJSで可能な限り抽出し、後でPythonで絞り込みます。
        js_ordered_urls = driver.execute_script("""
            var orderedUrls = [];
            var mainContentAreas = [
                document.getElementById('search'),
                document.getElementById('center_col'),
                document.getElementById('rso'),
                document.getElementById('main'),
                document.querySelector('.v7W49e')
            ].filter(el => el !== null);
            
            if (mainContentAreas.length === 0) {
                mainContentAreas = [document.body]; 
            }
            
            for (var a = 0; a < mainContentAreas.length; a++) {
                var mainArea = mainContentAreas[a];
                var h3Elements = mainArea.querySelectorAll('h3');
                
                for (var i = 0; i < h3Elements.length; i++) {
                    var h3 = h3Elements[i];
                    var isFooterOrNav = false;
                    var parent = h3;
                    while (parent && parent !== document.body) {
                         if (parent.id && (parent.id.includes('footer') || parent.id === 'botstuff' || parent.id === 'appbar' || parent.id === 'hdtb')) { isFooterOrNav = true; break; }
                         if (parent.className && typeof parent.className === 'string' && (parent.className.includes('footer') || parent.className.includes('navcnt') || parent.className.includes('NKcBbd'))) { isFooterOrNav = true; break; }
                         parent = parent.parentElement;
                    }
                    if (isFooterOrNav) continue;

                    var foundLink = null;
                    var directParent = h3.parentElement;
                    if (directParent && directParent.tagName === 'A') {
                        foundLink = directParent;
                    }
                    if (!foundLink) {
                        var current = h3;
                        while (current && current !== document.body) {
                            if (current.tagName === 'A') { foundLink = current; break; }
                            current = current.parentElement;
                        }
                    }
                    if (!foundLink) {
                         var parentWithLink = h3.closest('div.g, div[data-hveid], div[data-ved], div.yuRUbf, div.kb0PBd');
                         if (parentWithLink) {
                             var links = parentWithLink.querySelectorAll('a');
                             if (links.length > 0) foundLink = links[0];
                         }
                    }
                    
                    if (foundLink) {
                        var url = foundLink.href;
                        if (url && 
                            !url.includes('google.com/search') &&
                            !url.includes('google.com/travel') &&
                            !url.includes('google.com/maps') &&
                            !url.includes('google.co.jp/intl') &&
                            !url.includes('support.google.com') &&
                            !url.includes('policies.google.com') &&
                            !url.includes('accounts.google.com') &&
                            !url.includes('google.com/preferences') &&
                            !url.includes('google.com/advanced_search') &&
                            !orderedUrls.includes(url)) {
                            orderedUrls.push(url);
                        }
                    }
                }
            }
            return orderedUrls;
        """)

        if js_ordered_urls:
            print(f"JavaScriptによる抽出で {len(js_ordered_urls)} 件のh3関連URLを見つけました")
            for url in js_ordered_urls:
                 if extracted_count < num_urls and not is_excluded_url(url) and url not in urls:
                     urls.append(url)
                     extracted_count += 1
                     print(f"  URL{extracted_count}: {url}")
                 if extracted_count >= num_urls:
                     break
        
        # JS抽出が不十分な場合や失敗した場合のバックアップ (Pythonベース)
        if extracted_count < num_urls:
            print("バックアップ手法で追加のURLを抽出します...")
            h3_elements = driver.find_elements(By.TAG_NAME, "h3")
            print(f"{len(h3_elements)} 件のh3タグを発見")

            for h3 in h3_elements:
                if extracted_count >= num_urls:
                    break
                try:
                    # h3の親または先祖要素にaタグがあるか探す (優先度高)
                    try:
                        a_ancestor = h3.find_element(By.XPATH, "./ancestor-or-self::a")
                        url = a_ancestor.get_attribute('href')
                        if url and not is_excluded_url(url) and url not in urls:
                            urls.append(url)
                            extracted_count += 1
                            print(f"  URL{extracted_count}: {url}")
                            continue # 見つかったら次へ
                    except NoSuchElementException:
                         pass # 祖先にaがなければ次へ

                    # h3の最も近い祖先の主要なコンテナdiv内の最初のaタグを探す (一般的な構造)
                    try:
                        container = h3.find_element(By.XPATH, "./ancestor::div[contains(@class, 'g') or contains(@class, 'yuRUbf') or contains(@class, 'kb0PBd') or @data-hveid or @data-ved][1]")
                        # コンテナ内の最初のリンクを取得
                        a_element = container.find_element(By.TAG_NAME, "a")
                        url = a_element.get_attribute('href')
                        if url and not is_excluded_url(url) and url not in urls:
                            urls.append(url)
                            extracted_count += 1
                            print(f"  URL{extracted_count}: {url}")
                            continue # 見つかったら次へ
                    except NoSuchElementException:
                         print(f"  h3タグ '{h3.text[:30]}...' に関連するコンテナ内のリンクが見つかりませんでした")
                    except Exception as e_inner:
                         print(f"  コンテナ検索中に予期せぬエラー: {e_inner}")

                except Exception as e:
                    print(f"  h3タグの処理中にエラー: {e}")

        print(f"検索結果URL '{search_url}' から {len(urls)} 件の上位URLを抽出しました")
        
        # タブを閉じる
        driver.close()
        
        # 元のタブに戻る
        driver.switch_to.window(current_handles[0])
        
    except Exception as e:
        print(f"検索結果URL '{search_url}' の処理中にエラーが発生しました: {e}")
        # エラーが発生しても元のタブに戻る
        # エラーが発生しても元のタブに戻る試み
        try:
            # 現在のタブを閉じる
            driver.close()
            # 元のタブに戻る
            driver.switch_to.window(current_handles[0])
        except:
            pass # 元のタブに戻れなくても処理は続行
            pass
    
    # return urls
    return urls[:num_urls] # 念のため最後にnum_urlsでスライス

def integrated_google_search(google_url):
    driver = None # driver変数を初期化
    try:
        # ディレクトリの確認
        base_dir = ensure_directories_exist()
        
        # 保存先ファイルパスの設定
        output_file_path = os.path.join(base_dir, "google_urls.txt")
        
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
        
        # Google検索結果ページにアクセス
        print(f"Google検索結果ページにアクセス中...")
        driver.get(google_url)
        time.sleep(5)  # ページ読み込みのための十分な待機時間
        
        # CAPTCHAチェックを確認
        if "通常と異なるトラフィックが検出されました" in driver.page_source or "I'm not a robot" in driver.page_source or "私はロボットではありません" in driver.page_source:
            print("\n⚠️ Google CAPTCHAが検出されました。")
            print("手動でCAPTCHAを解決してください。")
            # input("完了したらEnterキーを押してください...") # 自動化のためコメントアウト
            # 手動介入が必要な場合、ここで待機するのではなく、エラーとして処理するか、タイムアウトを設定する方が適切かもしれません。
            # 今回は、CAPTCHAが表示されても続行を試みますが、失敗する可能性が高いです。
            print("CAPTCHAが表示されたため、処理を続行しますが、失敗する可能性があります。")
            # 必要であれば、ここで数秒待機するなど、ユーザーが手動で対応する時間を与えます。
            # time.sleep(60) # 例: 60秒待機

        # 1. 最初のGoogle検索結果からURLを抽出
        direct_urls = extract_google_urls(driver)
        
        # 2. Googleの関連検索URLを抽出 (class="ngTNl ggLgoc")
        related_search_urls = extract_related_search_urls(driver)
        # print(f"DEBUG: integrated_google_search に渡された related_search_urls: {related_search_urls}") # デバッグ用
        
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

        # 出力: 設定形式でURLを保存
        with open(output_file_path, 'w', encoding='utf-8') as f:
            for url in all_urls:
                # ファイル書き込み前にもう一度除外チェック（念のため）
                if not is_excluded_url(url):
                     f.write(f"{url}\n")
            
        
        print(f"\n合計 {len(all_urls)} 件のユニークなURLを {output_file_path} に保存しました")
        print("処理が完了しました。") # メッセージ変更
        # print("閉じる準備ができたらEnterキーを押してください...") # 削除
        # input() # 削除
        
        # ブラウザは閉じない（ユーザーが操作できるようにするため） # 変更: 自動で閉じる
        # print("ブラウザは開いたままになっています。手動で閉じることができます。") # 削除
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        # 可能であればドライバーを閉じる試み (エラー時も閉じる)
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
    parser = argparse.ArgumentParser(description='Google検索結果ページからURLを抽出します。')
    parser.add_argument('google_url', type=str, help='Google検索結果ページのURL')
    
    # 引数を解析
    args = parser.parse_args()
    
    # print("Google検索結果ページのURLを指定してください") # 削除
    # google_url = input("Google検索結果ページのURL: ") # 削除
    google_url = args.google_url # 引数からURLを取得
    
    if not google_url:
        print("URLを指定してください")
    else:
        integrated_google_search(google_url)