#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alternative Gradio app with File download component
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

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://ai-data-processing:8888")
GRADIO_PORT = int(os.getenv("GRADIO_PORT", "7866"))
GRADIO_HOST = os.getenv("GRADIO_HOST", "0.0.0.0")

class DownloadableAPIClient:
    """API client that downloads files to local temp directory"""
    
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
        """Async health check"""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.api_base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == "success":
                            return True, "✅ API sẵn sàng"
                        else:
                            return False, f"❌ API không sẵn sàng: {data.get('message', 'Unknown error')}"
                    else:
                        return False, f"❌ API trả về status {response.status}"
        except Exception as e:
            return False, f"❌ Không thể kết nối API: {str(e)}"
    
    def check_health(self) -> str:
        """Thread-safe health check"""
        try:
            healthy, message = self._run_async_safe(self._check_health_async())
            return message
        except Exception as e:
            return f"❌ Lỗi kiểm tra API: {str(e)}"
    
    async def _process_images_async(self, files: List[str], source_info: str) -> Dict[str, Any]:
        """Async image processing"""
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
                        
        except Exception as e:
            return {"success": False, "error": f"API request failed: {str(e)}"}
    
    def download_file(self, filename: str) -> Optional[str]:
        """Download file from API to local temp directory"""
        try:
            download_url = f"{self.api_base_url}/download/{filename}"
            response = requests.get(download_url, timeout=30)
            
            if response.status_code == 200:
                local_file_path = self.temp_dir / filename
                with open(local_file_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"✅ Downloaded file to: {local_file_path}")
                return str(local_file_path)
            else:
                print(f"❌ Download failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Download error: {e}")
            return None
    
    def process_images(self, files: List[str], source_info: str) -> Tuple[Dict[str, Any], Optional[str]]:
        """Process images and download result file"""
        try:
            result = self._run_async_safe(self._process_images_async(files, source_info))
            
            if result["success"] and result["data"].get("csv_filename"):
                # Download the result file
                downloaded_file = self.download_file(result["data"]["csv_filename"])
                return result, downloaded_file
            else:
                return result, None
                
        except Exception as e:
            return {"success": False, "error": f"Processing failed: {str(e)}"}, None

# Global API client
api_client = DownloadableAPIClient()

def safe_check_health() -> str:
    """Safe health check"""
    return api_client.check_health()

def safe_process_images(files: List[str], source_info: str, progress=gr.Progress()) -> Tuple[str, Optional[str]]:
    """Safe image processing with file download"""
    try:
        if not files:
            return "❌ Vui lòng upload ít nhất một ảnh", None
        
        valid_files = [f for f in files if f and Path(f).exists()]
        if not valid_files:
            return "❌ Không tìm thấy file hợp lệ", None
        
        progress(0.1, desc="Đang kết nối API...")
        progress(0.3, desc="Đang xử lý ảnh...")
        
        result, downloaded_file = api_client.process_images(valid_files, source_info)
        
        if result["success"]:
            data = result["data"]
            progress(0.8, desc="Đang tải file...")
            
            success_msg = f"""
✅ **Xử lý thành công!**

📊 **Thống kê:**
- Ảnh đã xử lý: {data.get('processed_images', 0)}
- Câu hỏi tìm thấy: {data.get('extracted_questions', 0)}
- File CSV: {data.get('csv_filename', 'N/A')}

💾 File CSV đã được tải xuống và sẵn sàng.
            """
            
            progress(1.0, desc="Hoàn thành!")
            return success_msg, downloaded_file
        else:
            error_msg = f"❌ Xử lý thất bại: {result.get('error', 'Unknown error')}"
            return error_msg, None
            
    except Exception as e:
        return f"❌ Lỗi: {str(e)}", None

def create_demo():
    """Create the Gradio demo interface with file download"""
    
    css = """
    .gradio-container {
        max-width: 1200px !important;
        margin: auto !important;
    }
    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    """
    
    with gr.Blocks(
        title="TOPIK OCR Tool",
        theme=gr.themes.Soft(),
        css=css
    ) as demo:
        
        # Header
        with gr.Row():
            gr.Markdown("""
            <div class="main-header">
                <h1>🇰🇷 TOPIK OCR Tool</h1>
                <p>Công cụ chuyên nghiệp để xử lý ảnh đề thi TOPIK thành dữ liệu CSV có cấu trúc</p>
            </div>
            """)
        
        # API Status
        with gr.Row():
            with gr.Column():
                status_btn = gr.Button("🔍 Kiểm tra trạng thái API", variant="secondary")
                status_output = gr.Markdown("Nhấn nút để kiểm tra...")
        
        # Main Processing Section
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### 📤 Upload ảnh đề thi")
                
                image_files = gr.File(
                    label="Chọn ảnh đề thi TOPIK",
                    file_count="multiple",
                    file_types=["image"],
                    height=200
                )
                
                source_info = gr.Textbox(
                    label="Thông tin nguồn đề thi",
                    value="TOPIK Practice Test",
                    placeholder="Ví dụ: TOPIK I 읽기 - 70회"
                )
                
                process_btn = gr.Button(
                    "🚀 Xử lý ảnh", 
                    variant="primary",
                    size="lg"
                )
            
            with gr.Column(scale=2):
                gr.Markdown("### 📊 Kết quả xử lý")
                result_output = gr.Markdown("Chờ xử lý...")
                
                gr.Markdown("### 📥 Tải xuống kết quả")
                download_file = gr.File(
                    label="File CSV kết quả",
                    visible=True,
                    interactive=False
                )
        
        # Event handlers
        status_btn.click(
            fn=safe_check_health,
            outputs=status_output
        )
        
        process_btn.click(
            fn=safe_process_images,
            inputs=[image_files, source_info],
            outputs=[result_output, download_file],
            show_progress=True
        )
        
        # Footer
        gr.Markdown("""
        ---
        💡 **Hướng dẫn sử dụng:**
        1. Kiểm tra trạng thái API trước khi xử lý
        2. Upload một hoặc nhiều ảnh đề thi TOPIK (JPG, PNG, etc.)
        3. Nhập thông tin nguồn đề thi (tùy chọn)
        4. Nhấn "Xử lý ảnh" và đợi kết quả
        5. File CSV sẽ xuất hiện trong phần "Tải xuống kết quả"
        
        🔧 **Hỗ trợ:** Tool này sử dụng PaddleOCR + Google Gemini để trích xuất và cấu trúc hóa dữ liệu đề thi.
        """)
    
    return demo

# Create demo for Gradio reload compatibility
demo = create_demo()

def main():
    """Main function to launch the app"""
    print(f"🚀 Starting TOPIK Gradio App (File Download Version)...")
    print(f"📡 API Base URL: {API_BASE_URL}")
    print(f"🌐 Gradio Host: {GRADIO_HOST}:{GRADIO_PORT}")
    
    demo.launch(
        server_name=GRADIO_HOST,
        server_port=GRADIO_PORT,
        share=False,
        show_error=True,
        quiet=False
    )

if __name__ == "__main__":
    main()
