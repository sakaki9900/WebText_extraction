import os
import re
import time
import requests
import concurrent.futures
import io # Add io for handling PDF data in memory
import configparser # configparserをインポート
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader # Add PdfReader from PyPDF2
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

class WebTextExtractor:
    def __init__(self, output_dir='outputs', num_workers=None, cpu_ratio=None):
        """
        初期化メソッド
        
        Parameters:
        output_dir (str): 出力ディレクトリのパス
        num_workers (int): 並列処理に使用するワーカー数（指定がなければCPUコア数）
        cpu_ratio (float): CPUコア数に対する使用率（0.0〜1.0）
        """
        # CPUのコア数を取得
        cpu_count = os.cpu_count()
        
        # ワーカー数の決定
        if num_workers is not None:
            self.num_workers = num_workers
        elif cpu_ratio is not None:
            # CPUコア数に対する割合から計算
            self.num_workers = max(1, int(cpu_count * cpu_ratio))
        else:
            # デフォルトはCPUコア数
            self.num_workers = cpu_count
        
        self.output_dir = output_dir
        
        # 出力ディレクトリがなければ作成
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Seleniumの設定（ヘッドレスモード）
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--window-size=1920,1080')
        self.chrome_options.add_argument('--disable-extensions')
        # User-Agentを設定
        self.chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')
        
    def get_driver(self):
        """WebDriverのインスタンスを作成する"""
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            return driver
        except Exception as e:
            print(f"ChromeDriver初期化エラー: {e}")
            # ローカルのドライバーを試す
            try:
                service = Service("./chromedriver-win64/chromedriver.exe")
                driver = webdriver.Chrome(service=service, options=self.chrome_options)
                return driver
            except Exception as e2:
                print(f"ローカルのドライバー初期化エラー: {e2}")
                return None
    
    def _try_jina_reader(self, url):
        """Jina AI Readerを使用してテキスト抽出を試みる"""
        jina_url = f"https://r.jina.ai/{url}"
        print(f"Jina AI Readerを試行: {jina_url}")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
            }
            response = requests.get(jina_url, headers=headers, timeout=60)
            response.raise_for_status()
            content = response.text

            # 不要な要素を除去
            # 1. ヘッダー行の削除 (Jinaが挿入する可能性のあるもの)
            content = re.sub(r'^Title:.*\n?', '', content, flags=re.MULTILINE)
            content = re.sub(r'^URL Source:.*\n?', '', content, flags=re.MULTILINE)
            content = re.sub(r'^Published Time:.*\n?', '', content, flags=re.MULTILINE)
            content = re.sub(r'^Markdown Content:\n?', '', content, flags=re.MULTILINE)

            # 2. Jina自身のソースリンクを削除
            content = re.sub(r'\[Source\]\(https://r\.jina\.ai/[^)]+\)\s*', '', content)

            # 3. 画像や不要なMarkdownリンクの削除 (URLは全て削除、テキストも含む)
            content = re.sub(r'\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)\s*', '', content) # 画像を含むリンク全体
            content = re.sub(r'!\[[^\]]*\]\([^)]*\)\s*', '', content) # 単独の画像
            content = re.sub(r'\[[^\]]*\]\([^)]*\)\s*', '', content) # 通常のMarkdownリンク全体

            # 4. HTML画像タグの削除
            content = re.sub(r'<img[^>]*>\s*', '', content)

            # 5. 余分な空行を整理
            content = re.sub(r'\n\s*\n', '\n\n', content).strip()

            # Jinaが空の内容や短いエラーメッセージを返す場合があるため、長さもチェック
            if content and len(content) > 50: # 最低限の文字数を期待
                print(f"Jina AI Reader成功 (加工後): {url}")
                return content
            else:
                print(f"Jina AI Readerの結果が空または短すぎます (加工後): {url}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Jina AI Readerでの取得エラー: {jina_url} - {e}")
            return None
        except Exception as e:
            print(f"Jina AI Reader処理中の予期せぬエラー: {url} - {e}")
            return None

    def _extract_text_from_pdf(self, url):
        """PDFファイルからテキストを抽出する"""
        print(f"PDF処理開始: {url}")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=60, stream=True) # stream=True for potentially large files
            response.raise_for_status()

            # メモリ上でPDFデータを扱う
            pdf_file = io.BytesIO(response.content)
            reader = PdfReader(pdf_file)
            
            text_content = ""
            for page in reader.pages:
                try:
                    page_text = page.extract_text()
                    if page_text: # 抽出できた場合のみ追加
                        text_content += page_text + "\n"
                except Exception as page_e:
                    print(f"PDFページ抽出エラー ({url}, page {reader.pages.index(page) + 1}): {page_e}")
                    # エラーが発生したページはスキップして続行
            
            if text_content.strip():
                print(f"PDF処理成功: {url}")
                return text_content.strip()
            else:
                print(f"PDFからテキストを抽出できませんでした（内容は空）: {url}")
                return f"PDFからテキストを抽出できませんでした: {url}" # 失敗メッセージ

        except requests.exceptions.RequestException as e:
            print(f"PDFダウンロードエラー: {url} - {e}")
            return f"PDFファイルのダウンロードに失敗しました: {url}"
        except Exception as e:
            # PyPDF2関連のエラー（パスワード保護、破損など）もここで捕捉される可能性
            print(f"PDF処理中に予期せぬエラー: {url} - {e}")
            return f"PDFファイルの処理中にエラーが発生しました: {url}"

    def _cleanup_extracted_text(self, text):
        """
        抽出されたテキストを整理する
        - 不要なURLの削除
        - 余分な空行の削除
        - その他の整形
        
        Parameters:
        text (str): 整理する元のテキスト
        
        Returns:
        str: 整理されたテキスト
        """
        if not text:
            return text
            
        import re
        
        # URLを削除（複数のパターンを試す）
        # 1. 標準的なURLパターン (http, https)
        text = re.sub(r'https?://\S+', '', text)
        
        # 2. www.で始まるURL
        text = re.sub(r'www\.\S+', '', text)
        
        # 3. URLと思われる文字列（より広範囲なパターン）
        text = re.sub(r'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'\".,<>?«»""'']))', '', text)
        
        # 余分な空行を整理
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # 先頭と末尾の空白を削除
        text = text.strip()
        
        # 文字化け文字の削除（制御文字、置換文字など。ただし改行・タブは保持）
        text = text.replace('\uFFFD', '')
        cleaned_chars = []
        for ch in text:
            if ch in '\n\t\r':
                cleaned_chars.append(ch)
            elif ch.isprintable():
                cleaned_chars.append(ch)
        text = ''.join(cleaned_chars)
        
        # 重複コンテンツの除去
        text = self._remove_duplicate_content(text)
        
        return text

    def _is_pinterest_navigation_error(self, text):
        """
        抽出されたテキストがPinterestのナビゲーション要素のみかチェックする
        
        Parameters:
        text (str): チェックするテキスト
        
        Returns:
        bool: Pinterestナビゲーション要素のみの場合True、そうでなければFalse
        """
        if not text or len(text.strip()) == 0:
            return False
        
        # 正常なコンテンツの兆候をチェック
        content_indicators = [
            # ドメイン名のパターン
            r'\b[a-zA-Z0-9-]+\.(com|net|org|jp|co\.jp)\b',
            # URLパターン
            r'https?://[^\s]+',
            # 記事タイトルっぽいパターン（日本語文字を含む長い文）
            r'[あ-んア-ンア-ヶー一-龯]{10,}',
            # 英語記事タイトルっぽいパターン
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){3,}',
            # 目次や番号付きリスト
            r'(?:目次|第\d+章|\d+\.\s)',
            # 日付パターン
            r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',
        ]
        
        import re
        for pattern in content_indicators:
            if re.search(pattern, text):
                print(f"正常なコンテンツを検出: {pattern[:20]}...")
                return False
        
        # Pinterestナビゲーション要素のキーフレーズ
        nav_phrases = [
            "Skip to content",
            "Explore ideas", 
            "Search for easy dinners",
            "When autocomplete results are available",
            "Log in",
            "Sign up",
            "コンテンツへスキップ",
            "アイデアを探す",
            "簡単ディナーレシピ"
        ]
        
        # ナビゲーション要素の文字数を計算
        nav_char_count = 0
        total_nav_phrases = 0
        
        for phrase in nav_phrases:
            if phrase in text:
                nav_char_count += len(phrase)
                total_nav_phrases += 1
        
        # テキスト全体の文字数
        total_char_count = len(text.strip())
        
        # ナビゲーション要素が大部分を占めている場合のみエラーと判定
        if total_nav_phrases >= 4 and total_char_count > 0:
            nav_ratio = nav_char_count / total_char_count
            if nav_ratio > 0.7:  # 70%以上がナビゲーション要素
                print(f"Pinterestナビゲーション要素の割合が高い: {nav_ratio:.2f}")
                return True
        
        # より厳密な完全一致パターンチェック
        # ナビゲーション要素のみで構成される典型的なパターン
        strict_nav_pattern = (
            "Skip to content "
            "Explore ideas "
            "Search for easy dinners, fashion, etc. "
            "When autocomplete results are available use up and down arrows to review and enter to select. Touch device users, explore by touch or with swipe gestures. "
            "Log in "
            "Sign up"
        )
        
        normalized_text = ' '.join(text.split())
        normalized_pattern = ' '.join(strict_nav_pattern.split())
        
        # 正規化されたテキストがナビゲーションパターンと非常に類似している場合
        if len(normalized_text) < 300 and normalized_pattern in normalized_text:
            return True
        
        return False

    def _remove_duplicate_content(self, text):
        """
        テキストから重複部分を除去する
        
        Parameters:
        text (str): 処理するテキスト
        
        Returns:
        str: 重複が除去されたテキスト
        """
        if not text or len(text.strip()) < 100:
            return text
        
        # テキストを段落ごとに分割
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        if len(paragraphs) < 2:
            return text
        
        # difflibを使って類似した段落を検出
        from difflib import SequenceMatcher
        
        unique_paragraphs = []
        seen_paragraphs = []
        
        for para in paragraphs:
            is_duplicate = False
            
            # 既存の段落と比較
            for seen_para in seen_paragraphs:
                # 類似度を計算（0.8以上で重複と判定）
                similarity = SequenceMatcher(None, para, seen_para).ratio()
                if similarity > 0.8:
                    print(f"重複段落を検出 (類似度: {similarity:.2f}): {para[:50]}...")
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_paragraphs.append(para)
                seen_paragraphs.append(para)
        
        # 重複が除去された場合のみログ出力
        if len(unique_paragraphs) < len(paragraphs):
            removed_count = len(paragraphs) - len(unique_paragraphs)
            print(f"重複除去: {removed_count}個の重複段落を削除")
        
        return '\n\n'.join(unique_paragraphs)

    def extract_text_from_url(self, url):
        """
        URLからメインコンテンツを抽出する (PDF / Jina AI Reader フォールバック付き)
        """
        print(f"処理中: {url}")

        # --- 最初にコンテンツタイプを確認 --- 
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
            }
            # HEADリクエストでContent-Typeを取得 (タイムアウト設定)
            head_response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
            head_response.raise_for_status() # エラーがあれば例外発生
            content_type = head_response.headers.get('Content-Type', '').lower()

            if 'application/pdf' in content_type:
                print(f"コンテンツタイプ application/pdf を検出: {url}")
                # PDF処理メソッドを呼び出す
                extracted_text = self._extract_text_from_pdf(url)
                if extracted_text and "失敗しました" not in extracted_text:
                    # PDFから抽出に成功した場合、テキストをクリーンアップして返す
                    return self._cleanup_extracted_text(extracted_text)
                return extracted_text  # 失敗メッセージはそのまま返す
            else:
                print(f"コンテンツタイプ: {content_type} (PDFではないため、HTML/Webページとして処理): {url}")

        except requests.exceptions.Timeout:
            print(f"コンテンツタイプ確認中にタイムアウト: {url} - Webページとして処理を続行します")
            # タイムアウトした場合でも、通常のWebページとして処理を試みる
            pass
        except requests.exceptions.RequestException as e:
            print(f"コンテンツタイプ確認中にエラー: {url} - {e} - Webページとして処理を続行します")
            # 他のRequestエラーでも通常のWebページとして処理を試みる
            pass
        except Exception as e:
            print(f"コンテンツタイプ確認中に予期せぬエラー: {url} - {e} - Webページとして処理を続行します")
            # 予期せぬエラーでも通常のWebページとして処理を試みる
            pass
        # --- コンテンツタイプ確認 終了 ---

        # 1. 特定ドメインまたは特定パスの場合: Jina -> Selenium
        target_domains = ['youtube.com'] # news.netkeiba.com を削除, instagram.com も削除済み
        is_target_domain = any(domain in url for domain in target_domains)
        is_yahoo_image_search = url.startswith('https://search.yahoo.co.jp/image/search')

        if is_target_domain or is_yahoo_image_search:
            log_prefix = ""
            if is_target_domain:
                log_prefix = "特定ドメイン"
            elif is_yahoo_image_search:
                log_prefix = "Yahoo画像検索"

            print(f"{log_prefix}を検出: {url}")
            jina_result = self._try_jina_reader(url)
            if jina_result: # Noneでなく、空でもないことを確認
                return jina_result

            print(f"{log_prefix}のJina AI Reader失敗、Seleniumを試みます: {url}")
            selenium_result = self.extract_with_selenium(url)
            if selenium_result: # Noneでなく、空でもないことを確認
                 print(f"{log_prefix}のSelenium抽出成功: {url}")
                 return selenium_result
            else:
                 print(f"{log_prefix}のJinaおよびSeleniumでの抽出に失敗しました: {url}")
                 # ここでは失敗メッセージを返さず、後続の処理を試す場合もあるが、
                 # この特定ドメイン処理は元々フォールバックしない設計だったので一旦そのまま
                 return f"{log_prefix}の抽出に失敗しました (Jina & Selenium): {url}"

        # --- ここから特殊ハンドラと通常ドメイン処理 ---
        extracted_text = None # 抽出結果を保持する変数を初期化
        special_handler_failed_message = None # 特殊ハンドラの失敗メッセージを保持

        # 2. 特殊ハンドラ試行
        special_handler_result = None
        is_special_handled = False
        if 'detail.chiebukuro.yahoo.co.jp' in url:
            is_special_handled = True
            special_handler_result = self.handle_yahoo_chiebukuro(url)
        elif 'instagram.com' in url:
            is_special_handled = True
            special_handler_result = self.handle_instagram_page(url)
        elif 'x.com' in url or 'twitter.com' in url:
            is_special_handled = True
            special_handler_result = self.handle_twitter_page(url)

        # 特殊ハンドラの結果をチェック
        if is_special_handled:
            if special_handler_result and "失敗しました" not in special_handler_result and special_handler_result.strip():
                print(f"特殊ハンドラでの抽出成功: {url}")
                # 特殊ハンドラで成功した結果をクリーンアップして返す
                return self._cleanup_extracted_text(special_handler_result)
            else:
                # ハンドラは実行されたが失敗した or 空の結果だった
                print(f"特殊ハンドラでの抽出失敗、通常抽出プロセスへフォールバック: {url}")
                if special_handler_result and "失敗しました" in special_handler_result:
                    special_handler_failed_message = special_handler_result # 失敗メッセージを保持
                # extracted_text は None のまま後続処理へ

        # --- ここから通常のドメイン処理 (特殊ハンドラ対象外 or 特殊ハンドラが失敗した場合) ---

        # 3. 通常抽出 (Requests + BeautifulSoup)
        # extracted_text が None の場合のみ実行 (特殊ハンドラが成功していればスキップされる)
        if extracted_text is None:
            soup = None # soupを初期化
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()

                # --- エンコーディング判定の改善 ---
                content_type = response.headers.get('content-type')
                encoding = None
                if content_type:
                    match = re.search(r'charset=([\w-]+)', content_type, re.IGNORECASE)
                    if match:
                        encoding = match.group(1)
                        try:
                            # エンコーダが存在するかテスト
                            "".encode(encoding)
                            print(f"HTTPヘッダーから有効なエンコーディング {encoding} を検出: {url}")
                        except LookupError:
                            print(f"HTTPヘッダーのエンコーディング {encoding} は無効です。無視します。: {url}")
                            encoding = None # 無効なエンコーディングは無視

                if not encoding:
                    # apparent_encoding を試す
                    encoding = response.apparent_encoding
                    if encoding:
                         try:
                            "".encode(encoding)
                            print(f"apparent_encodingから有効なエンコーディング {encoding} を検出: {url}")
                         except LookupError:
                            print(f"apparent_encoding {encoding} は無効です。無視します。: {url}")
                            encoding = None # 無効なエンコーディングは無視
                    else:
                         print(f"apparent_encodingでも検出できませんでした。: {url}")


                # それでもダメならUTF-8を試す
                if not encoding:
                    encoding = 'utf-8' # デフォルトエンコーディング
                    print(f"デフォルトエンコーディング {encoding} を使用: {url}")

                # response.text の代わりに content をデコードする
                html_content = None
                try:
                    html_content = response.content.decode(encoding, errors='replace')
                    print(f"{encoding} でデコード成功: {url}")
                except Exception as decode_e:
                    print(f"{encoding}でのデコードに失敗、UTF-8で再試行: {url} - {decode_e}")
                    # UTF-8でのデコードを試みる（エラーがあれば無視）
                    try:
                        html_content = response.content.decode('utf-8', errors='replace')
                        print(f"UTF-8での再試行デコード成功: {url}")
                        encoding = 'utf-8' # 成功したエンコーディングを記録
                    except Exception as utf8_decode_e:
                        print(f"UTF-8でのデコードにも失敗、BeautifulSoupに任せる: {url} - {utf8_decode_e}")
                        # 最悪の場合、BeautifulSoupに任せる (response.text と同様の挙動)
                        # この場合、html_content は None のままにするか、response.text を使う
                        html_content = response.text # response.textを使う場合

                if html_content:
                    # 渡されたエンコーディング情報があればそれを使う
                    soup = BeautifulSoup(html_content, 'html.parser')
                else:
                     # デコードに失敗した場合、BeautifulSoupに自動判別させる
                     print(f"デコードに失敗したため、BeautifulSoupの自動判別に任せます: {url}")
                     soup = BeautifulSoup(response.content, 'html.parser') # contentを直接渡す

                # --- soup を使った処理 ---
                if soup: # soupが正常に生成された場合のみ続行
                    domain_match = re.search(r'https?://(?:www\\.)?([^/]+)', url)
                    domain = domain_match.group(1) if domain_match else ""
                    content_from_soup = self.extract_main_content(soup, domain) # 失敗時は空文字列を返す想定

                    if content_from_soup and len(content_from_soup.strip()) >= 100:
                        print(f"通常抽出(Requests)成功: {url}")
                        extracted_text = content_from_soup.strip() # 成功結果を保持
                    else:
                        # extracted_text は None のまま、または短い結果を保持
                        extracted_text = content_from_soup if content_from_soup else None
                        print(f"通常抽出(Requests)失敗または不十分、Seleniumを試みます: {url}")
                else:
                    print(f"BeautifulSoupオブジェクトの生成に失敗しました、Seleniumを試みます: {url}")


            except requests.exceptions.RequestException as e:
                print(f"通常抽出(Requests)中にRequestエラー発生、Seleniumを試みます: {url} - {e}")
            except Exception as e:
                print(f"通常抽出(Requests)中に予期せぬエラー発生、Seleniumを試みます: {url} - {e}")

        # 4. Selenium抽出試行
        # extracted_text がまだ None か、または Requests の結果が短かった場合に実行
        # (十分な長さのテキストが取得できていればスキップ)
        if extracted_text is None or (extracted_text and len(extracted_text.strip()) < 100):
            print(f"Selenium抽出試行開始: {url}") # Selenium試行開始ログ
            selenium_result = self.extract_with_selenium(url)
            if selenium_result and len(selenium_result.strip()) >= 100:
                 print(f"Selenium抽出成功: {url}")
                 extracted_text = selenium_result # 成功結果を保持
            else:
                 # Seleniumの結果が短い場合でも、元のRequestsの結果よりは良いかもしれない
                 # より長い方を保持しておく (ただし、どちらもNoneや空文字列の可能性あり)
                 best_result_so_far = None
                 current_extracted = extracted_text if extracted_text else ""
                 selenium_res = selenium_result if selenium_result else ""

                 if len(selenium_res) > len(current_extracted):
                     best_result_so_far = selenium_res
                 else:
                     best_result_so_far = current_extracted

                 # best_result_so_far が空文字列でなければ extracted_text を更新
                 if best_result_so_far:
                      extracted_text = best_result_so_far
                 else: # 両方空なら None に戻す
                      extracted_text = None

                 print(f"Selenium抽出失敗または不十分、最終手段としてJina AI Readerを試みます: {url}")

        # 5. 最終手段: Jina AI Reader試行
        # extracted_text がまだ None か、または Selenium/Requests の結果が短かった場合に実行
        if extracted_text is None or (extracted_text and len(extracted_text.strip()) < 100):
            print(f"最終手段 Jina AI Reader 試行開始: {url}") # Jina試行開始ログ
            final_jina_result = self._try_jina_reader(url)
            if final_jina_result: # Jinaの結果があればそれを優先
                print(f"最終手段のJina AI Reader成功: {url}")
                # Jinaの結果をクリーンアップして保持
                extracted_text = self._cleanup_extracted_text(final_jina_result)
            # else: Jinaも失敗した場合、extracted_text は前のステップの結果（短いかもしれないが）または None のまま

        # --- 最終結果の返却 ---
        if extracted_text and extracted_text.strip():
            # Pinterestページの特別チェック
            if 'pinterest.com' in url and self._is_pinterest_navigation_error(extracted_text):
                print(f"Pinterestナビゲーション要素のみ検出、専用ハンドラーを実行: {url}")
                pinterest_result = self.handle_pinterest_page(url)
                if pinterest_result and "失敗しました" not in pinterest_result and pinterest_result.strip():
                    print(f"Pinterest専用ハンドラーでの抽出成功: {url}")
                    return self._cleanup_extracted_text(pinterest_result)
                else:
                    print(f"Pinterest専用ハンドラーも失敗、通常の抽出結果を返却: {url}")
                    # 専用ハンドラーも失敗した場合は通常の抽出結果をそのまま返す
            
            # テキストが抽出できた場合、クリーンアップして返す
            return self._cleanup_extracted_text(extracted_text.strip())
        else: # 本当に何も取れなかった場合
            print(f"すべての抽出方法が失敗しました: {url}")
            # 特殊ハンドラが実行されて失敗メッセージを返していた場合は、それを返す
            if special_handler_failed_message:
                return special_handler_failed_message
            else:
                # 汎用的な失敗メッセージを返す
                return f"すべての抽出方法でテキストを抽出できませんでした: {url}"

    def handle_twitter_page(self, url):
        """X (旧Twitter) ページの処理"""
        try:
            driver = self.get_driver()
            if not driver:
                return f"ドライバーの初期化に失敗したため、{url} からテキストを抽出できませんでした。"
                
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article"))
            )
            
            # スクロールして全コンテンツを読み込む
            for _ in range(3):  # 数回スクロールする
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            tweets = soup.select("article")
            
            text_content = []
            for tweet in tweets:
                tweet_text = tweet.get_text(separator=' ', strip=True)
                if tweet_text:
                    text_content.append(tweet_text)
            
            return "\n\n".join(text_content)
        except Exception as e:
            print(f"X処理エラー: {url} - {e}")
            return f"X (Twitter) ページからのテキスト抽出に失敗しました: {url}"
        finally:
            if driver:
                driver.quit()
    
    def handle_instagram_page(self, url):
        """Instagramページの処理"""
        try:
            driver = self.get_driver()
            if not driver:
                return f"ドライバーの初期化に失敗したため、{url} からテキストを抽出できませんでした。"
                
            driver.get(url)
            # Instagramはロードに時間がかかることがある
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article"))
            )
            time.sleep(3)  # 追加の待機時間
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # ポストの説明文を取得
            post_texts = []
            articles = soup.select("article")
            
            for article in articles:
                # キャプションを探す
                captions = article.select("h1, span")
                for caption in captions:
                    text = caption.get_text(strip=True)
                    if text and len(text) > 20:  # 短すぎるテキストは除外
                        post_texts.append(text)
            
            if not post_texts:
                # エレメントを直接探して見る
                try:
                    captions = driver.find_elements(By.CSS_SELECTOR, "._a9zs")
                    for caption in captions:
                        post_texts.append(caption.text)
                except:
                    pass
            
            return "\n\n".join(post_texts) if post_texts else f"Instagramポストからテキストが見つかりませんでした: {url}"
        except Exception as e:
            print(f"Instagram処理エラー: {url} - {e}")
            return f"Instagramページからのテキスト抽出に失敗しました: {url}"
        finally:
            if driver:
                driver.quit()
    
    def handle_yahoo_chiebukuro(self, url):
        """Yahoo知恵袋ページの処理"""
        try:
            driver = self.get_driver()
            if not driver:
                return f"ドライバーの初期化に失敗したため、{url} からテキストを抽出できませんでした。"
                
            driver.get(url)
            
            # ページが完全に読み込まれるまで待機
            time.sleep(5)  # 読み込み待機時間を増やす
            
            try:
                # 新しい質問タイトルのセレクタを待機
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".Title__title"))
                )
            except:
                # 古いセレクタでも試す
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".ColumnHead__title"))
                    )
                except:
                    pass  # どちらも見つからない場合は続行
            
            # 「その他の回答をもっと見る」ボタンをクリック
            try:
                # 複数のセレクタを試す
                more_buttons_selectors = [
                    "//button[contains(text(), 'その他の回答をもっと見る')]",
                    "//button[contains(text(), '回答をもっと見る')]",
                    "//*[contains(text(), 'その他の回答をもっと見る')]",
                    "//*[contains(text(), '回答をもっと見る')]",
                    "//button[contains(@class, 'MoreButton')]"
                ]
                
                for selector in more_buttons_selectors:
                    buttons = driver.find_elements(By.XPATH, selector)
                    if buttons:
                        for button in buttons:
                            try:
                                driver.execute_script("arguments[0].click();", button)
                                time.sleep(2)  # クリック後の待機時間を増やす
                                print(f"「その他の回答をもっと見る」ボタンをクリックしました")
                            except Exception as e:
                                print(f"ボタンクリックエラー: {e}")
            except Exception as e:
                print(f"「その他の回答をもっと見る」ボタンの処理中にエラー: {e}")
            
            # 「さらに返信を表示」ボタンをクリック
            try:
                # 複数のセレクタを試す
                more_reply_selectors = [
                    "//button[contains(text(), 'さらに返信を表示')]",
                    "//*[contains(text(), 'さらに返信を表示')]",
                    "//button[contains(@class, 'ReplyList__more')]"
                ]
                
                for selector in more_reply_selectors:
                    buttons = driver.find_elements(By.XPATH, selector)
                    if buttons:
                        for button in buttons:
                            try:
                                driver.execute_script("arguments[0].click();", button)
                                time.sleep(2)  # クリック後の待機時間を増やす
                                print(f"「さらに返信を表示」ボタンをクリックしました")
                            except Exception as e:
                                print(f"返信ボタンクリックエラー: {e}")
            except Exception as e:
                print(f"「さらに返信を表示」ボタンの処理中にエラー: {e}")
            
            # 最終的なページソースを取得
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # 特にleftColumnを探す
            left_column = soup.find('div', id='leftColumn')
            if left_column:
                # 「あわせて知りたい」セクションを削除
                related_sections = []
                
                # さまざまな「あわせて知りたい」セクションの検出方法を試す
                # 1. 直接テキストで検索
                for heading in left_column.find_all(['h2', 'h3', 'h4', 'div']):
                    if heading.get_text() and 'あわせて知りたい' in heading.get_text():
                        # 親要素も含めて削除対象に
                        parent = heading.parent
                        if parent not in related_sections:
                            related_sections.append(parent)
                
                # 2. クラス名で検索
                for related_div in left_column.find_all('div', class_=lambda c: c and ('RelatedContent' in c or 'related' in c.lower())):
                    if related_div not in related_sections:
                        related_sections.append(related_div)
                
                # 3. id名で検索
                for related_div in left_column.find_all('div', id=lambda i: i and ('RelatedContent' in i or 'related' in i.lower())):
                    if related_div not in related_sections:
                        related_sections.append(related_div)
                
                # 4. 「あわせて知りたい」を含むテキストを持つdivの親要素を検索
                for text_elem in left_column.find_all(text=lambda t: t and 'あわせて知りたい' in t):
                    parent = text_elem.parent
                    while parent and parent.name != 'div' and parent != left_column:
                        parent = parent.parent
                    if parent and parent != left_column and parent not in related_sections:
                        related_sections.append(parent)
                
                # 見つかったすべての「あわせて知りたい」セクションを削除
                for section in related_sections:
                    section.decompose()
                
                # 下部のその他のQ&Aや関連コンテンツも削除
                for heading in left_column.find_all(['h2', 'h3', 'h4']):
                    heading_text = heading.get_text().lower()
                    if any(keyword in heading_text for keyword in ['その他の回答をもっと見る', 'q&aをもっと見る', '人気の質問']):
                        parent = heading.parent
                        if parent:
                            parent.decompose()
                
                # 広告要素も削除
                for ad in left_column.find_all('div', class_=lambda c: c and ('Ad' in c or 'ad' in c.lower() or 'advertisement' in c.lower())):
                    ad.decompose()
                
                # サイドバー要素も削除
                for sidebar in left_column.find_all('div', class_=lambda c: c and ('sidebar' in c.lower() or 'side-bar' in c.lower())):
                    sidebar.decompose()
                
                # ページナビゲーションも削除
                for nav in left_column.find_all('div', class_=lambda c: c and ('navigation' in c.lower() or 'pagination' in c.lower())):
                    nav.decompose()
                
                # 質問と回答の主要部分のみを抽出
                content = left_column.get_text(separator='\n', strip=True)
                
                # 余分な空行を削除し、整形
                content = re.sub(r'\n\s*\n', '\n\n', content)
                
                return content
            
            # leftColumnが見つからない場合は従来の方法で抽出を試みる
            # 質問タイトル - 複数のセレクタを試す
            title_text = ""
            for title_selector in [".Title__title", ".ColumnHead__title", ".QuestionDetail__title"]:
                question_title = soup.select_one(title_selector)
                if question_title:
                    title_text = question_title.get_text(strip=True)
                    break
            
            # 質問内容 - 複数のセレクタを試す
            content_text = ""
            for content_selector in [".ClapLv1__content", ".QuestionDetail__content", ".Question__body"]:
                question_content = soup.select_one(content_selector)
                if question_content:
                    content_text = question_content.get_text(strip=True)
                    break
            
            # ベストアンサーと回答 - 複数のセレクタを試す
            answers = []
            for answer_selector in [".ClapLv2__item", ".AnswerItem", ".Answer__body"]:
                answer_elements = soup.select(answer_selector)
                if answer_elements:
                    for answer in answer_elements:
                        answer_text = answer.get_text(separator='\n', strip=True)
                        if answer_text:
                            answers.append(answer_text)
                    break
            
            # より一般的な方法で回答を見つける試み
            if not answers:
                # 親要素を特定せずに、回答らしい要素を探す
                possible_answers = soup.select("div.Answer, div.AnswerItem, div.ClapLv2__item, div[data-testid='answer']")
                for answer in possible_answers:
                    answer_text = answer.get_text(separator='\n', strip=True)
                    if answer_text and len(answer_text) > 50:  # 十分な長さを持つテキストのみ
                        answers.append(answer_text)
            
            # それでも見つからない場合は、より一般的なアプローチ
            if not title_text and not content_text and not answers:
                # 知恵袋は通常、質問と回答のセクションが明確に分かれている
                # まず、大きな塊のテキストを探す
                main_blocks = []
                for tag in soup.find_all(["div", "section", "article"]):
                    text = tag.get_text(strip=True)
                    if len(text) > 100 and not any(keyword in text.lower() for keyword in ['あわせて知りたい', '人気の質問']):  # ある程度長いテキストブロック
                        main_blocks.append((tag, text))
                
                # テキスト長でソートし、最も長い3つのブロックを取得
                main_blocks.sort(key=lambda x: len(x[1]), reverse=True)
                
                if main_blocks:
                    if not title_text and len(main_blocks) > 0:
                        # 最初のブロックは質問タイトルや内容の可能性が高い
                        title_candidate = main_blocks[0][0].find(["h1", "h2", "h3"])
                        if title_candidate:
                            title_text = title_candidate.get_text(strip=True)
                    
                    for i, (block, text) in enumerate(main_blocks[:3]):  # 上位3ブロックまで
                        if i == 0 and not content_text:
                            content_text = text
                        else:
                            answers.append(text)
            
            # 結果を結合
            result = []
            if title_text:
                result.append(f"【質問】{title_text}")
            if content_text:
                result.append(content_text)
            if answers:
                result.append("\n【回答】")
                result.extend(answers)
            
            # 結果が空の場合はエラーメッセージを返す
            if not result:
                print(f"知恵袋から抽出できませんでした: {url}")
                return f"知恵袋からコンテンツを抽出できませんでした: {url}"
            
            extracted_result = "\n\n".join(result)
            print(f"知恵袋抽出結果（先頭50文字）: {extracted_result[:50]}...")
            return extracted_result
            
        except Exception as e:
            print(f"知恵袋処理エラー: {url} - {e}")
            return f"Yahoo知恵袋ページからのテキスト抽出に失敗しました: {url}"
        finally:
            if driver:
                driver.quit()
    
    def handle_youtube_page(self, url):
        """YouTubeページの処理"""
        try:
            driver = self.get_driver()
            if not driver:
                return f"ドライバーの初期化に失敗したため、{url} からテキストを抽出できませんでした。"
                
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "title"))
            )
            
            # タイトルとチャンネル名の取得
            title_element = driver.find_element(By.CSS_SELECTOR, "h1.title")
            title = title_element.text if title_element else ""
            
            # 説明文の展開ボタンをクリック
            try:
                more_button = driver.find_element(By.CSS_SELECTOR, "#expand")
                driver.execute_script("arguments[0].click();", more_button)
                time.sleep(1)
            except:
                pass
            
            # 説明文の取得
            description = ""
            try:
                description_element = driver.find_element(By.CSS_SELECTOR, "#description-inline-expander")
                description = description_element.text
            except:
                pass
            
            result = []
            if title:
                result.append(f"【タイトル】{title}")
            if description:
                result.append(f"【説明】\n{description}")
            
            return "\n\n".join(result)
        except Exception as e:
            print(f"YouTube処理エラー: {url} - {e}")
            return f"YouTubeページからのテキスト抽出に失敗しました: {url}"
        finally:
            if driver:
                driver.quit()
    
    def handle_pinterest_page(self, url):
        """Pinterestページの包括的なテキスト抽出"""
        try:
            driver = self.get_driver()
            if not driver:
                return f"ドライバーの初期化に失敗したため、{url} からテキストを抽出できませんでした。"
                
            driver.get(url)
            
            # Pinterestはロードに時間がかかることがあるので十分な待機時間を設定
            time.sleep(5)
            
            # ピンのメインコンテナの読み込み完了を待機
            try:
                WebDriverWait(driver, 15).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test-id='pin-close-up-content']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test-id='closeup-body']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-test-id='pin']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "article")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "main"))
                    )
                )
            except TimeoutException:
                print(f"Pinterest: メインコンテンツの読み込みがタイムアウトしました: {url}")
                # タイムアウトしても処理を続行
            
            # ページを少しスクロールしてコンテンツを完全に読み込む
            driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 800);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            result = []
            extracted_content = []
            
            # 1. ドメインリンクを抽出
            domain_links = []
            domain_selectors = [
                "[data-test-id='pin-domain-link'] span",
                "[data-test-id='pin-domain-link'] a",
                "[data-test-id='pin-domain-link']",
                "span[style*='text-decoration: underline']",
                "a[href*='http']"
            ]
            
            for selector in domain_selectors:
                domain_elements = soup.select(selector)
                for elem in domain_elements:
                    domain_text = elem.get_text(strip=True)
                    if domain_text and ('.' in domain_text or 'http' in domain_text):
                        if domain_text not in domain_links and len(domain_text) < 100:
                            domain_links.append(domain_text)
            
            # 2. タイトルを抽出（より包括的に）
            pin_titles = []
            title_selectors = [
                "h1.FAo.dyH.Cc2.X8m.V2L.G1E",  # 具体的なクラス
                "h1[data-test-id='pin-title']",
                "h1[data-test-id='title']", 
                "div[data-test-id='pin-description'] h1",
                "div[data-test-id='closeup-title'] h1",
                "h1",
                ".FAo.dyH.Cc2.X8m.V2L.G1E"  # クラスベースの選択
            ]
            
            for selector in title_selectors:
                title_elements = soup.select(selector)
                for elem in title_elements:
                    title_text = elem.get_text(strip=True)
                    if title_text and len(title_text) > 5 and title_text not in pin_titles:
                        pin_titles.append(title_text)
            
            # 3. 説明文・概要を抽出
            descriptions = []
            description_selectors = [
                "span.X8m.zDA.IZT.eSP.dyH.llN.ryr",  # 具体的なクラス
                "div[data-test-id='pin-description'] span",
                "div[data-test-id='closeup-description'] span",
                "span[data-test-id='description-text']",
                ".X8m.zDA.IZT.eSP.dyH.llN.ryr"
            ]
            
            for selector in description_selectors:
                desc_elements = soup.select(selector)
                for elem in desc_elements:
                    desc_text = elem.get_text(strip=True)
                    if desc_text and len(desc_text) > 10 and desc_text not in descriptions:
                        descriptions.append(desc_text)
            
            # 4. ピンナー情報を抽出
            pinner_names = []
            pinner_selectors = [
                ".X8m.zDA.IZT.eSP.dyH.llN.Kv8",  # 具体的なクラス
                "div[data-test-id='pinner-name']",
                "a[data-test-id='pinner-name']",
                "[data-test-id='pinner-avatar'] + div",
                ".Kv8"  # ピンナー名っぽいクラス
            ]
            
            for selector in pinner_selectors:
                pinner_elements = soup.select(selector)
                for elem in pinner_elements:
                    pinner_text = elem.get_text(strip=True)
                    if pinner_text and len(pinner_text) > 2 and len(pinner_text) < 50 and pinner_text not in pinner_names:
                        pinner_names.append(pinner_text)
            
            # 5. コメント情報を抽出
            comments_info = []
            comment_selectors = [
                "h2.FAo.dyH.c51.X8m.V2L.G1E",  # コメント数ヘッダー
                "[data-test-id='comment-avatar-container'] + div",
                "[data-test-id='author-and-comment-container']",
                "[data-test-id='text-container']",
                "div[class*='comment']"
            ]
            
            for selector in comment_selectors:
                comment_elements = soup.select(selector)
                for elem in comment_elements:
                    comment_text = elem.get_text(strip=True)
                    if comment_text and len(comment_text) > 5 and comment_text not in comments_info:
                        comments_info.append(comment_text)
            
            # 6. 包括的なメインコンテンツエリア抽出
            main_content_areas = []
            comprehensive_selectors = [
                "div.KS5.hs0.un8.C9i.TB_",  # ユーザー指定のdiv
                "[data-test-id='pin-close-up-content']",
                "[data-test-id='closeup-body']",
                "main",
                "article"
            ]
            
            for selector in comprehensive_selectors:
                main_elements = soup.select(selector)
                for elem in main_elements:
                    # 子要素も含めて包括的にテキストを抽出
                    all_text_elements = elem.find_all(text=True)
                    filtered_texts = []
                    for text in all_text_elements:
                        clean_text = text.strip()
                        if clean_text and len(clean_text) > 3:
                            # scriptやstyleタグ内のテキストを除外
                            if text.parent.name not in ['script', 'style', 'noscript']:
                                filtered_texts.append(clean_text)
                    
                    if filtered_texts:
                        area_content = '\n'.join(filtered_texts)
                        if area_content not in main_content_areas and len(area_content) > 50:
                            main_content_areas.append(area_content)
            
            # 7. 結果を構築（ラベルなし、純粋なテキストのみ）
            # ドメインリンクを追加
            if domain_links:
                for domain in domain_links[:3]:  # 最大3つまで
                    result.append(domain)
            
            # タイトルを追加
            if pin_titles:
                for title in pin_titles[:2]:  # 最大2つまで
                    result.append(title)
            
            # 説明文を追加
            if descriptions:
                for desc in descriptions[:3]:  # 最大3つまで
                    result.append(desc)
            
            # ピンナー情報を追加
            if pinner_names:
                for pinner in pinner_names[:2]:  # 最大2つまで
                    result.append(pinner)
            
            # コメント情報を追加
            if comments_info:
                for comment in comments_info[:5]:  # 最大5つまで
                    result.append(comment)
            
            # メインコンテンツエリアの内容を追加
            if main_content_areas:
                for content in main_content_areas[:2]:  # 最大2つまで
                    result.append(content)
            
            # 8. フォールバック: 結果が不十分な場合はより広範囲に抽出
            if len('\n'.join(result)) < 200:
                print(f"Pinterest: 抽出結果が不十分のため、広範囲抽出を実行: {url}")
                
                # 不要な要素を除去
                for unwanted in soup.select('script, style, nav, header, footer, .ad, .advertisement, noscript'):
                    unwanted.decompose()
                
                # bodyの内容を段階的に抽出
                body_element = soup.find('body')
                if body_element:
                    # 大きなdiv要素を探して内容を抽出
                    large_divs = []
                    for div in body_element.find_all('div'):
                        div_text = div.get_text(separator=' ', strip=True)
                        if len(div_text) > 100:
                            large_divs.append((div, len(div_text)))
                    
                    # テキスト量でソート
                    if large_divs:
                        large_divs.sort(key=lambda x: x[1], reverse=True)
                        # 上位2つのdivの内容を取得
                        for div, _ in large_divs[:2]:
                            div_content = div.get_text(separator='\n', strip=True)
                            if div_content and div_content not in result:
                                result.append(div_content[:1000])  # 最大1000文字
            
            # 最終結果の返却
            if result:
                final_result = '\n\n'.join(result)
                print(f"Pinterest包括的抽出成功 (文字数: {len(final_result)}): {url}")
                return final_result
            else:
                print(f"Pinterestから抽出できませんでした: {url}")
                return f"Pinterestからコンテンツを抽出できませんでした: {url}"
                
        except Exception as e:
            print(f"Pinterest処理エラー: {url} - {e}")
            return f"Pinterestページからのテキスト抽出に失敗しました: {url} - エラー: {str(e)}"
        finally:
            if driver:
                driver.quit()
    
    def extract_with_selenium(self, url):
        """Seleniumを使用してページコンテンツを抽出する (失敗時はNoneを返す)"""
        driver = None
        try:
            driver = self.get_driver()
            if not driver:
                print(f"Selenium: ドライバー初期化失敗: {url}")
                return None # エラーメッセージではなくNoneを返す

            driver.get(url)
            time.sleep(3) # JS読み込み待ち

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            # ドメイン取得は extract_main_content 内で行うのでここでは不要
            # domain_match = re.search(r'https?://(?:www\\.)?([^/]+)', url)
            # domain = domain_match.group(1) if domain_match else ""

            # ドメインを渡して extract_main_content を呼び出す
            domain = "" # ドメイン情報を渡す準備 (もし必要なら再度取得)
            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
            if domain_match:
                domain = domain_match.group(1)

            extracted_text = self.extract_main_content(soup, domain) # 失敗時は空文字列

            # extract_main_content が空文字列を返した場合、または短すぎる場合にbody全体を試す
            if not extracted_text or len(extracted_text.strip()) < 100:
                print(f"Selenium: extract_main_content失敗または不十分、body全体を取得試行: {url}")
                # body全体から不要要素除去を試みる
                for tag in soup.select('header, footer, nav, script, style, .header, .footer, .nav, .menu, .sidebar, .ad, .advertisement, .banner, noscript'): # script, style, noscriptも除去
                    tag.decompose()
                body_text = soup.body.get_text(separator='\n', strip=True) if soup.body else None
                # body_textがNoneでなく、かつ元のextracted_textより長ければ更新
                if body_text and (not extracted_text or len(body_text) > len(extracted_text)):
                    extracted_text = body_text

            # 最終的に抽出できたテキストがNoneでなく、空文字列でもなければ返す
            return extracted_text.strip() if extracted_text and extracted_text.strip() else None

        except WebDriverException as e:
            print(f"Selenium WebDriverエラー: {url} - {e}")
            return None # エラーメッセージではなくNoneを返す
        except Exception as e:
            print(f"Selenium抽出中に予期せぬエラー: {url} - {e}")
            return None # エラーメッセージではなくNoneを返す
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    print(f"Seleniumドライバー終了エラー: {e}")

    def extract_main_content(self, soup, domain):
        """
        ドメインに応じてメインコンテンツを抽出する (失敗時は空文字列を返す)
        """
        # 一般的なメインコンテンツのセレクタ（優先順位順）
        main_content_selectors = [
            'main', 'article', '.article', '.post', '.entry', '.content', '#content',
            '.main-content', '.post-content', '.article-content', '.entry-content',
            'section.article', 'div.article', '[itemprop="articleBody"]', '.story-body',
        ]
        
        # ドメイン特有のセレクタのマッピング
        domain_specific_selectors = {
            'news.yahoo.co.jp': ['.article_body', '.highLightSearchTarget'],
            'www.nikkansports.com': ['.articleText'],
            'ja.wikipedia.org': ['#mw-content-text'],
            'number.bunshun.jp': ['.p-article__body'],
            'gendai.media': ['.article-body'],
            'www.oricon.co.jp': ['.full-text'],
            'www.chunichi.co.jp': ['.article-body'],
            'www.sanspo.com': ['.article-header, .article-body', '.article-body', '.article__text', 'article', 'main'],
            # 必要に応じて他のドメインを追加
        }
        
        # ドメイン特有のセレクタがあればそれを試す
        if domain in domain_specific_selectors:
            for selector in domain_specific_selectors[domain]:
                elements = soup.select(selector)
                if elements:
                    return '\n\n'.join([element.get_text(separator='\n', strip=True) for element in elements])
        
        # 一般的なセレクタを試す
        for selector in main_content_selectors:
            elements = soup.select(selector)
            if elements:
                # セレクタが複数見つかった場合、最も長いテキストコンテンツを持つものを選択
                best_element = max(elements, key=lambda x: len(x.get_text(strip=True)), default=None)
                if best_element:
                    # 不要な要素を削除
                    unwanted_selectors = [
                        'header', 'footer', 'nav', 'aside', 'script', 'style', 'noscript',
                        '.related', '.recommend', '.sidebar', '.ad', '.banner', 
                        '.ranking', '.sports', '.entame', '.latest', '.news', '.links', 
                        '.more', '.topics', '.column', '.comment', '.social', '.share',
                        '.breadcrumb', '.pagination', '.tag', '.category'
                    ]
                    for selector in unwanted_selectors:
                        for tag in best_element.select(selector):
                            tag.decompose()
                    main_text = best_element.get_text(separator='\n', strip=True)
                    if main_text: # 空でなければ返す
                        return main_text
        
        # メタ情報（タイトルなど）を抽出 (これは本文ではないので削除)
        # title = soup.title.get_text(strip=True) if soup.title else ""

        # ヒューリスティック: テキスト量が多いブロック要素を探す
        blocks = soup.find_all(['div', 'section', 'article', 'main', 'p']) # pタグも追加
        text_blocks = []

        for block in blocks:
            # ヘッダー、フッター、広告などを除外
            exclude_classes = ['header', 'footer', 'nav', 'sidebar', 'ad', 'banner', 'menu', 'related', 'recommend', 'ranking', 'sports', 'entame', 'latest', 'news', 'links', 'more', 'topics', 'column']
            exclude_tags = ['header', 'footer', 'nav', 'aside', 'script', 'style', 'noscript']
            
            if any(cls in str(block.get('class', [])).lower() for cls in exclude_classes)\
               or block.name in exclude_tags\
               or any(cls in str(block.get('id', '')).lower() for cls in exclude_classes):\
                continue

            text = block.get_text(strip=True)
            if len(text) > 200:  # 短すぎるブロックは除外
                # 親要素にメインコンテンツらしいクラス名があるかチェック (加点)
                score = len(text)
                parent = block.parent
                while parent and parent != soup:
                    if any(cls in str(parent.get('class', [])).lower() for cls in ['content', 'article', 'main', 'post', 'entry', 'body']):
                        score *= 1.5 # メインコンテンツっぽい親がいればスコアアップ
                        break
                    parent = parent.parent
                text_blocks.append((block, text, score))

        # スコアでソートして最大のものを選択
        if text_blocks:
            text_blocks.sort(key=lambda x: x[2], reverse=True)
            # 不要要素を除去してから返す
            best_block_content = text_blocks[0][0]
            unwanted_selectors = [
                'header', 'footer', 'nav', 'aside', 'script', 'style', 'noscript',
                '.related', '.recommend', '.sidebar', '.ad', '.banner', 
                '.ranking', '.sports', '.entame', '.latest', '.news', '.links', 
                '.more', '.topics', '.column', '.comment', '.social', '.share',
                '.breadcrumb', '.pagination', '.tag', '.category'
            ]
            for selector in unwanted_selectors:
                for tag in best_block_content.select(selector):
                    tag.decompose()
            best_text = best_block_content.get_text(separator='\n', strip=True)
            if best_text:
                return best_text

        # 何も見つからなかった場合は、bodyのテキストを返す前に最終チェック
        body = soup.body
        if body:
            # 不要要素を除去してからテキスト取得
            unwanted_selectors = [
                'header', 'footer', 'nav', 'script', 'style', 'aside', 'noscript',
                '.header', '.footer', '.nav', '.menu', '.sidebar', '.ad', '.advertisement', '.banner',
                '.related', '.recommend', '.ranking', '.sports', '.entame', '.latest', '.news', 
                '.links', '.more', '.topics', '.column', '.comment', '.social', '.share',
                '.breadcrumb', '.pagination', '.tag', '.category'
            ]
            for selector in unwanted_selectors:
                for tag in body.select(selector):
                    tag.decompose()
            body_text = body.get_text(separator='\n', strip=True)
            if body_text and len(body_text) > 50: # 短すぎるbodyは無視
                 return body_text # Bodyから取得できれば返す

        # それでもダメならタイトル (最終手段)
        title = soup.title.get_text(strip=True) if soup.title else ""
        if title:
            return title # タイトルがあれば返す

        return "" # 最終的に何も見つからなければ空文字列
    
    def extract_texts_from_urls(self, urls_file):
        """
        ファイルからURLのリストを読み込み、並列処理でテキストを抽出する
        
        Parameters:
        urls_file (str): URLのリストが含まれるファイルのパス
        
        Returns:
        list: 各URLの抽出結果のリスト [(url, text), ...]
        """
        # URLリストの読み込み
        with open(urls_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        results = []
        
        # 並列処理
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            future_to_url = {executor.submit(self.extract_text_from_url, url): url for url in urls}
            
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    text = future.result(timeout=600)  # 10分タイムアウト
                    results.append((url, text))
                    print(f"完了: {url}")
                except concurrent.futures.TimeoutError:
                    print(f"タイムアウト（20分）: {url}")
                    results.append((url, "（テキスト抽出タイムアウト）"))
                except Exception as e:
                    print(f"エラー: {url} - {e}")
                    results.append((url, f"エラーが発生しました: {e}"))
        
        # URLの元の順序を保持
        sorted_results = []
        for url in urls:
            for result_url, text in results:
                if url == result_url:
                    sorted_results.append((url, text))
                    break
        
        return sorted_results
    
    def detect_browser_errors(self, text, url):
        """
        ブラウザエラーメッセージを検出する
        
        Parameters:
        text (str): 検出対象のテキスト
        url (str): 対応するURL
        
        Returns:
        bool: エラーメッセージが検出された場合True
        """
        if not text:
            return False
        
        # config.iniからエラーパターンを読み込む
        config = configparser.ConfigParser()
        config_path = 'config.ini'
        
        try:
            if os.path.exists(config_path):
                config.read(config_path, encoding='utf-8')
                
                # ERROR_PATTERNSセクションが存在し、機能が有効かチェック
                if 'ERROR_PATTERNS' in config:
                    if not config.getboolean('ERROR_PATTERNS', 'enabled', fallback=True):
                        return False  # 機能が無効の場合は検出しない
                    
                    # ブラウザエラーパターンを取得
                    browser_errors = config.get('ERROR_PATTERNS', 'browser_errors', fallback='')
                    custom_patterns = config.get('ERROR_PATTERNS', 'custom_patterns', fallback='')
                    
                    # カンマ区切りで分割してパターンリストを作成
                    error_patterns = []
                    if browser_errors:
                        error_patterns.extend([pattern.strip() for pattern in browser_errors.split(',') if pattern.strip()])
                    if custom_patterns:
                        error_patterns.extend([pattern.strip() for pattern in custom_patterns.split(',') if pattern.strip()])
                    
                    # テキストに対してパターンマッチング
                    for pattern in error_patterns:
                        if pattern in text:
                            print(f"エラーパターン検出: '{pattern}' in URL: {url}")
                            return True
                            
        except (configparser.Error, ValueError) as e:
            print(f"config.ini読み込みエラー: {e}")
        
        return False
    
    def backup_url_file(self, url_file):
        """
        URLファイルのバックアップを作成する
        
        Parameters:
        url_file (str): バックアップ対象のファイルパス
        
        Returns:
        str: バックアップファイルのパス
        """
        import shutil
        from datetime import datetime
        
        if not os.path.exists(url_file):
            print(f"警告: バックアップ対象ファイルが存在しません: {url_file}")
            return None
        
        # config.iniでバックアップが有効かチェック
        config = configparser.ConfigParser()
        config_path = 'config.ini'
        
        try:
            if os.path.exists(config_path):
                config.read(config_path, encoding='utf-8')
                if 'ERROR_PATTERNS' in config:
                    if not config.getboolean('ERROR_PATTERNS', 'backup_enabled', fallback=True):
                        print(f"情報: バックアップが無効化されています: {url_file}")
                        return None
        except (configparser.Error, ValueError) as e:
            print(f"config.ini読み込みエラー: {e}")
        
        # バックアップファイル名を生成（タイムスタンプ付き）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"{url_file}.backup_{timestamp}"
        
        try:
            shutil.copy2(url_file, backup_file)
            print(f"バックアップ作成: {url_file} -> {backup_file}")
            return backup_file
        except Exception as e:
            print(f"バックアップ作成エラー: {e}")
            return None
    
    def remove_url_from_list(self, url, url_file):
        """
        URLリストから指定URLを除外する
        
        Parameters:
        url (str): 除外するURL
        url_file (str): URLリストファイルのパス
        
        Returns:
        bool: 成功した場合True
        """
        if not os.path.exists(url_file):
            print(f"警告: URLリストファイルが存在しません: {url_file}")
            return False
        
        try:
            # バックアップを作成
            backup_file = self.backup_url_file(url_file)
            if backup_file is None and os.path.exists('config.ini'):
                # バックアップが無効でない限り、失敗はエラー
                config = configparser.ConfigParser()
                config.read('config.ini', encoding='utf-8')
                if 'ERROR_PATTERNS' in config and config.getboolean('ERROR_PATTERNS', 'backup_enabled', fallback=True):
                    print(f"エラー: バックアップ作成に失敗したため、URL除外を中止します: {url_file}")
                    return False
            
            # ファイルを読み込み、指定URLを除外
            with open(url_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 指定URLを除外してフィルタリング
            filtered_lines = []
            url_removed = False
            
            for line in lines:
                line_url = line.strip()
                if line_url != url:
                    filtered_lines.append(line)
                else:
                    url_removed = True
                    print(f"URLを除外: {url} from {url_file}")
            
            if not url_removed:
                print(f"情報: 除外対象URLが見つかりませんでした: {url} in {url_file}")
                return False
            
            # ファイルを更新
            with open(url_file, 'w', encoding='utf-8') as f:
                f.writelines(filtered_lines)
            
            print(f"URLリスト更新完了: {url_file}")
            return True
            
        except Exception as e:
            print(f"URL除外エラー: {e}")
            return False
    
    def save_results(self, results, output_file="extracted_texts.txt", source_url_file=None):
        """
        抽出結果をファイルに保存する。ファイルの先頭にはヘッダーと元のURLリストを追加する。
        テキスト抽出に失敗したURLは除外する。

        Parameters:
        results (list): 抽出結果のリスト [(url, text), ...]
        output_file (str): 出力ファイル名
        source_url_file (str): 処理元のURLファイルパス
        """
        output_path = os.path.join(self.output_dir, output_file)

        # テキスト抽出に失敗したURLを除外
        filtered_results = []
        excluded_urls = []
        error_detected_urls = []  # エラーパターンで検出されたURL
        
        for url, text in results:
            is_failure = False # 失敗フラグを初期化
            
            # textがNoneでないことを確認
            if text is None:
                is_failure = True
                print(f"情報: URLを除外します。理由: 抽出結果がNoneです。 URL: {url}")
            else:
                # 新しいエラーパターン検出機能を使用
                if self.detect_browser_errors(text, url):
                    is_failure = True
                    error_detected_urls.append(url)
                    print(f"情報: URLを除外します。理由: ブラウザエラーパターンが検出されました。 URL: {url}")
                
                # 既存のエラーメッセージ検出ロジックも継続（後方互換性のため）
                if not is_failure:
                    # 完全一致でチェックする定型エラーメッセージのテンプレート
                    # URLを含むもの
                    failure_templates_with_url = [
                        "PDFからテキストを抽出できませんでした: {}",
                        "PDFファイルのダウンロードに失敗しました: {}",
                        "PDFファイルの処理中にエラーが発生しました: {}",
                        "すべての抽出方法でテキストを抽出できませんでした: {}",
                        "特定ドメインの抽出に失敗しました (Jina & Selenium): {}",
                        "Yahoo画像検索の抽出に失敗しました (Jina & Selenium): {}",
                        "ドライバーの初期化に失敗したため、{} からテキストを抽出できませんでした。",
                        "X (Twitter) ページからのテキスト抽出に失敗しました: {}",
                        "Instagramポストからテキストが見つかりませんでした: {}",
                        "Instagramページからのテキスト抽出に失敗しました: {}",
                        "Yahoo知恵袋ページからのテキスト抽出に失敗しました: {}",
                        "知恵袋からコンテンツを抽出できませんでした: {}",
                        "YouTubeページからのテキスト抽出に失敗しました: {}",
                    ]
                    # URLを含まないもの、または可変部分を含むもの
                    failure_patterns_prefix = [
                        "エラーが発生しました:", # concurrent.futures からのエラーメッセージ
                    ]

                    # URLを含むテンプレートとの完全一致をチェック
                    for template in failure_templates_with_url:
                        expected_error_message = template.format(url)
                        if text == expected_error_message:
                            is_failure = True
                            print(f"情報: URLを除外します。理由: 完全一致エラーメッセージ「{template.replace('{}', url)}」。 URL: {url}")
                            break
                    
                    # URLを含まないパターンとの前方一致をチェック（タイムアウトメッセージは除外しない）
                    if not is_failure:
                        for prefix in failure_patterns_prefix:
                            if text.startswith(prefix):
                                is_failure = True
                                print(f"情報: URLを除外します。理由: 前方一致エラーメッセージ「{prefix}...」。 URL: {url}")
                                break
                    
                    # タイムアウトメッセージは除外対象外
                    if text == "（テキスト抽出タイムアウト）":
                        is_failure = False

            # 失敗したURLを除外
            if is_failure:
                excluded_urls.append(url)
            else:
                filtered_results.append((url, text))
        
        # 除外したURLの数をログに出力
        if excluded_urls:
            print(f"テキスト抽出に失敗した {len(excluded_urls)} 件のURLを出力から除外しました")
            
            # エラーパターンで検出されたURLをURLリストからも除外
            if error_detected_urls and source_url_file:
                print(f"エラーパターンで検出された {len(error_detected_urls)} 件のURLをURLリストからも除外します")
                for error_url in error_detected_urls:
                    try:
                        success = self.remove_url_from_list(error_url, source_url_file)
                        if success:
                            print(f"URLリストから除外完了: {error_url}")
                        else:
                            print(f"URLリストから除外失敗: {error_url}")
                    except Exception as e:
                        print(f"URLリスト除外エラー: {error_url} - {e}")
            
        # 実際に保存するのはフィルタリング後の結果
        results = filtered_results

        header_text = ""
        url_list_to_include = ""
        url_list_path_to_read = None # 読み込むURLリストのパス

        # source_url_file が None でない場合のみ処理
        if source_url_file:
            source_filename = os.path.basename(source_url_file)

            # google_urls.txt の場合
            if 'google_urls.txt' in source_filename:
                header_text = "google========================================================\n\n" # \n に修正
                url_list_path_to_read = source_url_file # 自身のパスを使用

            # yahoo_urls.txt の場合
            elif 'yahoo_urls.txt' in source_filename:
                header_text = "yahoo=========================================================\n\n" # \n に修正
                url_list_path_to_read = source_url_file # 自身のパスを使用

            # ヘッダー対象ファイルの場合、URLリストを読み込む
            if url_list_path_to_read:
                try:
                    # 指定されたURLリストファイルを読む
                    with open(url_list_path_to_read, 'r', encoding='utf-8') as url_f:
                        url_list_content = url_f.readlines()
                    
                    # 除外したURLをURLリストからも除外
                    if excluded_urls:
                        filtered_url_list = []
                        for line in url_list_content:
                            line = line.strip()
                            if line and not any(excluded_url == line for excluded_url in excluded_urls):
                                filtered_url_list.append(line)
                        
                        # 除外結果をログに出力（URLリストからも除外した場合）
                        if len(filtered_url_list) < len(url_list_content):
                            print(f"URLリストからも {len(url_list_content) - len(filtered_url_list)} 件のURLを除外しました")
                        
                        url_list_to_include = "\n".join(filtered_url_list)
                    else:
                        # 除外するURLがなければ、そのまま全部を含める
                        url_list_to_include = "".join(url_list_content).rstrip()
                    
                    url_list_to_include += "\n\n\n\n\n" # 5行改行を追加 (\n に修正)
                except FileNotFoundError:
                    print(f"エラー: ヘッダー用のURLリストファイルが見つかりません: {url_list_path_to_read}")
                    url_list_to_include = f"エラー: {url_list_path_to_read} が見つかりません。\n\n\n\n\n" # \n に修正
            else:
                 # googleでもyahooでもない場合
                 print(f"情報: {source_url_file} はヘッダー追加の対象外です。")
                 # ヘッダーなしで続行
        else:
             # source_url_file が None の場合
             print(f"警告: source_url_fileが指定されませんでした。ヘッダーは追加されません。")

        with open(output_path, 'w', encoding='utf-8') as f:
            # ヘッダーとURLリストを書き込む
            if header_text:
                f.write(header_text)
            if url_list_to_include:
                f.write(url_list_to_include)

            # 抽出結果を書き込む
            for i, (url, text) in enumerate(results):
                f.write(f"{url}\n") # \n に修正
                f.write(f"{text}\n") # \n に修正

                # 最後の項目でなければ2行の空行を追加
                if i < len(results) - 1:
                    f.write("\n\n") # \n に修正

        print(f"結果を {output_path} に保存しました。")
        print(f"保存した結果: {len(results)} 件のURL（除外: {len(excluded_urls)} 件）")

        return output_path

def main():
    """メイン関数"""
    import argparse
    import os # os モジュールをインポート
    import configparser # configparserをここでもインポート（関数スコープ）

    parser = argparse.ArgumentParser(description='URLからメインコンテンツを抽出するツール')
    # '--urls' を複数指定可能にし、デフォルト値を設定
    parser.add_argument(
        '--urls',
        nargs='+',
        default=['urls/google_urls.txt', 'urls/yahoo_urls.txt'],
        help='処理するURLリストのファイルパス（複数指定可）。指定がない場合はデフォルトのリスト（google_urls.txt, yahoo_urls.txt）を処理します。'
    )
    # '--output' を出力ディレクトリ指定 '--output-dir' に変更
    parser.add_argument('--output-dir', default='outputs', help='出力ディレクトリのパス')
    parser.add_argument('--workers', type=int, default=None, help='並列処理に使用するワーカー数')
    # --cpu-ratio のデフォルトをNoneのままにする
    parser.add_argument('--cpu-ratio', type=float, default=None, help='CPUコア数に対する使用率（0.0〜1.0）')
    args = parser.parse_args()

    # CPU情報の表示
    cpu_count = os.cpu_count()
    print(f"CPUコア数: {cpu_count}")

    # --- CPU使用率の決定ロジック ---
    # 1. コマンドライン引数 --cpu-ratio が最優先
    if args.cpu_ratio is not None:
        if not (0 < args.cpu_ratio <= 1):
            print("エラー: コマンドライン引数 --cpu-ratio は0より大きく1以下の値を指定してください")
            return
        print(f"コマンドライン引数からCPU使用率 {args.cpu_ratio} を使用します。")
    # 2. --cpu-ratio が指定されていなければ config.ini を試す
    elif args.workers is None: # --workers が指定されている場合は cpu-ratio は無視されるため、この条件を追加
        config = configparser.ConfigParser()
        config_path = 'config.ini'
        cpu_ratio_from_config = None
        try:
            if os.path.exists(config_path):
                config.read(config_path, encoding='utf-8')
                if 'Settings' in config and 'cpu_ratio' in config['Settings']:
                    cpu_ratio_from_config = config.getfloat('Settings', 'cpu_ratio')
                    if 0 < cpu_ratio_from_config <= 1:
                        args.cpu_ratio = cpu_ratio_from_config
                        print(f"{config_path} からCPU使用率 {args.cpu_ratio} を読み込みました。")
                    else:
                        print(f"警告: {config_path} の cpu_ratio ({cpu_ratio_from_config}) が無効な値です。デフォルト値(1.0)を使用します。")
                        args.cpu_ratio = 1.0 # 無効な値の場合のデフォルト
                else:
                    print(f"警告: {config_path} に [Settings] セクションまたは cpu_ratio が見つかりません。デフォルト値(1.0)を使用します。")
                    args.cpu_ratio = 1.0 # 設定がない場合のデフォルト
            else:
                print(f"警告: {config_path} が見つかりません。デフォルト値(1.0)を使用します。")
                args.cpu_ratio = 1.0 # ファイルがない場合のデフォルト
        except (configparser.Error, ValueError) as e:
            print(f"警告: {config_path} の読み込み中にエラーが発生しました ({e})。デフォルト値(1.0)を使用します。")
            args.cpu_ratio = 1.0 # エラー発生時のデフォルト

    # 出力ディレクトリの取得 (WebTextExtractorの初期化で使う)
    output_dir = args.output_dir

    # 抽出器の初期化
    extractor = WebTextExtractor(output_dir=output_dir, num_workers=args.workers, cpu_ratio=args.cpu_ratio)
    print(f"使用並列処理数: {extractor.num_workers}")

    total_processed_count = 0
    processed_files = []

    # 指定された各URLファイルを処理
    for url_file_path in args.urls:
        # Windowsのパス区切り文字 \ を / に置換（一貫性のため）
        # normpathを使う方がより堅牢
        url_file_path = os.path.normpath(url_file_path) # パスを正規化

        if not os.path.exists(url_file_path):
            print(f"警告: URLファイルが見つかりません: {url_file_path} スキップします。")
            continue

        print(f"\n--- URLリストの処理開始: {url_file_path} ---")
        # 出力ファイル名を生成 (例: google_urls.txt -> google_urls_extracted.txt)
        output_file_name = os.path.basename(url_file_path).replace('.txt', '_extracted.txt')

        try:
            results = extractor.extract_texts_from_urls(url_file_path)
            if results: # 結果がある場合のみ保存
                # save_resultsに出力ファイル名と元のURLファイルパスを渡す
                output_path = extractor.save_results(results, output_file_name, source_url_file=url_file_path) # source_url_fileを追加
                print(f"処理完了: {url_file_path} -> {output_path}")
                print(f"{len(results)} 件のURLを処理しました。")
                total_processed_count += len(results)
                processed_files.append(output_path)
            else:
                 print(f"処理完了: {url_file_path} - 処理対象のURLが見つからなかったか、すべて失敗しました。")

        except FileNotFoundError:
             print(f"エラー: URLファイルが見つかりません: {url_file_path}")
        except Exception as e:
             print(f"エラー: {url_file_path} の処理中に予期せぬエラーが発生しました: {e}")


    print(f"\n--- 全ての処理が完了しました ---")
    if processed_files:
        print(f"合計 {total_processed_count} 件のURLを処理し、以下のファイルに出力しました:")
        for file_path in processed_files:
            print(f"- {file_path}")
    else:
        print("処理されたファイルはありませんでした。")
    # 処理完了後に自動で終了（キー入力待ちを削除）

if __name__ == "__main__":
    main()