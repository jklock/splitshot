from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path

import numpy as np


AUTO_LABEL_STATUS = "auto_labeled"
MANUAL_VERIFIED_STATUS = "verified"
AUTO_LABEL_MIN_SCORE = 0.65
DEFAULT_BEEP_CONSENSUS_TOLERANCE_MS = 180
@dataclass(frozen=True, slots=True)
class AutoLabelDecision:
    relative_path: str
    previous_status: str
    new_status: str
    auto_label_score: float | None
    auto_label_method: str
    auto_label_reasons: list[str]
    skip_reason: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AutoLabelSummary:
    manifest_path: str
    video_count: int
    preserved_verified_count: int
    auto_labeled_count: int
    demoted_to_needs_review_count: int
    skipped_reason_counts: dict[str, int]
    status_counts: dict[str, int]
    entries: list[AutoLabelDecision]

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest_path": self.manifest_path,
            "video_count": self.video_count,
            "preserved_verified_count": self.preserved_verified_count,
            "auto_labeled_count": self.auto_labeled_count,
            "demoted_to_needs_review_count": self.demoted_to_needs_review_count,
            "skipped_reason_counts": dict(self.skipped_reason_counts),
            "status_counts": dict(self.status_counts),
            "entries": [entry.to_dict() for entry in self.entries],
        }


def load_manifest(manifest_path: str | Path) -> dict[str, object]:
    path = Path(manifest_path).expanduser().resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Manifest must contain a JSON object: {path}")
    return payload


def _candidate_beep_times(video: dict[str, object]) -> list[tuple[str, int]]:
    candidates: list[tuple[str, int]] = []
    detector_beep_time_ms = video.get("detector_beep_time_ms")
    if detector_beep_time_ms is not None:
        candidates.append(("primary_detector", int(detector_beep_time_ms)))

    beep_multipass = video.get("beep_multipass", {})
    if isinstance(beep_multipass, dict):
        for label, key in (("tone", "tone_beep_time_ms"), ("model", "model_beep_time_ms")):
            value = beep_multipass.get(key)
            if value is None:
                continue
            candidates.append((label, int(value)))
    return candidates


def _select_consensus_beep(
    video: dict[str, object],
    tolerance_ms: int,
) -> tuple[int | None, float, str, list[str]]:
    candidates = _candidate_beep_times(video)
    if not candidates:
        return None, 0.0, "missing_beep_candidates", ["missing_beep_candidates"]

    primary_candidate = next((candidate for candidate in candidates if candidate[0] == "primary_detector"), None)
    if primary_candidate is not None:
        primary_label, primary_beep_time_ms = primary_candidate
        agreeing_candidates = [
            candidate
            for candidate in candidates
            if candidate[0] != primary_label and abs(candidate[1] - primary_beep_time_ms) <= tolerance_ms
        ]
        if agreeing_candidates:
            closest = min(agreeing_candidates, key=lambda item: abs(item[1] - primary_beep_time_ms))
            selected_beep_time_ms = int(round(np.mean([primary_beep_time_ms, closest[1]])))
            gap_ms = abs(primary_beep_time_ms - closest[1])
            score = 0.92 - min(gap_ms / 1200.0, 0.04)
            return (
                selected_beep_time_ms,
                max(0.0, score),
                "primary_detector_pair_consensus",
                [f"beep_pair_agreement:primary_detector+{closest[0]}"],
            )
        return (
            primary_beep_time_ms,
            0.76,
            "primary_detector_preferred",
            ["beep_primary_detector_preferred"],
        )

    if len(candidates) == 1:
        label, beep_time_ms = candidates[0]
        return beep_time_ms, 0.72, "single_candidate", [f"single_candidate:{label}"]

    best_pair: tuple[tuple[str, int], tuple[str, int]] | None = None
    best_gap_ms: int | None = None
    for index, left in enumerate(candidates):
        for right in candidates[index + 1 :]:
            gap_ms = abs(left[1] - right[1])
            if gap_ms > tolerance_ms:
                continue
            if best_gap_ms is None or gap_ms < best_gap_ms:
                best_gap_ms = gap_ms
                best_pair = (left, right)

    if best_pair is not None and best_gap_ms is not None:
        selected_beep_time_ms = int(round(np.mean([best_pair[0][1], best_pair[1][1]])))
        label_names = "+".join([best_pair[0][0], best_pair[1][0]])
        score = 0.92 if "final" in {best_pair[0][0], best_pair[1][0]} else 0.88
        score -= min(best_gap_ms / 1200.0, 0.04)
        return selected_beep_time_ms, max(0.0, score), "pair_consensus", [f"beep_pair_agreement:{label_names}"]

    spread_ms = max(candidate[1] for candidate in candidates) - min(candidate[1] for candidate in candidates)
    selected_beep_time_ms = int(round(float(np.median([candidate[1] for candidate in candidates]))))
    score = 0.70 - min(spread_ms / 10000.0, 0.12)
    return selected_beep_time_ms, max(0.0, score), "median_fallback", [f"beep_median_fallback:spread_ms={spread_ms}"]


def _blocking_reason(video: dict[str, object]) -> str | None:
    labels = video.get("labels", {})
    if not isinstance(labels, dict):
        labels = {}
    status = str(labels.get("status", "needs_review"))
    if status == MANUAL_VERIFIED_STATUS:
        return None

    detector_shot_times_ms = video.get("detector_shot_times_ms", [])
    if not detector_shot_times_ms:
        return "missing_detector_shots"
    return None


