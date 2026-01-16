#!/usr/bin/env python3
"""
WikinongSang Multi-Source Crawler
Thu thập nội dung từ nhiều trang web và tổng hợp thành bài viết wiki hoàn chỉnh
"""

import os
import json
import time
from pathlib import Path
from crawl import WebCrawler
from clean_text import TextCleaner

def multi_source_crawler():
    """Thu thập và tổng hợp nội dung từ nhiều trang web"""
    
    print("🌐 === WIKINONGSANG MULTI-SOURCE CRAWLER ===")
    print()
    
    # Khởi tạo các công cụ
    crawler = WebCrawler()
    cleaner = TextCleaner()
    
    print("🔧 Kiểm tra hệ thống...")
    print(f"🔗 Ollama URL: {cleaner.ollama_url}")
    
    # Kiểm tra Ollama
    if cleaner.test_ollama_connection():
    
        ai_available = True
    else:
        print("⚠️ Ollama chưa chạy - sẽ dùng làm sạch cơ bản")
        ai_available = False
    
    print()
    
    # Nhập URLs từ người dùng
    print("📝 Nhập các URL để crawl (tối thiểu 2, tối đa 5 URL):")
    print("💡 Gợi ý: Chọn các bài viết cùng chủ đề để có kết quả tốt nhất")
    print()
    
    urls = []
    
    while len(urls) < 5:
        url = input(f"URL {len(urls)+1} (Enter để kết thúc nếu đã có ít nhất 1 URL): ").strip()
        
        if not url:
            if len(urls) >= 1:
                break
            else:
                print("❌ Cần ít nhất 1 URL để thu thập!")
                continue
        
        if url.startswith('http://') or url.startswith('https://'):
            urls.append(url)

        else:
            print("❌ URL không hợp lệ! Phải bắt đầu bằng http:// hoặc https://")
    
    print(f"\n📋 Sẽ crawl {len(urls)} trang:")
    for i, url in enumerate(urls, 1):
        print(f"  {i}. {url}")
    
    confirm = input("\nTiếp tục? (y/n): ").lower()
    if confirm != 'y':
        print("❌ Đã hủy!")
        return
    
    print()
    
    # Bước 1: Crawl nội dung thật
    print("📡 BƯỚC 1: Thu thập nội dung từ web")
    print("-" * 50)
    
    crawled_data = []
    
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] Đang crawl: {url}")
        
        try:
            # Thử crawl bằng requests trước
            result = crawler.crawl_url(url, use_playwright=False)
            
            # Nếu nội dung quá ngắn, thử lại với Playwright
            if result and len(result['content']) < 500:
                print("  📄 Nội dung ngắn, thử lại với Playwright...")
                result = crawler.crawl_url(url, use_playwright=True)
            
            if result:
                crawled_data.append(result)
                print(f"  ✅ Thành công: {result['title'][:50]}...")

                
                # Lưu file thô
                raw_file = crawler.save_raw_content(result)
                print(f"  💾 Đã lưu: {raw_file}")
            else:
                print(f"  ❌ Không thể crawl {url}")
            
        except Exception as e:
            print(f"  ❌ Lỗi crawl {url}: {e}")
        
        # Nghỉ giữa các lần crawl
        if i < len(urls):
            print("  ⏳ Nghỉ 3 giây...")
            time.sleep(3)
    
    if not crawled_data:
        print("\n❌ Không crawl được trang nào! Vui lòng kiểm tra URLs.")
        return
    
    print(f"\n✅ Đã crawl thành công {len(crawled_data)}/{len(urls)} trang")
    
    # Bước 2: Tổng hợp nội dung
    print("\n🔄 BƯỚC 2: Tổng hợp nội dung")
    print("-" * 50)
    
    # Tạo tiêu đề tổng hợp
    topic = input("Nhập chủ đề chính cho bài viết tổng hợp: ").strip()
    if not topic:
        topic = "Tổng hợp thông tin nông nghiệp"
    
    # Tổng hợp nội dung
    combined_content = ""
    sources = []
    
    for i, data in enumerate(crawled_data, 1):
        combined_content += f"\n\n## Nguồn {i}: {data['title']}\n\n"
        combined_content += data['content'][:2000]  # Giới hạn độ dài
        if len(data['content']) > 2000:
            combined_content += "\n\n[...nội dung đã được rút gọn...]"
        
        sources.append({
            'title': data['title'],
            'url': data['url']
        })
    
    print(f"📝 Đã tổng hợp {len(crawled_data)} nguồn")
    print(f"📊 Tổng độ dài: {len(combined_content)} ký tự")
    
    # Bước 3: Làm sạch và tối ưu bằng AI
    print("\n🤖 BƯỚC 3: Làm sạch và tối ưu nội dung")
    print("-" * 50)
    
    if ai_available:
        print("🔄 Đang xử lý bằng AI...")
        
        # Prompt đặc biệt cho tổng hợp
        synthesis_prompt = f"""
Bạn là chuyên gia viết bài về nông nghiệp. Hãy tổng hợp và viết lại nội dung sau thành một bài viết wiki hoàn chỉnh về chủ đề "{topic}".

YÊU CẦU:
1. Tạo một bài viết mạch lạc, có cấu trúc rõ ràng
2. Loại bỏ thông tin trùng lặp giữa các nguồn
3. Tổng hợp thông tin từ nhiều nguồn thành nội dung thống nhất
4. Sử dụng định dạng Markdown với tiêu đề, danh sách, bảng biểu
5. Giữ lại thông tin quan trọng, loại bỏ quảng cáo
6. Viết bằng tiếng Việt, phong cách wiki chuyên nghiệp
7. Thêm các phần: Giới thiệu, Nội dung chính, Kết luận

NỘI DUNG CẦN TỔNG HỢP:
{combined_content[:4000]}

BÀI VIẾT WIKI HOÀN CHỈNH:
"""
        
        try:
            synthesized_content = cleaner.call_ollama(synthesis_prompt, max_tokens=3000)
            
            if synthesized_content:
                print("✅ AI đã tổng hợp thành công")
                final_content = synthesized_content
                method = "ai_synthesis"
            else:
                print("⚠️ AI không phản hồi, sử dụng tổng hợp cơ bản")
                final_content = cleaner.clean_raw_text(combined_content)
                method = "basic_synthesis"
                
        except Exception as e:
            print(f"❌ Lỗi AI: {e}")
            final_content = cleaner.clean_raw_text(combined_content)
            method = "basic_synthesis"
    else:
        print("🔧 Sử dụng làm sạch cơ bản...")
        final_content = cleaner.clean_raw_text(combined_content)
        method = "basic_synthesis"
    
    # Bước 4: Tạo bài viết wiki cuối cùng
    print("\n📚 BƯỚC 4: Tạo bài viết wiki")
    print("-" * 50)
    
    # Tạo phần nguồn tham khảo
    sources_section = "\n## Nguồn tham khảo\n\n"
    for i, source in enumerate(sources, 1):
        sources_section += f"{i}. [{source['title']}]({source['url']})\n"
    
    # Tạo nội dung markdown hoàn chỉnh
    wiki_content = f"""# {topic}

> **Tóm tắt:** Bài viết tổng hợp từ {len(sources)} nguồn tin uy tín về {topic.lower()}.

{final_content}

{sources_section}

---

**Phương pháp:** {method}  
**Số nguồn:** {len(sources)} trang web  
**Thời gian tạo:** {time.strftime('%d/%m/%Y %H:%M')}  
**Công cụ:** WikinongSang Crawler
"""
    
    # Lưu vào thư mục pages
    pages_dir = Path("pages")
    pages_dir.mkdir(exist_ok=True)
    
    # Tạo tên file an toàn
    safe_filename = topic.lower()
    safe_filename = ''.join(c for c in safe_filename if c.isalnum() or c in (' ', '-', '_'))
    safe_filename = safe_filename.replace(' ', '_')
    safe_filename = f"{safe_filename}_{int(time.time())}.md"
    
    wiki_file = pages_dir / safe_filename
    
    with open(wiki_file, 'w', encoding='utf-8') as f:
        f.write(wiki_content)
    
    print(f"✅ Đã tạo bài viết wiki: {wiki_file}")
    
    # Bước 5: Tóm tắt kết quả
    print("\n🎉 HOÀN THÀNH!")
    print("=" * 60)
    print(f"📄 Bài viết: {topic}")
    print(f"📁 File: {wiki_file}")
    print(f"📊 Độ dài: {len(wiki_content)} ký tự")
    print(f"🌐 Nguồn: {len(sources)} trang web")
    print(f"🤖 Phương pháp: {method}")
    print()
    print("📋 Các bước tiếp theo:")
    print("1. Chạy website: python app.py")
    print("2. Truy cập: http://localhost:8000")
    print(f"3. Xem bài viết: http://localhost:8000/page/{wiki_file.stem}")
    print("4. Đăng nhập admin để chỉnh sửa: /admin")
    print()
    print("🔄 Để thu thập thêm bài viết khác: python crawler.py")

