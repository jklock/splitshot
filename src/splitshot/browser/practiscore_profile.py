from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

import splitshot.config as splitshot_config


_PRACTISCORE_ROOT_DIRNAME = "practiscore"
_PRACTISCORE_PROFILE_DIRNAME = "browser-profile"


@dataclass(frozen=True, slots=True)
class PractiScoreProfilePaths:
    app_dir: Path
    root_dir: Path
    profile_dir: Path


def resolve_practiscore_profile_paths(app_dir: Path | None = None) -> PractiScoreProfilePaths:
    resolved_app_dir = Path(app_dir) if app_dir is not None else splitshot_config.APP_DIR
    root_dir = resolved_app_dir / _PRACTISCORE_ROOT_DIRNAME
    profile_dir = root_dir / _PRACTISCORE_PROFILE_DIRNAME
    return PractiScoreProfilePaths(
        app_dir=resolved_app_dir,
        root_dir=root_dir,
        profile_dir=profile_dir,
    )


def ensure_practiscore_profile_dir(app_dir: Path | None = None) -> Path:
    if app_dir is None:
        splitshot_config.ensure_app_dir()
    paths = resolve_practiscore_profile_paths(app_dir)
    paths.profile_dir.mkdir(parents=True, exist_ok=True)
    return paths.profile_dir


def clear_practiscore_profile_data(app_dir: Path | None = None) -> PractiScoreProfilePaths:
    paths = resolve_practiscore_profile_paths(app_dir)
    if paths.profile_dir.exists():
        shutil.rmtree(paths.profile_dir)
    if paths.root_dir.exists():
        try:
            paths.root_dir.rmdir()
        except OSError:
            pass
    return paths