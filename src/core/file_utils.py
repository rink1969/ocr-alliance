"""File system utilities for scanning inputs and resolving outputs."""

from __future__ import annotations

from pathlib import Path

from src.core.config import settings


def scan_images(input_dir: Path | str) -> list[Path]:
    """Recursively scan input directory for supported image files."""
    input_path = Path(input_dir)
    if not input_path.is_dir():
        raise ValueError(f"Input path is not a directory: {input_path}")

    images: list[Path] = []
    for ext in settings.image_extensions:
        images.extend(input_path.rglob(f"*{ext}"))
        images.extend(input_path.rglob(f"*{ext.upper()}"))

    # Deduplicate and sort
    seen = set()
    unique_images: list[Path] = []
    for img in images:
        resolved = img.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_images.append(img)
    unique_images.sort()
    return unique_images


def relative_path(input_dir: Path | str, image_path: Path | str) -> str:
    """Return the relative path of an image within the input directory."""
    return Path(image_path).relative_to(Path(input_dir)).as_posix()


def output_path_for(
    input_dir: Path | str,
    output_dir: Path | str,
    image_path: Path | str,
    suffix: str,
) -> Path:
    """Compute the output file path for a given image and result suffix."""
    rel = relative_path(input_dir, image_path)
    rel_text = Path(rel).with_suffix(suffix)
    return Path(output_dir) / rel_text


def ensure_output_dirs(input_dir: Path | str, output_dir: Path | str, images: list[Path]) -> None:
    """Create output subdirectories mirroring input structure."""
    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    for img in images:
        rel_parent = Path(relative_path(input_dir, img)).parent
        if rel_parent == Path("."):
            continue
        (out_root / rel_parent).mkdir(parents=True, exist_ok=True)
