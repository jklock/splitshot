from __future__ import annotations

import os
import wave
from pathlib import Path

import numpy as np
import pytest
import subprocess

import splitshot.config as splitshot_config


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def _ensure_qapp(qapp):
    return qapp


@pytest.fixture(autouse=True)
def _isolate_splitshot_settings(tmp_path, monkeypatch):
    home_dir = tmp_path / "home"
    app_dir = home_dir / ".splitshot"
    playwright_cache_candidates = [
        Path.home() / "Library" / "Caches" / "ms-playwright",
        Path.home() / ".cache" / "ms-playwright",
    ]
    home_dir.mkdir(parents=True, exist_ok=True)
    for cache_dir in playwright_cache_candidates:
        if cache_dir.exists():
            monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(cache_dir))
            break
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setattr(splitshot_config, "APP_DIR", app_dir)
    monkeypatch.setattr(splitshot_config, "SETTINGS_PATH", app_dir / "settings.json")


def _write_wav(path: Path, samples: np.ndarray, sample_rate: int) -> None:
    clipped = np.clip(samples, -1.0, 1.0)
    pcm = (clipped * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


@pytest.fixture()
def synthetic_video_factory(tmp_path):
    def create_video(
        name: str = "sample",
        duration_ms: int = 2000,
        beep_ms: int = 400,
        shot_times_ms: list[int] | None = None,
        resolution: tuple[int, int] = (640, 360),
        audio_stream_offset_ms: int = 0,
    ) -> Path:
        shot_times = shot_times_ms or [800, 1100, 1450]
        sample_rate = 22050
        duration_samples = int(sample_rate * (duration_ms / 1000.0))
        samples = np.zeros(duration_samples, dtype=np.float32)

        beep_start = int(sample_rate * (beep_ms / 1000.0))
        beep_length = int(sample_rate * 0.09)
        beep_time = np.arange(beep_length) / sample_rate
        beep_wave = 0.85 * np.sin(2 * np.pi * 2600 * beep_time) * np.hanning(beep_length)
        samples[beep_start : beep_start + beep_length] += beep_wave.astype(np.float32)

        rng = np.random.default_rng(7)
        for shot_ms in shot_times:
            shot_start = int(sample_rate * (shot_ms / 1000.0))
            shot_length = int(sample_rate * 0.025)
            envelope = np.exp(-np.linspace(0, 8, shot_length))
            burst = rng.normal(0, 1, shot_length).astype(np.float32) * envelope * 0.95
            samples[shot_start : shot_start + shot_length] += burst

        audio_path = tmp_path / f"{name}.wav"
        video_only_path = tmp_path / f"{name}-video-only.mp4"
        video_path = tmp_path / f"{name}.mp4"
        _write_wav(audio_path, samples, sample_rate)
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

        if audio_stream_offset_ms == 0:
            _ffmpeg(
                "-i",
                str(video_only_path),
                "-i",
                str(audio_path),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-shortest",
                str(video_path),
            )
            return video_path

        _ffmpeg(
            "-i",
            str(video_only_path),
            "-itsoffset",
            f"{audio_stream_offset_ms / 1000:.3f}",
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(video_path),
        )
        return video_path

    return create_video
