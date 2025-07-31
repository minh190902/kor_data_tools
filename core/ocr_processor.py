from PIL import Image
from pathlib import Path
from typing import List
from paddleocr import PaddleOCR

from config import logger, OCRResult
from config.ocr_config import DEFAULT_OCR_CONFIGS

class TOPIKOCRProcessor:
    """Enhanced OCR processor with robust error handling for PaddleOCR v3.1+"""
    
    def __init__(self):
        """Initialize PaddleOCR with multiple fallback configurations"""
        self.ocr = None
        self._initialize_ocr()
        logger.info("✅ PaddleOCR processor ready")
    
    def _initialize_ocr(self):
        """Initialize PaddleOCR with robust configuration and dependency checking"""
        try:
            # Check for required dependencies first
            missing_deps = []
            try:
                import setuptools
            except ImportError:
                missing_deps.append("setuptools")
            
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
                    
                    self.ocr = PaddleOCR(**config)
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
        """Enhanced text extraction with multiple fallback methods"""
        temp_path = None
        
        try:
            if not self.ocr:
                logger.error("OCR not initialized")
                return []
            
            # Validate image
            if not self._validate_image(image_path):
                return []
            
            # Normalize path
            safe_path = self._normalize_path(image_path)
            temp_path = safe_path if safe_path != image_path else None
            
            logger.info(f"Starting OCR for: {Path(image_path).name}")
            
            # Use predict method (recommended for PaddleOCR v3.1+)
            try:
                logger.debug("Using predict method for OCR")
                results = self.ocr.predict(safe_path)
                
                if not results or len(results) == 0:
                    logger.warning(f"No OCR results for {image_path}")
                    return []
                
                logger.info("✅ OCR successful using predict method")
                
            except Exception as e:
                logger.error(f"OCR predict method failed: {e}")
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
                
                logger.info(f"Found {len(texts)} text blocks from OCR")
                
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
                        logger.warning(f"Error processing OCR item {i}: {item_error}")
                        continue
            
            else:
                logger.error(f"OCRResult missing expected keys. Available keys: {list(ocr_result.keys()) if hasattr(ocr_result, 'keys') else 'N/A'}")
                return []
            
            logger.info(f"Successfully extracted {len(ocr_results)} text blocks")
            return ocr_results
            
        except Exception as e:
            logger.error(f"OCR extraction failed for {image_path}: {e}")
            return []
            
        finally:
            # Cleanup temporary files
            if temp_path and temp_path != image_path:
                try:
                    temp_file = Path(temp_path)
                    if temp_file.exists():
                        temp_file.unlink()
                        # Remove temp directory if empty
                        temp_dir = temp_file.parent
                        if temp_dir.name.startswith('tmp') and not any(temp_dir.iterdir()):
                            temp_dir.rmdir()
                except Exception as cleanup_error:
                    logger.debug(f"Cleanup warning: {cleanup_error}")
