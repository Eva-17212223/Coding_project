# tools.py
"""
Utility functions for the Mammography AI Assistant.
Handles file I/O, DICOM loading, image conversion, and report management.
"""

import os
import cv2
import numpy as np
import pydicom
from typing import List
from pathlib import Path
from config import INPUT_DIR, OUTPUT_DIR, ANNOTATED_DIR, REPORTS_DIR


# -------------------------------------------------------------
# FILE & DIRECTORY UTILITIES
# -------------------------------------------------------------
def ensure_dir(path: Path) -> Path:
    """Ensure that a directory exists, creating it if necessary."""
    path = Path(path)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    return path


def list_input_files() -> List[str]:
    """List all input files supported (DICOM, PNG, JPG, JPEG) in input/."""
    exts = {".dcm", ".dicom", ".png", ".jpg", ".jpeg"}
    files = [
        os.path.join(INPUT_DIR, f)
        for f in os.listdir(INPUT_DIR)
        if os.path.splitext(f.lower())[1] in exts
    ]
    return sorted(files)


# -------------------------------------------------------------
# IMAGE LOADING
# -------------------------------------------------------------
def load_image_any(path: str) -> np.ndarray:
    """
    Load an image from a supported format (DICOM or standard image).
    Converts to BGR (3-channel) uint8 image suitable for OpenCV processing.
    """
    path = str(path)
    ext = os.path.splitext(path.lower())[1]

    if ext in {".dcm", ".dicom"}:
        ds = pydicom.dcmread(path)
        arr = ds.pixel_array.astype(np.float32)
        arr -= arr.min()
        if arr.max() > 0:
            arr /= arr.max()
        arr = (arr * 255).clip(0, 255).astype(np.uint8)
        bgr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
        return bgr
    else:
        bgr = cv2.imread(path, cv2.IMREAD_COLOR)
        if bgr is None:
            raise ValueError(f"Cannot read image: {path}")
        return bgr


# -------------------------------------------------------------
# FILE PATH HELPERS
# -------------------------------------------------------------
from pathlib import Path

def annotated_path(filename_stem: str) -> Path:
    """
    Return the path for saving an annotated image (with overlay).
    Ensures consistent naming: annotated_<original>.jpg
    """
    name = Path(filename_stem).stem  # retire extension
    return ANNOTATED_DIR / f"annotated_{name}.jpg"


# -------------------------------------------------------------
# REPORT MANAGEMENT
# -------------------------------------------------------------
def save_report(filename_stem: str, report_text: str, base_dir: Path = REPORTS_DIR) -> str:
    """
    Save a diagnostic report as a text file and return its full path.
    """
    ensure_dir(base_dir)
    name = os.path.splitext(os.path.basename(filename_stem))[0]
    out_path = os.path.join(base_dir, f"report_{name}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report_text.strip() + "\n")
    return out_path


# -------------------------------------------------------------
# SIMPLE SELF-TEST (optional)
# -------------------------------------------------------------
if __name__ == "__main__":
    ensure_dir(OUTPUT_DIR)
    ensure_dir(ANNOTATED_DIR)
    ensure_dir(REPORTS_DIR)

    print("✅ tools.py ready.")
    print("Input files:", list_input_files())
