#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Improved Gradio app with modern UI and file management
"""

import gradio as gr
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import os
import requests
from datetime import datetime
import tempfile
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from utils.file_manager import file_manager

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://ai-data-processing:8888")
GRADIO_PORT = int(os.getenv("GRADIO_PORT", "7866"))
GRADIO_HOST = os.getenv("GRADIO_HOST", "0.0.0.0")

class SimpleAPIClient:
    """Simplified API client with basic functionality"""
    
    def __init__(self, api_base_url: str = API_BASE_URL):
        self.api_base_url = api_base_url
        self.temp_dir = Path(tempfile.gettempdir()) / "topik_downloads"
        self.temp_dir.mkdir(exist_ok=True)
    
    def check_health(self) -> str:
        """Check API health status"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return "🟢 API is running normally"
                else:
                    return f"🟡 API has issues: {data.get('message', 'Unknown error')}"
            else:
                return f"🔴 API error (code {response.status_code})"
        except requests.exceptions.Timeout:
            return "🔴 API timeout"
        except Exception as e:
            return f"🔴 Cannot connect: {str(e)}"
    
    def process_images(self, files: List[str], source_info: str) -> Tuple[Dict[str, Any], Optional[str]]:
        """Process images with simplified error handling"""
        try:
            files_data = []
            for file_path in files:
                if file_path and Path(file_path).exists():
                    with open(file_path, 'rb') as f:
                        files_data.append(('files', (Path(file_path).name, f.read(), 'image/jpeg')))
            
            data = {'source_info': source_info}
            response = requests.post(f"{self.api_base_url}/process-images", 
                                   files=files_data, data=data, timeout=300)
            
            result = response.json()
            
            if response.status_code == 200:
                # Try to download the file
                downloaded_file = None
                if result.get("csv_filename"):
                    downloaded_file = self.download_file(result["csv_filename"])
                return {"success": True, "data": result}, downloaded_file
            else:
                return {"success": False, "error": result.get("detail", "Unknown error")}, None
                
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Processing timeout"}, None
        except Exception as e:
            return {"success": False, "error": f"Processing error: {str(e)}"}, None
    
    def download_file(self, filename: str) -> Optional[str]:
        """Download file from API"""
        try:
            response = requests.get(f"{self.api_base_url}/download/{filename}", timeout=30)
            if response.status_code == 200:
                local_file_path = self.temp_dir / filename
                with open(local_file_path, 'wb') as f:
                    f.write(response.content)
                return str(local_file_path)
            return None
        except Exception:
            return None

# Global API client
api_client = SimpleAPIClient()

def check_health() -> str:
    """Simple health check with auto cleanup"""
    health_status = api_client.check_health()
    cleanup_msg = file_manager.auto_cleanup_if_needed()
    return f"{health_status}\n\n📁 **Storage:** {cleanup_msg}"

def get_storage_info() -> str:
    """Get basic storage information"""
    try:
        stats = file_manager.get_storage_stats()
        return f"""
📊 **Storage Status:**
- Files: {stats['total_files']}
- Size: {stats['total_size_mb']} MB
- Recent files: {stats['age_distribution']['0-1_days']} today, {stats['age_distribution']['2-7_days']} this week
"""
    except Exception as e:
        return f"❌ Error: {e}"

def cleanup_files() -> str:
    """Simple cleanup with basic feedback"""
    try:
        deleted_count, freed_mb = file_manager.cleanup_old_files(max_age_days=1, max_files=30)
        if deleted_count > 0:
            return f"🧹 Cleaned up {deleted_count} files, freed {freed_mb:.1f}MB"
        else:
            return "✅ No cleanup needed"
    except Exception as e:
        return f"❌ Cleanup error: {e}"

