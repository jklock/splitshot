# Media

This package owns FFmpeg resolution, media probing, waveform/audio extraction, and thumbnail generation.

## Purpose

Use it when the change touches media metadata, audio extraction, still-image handling, FFmpeg discovery, or thumbnail behavior.

## Read This First

- [ffmpeg.py](ffmpeg.py)
- [probe.py](probe.py)
- [audio.py](audio.py)

## Main Files

- [ffmpeg.py](ffmpeg.py): binary resolution, FFmpeg subprocess helpers, media errors
- [probe.py](probe.py): `VideoAsset` creation and still-image detection
- [audio.py](audio.py): WAV extraction, sample loading, waveform envelope generation
- [thumbnails.py](thumbnails.py): thumbnail rendering

## Runtime Flow

1. Resolve `ffmpeg` and `ffprobe`.
2. Probe media metadata and detect still images.
3. Extract audio and derive waveform data when analysis needs it.
4. Provide media helpers to controller, analysis, and export layers.

## Key Extension Points

- `resolve_media_binary`
- `probe_video`
- `extract_audio_wav`
- `waveform_envelope`

## Related Tests

- [../../../tests/media/](../../../tests/media/)
- [../../../tests/export/](../../../tests/export/)

## Related Docs

- [../../../docs/project/DEVELOPING.md](../../../docs/project/DEVELOPING.md)
- [../analysis/README.md](../analysis/README.md)
- [../export/README.md](../export/README.md)
