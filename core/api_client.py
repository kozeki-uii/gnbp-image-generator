# 文件路径: core/api_client.py

import requests
import time
import os
import json
from dataclasses import asdict
from config.config_mgr import GenConfig
from core.utils import ImageUtils

class GeminiApiClient:
    def __init__(self, log_callback, verify_ssl=True):
        self.log = log_callback
        self.verify_ssl = verify_ssl

    def generate(self, config: GenConfig):
        try:
            # 去除 URL 末尾斜杠，防止拼接错误
            api_url = config.api_url.rstrip('/')
            full_url = f"{api_url}/v1beta/models/{config.model}:generateContent?key={config.api_key}"

            # 预处理参考图 (调用 core.utils 里的工具)
            ref_parts = []
            if config.ref_images:
                self.log(f"🔄 正在预处理 {len(config.ref_images)} 张参考图...")
                for path in config.ref_images:
                    mime, data = ImageUtils.resize_and_encode(path)
                    if data:
                        ref_parts.append({"inlineData": {"mimeType": mime, "data": data}})
                        ref_parts.append({"text": f"\n[Reference Image: {os.path.basename(path)}]"})

            # 组装 Payload
            parts = [{"text": config.prompt}] + ref_parts

            payload = {
                "contents": [{"parts": parts}],
                "safetySettings": [{"category": c, "threshold": "BLOCK_NONE"} for c in [
                    "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"
                ]],
                "generationConfig": {
                    "temperature": config.temperature,
                    "responseModalities": ["IMAGE"],
                    "imageConfig": {"aspectRatio": config.aspect_ratio, "imageSize": config.resolution}
                }
            }

            self.log(f"🚀 发送请求: {config.model} | {config.aspect_ratio} | {config.resolution}")
            start_t = time.time()

            # 发送请求
            response = requests.post(
                full_url, json=payload, headers={"Content-Type": "application/json"},
                timeout=400, verify=self.verify_ssl
            )

            duration = time.time() - start_t

            if not response.ok:
                text = response.text.strip()
                if len(text) > 500:
                    text = f"{text[:500]}..."
                return False, f"HTTP {response.status_code}: {text}"

            result = response.json()
            candidates = result.get('candidates', [])

            if not candidates:
                reason = result.get('promptFeedback', {}).get('blockReason', 'Unknown')
                return False, f"Blocked: {reason}"

            # 解析返回的图片
            for part in candidates[0].get('content', {}).get('parts', []):
                if 'inlineData' in part or 'inline_data' in part:
                    img_data = part.get('inlineData') or part.get('inline_data')
                    # 保存图片 (调用 core.utils)
                    path, name = ImageUtils.save_image(img_data['data'], config.output_dir, asdict(config))
                    if path:
                        self.log(f"🎉 生成成功: {duration:.2f}s | {name}")
                        return True, path
                    else:
                        return False, f"Save Failed: {name}"

            return False, "No image data in response"

        except Exception as e:
            return False, str(e)
