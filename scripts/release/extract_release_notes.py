"""Extract one release section from CHANGELOG.md into a standalone notes file."""

from __future__ import annotations

import argparse
from pathlib import Path


def extract_section(changelog_path: Path, tag: str) -> str:
    lines = changelog_path.read_text(encoding="utf-8").splitlines()
    header = f"## {tag}"
    capture: list[str] = []
    active = False
    for line in lines:
        if line.startswith("## "):
            if active:
                break
            active = line.strip() == header
            continue
        if active:
            capture.append(line)
    body = "\n".join(capture).strip()
    if not body:
        raise SystemExit(f"No release notes found for {tag} in {changelog_path}")
    return body + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract the body of one semver release section from CHANGELOG.md."
    )
    parser.add_argument("tag", help="Release tag heading to extract, for example v1.0.0")
    parser.add_argument(
        "--changelog",
        default="CHANGELOG.md",
        help="Path to the changelog file. Defaults to CHANGELOG.md.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write the extracted release notes markdown file.",
    )
    args = parser.parse_args()
    body = extract_section(Path(args.changelog), args.tag)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