def single_url_crawler():
    """Thu thập nội dung từ 1 URL đơn lẻ"""
    print("\n📡 THU THẬP ĐƠN LẺ")
    print("-" * 30)
    
    crawler = WebCrawler()
    cleaner = TextCleaner()
    
    url = input("Nhập URL: ").strip()
    if not url or not (url.startswith('http://') or url.startswith('https://')):
        print("❌ URL không hợp lệ!")
        return
    
    print(f"\n🔄 Đang crawl: {url}")
    
    try:
        result = crawler.crawl_url(url)
        if result:
            print(f"✅ Thành công: {result['title']}")
            
            # Lưu raw
            raw_file = crawler.save_raw_content(result)
            
            # Làm sạch
            cleaned_file = cleaner.process_file(str(raw_file))
            
            # Copy vào pages
            pages_dir = Path("pages")
            pages_dir.mkdir(exist_ok=True)
            
            with open(cleaned_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            wiki_file = pages_dir / f"single_{int(time.time())}.md"
            with open(wiki_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"📚 Đã tạo wiki: {wiki_file}")
        else:
            print("❌ Không thể crawl URL này")
    except Exception as e:
        print(f"❌ Lỗi: {e}")

def show_guide():
    """Hiển thị hướng dẫn"""
    print("\n📖 HƯỚNG DẪN SỬ DỤNG")
    print("-" * 40)
    print()
    print("🎯 Mục đích:")
    print("- Thu thập nội dung thật từ các trang báo/blog")
    print("- Tổng hợp nhiều nguồn thành 1 bài viết wiki")
    print("- Làm sạch và tối ưu bằng AI")
    print()
    print("📋 Quy trình:")
    print("1. Nhập 2-5 URL từ các trang tin tức")
    print("2. Crawler tự động thu thập nội dung")
    print("3. AI tổng hợp và làm sạch")
    print("4. Tạo bài viết wiki hoàn chỉnh")
    print()
    print("💡 Gợi ý URL tốt:")
    print("- VnExpress: https://vnexpress.net/...")
    print("- Dân Trí: https://dantri.com.vn/...")
    print("- Nông nghiệp VN: https://nongnghiep.vn/...")
    print("- Báo Nông thôn: https://baonongthon.com.vn/...")
    print()
    print("⚠️ Lưu ý:")
    print("- Chọn các bài viết cùng chủ đề")
    print("- Tránh trang có quá nhiều quảng cáo")
    print("- Đảm bảo Ollama đang chạy để có kết quả tốt nhất")

def main():
    """Chương trình chính với menu"""
    print("🌾 === WIKINONGSANG CRAWLER ===")
    print()
    print("Chọn chế độ:")
    print("1. Thu thập từ nhiều URL và tổng hợp thành 1 bài viết")
    print("2. Thu thập từ 1 URL đơn lẻ")
    print("3. Xem hướng dẫn sử dụng")
    
    choice = input("\nChọn (1/2/3): ").strip()
    
    if choice == "1":
        multi_source_crawler()
    elif choice == "2":
        single_url_crawler()
    elif choice == "3":
        show_guide()
    else:
        print("❌ Lựa chọn không hợp lệ!")

if __name__ == "__main__":
    main()