def process_images(files: List[str], source_info: str, progress=gr.Progress()) -> Tuple[str, Optional[str], str]:
    """Simplified image processing"""
    try:
        if not files:
            return "❌ Please upload images", None, get_storage_info()
        
        valid_files = [f for f in files if f and Path(f).exists()]
        if not valid_files:
            return "❌ No valid files found", None, get_storage_info()
        
        progress(0.2, desc="🔍 Checking API...")
        
        # Check API health
        health = api_client.check_health()
        if "🔴" in health:
            return f"❌ API not ready:\n{health}", None, get_storage_info()
        
        progress(0.5, desc="📤 Processing images...")
        
        result, downloaded_file = api_client.process_images(valid_files, source_info)
        
        if result["success"]:
            data = result["data"]
            progress(1.0, desc="✅ Complete!")
            
            success_msg = f"""
✅ **Success!**
- Images: {data.get('processed_images', 0)}
- Questions: {data.get('extracted_questions', 0)}
- Time: {datetime.now().strftime('%H:%M:%S')}
"""
            return success_msg, downloaded_file, get_storage_info()
        else:
            return f"❌ **Failed:** {result.get('error', 'Unknown error')}", None, get_storage_info()
            
    except Exception as e:
        return f"❌ **Error:** {str(e)}", None, get_storage_info()

def create_demo():
    """Create simplified Gradio interface"""
    
    # Minimal CSS
    css = """
    .gradio-container {
        max-width: 1000px !important;
        margin: auto !important;
    }
    
    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
    }
    
    .main-header h1 {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    
    .card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    """
    
    js_func = """
    function refresh() {
        const url = new URL(window.location);
        if (url.searchParams.get('__theme') !== 'light') {
            url.searchParams.set('__theme', 'light');
            window.location.href = url.href;
        }
    }
    """
    
    with gr.Blocks(
        title="TOPIK OCR Tool",
        theme=gr.themes.Soft(primary_hue="blue"),
        css=css,
        js=js_func
    ) as demo:
        
        # Header
        gr.Markdown("""
        <div class="main-header">
            <h1>🇰🇷 TOPIK OCR Tool</h1>
            <p>Convert TOPIK exam images to structured data</p>
        </div>
        """)
        
        # Main Processing
        with gr.Column():
            with gr.Group(elem_classes=["card"]):
                gr.Markdown("### 📤 Process Images")
                
                image_files = gr.File(
                    label="Upload exam images",
                    file_count="multiple",
                    file_types=["image"]
                )
                
                with gr.Row():
                    source_info = gr.Textbox(
                        label="Exam info",
                        value="TOPIK Practice Test",
                        placeholder="Example: TOPIK I 읽기 - 70회"
                    )
                    
                    process_btn = gr.Button("🚀 Process", variant="primary")
        
        # Results
        with gr.Column():
            with gr.Group(elem_classes=["card"]):
                gr.Markdown("### 📊 Results")
                result_output = gr.Markdown("Ready to process...")
                download_file = gr.File(label="📥 Download CSV", visible=True)
        
        # System Status
        with gr.Column():
            with gr.Group(elem_classes=["card"]):
                gr.Markdown("### ⚙️ System")
                with gr.Row():
                    status_btn = gr.Button("🔍 API Status")
                    storage_btn = gr.Button("📁 Storage") 
                    cleanup_btn = gr.Button("🧹 Cleanup")
                system_output = gr.Markdown("Click buttons above for info...")
        
        # Event handlers
        status_btn.click(
            fn=check_health,
            outputs=system_output
        )
        
        storage_btn.click(
            fn=get_storage_info,
            outputs=system_output
        )
        
        cleanup_btn.click(
            fn=cleanup_files,
            outputs=system_output
        )
        
        process_btn.click(
            fn=process_images,
            inputs=[image_files, source_info],
            outputs=[result_output, download_file, system_output],
            show_progress=True
        )
        
        # Simple Footer
        gr.Markdown("""
        <div style="text-align: center; padding: 1rem; margin-top: 1rem; border-top: 1px solid #e5e7eb;">
            <p style="margin: 0; color: #6b7280;">
                🔧 PaddleOCR + Gemini AI • 🧹 Auto cleanup • 💾 Max 50 files
            </p>
        </div>
        """)
    
    return demo

# Create demo for Gradio reload compatibility
demo = create_demo()

def main():
    """Launch the simplified app"""
    print(f"🚀 Starting TOPIK Gradio App...")
    print(f"📡 API: {API_BASE_URL}")
    print(f"🌐 Server: {GRADIO_HOST}:{GRADIO_PORT}")
    
    demo.launch(
        server_name=GRADIO_HOST,
        server_port=GRADIO_PORT,
        share=False
    )

if __name__ == "__main__":
    main()