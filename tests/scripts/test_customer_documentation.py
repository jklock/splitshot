"""Keep customer documentation linked, current, and free of release-planning language."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CUSTOMER_DOCS = (ROOT / "README.md", ROOT / "docs" / "README.md", *sorted((ROOT / "docs" / "userfacing").rglob("*.md")))
LINK_PATTERN = re.compile(r'(?:href|src)="([^"#]+)"|\[[^]]*\]\(([^)#]+)(?:#[^)]+)?\)')
DISALLOWED_LANGUAGE = re.compile(
    r"\b(?:future|planned|roadmap|coming soon|pre-release|release-preparation|feature-frozen)\b",
    re.IGNORECASE,
)


def test_customer_documentation_links_and_images_resolve() -> None:
    missing: list[str] = []
    for document in CUSTOMER_DOCS:
        for html_target, markdown_target in LINK_PATTERN.findall(document.read_text(encoding="utf-8")):
            target = html_target or markdown_target
            if "://" in target or target.startswith(("mailto:", "#")):
                continue
            destination = (document.parent / target).resolve()
            if not destination.exists():
                missing.append(f"{document.relative_to(ROOT)} -> {target}")
    assert not missing, "Broken customer-documentation references:\n" + "\n".join(missing)


def test_customer_documentation_has_no_release_planning_language() -> None:
    violations = [
        str(document.relative_to(ROOT))
        for document in CUSTOMER_DOCS
        if DISALLOWED_LANGUAGE.search(document.read_text(encoding="utf-8"))
    ]
    assert not violations, "Customer documentation contains release-planning language: " + ", ".join(violations)
