import os
from datetime import datetime
from typing import List
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse

from .schemas import APIResponse, ProcessingStatus
from .services import TOPIKProcessingService, FileService
from config import logger

# Initialize services
processing_service = TOPIKProcessingService()
file_service = FileService()

# Create router
router = APIRouter()

@router.get("/", response_model=APIResponse)
async def root():
    """Health check endpoint - safe entry point"""
    try:
        return APIResponse(
            status="success",
            message="TOPIK OCR API is running (PydanticAI Optimized)",
            data={
                "version": "2.0.0-PydanticAI", 
                "processor_ready": processing_service.is_ready(),
                "features": [
                    "PydanticAI integration",
                    "Optimized batch processing", 
                    "Cross-image question handling",
                    "Type-safe validation"
                ]
            }
        )
    except Exception as e:
        logger.error(f"Root endpoint error: {e}")
        return APIResponse(
            status="error",
            message=f"API error: {str(e)}",
            data={"version": "2.0.0-PydanticAI"}
        )

@router.get("/health", response_model=APIResponse)
async def health_check():
    """Detailed health check with dependency status"""
    try:
        processor_ready = processing_service.is_ready()
        gemini_available = bool(os.getenv("GEMINI_API_KEY"))
        
        # Check dependencies
        dependencies = {}
        
        # Check PaddleOCR
        try:
            from paddleocr import PaddleOCR
            dependencies["paddleocr"] = "available"
        except ImportError as e:
            dependencies["paddleocr"] = f"import_error: {str(e)}"
        except Exception as e:
            dependencies["paddleocr"] = f"error: {str(e)}"
        
        # Check setuptools
        try:
            import setuptools
            dependencies["setuptools"] = f"available: {setuptools.__version__}"
        except ImportError:
            dependencies["setuptools"] = "missing"
        
        # Check PydanticAI
        try:
            import pydantic_ai
            dependencies["pydantic_ai"] = "available"
        except ImportError as e:
            dependencies["pydantic_ai"] = f"import_error: {str(e)}"
        
        # Determine overall status
        if processor_ready and gemini_available:
            status = "success"
            message = "API fully operational"
        elif gemini_available and dependencies.get("paddleocr") == "available":
            status = "warning"
            message = "Dependencies OK but processor failed to initialize"
        elif not gemini_available:
            status = "warning"
            message = "GEMINI_API_KEY not configured"
        else:
            status = "error"
            message = "Critical dependencies missing"
        
        return APIResponse(
            status=status,
            message=message,
            data={
                "processor_initialized": processor_ready,
                "gemini_available": gemini_available,
                "dependencies": dependencies,
                "timestamp": datetime.now().isoformat(),
                "version": "2.0.0-PydanticAI"
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return APIResponse(
            status="error",
            message=f"Health check error: {str(e)}",
            data={"timestamp": datetime.now().isoformat()}
        )

@router.post("/initialize", response_model=APIResponse)
async def manual_initialize():
    """Manually trigger processor initialization for debugging"""
    try:
        logger.info("🔄 Manual initialization requested...")
        success = await initialize_service()
        
        if success:
            return APIResponse(
                status="success",
                message="Processor initialized successfully",
                data={
                    "processor_ready": processing_service.is_ready(),
                    "timestamp": datetime.now().isoformat()
                }
            )
        else:
            return APIResponse(
                status="error",
                message="Processor initialization failed",
                data={
                    "processor_ready": processing_service.is_ready(),
                    "timestamp": datetime.now().isoformat()
                }
            )
    except Exception as e:
        logger.error(f"Manual initialization failed: {e}")
        return APIResponse(
            status="error",
            message=f"Manual initialization error: {str(e)}",
            data={"timestamp": datetime.now().isoformat()}
        )

@router.post("/process-images", response_model=ProcessingStatus)
async def process_images(
    files: List[UploadFile] = File(...),
    source_info: str = Form(default="TOPIK Practice")
):
    """
    Xử lý một hoặc nhiều ảnh đề thi TOPIK
    
    Args:
        files: Danh sách ảnh upload (JPG, PNG, etc.)
        source_info: Thông tin nguồn đề thi
    
    Returns:
        ProcessingStatus với link download CSV
    """
    try:
        if not processing_service.is_ready():
            raise HTTPException(status_code=500, detail="Processor not initialized")
        
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded")
        
        result = await processing_service.process_uploaded_images(files, source_info)
        logger.info(f"✅ Processed {len(result.message)}")
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.post("/process-zip", response_model=ProcessingStatus)
async def process_zip_file(
    file: UploadFile = File(...),
    source_info: str = Form(default="TOPIK Practice")
):
    """
    Xử lý file ZIP chứa nhiều ảnh đề thi
    
    Args:
        file: File ZIP chứa ảnh
        source_info: Thông tin nguồn đề thi
    """
    try:
        if not processing_service.is_ready():
            raise HTTPException(status_code=500, detail="Processor not initialized")
        
        result = await processing_service.process_zip_file(file, source_info)
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"ZIP processing error: {e}")
        raise HTTPException(status_code=500, detail=f"ZIP processing failed: {str(e)}")

@router.get("/download/{filename}")
async def download_csv(filename: str):
    """Download CSV file"""
    file_path = file_service.get_file_path(filename)
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='text/csv'
    )

@router.get("/list-outputs", response_model=APIResponse)
async def list_output_files():
    """List available CSV output files"""
    try:
        files = file_service.get_output_files()
        return APIResponse(
            status="success",
            message=f"Found {len(files)} output files",
            data={"files": [file.dict() for file in files]}
        )
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail="Failed to list files")

@router.delete("/cleanup", response_model=APIResponse)
async def cleanup_old_files():
    """Clean up old output files (older than 24 hours)"""
    try:
        deleted_count = file_service.cleanup_old_files()
        return APIResponse(
            status="success",
            message=f"Cleaned up {deleted_count} old files",
            data={"deleted_files": deleted_count}
        )
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise HTTPException(status_code=500, detail="Cleanup failed")


# Initialize processor on module load
async def initialize_service():
    """Initialize the processing service with graceful error handling"""
    try:
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            logger.error("❌ GEMINI_API_KEY không được tìm thấy trong environment variables!")
            logger.error("Vui lòng set GEMINI_API_KEY trong .env file hoặc environment")
            logger.warning("🔄 API will start without processing capabilities")
            return False
        
        logger.info("🚀 Initializing TOPIK processing service with PydanticAI...")
        logger.info(f"GEMINI_API_KEY found: {GEMINI_API_KEY[:8]}...") # Log first 8 chars for verification
        
        success = await processing_service.initialize_processor(GEMINI_API_KEY)
        
        if not success:
            logger.error("❌ Failed to initialize processing service")
            logger.warning("🔄 API will start in degraded mode")
            return False
            
        # Verify the processor is actually ready
        is_ready = processing_service.is_ready()
        logger.info(f"🔍 Processor ready status: {is_ready}")
        
        if is_ready:
            logger.info("✅ TOPIK processing service initialized successfully")
            return True
        else:
            logger.error("❌ Processor initialization appeared successful but is_ready() returned False")
            return False
        
    except Exception as e:
        logger.error(f"❌ Service initialization failed with exception: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        logger.warning("🔄 API will start in degraded mode - check dependencies")
        # Don't raise, allow API to start for debugging
        return False

async def cleanup_service():
    """Cleanup service resources"""
    try:
        if processing_service:
            await processing_service.cleanup()
            logger.info("🧹 Processing service cleaned up")
        logger.info("✅ Service cleanup completed")
    except Exception as e:
        logger.error(f"❌ Error during service cleanup: {e}")
