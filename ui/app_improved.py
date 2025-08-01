#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Improved Gradio app with modern UI and file management
"""

import asyncio
import aiohttp
import gradio as gr
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import json
import os
import threading
import concurrent.futures
from datetime import datetime
import tempfile
import requests
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from utils.file_manager import file_manager

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://ai-data-processing:8888")
GRADIO_PORT = int(os.getenv("GRADIO_PORT", "7866"))
GRADIO_HOST = os.getenv("GRADIO_HOST", "0.0.0.0")

class ImprovedAPIClient:
    """Enhanced API client with better error handling and file management"""
    
    def __init__(self, api_base_url: str = API_BASE_URL):
        self.api_base_url = api_base_url
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.temp_dir = Path(tempfile.gettempdir()) / "topik_downloads"
        self.temp_dir.mkdir(exist_ok=True)
    
    def _run_async_safe(self, coro):
        """Run async function in a thread-safe way"""
        def run_in_new_loop():
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        
        future = self._executor.submit(run_in_new_loop)
        return future.result(timeout=100)
    
    async def _check_health_async(self) -> Tuple[bool, str]:
        """Async health check with better error messages"""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.api_base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == "success":
                            return True, "🟢 API đang hoạt động bình thường"
                        else:
                            return False, f"🟡 API phản hồi nhưng có vấn đề: {data.get('message', 'Unknown error')}"
                    else:
                        return False, f"🔴 API lỗi với mã {response.status}"
        except asyncio.TimeoutError:
            return False, "🔴 API không phản hồi (timeout)"
        except Exception as e:
            return False, f"🔴 Không thể kết nối: {str(e)}"
    
    def check_health(self) -> str:
        """Thread-safe health check"""
        try:
            healthy, message = self._run_async_safe(self._check_health_async())
            return message
        except Exception as e:
            return f"🔴 Lỗi kiểm tra API: {str(e)}"
    
    async def _process_images_async(self, files: List[str], source_info: str) -> Dict[str, Any]:
        """Async image processing with better progress tracking"""
        try:
            timeout = aiohttp.ClientTimeout(total=300)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                data = aiohttp.FormData()
                data.add_field('source_info', source_info)
                
                for file_path in files:
                    if file_path and Path(file_path).exists():
                        file_name = Path(file_path).name
                        with open(file_path, 'rb') as f:
                            data.add_field('files', f.read(), filename=file_name, content_type='image/jpeg')
                
                async with session.post(f"{self.api_base_url}/process-images", data=data) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        return {"success": True, "data": result}
                    else:
                        return {"success": False, "error": result.get("detail", "Unknown error")}
                        
        except asyncio.TimeoutError:
            return {"success": False, "error": "Xử lý quá lâu (timeout)"}
        except Exception as e:
            return {"success": False, "error": f"Lỗi kết nối API: {str(e)}"}
    
    def download_file(self, filename: str) -> Optional[str]:
        """Download file from API to local temp directory"""
        try:
            download_url = f"{self.api_base_url}/download/{filename}"
            response = requests.get(download_url, timeout=30)
            
            if response.status_code == 200:
                local_file_path = self.temp_dir / filename
                with open(local_file_path, 'wb') as f:
                    f.write(response.content)
                
                return str(local_file_path)
            else:
                return None
                
        except Exception as e:
            return None
    
    def process_images(self, files: List[str], source_info: str) -> Tuple[Dict[str, Any], Optional[str]]:
        """Process images and download result file"""
        try:
            result = self._run_async_safe(self._process_images_async(files, source_info))
            
            if result["success"] and result["data"].get("csv_filename"):
                downloaded_file = self.download_file(result["data"]["csv_filename"])
                return result, downloaded_file
            else:
                return result, None
                
        except Exception as e:
            return {"success": False, "error": f"Xử lý thất bại: {str(e)}"}, None

# Global API client
api_client = ImprovedAPIClient()

def safe_check_health() -> str:
    """Safe health check with auto cleanup"""
    health_status = api_client.check_health()
    
    # Thực hiện auto cleanup khi check health
    cleanup_msg = file_manager.auto_cleanup_if_needed()
    
    return f"{health_status}\n\n📁 **Quản lý file:** {cleanup_msg}"

def get_storage_info() -> str:
    """Lấy thông tin storage hiện tại"""
    try:
        stats = file_manager.get_storage_stats()
        files_info = file_manager.get_output_files_info()
        
        info_text = f"""
📊 **Thống kê Storage:**
- Tổng số file: {stats['total_files']} file
- Dung lượng: {stats['total_size_mb']} MB
- Phân bố theo độ tuổi:
  - 0-1 ngày: {stats['age_distribution']['0-1_days']} file
  - 2-7 ngày: {stats['age_distribution']['2-7_days']} file  
  - 8-30 ngày: {stats['age_distribution']['8-30_days']} file
  - 30+ ngày: {stats['age_distribution']['30+_days']} file

