"""Encoder settings for the browser player.

Browsers cannot play what a Tablo actually receives: over-the-air broadcast is
MPEG-2 video with AC-3 audio, and no browser decodes either. So the browser
path has to re-encode, and every setting here is a quality/CPU trade someone
might want to make differently.

The defaults aim at "looks like the source on a laptop screen" rather than the
smallest possible stream. Broadcast 1080i runs 12-19 Mbit/s; squeezing that
into a couple of megabits with the fastest x264 preset is what makes a
re-encode look soft next to a TV playing the original.

None of this touches the IPTV path, which is a straight `-c copy` and stays
bit-for-bit identical to what the antenna received.
"""

import os


def _env(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


def video_args() -> list[str]:
    """x264 settings, and the deinterlacer the source requires.

    yadif is not optional: OTA 1080i is interlaced, and handing interlaced
    frames to a browser produces combing on every horizontal motion. Mode 1
    emits a frame per field, doubling the frame rate to ~59.94 for smoother
    motion at roughly twice the CPU.
    """
    mode = _env("TABLO_DEINTERLACE", "0")
    preset = _env("TABLO_PRESET", "veryfast")
    crf = _env("TABLO_CRF", "21")
    maxrate = _env("TABLO_MAXRATE", "8000k")
    bufsize = _env("TABLO_BUFSIZE", "16000k")
    return [
        "-vf", f"yadif={mode}",
        "-c:v", "libx264", "-preset", preset, "-crf", crf,
        "-maxrate", maxrate, "-bufsize", bufsize,
        "-pix_fmt", "yuv420p", "-g", "60",
    ]


def audio_args() -> list[str]:
    """AAC settings.

    The source is AC-3 5.1. Browsers handle multichannel AAC inconsistently,
    so the default folds to stereo — but at a bitrate that does not also throw
    away the audio while it is at it.
    """
    channels = _env("TABLO_AUDIO_CHANNELS", "2")
    bitrate = _env("TABLO_AUDIO_BITRATE", "192k")
    return ["-c:a", "aac", "-b:a", bitrate, "-ac", channels]


def describe() -> str:
    return " ".join(video_args() + audio_args())
