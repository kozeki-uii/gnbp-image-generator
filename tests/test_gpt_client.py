import base64
import io
import os
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from config.config_mgr import GenConfig
from core.gpt_client import GptApiClient, build_openai_image_url, normalize_openai_base_url


def make_png_bytes(color="red"):
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color).save(buffer, "PNG")
    return buffer.getvalue()


class FakeResponse:
    ok = True
    status_code = 200
    text = ""

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FakeImageResponse:
    ok = True
    status_code = 200
    text = ""

    def __init__(self, content):
        self.content = content


class GptClientTests(unittest.TestCase):
    def test_base_url_accepts_both_host_and_v1_forms(self):
        self.assertEqual(normalize_openai_base_url("https://example.com"), "https://example.com/v1")
        self.assertEqual(normalize_openai_base_url("https://example.com/v1/"), "https://example.com/v1")
        self.assertEqual(
            build_openai_image_url("https://example.com/v1", "images/edits"),
            "https://example.com/v1/images/edits",
        )

    def test_edit_uses_playground_multipart_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = os.path.join(directory, "source.png")
            mask_path = os.path.join(directory, "mask.png")
            output_dir = os.path.join(directory, "output")
            with open(source_path, "wb") as handle:
                handle.write(make_png_bytes())
            with open(mask_path, "wb") as handle:
                handle.write(make_png_bytes("black"))

            config = GenConfig(
                api_url="https://aihub.top/v1",
                api_key="secret",
                model="gpt-image-2",
                prompt="edit this image",
                aspect_ratio="",
                resolution="",
                output_dir=output_dir,
                api_type="gpt",
                ref_images=[source_path],
                mask_image=mask_path,
                size="1024x1024",
                quality="high",
                output_format="png",
                moderation="auto",
            )

            with patch(
                "core.gpt_client.requests.post",
                return_value=FakeResponse({"data": [{"b64_json": base64.b64encode(make_png_bytes()).decode()}]}),
            ) as post:
                success, result = GptApiClient(lambda _message: None).generate(config)

            self.assertTrue(success)
            self.assertTrue(os.path.isfile(result))
            self.assertEqual(post.call_args.args[0], "https://aihub.top/v1/images/edits")
            self.assertEqual([field for field, _value in post.call_args.kwargs["files"]], ["image[]", "mask"])
            self.assertEqual(post.call_args.kwargs["data"]["output_format"], "png")
            self.assertEqual(post.call_args.kwargs["data"]["moderation"], "auto")

    def test_generation_accepts_data_url_results(self):
        with tempfile.TemporaryDirectory() as directory:
            config = GenConfig(
                api_url="https://aihub.top",
                api_key="secret",
                model="gpt-image-2",
                prompt="generate",
                aspect_ratio="",
                resolution="",
                output_dir=directory,
                api_type="gpt",
            )
            data_url = "data:image/png;base64," + base64.b64encode(make_png_bytes()).decode()

            with patch(
                "core.gpt_client.requests.post",
                return_value=FakeResponse({"data": [{"url": data_url}]}),
            ):
                success, result = GptApiClient(lambda _message: None).generate(config)

            self.assertTrue(success)
            self.assertTrue(os.path.isfile(result))

    def test_generation_saves_all_results_and_sends_n(self):
        with tempfile.TemporaryDirectory() as directory:
            config = GenConfig(
                api_url="https://aihub.top/v1",
                api_key="secret",
                model="gpt-image-2",
                prompt="generate two",
                aspect_ratio="",
                resolution="",
                output_dir=directory,
                api_type="gpt",
                n=2,
            )
            image_b64 = base64.b64encode(make_png_bytes()).decode()

            with patch(
                "core.gpt_client.requests.post",
                return_value=FakeResponse({"data": [{"b64_json": image_b64}, {"b64_json": image_b64}]}),
            ) as post:
                success, result = GptApiClient(lambda _message: None).generate(config)

            self.assertTrue(success)
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 2)
            self.assertEqual(post.call_args.kwargs["json"]["n"], 2)
            self.assertTrue(all(os.path.isfile(path) for path in result))

    def test_remote_image_url_download_keeps_authorization(self):
        with tempfile.TemporaryDirectory() as directory:
            config = GenConfig(
                api_url="https://aihub.top/v1",
                api_key="secret",
                model="gpt-image-2",
                prompt="generate",
                aspect_ratio="",
                resolution="",
                output_dir=directory,
                api_type="gpt",
            )

            with patch(
                "core.gpt_client.requests.post",
                return_value=FakeResponse({"data": [{"url": "https://cdn.example/image.png"}]}),
            ), patch(
                "core.gpt_client.requests.get",
                return_value=FakeImageResponse(make_png_bytes()),
            ) as download:
                success, result = GptApiClient(lambda _message: None).generate(config)

            self.assertTrue(success)
            self.assertTrue(os.path.isfile(result))
            self.assertEqual(download.call_args.kwargs["headers"]["Authorization"], "Bearer secret")

    def test_responses_generation_uses_image_generation_tool(self):
        with tempfile.TemporaryDirectory() as directory:
            config = GenConfig(
                api_url="https://aihub.top/v1",
                api_key="secret",
                model="gpt-5",
                prompt="generate with responses",
                aspect_ratio="",
                resolution="",
                output_dir=directory,
                api_type="gpt",
                api_mode="responses",
                size="1536x1024",
                quality="high",
                output_format="png",
            )
            image_b64 = base64.b64encode(make_png_bytes()).decode()

            with patch(
                "core.gpt_client.requests.post",
                return_value=FakeResponse({
                    "output": [{"type": "image_generation_call", "result": image_b64}]
                }),
            ) as post:
                success, result = GptApiClient(lambda _message: None).generate(config)

            self.assertTrue(success)
            self.assertTrue(os.path.isfile(result))
            self.assertEqual(post.call_args.args[0], "https://aihub.top/v1/responses")
            payload = post.call_args.kwargs["json"]
            self.assertEqual(payload["tool_choice"], "required")
            self.assertEqual(payload["tools"][0]["type"], "image_generation")
            self.assertEqual(payload["tools"][0]["action"], "generate")
            self.assertEqual(payload["tools"][0]["size"], "1536x1024")
            self.assertIn("generate with responses", payload["input"])

    def test_responses_edit_embeds_references_and_mask_as_data_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = os.path.join(directory, "source.png")
            mask_path = os.path.join(directory, "mask.png")
            with open(source_path, "wb") as handle:
                handle.write(make_png_bytes())
            with open(mask_path, "wb") as handle:
                handle.write(make_png_bytes("black"))

            config = GenConfig(
                api_url="https://aihub.top",
                api_key="secret",
                model="gpt-5",
                prompt="edit with mask",
                aspect_ratio="",
                resolution="",
                output_dir=directory,
                api_type="gpt",
                api_mode="responses",
                ref_images=[source_path],
                mask_image=mask_path,
            )
            image_b64 = base64.b64encode(make_png_bytes()).decode()

            with patch(
                "core.gpt_client.requests.post",
                return_value=FakeResponse({
                    "output": [{
                        "type": "image_generation_call",
                        "result": {"b64_json": image_b64},
                    }]
                }),
            ) as post:
                success, result = GptApiClient(lambda _message: None).generate(config)

            self.assertTrue(success)
            self.assertTrue(os.path.isfile(result))
            payload = post.call_args.kwargs["json"]
            content = payload["input"][0]["content"]
            self.assertEqual(content[1]["type"], "input_image")
            self.assertTrue(content[1]["image_url"].startswith("data:image/png;base64,"))
            tool = payload["tools"][0]
            self.assertEqual(tool["action"], "edit")
            self.assertTrue(tool["input_image_mask"]["image_url"].startswith("data:image/png;base64,"))


if __name__ == "__main__":
    unittest.main()