📋 **File gần đây:**
"""
        
        # Hiển thị 5 file mới nhất
        for i, (filename, age_days, size_mb) in enumerate(files_info[:5]):
            info_text += f"- {filename} ({age_days} ngày, {size_mb:.1f}MB)\n"
        
        if len(files_info) > 5:
            info_text += f"... và {len(files_info) - 5} file khác"
            
        return info_text
        
    except Exception as e:
        return f"❌ Lỗi khi lấy thông tin storage: {e}"

def manual_cleanup() -> str:
    """Thực hiện dọn dẹp thủ công"""
    try:
        deleted_count, freed_mb = file_manager.cleanup_old_files(max_age_days=7, max_files=30)
        
        if deleted_count > 0:
            return f"🧹 **Dọn dẹp hoàn tất!**\n- Đã xóa: {deleted_count} file\n- Giải phóng: {freed_mb:.1f}MB"
        else:
            return "✅ Không có file nào cần dọn dẹp"
            
    except Exception as e:
        return f"❌ Lỗi khi dọn dẹp: {e}"

def safe_process_images(files: List[str], source_info: str, progress=gr.Progress()) -> Tuple[str, Optional[str], str]:
    """Safe image processing with enhanced feedback"""
    try:
        if not files:
            return "❌ Vui lòng upload ít nhất một ảnh", None, get_storage_info()
        
        valid_files = [f for f in files if f and Path(f).exists()]
        if not valid_files:
            return "❌ Không tìm thấy file hợp lệ", None, get_storage_info()
        
        progress(0.1, desc="🔍 Kiểm tra kết nối...")
        
        # Check API health first
        health_check = api_client.check_health()
        if "🔴" in health_check:
            return f"❌ API không sẵn sàng:\n{health_check}", None, get_storage_info()
        
        progress(0.3, desc="📤 Đang upload và xử lý ảnh...")
        
        result, downloaded_file = api_client.process_images(valid_files, source_info)
        
        if result["success"]:
            data = result["data"]
            progress(0.8, desc="💾 Đang tải file kết quả...")
            
            success_msg = f"""
✅ **Xử lý thành công!**

📊 **Kết quả:**
- 🖼️ Ảnh đã xử lý: {data.get('processed_images', 0)}
- ❓ Câu hỏi trích xuất: {data.get('extracted_questions', 0)}
- 📄 File CSV: `{data.get('csv_filename', 'N/A')}`

⏰ **Thời gian:** {datetime.now().strftime('%H:%M:%S')}
💾 File đã sẵn sàng để tải xuống bên dưới.
            """
            
            progress(1.0, desc="✅ Hoàn thành!")
            return success_msg, downloaded_file, get_storage_info()
        else:
            error_msg = f"""
❌ **Xử lý thất bại**

🔍 **Chi tiết lỗi:** {result.get('error', 'Unknown error')}

