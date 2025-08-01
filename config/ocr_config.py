#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR Configuration for TOPIK Data Processing
Cấu hình tối ưu cho PaddleOCR trên Windows
"""

import os
import platform
from typing import Dict, Any, List

class OCRConfig:
    """OCR configuration manager"""
    
    @staticmethod
    def get_optimal_config() -> List[Dict[str, Any]]:
        """Get optimal PaddleOCR v3.1.0+ configurations based on system"""
        
        # Configuration priority list (try in order)
        # Note: PaddleOCR v3.1.0+ has different parameter names
        configs = [
            # Config 1: Full Korean OCR with textline orientation
            {
                'use_textline_orientation': False,
                'lang': 'korean',
                'text_det_limit_side_len': 736,
                'text_det_limit_type': 'min',
                'text_recognition_batch_size': 4,
            },
            
            # Config 2: Korean OCR without textline orientation (faster)
            {
                'use_textline_orientation': False,
                'lang': 'korean',
                'text_det_limit_side_len': 960,
                'text_det_limit_type': 'max',
            },
            
            # Config 3: Minimal Korean setup
            {
                'lang': 'korean',
            },
            
            # Config 4: Fallback to English (last resort)
            {
                'lang': 'en',
            }
        ]
        
        return configs
    
    @staticmethod
    def get_image_preprocessing_config() -> Dict[str, Any]:
        """Get image preprocessing configuration"""
        return {
            'enhance_contrast': True,
            'denoise': True,
            'min_width': 600,
            'min_height': 800,
            'max_width': 2000,
            'max_height': 3000,
            'scale_factor': 1.2,  # Scale up small images
        }
    
    @staticmethod
    def get_threading_config() -> Dict[str, Any]:
        """Get threading configuration for multi-processing"""
        cpu_count = os.cpu_count() or 1
        
        return {
            'max_workers': min(4, cpu_count),  # Limit concurrent OCR processes
            'semaphore_limit': 2,  # Limit simultaneous OCR calls
            'timeout_seconds': 30,  # OCR timeout per image
            'retry_attempts': 2,  # Retry failed OCR attempts
        }
    
    @staticmethod
    def get_path_config() -> Dict[str, Any]:
        """Get path handling configuration"""
        return {
            'normalize_paths': True,
            'use_forward_slashes': True,
            'create_temp_for_unicode': True,
            'temp_dir_prefix': 'topik_ocr_',
            'cleanup_temp_files': True,
        }
    
    @staticmethod
    def get_validation_config() -> Dict[str, Any]:
        """Get image validation configuration"""
        return {
            'min_file_size': 1024,  # 1KB minimum
            'max_file_size': 50 * 1024 * 1024,  # 50MB maximum
            'min_image_width': 10,
            'min_image_height': 10,
            'supported_formats': ['.png', '.jpg', '.jpeg', '.bmp', '.tiff'],
            'validate_with_pil': True,
        }

# Export default configurations
DEFAULT_OCR_CONFIGS = OCRConfig.get_optimal_config()
DEFAULT_PREPROCESSING_CONFIG = OCRConfig.get_image_preprocessing_config()
DEFAULT_THREADING_CONFIG = OCRConfig.get_threading_config()
DEFAULT_PATH_CONFIG = OCRConfig.get_path_config()
DEFAULT_VALIDATION_CONFIG = OCRConfig.get_validation_config()