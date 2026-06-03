from __future__ import annotations

import sys
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter

from splitshot.domain.models import (
    BadgeSize,
    BadgeStyle,
    OverlayPosition,
    Project,
    overlay_text_boxes_for_render,
)
from splitshot.overlay.font_policy import (
    WINDOWS_MONO_FONT_FAMILIES,
    WINDOWS_SANS_FONT_FAMILIES,
    WINDOWS_SERIF_FONT_FAMILIES,
    WINDOWS_UI_FONT_FAMILY,
    default_overlay_font_family,
    is_windows_platform,
    resolve_overlay_font_family,
)
from splitshot.presentation.popups import (
    popup_bubble_content_type,
    popup_bubble_display_text,
    popup_bubble_image_path,
    popup_bubble_image_scale_mode,
    popup_bubble_is_visible_at,
    popup_bubble_point,
)
from splitshot.scoring.logic import (
    calculate_scoring_summary,
    current_shot_index,
    format_imported_stage_overlay_text,
    shot_display_time_ms,
)
from splitshot.timeline.model import compute_split_rows, draw_time_ms, raw_time_ms, sort_shots


@dataclass(slots=True)
class Badge:
    text: str
    style: BadgeStyle
    text_color: str | None = None
    background_color: str | None = None
    width: int | None = None
    height: int | None = None
    text_runs: tuple[tuple[str, str | None], ...] | None = None
    text_bias: str = "center"
    image_path: str = ""
    image_scale_mode: str = "contain"
    image_scale_percent: int | None = None
    content_opacity: float | None = None
    show_background: bool = True
    font_family: str | None = None
    font_size: int | None = None
    font_bold: bool | None = None
    font_italic: bool | None = None
    use_individual_auto_size: bool = False


_FONT_SIZE = {
    BadgeSize.XS: 10,
    BadgeSize.S: 12,
    BadgeSize.M: 14,
    BadgeSize.L: 16,
    BadgeSize.XL: 20,
    BadgeSize.CUSTOM: 14,
}

_BADGE_PADDING_X_PX = 10
_BADGE_PADDING_Y_PX = 5
_FIRST_SCORE_TOKEN_GAP = "  "

_PENALTY_LABELS = {
    "procedural_errors": "PE",
    "manual_no_shoots": "NS",
    "manual_misses": "M",
    "non_threats": "NT",
    "flagrant_penalties": "FP",
    "failures_to_do_right": "FTDR",
    "finger_pe": "FPE",
    "steel_misses": "PM",
    "stop_plate_failures": "SPF",
    "steel_not_down": "SND",
}

_ABOVE_FINAL_TEXT_BOX_QUADRANT = "above_final"

_LEAD_IN_CARD_STYLE_DEFAULTS = {
    "stage_info": {
        "show_match": True,
        "show_stage": True,
        "show_shooter": False,
        "show_division": True,
        "show_classification": False,
        "show_date": False,
    },
    "competitor": {
        "show_match": False,
        "show_stage": True,
        "show_shooter": True,
        "show_division": True,
        "show_classification": True,
        "show_date": False,
    },
}


def _ordered_unique_families(*families: str) -> list[str]:
    ordered: list[str] = []
    for family in families:
        normalized = str(family or "").strip()
        if normalized and normalized not in ordered:
            ordered.append(normalized)
    return ordered


def _overlay_font_catalog() -> tuple[dict[str, list[str]], QFont.StyleHint]:
    if is_windows_platform():
        return (
            {
                WINDOWS_UI_FONT_FAMILY: list(WINDOWS_SANS_FONT_FAMILIES),
                "Helvetica Neue": list(WINDOWS_SANS_FONT_FAMILIES),
                "Arial": _ordered_unique_families("Arial", *WINDOWS_SANS_FONT_FAMILIES),
                "Verdana": _ordered_unique_families("Verdana", *WINDOWS_SANS_FONT_FAMILIES),
                "Tahoma": _ordered_unique_families("Tahoma", *WINDOWS_SANS_FONT_FAMILIES),
                "Trebuchet MS": _ordered_unique_families(
                    "Trebuchet MS", *WINDOWS_SANS_FONT_FAMILIES
                ),
                "Courier New": list(WINDOWS_MONO_FONT_FAMILIES),
                "Consolas": list(WINDOWS_MONO_FONT_FAMILIES),
                "Georgia": list(WINDOWS_SERIF_FONT_FAMILIES),
                "Cambria": list(WINDOWS_SERIF_FONT_FAMILIES),
            },
            QFont.StyleHint.AnyStyle,
        )
    if sys.platform == "darwin":
        return (
            {
                "Helvetica Neue": ["Helvetica Neue", "Helvetica", "Arial"],
                "Arial": ["Arial", "Helvetica Neue", "Helvetica"],
                "Verdana": ["Verdana", "Arial", "Helvetica Neue"],
                "Courier New": ["Menlo", "Courier New", "Monaco"],
                "Georgia": ["Georgia", "Times New Roman", "Times"],
            },
            QFont.StyleHint.AnyStyle,
        )
    return (
        {
            "Helvetica Neue": ["DejaVu Sans", "Liberation Sans", "Arial", "Noto Sans"],
            "Arial": ["Arial", "DejaVu Sans", "Liberation Sans", "Noto Sans"],
            "Verdana": ["Verdana", "DejaVu Sans", "Liberation Sans", "Arial"],
            "Courier New": ["DejaVu Sans Mono", "Liberation Mono", "Courier New", "Noto Sans Mono"],
            "Georgia": [
                "DejaVu Serif",
                "Liberation Serif",
                "Georgia",
                "Times New Roman",
                "Noto Serif",
            ],
        },
        QFont.StyleHint.AnyStyle,
    )


def _overlay_qfont(font_family: str, font_size: int, bold: bool, italic: bool) -> QFont:
    primary_family = resolve_overlay_font_family(font_family, sys.platform)
    catalog, default_style_hint = _overlay_font_catalog()
    families = catalog.get(primary_family, [primary_family])
    if primary_family not in catalog:
        families = [primary_family, *families]
    font = QFont(families[0])
    if hasattr(font, "setFamilies"):
        font.setFamilies(families)
    if primary_family in {"Courier New", "Consolas"}:
        font.setStyleHint(QFont.StyleHint.Monospace)
    elif primary_family in {"Georgia", "Cambria"}:
        font.setStyleHint(QFont.StyleHint.Serif)
    else:
        font.setStyleHint(
            QFont.StyleHint.SansSerif
            if is_windows_platform()
            else (default_style_hint or QFont.StyleHint.SansSerif)
        )
    font.setPixelSize(max(1, int(font_size)))
    font.setBold(bold)
    font.setItalic(italic)
    return font


