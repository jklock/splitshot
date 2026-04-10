from __future__ import annotations

import io
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from splitshot.media.ffmpeg import MediaError, run_ffmpeg


def extract_audio_wav(video_path: str | Path, wav_path: str | Path, sample_rate: int = 22050) -> Path:
    output_path = Path(wav_path)
    run_ffmpeg(
        [
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    )
    return output_path


def read_wav_mono(path: str | Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_rate = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        frame_count = wav_file.getnframes()
        raw_frames = wav_file.readframes(frame_count)

    if sample_width != 2:
        raise MediaError("Only 16-bit PCM WAV is supported")

    samples = np.frombuffer(raw_frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples, sample_rate


def waveform_envelope(samples: np.ndarray, bins: int = 4096) -> list[float]:
    if samples.size == 0:
        return [0.0] * bins
    chunk_size = max(1, samples.size // bins)
    trimmed = samples[: chunk_size * bins]
    chunks = trimmed.reshape(-1, chunk_size)
    envelope = np.mean(np.abs(chunks), axis=1)
    if envelope.size < bins:
        envelope = np.pad(envelope, (0, bins - envelope.size))
    peak = float(np.max(envelope)) or 1.0
    return (envelope / peak).tolist()
