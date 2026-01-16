from fastapi import FastAPI, Request, Form, HTTPException, Depends, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import markdown
from pathlib import Path
import json
from datetime import datetime
import aiofiles
import asyncio
import subprocess
import threading
import time
from typing import List, Dict, Any
import uuid

app = FastAPI(title="WikiNongSan")

# Cấu hình thư mục
PAGES_DIR = Path("pages")
STATIC_DIR = Path("static")
TEMPLATES_DIR = Path("templates")

# Tạo thư mục nếu chưa có
PAGES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Cấu hình admin đơn giản (trong thực tế nên dùng database)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "123"

# Lưu trữ trạng thái các task đang chạy
running_tasks = {}
task_logs = {}

def check_admin(username: str = Form(), password: str = Form()):
    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu")
    return True

def get_all_pages():
    """Lấy danh sách tất cả các trang"""
    pages = []
    for file_path in PAGES_DIR.glob("*.md"):
        # Đọc tiêu đề từ nội dung file (dòng đầu tiên bắt đầu với #)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Tìm dòng đầu tiên bắt đầu với #
                for line in content.split('\n'):
                    if line.strip().startswith('# '):
                        title = line.strip()[2:].strip()  # Bỏ "# " ở đầu
                        break
                else:
                    # Nếu không tìm thấy, dùng tên file nhưng bỏ timestamp
                    title = file_path.stem
                    # Bỏ timestamp (phần _số cuối)
                    if '_' in title:
                        parts = title.split('_')
                        if parts[-1].isdigit():  # Nếu phần cuối là số (timestamp)
                            title = '_'.join(parts[:-1])
                    title = title.replace("_", " ").title()
        except:
            # Fallback nếu có lỗi đọc file
            title = file_path.stem.replace("_", " ").title()
        
        pages.append({
            "filename": file_path.name,
            "title": title,
            "slug": file_path.stem
        })
    return sorted(pages, key=lambda x: x["title"])

def markdown_to_html(content: str) -> str:
    """Chuyển đổi Markdown sang HTML"""
    md = markdown.Markdown(extensions=['extra', 'codehilite'])
    return md.convert(content)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Trang chủ hiển thị danh sách tất cả các trang"""
    pages = get_all_pages()
    return templates.TemplateResponse("home.html", {
        "request": request,
        "pages": pages
    })

@app.get("/page/{slug}", response_class=HTMLResponse)
async def view_page(request: Request, slug: str):
    """Xem nội dung một trang"""
    file_path = PAGES_DIR / f"{slug}.md"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy trang")
    
    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
        content = await f.read()
    
    html_content = markdown_to_html(content)
    
    # Đọc tiêu đề từ nội dung file (dòng đầu tiên bắt đầu với #)
    title = None
    for line in content.split('\n'):
        if line.strip().startswith('# '):
            title = line.strip()[2:].strip()  # Bỏ "# " ở đầu
            break
    
    # Nếu không tìm thấy tiêu đề trong nội dung, dùng slug nhưng bỏ timestamp
    if not title:
        title = slug
        # Bỏ timestamp (phần _số cuối)
        if '_' in title:
            parts = title.split('_')
            if parts[-1].isdigit():  # Nếu phần cuối là số (timestamp)
                title = '_'.join(parts[:-1])
        title = title.replace("_", " ").title()
    
    return templates.TemplateResponse("page.html", {
        "request": request,
        "title": title,
        "content": html_content,
        "slug": slug
    })

@app.get("/admin", response_class=HTMLResponse)
async def admin_login(request: Request):
    """Trang đăng nhập admin"""
    return templates.TemplateResponse("admin_login.html", {"request": request})

@app.post("/admin/login")
async def admin_login_post(admin_check: bool = Depends(check_admin)):
    """Xử lý đăng nhập admin"""
    return RedirectResponse(url="/admin/dashboard", status_code=302)

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Dashboard admin"""
    pages = get_all_pages()
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "pages": pages
    })

@app.get("/admin/crawler", response_class=HTMLResponse)
async def admin_crawler(request: Request):
    """Trang crawler và AI processing"""
    return templates.TemplateResponse("admin_crawler.html", {
        "request": request
    })

