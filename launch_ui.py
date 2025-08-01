#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI Launcher - Choose between different UI versions
"""

import sys
import os
from pathlib import Path

def show_menu():
    """Hiển thị menu chọn UI"""
    print("🇰🇷 TOPIK OCR Tool - UI Launcher")
    print("=" * 50)
    print("Chọn phiên bản giao diện:")
    print()
    print("1. 🎨 UI Cải tiến (Khuyến nghị)")
    print("   • Giao diện hiện đại, nhẹ nhàng")
    print("   • Tự động dọn dẹp file cũ")
    print("   • Quản lý storage thông minh")
    print("   • Thông báo chi tiết hơn")
    print()
    print("2. 📁 UI Tải xuống (Cũ)")
    print("   • Giao diện cơ bản")
    print("   • Tính năng tải file")
    print()
    print("3. 🔧 UI Cơ bản (app.py)")
    print("   • Phiên bản gốc")
    print()
    print("0. ❌ Thoát")
    print("=" * 50)

def launch_ui(choice: str):
    """Khởi chạy UI được chọn"""
    try:
        if choice == "1":
            print("🚀 Đang khởi chạy UI Cải tiến...")
            from ui.app_improved import main
            main()
        elif choice == "2":
            print("🚀 Đang khởi chạy UI Tải xuống...")
            from ui.app_download import main
            main()
        elif choice == "3":
            print("🚀 Đang khởi chạy UI Cơ bản...")
            from ui.app import main
            main()
        else:
            print("❌ Lựa chọn không hợp lệ!")
            return False
        return True
    except ImportError as e:
        print(f"❌ Lỗi import: {e}")
        print("Đảm bảo tất cả dependencies đã được cài đặt:")
        print("pip install -r requirements-gradio.txt")
        return False
    except Exception as e:
        print(f"❌ Lỗi khởi chạy: {e}")
        return False

def main():
    """Main launcher function"""
    # Check if running from correct directory
    if not Path("ui").exists():
        print("❌ Vui lòng chạy script từ thư mục gốc của project!")
        print("cd /path/to/your/project")
        print("python launch_ui.py")
        return
    
    # Check environment
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  Cảnh báo: GEMINI_API_KEY chưa được thiết lập")
        print("Một số tính năng có thể không hoạt động")
        print()
    
    while True:
        show_menu()
        choice = input("Nhập lựa chọn (0-3): ").strip()
        
        if choice == "0":
            print("👋 Tạm biệt!")
            break
        elif choice in ["1", "2", "3"]:
            if launch_ui(choice):
                break  # UI launched successfully
            else:
                input("Nhấn Enter để tiếp tục...")
        else:
            print("❌ Vui lòng nhập số từ 0-3")
            input("Nhấn Enter để tiếp tục...")

if __name__ == "__main__":
    main()