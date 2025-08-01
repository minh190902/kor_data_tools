#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File management utilities for output cleanup
"""

import os
import glob
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

class OutputFileManager:
    """Quản lý file output với tính năng tự động dọn dẹp"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def get_file_age_days(self, file_path: Path) -> int:
        """Tính số ngày từ khi file được tạo"""
        try:
            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            return (datetime.now() - file_time).days
        except Exception as e:
            logger.error(f"Lỗi khi tính tuổi file {file_path}: {e}")
            return 0
    
    def get_output_files_info(self) -> List[Tuple[str, int, float]]:
        """Lấy thông tin các file output (tên, tuổi_ngày, kích_thước_MB)"""
        files_info = []
        
        # Lấy tất cả file CSV
        csv_files = list(self.output_dir.glob("*.csv"))
        
        for file_path in csv_files:
            try:
                age_days = self.get_file_age_days(file_path)
                size_mb = file_path.stat().st_size / (1024 * 1024)  # Convert to MB
                files_info.append((file_path.name, age_days, size_mb))
            except Exception as e:
                logger.error(f"Lỗi khi đọc thông tin file {file_path}: {e}")
        
        return sorted(files_info, key=lambda x: x[1], reverse=True)  # Sort by age
    
    def cleanup_old_files(self, max_age_days: int = 7, max_files: int = 50) -> Tuple[int, float]:
        """
        Dọn dẹp file cũ theo 2 tiêu chí:
        - File cũ hơn max_age_days ngày
        - Giữ lại tối đa max_files file mới nhất
        
        Returns: (số_file_đã_xóa, dung_lượng_đã_giải_phóng_MB)
        """
        deleted_count = 0
        freed_space_mb = 0.0
        
        try:
            csv_files = list(self.output_dir.glob("*.csv"))
            
            # Sort by modification time (newest first)
            csv_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            files_to_delete = []
            
            # 1. Xóa file cũ hơn max_age_days
            for file_path in csv_files:
                age_days = self.get_file_age_days(file_path)
                if age_days > max_age_days:
                    files_to_delete.append(file_path)
            
            # 2. Nếu vẫn còn quá nhiều file, xóa file cũ nhất
            remaining_files = [f for f in csv_files if f not in files_to_delete]
            if len(remaining_files) > max_files:
                files_to_delete.extend(remaining_files[max_files:])
            
            # Thực hiện xóa
            for file_path in files_to_delete:
                try:
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    file_path.unlink()
                    deleted_count += 1
                    freed_space_mb += size_mb
                    logger.info(f"Đã xóa file cũ: {file_path.name}")
                except Exception as e:
                    logger.error(f"Lỗi khi xóa file {file_path}: {e}")
            
            return deleted_count, freed_space_mb
            
        except Exception as e:
            logger.error(f"Lỗi trong quá trình dọn dẹp: {e}")
            return 0, 0.0
    
    def get_storage_stats(self) -> dict:
        """Lấy thống kê dung lượng storage"""
        try:
            csv_files = list(self.output_dir.glob("*.csv"))
            total_files = len(csv_files)
            total_size_mb = sum(f.stat().st_size for f in csv_files) / (1024 * 1024)
            
            # Thống kê theo độ tuổi
            age_stats = {"0-1_days": 0, "2-7_days": 0, "8-30_days": 0, "30+_days": 0}
            
            for file_path in csv_files:
                age_days = self.get_file_age_days(file_path)
                if age_days <= 1:
                    age_stats["0-1_days"] += 1
                elif age_days <= 7:
                    age_stats["2-7_days"] += 1
                elif age_days <= 30:
                    age_stats["8-30_days"] += 1
                else:
                    age_stats["30+_days"] += 1
            
            return {
                "total_files": total_files,
                "total_size_mb": round(total_size_mb, 2),
                "age_distribution": age_stats
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi tính thống kê: {e}")
            return {"total_files": 0, "total_size_mb": 0, "age_distribution": {}}
    
    def auto_cleanup_if_needed(self, max_age_days: int = 7, max_files: int = 50, 
                              max_size_mb: int = 100) -> str:
        """
        Tự động dọn dẹp nếu cần thiết
        Returns: Thông báo kết quả
        """
        try:
            stats = self.get_storage_stats()
            
            # Kiểm tra xem có cần dọn dẹp không
            need_cleanup = (
                stats["total_files"] > max_files or 
                stats["total_size_mb"] > max_size_mb or
                stats["age_distribution"]["30+_days"] > 0
            )
            
            if need_cleanup:
                deleted_count, freed_mb = self.cleanup_old_files(max_age_days, max_files)
                return f"🧹 Đã dọn dẹp {deleted_count} file, giải phóng {freed_mb:.1f}MB"
            else:
                return "✅ Storage trong tình trạng tốt, không cần dọn dẹp"
                
        except Exception as e:
            return f"❌ Lỗi khi kiểm tra cleanup: {e}"

# Global instance
file_manager = OutputFileManager()