import base64
import json
import mimetypes
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from config.config_mgr import GenConfig
from core.utils import ImageUtils


REQUEST_TIMEOUT = 400
PROMPT_REWRITE_GUARD_PREFIX = (
    'Treat everything after this line as one complete image-generation prompt, '
    'including the resolution instruction. Follow it exactly without rewriting '
    'or omitting anything:'
)


def normalize_openai_base_url(api_url):
    """同时接受 https://host 和 https://host/v1 两种填写方式。"""
    base_url = api_url.strip().rstrip('/')
    if not base_url:
        return ''
    if base_url.lower().endswith('/v1'):
        return base_url
    return f'{base_url}/v1'


def build_openai_image_url(api_url, path):
    base_url = normalize_openai_base_url(api_url)
    return f"{base_url}/{path.lstrip('/')}"


class GptApiClient:
    def __init__(self, log_callback, verify_ssl=True):
        self.log = log_callback
        self.verify_ssl = verify_ssl

    def generate(self, config: GenConfig):
        if config.api_mode == 'responses':
            return self._responses(config)
        if config.ref_images:
            return self._edit(config)
        return self._generate(config)

    def _headers(self):
        return {
            'Accept': 'application/json',
        }

    def _auth_headers(self, config):
        return {
            **self._headers(),
            'Authorization': f'Bearer {config.api_key}',
        }

    @staticmethod
    def _file_to_data_url(path, force_png=False):
        if force_png:
            content = ImageUtils.image_bytes_as_png(path)
            mime_type = 'image/png'
        else:
            with open(path, 'rb') as handle:
                content = handle.read()
            mime_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        if not content:
            return None
        encoded = base64.b64encode(content).decode('ascii')
        return f'data:{mime_type};base64,{encoded}'

    def _build_responses_payload(self, config):
        input_images = []
        for index, path in enumerate(config.ref_images):
            if not os.path.isfile(path):
                continue
            data_url = self._file_to_data_url(
                path,
                force_png=bool(config.mask_image and index == 0),
            )
            if data_url:
                input_images.append(data_url)

        if config.ref_images and not input_images:
            raise ValueError('没有有效的参考图文件')

        tool = {
            'type': 'image_generation',
            'action': 'edit' if input_images else 'generate',
            'output_format': config.output_format,
            'moderation': config.moderation,
            'size': config.size,
            'quality': config.quality,
        }
        if config.output_compression is not None and config.output_format != 'png':
            tool['output_compression'] = config.output_compression

        if config.mask_image:
            if not input_images:
                raise ValueError('使用遮罩前请先添加至少一张参考图')
            if not os.path.isfile(config.mask_image):
                raise ValueError('遮罩文件不存在')
            if not ImageUtils.images_have_same_size(config.ref_images[0], config.mask_image):
                raise ValueError('遮罩尺寸必须与第一张参考图一致')
            mask_data_url = self._file_to_data_url(config.mask_image, force_png=True)
            if not mask_data_url:
                raise ValueError('遮罩文件无法读取')
            tool['input_image_mask'] = {'image_url': mask_data_url}

        prompt = f'{PROMPT_REWRITE_GUARD_PREFIX}\n{config.prompt}'
        if input_images:
            request_input = [{
                'role': 'user',
                'content': [
                    {'type': 'input_text', 'text': prompt},
                    *[
                        {'type': 'input_image', 'image_url': image_url}
                        for image_url in input_images
                    ],
                ],
            }]
        else:
            request_input = prompt

        return {
            'model': config.model,
            'input': request_input,
            'tools': [tool],
            'tool_choice': 'required',
        }

    def _responses(self, config):
        count = max(1, min(10, int(config.n)))
        if count == 1:
            return self._responses_single(config)

        saved_paths = []
        errors = []
        with ThreadPoolExecutor(max_workers=min(count, 8)) as executor:
            futures = [executor.submit(self._responses_single, config) for _ in range(count)]
            for future in as_completed(futures):
                success, result = future.result()
                if success:
                    saved_paths.extend(result if isinstance(result, list) else [result])
                else:
                    errors.append(result)

        if saved_paths:
            return True, saved_paths[0] if len(saved_paths) == 1 else saved_paths
        return False, errors[0] if errors else '所有 Responses API 请求均失败'

    def _responses_single(self, config):
        try:
            full_url = build_openai_image_url(config.api_url, 'responses')
            payload = self._build_responses_payload(config)
            self.log(f'🚀 发送 Responses 请求: {config.model} | {config.size} | {config.quality}')
            start_t = time.time()
            response = requests.post(
                full_url,
                json=payload,
                headers={**self._auth_headers(config), 'Content-Type': 'application/json'},
                timeout=REQUEST_TIMEOUT,
                verify=self.verify_ssl,
            )
            duration = time.time() - start_t
            if not response.ok:
                return False, self._format_http_error(response)
            return self._parse_responses_response(response.json(), config, duration)
        except Exception as e:
            return False, str(e)

    def _generate(self, config):
        try:
            full_url = build_openai_image_url(config.api_url, 'images/generations')
            payload = {
                'model': config.model,
                'prompt': config.prompt,
                'n': max(1, min(10, int(config.n))),
                'size': config.size,
                'quality': config.quality,
                'output_format': config.output_format,
                'moderation': config.moderation,
            }
            if config.output_compression is not None and config.output_format != 'png':
                payload['output_compression'] = config.output_compression

            self.log(f'🚀 发送请求: {config.model} | {config.size} | {config.quality}')
            start_t = time.time()
            response = requests.post(
                full_url,
                json=payload,
                headers={**self._auth_headers(config), 'Content-Type': 'application/json'},
                timeout=REQUEST_TIMEOUT,
                verify=self.verify_ssl,
            )
            duration = time.time() - start_t
            if not response.ok:
                return False, self._format_http_error(response)
            return self._parse_response(response.json(), config, duration)
        except Exception as e:
            return False, str(e)

    def _edit(self, config):
        try:
            full_url = build_openai_image_url(config.api_url, 'images/edits')
            data = {
                'model': config.model,
                'prompt': config.prompt,
                'n': str(max(1, min(10, int(config.n)))),
                'size': config.size,
                'quality': config.quality,
                'output_format': config.output_format,
                'moderation': config.moderation,
            }
            if config.output_compression is not None and config.output_format != 'png':
                data['output_compression'] = str(config.output_compression)

            files = []
            for index, path in enumerate(config.ref_images):
                if not os.path.isfile(path):
                    continue
                if config.mask_image and index == 0:
                    content = ImageUtils.image_bytes_as_png(path)
                    mime_type = 'image/png'
                else:
                    with open(path, 'rb') as handle:
                        content = handle.read()
                    mime_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
                if content:
                    files.append(('image[]', (os.path.basename(path), content, mime_type)))

            if not files:
                return False, '没有有效的参考图文件'

            if config.mask_image:
                if not os.path.isfile(config.mask_image):
                    return False, '遮罩文件不存在'
                if not ImageUtils.images_have_same_size(config.ref_images[0], config.mask_image):
                    return False, '遮罩尺寸必须与第一张参考图一致'
                mask_content = ImageUtils.image_bytes_as_png(config.mask_image)
                if not mask_content:
                    return False, '遮罩文件无法读取'
                files.append(('mask', ('mask.png', mask_content, 'image/png')))

            self.log(f'🔄 正在上传 {len(files) - (1 if config.mask_image else 0)} 张参考图...')
            self.log(f'🚀 发送编辑请求: {config.model} | {config.size} | {config.quality}')
            start_t = time.time()
            response = requests.post(
                full_url,
                headers=self._auth_headers(config),
                data=data,
                files=files,
                timeout=REQUEST_TIMEOUT,
                verify=self.verify_ssl,
            )
            duration = time.time() - start_t
            if not response.ok:
                return False, self._format_http_error(response)
            return self._parse_response(response.json(), config, duration)
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _format_http_error(response):
        text = response.text.strip()
        if len(text) > 500:
            text = f'{text[:500]}...'
        return f'HTTP {response.status_code}: {text}'

    def _parse_response(self, result, config, duration):
        if not isinstance(result, dict):
            return False, '接口返回的数据不是 JSON 对象'
        data_field = result.get('data', [])
        if isinstance(data_field, dict):
            data_field = [data_field]
        if not isinstance(data_field, list) or not data_field:
            return False, f'No image data in response: {json.dumps(result, ensure_ascii=False)[:500]}'

        saved_paths = []
        for item in data_field:
            if not isinstance(item, dict):
                continue
            b64 = item.get('b64_json')
            if isinstance(b64, str) and b64:
                try:
                    image_path, image_name = ImageUtils.save_image(b64, config.output_dir, vars(config))
                except Exception as e:
                    return False, f'Save Failed: {e}'
            else:
                image_url = item.get('url')
                if not isinstance(image_url, str) or not image_url:
                    continue
                if image_url.startswith('data:'):
                    image_path, image_name = ImageUtils.save_image(
                        image_url, config.output_dir, vars(config)
                    )
                else:
                    image_response = requests.get(
                        image_url,
                        headers=self._auth_headers(config),
                        timeout=REQUEST_TIMEOUT,
                        verify=self.verify_ssl,
                    )
                    if not image_response.ok:
                        return False, self._format_http_error(image_response)
                    image_path, image_name = ImageUtils.save_image_bytes(
                        image_response.content, config.output_dir, vars(config)
                    )

            if image_path:
                self.log(f'🎉 生成成功: {duration:.2f}s | {image_name}')
                saved_paths.append(image_path)

        if saved_paths:
            return True, saved_paths[0] if len(saved_paths) == 1 else saved_paths

        return False, f'No image data in response: {json.dumps(result, ensure_ascii=False)[:500]}'

    def _parse_responses_response(self, result, config, duration):
        if not isinstance(result, dict):
            return False, '接口返回的数据不是 JSON 对象'
        output = result.get('output', [])
        if not isinstance(output, list):
            output = []

        saved_paths = []
        for item in output:
            if not isinstance(item, dict) or item.get('type') != 'image_generation_call':
                continue
            image_result = item.get('result')
            if isinstance(image_result, dict):
                image_result = next((
                    image_result.get(key)
                    for key in ('b64_json', 'base64', 'image', 'data')
                    if isinstance(image_result.get(key), str) and image_result.get(key)
                ), None)
            if not isinstance(image_result, str) or not image_result.strip():
                continue
            image_path, image_name = ImageUtils.save_image(
                image_result,
                config.output_dir,
                vars(config),
            )
            if image_path:
                self.log(f'🎉 生成成功: {duration:.2f}s | {image_name}')
                saved_paths.append(image_path)

        if saved_paths:
            return True, saved_paths[0] if len(saved_paths) == 1 else saved_paths
        return False, f'No image data in Responses output: {json.dumps(result, ensure_ascii=False)[:500]}'
