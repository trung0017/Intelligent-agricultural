import requests
import json
import re
from pathlib import Path
import time
from typing import Optional

class TextCleaner:
    def __init__(self, ollama_url: str = None):
        # Tự động phát hiện OLLAMA_HOST từ environment variable
        import os
        ollama_host = os.getenv('OLLAMA_HOST', 'localhost:11500')
        if not ollama_host.startswith('http'):
            ollama_host = f"http://{ollama_host}"
        
        self.ollama_url = ollama_url or f"{ollama_host}/api/generate"
        self.ollama_base_url = ollama_host
        self.model = "qwen2.5:7b"  # Khuyên dùng cho tiếng Việt với 16GB RAM
        

        
    def test_ollama_connection(self) -> bool:
        """Kiểm tra kết nối Ollama chi tiết"""
        try:

            
            # Kiểm tra server
            tags_url = f"{self.ollama_base_url}/api/tags"
            response = requests.get(tags_url, timeout=10)
            
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                

                
                # Kiểm tra model cần thiết
                if self.model in model_names:

                    return True
                else:
                    print(f"⚠️ Model {self.model} chưa có")
                    print(f"💡 Chạy: ollama pull {self.model}")
                    return False
            else:

                return False
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Không thể kết nối đến {self.ollama_base_url}")
            print("💡 Kiểm tra:")
            print("   1. Ollama có đang chạy? (ollama serve)")
            print("   2. Port có đúng? (11500)")
            print("   3. Firewall có chặn không?")
            return False
        except Exception as e:
            print(f"❌ Lỗi kết nối Ollama: {e}")
            return False
    
    def call_ollama(self, prompt: str, max_tokens: int = 2000, retries: int = 1) -> Optional[str]:
        """Gọi Ollama API với retry mechanism cải thiện"""
        
        # Rút ngắn prompt nếu quá dài để tránh timeout
        if len(prompt) > 3000:
            print("⚠️ Prompt quá dài, rút gọn để tránh timeout...")
            prompt = prompt[:3000] + "\n\nHãy tóm tắt và viết lại nội dung trên thành bài viết wiki hoàn chỉnh."
        
        for attempt in range(retries + 1):
            try:

                
                # Giảm max_tokens để xử lý nhanh hơn
                adjusted_tokens = min(max_tokens, 1500)
                
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": adjusted_tokens,
                        "num_ctx": 2048,  # Giảm context window
                        "repeat_penalty": 1.1
                    }
                }
                
                # Tăng timeout lên 180s nhưng giảm số lần retry
                response = requests.post(
                    self.ollama_url,
                    json=payload,
                    timeout=180
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get('response', '').strip()
                    if content:
                        return content
                    else:
                        pass
                else:
                    pass

                    
            except requests.exceptions.Timeout:
                print(f"⏰ Timeout lần {attempt + 1} (180s)")
                if attempt < retries:
                    print("🔄 Thử lại với prompt ngắn hơn...")
                    # Rút ngắn prompt thêm nữa cho lần retry
                    prompt = prompt[:2000] + "\n\nTóm tắt ngắn gọn nội dung trên."
                    time.sleep(3)
            except requests.exceptions.ConnectionError:
                print(f"🔌 Lỗi kết nối Ollama lần {attempt + 1}")
                print("💡 Kiểm tra: Ollama có đang chạy trên port 11500?")
                if attempt < retries:
                    print("🔄 Thử lại sau 5 giây...")
                    time.sleep(5)
            except Exception as e:
                print(f"❌ Lỗi không xác định: {e}")
                break
        
        print("❌ AI không phản hồi, sử dụng làm sạch cơ bản")
        return None
    
    def test_ai_simple(self) -> bool:
        """Test AI với prompt đơn giản"""
        try:
            print("🧪 Test AI với prompt đơn giản...")
            simple_prompt = "Viết 1 câu về nông nghiệp Việt Nam."
            
            result = self.call_ollama(simple_prompt, max_tokens=100, retries=0)
            
            if result and len(result) > 10:
                print("✅ AI test thành công")
                return True
            else:
                print("❌ AI test thất bại")
                return False
                
        except Exception as e:
            print(f"❌ Lỗi test AI: {e}")
            return False
    
    def clean_raw_text(self, text: str) -> str:
        """Làm sạch văn bản cơ bản"""
        # Xóa ký tự đặc biệt
        text = re.sub(r'\s+', ' ', text)  # Nhiều khoảng trắng thành 1
        text = re.sub(r'\n+', '\n', text)  # Nhiều xuống dòng thành 1
        text = re.sub(r'[^\w\s\.\,\!\?\:\;\-\(\)\[\]\"\'\n]', '', text)  # Xóa ký tự lạ
        
        # Xóa các dòng ngắn (có thể là menu, quảng cáo)
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if len(line) > 20 and not any(keyword in line.lower() for keyword in 
                ['quảng cáo', 'advertisement', 'cookie', 'đăng ký', 'subscribe', 'follow']):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def clean_with_ai(self, title: str, content: str) -> dict:
        """Làm sạch văn bản bằng AI"""
        
        # Kiểm tra kết nối Ollama nhanh
        print("🔍 Kiểm tra kết nối AI...")
        if not self.test_ollama_connection():
            print("⚠️ Ollama không khả dụng. Chuyển sang làm sạch cơ bản...")
            cleaned_basic = self.clean_raw_text(content)
            return {
                'title': title,
                'content': cleaned_basic,
                'summary': cleaned_basic[:200] + "..." if len(cleaned_basic) > 200 else cleaned_basic,
                'method': 'basic_cleaning'
            }
        
        print("🤖 Đang làm sạch bằng AI...")
        
        # Prompt cho việc làm sạch
        # Rút ngắn prompt để giảm thời gian xử lý
        clean_prompt = f"""
Làm sạch văn bản sau thành Markdown:

TIÊU ĐỀ: {title}

NỘI DUNG: {content[:2000]}

YÊU CẦU:
- Xóa quảng cáo, menu
- Giữ nội dung chính
- Định dạng Markdown
- Ngắn gọn, súc tích

KẾT QUẢ:
"""

        cleaned_content = self.call_ollama(clean_prompt, max_tokens=1500)  # Giảm max_tokens
        
        if not cleaned_content:
            print("⚠️ AI không phản hồi. Sử dụng làm sạch cơ bản...")
            cleaned_content = self.clean_raw_text(content)
        
        # Tạo tóm tắt
        # Tạo tóm tắt đơn giản hơn
        summary_prompt = f"""
Tóm tắt ngắn gọn:

{cleaned_content[:500]}

Tóm tắt 1 câu:
"""
        
        summary = self.call_ollama(summary_prompt, max_tokens=100)  # Giảm xuống 100 tokens
        if not summary:
            summary = cleaned_content[:200] + "..."
        
        return {
            'title': title,
            'content': cleaned_content,
            'summary': summary,
            'method': 'ai_cleaning'
        }
    
    def process_file(self, input_file: str, output_dir: str = "cleaned_content") -> str:
        """Xử lý file JSON thô thành Markdown sạch"""
        
        # Đọc file đầu vào
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        title = data.get('title', 'Không có tiêu đề')
        content = data.get('content', '')
        url = data.get('url', '')
        
        print(f"📄 Đang xử lý: {title}")
        
        # Làm sạch bằng AI
        result = self.clean_with_ai(title, content)
        
        # Tạo nội dung Markdown
        markdown_content = f"""# {result['title']}

> **Tóm tắt:** {result['summary']}

{result['content']}

---

**Nguồn:** [{url}]({url})  
**Xử lý:** {result['method']}  
**Thời gian:** {time.strftime('%d/%m/%Y %H:%M')}
"""
        
        # Lưu file
        Path(output_dir).mkdir(exist_ok=True)
        
        # Tạo tên file từ tiêu đề
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '_', safe_title)
        output_file = Path(output_dir) / f"{safe_title}.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"✅ Đã lưu: {output_file}")
        return str(output_file)
    
    def batch_process(self, input_dir: str = "raw_content", output_dir: str = "cleaned_content"):
        """Xử lý hàng loạt file"""
        input_path = Path(input_dir)
        if not input_path.exists():
            print(f"Thư mục {input_dir} không tồn tại!")
            return
        
        json_files = list(input_path.glob("*.json"))
        if not json_files:
            print(f"Không tìm thấy file JSON trong {input_dir}")
            return
        
        print(f"🔄 Tìm thấy {len(json_files)} file để xử lý...")
        
        for i, file_path in enumerate(json_files, 1):
            print(f"\n[{i}/{len(json_files)}] Xử lý {file_path.name}")
            try:
                self.process_file(str(file_path), output_dir)
                time.sleep(2)  # Tránh spam API
            except Exception as e:
                print(f"❌ Lỗi xử lý {file_path.name}: {e}")

