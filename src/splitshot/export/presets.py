from __future__ import annotations

from dataclasses import dataclass

from splitshot.domain.models import (
    AspectRatio,
    ExportAudioCodec,
    ExportColorSpace,
    ExportFrameRate,
    ExportPreset,
    ExportQuality,
    ExportSettings,
    ExportVideoCodec,
    Project,
)


@dataclass(frozen=True, slots=True)
class ExportPresetDefinition:
    id: str
    name: str
    description: str
    quality: ExportQuality
    aspect_ratio: AspectRatio
    target_width: int | None
    target_height: int | None
    frame_rate: ExportFrameRate
    video_codec: ExportVideoCodec
    video_bitrate_mbps: float
    audio_codec: ExportAudioCodec
    audio_sample_rate: int
    audio_bitrate_kbps: int
    color_space: ExportColorSpace
    two_pass: bool
    ffmpeg_preset: str


EXPORT_PRESETS: dict[str, ExportPresetDefinition] = {
    ExportPreset.SOURCE.value: ExportPresetDefinition(
        id=ExportPreset.SOURCE.value,
        name="Source MP4",
        description="H.264 MP4 using source dimensions and source frame rate.",
        quality=ExportQuality.HIGH,
        aspect_ratio=AspectRatio.ORIGINAL,
        target_width=None,
        target_height=None,
        frame_rate=ExportFrameRate.SOURCE,
        video_codec=ExportVideoCodec.H264,
        video_bitrate_mbps=15.0,
        audio_codec=ExportAudioCodec.AAC,
        audio_sample_rate=48000,
        audio_bitrate_kbps=320,
        color_space=ExportColorSpace.BT709_SDR,
        two_pass=False,
        ffmpeg_preset="medium",
    ),
    ExportPreset.UNIVERSAL_VERTICAL.value: ExportPresetDefinition(
        id=ExportPreset.UNIVERSAL_VERTICAL.value,
        name="Universal Vertical Master",
        description="MP4 H.264 1080x1920 9:16, source frame rate, 20 Mbps, AAC 48 kHz 320 kbps, SDR Rec.709.",
        quality=ExportQuality.HIGH,
        aspect_ratio=AspectRatio.PORTRAIT,
        target_width=1080,
        target_height=1920,
        frame_rate=ExportFrameRate.SOURCE,
        video_codec=ExportVideoCodec.H264,
        video_bitrate_mbps=20.0,
        audio_codec=ExportAudioCodec.AAC,
        audio_sample_rate=48000,
        audio_bitrate_kbps=320,
        color_space=ExportColorSpace.BT709_SDR,
        two_pass=False,
        ffmpeg_preset="slow",
    ),
    ExportPreset.SHORT_FORM_VERTICAL.value: ExportPresetDefinition(
        id=ExportPreset.SHORT_FORM_VERTICAL.value,
        name="Short-Form Vertical",
        description="MP4 H.264 1080x1920 9:16 for Shorts/Reels/TikTok, source frame rate, 15 Mbps.",
        quality=ExportQuality.HIGH,
        aspect_ratio=AspectRatio.PORTRAIT,
        target_width=1080,
        target_height=1920,
        frame_rate=ExportFrameRate.SOURCE,
        video_codec=ExportVideoCodec.H264,
        video_bitrate_mbps=15.0,
        audio_codec=ExportAudioCodec.AAC,
        audio_sample_rate=48000,
        audio_bitrate_kbps=320,
        color_space=ExportColorSpace.BT709_SDR,
        two_pass=False,
        ffmpeg_preset="medium",
    ),
    ExportPreset.YOUTUBE_LONG_1080P.value: ExportPresetDefinition(
        id=ExportPreset.YOUTUBE_LONG_1080P.value,
        name="YouTube Long-Form 1080p",
        description="MP4 H.264 1920x1080 16:9, source frame rate, 15 Mbps for high-frame-rate safety.",
        quality=ExportQuality.HIGH,
        aspect_ratio=AspectRatio.LANDSCAPE,
        target_width=1920,
        target_height=1080,
        frame_rate=ExportFrameRate.SOURCE,
        video_codec=ExportVideoCodec.H264,
        video_bitrate_mbps=15.0,
        audio_codec=ExportAudioCodec.AAC,
        audio_sample_rate=48000,
        audio_bitrate_kbps=320,
        color_space=ExportColorSpace.BT709_SDR,
        two_pass=False,
        ffmpeg_preset="medium",
    ),
    ExportPreset.YOUTUBE_LONG_4K.value: ExportPresetDefinition(
        id=ExportPreset.YOUTUBE_LONG_4K.value,
        name="YouTube Long-Form 4K",
        description="MP4 H.264 3840x2160 16:9, source frame rate, 56 Mbps SDR Rec.709.",
        quality=ExportQuality.HIGH,
        aspect_ratio=AspectRatio.LANDSCAPE,
        target_width=3840,
        target_height=2160,
        frame_rate=ExportFrameRate.SOURCE,
        video_codec=ExportVideoCodec.H264,
        video_bitrate_mbps=56.0,
        audio_codec=ExportAudioCodec.AAC,
        audio_sample_rate=48000,
        audio_bitrate_kbps=320,
        color_space=ExportColorSpace.BT709_SDR,
        two_pass=False,
        ffmpeg_preset="slow",
    ),
}


