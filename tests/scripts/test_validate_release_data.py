from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "testing" / "validate_release_data.py"
SPEC = importlib.util.spec_from_file_location("validate_release_data_module", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fixture(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    corpus = tmp_path / "tests" / "release_data"
    corpus.mkdir(parents=True)
    primary = b"primary-real-video"
    secondary = b"secondary-real-video"
    csv_bytes = b"name,value\nShooter,1\n"
    (corpus / "primary.MP4").write_bytes(primary)
    (corpus / "secondary.MP4").write_bytes(secondary)
    (corpus / "practiscore.csv").write_bytes(csv_bytes)
    manifest = {
        "schema_version": 1,
        "corpus_revision": "test-corpus",
        "files": {
            "primary.MP4": {
                "bytes": len(primary),
                "sha256": _digest(primary),
                "video": {
                    "codec": "h264",
                    "width": 1920,
                    "height": 1080,
                    "frame_rate": "60/1",
                    "duration_seconds": 2.0,
                },
                "audio": {"codec": "pcm_s16le", "channels": 2},
            },
            "secondary.MP4": {
                "bytes": len(secondary),
                "sha256": _digest(secondary),
                "video": {
                    "codec": "h264",
                    "width": 1920,
                    "height": 1080,
                    "frame_rate": "60/1",
                    "duration_seconds": 2.0,
                },
                "audio": {"codec": "pcm_s16le", "channels": 2},
            },
            "practiscore.csv": {
                "bytes": len(csv_bytes),
                "sha256": _digest(csv_bytes),
                "csv": {
                    "match_type": "idpa",
                    "columns": 2,
                    "competitors": 1,
                    "stages": [1, 2, 3, 4],
                },
            },
        },
    }
    manifest_path = corpus / "corpus-v1.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(
        MODULE,
        "_tracked_files",
        lambda root, paths: {path.relative_to(root).as_posix() for path in paths},
    )
    monkeypatch.setattr(MODULE, "_resolve_tool", lambda name: name)
    monkeypatch.setattr(
        MODULE,
        "_probe_video",
        lambda path, ffprobe: {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "60/1",
                },
                {"codec_type": "audio", "codec_name": "pcm_s16le", "channels": 2},
            ],
            "format": {"duration": "2.0"},
        },
    )
    monkeypatch.setattr(
        MODULE,
        "_decoded_frame_stats",
        lambda path, duration, ffmpeg: {
            "minimum": 0.0,
            "maximum": 200.0,
            "mean": 80.0,
            "range": 200.0,
            "sha256": _digest(path.name.encode()),
        },
    )
    monkeypatch.setattr(
        MODULE,
        "describe_practiscore_file",
        lambda path: SimpleNamespace(
            match_type="idpa", stage_numbers=[1, 2, 3, 4], competitors=["Shooter"]
        ),
    )
    return corpus, manifest_path


def test_release_data_validation_passes_exact_corpus(tmp_path: Path, monkeypatch) -> None:
    corpus, manifest = _fixture(tmp_path, monkeypatch)

    report = MODULE.validate(root=tmp_path, corpus_root=corpus, manifest_path=manifest)

    assert report["result"] == "passed"
    assert report["failed_checks"] == []


def test_release_data_validation_rejects_checksum_change(tmp_path: Path, monkeypatch) -> None:
    corpus, manifest = _fixture(tmp_path, monkeypatch)
    (corpus / "primary.MP4").write_bytes(b"changed")

    report = MODULE.validate(root=tmp_path, corpus_root=corpus, manifest_path=manifest)

    assert report["result"] == "failed"
    assert "size:primary.MP4" in report["failed_checks"]
    assert "sha256:primary.MP4" in report["failed_checks"]


def test_release_data_validation_rejects_unexpected_file(tmp_path: Path, monkeypatch) -> None:
    corpus, manifest = _fixture(tmp_path, monkeypatch)
    (corpus / "synthetic.mp4").write_bytes(b"synthetic")

    report = MODULE.validate(root=tmp_path, corpus_root=corpus, manifest_path=manifest)

    assert report["result"] == "failed"
    assert "exact-file-set" in report["failed_checks"]


def test_release_data_validation_rejects_blank_or_duplicate_frames(
    tmp_path: Path, monkeypatch
) -> None:
    corpus, manifest = _fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        MODULE,
        "_decoded_frame_stats",
        lambda path, duration, ffmpeg: {
            "minimum": 0.0,
            "maximum": 0.0,
            "mean": 0.0,
            "range": 0.0,
            "sha256": "same-frame",
        },
    )

    report = MODULE.validate(root=tmp_path, corpus_root=corpus, manifest_path=manifest)

    assert report["result"] == "failed"
    assert "nonblank-frame:primary.MP4" in report["failed_checks"]
    assert "nonblank-frame:secondary.MP4" in report["failed_checks"]
    assert "videos-distinct" in report["failed_checks"]
