#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOPIK Data Processing Tool - Enhanced with PydanticAI
Công cụ xử lý dữ liệu đề thi TOPIK tự động với OCR và AI structuring

🚀 NEW FEATURES:
- Enhanced workflow: OCR all images → Single LLM call  
- PydanticAI integration for better output validation
- Cross-image question handling
- Optimized prompting and reduced API costs
- Better error handling and type safety

Features:
- OCR ảnh đề thi TOPIK với PaddleOCR v3.1+
- Chuyển đổi text thô thành structured data với PydanticAI + Gemini
- Xử lý cross-image questions (câu hỏi chia nhiều ảnh)
- Xử lý đa luồng để tối ưu tốc độ
- Pydantic validation cho output quality
- Lưu trữ vào MongoDB hoặc PostgreSQL
- Enhanced validation và error handling
"""

import asyncio
import os
from dotenv import load_dotenv

from processors.topik_processor import TOPIKDataProcessor

# Load environment variables
load_dotenv()

# CLI Usage Example
async def main():
    """Enhanced main function with PydanticAI workflow"""
    
    # Configuration - Get API key from environment
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY không được tìm thấy!")
        print("Vui lòng:")
        print("1. Tạo file .env trong thư mục gốc")
        print("2. Thêm dòng: GEMINI_API_KEY=your_actual_api_key")
        print("3. Hoặc set environment variable GEMINI_API_KEY")
        return
    
    # Database config - chọn một trong hai
    DB_CONFIG_MONGO = {
        "db_type": "mongodb",
        "mongo_uri": "mongodb://localhost:27017/",
        "db_name": "topik",
        "collection": "questions"
    }
    
    DB_CONFIG_POSTGRES = {
        "db_type": "postgresql", 
        "host": "localhost",
        "database": "topik",
        "user": "postgres",
        "password": "your_password",
        "table": "topik_questions"
    }
    
    # 🚀 Initialize optimized processor with PydanticAI only
    print(f"🚀 Khởi tạo Optimized TOPIK Data Processor...")
    print(f"🔥 Features: PydanticAI + Cross-Image Processing + Tối ưu hóa hoàn toàn")
    
    processor = TOPIKDataProcessor(
        gemini_api_key=GEMINI_API_KEY,
        db_config=None,
        max_workers=4,
        save_to_db=False
    )
    
    # Process directory with optimized workflow
    source_info = "TOPIK I Reading Practice - PydanticAI Optimized"
    
    print(f"📁 Bắt đầu xử lý với PydanticAI Workflow...")
    print(f"📊 Mode: PydanticAI Batch Processing (Legacy đã loại bỏ)")
    
    success = await processor.process_directory(
        source_info=source_info
    )
    
    if success:
        print("✅ PydanticAI processing hoàn tất!")
        print("🎯 Ưu điểm của PydanticAI workflow:")
        print("   • Chỉ 1 API call thay vì N calls → Tiết kiệm cost")
        print("   • Xử lý cross-image questions → Không bỏ sót thông tin")
        print("   • Pydantic validation → Đảm bảo output quality")
        print("   • Clean code → Loại bỏ hoàn toàn legacy Gemini")
        print("   • Better performance → Tối ưu hóa và gọn gàng")
    else:
        print("❌ Có lỗi trong quá trình xử lý!")


async def demo_pydantic_ai():
    """Demo PydanticAI workflow"""
    print("🔬 DEMO: PydanticAI Optimized Workflow")
    print("="*60)
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        print("❌ Cần GEMINI_API_KEY để chạy demo")
        return
    
    # Test với PydanticAI workflow
    print("\n🚀 Testing PydanticAI Optimized Workflow...")
    processor = TOPIKDataProcessor(
        gemini_api_key=GEMINI_API_KEY,
        max_workers=4
    )
    
    success = await processor.process_directory(
        source_info="TOPIK Demo - PydanticAI Optimized"
    )
    
    # Show results
    print("\n📊 PYDANTIC AI RESULTS:")
    print("="*40)
    print(f"Stats: {processor.stats}")
    print("🎯 Ưu điểm:")
    print("   ✅ Code gọn gàng - loại bỏ hoàn toàn legacy")
    print("   ✅ Performance cao - batch processing")  
    print("   ✅ Type safety - Pydantic validation")
    print("   ✅ Cost effective - ít API calls hơn")


if __name__ == "__main__":
    # Chọn mode chạy
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        # Demo PydanticAI
        asyncio.run(demo_pydantic_ai())
    else:
        # Normal processing với PydanticAI workflow
        asyncio.run(main())