@app.get("/admin/create", response_class=HTMLResponse)
async def admin_create_page(request: Request):
    """Form tạo trang mới"""
    return templates.TemplateResponse("admin_create.html", {"request": request})

@app.post("/admin/create")
async def admin_create_page_post(
    title: str = Form(),
    content: str = Form()
):
    """Tạo trang mới"""
    slug = title.lower().replace(" ", "_").replace("-", "_")
    file_path = PAGES_DIR / f"{slug}.md"
    
    # Thêm metadata
    full_content = f"""# {title}

{content}

---
*Tạo ngày: {datetime.now().strftime('%d/%m/%Y %H:%M')}*
"""
    
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        await f.write(full_content)
    
    return RedirectResponse(url=f"/page/{slug}", status_code=302)

@app.get("/admin/edit/{slug}", response_class=HTMLResponse)
async def admin_edit_page(request: Request, slug: str):
    """Form chỉnh sửa trang"""
    file_path = PAGES_DIR / f"{slug}.md"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy trang")
    
    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
        content = await f.read()
    
    title = slug.replace("_", " ").title()
    return templates.TemplateResponse("admin_edit.html", {
        "request": request,
        "title": title,
        "content": content,
        "slug": slug
    })

@app.post("/admin/edit/{slug}")
async def admin_edit_page_post(
    slug: str,
    content: str = Form()
):
    """Cập nhật trang"""
    file_path = PAGES_DIR / f"{slug}.md"
    
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        await f.write(content)
    
    return RedirectResponse(url=f"/page/{slug}", status_code=302)

@app.post("/admin/delete/{slug}")
async def admin_delete_page(slug: str):
    """Xóa trang"""
    file_path = PAGES_DIR / f"{slug}.md"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Trang không tồn tại")
    
    try:
        file_path.unlink()  # Xóa file
        return JSONResponse(content={
            "success": True,
            "message": f"Đã xóa '{slug}'"
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Lỗi khi xóa trang: {str(e)}"
            }
        )

@app.post("/admin/delete-all")
async def admin_delete_all_pages():
    """Xóa tất cả trang"""
    try:
        deleted_count = 0
        
        if PAGES_DIR.exists():
            for file_path in PAGES_DIR.glob("*.md"):
                file_path.unlink()
                deleted_count += 1
        
        return JSONResponse(content={
            "success": True,
            "message": f"Đã xóa {deleted_count} trang",
            "deleted_count": deleted_count
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Lỗi khi xóa tất cả: {str(e)}"
            }
        )

