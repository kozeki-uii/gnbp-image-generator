# 文件路径: core/gpt_client.py

import requests
import time
import os
import json
import urllib3
from dataclasses import asdict
from config.config_mgr import GenConfig
from core.utils import ImageUtils

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class GptApiClient:
    def __init__(self, log_callback):
        self.log = log_callback

    def generate(self, config: GenConfig):
        if config.ref_images:
            return self._edit(config)
        return self._generate(config)

    def _generate(self, config: GenConfig):
        try:
            api_url = config.api_url.rstrip('/')
            full_url = f"{api_url}/v1/images/generations"

            payload = {
                "model": config.model,
                "prompt": config.prompt,
                "n": 1,
                "size": config.size,
                "quality": config.quality
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {config.api_key}"
            }

            self.log(f"🚀 发送请求: {config.model} | {config.size} | {config.quality}")
            start_t = time.time()

            response = requests.post(
                full_url, json=payload, headers=headers,
                timeout=400, verify=False, proxies={"http": None, "https": None}
            )

            duration = time.time() - start_t

            if response.status_code != 200:
                return False, f"HTTP {response.status_code}: {response.text[:200]}..."

            result = response.json()
            return self._parse_response(result, config, duration)

        except Exception as e:
            return False, str(e)

    def _edit(self, config: GenConfig):
        try:
            api_url = config.api_url.rstrip('/')
            full_url = f"{api_url}/v1/images/edits"

            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {config.api_key}"
            }

            data = {
                "model": config.model,
                "prompt": config.prompt,
                "n": "1",
                "size": config.size,
                "quality": config.quality
            }

            self.log(f"🔄 正在上传 {len(config.ref_images)} 张参考图...")
            files = []
            open_files = []
            for path in config.ref_images:
                if os.path.exists(path):
                    f = open(path, "rb")
                    open_files.append(f)
                    files.append(("image", (os.path.basename(path), f, "image/png")))

            if not files:
                return False, "没有有效的参考图文件"

            self.log(f"🚀 发送编辑请求: {config.model} | {config.size} | {config.quality}")
            start_t = time.time()

            try:
                response = requests.post(
                    full_url, headers=headers, data=data, files=files,
                    timeout=400, verify=False, proxies={"http": None, "https": None}
                )
            finally:
                for f in open_files:
                    f.close()

            duration = time.time() - start_t

            if response.status_code != 200:
                return False, f"HTTP {response.status_code}: {response.text[:200]}..."

            result = response.json()
            return self._parse_response(result, config, duration)

        except Exception as e:
            return False, str(e)

    def _parse_response(self, result, config, duration):
        data_field = result.get("data", [])
        if isinstance(data_field, list) and len(data_field) > 0:
            b64 = data_field[0].get("b64_json")
        elif isinstance(data_field, dict):
            b64 = data_field.get("b64_json")
        else:
            b64 = None

        if not b64:
            return False, f"No image data in response: {json.dumps(result, ensure_ascii=False)[:200]}"

        path, name = ImageUtils.save_image(b64, config.output_dir, asdict(config))
        if path:
            self.log(f"🎉 生成成功: {duration:.2f}s | {name}")
            return True, path
        else:
            return False, f"Save Failed: {name}"
