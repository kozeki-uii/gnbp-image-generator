import base64
import io
import os
import tempfile
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


if __name__ == "__main__":
    unittest.main()
