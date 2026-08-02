from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    project_dir: Path
    static_dir: Path
    minimum_year: int


def load_settings(project_dir: Path) -> AppSettings:
    resolved_project_dir = project_dir.resolve()
    return AppSettings(
        project_dir=resolved_project_dir,
        static_dir=resolved_project_dir / "time_radio" / "static",
        minimum_year=1949,
    )
