"""Verify the bundled tone through the public CLI."""

import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent


class FilmStripSoundTest(unittest.TestCase):
    def read_samples(self, path: Path) -> tuple[int, ...]:
        with wave.open(str(path), "rb") as wav:
            self.assertEqual(wav.getparams()[:5], (1, 2, 8000, 8000, "NONE"))
            return struct.unpack("<8000h", wav.readframes(8000))

    def test_round_trip_and_painted_silence(self) -> None:
        cli = [sys.executable, str(ROOT / "film_strip_sound.py")]
        tone = ROOT / "examples" / "tone.wav"
        start, stop = 2002, 2802

        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            track = work / "tone.png"
            round_trip = work / "roundtrip.wav"
            edited_track = work / "tone-muted.png"
            edited_wav = work / "muted.wav"

            subprocess.run([*cli, "encode", str(tone), str(track)], check=True)
            subprocess.run([*cli, "decode", str(track), str(round_trip)], check=True)
            original = self.read_samples(tone)
            decoded = self.read_samples(round_trip)
            max_error = max(abs(a - b) for a, b in zip(original, decoded, strict=True))
            self.assertLessEqual(max_error, 512)

            with Image.open(track) as image:
                self.assertEqual((image.mode, image.size), ("1", (64, 8000)))
                edited = image.convert("RGB")
            edited.paste((255, 255, 255), (0, start, 32, stop))
            edited.paste((0, 0, 0), (32, start, 64, stop))
            edited.save(edited_track)

            subprocess.run([*cli, "decode", str(edited_track), str(edited_wav)], check=True)
            muted = self.read_samples(edited_wav)
            self.assertEqual(muted[start:stop], (0,) * 800)
            self.assertNotEqual(muted[start - 1], 0)
            self.assertNotEqual(muted[stop], 0)
            self.assertEqual(muted[:start], decoded[:start])
            self.assertEqual(muted[stop:], decoded[stop:])
