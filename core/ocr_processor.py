from PIL import Image
from pathlib import Path
from typing import List, Optional
import threading

from config import logger, OCR_LOGGER, OCRResult
from config.ocr_config import DEFAULT_OCR_CONFIGS

class TOPIKOCRProcessor:
    """Thread-safe OCR processor with model caching and memory management for PaddleOCR v3.1+"""
    
    _instance = None
    _lock = threading.Lock()
    _ocr_model = None
    _initialized = False
    _processing_lock = threading.RLock()  # Reentrant lock for processing
    
    def __new__(cls):
        """Singleton pattern to reuse OCR model across instances"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TOPIKOCRProcessor, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize PaddleOCR with model caching - only once per application lifecycle"""
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    # OCR_LOGGER.info("🔄 Initializing PaddleOCR processor (singleton)...")
                    self._initialize_ocr()
                    self._initialized = True
                    # OCR_LOGGER.info("✅ PaddleOCR processor ready (cached for reuse)")
                    import sys
                    sys.stdout.flush()  # Force flush for Docker
                else:
                    OCR_LOGGER.info("♻️ Reusing existing PaddleOCR instance")
        else:
            OCR_LOGGER.info("♻️ Reusing existing PaddleOCR instance")
    
    @property
    def ocr(self):
        """Thread-safe access to OCR model"""
        return self._ocr_model
    
    def _initialize_ocr(self):
        """Initialize PaddleOCR with robust configuration and dependency checking"""
        try:
            # Check for required dependencies first
            missing_deps = []
            
            try:
                from paddleocr import PaddleOCR
            except ImportError as e:
                missing_deps.append(f"paddleocr ({str(e)})")
            
            if missing_deps:
                error_msg = f"Missing dependencies: {', '.join(missing_deps)}"
                logger.error(f"❌ {error_msg}")
                raise RuntimeError(error_msg)
            
            logger.info("✅ All required dependencies found, initializing PaddleOCR...")
            
            # Use configurations from config file
            configs = DEFAULT_OCR_CONFIGS
            
            for i, config in enumerate(configs):
                try:
                    logger.info(f"Trying OCR configuration {i+1}/{len(configs)}")
                    logger.debug(f"Config: {config}")
                    
                    self._ocr_model = PaddleOCR(**config)
                    logger.info(f"✅ PaddleOCR initialized successfully with config {i+1}")
                    return
                    
                except Exception as e:
                    logger.warning(f"Configuration {i+1} failed: {e}")
                    # Log more details for setuptools errors
                    if "setuptools" in str(e).lower():
                        logger.error(f"❌ setuptools error in config {i+1}: {e}")
                    continue
            
            raise RuntimeError("All OCR configurations failed")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize PaddleOCR: {e}")
            raise RuntimeError(f"PaddleOCR initialization failed: {e}")
    
    def _normalize_path(self, image_path: str) -> str:
        """Normalize path to avoid Windows/Unicode issues"""
        try:
            # Convert to absolute path with forward slashes
            abs_path = Path(image_path).resolve()
            normalized = str(abs_path).replace('\\', '/')
            
            # Check if path contains problematic characters
            try:
                normalized.encode('ascii')
                return normalized
            except UnicodeEncodeError:
                # Create temp copy with ASCII-safe name
                import tempfile
                import shutil
                
                temp_dir = tempfile.mkdtemp()
                temp_name = f"temp_ocr_{abs_path.suffix}"
                temp_path = Path(temp_dir) / temp_name
                shutil.copy2(abs_path, temp_path)
                logger.info(f"Created temp copy: {temp_path}")
                return str(temp_path)
                
        except Exception as e:
            logger.warning(f"Path normalization failed: {e}, using original")
            return image_path
    
    def _validate_image(self, image_path: str) -> bool:
        """Validate image file before OCR"""
        try:
            if not Path(image_path).is_file():
                logger.error(f"Image file not found: {image_path}")
                return False
            
            # Check file size
            file_size = Path(image_path).stat().st_size
            if file_size == 0:
                logger.error(f"Image file is empty: {image_path}")
                return False
            
            # Try to open with PIL to validate format
            with Image.open(image_path) as img:
                if img.size[0] < 10 or img.size[1] < 10:
                    logger.error(f"Image too small: {img.size}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Image validation failed: {e}")
            return False
    
    def extract_text(self, image_path: str) -> List[OCRResult]:
        """Thread-safe text extraction with memory management to prevent segfaults"""
        temp_path = None
        
        # Use processing lock to prevent concurrent OCR calls that cause segfaults
        with self._processing_lock:
            try:
                if not self.ocr:
                    OCR_LOGGER.error("OCR not initialized")
                    return []
                
                # Validate image
                if not self._validate_image(image_path):
                    return []
                
                # Normalize path
                safe_path = self._normalize_path(image_path)
                temp_path = safe_path if safe_path != image_path else None
                
                image_name = Path(image_path).name
                
                # Use predict method with error handling for segfaults
                try:
                    # Force garbage collection before OCR to free memory
                    import gc
                    gc.collect()
                    
                    results = self.ocr.predict(safe_path)
                    
                    if not results or len(results) == 0:
                        OCR_LOGGER.warning(f"❌ No OCR results for {image_name}")
                        return []
                                        
                except Exception as e:
                    OCR_LOGGER.error(f"❌ OCR predict failed for {image_name}: {e}")
                    return []
                
                # Process results - handle PaddleOCR v3.1+ OCRResult format
                ocr_results = []
                ocr_result = results[0]  # First page result (OCRResult object)
                
                # Extract data from OCRResult object (it's dict-like)
                if 'rec_texts' in ocr_result and 'rec_scores' in ocr_result:
                    texts = ocr_result['rec_texts']
                    scores = ocr_result['rec_scores']
                    
                    # Get boxes if available
                    if 'rec_polys' in ocr_result:
                        boxes = ocr_result['rec_polys']
                    elif 'dt_polys' in ocr_result:
                        boxes = ocr_result['dt_polys']
                    else:
                        boxes = []
                    
                    OCR_LOGGER.info(f"📝 Found {len(texts)} text blocks from {image_name}")
                    
                    # Process each detected text
                    for i, (text, score) in enumerate(zip(texts, scores)):
                        try:
                            # Clean and validate text
                            text = str(text).strip()
                            if not text or len(text) < 1:
                                continue
                            
                            # Get corresponding box
                            if i < len(boxes) and boxes[i] is not None:
                                box = boxes[i]
                                # Convert to list if it's array-like (numpy array or similar)
                                if hasattr(box, 'tolist') and callable(getattr(box, 'tolist')):
                                    box = box.tolist()
                                elif not isinstance(box, list):
                                    # Try to convert to list if it's array-like
                                    try:
                                        box = list(box)
                                    except (TypeError, ValueError):
                                        box = [[0, 0], [100, 0], [100, 20], [0, 20]]
                            else:
                                # Default box if not available
                                box = [[0, 0], [100, 0], [100, 20], [0, 20]]
                            
                            ocr_results.append(OCRResult(
                                box=box,
                                text=text,
                                confidence=float(score) if score else 1.0
                            ))
                            
                        except Exception as item_error:
                            OCR_LOGGER.warning(f"Error processing OCR item {i}: {item_error}")
                            continue
                
                else:
                    OCR_LOGGER.error(f"OCRResult missing expected keys. Available keys: {list(ocr_result.keys()) if hasattr(ocr_result, 'keys') else 'N/A'}")
                    return []
                
                OCR_LOGGER.info(f"✅ Successfully extracted {len(ocr_results)} text blocks from {image_name}")
                return ocr_results
            
            except Exception as e:
                logger.error(f"OCR extraction failed for {image_path}: {e}")
                return []
                
            finally:
                # Cleanup temporary files - ONLY delete temp files, never original images
                if temp_path and temp_path != image_path:
                    try:
                        temp_file = Path(temp_path)
                        original_file = Path(image_path)
                        
                        # Extra safety check: only delete if it's actually a temp file
                        if (temp_file.exists() and 
                            temp_file != original_file and 
                            'temp_ocr_' in temp_file.name and
                            temp_file.parent.name.startswith('tmp')):
                            
                            logger.info(f"Cleaning up temp file: {temp_file}")
                            temp_file.unlink()
                            
                            # Remove temp directory if empty
                            temp_dir = temp_file.parent
                            if temp_dir.name.startswith('tmp') and not any(temp_dir.iterdir()):
                                temp_dir.rmdir()
                                logger.info(f"Cleaned up temp directory: {temp_dir}")
                        else:
                            logger.warning(f"Skipped cleanup - not a temp file: {temp_file}")
                            
                    except Exception as cleanup_error:
                        logger.debug(f"Cleanup warning: {cleanup_error}")
