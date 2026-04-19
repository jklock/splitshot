from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path


STATUS_BASE_SCORES = {
    "needs_review": 100.0,
    "verified": 10.0,
}
FLAG_PENALTIES = {
    "possible_clipping": 35.0,
    "shot_count_instability": 30.0,
    "shot_multipass_disagreement": 28.0,
    "duplicate_stage_inconsistency": 12.0,
    "possible_microphone_cutoff": 10.0,
    "beep_instability": 10.0,
    "beep_multipass_disagreement": 8.0,
    "confidence_saturation": 3.0,
}
CRITICAL_REVIEW_FLAGS = frozenset(
    {
        "possible_clipping",
        "shot_count_instability",
        "shot_multipass_disagreement",
    }
)
ACTION_REVIEW_NOW = "review_now"
ACTION_REVIEW_DUPLICATE_REPRESENTATIVE = "review_duplicate_representative"
ACTION_DEFER_DUPLICATE = "defer_duplicate"
ACTION_BLOCKED = "blocked"
ACTION_ALREADY_VERIFIED = "already_verified"
ACTION_PRIORITY = {
    ACTION_REVIEW_NOW: 0,
    ACTION_REVIEW_DUPLICATE_REPRESENTATIVE: 1,
    ACTION_DEFER_DUPLICATE: 2,
    ACTION_BLOCKED: 3,
    ACTION_ALREADY_VERIFIED: 4,
}


@dataclass(frozen=True, slots=True)
class ReviewQueueEntry:
    rank: int
    path: str
    relative_path: str
    status: str
    priority_score: float
    recommended_action: str
    priority_reasons: list[str]
    duration_seconds: float
    beep_family: str
    detector_shot_count: int
    detector_beep_time_ms: int | None
    review_flags: list[str]
    duplicate_group_key: str | None
    duplicate_group_review_required: bool
    duplicate_representative: bool
    beep_gap_ms: int | None
    shot_effective_unmatched_count: int
    shot_echo_like_count: int
    shot_review_required: bool
    beep_review_required: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReviewQueueSummary:
    manifest_path: str
    video_count: int
    queued_video_count: int
    included_statuses: list[str]
    status_counts: dict[str, int]
    action_counts: dict[str, int]
    beep_family_counts: dict[str, int]
    entries: list[ReviewQueueEntry]

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest_path": self.manifest_path,
            "video_count": self.video_count,
            "queued_video_count": self.queued_video_count,
            "included_statuses": list(self.included_statuses),
            "status_counts": dict(self.status_counts),
            "action_counts": dict(self.action_counts),
            "beep_family_counts": dict(self.beep_family_counts),
            "entries": [entry.to_dict() for entry in self.entries],
        }


def load_review_manifest(manifest_path: str | Path) -> dict[str, object]:
    path = Path(manifest_path).expanduser().resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Manifest must contain a JSON object: {path}")
    return payload


