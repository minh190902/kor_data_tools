import asyncio
from pathlib import Path
from datetime import datetime
import pandas as pd
from tqdm import tqdm

from typing import List, Dict, Any, Optional
from config import logger, TOPIK_PROCESSOR_LOGGER, TOPIKQuestion, TOPIKQuestionPydantic, TOPIKBatchResult
from core import TOPIKOCRProcessor, TOPIKStructurer

class TOPIKDataProcessor:
    """Tối ưu hóa processor với PydanticAI core - loại bỏ hoàn toàn legacy Gemini"""
    
    def __init__(self, 
                 gemini_api_key: str,
                 db_config: Optional[Dict[str, Any]] = None,
                 max_workers: int = 4,
                 save_to_db: bool = False):
        
        self.ocr_processor = TOPIKOCRProcessor()
        
        # Chỉ sử dụng PydanticAI structurer 
        self.pydantic_structurer = TOPIKStructurer(gemini_api_key)
        
        self.save_to_db = save_to_db
        # if self.save_to_db and db_config:
        #     self.db_manager = DatabaseManager(**db_config)
        # else:
        self.db_manager = None
        self.max_workers = max_workers
        
        # Stats tracking
        self.stats = {
            'processed_images': 0,
            'extracted_questions': 0,
            'saved_questions': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None,
            'processing_method': 'PydanticAI'
        }
    
    async def process_images_optimized(self, 
                                     image_paths: List[str], 
                                     source_info: str = "TOPIK") -> TOPIKBatchResult:
        """
        🚀 OPTIMIZED WORKFLOW: OCR tất cả ảnh trước → PydanticAI 1 lần duy nhất
        Tối ưu cho cross-image questions và giảm API calls với Docker logging
        """
        try:
            TOPIK_PROCESSOR_LOGGER.info(f"🔥 Starting optimized batch processing for {len(image_paths)} images")
            TOPIK_PROCESSOR_LOGGER.info(f"📊 Processing method: {self.stats['processing_method']}")
            
            # STEP 1: OCR tất cả ảnh SEQUENTIAL để tránh segmentation fault
            TOPIK_PROCESSOR_LOGGER.info("📄 Step 1: OCR all images sequentially (safer for memory)...")
            import sys
            sys.stdout.flush()  # Force flush for Docker
            
            # Process images one by one to prevent PaddleOCR memory conflicts
            valid_ocr_data = []
            successful_count = 0
            
            for i, image_path in enumerate(image_paths):
                try:
                    image_name = Path(image_path).name
                    TOPIK_PROCESSOR_LOGGER.info(f"🔍 Processing image {i+1}/{len(image_paths)}: {image_name}")
                    sys.stdout.flush()
                    
                    # Force garbage collection before each OCR to free memory
                    import gc
                    gc.collect()
                    
                    # Use single OCR instance to prevent conflicts
                    results = await asyncio.to_thread(self.ocr_processor.extract_text, image_path)
                    
                    if results and len(results) > 0:
                        valid_ocr_data.append((image_path, results))
                        successful_count += 1
                    else:
                        TOPIK_PROCESSOR_LOGGER.warning(f"⚠️ No OCR results for {image_name}")
                        self.stats['errors'] += 1
                    
                    sys.stdout.flush()
                    
                    # Small delay to prevent memory pressure
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    TOPIK_PROCESSOR_LOGGER.error(f"❌ OCR failed for {Path(image_path).name}: {e}")
                    self.stats['errors'] += 1
                    sys.stdout.flush()
                    
                    # Continue processing other images even if one fails
                    continue
            
            TOPIK_PROCESSOR_LOGGER.info(f"📝 OCR completed: {successful_count}/{len(image_paths)} images successful")
            sys.stdout.flush()  # Force flush for Docker
            
            if not valid_ocr_data:
                TOPIK_PROCESSOR_LOGGER.warning("❌ No valid OCR data to process")
                return TOPIKBatchResult(
                    questions=[], 
                    total_questions=0, 
                    source_images=[Path(p).name for p in image_paths],
                    processing_notes="No valid OCR data"
                )
            
            # STEP 2: Sắp xếp theo tên file để đảm bảo thứ tự đúng
            TOPIK_PROCESSOR_LOGGER.info("🔄 Step 2: Sorting OCR results by filename...")
            valid_ocr_data.sort(key=lambda x: Path(x[0]).name)
            sys.stdout.flush()  # Force flush for Docker
            
            # STEP 3: Gọi PydanticAI
            TOPIK_PROCESSOR_LOGGER.info("🤖 Step 3: Single PydanticAI call for all data...")
            sys.stdout.flush()  # Force flush for Docker
            structured_result = await self.pydantic_structurer.structure_batch_ocr(
                valid_ocr_data, source_info
            )
            
            # Update stats
            self.stats['processed_images'] = len(valid_ocr_data)
            self.stats['extracted_questions'] = structured_result.total_questions
            
            TOPIK_PROCESSOR_LOGGER.info(f"✅ Optimized processing completed: {structured_result.total_questions} questions extracted")
            sys.stdout.flush()  # Force flush for Docker
            return structured_result
            
        except Exception as e:
            logger.error(f"❌ Optimized batch processing failed: {e}")
            self.stats['errors'] += 1
            return TOPIKBatchResult(
                questions=[], 
                total_questions=0, 
                source_images=[Path(p).name for p in image_paths],
                processing_notes=f"Batch processing failed: {str(e)}"
            )
    
    def _validate_and_clean_questions(self, questions: List[TOPIKQuestionPydantic]) -> List[Dict[str, Any]]:
        """Convert Pydantic questions to dict format for CSV export"""
        cleaned = []
        
        for q in questions:
            try:
                # Convert Pydantic object to dict using its method
                cleaned_q = q.to_legacy_dict()
                cleaned.append(cleaned_q)
                
            except Exception as e:
                logger.warning(f"Failed to convert Pydantic question: {e}")
                continue
        
        return cleaned
    
    async def process_images_batch(self, 
                                     image_paths: List[str], 
                                     source_info: str = None) -> List[Dict[str, Any]]:
        """Process a batch of images using optimized PydanticAI workflow"""
        
        try:
            # Use the optimized workflow for batch processing
            batch_result = await self.process_images_optimized(image_paths, source_info)
            
            # Convert Pydantic objects to dict for backward compatibility
            all_questions = [q.to_legacy_dict() for q in batch_result.questions]
            
            return all_questions
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            self.stats['errors'] += 1
            return []
    
    async def process_directory(self, 
                              directory: str = None, 
                              pattern: str = "*.{jpg,jpeg,png,bmp,tiff}",
                              source_info: str = None) -> bool:
        """🚀 Enhanced directory processing with optimized workflow"""
        
        self.stats['start_time'] = datetime.now()
        
        try:
            # Lấy tất cả ảnh trong thư mục topik_images
            topik_images_dir = Path(__file__).parent.parent / 'topik_images'
            image_extensions = ['jpg', 'jpeg', 'png', 'bmp', 'tiff']
            image_paths = []
            for ext in image_extensions:
                image_paths.extend(sorted(topik_images_dir.glob(f'*.{ext}')))
            
            # Convert to absolute paths
            abs_image_paths = [str(p.resolve()) for p in image_paths]
            
            if not abs_image_paths:
                logger.error(f"Không tìm thấy ảnh nào trong thư mục topik_images")
                return False
                
            logger.info(f"Tìm thấy {len(abs_image_paths)} ảnh để xử lý trong topik_images")
            logger.info(f"🔥 Using {self.stats['processing_method']} workflow")
            
            # Determine source info
            if not source_info:
                source_info = f"TOPIK - {datetime.now().strftime('%Y%m%d')}"
            
            # 🚀 OPTIMIZED WORKFLOW: Process all images at once with PydanticAI
            logger.info("🚀 Using optimized PydanticAI batch processing...")
            batch_result = await self.process_images_optimized(abs_image_paths, source_info)
            
            # Convert Pydantic objects to dict for CSV export
            all_questions = [q.to_legacy_dict() for q in batch_result.questions]
            
            # Update stats
            self.stats['extracted_questions'] = len(all_questions)
            
            # Optional: Save to database
            if self.save_to_db and self.db_manager and all_questions:
                success = await self.db_manager.save_questions(all_questions)
                if success:
                    self.stats['saved_questions'] = len(all_questions)
                    logger.info(f"✅ Saved {len(all_questions)} questions to database")
                else:
                    logger.warning("❌ Database save failed")
            
            self.stats['end_time'] = datetime.now()
            
            # Export to CSV
            output_dir = directory or str(Path(__file__).parent.parent / 'output')
            await self._export_to_csv(all_questions, output_dir)
            
            # Print traditional stats
            self._print_stats()
            
            return True
            
        except Exception as e:
            logger.error(f"Lỗi xử lý thư mục: {e}")
            return False
    
    def _print_stats(self):
        """In thống kê xử lý với thông tin method được sử dụng"""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        print("\n" + "="*60)
        print("🚀 THỐNG KÊ XỬ LÝ TOPIK DATA - PYDANTIC AI WORKFLOW")
        print("="*60)
        print(f"📊 Phương pháp xử lý: {self.stats['processing_method']}")
        print(f"📸 Ảnh đã xử lý: {self.stats['processed_images']}")
        print(f"❓ Câu hỏi trích xuất: {self.stats['extracted_questions']}")
        print(f"💾 Câu hỏi đã lưu: {self.stats['saved_questions']}")
        print(f"❌ Lỗi: {self.stats['errors']}")
        print(f"⏱️ Thời gian xử lý: {duration:.2f} giây")
        if self.stats['processed_images'] > 0:
            print(f"🚄 Tốc độ trung bình: {self.stats['processed_images']/duration:.2f} ảnh/giây")
        if self.stats['extracted_questions'] > 0 and duration > 0:
            print(f"📈 Hiệu suất: {self.stats['extracted_questions']/duration:.2f} câu hỏi/giây")
        print("="*60)
    
    async def _export_to_csv(self, questions: List[Dict[str, Any]], output_dir: str):
        """Enhanced CSV export with better formatting"""
        try:
            if not questions:
                logger.warning("No questions to export")
                return
            
            # Create output directory if it doesn't exist
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Convert to DataFrame
            df = pd.DataFrame(questions)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_filename = f"topik_questions_{timestamp}.csv"
            csv_path = output_path / csv_filename
            
            # Export with UTF-8 BOM for Excel compatibility
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            
            logger.info(f"✅ Successfully exported {len(questions)} questions to {csv_path}")
            logger.info(f"📁 Output file: {csv_path.absolute()}")
            
        except Exception as e:
            logger.error(f"❌ CSV export failed: {e}")