def _combined_rect(rects: list[QRectF]) -> QRectF | None:
    if not rects:
        return None
    left = min(rect.left() for rect in rects)
    top = min(rect.top() for rect in rects)
    right = max(rect.right() for rect in rects)
    bottom = max(rect.bottom() for rect in rects)
    return QRectF(left, top, max(0.0, right - left), max(0.0, bottom - top))


def _terminal_stack_rect(rects: list[QRectF], direction: str) -> QRectF | None:
    if not rects:
        return None
    if direction == "left":
        return min(rects, key=lambda rect: rect.left())
    if direction == "up":
        return min(rects, key=lambda rect: rect.top())
    if direction == "down":
        return max(rects, key=lambda rect: rect.bottom())
    return max(rects, key=lambda rect: rect.right())


def _score_token_color(project: Project, token: str) -> str | None:
    normalized_token = str(token).strip()
    if not normalized_token:
        return None
    return project.overlay.scoring_colors.get(normalized_token)


def _metric_caption_overlay_config(project: Project) -> dict:
    config = getattr(project, "_metric_caption_overlay", None)
    return config if isinstance(config, dict) else {}


def _metric_caption_show_split_times(project: Project) -> bool:
    config = _metric_caption_overlay_config(project)
    if not config:
        return True
    return bool(config.get("show_split_times"))


def _metric_caption_show_shot_scores(project: Project) -> bool:
    config = _metric_caption_overlay_config(project)
    if not config:
        return True
    return bool(config.get("show_shot_scores"))


def _shot_badge_base_text(shot_number: int, split_text: str, interval_label: str | None) -> str:
    normalized_split = str(split_text or "").strip()
    normalized_label = str(interval_label or "").strip()
    parts = [f"Shot {shot_number}"]
    if normalized_label and normalized_label != "Split":
        parts.append(normalized_label)
    if normalized_split:
        parts.append(normalized_split)
    return " ".join(parts)


def _shot_score_badge_content(
    project: Project, shot: object, base_text: str
) -> tuple[str, tuple[tuple[str, str | None], ...] | None]:
    score = getattr(shot, "score", None)
    if (
        not project.scoring.enabled
        or score is None
        or not _metric_caption_show_shot_scores(project)
    ):
        return base_text, None

    text_parts: list[tuple[str, str | None]] = [
        (base_text, None),
        (_FIRST_SCORE_TOKEN_GAP, None),
        (score.letter.value, _score_token_color(project, score.letter.value)),
    ]
    plain_text = f"{base_text}{_FIRST_SCORE_TOKEN_GAP}{score.letter.value}"
    for field_id, value in score.penalty_counts.items():
        numeric = max(0.0, float(value))
        if numeric <= 0:
            continue
        label = _PENALTY_LABELS.get(field_id, field_id.replace("_", " "))
        count_text = f" x{_format_penalty_count(numeric)}"
        plain_text = f"{plain_text} {label}{count_text}"
        text_parts.extend(
            [
                (" ", None),
                (label, _score_token_color(project, label)),
                (count_text, None),
            ]
        )
    return plain_text, tuple(text_parts)


def _format_split_seconds(value_ms: int) -> str:
    return f"{value_ms / 1000.0:.2f}s"


def _format_elapsed_seconds(value_ms: int | None) -> str:
    if value_ms is None:
        return "--.--"
    return f"{value_ms / 1000.0:.2f}"


def _format_penalty_count(value: float) -> str:
    numeric = float(value)
    return str(int(numeric)) if numeric.is_integer() else f"{numeric:.1f}"


def _format_penalty_counts(penalty_counts: dict[str, float]) -> str:
    parts: list[str] = []
    for field_id, value in penalty_counts.items():
        numeric = float(value)
        if numeric <= 0:
            continue
        label = _PENALTY_LABELS.get(field_id, field_id.replace("_", " "))
        parts.append(f"{label} x{_format_penalty_count(numeric)}")
    return ", ".join(parts)


def _text_bias_for_direction(direction: str | None) -> str:
    if direction == "left":
        return "right"
    if direction == "right":
        return "left"
    return "center"


def _hook_duration_ms(payload: dict | None, fallback_seconds: float = 0.0) -> int:
    if not isinstance(payload, dict):
        return 0
    try:
        duration_s = float(payload.get("duration_s", fallback_seconds) or fallback_seconds)
    except (TypeError, ValueError):
        duration_s = fallback_seconds
    return max(0, int(round(duration_s * 1000)))


def _stage_title_line(project: Project) -> str:
    imported = project.scoring.imported_stage
    title = str(project.name or "").strip()
    if title:
        return title
    if imported is not None and str(imported.stage_name or "").strip():
        return str(imported.stage_name).strip()
    if imported is not None and imported.stage_number is not None:
        return f"Stage {imported.stage_number}"
    if project.scoring.stage_number is not None:
        return f"Stage {project.scoring.stage_number}"
    return "SplitShot"


def _stage_subtitle_line(project: Project) -> str:
    imported = project.scoring.imported_stage
    parts: list[str] = []
    if imported is not None:
        stage_name = str(imported.stage_name or "").strip()
        if stage_name and stage_name != _stage_title_line(project):
            parts.append(stage_name)
        elif imported.stage_number is not None:
            parts.append(f"Stage {imported.stage_number}")
        if imported.division:
            parts.append(str(imported.division).strip())
        if imported.match_type:
            parts.append(str(imported.match_type).strip().upper())
    elif project.description.strip():
        parts.append(project.description.strip())
    return " • ".join(part for part in parts if part)


def _hook_bool(payload: dict | None, key: str, default: bool = False) -> bool:
    if not isinstance(payload, dict):
        return default
    value = payload.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


def _lead_in_card_field_enabled(card: dict | None, key: str, style: str) -> bool:
    default = bool(_LEAD_IN_CARD_STYLE_DEFAULTS.get(style, {}).get(key, False))
    return _hook_bool(card, key, default)


