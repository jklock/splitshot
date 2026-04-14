# Media

The media package locates FFmpeg binaries, probes video files, and extracts audio or thumbnails for review and export.

## Files

- [ffmpeg.py](ffmpeg.py) resolves `ffmpeg` and `ffprobe`, runs subprocesses, and raises `MediaError` on failure.
- [probe.py](probe.py) turns a path into a `VideoAsset` and detects still-image inputs before treating them as video.
- [audio.py](audio.py) extracts mono WAV audio, reads PCM samples, and builds the normalized waveform envelope.
- [thumbnails.py](thumbnails.py) renders preview thumbnails.

## Binary Resolution

`resolve_media_binary` checks these locations in order:

1. `SPLITSHOT_FFMPEG_DIR`
2. Bundled resources in packaged builds
3. The current `PATH`

If none of those locations contains the requested tool, the module raises `MediaError`.

## Probe and Audio Details

- `probe_video` first tries `QImage` so still images can be handled directly.
- If the file is not a still image, the module uses `ffprobe` to gather duration, frame rate, sample rate, and rotation metadata.
- `extract_audio_wav` writes a mono PCM WAV file that the analysis pipeline can consume.
- `waveform_envelope` compresses the full waveform into a normalized envelope for UI rendering.

## Consumer Notes

- `ui.controller.ProjectController` uses `probe_video` when the user imports a primary or merge media path.
- `export.pipeline` uses `ffmpeg_command` and `run_ffmpeg` to build and encode the final video.

**Last updated:** 2026-04-13
**Referenced files last updated:** 2026-04-13
