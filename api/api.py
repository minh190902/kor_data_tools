#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI application for TOPIK Data Processing Tool
API để xử lý ảnh đề thi TOPIK thành CSV
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .endpoints import router, initialize_service, cleanup_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup with graceful error handling"""
    try:
        # Startup
        await initialize_service()
        print("✅ All services initialized successfully")
        yield
    except Exception as e:
        print(f"⚠️  Service initialization failed: {e}")
        print("🔄 API will start in degraded mode - check /health for details")
        # Allow API to start even if some services fail
        # This enables debugging via health endpoint
        yield
    finally:
        # Cleanup
        try:
            await cleanup_service()
            print("✅ Service cleanup completed")
        except Exception as e:
            print(f"⚠️  Error during cleanup: {e}")

# Initialize FastAPI with lifespan
app = FastAPI(
    title="TOPIK OCR API",
    description="API để xử lý ảnh đề thi TOPIK thành dữ liệu có cấu trúc (CSV) - PydanticAI Optimized",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
