from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

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


_EXPORT_SETTINGS_PAYLOAD_FIELDS = (
    "preset",
    "quality",
    "aspect_ratio",
    "crop_center_x",
    "crop_center_y",
    "output_path",
    "target_width",
    "target_height",
    "frame_rate",
    "video_codec",
    "video_bitrate_mbps",
    "audio_codec",
    "audio_sample_rate",
    "audio_bitrate_kbps",
    "color_space",
    "two_pass",
    "ffmpeg_preset",
)

_EXPORT_SETTINGS_MANUAL_OVERRIDE_FIELDS = frozenset(
    {
        "quality",
        "aspect_ratio",
        "crop_center_x",
        "crop_center_y",
        "target_width",
        "target_height",
        "frame_rate",
        "video_codec",
        "video_bitrate_mbps",
        "audio_codec",
        "audio_sample_rate",
        "audio_bitrate_kbps",
        "color_space",
        "two_pass",
        "ffmpeg_preset",
    }
)

EXPORT_SETTINGS_SYNC_COMPARISON_FIELDS = frozenset(
    {
        "quality",
        "aspect_ratio",
        "target_width",
        "target_height",
        "frame_rate",
        "video_codec",
        "video_bitrate_mbps",
        "audio_codec",
        "audio_sample_rate",
        "audio_bitrate_kbps",
        "color_space",
        "two_pass",
        "ffmpeg_preset",
    }
)


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


def _enum_raw_value(value: object) -> object:
    return value.value if hasattr(value, "value") else value


def apply_export_preset_to_settings(settings: ExportSettings, preset_id: str) -> None:
    normalized_preset_id = str(_enum_raw_value(preset_id) or "").strip().lower()
    if normalized_preset_id == ExportPreset.CUSTOM.value:
        settings.preset = ExportPreset.CUSTOM
        return

    preset = get_export_preset(normalized_preset_id)
    settings.preset = ExportPreset(preset.id)
    settings.quality = preset.quality
    settings.aspect_ratio = preset.aspect_ratio
    settings.target_width = preset.target_width
    settings.target_height = preset.target_height
    settings.frame_rate = preset.frame_rate
    settings.video_codec = preset.video_codec
    settings.video_bitrate_mbps = preset.video_bitrate_mbps
    settings.audio_codec = preset.audio_codec
    settings.audio_sample_rate = preset.audio_sample_rate
    settings.audio_bitrate_kbps = preset.audio_bitrate_kbps
    settings.color_space = preset.color_space
    settings.two_pass = preset.two_pass
    settings.ffmpeg_preset = preset.ffmpeg_preset


def apply_export_preset(project: Project, preset_id: str) -> None:
    apply_export_preset_to_settings(project.export, preset_id)
    project.touch()


def normalize_export_settings_payload(payload: Mapping[str, object] | None) -> dict[str, object]:
    if not isinstance(payload, Mapping):
        return {}

    normalized: dict[str, object] = {}
    for key in _EXPORT_SETTINGS_PAYLOAD_FIELDS:
        if key not in payload:
            continue
        value = _enum_raw_value(payload[key])
        if key == "preset":
            normalized_preset = str(value or "").strip().lower()
            if normalized_preset:
                normalized[key] = normalized_preset
        elif key == "quality":
            normalized[key] = ExportQuality(str(value))
        elif key == "aspect_ratio":
            normalized[key] = AspectRatio(str(value))
        elif key in {"crop_center_x", "crop_center_y"}:
            normalized[key] = float(value)
        elif key in {"target_width", "target_height"}:
            normalized[key] = None if value in {"", None} else max(2, int(value))
        elif key == "frame_rate":
            normalized[key] = ExportFrameRate(str(value))
        elif key == "video_codec":
            normalized[key] = ExportVideoCodec(str(value))
        elif key == "video_bitrate_mbps":
            normalized[key] = max(0.1, float(value))
        elif key == "audio_codec":
            normalized[key] = ExportAudioCodec(str(value))
        elif key == "audio_sample_rate":
            normalized[key] = max(8000, int(value))
        elif key == "audio_bitrate_kbps":
            normalized[key] = max(32, int(value))
        elif key == "color_space":
            normalized[key] = ExportColorSpace(str(value))
        elif key == "two_pass":
            normalized[key] = bool(value)
        elif key == "ffmpeg_preset":
            normalized[key] = str(value)
        elif key == "output_path":
            next_output_path = str(value or "").strip()
            normalized[key] = None if not next_output_path else next_output_path
    return normalized