def _lead_in_card_match_value(project: Project) -> str:
    imported = project.scoring.imported_stage
    candidate = ""
    if imported is not None:
        candidate = str(imported.match_type or "").strip()
    if not candidate:
        candidate = str(project.scoring.match_type or "").strip()
    return candidate.upper() if candidate else ""


def _lead_in_card_shooter_value(project: Project) -> str:
    imported = project.scoring.imported_stage
    if imported is not None:
        candidate = str(imported.competitor_name or "").strip()
        if candidate:
            return candidate
    return str(project.scoring.competitor_name or "").strip()


def _lead_in_card_division_value(project: Project) -> str:
    imported = project.scoring.imported_stage
    return str(imported.division or "").strip() if imported is not None else ""


def _lead_in_card_classification_value(project: Project) -> str:
    imported = project.scoring.imported_stage
    return str(imported.classification or "").strip() if imported is not None else ""


def _lead_in_card_date_value(project: Project) -> str:
    created_at = getattr(project, "created_at", None)
    if created_at is None:
        return ""
    try:
        return created_at.date().isoformat()
    except AttributeError:
        return ""


def _lead_in_card_stage_subtitle_value(project: Project, title: str) -> str:
    imported = project.scoring.imported_stage
    if imported is not None:
        stage_name = str(imported.stage_name or "").strip()
        if stage_name and stage_name != title:
            return stage_name
        if imported.stage_number is not None:
            stage_number = f"Stage {imported.stage_number}"
            if stage_number != title:
                return stage_number
    candidate = _stage_title_line(project)
    return "" if candidate == title else candidate


def _append_unique_part(parts: list[str], value: str, *, title: str = "") -> None:
    normalized = str(value or "").strip()
    if not normalized:
        return
    if title and normalized == title:
        return
    if normalized in parts:
        return
    parts.append(normalized)


def _lead_in_card_text(project: Project, card: dict | None) -> str:
    if not isinstance(card, dict):
        return ""
    style = str(card.get("style", "") or "").strip().lower()
    if style in {"", "none"}:
        return ""

    title_override = str(card.get("custom_title") or card.get("title") or "").strip()
    subtitle_override = str(card.get("custom_subtitle") or card.get("subtitle") or "").strip()
    field_values = {
        "match": _lead_in_card_match_value(project),
        "stage": _stage_title_line(project),
        "shooter": _lead_in_card_shooter_value(project),
        "division": _lead_in_card_division_value(project),
        "classification": _lead_in_card_classification_value(project),
        "date": _lead_in_card_date_value(project),
    }
    enabled_fields = {
        field_name
        for field_name in field_values
        if _lead_in_card_field_enabled(card, f"show_{field_name}", style)
    }

    title = title_override
    if not title:
        preferred_order = (
            ("shooter", "stage", "match")
            if style == "competitor"
            else ("stage", "shooter", "match")
        )
        for field_name in preferred_order:
            candidate = field_values.get(field_name, "")
            if field_name in enabled_fields and candidate:
                title = candidate
                break
    if not title:
        title = field_values.get("stage") or "SplitShot"

    subtitle_parts: list[str] = []
    _append_unique_part(subtitle_parts, subtitle_override, title=title)
    for field_name in ("match", "stage", "shooter", "division", "classification", "date"):
        if field_name not in enabled_fields:
            continue
        candidate = (
            _lead_in_card_stage_subtitle_value(project, title)
            if field_name == "stage"
            else field_values.get(field_name, "")
        )
        _append_unique_part(subtitle_parts, candidate, title=title)

    has_explicit_composition = any(
        key in card
        for key in (
            "show_match",
            "show_stage",
            "show_shooter",
            "show_division",
            "show_classification",
            "show_date",
            "custom_title",
            "custom_subtitle",
            "title",
            "subtitle",
        )
    )
    subtitle = (
        " • ".join(subtitle_parts)
        if subtitle_parts
        else ("" if has_explicit_composition else _stage_subtitle_line(project))
    )
    return title if not subtitle else f"{title}\n{subtitle}"


def _clamped_float(
    value: object,
    default: float,
    *,
    minimum: float = 0.0,
    maximum: float = 1.0,
) -> float:
    try:
        return max(minimum, min(maximum, float(value)))
    except (TypeError, ValueError):
        return default


