"""
agent.py — Mammography AI Assistant (Advanced Optimized Version)
WITH FUNCTION CALLING SUPPORT & IMAGE DISPLAY + LAST-ANALYZED MEMORY
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Optional

from analyser import analyze_image, explain_suspicious_zone
from config import INPUT_DIR, ANNOTATED_DIR, REPORTS_DIR

# Optional email service
send_gmail = None
try:
    if os.path.exists("gmail_service.py"):
        from gmail_service import send_email as send_gmail
except Exception:
    send_gmail = None

# ============================================================
# IMAGE RETRIEVAL HELPERS
# ============================================================

def list_all_images():
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".dcm"}
    return sorted([p for p in INPUT_DIR.glob("*") if p.suffix.lower() in exts], key=os.path.getmtime)

def get_image_by_index(index: int) -> Optional[Path]:
    images = list_all_images()
    if 0 <= index < len(images):
        return images[index]
    return None

def get_image_by_position(text: str) -> Optional[Path]:
    """
    Understands:
    - "latest", "first", "second", "third", "fourth"
    - "image 3", "show 7", "the 12th", etc...
    """
    text = text.lower().strip()
    images = list_all_images()
    if not images:
        return None

    # Numeric index detection: "6", "image 12", "12th"
    match = re.search(r"\b(\d+)\b", text)
    if match:
        num = int(match.group(1))
        return get_image_by_index(num - 1)

    position_map = {
        "latest": -1, "last": -1,
        "first": 0,
        "second": 1,
        "third": 2,
        "fourth": 3,
        "fifth": 4,
        "sixth": 5,
        "seventh": 6,
        "eighth": 7
    }

    for key, idx in position_map.items():
        if key in text:
            if idx < 0:
                return images[-1]
            if idx < len(images):
                return images[idx]

    # default fallback → latest
    return images[-1]

# ============================================================
# FUNCTION CALLS IMPLEMENTATIONS
# ============================================================

def fc_analyze(image_path: Path) -> Dict:
    """Run analysis and return full structured output"""
    result = analyze_image(image_path)
    annotated = ANNOTATED_DIR / f"annotated_{image_path.stem}.jpg"

    return {
        "type": "analysis_result",
        "success": True,
        "filename": result["filename"],
        "original": str(image_path),
        "annotated": str(annotated),
        "suspicious_ratio": result["ratio"],
        "density_class": result["density_class"],
        "region": result["region"],
        "suspicion_index": result["suspicion_index"],
        "severity": "HIGH" if result["severe_case"] else "NORMAL",
        "message": f"Analysis complete for {result['filename']}"
    }

def fc_show_image(original_path: str, annotated_path: Optional[str]) -> Dict:
    """Return structure telling Streamlit to show the original image"""
    return {
        "type": "show_image",
        "success": True,
        "original": original_path,
        "annotated": annotated_path,
    }

def fc_show_last_annotated(last: Dict) -> Dict:
    """Return annotated image from last analysis"""
    return {
        "type": "show_image",
        "success": True,
        "original": last["original"],
        "annotated": last["annotated"],
    }

# ============================================================
# THE AGENT CLASS
# ============================================================

class Agent:

    def __init__(self):
        # Always store the last analyzed image:
        self.last_analyzed = None

    # --------------------------
    # MAIN MESSAGE PROCESSOR
    # --------------------------
    def process_message(self, messages: List[Dict], user_input: str):
        text = user_input.lower().strip()

        # ------------------------------
        # SHOW ANNOTATED / SHOW IMAGE
        # ------------------------------
        if "show" in text or "display" in text or "view" in text:

            # If user says "show annotated"
            if "annotated" in text or "processed" in text:
                if self.last_analyzed:
                    return messages, fc_show_last_annotated(self.last_analyzed)
                else:
                    return messages, "❌ No previous analysis found. Analyze an image first."

            # Else → show original image by position or index
            img = get_image_by_position(text)
            if not img:
                return messages, "❌ No matching image found."

            annotated = ANNOTATED_DIR / f"annotated_{img.stem}.jpg"
            annotated_path = str(annotated) if annotated.exists() else None

            return messages, fc_show_image(str(img), annotated_path)

        # ------------------------------
        # ANALYZE
        # ------------------------------
        if "analyze" in text or "analyse" in text or "scan" in text:

            img = get_image_by_position(text)
            if not img:
                return messages, "❌ No image found to analyze."

            # Run analysis:
            result = fc_analyze(img)

            # Store last analyzed image for later image display
            self.last_analyzed = {
                "filename": result["filename"],
                "original": result["original"],
                "annotated": result["annotated"]
            }

            # Format natural message instead of JSON
            severity = result["severity"]
            ratio = result["suspicious_ratio"]
            density = result["density_class"]
            region = result["region"]
            
            response = f"""
🔍 **Analysis Complete - {result['filename']}**

**Findings:**
- Suspicious area ratio: **{ratio}%**
- Density class: **{density}**
- Region: **{region}**
- Suspicion index: **{result['suspicion_index']:.1f}**
- Severity: **{severity}**

"""

            # Add email proposal for severe cases
            if severity == "HIGH" or ratio >= 50:
                response += f"""
🚨 **HIGH SEVERITY CASE - Patient Notification Recommended**

This case requires immediate follow-up due to:
- High suspicious area ratio ({ratio}%)
- {density}

**Would you like me to send a notification email to the patient for an additional appointment?**
Please respond with 'YES' to send the email or 'NO' to decline.
"""
            else:
                response += "✅ This case appears to be within normal parameters. No immediate action required."

            return messages, response

        # ------------------------------
        # EXPLAIN REGION
        # ------------------------------
        if "explain" in text and "region" in text:
            explanation = explain_suspicious_zone()
            return messages, f"**Region Explanation:**\n\n{explanation}"

        # ------------------------------
        # FALLBACK RESPONSE
        # ------------------------------
        return messages, (
            "🩺 **Mammography Analysis Assistant**\n\n"
            "I can help you with:\n"
            "• **Analyze images** - 'Analyze the latest mammogram' or 'Analyze image 3'\n"
            "• **View results** - 'Show annotated image' or 'Show image 2'\n"
            "• **Explain findings** - 'Explain the suspicious region'\n"
            "• **Patient notifications** - Automatic for high severity cases\n\n"
            "How can I assist you today?"
        )