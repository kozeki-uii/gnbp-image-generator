import base64
import io
import os
import tempfile
import time
import unittest

from PIL import Image

from core.utils import ImageUtils


def make_image_data():
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), "red").save(buffer, "PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


class ImageUtilsTests(unittest.TestCase):
    def test_repeated_saves_use_unique_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            first, _ = ImageUtils.save_image(make_image_data(), directory, {})
            second, _ = ImageUtils.save_image(make_image_data(), directory, {})

            self.assertNotEqual(first, second)
            self.assertEqual(len(os.listdir(directory)), 2)

    def test_metadata_removes_key_and_private_reference_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _ = ImageUtils.save_image(
                make_image_data(),
                directory,
                {
                    "api_key": "secret",
                    "prompt": "test prompt",
                    "ref_images": [r"C:\private\source.png"],
                },
            )

            metadata = ImageUtils.read_metadata(path)

            self.assertNotIn("api_key", metadata)
            self.assertEqual(metadata["ref_images"], ["source.png"])
            self.assertEqual(metadata["prompt"], "test prompt")

    def test_non_png_output_uses_extension_and_sidecar_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _ = ImageUtils.save_image(
                make_image_data(),
                directory,
                {"output_format": "jpeg", "prompt": "jpeg prompt"},
            )

            self.assertTrue(path.endswith(".jpg"))
            self.assertTrue(os.path.isfile(f"{path}.json"))
            self.assertEqual(ImageUtils.read_metadata(path)["prompt"], "jpeg prompt")

    def test_list_image_files_returns_newest_files_with_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            first, _ = ImageUtils.save_image(make_image_data(), directory, {})
            time.sleep(0.02)
            second, _ = ImageUtils.save_image(make_image_data(), directory, {})

            paths = ImageUtils.list_image_files(directory, limit=1)

            self.assertEqual(paths, [second])
            self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
