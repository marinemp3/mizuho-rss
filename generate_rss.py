#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import random
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# タイムゾーン設定（中国時間=UTC+8）
CHINA_TZ = timezone(timedelta(hours=8))

# ユーザーエージェントのリスト
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]

def clean_title(title):
    """
    タイトルからPDFファイルサイズ情報などを除去する
    例: "CHINA BUSINESS QUARTERY＜2026年7-9月＞(PDF/18998KB)" → "CHINA BUSINESS QUARTERY＜2026年7-9月＞"
    """
    if not title:
        return title
    
    # (PDF/数字KB) または (PDF/数字MB) を除去
    cleaned = re.sub(r'\(PDF/\d+(?:KB|MB)\)', '', title)
    
    # 末尾の空白を除去
    cleaned = cleaned.strip()
    
    return cleaned

def get_china_time():
    """中国時間（UTC+8）の現在時刻を取得"""
    return datetime.now(CHINA_TZ)

def fetch_html_with_selenium(url):
    """Seleniumを使用してHTMLを取得"""
    try:
        print("Seleniumでアクセスを開始します...")
        
        # Chromeオプションの設定
        options = Options()
        options.add_argument('--headless')  # ヘッドレスモード（ブラウザを表示しない）
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # ランダムなユーザーエージェントを設定
        user_agent = random.choice(USER_AGENTS)
        options.add_argument(f'--user-agent={user_agent}')
        
        # その他の設定
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-images')
        options.add_argument('--disable-javascript')  # JavaScriptを無効にする（軽量化）
        
        print(f"Chromeドライバーを起動中... (ユーザーエージェント: {user_agent[:50]}...)")
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        
        # まずトップページにアクセス（セッション確立）
        print("トップページにアクセスしてセッションを確立...")
        driver.get('https://www.mizuhobank.co.jp/')
        time.sleep(random.uniform(2, 4))
        
        # 目的のページにアクセス
        print(f"メインページにアクセス: {url}")
        driver.get(url)
        
        # ページ読み込み待機（テーブルが表示されるまで待つ）
        wait = WebDriverWait(driver, 20)
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
            print("テーブルの読み込みを確認しました")
        except:
            print("テーブルの読み込み待機中にタイムアウトしましたが、続行します")
        
        # 追加の待機時間
        time.sleep(random.uniform(3, 5))
        
        # ページソースを取得
        html = driver.page_source
        driver.quit()
        
        print("HTMLの取得に成功しました")
        return BeautifulSoup(html, 'html.parser')
        
    except Exception as e:
        print(f"Seleniumエラー: {e}")
        return None

def parse_reports(soup):
    """HTMLからレポート情報を抽出"""
    reports = []
    
    if not soup:
        return reports
    
    # テーブルを探す
    table = None
    
    # 方法1: class="type1"
    table = soup.find('table', class_='type1')
    
    # 方法2: テーブル内に「タイトル」「掲載日」を含むthがあるか
    if not table:
        print("'type1'クラスのテーブルが見つかりません。他のテーブルを探索します...")
        tables = soup.find_all('table')
        for t in tables:
            th_texts = t.find_all('th')
            for th in th_texts:
                text = th.get_text(strip=True)
                if 'タイトル' in text or '掲載日' in text:
                    table = t
                    break
            if table:
                break
    
    if not table:
        print("テーブルが見つかりませんでした")
        return parse_reports_fallback(soup)
    
    tbody = table.find('tbody')
    if not tbody:
        tbody = table
    
    rows = tbody.find_all('tr')
    print(f"{len(rows)}行のデータを検出しました")
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 3:
            title_cell = cells[0]
            title_link = title_cell.find('a')
            
            if not title_link:
                continue
            
            # タイトルを取得してクリーンアップ
            raw_title = title_link.get_text(strip=True)
            title = clean_title(raw_title)
            
            pdf_url = title_link.get('href')
            
            if pdf_url:
                if not pdf_url.startswith('http'):
                    pdf_url = urljoin('https://www.mizuhobank.co.jp', pdf_url)
            else:
                continue
            
            date_cell = cells[1]
            date_text = date_cell.get_text(strip=True)
            
            summary_cell = cells[2]
            summary = summary_cell.get_text(strip=True)
            
            pub_date = parse_date(date_text)
            
            reports.append({
                'title': title,
                'pdf_url': pdf_url,
                'date': date_text,
                'pub_date': pub_date,
                'summary': summary[:200] + '...' if len(summary) > 200 else summary
            })
    
    return reports

