#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gradio App for TOPIK Data Processing Tool
Giao diện web chuyên nghiệp để upload ảnh và xử lý đề thi TOPIK
"""

import asyncio
import aiohttp
import gradio as gr
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import json
import os
from datetime import datetime

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://ai-data-processing:8888")  # Docker internal URL
GRADIO_PORT = int(os.getenv("GRADIO_PORT", "7866"))
GRADIO_HOST = os.getenv("GRADIO_HOST", "0.0.0.0")

class TOPIKGradioApp:
    """Main Gradio application class"""
    
    def __init__(self, api_base_url: str = API_BASE_URL):
        self.api_base_url = api_base_url
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=300)  # 5 minutes timeout
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def check_api_health(self) -> Tuple[bool, str]:
        """Check if API is healthy"""
        try:
            session = await self._get_session()
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
    
    async def process_images_api(self, files: List[str], source_info: str) -> Dict[str, Any]:
        """Send images to API for processing"""
        try:
            session = await self._get_session()
            
            # Prepare multipart form data
            data = aiohttp.FormData()
            data.add_field('source_info', source_info)
            
            # Add files
            for file_path in files:
                if file_path and Path(file_path).exists():
                    file_name = Path(file_path).name
                    with open(file_path, 'rb') as f:
                        data.add_field('files', f.read(), filename=file_name, content_type='image/jpeg')
            
            # Send request
            async with session.post(f"{self.api_base_url}/process-images", data=data) as response:
                result = await response.json()
                
                if response.status == 200:
                    return {"success": True, "data": result}
                else:
                    return {"success": False, "error": result.get("detail", "Unknown error")}
                    
        except Exception as e:
            return {"success": False, "error": f"API request failed: {str(e)}"}
    
    async def get_download_url(self, filename: str) -> str:
        """Get download URL for a file"""
        return f"{self.api_base_url}/download/{filename}"
    
    async def list_output_files(self) -> List[Dict[str, Any]]:
        """List available output files"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.api_base_url}/list-outputs") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", {}).get("files", [])
                else:
                    return []
        except Exception as e:
            print(f"Error listing files: {e}")
            return []

# Global app instance
app = TOPIKGradioApp()

# Gradio Interface Functions
def sync_check_health() -> str:
    """Synchronous wrapper for health check"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        healthy, message = loop.run_until_complete(app.check_api_health())
        loop.close()
        return message
    except Exception as e:
        return f"❌ Lỗi kiểm tra API: {str(e)}"

def sync_process_images(files: List[str], source_info: str, progress=gr.Progress()) -> Tuple[str, str, str]:
    """Synchronous wrapper for image processing"""
    try:
        if not files:
            return "❌ Vui lòng upload ít nhất một ảnh", "", ""
        
        # Filter valid files
        valid_files = [f for f in files if f and Path(f).exists()]
        if not valid_files:
            return "❌ Không tìm thấy file hợp lệ", "", ""
        
        progress(0.1, desc="Đang kết nối API...")
        
        # Process with API
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        progress(0.3, desc="Đang xử lý ảnh...")
        result = loop.run_until_complete(app.process_images_api(valid_files, source_info))
        
        if result["success"]:
            data = result["data"]
            progress(0.8, desc="Đang tạo file CSV...")
            
            success_msg = f"""
✅ **Xử lý thành công!**

📊 **Thống kê:**
- Ảnh đã xử lý: {data['processed_images']}
- Câu hỏi tìm thấy: {data['extracted_questions']}
- File CSV: {data.get('csv_filename', 'N/A')}

💾 File CSV đã được tạo và sẵn sàng tải xuống.
            """
            
            download_url = ""
            if data.get('csv_filename'):
                download_url = loop.run_until_complete(app.get_download_url(data['csv_filename']))
            
            progress(1.0, desc="Hoàn thành!")
            loop.close()
            
            return success_msg, download_url, data.get('csv_filename', '')
        
        else:
            error_msg = f"❌ Xử lý thất bại: {result['error']}"
            loop.close()
            return error_msg, "", ""
            
    except Exception as e:
        return f"❌ Lỗi: {str(e)}", "", ""

def sync_list_files() -> str:
    """List available output files"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        files = loop.run_until_complete(app.list_output_files())
        loop.close()
        
        if not files:
            return "Chưa có file nào được tạo."
        
        file_list = "📁 **File CSV có sẵn:**\n\n"
        for file in files[:10]:  # Show last 10 files
            size_mb = file['size'] / (1024 * 1024)
            created = datetime.fromisoformat(file['created'].replace('Z', '+00:00')).strftime('%d/%m/%Y %H:%M')
            file_list += f"• **{file['filename']}** ({size_mb:.1f}MB) - {created}\n"
        
        return file_list
        
    except Exception as e:
        return f"❌ Lỗi: {str(e)}"

def create_interface():
    """Create the Gradio interface"""
    
    # Custom CSS for better styling
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
    .status-box {
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    """
    
    with gr.Blocks(
        title="TOPIK OCR Tool",
        theme=gr.themes.Soft(),
        css=css
    ) as interface:
        
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
                
                with gr.Row():
                    download_link = gr.HTML(label="Download Link")
                    csv_filename = gr.Textbox(visible=False)
        
        # File Management Section
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 📁 Quản lý file")
                
                refresh_btn = gr.Button("🔄 Làm mới danh sách", variant="secondary")
                file_list_output = gr.Markdown("Nhấn 'Làm mới' để xem danh sách file...")
        
        # Event handlers
        status_btn.click(
            fn=sync_check_health,
            outputs=status_output
        )
        
        process_btn.click(
            fn=sync_process_images,
            inputs=[image_files, source_info],
            outputs=[result_output, download_link, csv_filename],
            show_progress=True
        )
        
        refresh_btn.click(
            fn=sync_list_files,
            outputs=file_list_output
        )
        
        # Auto-check API status on load
        interface.load(
            fn=sync_check_health,
            outputs=status_output
        )
        
        # Footer
        gr.Markdown("""
        ---
        💡 **Hướng dẫn sử dụng:**
        1. Kiểm tra trạng thái API trước khi xử lý
        2. Upload một hoặc nhiều ảnh đề thi TOPIK (JPG, PNG, etc.)
        3. Nhập thông tin nguồn đề thi (tùy chọn)
        4. Nhấn "Xử lý ảnh" và đợi kết quả
        5. Tải xuống file CSV khi xử lý hoàn tất
        
        🔧 **Hỗ trợ:** Tool này sử dụng PaddleOCR + Google Gemini để trích xuất và cấu trúc hóa dữ liệu đề thi.
        """)
    
    return interface

def main():
    """Main function to launch the app"""
    print(f"🚀 Starting TOPIK Gradio App...")
    print(f"📡 API Base URL: {API_BASE_URL}")
    print(f"🌐 Gradio Host: {GRADIO_HOST}:{GRADIO_PORT}")
    
    interface = create_interface()
    
    # Launch the interface
    interface.launch(
        server_name=GRADIO_HOST,
        server_port=GRADIO_PORT,
        share=False,
        show_error=True,
        quiet=False,
        favicon_path=None,
        ssl_verify=False
    )

if __name__ == "__main__":
    main()