def _auto_label_score(
    video: dict[str, object],
    beep_score: float,
) -> float:
    score = 0.50
    score += 0.25
    score += 0.15
    score += min(beep_score, 0.20)

    beep_multipass = video.get("beep_multipass", {})
    if isinstance(beep_multipass, dict):
        beep_gap_candidates = [
            value
            for value in (
                beep_multipass.get("tone_model_gap_ms"),
                beep_multipass.get("final_tone_gap_ms"),
                beep_multipass.get("final_model_gap_ms"),
            )
            if value is not None
        ]
        if beep_gap_candidates:
            worst_beep_gap_ms = max(int(value) for value in beep_gap_candidates)
            score -= min(worst_beep_gap_ms / 8000.0, 0.15)

    review_flags = {str(flag) for flag in video.get("review_flags", [])}
    if "confidence_saturation" in review_flags:
        score -= 0.05
    if "beep_instability" in review_flags:
        score -= 0.10
    if "possible_microphone_cutoff" in review_flags:
        score -= 0.05

    return max(0.0, min(1.0, score))


def _clear_auto_label_fields(labels: dict[str, object]) -> None:
    labels["auto_beep_time_ms"] = None
    labels["auto_shot_times_ms"] = []
    labels["auto_label_score"] = None
    labels["auto_label_method"] = ""
    labels["auto_label_reasons"] = []


def apply_auto_labels(
    manifest: dict[str, object],
    *,
    min_score: float = AUTO_LABEL_MIN_SCORE,
    beep_consensus_tolerance_ms: int = DEFAULT_BEEP_CONSENSUS_TOLERANCE_MS,
) -> AutoLabelSummary:
    videos = manifest.get("videos", [])
    if not isinstance(videos, list):
        raise ValueError("Manifest videos must be a list.")

    decisions: list[AutoLabelDecision] = []
    skipped_reason_counts: Counter[str] = Counter()
    preserved_verified_count = 0
    auto_labeled_count = 0
    demoted_to_needs_review_count = 0

    for video in videos:
        if not isinstance(video, dict):
            continue
        labels = video.get("labels")
        if not isinstance(labels, dict):
            labels = {}
            video["labels"] = labels

        previous_status = str(labels.get("status", "needs_review"))
        relative_path = str(video.get("relative_path") or Path(str(video.get("path", "unknown"))).name)

        if previous_status == MANUAL_VERIFIED_STATUS:
            preserved_verified_count += 1
            decisions.append(
                AutoLabelDecision(
                    relative_path=relative_path,
                    previous_status=previous_status,
                    new_status=previous_status,
                    auto_label_score=None,
                    auto_label_method="preserve_verified",
                    auto_label_reasons=[],
                    skip_reason=None,
                )
            )
            continue

        blocking_reason = _blocking_reason(video)
        if blocking_reason is not None:
            skipped_reason_counts[blocking_reason] += 1
            if previous_status == AUTO_LABEL_STATUS:
                demoted_to_needs_review_count += 1
            labels["status"] = "needs_review"
            _clear_auto_label_fields(labels)
            decisions.append(
                AutoLabelDecision(
                    relative_path=relative_path,
                    previous_status=previous_status,
                    new_status="needs_review",
                    auto_label_score=None,
                    auto_label_method="",
                    auto_label_reasons=[],
                    skip_reason=blocking_reason,
                )
            )
            continue

        auto_beep_time_ms, beep_score, auto_label_method, auto_label_reasons = _select_consensus_beep(
            video,
            beep_consensus_tolerance_ms,
        )
        auto_shot_times_ms = [int(value) for value in video.get("detector_shot_times_ms", [])]
        overall_score = _auto_label_score(video, beep_score)
        if auto_beep_time_ms is None or overall_score < min_score:
            skip_reason = "insufficient_auto_label_consensus"
            skipped_reason_counts[skip_reason] += 1
            if previous_status == AUTO_LABEL_STATUS:
                demoted_to_needs_review_count += 1
            labels["status"] = "needs_review"
            _clear_auto_label_fields(labels)
            decisions.append(
                AutoLabelDecision(
                    relative_path=relative_path,
                    previous_status=previous_status,
                    new_status="needs_review",
                    auto_label_score=round(overall_score, 3),
                    auto_label_method=auto_label_method,
                    auto_label_reasons=list(auto_label_reasons),
                    skip_reason=skip_reason,
                )
            )
            continue

        labels["status"] = AUTO_LABEL_STATUS
        labels["auto_beep_time_ms"] = auto_beep_time_ms
        labels["auto_shot_times_ms"] = auto_shot_times_ms
        labels["auto_label_score"] = round(overall_score, 3)
        labels["auto_label_method"] = auto_label_method
        labels["auto_label_reasons"] = list(auto_label_reasons)
        auto_labeled_count += 1
        decisions.append(
            AutoLabelDecision(
                relative_path=relative_path,
                previous_status=previous_status,
                new_status=AUTO_LABEL_STATUS,
                auto_label_score=round(overall_score, 3),
                auto_label_method=auto_label_method,
                auto_label_reasons=list(auto_label_reasons),
                skip_reason=None,
            )
        )

    status_counts = Counter(
        str(video.get("labels", {}).get("status", "needs_review"))
        for video in videos
        if isinstance(video, dict)
    )
    manifest_path = str(manifest.get("manifest_path", ""))
    return AutoLabelSummary(
        manifest_path=manifest_path,
        video_count=len(videos),
        preserved_verified_count=preserved_verified_count,
        auto_labeled_count=auto_labeled_count,
        demoted_to_needs_review_count=demoted_to_needs_review_count,
        skipped_reason_counts=dict(sorted(skipped_reason_counts.items())),
        status_counts=dict(sorted(status_counts.items())),
        entries=decisions,
    )
