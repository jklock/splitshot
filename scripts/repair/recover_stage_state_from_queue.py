"""Recover missing live stage media and analysis from matching queue snapshots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from splitshot.repair import apply_stage_queue_recovery, recover_project_payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path, help="Project directory or project.json")
    parser.add_argument("--apply", action="store_true", help="Back up and write the repaired project")
    args = parser.parse_args()
    project_file = args.project / "project.json" if args.project.is_dir() else args.project
    payload = json.loads(project_file.read_text(encoding="utf-8"))
    _, labels = recover_project_payload(payload, project_root=project_file.parent)
    print(json.dumps({"project": str(project_file), "recoverable_stages": labels}, indent=2))
    if args.apply and labels:
        backup, applied_labels = apply_stage_queue_recovery(project_file)
        print(json.dumps({"backup": str(backup), "recovered_stages": applied_labels}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
