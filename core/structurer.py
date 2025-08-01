import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import threading

# PydanticAI imports - install with: pip install pydantic-ai
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider

from config import logger, STRUCTURER_LOGGER, OCRResult, TOPIKBatchResult, TOPIKQuestionPydantic


class TOPIKStructurer:
    """Enhanced structurer using PydanticAI with model caching and singleton pattern"""
    
    _instance = None
    _lock = threading.Lock()
    _model = None
    _agent = None
    _initialized = False
    _current_api_key = None
    
    def __new__(cls, api_key: str):
        """Singleton pattern with API key validation"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TOPIKStructurer, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, api_key: str):
        """Initialize PydanticAI agent with model caching"""
        if not self._initialized or self._current_api_key != api_key:
            with self._lock:
                if not self._initialized or self._current_api_key != api_key:
                    STRUCTURER_LOGGER.info("🔄 Initializing PydanticAI structurer (cached model)...")
                    self._initialize_agent(api_key)
                    self._initialized = True
                    self._current_api_key = api_key
                    STRUCTURER_LOGGER.info("✅ PydanticAI structurer ready (cached for reuse)")
                    import sys
                    sys.stdout.flush()  # Force flush for Docker
                else:
                    STRUCTURER_LOGGER.info("♻️ Reusing existing PydanticAI agent")
        else:
            STRUCTURER_LOGGER.info("♻️ Reusing existing PydanticAI agent")
    
    def _initialize_agent(self, api_key: str):
        """Initialize the PydanticAI agent with Gemini model"""
        try:
            logger.info("🤖 Creating Gemini model connection...")
            self._model = GeminiModel('gemini-2.5-flash', provider=GoogleGLAProvider(api_key=api_key))
            
            logger.info("🧠 Setting up PydanticAI agent with system prompt...")
            self._agent = Agent(
                model=self._model,
                output_type=TOPIKBatchResult,
                system_prompt="""
Bạn là AI chuyên phân tích đề thi TOPIK. Nhiệm vụ: phân tích TOÀN BỘ dữ liệu OCR từ nhiều ảnh 
và trích xuất TẤT CẢ câu hỏi thành format có cấu trúc.

🔥 QUAN TRỌNG - Xử lý Cross-Image Questions:
- Nếu câu hỏi bị chia làm nhiều ảnh (VD: ảnh 1 có "34", ảnh 2 có nội dung), hãy GHÉP CHÚNG LẠI
- Đặc biệt chú ý các trường hợp:
  * Số câu hỏi ở ảnh này, nội dung ở ảnh khác  
  * Đoạn văn dài chia nhiều ảnh
  * Chỉ thị chung (※ [31-33]) áp dụng cho nhiều ảnh

📋 Quy tắc xử lý:
1. SẮP XẾP theo thứ tự câu hỏi (question_number)
2. GHÉP thông tin từ nhiều ảnh cho cùng 1 câu hỏi
3. Đảm bảo KHÔNG BỊ THIẾU câu hỏi nào
4. Tạo question_id duy nhất cho mỗi câu (format: T{Level}{Skill}_{Test}_{Number})
5. Điền đầy đủ thông tin có thể trích xuất được
6. skill_area phải là một trong: "읽기", "듣기", "쓰기"
7. question_number phải là số nguyên dương
8. correct_answer nếu có phải là 1, 2, 3, hoặc 4

💡 Lưu ý đặc biệt:
- Nếu thấy pattern như "34)", "35)" trong ảnh A và nội dung câu hỏi trong ảnh B → ghép lại
- Chỉ thị chung như "※ [31-33] 다음 글을 읽고 물음에 답하시오" áp dụng cho tất cả câu trong range
- Đoạn văn dài có thể span nhiều ảnh → ghép đầy đủ nội dung

Trả về structured data theo Pydantic schema với:
- questions: List[TOPIKQuestionPydantic] 
- total_questions: int
- source_images: List[str]
- processing_notes: str (ghi chú quá trình xử lý)
            """
            )
            logger.info("✅ PydanticAI agent initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize PydanticAI agent: {e}")
            raise RuntimeError(f"PydanticAI initialization failed: {e}")
    
    @property
    def agent(self):
        """Thread-safe access to PydanticAI agent"""
        return self._agent
    
    async def structure_batch_ocr(self, 
                                all_ocr_data: List[tuple[str, List[OCRResult]]], 
                                source_info: str = "TOPIK") -> TOPIKBatchResult:
        """
        🚀 Structure toàn bộ OCR data từ nhiều ảnh với PydanticAI
        
        Args:
            all_ocr_data: List of (image_path, ocr_results) tuples
            source_info: Thông tin nguồn
        """
        try:
            STRUCTURER_LOGGER.info(f"🤖 Starting PydanticAI batch processing for {len(all_ocr_data)} images")
            import sys
            sys.stdout.flush()  # Force flush for Docker
            
            # Chuẩn bị input context cho AI
            context_parts = []
            source_images = []
            
            for i, (image_path, ocr_results) in enumerate(all_ocr_data):
                image_name = Path(image_path).name
                source_images.append(image_name)
                
                # Format OCR với confidence scores
                ocr_text = "\n".join([f"[Conf:{result.confidence:.2f}] {result.text}" 
                                    for result in ocr_results if result.text.strip()])
                
                context_parts.append(f"""
=== ẢNH {i+1}: {image_name} ===
{ocr_text}
""")
            
            # Tạo prompt với toàn bộ context
            full_context = f"""
Nguồn đề thi: {source_info}
Tổng số ảnh cần xử lý: {len(all_ocr_data)}

{''.join(context_parts)}

Hãy phân tích TOÀN BỘ dữ liệu trên và trích xuất tất cả câu hỏi.
Đặc biệt chú ý ghép nối thông tin từ nhiều ảnh cho cùng 1 câu hỏi.
            """
            
            # Gọi PydanticAI agent
            STRUCTURER_LOGGER.info("🔥 Calling PydanticAI for structured extraction...")
            sys.stdout.flush()  # Force flush for Docker
            result = await self.agent.run(full_context)
            
            STRUCTURER_LOGGER.info(f"✅ PydanticAI completed: {result.output.total_questions} questions from {len(all_ocr_data)} images")
            sys.stdout.flush()  # Force flush for Docker
            
            # Add source images info
            result.output.source_images = source_images
            
            return result.output
            
        except Exception as e:
            logger.error(f"❌ PydanticAI structuring failed: {e}")
            # Return empty result on failure
            return TOPIKBatchResult(
                questions=[],
                total_questions=0,
                source_images=[Path(img[0]).name for img in all_ocr_data],
                processing_notes=f"Processing failed: {str(e)}"
            )
