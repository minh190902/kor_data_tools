import asyncio
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import time

import pandas as pd

from processors.topik_processor import TOPIKDataProcessor
from .schemas import ProcessingStatus, FileInfo
import logging

logger = logging.getLogger(__name__)


class TOPIKProcessingService:
    """Service layer for TOPIK processing operations"""
    
    def __init__(self):
        self.processor: Optional[TOPIKDataProcessor] = None
        self._initialized = False
    
    async def initialize_processor(self, gemini_api_key: str) -> bool:
        """Initialize the TOPIK processor"""
        try:
            self.processor = TOPIKDataProcessor(
                gemini_api_key=gemini_api_key,
                db_config=None,
                max_workers=2,  # Reduce for API stability
                save_to_db=False
            )
            logger.info("🔧 TOPIKDataProcessor instance created successfully")
            
            # Test if the processor components are working
            logger.info("🔧 Testing processor components...")
            if hasattr(self.processor, 'pydantic_structurer') and self.processor.pydantic_structurer:
                logger.info("✅ PydanticAI structurer initialized")
            else:
                logger.error("❌ PydanticAI structurer not initialized")
                return False
                
            if hasattr(self.processor, 'ocr_processor') and self.processor.ocr_processor:
                logger.info("✅ OCR processor initialized")
            else:
                logger.error("❌ OCR processor not initialized")
                return False
            
            self._initialized = True
            logger.info("✅ TOPIK Data Processor initialized for API (PydanticAI)")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize processor: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self._initialized = False
            return False
    
    def is_ready(self) -> bool:
        """Check if processor is ready"""
        return self._initialized and self.processor is not None
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.processor:
                # Perform any necessary cleanup
                logger.info("🧹 Cleaning up TOPIK processor...")
            self._initialized = False
            self.processor = None
        except Exception as e:
            logger.error(f"Error during processor cleanup: {e}")
    
    async def process_uploaded_images(self, files: List, source_info: str) -> ProcessingStatus:
        """Process uploaded image files"""
        if not self.processor:
            raise RuntimeError("Processor not initialized")
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            uploaded_files = []
            
            try:
                # Save uploaded files
                for file in files:
                    if not file.content_type.startswith('image/'):
                        raise ValueError(f"File {file.filename} is not an image")
                    
                    file_path = temp_path / file.filename
                    content = await file.read()
                    
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    
                    uploaded_files.append(str(file_path))
                    logger.info(f"Saved upload: {file.filename}")
                
                # Process all images using optimized workflow
                logger.info(f"🚀 Processing {len(uploaded_files)} images with PydanticAI...")
                
                batch_result = await self.processor.process_images_optimized(
                    uploaded_files, source_info
                )
                
                # Convert Pydantic objects to dict for CSV
                all_questions = [q.to_legacy_dict() for q in batch_result.questions]
                processed_count = batch_result.total_questions
                
                if not all_questions:
                    return ProcessingStatus(
                        success=False,
                        message="Không tìm thấy câu hỏi nào trong ảnh upload",
                        processed_images=len(uploaded_files),
                        extracted_questions=0
                    )
                
                # Create CSV
                csv_filename = await self._save_to_csv(all_questions)
                
                return ProcessingStatus(
                    success=True,
                    message=f"Xử lý thành công {len(uploaded_files)} ảnh, tìm thấy {len(all_questions)} câu hỏi (PydanticAI)",
                    processed_images=len(uploaded_files),
                    extracted_questions=len(all_questions),
                    csv_filename=csv_filename
                )
                
            except Exception as e:
                logger.error(f"Processing error: {e}")
                raise RuntimeError(f"Processing failed: {str(e)}")
    
    async def process_zip_file(self, zip_file, source_info: str) -> ProcessingStatus:
        """Process ZIP file containing images"""
        if not self.processor:
            raise RuntimeError("Processor not initialized")
        
        if not zip_file.filename.endswith('.zip'):
            raise ValueError("File must be a ZIP archive")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            try:
                # Save and extract ZIP
                zip_path = temp_path / zip_file.filename
                content = await zip_file.read()
                
                with open(zip_path, 'wb') as f:
                    f.write(content)
                
                # Extract ZIP
                extract_path = temp_path / "extracted"
                extract_path.mkdir()
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                
                # Find image files
                image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
                image_files = []
                
                for ext in image_extensions:
                    image_files.extend(extract_path.rglob(f"*{ext}"))
                    image_files.extend(extract_path.rglob(f"*{ext.upper()}"))
                
                if not image_files:
                    raise ValueError("No image files found in ZIP archive")
                
                # Process images
                all_questions = []
                processed_count = 0
                
                for image_path in image_files:
                    try:
                        questions = await self.processor.process_single_image(
                            image_path=str(image_path),
                            source_info=source_info
                        )
                        all_questions.extend(questions)
                        processed_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing {image_path}: {e}")
                        continue
                
                if not all_questions:
                    return ProcessingStatus(
                        success=False,
                        message="Không tìm thấy câu hỏi nào trong ZIP file",
                        processed_images=processed_count,
                        extracted_questions=0
                    )
                
                # Create and save CSV
                csv_filename = await self._save_to_csv(all_questions, prefix="zip")
                
                return ProcessingStatus(
                    success=True,
                    message=f"Xử lý ZIP thành công: {processed_count} ảnh, {len(all_questions)} câu hỏi",
                    processed_images=processed_count,
                    extracted_questions=len(all_questions),
                    csv_filename=csv_filename
                )
                
            except Exception as e:
                logger.error(f"ZIP processing error: {e}")
                raise RuntimeError(f"ZIP processing failed: {str(e)}")
    
    async def _save_to_csv(self, questions: List[dict], prefix: str = "") -> str:
        """Save questions to CSV file"""
        df = pd.DataFrame(questions)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix_str = f"{prefix}_" if prefix else ""
        csv_filename = f"topik_questions_{prefix_str}{timestamp}.csv"
        csv_path = Path("output") / csv_filename
        
        # Ensure output directory exists
        csv_path.parent.mkdir(exist_ok=True)
        
        # Save CSV
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        return csv_filename


class FileService:
    """Service for file operations"""
    
    @staticmethod
    def get_output_files() -> List[FileInfo]:
        """List available CSV output files"""
        output_dir = Path("output")
        
        if not output_dir.exists():
            return []
        
        csv_files = []
        for file_path in output_dir.glob("*.csv"):
            stat = file_path.stat()
            csv_files.append(FileInfo(
                filename=file_path.name,
                size=stat.st_size,
                created=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                download_url=f"/download/{file_path.name}"
            ))
        
        # Sort by creation time (newest first)
        csv_files.sort(key=lambda x: x.created, reverse=True)
        return csv_files
    
    @staticmethod
    def cleanup_old_files() -> int:
        """Clean up old output files (older than 24 hours)"""
        output_dir = Path("output")
        
        if not output_dir.exists():
            return 0
        
        current_time = time.time()
        deleted_count = 0
        
        for file_path in output_dir.glob("*.csv"):
            file_age = current_time - file_path.stat().st_ctime
            if file_age > 24 * 3600:  # 24 hours
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old file: {file_path.name}")
                except Exception as e:
                    logger.error(f"Error deleting {file_path.name}: {e}")
        
        return deleted_count
    
    @staticmethod
    def get_file_path(filename: str) -> Path:
        """Get path to output file"""
        return Path("output") / filename
