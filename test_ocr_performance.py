import time
import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from core.ocr_processor import TOPIKOCRProcessor
from config import OCR_LOGGER

def draw_ocr_results(image_path: str, ocr_results, output_dir: Path):
    """Vẽ bounding boxes và text lên ảnh để visualize kết quả OCR với font tiếng Hàn"""
    try:
        # Đọc ảnh bằng PIL
        image = Image.open(image_path)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Tạo drawing context
        draw = ImageDraw.Draw(image)
        
        # Load font hỗ trợ tiếng Hàn
        font = None
        korean_fonts = [
            "C:/Windows/Fonts/malgun.ttf",      # Malgun Gothic (Windows Korean)
            "C:/Windows/Fonts/gulim.ttc",       # Gulim (Windows Korean)
            "C:/Windows/Fonts/batang.ttc",      # Batang (Windows Korean)
            "C:/Windows/Fonts/NanumGothic.ttf", # Nanum Gothic
            "/System/Library/Fonts/AppleGothic.ttf",  # macOS Korean
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"  # Linux Korean
        ]
        
        try:
            for font_path in korean_fonts:
                if Path(font_path).exists():
                    font = ImageFont.truetype(font_path, 14)
                    break
            if font is None:
                # Fallback to default font
                font = ImageFont.load_default()
        except Exception as e:
            print(f"  -> Font loading warning: {e}")
            font = ImageFont.load_default()
        
        # Màu sắc đẹp hơn cho bounding boxes
        colors = [
            (255, 87, 87),   # Coral Red
            (87, 255, 87),   # Light Green  
            (87, 87, 255),   # Light Blue
            (255, 215, 0),   # Gold
            (255, 105, 180), # Hot Pink
            (0, 255, 255),   # Cyan
            (255, 165, 0),   # Orange
            (147, 112, 219), # Medium Purple
        ]
        
        # Tạo ảnh overlay để vẽ bounding boxes với transparency
        overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        for i, result in enumerate(ocr_results):
            if not result.text.strip():
                continue
                
            # Lấy bounding box coordinates
            box = result.box
            if len(box) >= 4:
                # Convert box coordinates to integers
                points = [(int(point[0]), int(point[1])) for point in box]
                
                # Chọn màu theo index
                color = colors[i % len(colors)]
                
                # Vẽ bounding box với fill nhẹ
                overlay_draw.polygon(points, outline=color + (255,), fill=color + (30,), width=2)
                
                # Vẽ số thứ tự trong góc box
                box_center_x = sum(p[0] for p in points) // 4
                box_center_y = sum(p[1] for p in points) // 4
                
                # Vẽ circle với số thứ tự
                circle_radius = 12
                circle_bbox = [
                    box_center_x - circle_radius, box_center_y - circle_radius,
                    box_center_x + circle_radius, box_center_y + circle_radius
                ]
                overlay_draw.ellipse(circle_bbox, fill=color + (200,), outline=(255, 255, 255, 255), width=2)
                
                # Vẽ số thứ tự
                number_text = str(i + 1)
                try:
                    # Tính toán vị trí để center text trong circle
                    bbox = overlay_draw.textbbox((0, 0), number_text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    text_x = box_center_x - text_width // 2
                    text_y = box_center_y - text_height // 2
                    overlay_draw.text((text_x, text_y), number_text, fill=(255, 255, 255, 255), font=font)
                except:
                    # Fallback nếu textbbox không hoạt động
                    overlay_draw.text((box_center_x - 5, box_center_y - 7), number_text, fill=(255, 255, 255, 255), font=font)
        
        # Composite overlay lên ảnh gốc
        image = image.convert('RGBA')
        image = Image.alpha_composite(image, overlay)
        image = image.convert('RGB')
        
        # Tạo ảnh thông tin text riêng biệt
        info_height = max(200, len(ocr_results) * 25 + 50)
        info_image = Image.new('RGB', (image.width, info_height), (240, 240, 240))
        info_draw = ImageDraw.Draw(info_image)
        
        # Vẽ header
        header_text = f"OCR Results - {len(ocr_results)} text blocks detected"
        info_draw.text((10, 10), header_text, fill=(0, 0, 0), font=font)
        
        # Vẽ thông tin từng text block
        y_offset = 40
        for i, result in enumerate(ocr_results):
            if not result.text.strip():
                continue
                
            color = colors[i % len(colors)]
            
            # Vẽ color indicator
            info_draw.rectangle([10, y_offset, 25, y_offset + 15], fill=color)
            
            # Vẽ text info
            text_info = f"{i+1}. {result.text} (conf: {result.confidence:.3f})"
            # Truncate nếu quá dài
            if len(text_info) > 100:
                text_info = text_info[:97] + "..."
            
            try:
                info_draw.text((35, y_offset), text_info, fill=(0, 0, 0), font=font)
            except UnicodeEncodeError:
                # Fallback nếu font không hỗ trợ ký tự
                safe_text = f"{i+1}. [Korean Text] (conf: {result.confidence:.3f})"
                info_draw.text((35, y_offset), safe_text, fill=(0, 0, 0), font=font)
            
            y_offset += 25
        
        # Ghép ảnh chính và ảnh thông tin
        final_image = Image.new('RGB', (image.width, image.height + info_height))
        final_image.paste(image, (0, 0))
        final_image.paste(info_image, (0, image.height))
        
        # Lưu ảnh kết quả
        output_path = output_dir / f"ocr_result_{Path(image_path).stem}.png"
        final_image.save(output_path, quality=95)
        print(f"  -> Saved visualization: {output_path}")
        
    except Exception as e:
        print(f"  -> Error creating visualization: {e}")
        import traceback
        traceback.print_exc()

def test_ocr_folder(image_folder: str, visualize: bool = True):
    """Test OCR performance với tùy chọn visualization"""
    ocr = TOPIKOCRProcessor()
    image_dir = Path(image_folder)
    image_files = list(image_dir.glob('*.png')) + list(image_dir.glob('*.jpg')) + list(image_dir.glob('*.jpeg'))
    print(f"Found {len(image_files)} images in {image_folder}")
    
    # Tạo thư mục output cho visualization
    output_dir = None
    if visualize:
        output_dir = Path("output") / "ocr_visualization"
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Visualization results will be saved to: {output_dir}")
    
    total_time = 0
    results_count = 0
    
    for idx, img_path in enumerate(image_files):
        print(f"\n[{idx+1}/{len(image_files)}] Processing: {img_path.name}")
        start = time.time()
        
        # Thực hiện OCR
        results = ocr.extract_text(str(img_path))
        
        # Log kết quả text
        for i, result in enumerate(results):
            if result.text.strip():
                OCR_LOGGER.info(f"Text Block {i+1}: {result.text}, Confidence: {result.confidence:.2f}")
                print(f"  Text {i+1}: '{result.text}' (confidence: {result.confidence:.2f})")

        elapsed = time.time() - start
        print(f"  -> {len(results)} text blocks, {elapsed:.2f}s")
        
        # Tạo visualization nếu được yêu cầu
        if visualize and results and output_dir:
            draw_ocr_results(str(img_path), results, output_dir)
        
        total_time += elapsed
        results_count += len(results)
    
    print(f"\n=== SUMMARY ===")
    print(f"Total images: {len(image_files)}")
    print(f"Total OCR time: {total_time:.2f}s")
    print(f"Average per image: {total_time/len(image_files):.2f}s" if image_files else "N/A")
    print(f"Total text blocks: {results_count}")
    print(f"Average text blocks per image: {results_count/len(image_files):.1f}" if image_files else "N/A")
    
    if visualize and output_dir:
        print(f"\nVisualization images saved in: {output_dir}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python test_ocr_performance.py <image_folder> [--no-viz]")
        print("  --no-viz: Disable visualization (faster processing)")
    else:
        image_folder = sys.argv[1]
        visualize = "--no-viz" not in sys.argv
        test_ocr_folder(image_folder, visualize)