def _clamped_int(
    value: object,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    try:
        return max(minimum, min(maximum, int(round(float(value)))))
    except (TypeError, ValueError):
        return default


def _lead_in_card_animation(card: dict | None) -> str:
    if not isinstance(card, dict):
        return "static"
    animation = str(card.get("animation") or "static").strip().lower()
    return animation if animation in {"static", "fade", "slide_up"} else "static"


def _lead_in_card_logo_path(card: dict | None) -> str:
    if not isinstance(card, dict):
        return ""
    return str(card.get("logo_path") or "").strip()


def _lead_in_card_logo_scale_percent(card: dict | None) -> int:
    if not isinstance(card, dict):
        return 100
    return _clamped_int(card.get("logo_scale_percent", 100), 100, minimum=20, maximum=400)


def _lead_in_card_animation_state(
    card: dict | None,
    position_ms: int,
    duration_ms: int,
) -> tuple[float, float]:
    animation = _lead_in_card_animation(card)
    if animation == "static" or duration_ms <= 0:
        return 1.0, 0.18

    edge_ms = max(180, min(650, int(duration_ms * 0.25)))
    fade_in = _clamped_float(position_ms / max(1, edge_ms), 0.0)
    fade_out = _clamped_float((duration_ms - position_ms) / max(1, edge_ms), 0.0)
    opacity = min(fade_in, fade_out)
    if animation == "fade":
        return opacity, 0.18
    return opacity, 0.18 + ((1.0 - fade_in) * 0.06) - ((1.0 - fade_out) * 0.02)


def _brand_mark_text(brand: dict | None) -> str:
    if not isinstance(brand, dict):
        return ""
    style = str(brand.get("style", "") or "").strip().lower()
    if style in {"", "none"}:
        return ""
    text = str(brand.get("text", "") or "").strip()
    if style == "splitshot":
        return text or "SplitShot"
    if style == "image":
        return text
    return text or style.replace("_", " ").title()


def _brand_mark_image_path(brand: dict | None) -> str:
    if not isinstance(brand, dict):
        return ""
    return str(brand.get("image_path") or "").strip()


def _brand_mark_image_scale_percent(brand: dict | None) -> int:
    if not isinstance(brand, dict):
        return 100
    return _clamped_int(brand.get("image_scale_percent", 100), 100, minimum=20, maximum=400)


def _brand_mark_text_color(brand: dict | None) -> str:
    if not isinstance(brand, dict):
        return "#ffffff"
    color = str(brand.get("text_color") or "").strip()
    return color or "#ffffff"


def _brand_mark_font_size(brand: dict | None) -> int | None:
    if not isinstance(brand, dict):
        return None
    raw_value = brand.get("font_size")
    if raw_value in (None, "", 0):
        return None
    return _clamped_int(raw_value, 14, minimum=8, maximum=96)


def _brand_mark_font_family(brand: dict | None) -> str | None:
    if not isinstance(brand, dict):
        return None
    value = str(brand.get("font_family") or "").strip()
    return value or None


def _brand_mark_point(brand: dict | None) -> tuple[float, float]:
    position = str((brand or {}).get("position", "top_right") or "top_right").strip().lower()
    return {
        "top_left": (0.13, 0.1),
        "top_right": (0.87, 0.1),
        "bottom_left": (0.13, 0.9),
        "bottom_right": (0.87, 0.9),
        "center": (0.5, 0.5),
    }.get(position, (0.87, 0.1))


def _brand_mark_opacity(brand: dict | None) -> float:
    if not isinstance(brand, dict):
        return 0.72
    try:
        return max(0.0, min(1.0, float(brand.get("opacity", 0.72))))
    except (TypeError, ValueError):
        return 0.72


def _standard_badge_texts(project: Project) -> tuple[str, ...]:
    texts: list[str] = []
    shots = sort_shots(project.analysis.shots)
    split_row_by_shot_id = {
        row.shot_id: row for row in compute_split_rows(project) if row.shot_id is not None
    }

    if project.overlay.show_timer:
        texts.append(f"Timer {_format_elapsed_seconds(raw_time_ms(project))}")

    draw_value = draw_time_ms(project)
    if project.overlay.show_draw and draw_value is not None:
        texts.append(f"Draw {_format_elapsed_seconds(draw_value)}")

    if project.overlay.show_shots:
        for index, shot in enumerate(shots, start=1):
            split_row = split_row_by_shot_id.get(shot.id)
            split_ms = None if split_row is None else split_row.split_ms
            split_text = (
                _format_split_seconds(max(0, split_ms or 0))
                if _metric_caption_show_split_times(project)
                else ""
            )
            base_text = _shot_badge_base_text(
                index,
                split_text,
                None if split_row is None else split_row.interval_label,
            )
            score_text, _score_runs = _shot_score_badge_content(project, shot, base_text)
            texts.append(score_text)

    if project.overlay.show_score and project.scoring.enabled:
        summary = calculate_scoring_summary(project)
        if summary["display_value"] != "--":
            texts.append(f"{summary['display_label']} {summary['display_value']}")

    return tuple(texts)


def _auto_badge_size(
    texts: tuple[str, ...], metrics, line_height: int | None = None
) -> tuple[int, int] | None:
    if not texts:
        return None
    text_width = 0
    text_height = 0
    resolved_line_height = max(1, int(line_height or metrics.height()))
    for text in texts:
        lines = str(text or "").splitlines() or [""]
        text_width = max(text_width, max(metrics.horizontalAdvance(line or " ") for line in lines))
        text_height = max(text_height, resolved_line_height * max(1, len(lines)))
    if text_width <= 0 or text_height <= 0:
        return None
    return (
        text_width + (_BADGE_PADDING_X_PX * 2),
        text_height + (_BADGE_PADDING_Y_PX * 2),
    )


def _badge_line_height(font: QFont, metrics) -> int:
    pixel_size = font.pixelSize()
    if pixel_size > 0:
        return max(1, int(pixel_size))
    return max(1, int(metrics.height()))


class OverlayRenderer:
    def build_badges(
        self,
        project: Project,
        position_ms: int,
    ) -> tuple[list[Badge], list[tuple[str, float, float, float]]]:
        badges, positioned_badges, score_marks = self._build_badges_with_positions(
            project, position_ms
        )
        return badges + [badge for badge, _x, _y in positioned_badges], score_marks

    def _build_badges_with_positions(
        self,
        project: Project,
        position_ms: int,
    ) -> tuple[
        list[Badge], list[tuple[Badge, float, float]], list[tuple[str, float, float, float]]
    ]:
        lead_in_text = _lead_in_card_text(project, project._lead_in_card)
        lead_in_logo_path = _lead_in_card_logo_path(project._lead_in_card)
        lead_in_duration_ms = _hook_duration_ms(project._lead_in_card, 0.0)
        lead_in_visible = (
            bool(lead_in_text or lead_in_logo_path)
            and lead_in_duration_ms > 0
            and position_ms < lead_in_duration_ms
        )
        brand_text = _brand_mark_text(project._brand_mark)
        brand_image_path = _brand_mark_image_path(project._brand_mark)
        brand_duration_ms = _hook_duration_ms(project._brand_mark, 0.0)
        brand_visible = bool(brand_text or brand_image_path) and (
            brand_duration_ms <= 0 or position_ms < brand_duration_ms
        )
        if (
            project.overlay.position == OverlayPosition.NONE
            and not lead_in_visible
            and not brand_visible
        ):
            return [], [], []
        shots = sort_shots(project.analysis.shots)
        current_index = current_shot_index(project, position_ms)
        badges: list[Badge] = []
        positioned_badges: list[tuple[Badge, float, float]] = []
        split_rows = compute_split_rows(project)
        split_row_by_shot_id = {row.shot_id: row for row in split_rows if row.shot_id is not None}

        def append_badge(badge: Badge, x: float | None = None, y: float | None = None) -> None:
            if x is not None and y is not None:
                positioned_badges.append((badge, x, y))
                return
            badges.append(badge)

        beep_time = project.analysis.beep_time_ms_primary
        elapsed = max(0, position_ms - beep_time) if beep_time is not None else position_ms
        if beep_time is not None and shots:
            elapsed = min(elapsed, max(0, shots[-1].time_ms - beep_time))
        if project.overlay.show_timer:
            append_badge(
                Badge(f"Timer {_format_elapsed_seconds(elapsed)}", project.overlay.timer_badge),
                None if project.overlay.timer_lock_to_stack else project.overlay.timer_x,
                None if project.overlay.timer_lock_to_stack else project.overlay.timer_y,
            )

        draw_value = draw_time_ms(project)
        first_shot_time = None if not shots else shot_display_time_ms(project, shots[0].time_ms)
        if (
            project.overlay.show_draw
            and draw_value is not None
            and first_shot_time is not None
            and position_ms < first_shot_time
        ):
            append_badge(
                Badge(f"Draw {_format_elapsed_seconds(draw_value)}", project.overlay.shot_badge),
                None if project.overlay.draw_lock_to_stack else project.overlay.draw_x,
                None if project.overlay.draw_lock_to_stack else project.overlay.draw_y,
            )

        final_shot_time = None if not shots else shot_display_time_ms(project, shots[-1].time_ms)
        final_shot_reached = final_shot_time is not None and position_ms >= final_shot_time

        if project.overlay.show_shots and current_index is not None:
            max_visible = max(1, int(project.overlay.max_visible_shots))
            start = max(0, current_index - max_visible + 1)
            for index in range(start, current_index + 1):
                shot = shots[index]
                split_row = split_row_by_shot_id.get(shot.id)
                split_ms = None if split_row is None else split_row.split_ms
                split_text = (
                    _format_split_seconds(max(0, split_ms or 0))
                    if _metric_caption_show_split_times(project)
                    else ""
                )
                style = (
                    project.overlay.current_shot_badge
                    if index == current_index
                    else project.overlay.shot_badge
                )
                base_text = _shot_badge_base_text(
                    index + 1,
                    split_text,
                    None if split_row is None else split_row.interval_label,
                )
                score_text, score_runs = _shot_score_badge_content(project, shot, base_text)
                badges.append(
                    Badge(
                        score_text,
                        style,
                        style.text_color,
                        None,
                        text_runs=score_runs,
                        text_bias=_text_bias_for_direction(project.overlay.shot_direction),
                    )
                )

        if final_shot_reached and project.scoring.enabled and project.overlay.show_score:
            summary = calculate_scoring_summary(project)
            if summary["display_value"] != "--":
                append_badge(
                    Badge(
                        f"{summary['display_label']} {summary['display_value']}",
                        project.overlay.hit_factor_badge,
                    ),
                    None if project.overlay.score_lock_to_stack else project.overlay.score_x,
                    None if project.overlay.score_lock_to_stack else project.overlay.score_y,
                )

        if lead_in_visible:
            intro_opacity, intro_y = _lead_in_card_animation_state(
                project._lead_in_card,
                position_ms,
                lead_in_duration_ms,
            )
            append_badge(
                Badge(
                    lead_in_text,
                    BadgeStyle(
                        background_color="#000000",
                        text_color="#ffffff",
                        opacity=0.84 * intro_opacity,
                    ),
                    text_bias="center",
                    image_path=lead_in_logo_path,
                    image_scale_percent=_lead_in_card_logo_scale_percent(project._lead_in_card),
                    content_opacity=intro_opacity,
                    use_individual_auto_size=True,
                ),
                0.5,
                intro_y,
            )

        if brand_visible:
            brand_x, brand_y = _brand_mark_point(project._brand_mark)
            append_badge(
                Badge(
                    brand_text,
                    BadgeStyle(
                        background_color="#000000",
                        text_color=_brand_mark_text_color(project._brand_mark),
                        opacity=_brand_mark_opacity(project._brand_mark),
                    ),
                    text_color=_brand_mark_text_color(project._brand_mark),
                    text_bias="center",
                    image_path=brand_image_path,
                    image_scale_percent=_brand_mark_image_scale_percent(project._brand_mark),
                    content_opacity=_brand_mark_opacity(project._brand_mark),
                    show_background=False,
                    font_family=_brand_mark_font_family(project._brand_mark),
                    font_size=_brand_mark_font_size(project._brand_mark),
                    use_individual_auto_size=True,
                ),
                brand_x,
                brand_y,
            )

        score_marks: list[tuple[str, float, float, float]] = []

        return badges, positioned_badges, score_marks

    @staticmethod
    def _text_box_text(
        project: Project, position_ms: int, source: str, text: str, enabled: bool
    ) -> str:
        if not enabled:
            return ""
        if source == "imported_summary":
            final_shot_time = (
                shot_display_time_ms(project, project.analysis.shots[-1].time_ms)
                if project.analysis.shots
                else None
            )
            if final_shot_time is None or position_ms < final_shot_time:
                return ""
            override_text = text.strip()
            if override_text:
                return override_text
            return format_imported_stage_overlay_text(project.scoring.imported_stage).strip()
        return text.strip()

    def paint(
        self, painter: QPainter, project: Project, position_ms: int, width: int, height: int
    ) -> None:
        lead_in_duration_ms = _hook_duration_ms(project._lead_in_card, 0.0)
        lead_in_visible = (
            bool(
                _lead_in_card_text(project, project._lead_in_card)
                or _lead_in_card_logo_path(project._lead_in_card)
            )
            and lead_in_duration_ms > 0
            and position_ms < lead_in_duration_ms
        )
        brand_duration_ms = _hook_duration_ms(project._brand_mark, 0.0)
        brand_visible = bool(
            _brand_mark_text(project._brand_mark) or _brand_mark_image_path(project._brand_mark)
        ) and (brand_duration_ms <= 0 or position_ms < brand_duration_ms)
        has_visible_popup = any(
            popup.enabled
            and popup_bubble_display_text(project, popup).strip()
            and popup_bubble_is_visible_at(project, popup, position_ms)
            for popup in project.popups
        )
        if (
            project.overlay.position == OverlayPosition.NONE
            and not has_visible_popup
            and not lead_in_visible
            and not brand_visible
        ):
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        font_size = project.overlay.font_size or _FONT_SIZE.get(
            project.overlay.badge_size, _FONT_SIZE[BadgeSize.M]
        )
        font = _overlay_qfont(
            project.overlay.font_family or default_overlay_font_family(),
            font_size,
            project.overlay.font_bold,
            project.overlay.font_italic,
        )
        painter.setFont(font)
        metrics = painter.fontMetrics()
        line_height = _badge_line_height(font, metrics)
        auto_badge_size = _auto_badge_size(
            _standard_badge_texts(project), metrics, line_height=line_height
        )

        badges, positioned_badges, score_marks = self._build_badges_with_positions(
            project, position_ms
        )
        final_shot_time = (
            None
            if not project.analysis.shots
            else shot_display_time_ms(project, project.analysis.shots[-1].time_ms)
        )
        final_shot_reached = final_shot_time is not None and position_ms >= final_shot_time
        score_summary = calculate_scoring_summary(project) if project.scoring.enabled else None
        has_final_score_badge = (
            final_shot_reached
            and project.overlay.show_score
            and project.scoring.enabled
            and score_summary is not None
            and score_summary["display_value"] != "--"
        )

        final_score_rect: QRectF | None = None
        badge_rects = self._paint_badges(
            painter, badges, project, width, height, auto_badge_size=auto_badge_size
        )
        stack_anchor_rect = _combined_rect(badge_rects)
        stack_terminal_rect = _terminal_stack_rect(badge_rects, project.overlay.shot_direction)
        if has_final_score_badge and project.overlay.score_lock_to_stack and badge_rects:
            final_score_rect = badge_rects[-1]
        for index, (badge, x, y) in enumerate(positioned_badges):
            positioned_badge_auto_size = auto_badge_size
            if badge.use_individual_auto_size and not badge.width and not badge.height:
                positioned_badge_auto_size = _auto_badge_size(
                    (badge.text,),
                    metrics,
                    line_height=line_height,
                )
            rects = self._paint_badges(
                painter,
                [badge],
                project,
                width,
                height,
                quadrant="custom",
                custom_x=x,
                custom_y=y,
                auto_badge_size=positioned_badge_auto_size,
            )
            if (
                has_final_score_badge
                and not project.overlay.score_lock_to_stack
                and index == len(positioned_badges) - 1
                and rects
            ):
                final_score_rect = rects[-1]
        text_boxes = (
            []
            if project.overlay.position == OverlayPosition.NONE
            else overlay_text_boxes_for_render(project.overlay)
        )
        for text_box in text_boxes:
            text_value = self._text_box_text(
                project,
                position_ms,
                text_box.source,
                text_box.text,
                text_box.enabled,
            )
            if not text_value:
                continue
            custom_style = BadgeStyle(
                background_color=text_box.background_color
                or project.overlay.hit_factor_badge.background_color,
                text_color=text_box.text_color or project.overlay.hit_factor_badge.text_color,
                opacity=text_box.opacity,
            )
            text_box_auto_size = _auto_badge_size((text_value,), metrics, line_height=line_height)
            if text_box.lock_to_stack and text_box.quadrant != _ABOVE_FINAL_TEXT_BOX_QUADRANT:
                rects = self._paint_badges(
                    painter,
                    [
                        Badge(
                            text_value,
                            custom_style,
                            width=text_box.width or None,
                            height=text_box.height or None,
                        )
                    ],
                    project,
                    width,
                    height,
                    quadrant=project.overlay.shot_quadrant,
                    anchor_rect=None,
                    after_rect=stack_terminal_rect,
                    auto_badge_size=text_box_auto_size,
                    use_project_bubble_size=False,
                )
                if rects:
                    stack_terminal_rect = rects[-1]
                continue
            text_box_quadrant = text_box.quadrant
            anchor_rect = final_score_rect
            if (
                text_box_quadrant == _ABOVE_FINAL_TEXT_BOX_QUADRANT
                and anchor_rect is None
                and getattr(text_box, "source", "") == "imported_summary"
            ):
                anchor_rect = stack_anchor_rect
            if text_box_quadrant == _ABOVE_FINAL_TEXT_BOX_QUADRANT and anchor_rect is None:
                text_box_quadrant = "top_middle"
            self._paint_badges(
                painter,
                [
                    Badge(
                        text_value,
                        custom_style,
                        width=text_box.width or None,
                        height=text_box.height or None,
                    )
                ],
                project,
                width,
                height,
                quadrant=text_box_quadrant,
                custom_x=text_box.x,
                custom_y=text_box.y,
                anchor_rect=anchor_rect,
                auto_badge_size=text_box_auto_size,
                use_project_bubble_size=False,
            )
        for popup in project.popups:
            popup_text = popup_bubble_display_text(project, popup)
            popup_content_type = popup_bubble_content_type(popup)
            popup_image_path = popup_bubble_image_path(popup)
            popup_has_text = popup_content_type in {"text", "text_image"} and bool(
                popup_text.strip()
            )
            popup_has_image = popup_content_type in {"image", "text_image"} and bool(
                popup_image_path
            )
            if (
                not popup.enabled
                or (not popup_has_text and not popup_has_image)
                or not popup_bubble_is_visible_at(project, popup, position_ms)
            ):
                continue
            popup_style = BadgeStyle(
                background_color=popup.background_color,
                text_color=popup.text_color,
                opacity=popup.opacity,
            )
            popup_auto_size = _auto_badge_size((popup_text,), metrics, line_height=line_height)
            popup_x, popup_y = popup_bubble_point(project, popup, position_ms)
            self._paint_badges(
                painter,
                [
                    Badge(
                        popup_text if popup_has_text else "",
                        popup_style,
                        width=popup.width or None,
                        height=popup.height or None,
                        image_path=popup_image_path,
                        image_scale_mode=popup_bubble_image_scale_mode(popup),
                    )
                ],
                project,
                width,
                height,
                quadrant="custom",
                custom_x=popup_x,
                custom_y=popup_y,
                auto_badge_size=popup_auto_size,
                use_project_bubble_size=False,
            )
        self._paint_scores(painter, project, score_marks, width, height)

        painter.restore()

    def _paint_badges(
        self,
        painter: QPainter,
        badges: list[Badge],
        project: Project,
        width: int,
        height: int,
        quadrant: str | None = None,
        custom_x: float | None = None,
        custom_y: float | None = None,
        auto_badge_size: tuple[int, int] | None = None,
        anchor_rect: QRectF | None = None,
        after_rect: QRectF | None = None,
        use_project_bubble_size: bool = True,
    ) -> list[QRectF]:
        if not badges:
            return []

        font_size = project.overlay.font_size or _FONT_SIZE.get(
            project.overlay.badge_size, _FONT_SIZE[BadgeSize.M]
        )
        font = _overlay_qfont(
            project.overlay.font_family or default_overlay_font_family(),
            font_size,
            project.overlay.font_bold,
            project.overlay.font_italic,
        )
        painter.setFont(font)
        metrics = painter.fontMetrics()
        line_height = _badge_line_height(font, metrics)
        padding_y = _BADGE_PADDING_Y_PX
        padding_x = _BADGE_PADDING_X_PX
        gap = max(0, int(project.overlay.spacing))
        frame_padding = max(0, int(project.overlay.margin))
        quadrant_value = quadrant or project.overlay.shot_quadrant

        x_override = (
            project.overlay.custom_x
            if custom_x is None and quadrant_value == "custom"
            else custom_x
        )
        y_override = (
            project.overlay.custom_y
            if custom_y is None and quadrant_value == "custom"
            else custom_y
        )
        if quadrant_value == "custom":
            if x_override is None:
                x_override = 0.5
            if y_override is None:
                y_override = 0.5

        previous_rect: QRectF | None = None
        painted_rects: list[QRectF] = []
        for index, badge in enumerate(badges):
            badge_font = _overlay_qfont(
                badge.font_family or project.overlay.font_family or default_overlay_font_family(),
                badge.font_size or font_size,
                project.overlay.font_bold if badge.font_bold is None else badge.font_bold,
                project.overlay.font_italic if badge.font_italic is None else badge.font_italic,
            )
            painter.setFont(badge_font)
            metrics = painter.fontMetrics()
            line_height = _badge_line_height(badge_font, metrics)
            lines = badge.text.splitlines() or [""]
            image = QImage(badge.image_path) if badge.image_path else QImage()
            has_image = not image.isNull()
            badge_auto_size = auto_badge_size
            if (
                has_image
                or badge.image_scale_percent
                or badge.font_family
                or badge.font_size
                or badge.font_bold is not None
                or badge.font_italic is not None
            ):
                badge_auto_size = None
            if badge.text_runs:
                text_width = sum(
                    metrics.horizontalAdvance(segment_text)
                    for segment_text, _segment_color in badge.text_runs
                )
            else:
                text_width = max(
                    max(metrics.horizontalAdvance(line) for line in lines),
                    self._minimum_badge_text_width(metrics, badge.text),
                )
            text_height = line_height * max(1, len(lines))
            explicit_width = int(
                badge.width or (project.overlay.bubble_width if use_project_bubble_size else 0) or 0
            )
            explicit_height = int(
                badge.height
                or (project.overlay.bubble_height if use_project_bubble_size else 0)
                or 0
            )
            fallback_width = text_width + (padding_x * 2)
            fallback_height = text_height + (padding_y * 2)
            if has_image:
                image_scale = max(
                    0.2,
                    min(4.0, float((badge.image_scale_percent or 100) / 100.0)),
                )
                scaled_image_width = max(96.0, float(image.width()) * image_scale)
                scaled_image_height = max(72.0, float(image.height()) * image_scale)
                if image.width() > 0 and image.height() > 0:
                    fit_ratio = min(
                        min(320.0, max(220.0, scaled_image_width)) / float(image.width()),
                        min(220.0, max(124.0, scaled_image_height)) / float(image.height()),
                    )
                    scaled_image_width = max(1.0, float(image.width()) * fit_ratio)
                    scaled_image_height = max(1.0, float(image.height()) * fit_ratio)
                fallback_width = max(
                    fallback_width,
                    int(round(scaled_image_width)) + (padding_x * 2),
                )
                image_height = int(round(scaled_image_height))
                fallback_height = max(
                    fallback_height,
                    image_height if not badge.text else image_height + text_height + 14,
                )
            badge_width = (
                explicit_width
                if explicit_width > 0
                else (badge_auto_size[0] if badge_auto_size else fallback_width)
            )
            badge_height = (
                explicit_height
                if explicit_height > 0
                else (badge_auto_size[1] if badge_auto_size else fallback_height)
            )
            base_rect = previous_rect or after_rect
            if base_rect is None:
                if quadrant_value == "custom":
                    rect_x = (max(0.0, min(1.0, float(x_override))) * width) - (badge_width / 2)
                    rect_y = (max(0.0, min(1.0, float(y_override))) * height) - (badge_height / 2)
                elif quadrant_value == _ABOVE_FINAL_TEXT_BOX_QUADRANT and anchor_rect is not None:
                    rect_x = anchor_rect.center().x() - (badge_width / 2)
                    rect_y = anchor_rect.top() - gap - badge_height
                else:
                    rect_x, rect_y = self._first_badge_position(
                        width,
                        height,
                        badge_width,
                        badge_height,
                        frame_padding,
                        quadrant_value,
                    )
                rect_x = max(0.0, min(rect_x, max(0.0, width - badge_width)))
                rect_y = max(0.0, min(rect_y, max(0.0, height - badge_height)))
            else:
                center_on_base = after_rect is not None
                rect_x = base_rect.x()
                rect_y = base_rect.y()
                if project.overlay.shot_direction == "right":
                    rect_x = base_rect.x() + base_rect.width() + gap
                    if center_on_base:
                        rect_y = base_rect.center().y() - (badge_height / 2)
                elif project.overlay.shot_direction == "left":
                    rect_x = base_rect.x() - badge_width - gap
                    if center_on_base:
                        rect_y = base_rect.center().y() - (badge_height / 2)
                elif project.overlay.shot_direction == "up":
                    if center_on_base:
                        rect_x = base_rect.center().x() - (badge_width / 2)
                    rect_y = base_rect.y() - badge_height - gap
                else:
                    if center_on_base:
                        rect_x = base_rect.center().x() - (badge_width / 2)
                    rect_y = base_rect.y() + base_rect.height() + gap
                if center_on_base:
                    rect_x = max(0.0, min(rect_x, max(0.0, width - badge_width)))
                    rect_y = max(0.0, min(rect_y, max(0.0, height - badge_height)))
            rect = QRectF(rect_x, rect_y, badge_width, badge_height)
            previous_rect = rect
            painted_rects.append(rect)
            text_bias = badge.text_bias or "center"
            content_opacity = _clamped_float(
                1.0 if badge.content_opacity is None else badge.content_opacity,
                1.0,
            )

            if badge.show_background:
                background = QColor(badge.background_color or badge.style.background_color)
                background.setAlphaF(badge.style.opacity)
                painter.setPen(Qt.NoPen)
                painter.setBrush(background)
                if project.overlay.style_type == "bubble":
                    radius = rect.height() / 2
                elif project.overlay.style_type == "rounded":
                    radius = 16
                else:
                    radius = 0
                if radius:
                    painter.drawRoundedRect(rect, radius, radius)
                else:
                    painter.drawRect(rect)
            text_rect = rect.adjusted(padding_x, padding_y, -padding_x, -padding_y)
            if has_image:
                image_rect = QRectF(text_rect)
                if badge.text:
                    image_rect.setBottom(
                        max(image_rect.top(), image_rect.bottom() - line_height - 6)
                    )
                if badge.image_scale_percent:
                    requested_scale = max(
                        0.2,
                        min(4.0, float(badge.image_scale_percent) / 100.0),
                    )
                    requested_width = max(1.0, float(image.width()) * requested_scale)
                    requested_height = max(1.0, float(image.height()) * requested_scale)
                    fit_ratio = min(
                        image_rect.width() / max(1.0, requested_width),
                        image_rect.height() / max(1.0, requested_height),
                        1.0,
                    )
                    draw_width = max(1.0, requested_width * fit_ratio)
                    draw_height = max(1.0, requested_height * fit_ratio)
                    image_rect = QRectF(
                        image_rect.center().x() - (draw_width / 2),
                        image_rect.center().y() - (draw_height / 2),
                        draw_width,
                        draw_height,
                    )
                source_rect = QRectF(0.0, 0.0, float(image.width()), float(image.height()))
                if (
                    badge.image_scale_mode == "cover"
                    and image_rect.width() > 0
                    and image_rect.height() > 0
                ):
                    source_ratio = image.width() / max(1.0, image.height())
                    target_ratio = image_rect.width() / max(1.0, image_rect.height())
                    if source_ratio > target_ratio:
                        cropped_width = image.height() * target_ratio
                        source_rect.setLeft((image.width() - cropped_width) / 2.0)
                        source_rect.setWidth(cropped_width)
                    else:
                        cropped_height = image.width() / max(0.0001, target_ratio)
                        source_rect.setTop((image.height() - cropped_height) / 2.0)
                        source_rect.setHeight(cropped_height)
                painter.save()
                painter.setOpacity(content_opacity)
                painter.drawImage(image_rect, image, source_rect)
                painter.restore()
            if badge.text_runs:
                default_color = QColor(badge.text_color or badge.style.text_color)
                total_text_width = sum(
                    metrics.horizontalAdvance(segment_text)
                    for segment_text, _segment_color in badge.text_runs
                )
                if text_bias == "left":
                    start_x = text_rect.left()
                elif text_bias == "right":
                    start_x = text_rect.right() - total_text_width
                else:
                    start_x = text_rect.left() + max(
                        0.0, (text_rect.width() - total_text_width) / 2
                    )
                baseline_y = (
                    text_rect.top()
                    + max(0.0, (text_rect.height() - metrics.height()) / 2)
                    + metrics.ascent()
                )
                cursor_x = start_x
                painter.save()
                painter.setOpacity(content_opacity)
                for segment_text, segment_color in badge.text_runs:
                    if not segment_text:
                        continue
                    painter.setPen(QColor(segment_color) if segment_color else default_color)
                    painter.drawText(QPointF(cursor_x, baseline_y), segment_text)
                    cursor_x += metrics.horizontalAdvance(segment_text)
                painter.restore()
            else:
                painter.save()
                painter.setOpacity(content_opacity)
                painter.setPen(QColor(badge.text_color or badge.style.text_color))
                if len(lines) > 1:
                    total_text_height = line_height * len(lines)
                    line_top = text_rect.top() + max(
                        0.0, (text_rect.height() - total_text_height) / 2
                    )
                    baseline_offset = min(metrics.ascent(), line_height)
                    painter.save()
                    painter.setClipRect(text_rect)
                    for line_index, line in enumerate(lines):
                        line_text = line or " "
                        line_width = metrics.horizontalAdvance(line_text)
                        if text_bias == "left":
                            line_x = text_rect.left()
                        elif text_bias == "right":
                            line_x = text_rect.right() - line_width
                        else:
                            line_x = text_rect.left() + max(
                                0.0, (text_rect.width() - line_width) / 2
                            )
                        baseline_y = line_top + (line_index * line_height) + baseline_offset
                        painter.drawText(QPointF(line_x, baseline_y), line)
                    painter.restore()
                else:
                    text_flags = Qt.AlignVCenter
                    if text_bias == "left":
                        text_flags |= Qt.AlignLeft
                    elif text_bias == "right":
                        text_flags |= Qt.AlignRight
                    else:
                        text_flags |= Qt.AlignHCenter
                    painter.drawText(
                        text_rect,
                        text_flags,
                        badge.text,
                    )
                painter.restore()
        return painted_rects

    @staticmethod
    def _first_badge_position(
        width: int,
        height: int,
        badge_width: int,
        badge_height: int,
        margin: int,
        quadrant: str,
    ) -> tuple[float, float]:
        vertical, horizontal = quadrant.split("_", 1) if "_" in quadrant else ("bottom", "left")
        x_map = {
            "left": float(margin),
            "middle": max(0.0, (width - badge_width) / 2),
            "right": max(0.0, width - badge_width - margin),
        }
        y_map = {
            "top": float(margin),
            "middle": max(0.0, (height - badge_height) / 2),
            "bottom": max(0.0, height - badge_height - margin),
        }
        return x_map.get(horizontal, float(margin)), y_map.get(vertical, float(margin))

    @staticmethod
    def _minimum_badge_text_width(metrics, text: str) -> int:
        if text.startswith("Timer"):
            return metrics.horizontalAdvance("Timer 00.00")
        if text.startswith("Draw"):
            return metrics.horizontalAdvance("Draw 00.00")
        if text.startswith("Hit Factor"):
            return metrics.horizontalAdvance("Hit Factor 00.00")
        if text.startswith("Final"):
            return metrics.horizontalAdvance("Final 00.00")
        return 0

    def _paint_scores(
        self,
        painter: QPainter,
        project: Project,
        score_marks: list[tuple[str, float, float, float]],
        width: int,
        height: int,
    ) -> None:
        if not score_marks:
            return

        for letter, x_norm, y_norm, alpha in score_marks:
            color = QColor(project.overlay.scoring_colors.get(letter, "#FFFFFF"))
            color.setAlphaF(alpha)
            painter.setPen(color)
            font = _overlay_qfont(default_overlay_font_family(), 28, bold=True, italic=False)
            painter.setFont(font)
            point = QPointF(x_norm * width, y_norm * height)
            painter.drawText(point, letter)
