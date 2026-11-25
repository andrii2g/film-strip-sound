"""Encode and decode a variable-area optical soundtrack in a PNG."""

import argparse
import struct
import wave
from pathlib import Path

from PIL import Image


SAMPLE_RATE = 8000
TRACK_WIDTH = 64
SILENCE_WIDTH = TRACK_WIDTH // 2
PCM_STEP = 1024


def encode(source: Path, destination: Path) -> None:
    with wave.open(str(source), "rb") as wav:
        audio_format = (wav.getframerate(), wav.getnchannels(), wav.getsampwidth(), wav.getcomptype())
        if audio_format != (SAMPLE_RATE, 1, 2, "NONE"):
            raise ValueError("Expected an 8 kHz mono, signed 16-bit PCM WAV.")
        frame_count = wav.getnframes()
        pcm = wav.readframes(frame_count)

    if not frame_count or len(pcm) != frame_count * 2:
        raise ValueError("The WAV has no samples or its audio data is truncated.")

    rows = [
        b"\xff" * width + b"\x00" * (TRACK_WIDTH - width)
        for width in range(TRACK_WIDTH + 1)
    ]
    pixels = b"".join(
        rows[SILENCE_WIDTH + round(sample / PCM_STEP)]
        for (sample,) in struct.iter_unpack("<h", pcm)
    )
    track = Image.frombytes("L", (TRACK_WIDTH, frame_count), pixels)
    track.convert("1", dither=Image.Dither.NONE).save(destination, format="PNG")


def decode(source: Path, destination: Path) -> None:
    with Image.open(source, formats=["PNG"]) as track:
        if track.width != TRACK_WIDTH:
            raise ValueError(f"Expected a {TRACK_WIDTH}-pixel-wide PNG.")
        if track.is_animated:
            raise ValueError("Expected a single-frame PNG.")
        if track.mode not in {"1", "L", "LA", "P", "RGB", "RGBA"}:
            raise ValueError(f"Unsupported PNG color mode: {track.mode}.")
        pixels = track.convert("RGBA").tobytes()

    white = b"\xff\xff\xff\xff"
    black = b"\x00\x00\x00\xff"
    samples_by_row = {
        white * width + black * (TRACK_WIDTH - width): struct.pack(
            "<h", min(32767, (width - SILENCE_WIDTH) * PCM_STEP)
        )
        for width in range(TRACK_WIDTH + 1)
    }
    pcm = bytearray()
    row_size = TRACK_WIDTH * 4
    for row_number, offset in enumerate(range(0, len(pixels), row_size)):
        sample = samples_by_row.get(pixels[offset : offset + row_size])
        if sample is None:
            raise ValueError(
                f"Invalid row {row_number}: expected white pixels followed by black pixels, "
                "all opaque."
            )
        pcm.extend(sample)

    with wave.open(str(destination), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, action, help_text in (
        ("encode", encode, "Convert an 8 kHz mono PCM WAV to a track PNG."),
        ("decode", decode, "Convert a track PNG to an 8 kHz mono PCM WAV."),
    ):
        command = commands.add_parser(name, help=help_text, description=help_text)
        command.add_argument("source", type=Path, help="Input file")
        command.add_argument("destination", type=Path, help="Output file")
        command.set_defaults(action=action)

    args = parser.parse_args()
    try:
        args.action(args.source, args.destination)
    except (EOFError, OSError, ValueError, wave.Error, Image.DecompressionBombError) as error:
        parser.exit(1, f"{parser.prog}: {args.command}: {error or 'unexpected end of file'}\n")


if __name__ == "__main__":
    main()
