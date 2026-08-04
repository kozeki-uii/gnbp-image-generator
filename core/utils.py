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
    def image_bytes_as_png(image_path):
        """将图片转成 PNG 字节，用于遮罩编辑接口的文件上传。"""
        try:
            with Image.open(image_path) as image:
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                return buffer.getvalue()
        except Exception as e:
            print(f"PNG 转换失败: {e}")
            return None

    @staticmethod
    def images_have_same_size(first_path, second_path):
        try:
            with Image.open(first_path) as first, Image.open(second_path) as second:
                return first.size == second.size
        except Exception:
            return False

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
            if "," in base64_data: base64_data = base64_data.split(",")[1]
            base64_data = base64_data.replace('\n', '').replace('\r', '')
            return ImageUtils.save_image_bytes(
                base64.b64decode(base64_data, validate=True), output_dir, config_dict
            )
        except Exception as e:
            return None, str(e)

    @staticmethod
    def save_image_bytes(image_bytes, output_dir, config_dict):
        try:
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            output_format = str(config_dict.get("output_format", "png")).lower()
            format_map = {
                "png": ("PNG", "png"),
                "jpeg": ("JPEG", "jpg"),
                "jpg": ("JPEG", "jpg"),
                "webp": ("WEBP", "webp"),
            }
            image_format, extension = format_map.get(output_format, ("PNG", "png"))
            filename = f"gen_{timestamp}_{uuid.uuid4().hex[:8]}.{extension}"
            full_path = os.path.join(output_dir, filename)

            image = Image.open(io.BytesIO(image_bytes))

            # 元数据处理 (脱敏)
            safe_config = copy.deepcopy(config_dict)
            if "api_key" in safe_config: del safe_config["api_key"]
            if "ref_images" in safe_config:
                safe_config["ref_images"] = [os.path.basename(p) for p in safe_config["ref_images"]]
            if safe_config.get("mask_image"):
                safe_config["mask_image"] = os.path.basename(safe_config["mask_image"])

            metadata = json.dumps(safe_config, ensure_ascii=False)
            if image_format == "PNG":
                png_info = PngImagePlugin.PngInfo()
                png_info.add_text("parameters", metadata)
                png_info.add_text("Software", "GNBP Image Generator")
                image.save(full_path, image_format, pnginfo=png_info)
            else:
                if image_format == "JPEG" and image.mode not in ("RGB", "L"):
                    image = image.convert("RGB")
                compression = config_dict.get("output_compression")
                quality = 95
                if isinstance(compression, (int, float)) and compression > 0:
                    quality = max(1, min(95, int(100 - compression)))
                image.save(full_path, image_format, quality=quality)
                with open(f"{full_path}.json", "w", encoding="utf-8") as handle:
                    json.dump(safe_config, handle, ensure_ascii=False, indent=2)
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
        try:
            sidecar_path = f"{image_path}.json"
            if os.path.isfile(sidecar_path):
                with open(sidecar_path, "r", encoding="utf-8") as handle:
                    return json.load(handle)
        except Exception:
            pass
        return None

    @staticmethod
    def list_image_files(output_dir, limit=60):
        """返回输出目录中最新的图片，供应用启动时恢复历史图库。"""
        if not output_dir or not os.path.isdir(output_dir):
            return []

        image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        files = []
        try:
            for entry in os.scandir(output_dir):
                if not entry.is_file() or os.path.splitext(entry.name)[1].lower() not in image_extensions:
                    continue
                try:
                    files.append((entry.stat().st_mtime, entry.path))
                except OSError:
                    continue
        except OSError:
            return []

        files.sort(key=lambda item: item[0], reverse=True)
        return [path for _mtime, path in files[:max(0, int(limit))]]