def _safe_int(value: object, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _beep_gap_ms(video: dict[str, object]) -> int | None:
    multipass = video.get("beep_multipass", {})
    if not isinstance(multipass, dict):
        return None
    gaps = [
        _safe_int(multipass.get("tone_model_gap_ms"), default=-1),
        _safe_int(multipass.get("final_tone_gap_ms"), default=-1),
        _safe_int(multipass.get("final_model_gap_ms"), default=-1),
    ]
    filtered = [gap for gap in gaps if gap >= 0]
    if not filtered:
        return None
    return max(filtered)


def _shot_effective_unmatched_count(video: dict[str, object]) -> tuple[int, int]:
    multipass = video.get("shot_multipass", {})
    if not isinstance(multipass, dict):
        return 0, 0
    unmatched_final_count = _safe_int(multipass.get("unmatched_final_count"))
    unmatched_onset_count = _safe_int(multipass.get("unmatched_onset_count"))
    echo_like_count = _safe_int(multipass.get("echo_like_onset_count"))
    effective_onset_count = max(0, unmatched_onset_count - echo_like_count)
    return unmatched_final_count + effective_onset_count, echo_like_count


def _priority_score(candidate: dict[str, object]) -> float:
    score = STATUS_BASE_SCORES.get(str(candidate["status"]), 60.0)
    score += max(0.0, 18.0 - (min(float(candidate["duration_seconds"]), 90.0) * 0.25))
    score += min(int(candidate["detector_shot_count"]), 30) * 0.3
    if not bool(candidate["shot_review_required"]):
        score += 18.0
    if not bool(candidate["beep_review_required"]):
        score += 8.0
    if not bool(candidate["duplicate_group_review_required"]):
        score += 10.0
    if candidate["duplicate_group_key"] is None:
        score += 4.0

    beep_gap_ms = candidate["beep_gap_ms"]
    if beep_gap_ms is not None:
        score -= min(float(beep_gap_ms) / 350.0, 12.0)

    score -= min(float(candidate["shot_effective_unmatched_count"]) * 8.0, 24.0)
    for flag in candidate["review_flags"]:
        score -= FLAG_PENALTIES.get(flag, 6.0)
    return score


def _build_candidate(video: dict[str, object]) -> dict[str, object] | None:
    path = video.get("path")
    if not isinstance(path, str) or not path:
        return None

    labels = video.get("labels", {})
    if not isinstance(labels, dict):
        labels = {}
    status = str(labels.get("status", "needs_review"))

    review_flags = sorted({str(flag) for flag in video.get("review_flags", [])})
    shot_multipass = video.get("shot_multipass", {})
    if not isinstance(shot_multipass, dict):
        shot_multipass = {}
    beep_multipass = video.get("beep_multipass", {})
    if not isinstance(beep_multipass, dict):
        beep_multipass = {}

    shot_effective_unmatched_count, shot_echo_like_count = _shot_effective_unmatched_count(video)
    candidate = {
        "path": path,
        "relative_path": str(video.get("relative_path") or Path(path).name),
        "status": status,
        "duration_seconds": _safe_float(video.get("duration_seconds")),
        "beep_family": str(video.get("beep_family", "unknown")),
        "detector_shot_count": _safe_int(video.get("detector_shot_count")),
        "detector_beep_time_ms": None
        if video.get("detector_beep_time_ms") is None
        else _safe_int(video.get("detector_beep_time_ms")),
        "review_flags": review_flags,
        "duplicate_group_key": None
        if video.get("duplicate_group_key") is None
        else str(video.get("duplicate_group_key")),
        "duplicate_group_review_required": bool(video.get("duplicate_group_review_required")),
        "duplicate_representative": False,
        "beep_gap_ms": _beep_gap_ms(video),
        "shot_effective_unmatched_count": shot_effective_unmatched_count,
        "shot_echo_like_count": shot_echo_like_count,
        "shot_review_required": bool(shot_multipass.get("review_required")),
        "beep_review_required": bool(beep_multipass.get("review_required")),
        "priority_reasons": [],
    }
    candidate["priority_score"] = _priority_score(candidate)
    return candidate


def build_review_queue(
    manifest_path: str | Path,
    include_statuses: tuple[str, ...] = ("needs_review",),
) -> ReviewQueueSummary:
    path = Path(manifest_path).expanduser().resolve()
    manifest = load_review_manifest(path)
    videos = manifest.get("videos", [])
    if not isinstance(videos, list):
        raise ValueError(f"Manifest videos must be a list: {path}")

    included = []
    for video in videos:
        if not isinstance(video, dict):
            continue
        candidate = _build_candidate(video)
        if candidate is None:
            continue
        if include_statuses and str(candidate["status"]) not in include_statuses:
            continue
        included.append(candidate)

    duplicate_groups: dict[str, list[dict[str, object]]] = {}
    for candidate in included:
        group_key = candidate["duplicate_group_key"]
        if group_key is None:
            continue
        duplicate_groups.setdefault(group_key, []).append(candidate)

    for group_candidates in duplicate_groups.values():
        if len(group_candidates) < 2 or not any(
            bool(candidate["duplicate_group_review_required"]) for candidate in group_candidates
        ):
            continue
        representative = max(
            group_candidates,
            key=lambda item: (
                float(item["priority_score"]),
                -float(item["duration_seconds"]),
                str(item["relative_path"]).lower(),
            ),
        )
        for candidate in group_candidates:
            if candidate is representative:
                candidate["duplicate_representative"] = True
                candidate["priority_score"] = float(candidate["priority_score"]) + 12.0
                candidate["priority_reasons"].append("best_duplicate_representative")
                continue
            candidate["priority_score"] = float(candidate["priority_score"]) - 18.0
            candidate["priority_reasons"].append("defer_duplicate_until_representative_reviewed")

    family_best: dict[str, dict[str, object]] = {}
    for candidate in included:
        family = str(candidate["beep_family"])
        if not family or family == "unknown":
            continue
        current = family_best.get(family)
        if current is None or float(candidate["priority_score"]) > float(current["priority_score"]):
            family_best[family] = candidate
    for family, candidate in family_best.items():
        candidate["priority_score"] = float(candidate["priority_score"]) + 8.0
        candidate["priority_reasons"].append(f"family_coverage_anchor:{family}")

    for candidate in included:
        status = str(candidate["status"])
        flags = set(str(flag) for flag in candidate["review_flags"])
        if status == "verified":
            candidate["recommended_action"] = ACTION_ALREADY_VERIFIED
        elif flags & CRITICAL_REVIEW_FLAGS:
            candidate["recommended_action"] = ACTION_BLOCKED
        elif bool(candidate["duplicate_group_review_required"]) and bool(candidate["duplicate_representative"]):
            candidate["recommended_action"] = ACTION_REVIEW_DUPLICATE_REPRESENTATIVE
        elif bool(candidate["duplicate_group_review_required"]) and candidate["duplicate_group_key"] is not None:
            candidate["recommended_action"] = ACTION_DEFER_DUPLICATE
        else:
            candidate["recommended_action"] = ACTION_REVIEW_NOW

    ordered = sorted(
        included,
        key=lambda item: (
            ACTION_PRIORITY.get(str(item["recommended_action"]), 99),
            -float(item["priority_score"]),
            str(item["relative_path"]).lower(),
        ),
    )

    entries: list[ReviewQueueEntry] = []
    for index, candidate in enumerate(ordered, start=1):
        entry = ReviewQueueEntry(
            rank=index,
            path=str(candidate["path"]),
            relative_path=str(candidate["relative_path"]),
            status=str(candidate["status"]),
            priority_score=round(float(candidate["priority_score"]), 2),
            recommended_action=str(candidate["recommended_action"]),
            priority_reasons=list(dict.fromkeys(str(reason) for reason in candidate["priority_reasons"])),
            duration_seconds=float(candidate["duration_seconds"]),
            beep_family=str(candidate["beep_family"]),
            detector_shot_count=int(candidate["detector_shot_count"]),
            detector_beep_time_ms=None
            if candidate["detector_beep_time_ms"] is None
            else int(candidate["detector_beep_time_ms"]),
            review_flags=list(candidate["review_flags"]),
            duplicate_group_key=None
            if candidate["duplicate_group_key"] is None
            else str(candidate["duplicate_group_key"]),
            duplicate_group_review_required=bool(candidate["duplicate_group_review_required"]),
            duplicate_representative=bool(candidate["duplicate_representative"]),
            beep_gap_ms=None if candidate["beep_gap_ms"] is None else int(candidate["beep_gap_ms"]),
            shot_effective_unmatched_count=int(candidate["shot_effective_unmatched_count"]),
            shot_echo_like_count=int(candidate["shot_echo_like_count"]),
            shot_review_required=bool(candidate["shot_review_required"]),
            beep_review_required=bool(candidate["beep_review_required"]),
        )
        entries.append(entry)

    status_counts = Counter(entry.status for entry in entries)
    action_counts = Counter(entry.recommended_action for entry in entries)
    family_counts = Counter(entry.beep_family for entry in entries)
    return ReviewQueueSummary(
        manifest_path=str(path),
        video_count=len(videos),
        queued_video_count=len(entries),
        included_statuses=list(include_statuses),
        status_counts=dict(sorted(status_counts.items())),
        action_counts=dict(sorted(action_counts.items())),
        beep_family_counts=dict(sorted(family_counts.items())),
        entries=entries,
    )