@app.post("/admin/api/upload-image")
async def admin_upload_image(file: UploadFile = File(...), slug: str = Form(...)):
    """Upload ảnh cho bài viết cụ thể"""

    try:
        # Kiểm tra file ảnh
        if not file.content_type.startswith('image/'):
            return JSONResponse(
                status_code=400,
                content={"error": "Chỉ chấp nhận file ảnh"}
            )
        
        # Tạo thư mục uploads nếu chưa có
        uploads_dir = Path("static/uploads")
        uploads_dir.mkdir(exist_ok=True)
        
        # Lưu file với tên theo slug
        image_path = uploads_dir / f"{slug}.jpg"
        
        with open(image_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        return JSONResponse(content={
            "success": True,
            "message": "Upload ảnh thành công",
            "image_url": f"/static/uploads/{slug}.jpg"
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Lỗi upload: {str(e)}"}
        )

@app.post("/admin/api/delete-image")
async def admin_delete_image(slug: str = Form(...)):
    """Xóa ảnh của bài viết cụ thể"""
    try:
        image_path = Path(f"static/uploads/{slug}.jpg")
        
        if image_path.exists():
            image_path.unlink()
            return JSONResponse(content={
                "success": True,
                "message": "Đã xóa ảnh bài viết"
            })
        else:
            return JSONResponse(content={
                "success": False,
                "message": "Không có ảnh để xóa"
            })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Lỗi xóa ảnh: {str(e)}"}
        )

@app.post("/admin/upload")
async def admin_upload_file(file: UploadFile = File(...)):
    """Upload file đã làm sạch"""
    if not file.filename.endswith('.md'):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .md")
    
    content = await file.read()
    file_path = PAGES_DIR / file.filename
    
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    return {"message": f"Đã upload thành công {file.filename}"}

# ===== CRAWLER & AI PROCESSING APIs =====

def run_crawler_task(task_id: str, urls: List[str], topic: str):
    """Chạy crawler trong background thread"""
    try:
        task_logs[task_id] = []
        
        def log_message(msg: str):
            task_logs[task_id].append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        
        log_message("🚀 Bắt đầu thu thập nội dung...")
        
        # Import crawler modules
        from crawl import WebCrawler
        
        crawler = WebCrawler()
        
        # Crawl từng URL
        crawled_data = []
        for i, url in enumerate(urls, 1):
            log_message(f"📡 [{i}/{len(urls)}] Đang crawl: {url}")
            
            try:
                result = crawler.crawl_url(url, use_playwright=False)
                
                if result and len(result['content']) < 500:
                    log_message("📄 Nội dung ngắn, thử lại với Playwright...")
                    result = crawler.crawl_url(url, use_playwright=True)
                
                if result:
                    crawled_data.append(result)
                    log_message(f"✅ Thành công: {result['title'][:50]}... ({len(result['content'])} ký tự)")
                    
                    # Lưu raw file
                    raw_file = crawler.save_raw_content(result)
                    log_message(f"💾 Đã lưu: {raw_file}")
                else:
                    log_message(f"❌ Không thể crawl {url}")
                    
            except Exception as e:
                log_message(f"❌ Lỗi crawl {url}: {str(e)}")
            
            time.sleep(2)  # Nghỉ giữa các lần crawl
        
        if not crawled_data:
            log_message("❌ Không crawl được trang nào!")
            running_tasks[task_id] = "failed"
            return
        
        log_message(f"📝 Đã crawl thành công {len(crawled_data)}/{len(urls)} trang")
        
        # Tổng hợp nội dung
        log_message("🔄 Đang tổng hợp nội dung...")
        
        combined_content = ""
        sources = []
        
        for i, data in enumerate(crawled_data, 1):
            combined_content += f"\n\n## Nguồn {i}: {data['title']}\n\n"
            combined_content += data['content'][:2000]
            if len(data['content']) > 2000:
                combined_content += "\n\n[...nội dung đã được rút gọn...]"
            
            sources.append({
                'title': data['title'],
                'url': data['url']
            })
        
        # Lưu thông tin tổng hợp để xử lý sau
        summary_data = {
            "topic": topic,
            "crawled_count": len(crawled_data),
            "total_urls": len(urls),
            "sources": sources,
            "timestamp": time.strftime('%d/%m/%Y %H:%M'),
            "combined_content": combined_content
        }
        
        # Lưu summary file
        summary_file = Path("raw_content") / f"summary_{topic.replace(' ', '_')}_{int(time.time())}.json"
        summary_file.parent.mkdir(exist_ok=True)
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        
        log_message(f"📋 Đã lưu thông tin tổng hợp: {summary_file}")
        log_message("✅ Thu thập hoàn tất!")
        log_message("💡 Sử dụng 'Text Cleaner' để xử lý AI và tạo wiki")
        
        running_tasks[task_id] = "completed"
        
    except Exception as e:
        task_logs[task_id].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Lỗi: {str(e)}")
        running_tasks[task_id] = "failed"

@app.post("/admin/api/crawler/start")
async def start_crawler_task(
    background_tasks: BackgroundTasks,
    urls: str = Form(),
    topic: str = Form()
):
    """Bắt đầu task crawler"""
    try:
        # Parse URLs
        url_list = [url.strip() for url in urls.split('\n') if url.strip()]
        
        if len(url_list) < 1:
            return JSONResponse(
                status_code=400,
                content={"error": "Cần ít nhất 1 URL để thu thập"}
            )
        
        if len(url_list) > 5:
            return JSONResponse(
                status_code=400,
                content={"error": "Tối đa 5 URL mỗi lần"}
            )
        
        # Validate URLs
        for url in url_list:
            if not (url.startswith('http://') or url.startswith('https://')):
                return JSONResponse(
                    status_code=400,
                    content={"error": f"URL không hợp lệ: {url}"}
                )
        
        # Tạo task ID
        task_id = str(uuid.uuid4())
        running_tasks[task_id] = "running"
        
        # Chạy trong background thread
        thread = threading.Thread(
            target=run_crawler_task,
            args=(task_id, url_list, topic)
        )
        thread.daemon = True
        thread.start()
        
        return JSONResponse(content={
            "task_id": task_id,
            "message": "Đã bắt đầu thu thập nội dung",
            "urls_count": len(url_list)
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Lỗi khởi tạo task: {str(e)}"}
        )

@app.get("/admin/api/crawler/status/{task_id}")
async def get_crawler_status(task_id: str):
    """Lấy trạng thái task crawler"""
    if task_id not in running_tasks:
        return JSONResponse(
            status_code=404,
            content={"error": "Task không tồn tại"}
        )
    
    return JSONResponse(content={
        "task_id": task_id,
        "status": running_tasks[task_id],
        "logs": task_logs.get(task_id, [])
    })

@app.get("/admin/api/crawler/logs/{task_id}")
async def get_crawler_logs(task_id: str):
    """Lấy logs của task crawler"""
    if task_id not in task_logs:
        return JSONResponse(content={"logs": []})
    
    return JSONResponse(content={
        "task_id": task_id,
        "logs": task_logs[task_id]
    })

@app.post("/admin/api/clean-text")
async def clean_text_api(
    background_tasks: BackgroundTasks,
    action: str = Form(),  # "single" hoặc "batch"
    custom_prompt: str = Form(None)  # Prompt tùy chỉnh từ admin
):
    """API làm sạch văn bản"""
    try:
        from clean_text import TextCleaner
        
        cleaner = TextCleaner()
        
        if action == "batch":
            # Xử lý hàng loạt - tìm summary files và tạo wiki
            raw_dir = Path("raw_content")
            if not raw_dir.exists():
                return JSONResponse(
                    status_code=400,
                    content={"error": "Thư mục raw_content không tồn tại"}
                )
            
            # Tìm summary files
            summary_files = list(raw_dir.glob("summary_*.json"))
            regular_files = [f for f in raw_dir.glob("*.json") if not f.name.startswith("summary_")]
            
            # Kiểm tra có file summary để xử lý không
            if not summary_files:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Không có file summary để tạo wiki",
                        "message": "Cần file summary từ Multi-Source Crawler để tạo bài wiki.",
                        "suggestion": "Sử dụng Multi-Source Crawler để tạo file summary",
                        "note": f"Có {len(regular_files)} file JSON thông thường nhưng chỉ xử lý file summary"
                    }
                )
            
            results = []
            
            # Xử lý summary files (tạo wiki từ crawler data)
            for summary_file in summary_files:
                try:
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summary_data = json.load(f)
                    
                    topic = summary_data['topic']
                    combined_content = summary_data['combined_content']
                    sources = summary_data['sources']
                    
                    # AI processing
                    ai_available = cleaner.test_ollama_connection()
                    
                    if ai_available:
                        # Sử dụng custom prompt nếu có, nếu không dùng mặc định
                        if custom_prompt and custom_prompt.strip():
                            # Thay thế placeholder trong custom prompt
                            synthesis_prompt = custom_prompt.replace('{content}', combined_content[:4000])
                            synthesis_prompt = synthesis_prompt.replace('{topic}', topic)
                        else:
                            # Prompt mặc định
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
                                final_content = synthesized_content
                                method = "ai_synthesis"
                            else:
                                final_content = cleaner.clean_raw_text(combined_content)
                                method = "basic_synthesis"
                        except Exception:
                            final_content = cleaner.clean_raw_text(combined_content)
                            method = "basic_synthesis"
                    else:
                        final_content = cleaner.clean_raw_text(combined_content)
                        method = "basic_synthesis"
                    
                    # Tạo bài viết wiki
                    sources_section = "\n## Nguồn tham khảo\n\n"
                    for i, source in enumerate(sources, 1):
                        sources_section += f"{i}. [{source['title']}]({source['url']})\n"
                    
                    wiki_content = f"""# {topic}

> **Tóm tắt:** Bài viết tổng hợp từ {len(sources)} nguồn tin uy tín về {topic.lower()}.

{final_content}

{sources_section}

---

**Phương pháp:** {method}  
**Số nguồn:** {len(sources)} trang web  
**Thời gian tạo:** {summary_data['timestamp']}  
**Công cụ:** WikinongSang Web Crawler
"""
                    
                    # Lưu vào pages
                    safe_filename = topic.lower()
                    safe_filename = ''.join(c for c in safe_filename if c.isalnum() or c in (' ', '-', '_'))
                    safe_filename = safe_filename.replace(' ', '_')
                    safe_filename = f"{safe_filename}_{int(time.time())}.md"
                    
                    wiki_file = PAGES_DIR / safe_filename
                    
                    with open(wiki_file, 'w', encoding='utf-8') as f:
                        f.write(wiki_content)
                    
                    # Tạo URL slug sạch (không có timestamp)
                    clean_slug = topic.lower()
                    clean_slug = ''.join(c for c in clean_slug if c.isalnum() or c in (' ', '-', '_'))
                    clean_slug = clean_slug.replace(' ', '_')
                    
                    results.append({
                        "input": str(summary_file),
                        "output": f"Wiki: {wiki_file}",
                        "status": "success",
                        "type": "wiki_created",
                        "wiki_title": topic,
                        "wiki_url": f"/page/{safe_filename[:-3]}",  # URL với timestamp (file thật)
                        "wiki_display_title": topic,  # Tiêu đề hiển thị gốc
                        "sources_count": len(sources),
                        "method": method
                    })
                    
                    # Xóa summary file sau khi xử lý
                    summary_file.unlink()
                    
                except Exception as e:
                    results.append({
                        "input": str(summary_file),
                        "error": str(e),
                        "status": "failed",
                        "type": "wiki_failed"
                    })
            
            # Bỏ qua regular files - chỉ xử lý summary files để tạo wiki
            if regular_files:
                results.append({
                    "input": f"{len(regular_files)} file JSON thông thường",
                    "output": "Bỏ qua (chỉ xử lý file summary)",
                    "status": "skipped",
                    "type": "skipped"
                })
            
            # Tạo thông báo tổng kết
            wiki_created = [r for r in results if r["type"] == "wiki_created"]
            skipped_items = [r for r in results if r["type"] == "skipped"]
            failed_items = [r for r in results if r["status"] == "failed"]
            
            summary_message = []
            if wiki_created:
                summary_message.append(f"✅ Tạo thành công {len(wiki_created)} bài wiki")
            if failed_items:
                summary_message.append(f"❌ Thất bại {len(failed_items)} file")
            
            return JSONResponse(content={
                "message": " | ".join(summary_message) if summary_message else "Hoàn thành xử lý",
                "results": results,
                "summary": {
                    "total_processed": len(wiki_created) + len(failed_items),
                    "wiki_created": len(wiki_created),
                    "skipped": len(skipped_items),
                    "failed": len(failed_items)
                }
            })
        
        else:
            return JSONResponse(
                status_code=400,
                content={"error": "Action không hợp lệ"}
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Lỗi xử lý: {str(e)}"}
        )

