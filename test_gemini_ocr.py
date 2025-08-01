import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any
import json
import os

# Import từ project có sẵn
from core.structurer import TOPIKStructurer
from config import OCRResult, STRUCTURER_LOGGER

from dotenv import load_dotenv
load_dotenv()  # Tải biến môi trường từ .env file

class GeminiVisionOCR:
    """OCR processor sử dụng Gemini 2.0 Flash thông qua TOPIKStructurer"""
    
    def __init__(self, api_key: str = None):
        """Initialize với API key"""
        if api_key is None:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("Cần GEMINI_API_KEY trong environment hoặc truyền vào constructor")
        
        self.api_key = api_key
        self.structurer = TOPIKStructurer(api_key)
        print("✅ Gemini Vision OCR initialized với PydanticAI")
    
    async def extract_text_from_image(self, image_path: str) -> List[OCRResult]:
        """Extract text từ một ảnh sử dụng Gemini vision"""
        try:
            # Import thêm để sử dụng trực tiếp Gemini model
            from pydantic_ai.models.gemini import GeminiModel
            from pydantic_ai.providers.google_gla import GoogleGLAProvider
            from pydantic_ai import Agent
            import base64
            
            # Đọc và encode ảnh
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Tạo model riêng cho OCR (không cần structured output)
            model = GeminiModel('gemini-2.5-flash', provider=GoogleGLAProvider(api_key=self.api_key))
            
            # Tạo agent đơn giản cho OCR
            ocr_agent = Agent(
                model=model,
                system_prompt="""
                Bạn là AI chuyên OCR. Nhiệm vụ: trích xuất TẤT CẢ text từ ảnh.
                
                Yêu cầu:
                1. Trích xuất TOÀN BỘ text (tiếng Hàn, tiếng Anh, số, ký hiệu)
                2. Giữ nguyên format và cấu trúc
                3. Sắp xếp theo thứ tự đọc tự nhiên (trên xuống dưới, trái sang phải)
                4. Mỗi text block trên một dòng riêng biệt
                5. Không thêm giải thích, chỉ trả về text thuần túy
                
                Trả về format: mỗi dòng là một text block được phát hiện.
                """
            )
            
            # Tạo prompt với ảnh
            prompt = "Trích xuất tất cả text từ ảnh này:"
            
            # Gửi request với ảnh
            result = await ocr_agent.run(
                prompt,
                message_parts=[
                    {"type": "text", "text": prompt},
                    {
                        "type": "image", 
                        "image": image_data,
                        "image_format": "auto"
                    }
                ]
            )
            
            # Parse kết quả
            response_text = result.data if hasattr(result, 'data') else str(result)
            return self._parse_to_ocr_results(response_text)
            
        except Exception as e:
            print(f"❌ Gemini Vision OCR failed for {image_path}: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _parse_to_ocr_results(self, response_text: str) -> List[OCRResult]:
        """Parse response thành OCRResult objects"""
        try:
            # Split thành các dòng và tạo OCRResult
            lines = [line.strip() for line in str(response_text).split('\n') if line.strip()]
            
            results = []
            for i, line in enumerate(lines):
                if line:
                    # Tạo default bounding box
                    box = [[0, i*20], [200, i*20], [200, (i+1)*20], [0, (i+1)*20]]
                    results.append(OCRResult(
                        box=box,
                        text=line,
                        confidence=0.95  # Default confidence
                    ))
            
            return results
            
        except Exception as e:
            print(f"⚠️ Parse warning: {e}")
            return [OCRResult(
                box=[[0, 0], [100, 0], [100, 20], [0, 20]],
                text=str(response_text),
                confidence=0.9
            )]

async def test_gemini_vision_ocr_folder(image_folder: str, api_key: str = None):
    """Test Gemini Vision OCR performance sử dụng TOPIKStructurer"""
    try:
        ocr = GeminiVisionOCR(api_key)
    except ValueError as e:
        print(f"❌ {e}")
        print("💡 Hướng dẫn:")
        print("   1. Lấy API key từ: https://aistudio.google.com/app/apikey")
        print("   2. Set environment: set GEMINI_API_KEY=your_api_key")
        print("   3. Hoặc truyền trực tiếp: python test_gemini_ocr.py folder --api-key your_key")
        return
    
    image_dir = Path(image_folder)
    image_files = list(image_dir.glob('*.png')) + list(image_dir.glob('*.jpg')) + list(image_dir.glob('*.jpeg'))
    print(f"Found {len(image_files)} images in {image_folder}")
    
    # Tạo output directory
    output_dir = Path("output") / "gemini_vision_ocr_results"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    total_time = 0
    results_count = 0
    all_results = {}
    
    for idx, img_path in enumerate(image_files):
        print(f"\n[{idx+1}/{len(image_files)}] Processing: {img_path.name}")
        start = time.time()
        
        try:
            # Thực hiện OCR với Gemini Vision
            results = await ocr.extract_text_from_image(str(img_path))
            
            # Log kết quả
            print(f"  -> {len(results)} text blocks extracted:")
            for i, result in enumerate(results):
                if result.text.strip():
                    print(f"     {i+1}. '{result.text}' (confidence: {result.confidence:.2f})")
            
            elapsed = time.time() - start
            print(f"  -> Processing time: {elapsed:.2f}s")
            
            # Lưu kết quả
            all_results[img_path.name] = {
                'processing_time': elapsed,
                'text_blocks': [
                    {
                        'text': r.text,
                        'confidence': r.confidence
                    } for r in results
                ]
            }
            
            total_time += elapsed
            results_count += len(results)
            
        except Exception as e:
            print(f"  -> ❌ Error processing {img_path.name}: {e}")
            all_results[img_path.name] = {
                'processing_time': 0,
                'error': str(e),
                'text_blocks': []
            }
        
        # Rate limiting để tránh quota exceeded
        if idx < len(image_files) - 1:  # Không sleep ở file cuối
            print("  -> Waiting 2s to avoid rate limit...")
            await asyncio.sleep(2)  # 2 giây giữa các requests
    
    # Lưu kết quả tổng hợp
    summary_file = output_dir / "gemini_vision_ocr_summary.json"
    summary = {
        'total_images': len(image_files),
        'total_time': total_time,
        'average_time_per_image': total_time / len(image_files) if image_files else 0,
        'total_text_blocks': results_count,
        'average_blocks_per_image': results_count / len(image_files) if image_files else 0,
        'results': all_results
    }
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n=== GEMINI VISION OCR SUMMARY ===")
    print(f"Total images: {len(image_files)}")
    print(f"Total OCR time: {total_time:.2f}s")
    print(f"Average per image: {total_time/len(image_files):.2f}s" if image_files else "N/A")
    print(f"Total text blocks: {results_count}")
    print(f"Average text blocks per image: {results_count/len(image_files):.1f}" if image_files else "N/A")
    print(f"Results saved to: {summary_file}")

def test_gemini_batch_processing(image_folder: str, api_key: str = None):
    """Test batch processing với TOPIKStructurer (như workflow thực tế)"""
    try:
        if api_key is None:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("Cần GEMINI_API_KEY")
        
        structurer = TOPIKStructurer(api_key)
        
        image_dir = Path(image_folder)
        image_files = list(image_dir.glob('*.png')) + list(image_dir.glob('*.jpg')) + list(image_dir.glob('*.jpeg'))
        print(f"Found {len(image_files)} images for batch processing")
        
        # Tạo fake OCR data để test structurer
        all_ocr_data = []
        for img_path in image_files:
            # Tạo fake OCR results (trong thực tế sẽ từ PaddleOCR)
            fake_ocr = [
                OCRResult(box=[[0, 0], [100, 0], [100, 20], [0, 20]], 
                         text=f"Sample text from {img_path.name}", 
                         confidence=0.9)
            ]
            all_ocr_data.append((str(img_path), fake_ocr))
        
        # Test batch processing
        async def run_batch():
            print("\n🚀 Testing batch processing với TOPIKStructurer...")
            start = time.time()
            
            result = await structurer.structure_batch_ocr(
                all_ocr_data=all_ocr_data,
                source_info="Test TOPIK"
            )
            
            elapsed = time.time() - start
            
            print(f"✅ Batch processing completed in {elapsed:.2f}s")
            print(f"📊 Results: {result.total_questions} questions from {len(result.source_images)} images")
            print(f"📝 Processing notes: {result.processing_notes}")
            
            # Lưu kết quả
            output_dir = Path("output") / "gemini_batch_results"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            result_file = output_dir / "batch_processing_result.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)
            
            print(f"💾 Results saved to: {result_file}")
        
        return asyncio.run(run_batch())
        
    except Exception as e:
        print(f"❌ Batch processing failed: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_gemini_ocr.py <image_folder> [--api-key YOUR_KEY] [--mode MODE]")
        print("Modes:")
        print("  ocr    - Test individual image OCR (default)")
        print("  batch  - Test batch processing với structurer")
        print("Environment: set GEMINI_API_KEY=your_api_key")
    else:
        image_folder = sys.argv[1]
        api_key = None
        mode = "ocr"
        
        # Parse arguments
        api_key = os.getenv('GEMINI_API_KEY')
        
        if '--mode' in sys.argv:
            try:
                mode_idx = sys.argv.index('--mode') + 1
                mode = sys.argv[mode_idx]
            except IndexError:
                print("❌ Missing mode after --mode")
                exit(1)
        
        # Run test theo mode
        if mode == "batch":
            test_gemini_batch_processing(image_folder, api_key)
        else:
            asyncio.run(test_gemini_vision_ocr_folder(image_folder, api_key))