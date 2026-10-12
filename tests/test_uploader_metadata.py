import io
import unittest

import piexif
from PIL import Image

from app.uploader_metadata import (
    format_uploader_description,
    format_uploader_photographer,
    write_photographer_exif,
)


class PhotographerExifTests(unittest.TestCase):
    def test_name_only_in_exif_and_prefix_only_in_description(self):
        photographer = format_uploader_photographer(" Alex ", enabled=True)
        self.assertEqual(photographer, "Alex")
        self.assertEqual(
            format_uploader_description(photographer, "Photo taken by "),
            "Photo taken by Alex",
        )

    def test_disabled_or_blank_name_skips_both_fields(self):
        for name, enabled in (("Alex", False), ("  ", True), (None, True)):
            photographer = format_uploader_photographer(name, enabled=enabled)
            self.assertIsNone(photographer)
            self.assertIsNone(format_uploader_description(photographer, "Photo taken by "))

    def test_writes_artist_without_changing_pixels_or_existing_exif(self):
        original = io.BytesIO()
        image = Image.new("RGB", (8, 8), (24, 96, 180))
        image.save(
            original,
            format="JPEG",
            exif=piexif.dump({
                "0th": {piexif.ImageIFD.Make: b"Test camera"},
                "Exif": {piexif.ExifIFD.DateTimeOriginal: b"2026:10:12 11:11:09"},
            }),
        )
        original_bytes = original.getvalue()

        result, warning = write_photographer_exif(original_bytes, "Alex")

        self.assertIsNone(warning)
        metadata = piexif.load(result)
        self.assertEqual(metadata["0th"][piexif.ImageIFD.Artist], b"Alex")
        self.assertEqual(metadata["0th"][piexif.ImageIFD.Make], b"Test camera")
        self.assertEqual(
            metadata["Exif"][piexif.ExifIFD.DateTimeOriginal],
            b"2026:10:12 11:11:09",
        )
        with Image.open(io.BytesIO(original_bytes)) as before:
            with Image.open(io.BytesIO(result)) as after:
                self.assertEqual(before.size, after.size)
                self.assertEqual(before.tobytes(), after.tobytes())

    def test_empty_name_leaves_file_unchanged(self):
        original = b"unchanged"
        self.assertEqual(write_photographer_exif(original, None), (original, None))

    def test_unsupported_file_returns_warning_and_original_bytes(self):
        original = b"\x89PNG\r\n\x1a\n"
        result, warning = write_photographer_exif(original, "Alex")
        self.assertEqual(result, original)
        self.assertIn("only supported for JPEG", warning)


if __name__ == "__main__":
    unittest.main()
