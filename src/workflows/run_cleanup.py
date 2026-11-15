"""Helpers for starting each workflow with a clean generated-run directory."""
from __future__ import annotations

import shutil
from pathlib import Path


def clean_run_root(output_root: Path) -> None:
    """Remove generated runs while preserving the output directory placeholder."""
    root = output_root.expanduser().resolve()
    if root == root.parent:
        raise ValueError("Refusing to clean a filesystem root.")
    root.mkdir(parents=True, exist_ok=True)
    for child in root.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
