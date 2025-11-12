# analyser.py
"""
Extended analysis pipeline for the Mammography AI Assistant.
- Builds upon the previous robust preprocessing, segmentation, and quantification pipeline.
- Adds multi-image handling (input folder traversal).
- Supports 'first' or 'latest' image selection.
- Stores context of the latest analysis for explanatory follow-up (e.g. suspicious zone explanation).

Returns (to agent.py):
    ratio_percent (float), region_desc (str), annotated_file (Path), report_path (Path)
"""

from pathlib import Path
import cv2
import numpy as np
import os
from datetime import datetime

from config import (
    TARGET_SIZE,
    CLAHE_CLIP,
    CLAHE_TILEGRID,
    MORPH_KERNEL,
    MIN_COMPONENT_AREA,
    BORDER_CROP_PCT,
    THRESH_STRATEGY,
    ADAPTIVE_BLOCK_SIZE,
    ADAPTIVE_C,
    MIN_SUSPICIOUS_RATIO,
    MAX_SUSPICIOUS_RATIO,
    REPORTS_DIR,
    ANNOTATED_DIR,
)
from tools import load_image_any, annotated_path, save_report, ensure_dir


# Keep global memory of the last analysis for explanations
_last_analysis = {
    "file": None,
    "ratio": None,
    "region": None,
    "density": None,
    "suspicion_index": None,
    "annotation_path": None,
    "report_path": None,
}


# -------------------------------------------------------------
# 1) PREPROCESS (same as before)
# -------------------------------------------------------------
def preprocess(img_bgr: np.ndarray) -> np.ndarray:
    resized = cv2.resize(img_bgr, TARGET_SIZE, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=CLAHE_TILEGRID)
    gray = clahe.apply(gray)

    crop_y = int(gray.shape[0] * BORDER_CROP_PCT)
    crop_x = int(gray.shape[1] * BORDER_CROP_PCT)
    if crop_y > 0 and crop_x > 0:
        gray = gray[crop_y:-crop_y, crop_x:-crop_x]
    return gray


# -------------------------------------------------------------
# 2) SEGMENT (same as before)
# -------------------------------------------------------------
def segment_suspicious(gray: np.ndarray) -> np.ndarray:
    if THRESH_STRATEGY == "adaptive":
        mask = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            ADAPTIVE_BLOCK_SIZE, ADAPTIVE_C
        )
    else:
        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    mask = cv2.bitwise_not(mask)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, MORPH_KERNEL)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    num, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    cleaned = np.zeros_like(mask)
    for i in range(1, num):
        if stats[i, cv2.CC_STAT_AREA] >= MIN_COMPONENT_AREA:
            cleaned[labels == i] = 255
    return cleaned


def largest_component(mask: np.ndarray) -> np.ndarray:
    num, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if num <= 2:
        return mask
    areas = stats[1:, cv2.CC_STAT_AREA]
    idx = 1 + int(np.argmax(areas))
    largest = np.zeros_like(mask)
    largest[labels == idx] = 255
    return largest


# -------------------------------------------------------------
# 3) QUANTIFY & LOCALIZE
# -------------------------------------------------------------
def ratio_percent_from_mask(mask: np.ndarray) -> float:
    total = mask.size
    suspicious = int(np.count_nonzero(mask))
    if total == 0:
        return 0.0
    ratio = suspicious / total
    ratio = float(np.clip(ratio, MIN_SUSPICIOUS_RATIO, MAX_SUSPICIOUS_RATIO))
    return round(ratio * 100.0, 1)


def density_class_from_ratio(ratio_percent: float) -> str:
    if ratio_percent < 5:
        return "A – Almost entirely fatty"
    if ratio_percent < 15:
        return "B – Scattered fibroglandular"
    if ratio_percent < 35:
        return "C – Heterogeneously dense"
    return "D – Extremely dense"


def suspicion_index(mask: np.ndarray, ratio_percent: float) -> float:
    v = cv2.Laplacian(mask, cv2.CV_64F).var()
    idx = 0.6 * ratio_percent + 0.004 * v
    return float(np.clip(idx, 0.0, 100.0))


def centroid_and_quadrant(mask: np.ndarray) -> tuple[str, tuple[int, int]]:
    M = cv2.moments(mask, binaryImage=True)
    h, w = mask.shape[:2]
    if M["m00"] == 0:
        cx, cy = w // 2, h // 2
    else:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
    vertical = "upper" if cy < h / 2 else "lower"
    horizontal = "inner" if cx < w / 2 else "outer"
    return f"{vertical}-{horizontal} quadrant", (cx, cy)


