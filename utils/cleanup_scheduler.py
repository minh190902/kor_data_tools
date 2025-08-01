#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scheduled cleanup utility for output files
"""

import schedule
import time
import logging
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from utils.file_manager import file_manager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cleanup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def scheduled_cleanup():
    """Thực hiện dọn dẹp theo lịch"""
    try:
        logger.info("🧹 Bắt đầu dọn dẹp định kỳ...")
        
        # Lấy thống kê trước khi dọn dẹp
        stats_before = file_manager.get_storage_stats()
        logger.info(f"📊 Trước dọn dẹp: {stats_before['total_files']} files, {stats_before['total_size_mb']}MB")
        
        # Thực hiện dọn dẹp
        deleted_count, freed_mb = file_manager.cleanup_old_files(
            max_age_days=7,    # Xóa file cũ hơn 7 ngày
            max_files=50       # Giữ tối đa 50 file
        )
        
        # Lấy thống kê sau khi dọn dẹp
        stats_after = file_manager.get_storage_stats()
        
        if deleted_count > 0:
            logger.info(f"✅ Dọn dẹp hoàn tất: {deleted_count} files, {freed_mb:.1f}MB")
            logger.info(f"📊 Sau dọn dẹp: {stats_after['total_files']} files, {stats_after['total_size_mb']}MB")
        else:
            logger.info("✅ Không có file nào cần dọn dẹp")
            
    except Exception as e:
        logger.error(f"❌ Lỗi trong quá trình dọn dẹp: {e}")

def run_cleanup_scheduler():
    """Chạy scheduler dọn dẹp"""
    logger.info("🚀 Khởi động Cleanup Scheduler...")
    logger.info("📅 Lịch dọn dẹp:")
    logger.info("   • Mỗi ngày lúc 02:00")
    logger.info("   • Mỗi 6 tiếng")
    logger.info("   • Khi khởi động")
    
    # Lên lịch dọn dẹp
    schedule.every().day.at("02:00").do(scheduled_cleanup)  # Mỗi ngày lúc 2h sáng
    schedule.every(6).hours.do(scheduled_cleanup)           # Mỗi 6 tiếng
    
    # Chạy một lần ngay khi khởi động
    scheduled_cleanup()
    
    # Vòng lặp chính
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check mỗi phút
    except KeyboardInterrupt:
        logger.info("👋 Dừng Cleanup Scheduler")

def manual_cleanup_with_options():
    """Dọn dẹp thủ công với tùy chọn"""
    print("🧹 TOPIK File Cleanup Tool")
    print("=" * 40)
    
    # Hiển thị thống kê hiện tại
    stats = file_manager.get_storage_stats()
    files_info = file_manager.get_output_files_info()
    
    print(f"📊 Thống kê hiện tại:")
    print(f"   • Tổng số file: {stats['total_files']}")
    print(f"   • Dung lượng: {stats['total_size_mb']} MB")
    print(f"   • File cũ (30+ ngày): {stats['age_distribution']['30+_days']}")
    print()
    
    if stats['total_files'] == 0:
        print("✅ Không có file nào để dọn dẹp")
        return
    
    # Hiển thị tùy chọn
    print("Chọn chế độ dọn dẹp:")
    print("1. 🕐 Dọn dẹp file cũ hơn 7 ngày")
    print("2. 🕐 Dọn dẹp file cũ hơn 30 ngày")
    print("3. 📁 Giữ lại 30 file mới nhất")
    print("4. 📁 Giữ lại 10 file mới nhất")
    print("5. 🔥 Xóa tất cả file")
    print("0. ❌ Hủy")
    
    choice = input("\nNhập lựa chọn (0-5): ").strip()
    
    if choice == "0":
        print("❌ Hủy dọn dẹp")
        return
    elif choice == "1":
        deleted, freed = file_manager.cleanup_old_files(max_age_days=7, max_files=1000)
    elif choice == "2":
        deleted, freed = file_manager.cleanup_old_files(max_age_days=30, max_files=1000)
    elif choice == "3":
        deleted, freed = file_manager.cleanup_old_files(max_age_days=0, max_files=30)
    elif choice == "4":
        deleted, freed = file_manager.cleanup_old_files(max_age_days=0, max_files=10)
    elif choice == "5":
        confirm = input("⚠️  Bạn có chắc muốn xóa TẤT CẢ file? (yes/no): ")
        if confirm.lower() == "yes":
            deleted, freed = file_manager.cleanup_old_files(max_age_days=0, max_files=0)
        else:
            print("❌ Hủy xóa tất cả")
            return
    else:
        print("❌ Lựa chọn không hợp lệ")
        return
    
    print(f"\n✅ Dọn dẹp hoàn tất:")
    print(f"   • Đã xóa: {deleted} file")
    print(f"   • Giải phóng: {freed:.1f} MB")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "schedule":
            # Chạy scheduler
            run_cleanup_scheduler()
        elif sys.argv[1] == "manual":
            # Dọn dẹp thủ công
            manual_cleanup_with_options()
        elif sys.argv[1] == "auto":
            # Dọn dẹp tự động một lần
            scheduled_cleanup()
        else:
            print("Usage:")
            print("  python cleanup_scheduler.py schedule  # Chạy scheduler")
            print("  python cleanup_scheduler.py manual    # Dọn dẹp thủ công")
            print("  python cleanup_scheduler.py auto      # Dọn dẹp tự động một lần")
    else:
        # Mặc định chạy manual
        manual_cleanup_with_options()