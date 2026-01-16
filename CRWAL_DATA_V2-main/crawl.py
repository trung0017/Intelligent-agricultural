import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import json
import time
from urllib.parse import urljoin, urlparse
import os
from pathlib import Path

class WebCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def crawl_with_requests(self, url: str) -> dict:
        """Crawl bằng requests + BeautifulSoup (nhanh hơn)"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Xóa các thẻ không cần thiết
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
                tag.decompose()
            
            # Tìm tiêu đề
            title = ""
            if soup.find('h1'):
                title = soup.find('h1').get_text().strip()
            elif soup.find('title'):
                title = soup.find('title').get_text().strip()
            
            # Tìm nội dung chính
            content_selectors = [
                'article', '.content', '.post-content', '.entry-content',
                '.article-body', '.story-body', '.post-body', 'main'
            ]
            
            content = ""
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(separator='\n').strip()
                    break
            
            # Nếu không tìm thấy, lấy toàn bộ body
            if not content:
                body = soup.find('body')
                if body:
                    content = body.get_text(separator='\n').strip()
            
            return {
                'url': url,
                'title': title,
                'content': content,
                'method': 'requests',
                'timestamp': time.time()
            }
            
        except Exception as e:
            print(f"Lỗi khi crawl {url}: {e}")
            return None
    
    def crawl_with_playwright(self, url: str) -> dict:
        """Crawl bằng Playwright (cho trang có JavaScript)"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Chặn hình ảnh và CSS để tăng tốc
                page.route("**/*.{png,jpg,jpeg,gif,svg,css}", lambda route: route.abort())
                
                page.goto(url, wait_until='networkidle', timeout=30000)
                
                # Đợi nội dung load
                page.wait_for_timeout(2000)
                
                # Lấy tiêu đề
                title = page.title()
                h1 = page.query_selector('h1')
                if h1:
                    title = h1.inner_text().strip()
                
                # Xóa các element không cần thiết
                page.evaluate("""
                    const elementsToRemove = document.querySelectorAll('script, style, nav, footer, header, aside, iframe, .advertisement, .ads');
                    elementsToRemove.forEach(el => el.remove());
                """)
                
                # Lấy nội dung
                content_selectors = [
                    'article', '.content', '.post-content', '.entry-content',
                    '.article-body', '.story-body', '.post-body', 'main'
                ]
                
                content = ""
                for selector in content_selectors:
                    element = page.query_selector(selector)
                    if element:
                        content = element.inner_text().strip()
                        break
                
                if not content:
                    body = page.query_selector('body')
                    if body:
                        content = body.inner_text().strip()
                
                browser.close()
                
                return {
                    'url': url,
                    'title': title,
                    'content': content,
                    'method': 'playwright',
                    'timestamp': time.time()
                }
                
        except Exception as e:
            print(f"Lỗi khi crawl với Playwright {url}: {e}")
            return None
    
    def crawl_url(self, url: str, use_playwright: bool = False) -> dict:
        """Crawl một URL"""
        print(f"Đang crawl: {url}")
        
        if use_playwright:
            result = self.crawl_with_playwright(url)
        else:
            result = self.crawl_with_requests(url)
            
        if result and len(result['content']) < 500:
            print("Nội dung quá ngắn, thử lại với Playwright...")
            result = self.crawl_with_playwright(url)
            
        return result
    
    def save_raw_content(self, data: dict, output_dir: str = "raw_content"):
        """Lưu nội dung thô"""
        Path(output_dir).mkdir(exist_ok=True)
        
        # Tạo tên file từ URL
        parsed_url = urlparse(data['url'])
        filename = f"{parsed_url.netloc}_{int(data['timestamp'])}.json"
        filename = filename.replace(':', '_').replace('/', '_')
        
        filepath = Path(output_dir) / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Đã lưu: {filepath}")
        return filepath

def main():
    """Chạy crawler từ command line"""
    crawler = WebCrawler()
    
    print("=== WikiNongSan Web Crawler ===")
    url = input("Nhập URL để crawl: ").strip()
    
    if url:
        use_playwright = input("Sử dụng Playwright? (y/n): ").lower() == 'y'
        result = crawler.crawl_url(url, use_playwright)
        if result:
            filepath = crawler.save_raw_content(result)
            print(f"\nTiêu đề: {result['title']}")
            print(f"Độ dài nội dung: {len(result['content'])} ký tự")
            print(f"Đã lưu vào: {filepath}")
        else:
            print("Không thể crawl URL này")
    else:
        print("Vui lòng nhập URL hợp lệ")

if __name__ == "__main__":
    main()