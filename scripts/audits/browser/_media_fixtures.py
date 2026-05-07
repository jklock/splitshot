from __future__ import annotations

import math
import random
import struct
import subprocess
import wave
from pathlib import Path


def _write_wav(path: Path, samples: list[float], sample_rate: int) -> None:
    frames = bytearray()
    for sample in samples:
        clipped = max(-1.0, min(1.0, sample))
        frames.extend(struct.pack("<h", int(clipped * 32767)))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(bytes(frames))


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def ensure_stage_video(
    path: Path,
    *,
    duration_ms: int = 2_400,
    beep_ms: int = 400,
    shot_times_ms: list[int] | None = None,
    resolution: tuple[int, int] = (640, 360),
    seed: int = 7,
) -> Path:
    resolved = path.expanduser().resolve()
    if resolved.is_file():
        return resolved

    resolved.parent.mkdir(parents=True, exist_ok=True)
    shot_times = shot_times_ms or [800, 1_150, 1_650]
    sample_rate = 22_050
    duration_samples = int(sample_rate * (duration_ms / 1000.0))
    samples = [0.0] * duration_samples

    beep_start = int(sample_rate * (beep_ms / 1000.0))
    beep_length = int(sample_rate * 0.09)
    for index in range(beep_length):
        window = 0.5 - 0.5 * math.cos((2.0 * math.pi * index) / max(1, beep_length - 1))
        tone = math.sin(2.0 * math.pi * 2600.0 * (index / sample_rate))
        sample_index = beep_start + index
        if 0 <= sample_index < duration_samples:
            samples[sample_index] += 0.85 * tone * window

    rng = random.Random(seed)
    for shot_ms in shot_times:
        shot_start = int(sample_rate * (shot_ms / 1000.0))
        shot_length = int(sample_rate * 0.025)
        for index in range(shot_length):
            envelope = math.exp(-(8.0 * index) / max(1, shot_length - 1))
            burst = rng.gauss(0.0, 1.0) * envelope * 0.95
            sample_index = shot_start + index
            if 0 <= sample_index < duration_samples:
                samples[sample_index] += burst

    wav_path = resolved.with_suffix(".wav")
    video_only_path = resolved.with_name(f"{resolved.stem}-video-only.mp4")
    try:
        _write_wav(wav_path, samples, sample_rate)
        _ffmpeg(
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s={resolution[0]}x{resolution[1]}:d={duration_ms / 1000:.3f}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(video_only_path),
        )
        _ffmpeg(
            "-i",
            str(video_only_path),
            "-i",
            str(wav_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(resolved),
        )
    finally:
        wav_path.unlink(missing_ok=True)
        video_only_path.unlink(missing_ok=True)
    return resolved
