import os
import shutil
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from PIL import Image

from convert_everything.engine.image import ImageConverter
from convert_everything.engine.audio import AudioConverter
from convert_everything.engine.video import VideoConverter
from convert_everything.engine.document import DocumentConverter

class TestConverters(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.test_dir.name)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_01_image_conversions(self):
        # 1. Create a sample RGBA image
        img_path = self.dir_path / "test_image.png"
        img = Image.new("RGBA", (200, 200), color=(255, 0, 0, 128))
        img.save(img_path)

        conv = ImageConverter()

        # Convert to WebP
        res_webp = conv.convert(img_path, target_ext="webp")
        self.assertTrue(res_webp.success, f"WebP conversion failed: {res_webp.error}")
        self.assertTrue(res_webp.output_path.exists())
        self.assertEqual(res_webp.output_path.suffix, ".webp")

        # Convert to JPG (RGBA should blend cleanly with white background)
        res_jpg = conv.convert(img_path, target_ext="jpg", quality=90)
        self.assertTrue(res_jpg.success, f"JPG conversion failed: {res_jpg.error}")
        self.assertTrue(res_jpg.output_path.exists())

        # Convert to ICO
        res_ico = conv.convert(img_path, target_ext="ico")
        self.assertTrue(res_ico.success, f"ICO conversion failed: {res_ico.error}")
        self.assertTrue(res_ico.output_path.exists())

        # Convert to PDF
        res_pdf = conv.convert(img_path, target_ext="pdf")
        self.assertTrue(res_pdf.success, f"PDF conversion failed: {res_pdf.error}")
        self.assertTrue(res_pdf.output_path.exists())

        # Merge multiple images to PDF
        img2_path = self.dir_path / "test_image2.png"
        Image.new("RGB", (100, 100), color=(0, 255, 0)).save(img2_path)
        out_merged_pdf = self.dir_path / "merged_images.pdf"
        res_merge = ImageConverter.merge_to_pdf([img_path, img2_path], out_merged_pdf)
        self.assertTrue(res_merge.success, f"Merge images to PDF failed: {res_merge.error}")
        self.assertTrue(out_merged_pdf.exists())

    def test_02_audio_conversions(self):
        if not shutil.which("ffmpeg"):
            self.skipTest("FFmpeg not installed")

        # Generate a small 0.5s dummy WAV file
        wav_path = self.dir_path / "test_sound.wav"
        framerate = 44100
        nchannels = 1
        sampwidth = 2
        nframes = int(framerate * 0.5)

        with wave.open(str(wav_path), "w") as wf:
            wf.setnchannels(nchannels)
            wf.setsampwidth(sampwidth)
            wf.setframerate(framerate)
            # Silence / low hum
            raw_data = struct.pack(f"<{nframes}h", *([1000] * nframes))
            wf.writeframes(raw_data)

        conv = AudioConverter()

        # Convert to MP3
        res_mp3 = conv.convert(wav_path, target_ext="mp3", bitrate="192k")
        self.assertTrue(res_mp3.success, f"Audio MP3 conversion failed: {res_mp3.error}")
        self.assertTrue(res_mp3.output_path.exists())
        self.assertEqual(res_mp3.output_path.suffix, ".mp3")

        # Convert to FLAC
        res_flac = conv.convert(wav_path, target_ext="flac")
        self.assertTrue(res_flac.success, f"Audio FLAC conversion failed: {res_flac.error}")
        self.assertTrue(res_flac.output_path.exists())

        # Convert to OGG
        res_ogg = conv.convert(wav_path, target_ext="ogg")
        self.assertTrue(res_ogg.success, f"Audio OGG conversion failed: {res_ogg.error}")
        self.assertTrue(res_ogg.output_path.exists())

    def test_03_video_conversions(self):
        if not shutil.which("ffmpeg"):
            self.skipTest("FFmpeg not installed")

        # Generate a 1-second test MP4 via ffmpeg lavfi
        video_path = self.dir_path / "test_video.mp4"
        import subprocess
        gen_cmd = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "testsrc=duration=1:size=160x120:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-c:v", "libx264", "-c:a", "aac",
            str(video_path)
        ]
        subprocess.run(gen_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertTrue(video_path.exists())

        conv = VideoConverter()

        # Convert to WebM
        res_webm = conv.convert(video_path, target_ext="webm")
        self.assertTrue(res_webm.success, f"Video WebM conversion failed: {res_webm.error}")
        self.assertTrue(res_webm.output_path.exists())

        # Convert to 2-pass GIF
        res_gif = conv.convert(video_path, target_ext="gif")
        self.assertTrue(res_gif.success, f"Video to GIF conversion failed: {res_gif.error}")
        self.assertTrue(res_gif.output_path.exists())

        # Extract Audio (MP3) from video
        res_audio = conv.convert(video_path, target_ext="mp3")
        self.assertTrue(res_audio.success, f"Audio extraction from video failed: {res_audio.error}")
        self.assertTrue(res_audio.output_path.exists())

    def test_04_document_and_pdf_merge(self):
        # Create 2 simple PDFs via Pillow
        pdf1_path = self.dir_path / "doc1.pdf"
        pdf2_path = self.dir_path / "doc2.pdf"
        Image.new("RGB", (300, 300), color="white").save(pdf1_path, "PDF")
        Image.new("RGB", (300, 300), color="yellow").save(pdf2_path, "PDF")

        doc_conv = DocumentConverter()

        # Check PDF info
        info = doc_conv.get_pdf_info(pdf1_path)
        self.assertGreaterEqual(info.get("pages", 0), 1)

        # Merge PDFs (User's requested feature)
        merged_pdf = self.dir_path / "merged_docs.pdf"
        res_merge = doc_conv.merge_pdfs([pdf1_path, pdf2_path], merged_pdf)
        self.assertTrue(res_merge.success, f"PDF Merge failed: {res_merge.error}")
        self.assertTrue(merged_pdf.exists())

        merged_info = doc_conv.get_pdf_info(merged_pdf)
        self.assertEqual(merged_info.get("pages"), 2)

        # Compress PDF
        comp_pdf = self.dir_path / "compressed.pdf"
        res_comp = doc_conv.compress_pdf(merged_pdf, output_path=comp_pdf)
        self.assertTrue(res_comp.success, f"PDF Compression failed: {res_comp.error}")
        self.assertTrue(comp_pdf.exists())

        # Extract pages to images
        if shutil.which("pdftoppm"):
            res_ext = doc_conv.extract_pages_to_images(merged_pdf, target_ext="png", output_dir=self.dir_path)
            self.assertTrue(res_ext.success, f"PDF page extraction failed: {res_ext.error}")

if __name__ == "__main__":
    unittest.main()
