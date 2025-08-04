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
                instructions="""
You are an AI specialist for analyzing TOPIK (Test of Proficiency in Korean) exam papers. 
Your task: Analyze ALL OCR data from multiple images and extract ALL questions into structured format.

# CRITICAL - Handle Cross-Image Questions:
- If questions are split across multiple images (e.g., image 1 has "34", image 2 has content), MERGE THEM
- Pay special attention to these cases:
  * Question number in one image, content in another
  * Long passages split across multiple images  
  * General instructions (※ [31-33]) applying to multiple images

# Processing Rules:
1. SORT by question order (question_number)
2. MERGE information from multiple images for the same question
3. Ensure NO questions are missed
4. Create unique question_id for each question (format: T{{Level}}{{Skill}}_{Test}_{Number}) (e.g., T1R_EX_31)
    + level: (e.g., 1, 2)
    + skill: "읽기" -> "R", "듣기" -> "L", "쓰기" -> "W"
5. Fill in all extractable information completely
6. skill_area must be one of: "읽기", "듣기", "쓰기" (in Korean)
7. question_number must be a positive integer
8. correct_answer if available must be 1, 2, 3, or 4

# Special Notes:
- If you see patterns like "34)", "35)" in image A and question content in image B → merge them
- General instructions like "※ [31-33] 다음 글을 읽고 물음에 답하시오" apply to all questions in that range
- Long passages may span multiple images → merge complete content

IMPORTANT: All Korean text content (questions, options, passages) must be preserved in Korean.
Only structural elements and metadata can be in English.
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
    
    def _filter_ocr_text(self, ocr_results: List[OCRResult], min_confidence: float = 0.7) -> str:
        """Filter OCR results by confidence and remove noise"""
        filtered_texts = []
        for result in ocr_results:
            text = result.text.strip()
            # Skip very short noise text or low confidence
            if result.confidence < min_confidence:
                continue

            filtered_texts.append(text)
        
        return "\n".join(filtered_texts)
    
    def _create_compact_context(self, all_ocr_data: List[tuple[str, List[OCRResult]]]) -> tuple[str, List[str]]:
        """Create compact context for AI processing"""
        context_parts = []
        source_images = []
        
        for i, (image_path, ocr_results) in enumerate(all_ocr_data):
            image_name = Path(image_path).name
            source_images.append(image_name)
            
            # Filter and compact OCR text
            filtered_text = self._filter_ocr_text(ocr_results)
            
            if filtered_text:  # Only add if we have meaningful content
                context_parts.append(f"IMG{i+1}:\n{filtered_text}")
        
        return "\n\n".join(context_parts), source_images
    
    async def structure_batch_ocr(self, 
                                all_ocr_data: List[tuple[str, List[OCRResult]]], 
                                source_info: str = "TOPIK") -> TOPIKBatchResult:
        """
        🚀 Structure toàn bộ OCR data từ nhiều ảnh với PydanticAI (Token optimized)
        
        Args:
            all_ocr_data: List of (image_path, ocr_results) tuples
            source_info: Thông tin nguồn
        """
        try:
            STRUCTURER_LOGGER.info(f"🤖 Starting PydanticAI batch processing for {len(all_ocr_data)} images")
            import sys
            sys.stdout.flush()  # Force flush for Docker
            
            # Create compact context
            compact_context, source_images = self._create_compact_context(all_ocr_data)
            
            # Check if we have meaningful content
            if not compact_context.strip():
                STRUCTURER_LOGGER.warning("⚠️ No meaningful OCR content found")
                return TOPIKBatchResult(
                    questions=[],
                    total_questions=0,
                    source_images=source_images,
                    processing_notes="No meaningful OCR content extracted"
                )
            
            # Compact prompt
            prompt = f"{source_info} exam ({len(all_ocr_data)} images):\n\n{compact_context}"
            
            # Log token estimation (rough)
            token_estimate = len(prompt.split())
            STRUCTURER_LOGGER.info(f"📊 Token estimate: ~{token_estimate} words")
            
            # Gọi PydanticAI agent
            STRUCTURER_LOGGER.info("🔥 Calling PydanticAI for structured extraction...")
            sys.stdout.flush()  # Force flush for Docker
            result = await self.agent.run(prompt)
            
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