def main():
    """Chương trình chính"""
    cleaner = TextCleaner()
    
    print("=== WikinongSang Text Cleaner ===")
    print("Sử dụng model:", cleaner.model)
    print("Ollama URL:", cleaner.ollama_url)
    
    # Kiểm tra Ollama
    if cleaner.test_ollama_connection():
        print("✅ Ollama đã sẵn sàng")
    else:
        print("⚠️ Ollama chưa chạy hoặc chưa cài model")
        print("Hướng dẫn:")
        print("1. Cài Ollama: https://ollama.ai/download")
        print("2. Chạy: ollama pull qwen2.5:7b")
        print("3. Khởi động với port tùy chỉnh:")
        print("   set OLLAMA_HOST=127.0.0.1:11500")
        print("   ollama serve")
        print("4. Hoặc: OLLAMA_HOST=127.0.0.1:11500 ollama serve")
    
    print("\n1. Xử lý một file JSON")
    print("2. Xử lý hàng loạt file trong thư mục raw_content")
    
    choice = input("Chọn (1/2): ").strip()
    
    if choice == "1":
        file_path = input("Đường dẫn file JSON: ").strip()
        if Path(file_path).exists():
            result_file = cleaner.process_file(file_path)
            print(f"\n✅ Hoàn thành! File đã làm sạch: {result_file}")
        else:
            print("File không tồn tại!")
    
    elif choice == "2":
        cleaner.batch_process()
        print("\n✅ Hoàn thành xử lý hàng loạt!")

if __name__ == "__main__":
    main()