def apply_export_settings_payload(
    settings: ExportSettings,
    payload: Mapping[str, object] | None,
) -> dict[str, object]:
    normalized = normalize_export_settings_payload(payload)

    if "quality" in normalized:
        settings.quality = normalized["quality"]
    if "aspect_ratio" in normalized:
        settings.aspect_ratio = normalized["aspect_ratio"]
    if "crop_center_x" in normalized:
        settings.crop_center_x = normalized["crop_center_x"]
    if "crop_center_y" in normalized:
        settings.crop_center_y = normalized["crop_center_y"]
    if "target_width" in normalized:
        settings.target_width = normalized["target_width"]
    if "target_height" in normalized:
        settings.target_height = normalized["target_height"]
    if "frame_rate" in normalized:
        settings.frame_rate = normalized["frame_rate"]
    if "video_codec" in normalized:
        settings.video_codec = normalized["video_codec"]
    if "video_bitrate_mbps" in normalized:
        settings.video_bitrate_mbps = normalized["video_bitrate_mbps"]
    if "audio_codec" in normalized:
        settings.audio_codec = normalized["audio_codec"]
    if "audio_sample_rate" in normalized:
        settings.audio_sample_rate = normalized["audio_sample_rate"]
    if "audio_bitrate_kbps" in normalized:
        settings.audio_bitrate_kbps = normalized["audio_bitrate_kbps"]
    if "color_space" in normalized:
        settings.color_space = normalized["color_space"]
    if "two_pass" in normalized:
        settings.two_pass = normalized["two_pass"]
    if "ffmpeg_preset" in normalized:
        settings.ffmpeg_preset = normalized["ffmpeg_preset"]
    if "output_path" in normalized:
        settings.output_path = normalized["output_path"]

    if _EXPORT_SETTINGS_MANUAL_OVERRIDE_FIELDS.intersection(normalized):
        settings.preset = ExportPreset.CUSTOM

    return normalized


def export_settings_payload_matches(
    settings: ExportSettings,
    payload: Mapping[str, object] | None,
    *,
    comparison_fields: frozenset[str] | set[str] | None = None,
) -> bool:
    normalized = normalize_export_settings_payload(payload)
    if comparison_fields is None:
        comparable_keys = {key for key in normalized if key not in {"preset", "output_path"}}
    else:
        comparable_keys = set(comparison_fields)

    for key in comparable_keys:
        if key not in normalized:
            continue
        if normalized[key] != getattr(settings, key):
            return False
    return True


def synchronize_export_settings_payload(
    settings: ExportSettings,
    payload: Mapping[str, object] | None,
    *,
    comparison_fields: frozenset[str] | set[str] | None = None,
) -> dict[str, object]:
    normalized = normalize_export_settings_payload(payload)
    selected_preset = str(normalized.get("preset") or settings.preset.value)
    if selected_preset == ExportPreset.CUSTOM.value:
        settings.preset = ExportPreset.CUSTOM
    else:
        apply_export_preset_to_settings(settings, selected_preset)

    if selected_preset == ExportPreset.CUSTOM.value or not export_settings_payload_matches(
        settings,
        normalized,
        comparison_fields=comparison_fields,
    ):
        apply_export_settings_payload(settings, normalized)
    return normalized


def resolved_export_settings(
    settings: ExportSettings,
    payload: Mapping[str, object] | None,
    *,
    synchronize_preset: bool = False,
    comparison_fields: frozenset[str] | set[str] | None = None,
) -> ExportSettings:
    resolved = replace(settings)
    if synchronize_preset:
        synchronize_export_settings_payload(
            resolved,
            payload,
            comparison_fields=comparison_fields,
        )
    else:
        apply_export_settings_payload(resolved, payload)
    return resolved


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