💡 **Gợi ý:**
- Kiểm tra kết nối mạng
- Đảm bảo ảnh có chất lượng tốt
- Thử lại sau vài phút
            """
            return error_msg, None, get_storage_info()
            
    except Exception as e:
        return f"❌ **Lỗi hệ thống:** {str(e)}", None, get_storage_info()

def create_improved_demo():
    """Create modern, lightweight Gradio interface"""
    
    # Modern CSS with soft colors and smooth animations
    css = """
    .gradio-container {
        max-width: 1400px !important;
        margin: auto !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2.5rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }
    
    .status-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
    }
    
    .info-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
    }
    
    .upload-area {
        border: 2px dashed #667eea;
        border-radius: 12px;
        padding: 2rem;
        background: linear-gradient(135deg, #f8f9ff 0%, #e8f0ff 100%);
        transition: all 0.3s ease;
    }
    
    .upload-area:hover {
        border-color: #764ba2;
        background: linear-gradient(135deg, #f0f4ff 0%, #dde8ff 100%);
    }
    
    .result-area {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
    }
    
    .btn-primary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px 24px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
    
    .btn-primary:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4) !important;
    }
    
    .btn-secondary {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%) !important;
        color: #333 !important;
        border: none !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }
    """
    
    with gr.Blocks(
        title="TOPIK OCR Tool - Enhanced",
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="pink",
            neutral_hue="slate",
            font=gr.themes.GoogleFont("Inter")
        ),
        css=css
    ) as demo:
        
        # Header
        with gr.Row():
            gr.Markdown("""
            <div class="main-header">
                <h1>🇰🇷 TOPIK OCR Tool</h1>
                <p style="font-size: 1.1em; margin-top: 1rem; opacity: 0.9;">
                    Công cụ AI chuyên nghiệp xử lý đề thi TOPIK thành dữ liệu có cấu trúc
                </p>
                <p style="font-size: 0.9em; margin-top: 0.5rem; opacity: 0.8;">
                    ✨ Giao diện mới • 🧹 Tự động dọn dẹp • 📊 Quản lý thông minh
                </p>
            </div>
            """)
        
        # Status and Management Section
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 🔍 Trạng thái hệ thống")
                status_btn = gr.Button("Kiểm tra API & Dọn dẹp", variant="secondary", size="sm")
                status_output = gr.Markdown("Nhấn để kiểm tra trạng thái...")
            
            with gr.Column(scale=1):
                gr.Markdown("### 📁 Quản lý Storage")
                storage_btn = gr.Button("Xem thông tin Storage", variant="secondary", size="sm")
                cleanup_btn = gr.Button("Dọn dẹp thủ công", variant="secondary", size="sm")
                storage_output = gr.Markdown("Nhấn để xem thông tin...")
        
        # Main Processing Section
        with gr.Row():
            with gr.Column(scale=3):
                gr.Markdown("### 📤 Upload & Xử lý")
                
                with gr.Group():
                    image_files = gr.File(
                        label="🖼️ Chọn ảnh đề thi TOPIK",
                        file_count="multiple",
                        file_types=["image"],
                        height=180,
                        elem_classes=["upload-area"]
                    )
                    
                    source_info = gr.Textbox(
                        label="📝 Thông tin nguồn đề thi",
                        value="TOPIK Practice Test",
                        placeholder="Ví dụ: TOPIK I 읽기 - 70회",
                        lines=2
                    )
                    
                    process_btn = gr.Button(
                        "🚀 Bắt đầu xử lý", 
                        variant="primary",
                        size="lg",
                        elem_classes=["btn-primary"]
                    )
            
            with gr.Column(scale=2):
                gr.Markdown("### 📊 Kết quả & Tải xuống")
                
                result_output = gr.Markdown(
                    "🎯 Sẵn sàng xử lý ảnh đề thi...",
                    elem_classes=["result-area"]
                )
                
                download_file = gr.File(
                    label="📥 File CSV kết quả",
                    visible=True,
                    interactive=False
                )
        
        # Event handlers
        status_btn.click(
            fn=safe_check_health,
            outputs=status_output
        )
        
        storage_btn.click(
            fn=get_storage_info,
            outputs=storage_output
        )
        
        cleanup_btn.click(
            fn=manual_cleanup,
            outputs=storage_output
        )
        
        process_btn.click(
            fn=safe_process_images,
            inputs=[image_files, source_info],
            outputs=[result_output, download_file, storage_output],
            show_progress=True
        )
        
        # Enhanced Footer
        gr.Markdown("""
        ---
        <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #f8f9ff 0%, #e8f0ff 100%); border-radius: 12px; margin-top: 2rem;">
            <h3>💡 Hướng dẫn sử dụng</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin-top: 1rem;">
                <div>
                    <strong>1️⃣ Chuẩn bị</strong><br>
                    Kiểm tra trạng thái API và dọn dẹp file cũ
                </div>
                <div>
                    <strong>2️⃣ Upload</strong><br>
                    Chọn ảnh đề thi TOPIK (JPG, PNG, WebP)
                </div>
                <div>
                    <strong>3️⃣ Xử lý</strong><br>
                    Nhấn "Bắt đầu xử lý" và đợi kết quả
                </div>
                <div>
                    <strong>4️⃣ Tải xuống</strong><br>
                    File CSV sẽ xuất hiện tự động
                </div>
            </div>
            
            <div style="margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #ddd;">
                <p><strong>🔧 Công nghệ:</strong> PaddleOCR + Google Gemini AI</p>
                <p><strong>🧹 Tự động dọn dẹp:</strong> File cũ hơn 7 ngày sẽ được xóa tự động</p>
                <p><strong>💾 Giới hạn:</strong> Tối đa 50 file, 100MB storage</p>
            </div>
        </div>
        """)
    
    return demo

# Create demo for Gradio reload compatibility
demo = create_improved_demo()

def main():
    """Main function to launch the improved app"""
    print(f"🚀 Starting Enhanced TOPIK Gradio App...")
    print(f"📡 API Base URL: {API_BASE_URL}")
    print(f"🌐 Gradio Host: {GRADIO_HOST}:{GRADIO_PORT}")
    print(f"🧹 Auto cleanup enabled: 7 days, 50 files max")
    
    demo.launch(
        server_name=GRADIO_HOST,
        server_port=GRADIO_PORT,
        share=False,
        show_error=True,
        quiet=False
    )

if __name__ == "__main__":
    main()