@app.post("/admin/api/cleanup")
async def cleanup_files(
    target: str = Form()  # "raw_content", "cleaned_content", "all"
):
    """Dọn dẹp file"""
    try:
        deleted_count = 0
        
        if target == "raw_content" or target == "all":
            raw_dir = Path("raw_content")
            if raw_dir.exists():
                for file_path in raw_dir.glob("*.json"):
                    file_path.unlink()
                    deleted_count += 1
        
        if target == "cleaned_content" or target == "all":
            cleaned_dir = Path("cleaned_content")
            if cleaned_dir.exists():
                for file_path in cleaned_dir.glob("*.md"):
                    file_path.unlink()
                    deleted_count += 1
        
        return JSONResponse(content={
            "success": True,
            "message": f"Đã xóa {deleted_count} file từ {target}",
            "deleted_count": deleted_count
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Lỗi khi dọn dẹp: {str(e)}"
            }
        )

@app.get("/admin/api/files/{folder}")
async def get_file_list(folder: str):
    """Lấy danh sách file trong thư mục"""
    try:
        if folder not in ['raw_content', 'cleaned_content', 'pages']:
            return JSONResponse(
                status_code=400,
                content={"error": "Thư mục không hợp lệ"}
            )
        
        folder_path = Path(folder)
        if not folder_path.exists():
            return JSONResponse(content={"files": []})
        
        files = []
        for file_path in folder_path.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime('%d/%m/%Y %H:%M'),
                    "path": str(file_path)
                })
        
        # Sắp xếp theo thời gian sửa đổi mới nhất
        files.sort(key=lambda x: x['modified'], reverse=True)
        
        return JSONResponse(content={"files": files})
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Lỗi đọc thư mục: {str(e)}"}
        )