# -------------------------------------------------------------
# 4) ANNOTATE
# -------------------------------------------------------------
def annotate_image(original_bgr: np.ndarray, work_mask: np.ndarray,
                   ratio_percent: float, region_desc: str,
                   dens_class: str, susp_idx: float) -> np.ndarray:
    mask_resized = cv2.resize(work_mask, (original_bgr.shape[1], original_bgr.shape[0]),
                              interpolation=cv2.INTER_NEAREST)

    overlay = original_bgr.copy()
    red = np.zeros_like(original_bgr)
    red[:, :, 2] = mask_resized
    annotated = cv2.addWeighted(overlay, 0.8, red, 0.35, 0)

    contours, _ = cv2.findContours(mask_resized, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        if cv2.contourArea(c) < MIN_COMPONENT_AREA:
            continue
        x, y, w, h = cv2.boundingRect(c)
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 0, 255), 2)

    M = cv2.moments(mask_resized, binaryImage=True)
    if M["m00"] > 0:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        cv2.circle(annotated, (cx, cy), 5, (0, 255, 0), -1)

    panel = annotated.copy()
    x0, y0, x1, y1 = 12, 12, 360, 150
    cv2.rectangle(panel, (x0, y0), (x1, y1), (0, 0, 0), -1)
    annotated = cv2.addWeighted(panel, 0.35, annotated, 0.65, 0)
    cv2.putText(annotated, f"Density: {ratio_percent:.1f}%", (22, 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.70, (255, 255, 255), 2)
    cv2.putText(annotated, f"Class: {dens_class}", (22, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    cv2.putText(annotated, f"Region: {region_desc}", (22, 115),
                cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2)
    return annotated


# -------------------------------------------------------------
# 5) SINGLE IMAGE ANALYSIS (base function)
# -------------------------------------------------------------
def analyze_image(image_path: Path):
    bgr = load_image_any(str(image_path))
    gray = preprocess(bgr)
    mask = segment_suspicious(gray)
    mask_main = largest_component(mask) if np.count_nonzero(mask) > 0 else mask

    ratio = ratio_percent_from_mask(mask)
    dens_class = density_class_from_ratio(ratio)
    susp_idx = suspicion_index(mask_main, ratio)
    region_desc, _ = centroid_and_quadrant(mask_main if np.count_nonzero(mask_main) else mask)

    annotated_img = annotate_image(bgr, mask_main, ratio, region_desc, dens_class, susp_idx)
    out_img_path = annotated_path(image_path)
    ensure_dir(ANNOTATED_DIR)
    cv2.imwrite(str(out_img_path), annotated_img)

    ensure_dir(REPORTS_DIR)
    tech_report = (
        f"File: {Path(image_path).name}\n"
        f"Suspicious area ratio: {ratio:.1f}%\n"
        f"Density class: {dens_class}\n"
        f"Suspicion index (0–100): {susp_idx:.1f}\n"
        f"Region (centroid-based): {region_desc}\n"
        f"Disclaimer: Automatic analysis for research only.\n"
    )
    out_report_path = save_report(Path(image_path).name, tech_report)

    # Save context
    global _last_analysis
    _last_analysis.update({
        "file": str(image_path),
        "ratio": ratio,
        "region": region_desc,
        "density": dens_class,
        "suspicion_index": susp_idx,
        "annotation_path": str(out_img_path),
        "report_path": str(out_report_path),
    })

    return ratio, region_desc, out_img_path, Path(out_report_path)


# -------------------------------------------------------------
# 6) MULTI-IMAGE SUPPORT
# -------------------------------------------------------------
def get_images(input_dir: str = "input") -> list[Path]:
    valid_ext = ('.png', '.jpg', '.jpeg', '.dcm')
    files = [Path(f) for f in Path(input_dir).iterdir() if f.suffix.lower() in valid_ext]
    return sorted(files, key=lambda x: x.stat().st_mtime)


def analyze_images(mode: str = "latest"):
    images = get_images()
    if not images:
        raise FileNotFoundError("No mammogram images found in input/")

    if mode == "first":
        selected = images[0]
    elif mode == "latest":
        selected = images[-1]
    else:
        raise ValueError("Mode must be 'first' or 'latest'.")

    return analyze_image(selected)


# -------------------------------------------------------------
# 7) EXPLANATION
# -------------------------------------------------------------
def explain_suspicious_zone():
    """Provide a textual explanation of the suspicious region from the last analysis."""
    if not _last_analysis["file"]:
        return "No previous analysis available to explain."

    ratio = _last_analysis["ratio"]
    region = _last_analysis["region"]
    dens = _last_analysis["density"]
    idx = _last_analysis["suspicion_index"]

    # Simple interpretive explanation
    if idx < 20:
        severity = "low suspicion — likely benign tissue pattern."
    elif idx < 50:
        severity = "moderate suspicion — area merits follow-up imaging."
    else:
        severity = "high suspicion — further diagnostic evaluation recommended."

    return (
        f"The suspicious region lies in the {region}, with a density class of {dens}. "
        f"The computed suspicion index is {idx:.1f}, indicating {severity}"
    )


def analyze_file(image_path: str) -> dict:
    """Wrapper used by the Streamlit app to analyze one file and return structured info."""
    ratio, region, annotated_path, report_path = analyze_image(Path(image_path))

    # Calcul de la densité et de l’indice de suspicion pour affichage
    dens_class = density_class_from_ratio(ratio)
    susp_idx = suspicion_index(cv2.imread(str(annotated_path), cv2.IMREAD_GRAYSCALE), ratio)

    # Déterminer la priorité en fonction de l’indice de suspicion
    if susp_idx < 20:
        priority = "Low"
    elif susp_idx < 50:
        priority = "Medium"
    else:
        priority = "High"

    interpretation = explain_suspicious_zone()
    recommendations = [
        "Follow up with a radiologist.",
        "Compare with previous mammograms.",
        "Schedule additional imaging if needed."
    ]

    return {
        "filename": Path(image_path).name,
        "suspicious_ratio": ratio,
        "density_class": dens_class,
        "region": region,
        "suspicion_index": susp_idx,
        "priority": priority,
        "interpretation": interpretation,
        "recommendations": recommendations,
    }

# -------------------------------------------------------------
# 8) CLI TEST
# -------------------------------------------------------------
if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "latest"
    r, reg, img_out, rep = analyze_images(mode=mode)
    print("Analysis completed for", mode)
    print("→ Ratio:", r, "| Region:", reg)
    print("→ Annotated:", img_out)
    print("→ Report:", rep)
    print("Explanation:", explain_suspicious_zone())
