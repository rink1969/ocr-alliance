"""Build a standalone binary for the current platform using PyInstaller."""

from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path


def build() -> None:
    """Run PyInstaller to package src/main.py."""
    root = Path(__file__).resolve().parent.parent
    src = root / "src"
    main_script = src / "main.py"
    web_dir = src / "web"

    if not main_script.is_file():
        raise FileNotFoundError(f"Entry script not found: {main_script}")

    system = platform.system()
    data_sep = ";" if system == "Windows" else ":"

    name = "OCRAlliance"
    dist_path = root / "dist"
    work_path = root / "build"

    hidden_imports = [
        "src.api.routes",
        "src.api.schemas",
        "src.core.config",
        "src.core.database",
        "src.core.scheduler",
        "src.core.file_utils",
        "src.ocr.paddleocr",
        "src.ocr.hunyuan",
        "src.ocr.glm",
        "src.ocr.registry",
        "src.llm.unifier",
    ]

    cmd: list[str] = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(main_script),
        "--name",
        name,
        "--windowed",
        "--onedir",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(dist_path),
        "--workpath",
        str(work_path),
        "--paths",
        str(src),
        "--add-data",
        f"{web_dir}{data_sep}src/web",
    ]

    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    if system == "Darwin":
        cmd.extend(["--osx-bundle-identifier", "com.ocralliance.app"])

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"Build complete. Output: {dist_path / name}")


if __name__ == "__main__":
    build()
