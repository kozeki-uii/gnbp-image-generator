# 文件路径: core/utils.py

import os
import io
import base64
import json
import mimetypes
import copy
import uuid
from datetime import datetime
from PIL import Image, PngImagePlugin

class ImageUtils:
    @staticmethod
    def resize_and_encode(image_path, max_size=1536):
        """压缩图片并转Base64，限制最大边长，减少内存和流量"""
        try:
            if not os.path.exists(image_path): return None, None
            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type: mime_type = "image/png"

            with Image.open(image_path) as img:
                # 转换颜色模式，防止 RGBA 保存为 JPEG 报错
                if img.mode in ('RGBA', 'P'): img = img.convert('RGB')

                # 缩放逻辑
                width, height = img.size
                if max(width, height) > max_size:
                    ratio = max_size / max(width, height)
                    new_size = (int(width * ratio), int(height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                buffer = io.BytesIO()
                # 统一转为 JPEG 以获得更好的压缩率
                img.save(buffer, format="JPEG", quality=85)
                b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")

            return "image/jpeg", b64_str
        except Exception as e:
            print(f"Compress Error: {e}")
            return None, None

    @staticmethod
    def save_image(base64_data, output_dir, config_dict):
        try:
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"gen_{timestamp}_{uuid.uuid4().hex[:8]}.png"
            full_path = os.path.join(output_dir, filename)

            if "," in base64_data: base64_data = base64_data.split(",")[1]
            base64_data = base64_data.replace('\n', '').replace('\r', '')
            img_bytes = base64.b64decode(base64_data)
            image = Image.open(io.BytesIO(img_bytes))

            # 元数据处理 (脱敏)
            safe_config = copy.deepcopy(config_dict)
            if "api_key" in safe_config: del safe_config["api_key"]
            if "ref_images" in safe_config:
                safe_config["ref_images"] = [os.path.basename(p) for p in safe_config["ref_images"]]

            png_info = PngImagePlugin.PngInfo()
            png_info.add_text("parameters", json.dumps(safe_config, ensure_ascii=False))
            png_info.add_text("Software", "Gemini Generator")

            image.save(full_path, "PNG", pnginfo=png_info)
            return full_path, filename
        except Exception as e:
            return None, str(e)

    @staticmethod
    def read_metadata(image_path):
        try:
            with Image.open(image_path) as img:
                params_str = img.info.get("parameters")
                if params_str:
                    return json.loads(params_str)
        except Exception:
            pass
        return None