def export_presets_for_api() -> list[dict[str, object]]:
    return [
        {
            "id": preset.id,
            "name": preset.name,
            "description": preset.description,
            "quality": preset.quality.value,
            "aspect_ratio": preset.aspect_ratio.value,
            "target_width": preset.target_width,
            "target_height": preset.target_height,
            "frame_rate": preset.frame_rate.value,
            "video_codec": preset.video_codec.value,
            "video_bitrate_mbps": preset.video_bitrate_mbps,
            "audio_codec": preset.audio_codec.value,
            "audio_sample_rate": preset.audio_sample_rate,
            "audio_bitrate_kbps": preset.audio_bitrate_kbps,
            "color_space": preset.color_space.value,
            "two_pass": preset.two_pass,
            "ffmpeg_preset": preset.ffmpeg_preset,
        }
        for preset in EXPORT_PRESETS.values()
    ]


def get_export_preset(preset_id: str) -> ExportPresetDefinition:
    return EXPORT_PRESETS.get(preset_id, EXPORT_PRESETS[ExportPreset.SOURCE.value])


def apply_export_preset(project: Project, preset_id: str) -> None:
    preset = get_export_preset(preset_id)
    project.export.preset = ExportPreset(preset.id)
    project.export.quality = preset.quality
    project.export.aspect_ratio = preset.aspect_ratio
    project.export.target_width = preset.target_width
    project.export.target_height = preset.target_height
    project.export.frame_rate = preset.frame_rate
    project.export.video_codec = preset.video_codec
    project.export.video_bitrate_mbps = preset.video_bitrate_mbps
    project.export.audio_codec = preset.audio_codec
    project.export.audio_sample_rate = preset.audio_sample_rate
    project.export.audio_bitrate_kbps = preset.audio_bitrate_kbps
    project.export.color_space = preset.color_space
    project.export.two_pass = preset.two_pass
    project.export.ffmpeg_preset = preset.ffmpeg_preset
    project.touch()


def export_settings_summary(settings: ExportSettings) -> dict[str, object]:
    return {
        "preset": settings.preset.value,
        "quality": settings.quality.value,
        "aspect_ratio": settings.aspect_ratio.value,
        "target_width": settings.target_width,
        "target_height": settings.target_height,
        "frame_rate": settings.frame_rate.value,
        "video_codec": settings.video_codec.value,
        "video_bitrate_mbps": settings.video_bitrate_mbps,
        "audio_codec": settings.audio_codec.value,
        "audio_sample_rate": settings.audio_sample_rate,
        "audio_bitrate_kbps": settings.audio_bitrate_kbps,
        "color_space": settings.color_space.value,
        "two_pass": settings.two_pass,
        "ffmpeg_preset": settings.ffmpeg_preset,
        "last_log": settings.last_log,
        "last_error": settings.last_error,
    }