@app.delete("/admin/api/files/{folder}/{filename}")
async def delete_single_file(folder: str, filename: str):
    """Xóa một file cụ thể"""
    try:
        if folder not in ['raw_content', 'cleaned_content']:
            return JSONResponse(
                status_code=400,
                content={"error": "Không được phép xóa file trong thư mục này"}
            )
        
        file_path = Path(folder) / filename
        
        if not file_path.exists():
            return JSONResponse(
                status_code=404,
                content={"error": "File không tồn tại"}
            )
        
        file_path.unlink()
        
        return JSONResponse(content={
            "success": True,
            "message": f"Đã xóa file {filename}"
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Lỗi xóa file: {str(e)}"}
        )

@app.get("/admin/api/system/status")
async def get_system_status():
    """Lấy trạng thái hệ thống"""
    try:
        from clean_text import TextCleaner
        
        # Kiểm tra Ollama (chỉ kiểm tra nhanh, không gọi AI)
        ollama_status = False
        ollama_error = ""
        try:
            import os
            import requests
            ollama_host = os.getenv('OLLAMA_HOST', 'localhost:11500')
            if not ollama_host.startswith('http'):
                ollama_host = f"http://{ollama_host}"
            
            response = requests.get(f"{ollama_host}/api/tags", timeout=5)
            ollama_status = response.status_code == 200
        except Exception as e:
            ollama_error = str(e)

            ollama_status = False
        
        # Kiểm tra thư mục
        directories = {
            "pages": PAGES_DIR.exists(),
            "raw_content": Path("raw_content").exists(),
            "cleaned_content": Path("cleaned_content").exists()
        }
        
        # Đếm file
        file_counts = {
            "pages": len(list(PAGES_DIR.glob("*.md"))) if PAGES_DIR.exists() else 0,
            "raw_content": len(list(Path("raw_content").glob("*.json"))) if Path("raw_content").exists() else 0,
            "cleaned_content": len(list(Path("cleaned_content").glob("*.md"))) if Path("cleaned_content").exists() else 0
        }
        
        return JSONResponse(content={
            "ollama": {
                "status": "connected" if ollama_status else "disconnected",
                "url": ollama_host,
                "error": ollama_error if not ollama_status else None
            },
            "directories": directories,
            "file_counts": file_counts,
            "running_tasks": len([t for t in running_tasks.values() if t == "running"])
        })
        
    except Exception as e:
        return JSONResponse(content={
            "error": str(e),
            "ollama": {"status": "error"},
            "directories": {},
            "file_counts": {}
        })

@app.get("/search", response_class=HTMLResponse)
async def search_pages(request: Request, q: str = ""):
    """Tìm kiếm trang"""
    results = []
    if q:
        for file_path in PAGES_DIR.glob("*.md"):
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            if q.lower() in content.lower() or q.lower() in file_path.stem.lower():
                title = file_path.stem.replace("_", " ").title()
                results.append({
                    "title": title,
                    "slug": file_path.stem,
                    "snippet": content[:200] + "..."
                })
    
    return templates.TemplateResponse("search.html", {
        "request": request,
        "query": q,
        "results": results
    })




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)