def parse_reports_fallback(soup):
    """テーブルが見つからない場合のフォールバック処理"""
    reports = []
    
    # PDFリンクを全て探す
    pdf_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
    
    for link in pdf_links:
        # タイトルを取得してクリーンアップ
        raw_title = link.get_text(strip=True)
        title = clean_title(raw_title)
        
        pdf_url = link.get('href')
        if pdf_url and not pdf_url.startswith('http'):
            pdf_url = urljoin('https://www.mizuhobank.co.jp', pdf_url)
        
        # 日付情報を探す
        parent = link.parent
        date_text = ""
        for _ in range(5):
            if parent:
                text = parent.get_text(strip=True)
                date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
                if date_match:
                    date_text = date_match.group(0)
                    break
                parent = parent.parent
        
        pub_date = parse_date(date_text) if date_text else datetime.now(CHINA_TZ)
        
        reports.append({
            'title': title,
            'pdf_url': pdf_url,
            'date': date_text or '日付不明',
            'pub_date': pub_date,
            'summary': ''
        })
    
    return reports

def parse_date(date_text):
    """日付文字列をdatetimeオブジェクトに変換（タイムゾーン情報付き）"""
    try:
        date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_text)
        if date_match:
            year = int(date_match.group(1))
            month = int(date_match.group(2))
            day = int(date_match.group(3))
            dt = datetime(year, month, day, tzinfo=CHINA_TZ)
            return dt
    except:
        pass
    return datetime.now(CHINA_TZ)

def generate_rss(reports, output_path='feed.xml'):
    """RSSフィードを生成"""
    fg = FeedGenerator()
    fg.title('CHINA BUSINESS QUARTERLY - みずほ銀行')
    fg.description('みずほ銀行が提供する中国経済・ビジネスに関する最新レポートのRSSフィードです。')
    fg.link(href='https://www.mizuhobank.co.jp/corporate/world/info/cndb/economics/monthly/index.html', rel='alternate')
    fg.link(href='https://your-github-username.github.io/mizuhocbq-rss/feed.xml', rel='self')
    fg.language('ja')
    
    if reports:
        latest_date = max(r['pub_date'] for r in reports)
        if latest_date.tzinfo is None:
            latest_date = latest_date.replace(tzinfo=CHINA_TZ)
        fg.lastBuildDate(latest_date)
    
    for report in reports:
        fe = fg.add_entry()
        fe.title(report['title'])  # クリーンアップされたタイトルを使用
        fe.link(href=report['pdf_url'], rel='alternate')
        fe.description(report['summary'])
        
        pub_date = report['pub_date']
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=CHINA_TZ)
        fe.pubDate(pub_date)
        
        fe.guid(report['pdf_url'], permalink=True)
        fe.author({'name': 'みずほ銀行'})
    
    rss_str = fg.rss_str(pretty=True)
    
    with open(output_path, 'wb') as f:
        f.write(rss_str)
    
    print(f"RSSフィードを生成しました: {output_path}")
    print(f"件数: {len(reports)}")
    
    # 最初の5件のタイトルを表示（確認用）
    print("\n--- タイトルサンプル（最初の5件） ---")
    for i, report in enumerate(reports[:5]):
        print(f"{i+1}. {report['title']}")

def main():
    print("=== CHINA BUSINESS QUARTERLY RSS 生成ツール (Selenium版) ===")
    print(f"実行時刻: {datetime.now(CHINA_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    url = 'https://www.mizuhobank.co.jp/corporate/world/info/cndb/economics/monthly/index.html'
    
    # SeleniumでHTMLを取得
    soup = fetch_html_with_selenium(url)
    
    if not soup:
        print("HTMLの取得に失敗しました。終了します。")
        return
    
    # レポート情報を抽出
    reports = parse_reports(soup)
    
    if not reports:
        print("レポートが見つかりませんでした。終了します。")
        return
    
    print(f"{len(reports)}件のレポートを検出しました")
    
    # RSSフィードを生成
    generate_rss(reports, 'feed.xml')
    
    print("=== 完了 ===")

if __name__ == "__main__":
    main()
