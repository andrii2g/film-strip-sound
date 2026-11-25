# film-strip-sound

Turn a WAV into a black-and-white picture you can edit and play back. The
codec borrows the width modulation of a [variable-area optical soundtrack][fiaf].

## Try it

```sh
python -m pip install -r requirements.txt
python film_strip_sound.py encode examples/tone.wav tone.png
python film_strip_sound.py decode tone.png roundtrip.wav
```

`examples/tone.wav` is a one-second, 440 Hz sine wave with a peak amplitude of
24,000 PCM counts. Compare it with `roundtrip.wav` to hear the effect of
quantizing the waveform to whole pixels.

To add a 100 ms gap, edit a copy of `tone.png` without resizing or antialiasing.
In zero-based rows 2002 through 2801, make columns 0 through 31 white and
columns 32 through 63 black. Save the copy as `tone-muted.png` and decode it.

```sh
python film_strip_sound.py decode tone-muted.png muted.wav
```

## Track format

Audio is 8 kHz mono, signed 16-bit PCM. The PNG is 64 pixels wide, with one
sample per row from top to bottom. Each row consists of a white band starting
at the left edge and a black remainder. Either can be empty. The encoder
writes a 1-bit PNG, and the decoder also accepts opaque black-and-white rows
in PNGs saved by typical image editors.

The encoder uses `width = 32 + round(sample / 1024)`. The decoder uses
`sample = min(32767, (width - 32) * 1024)`. Width 32 is digital silence. Each
pixel of width represents 1,024 PCM counts, and the untouched round trip
differs by at most 512 counts per sample.

## Verify

```sh
python -m unittest -v
```

The test runs both commands on the bundled tone. It checks the 512-count
error bound, paints the 800 rows in an RGB copy of the track, and verifies
that the decoded edit gives exactly 100 ms of digital silence with identical
audio to the untouched decode outside the gap.

[fiaf]: https://www.fiafnet.org/pages/E-Resources/Technical-Terms-Full-List.html
