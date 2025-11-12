"""
agent.py — Radiologist-oriented Mammography AI Assistant
--------------------------------------------------------
This assistant supports the radiologist during screening by:
- Automatically analyzing mammogram images
- Highlighting areas of interest
- Generating structured pre-diagnostic summaries
- Maintaining a collegial, assistant-style tone
"""

import os
import json
import requests
import subprocess
import sys
import platform
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from analyser import analyze_image
from memory import add_text_message, add_report_message
from config import (
    INPUT_DIR,
    ANNOTATED_DIR,
    REPORTS_DIR,
    LLM_API_KEY as MISTRAL_API_KEY,
    LLM_MODEL as MISTRAL_MODEL,
    load_prompts,
)
from tools import ensure_dir, list_input_files


# -------------------------------------------------------------
# Load prompts
# -------------------------------------------------------------
try:
    prompts = load_prompts()
except Exception:
    prompts = {}


# -------------------------------------------------------------
# Conversational keywords
# -------------------------------------------------------------
GENERIC_GREETINGS = ["hi", "hello", "hey", "bonjour", "salut", "good morning", "good afternoon"]
GENERIC_QUESTIONS = ["how are you", "what's up", "ça va", "comment ça va", "how is it going"]


# -------------------------------------------------------------
# REPORT GENERATION RULES (internal only)
# -------------------------------------------------------------
"""
CRITICAL RULES:
• Never use markdown bold in section headers, only for key metrics
• Keep interpretation concise and clinical (1–2 sentences maximum)
• Recommendations must be actionable and appropriate for the finding severity
• Always include the disclaimer
• Use proper medical terminology but avoid alarmist language
• Base recommendations on these guidelines:
   - Low suspicion (<20): Routine screening follow-up
   - Moderate suspicion (20–50): Short-term follow-up or ultrasound consideration
   - High suspicion (>50): Targeted ultrasound and radiologist review
"""


# -------------------------------------------------------------
# Local fallback report generator
# -------------------------------------------------------------
def _local_report_template(filename, ratio_percent, density_class, suspicion_index, region_desc):
    """Structured fallback report — concise and clinical."""
    if suspicion_index < 20:
        priority = "Low (benign-appearing pattern)"
        recommendation = "Routine screening follow-up is appropriate."
        interpretation = "Findings consistent with benign-appearing fibroglandular tissue."
    elif suspicion_index < 50:
        priority = "Moderate (requires correlation with prior studies)"
        recommendation = "Short-term follow-up or targeted ultrasound may be considered."
        interpretation = "Focal asymmetry noted that warrants correlation with prior imaging."
    else:
        priority = "High (requires additional evaluation)"
        recommendation = "Targeted ultrasound and radiologist review recommended."
        interpretation = "Significant opacity identified that requires further evaluation."

    report_text = (
        f"🩻 Automated analysis for {filename}\n\n"
        f"Quantitative summary:\n"
        f"- Suspicious area ratio: *{ratio_percent:.1f}%*\n"
        f"- Density class: *{density_class}*\n"
        f"- Region of interest: *{region_desc}*\n"
        f"- Suspicion index (0–100): *{suspicion_index:.1f} ({priority})*\n\n"
        f"Interpretation: {interpretation}\n\n"
        f"Recommendations:\n"
        f"- {recommendation}\n"
        f"- Correlate with prior studies when available.\n\n"
        "Disclaimer: This AI-generated report assists your diagnostic workflow. "
        "Final interpretation remains under your clinical judgment."
    )

    ensure_dir(REPORTS_DIR)
    report_path = REPORTS_DIR / f"{Path(filename).stem}_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    return report_text


# -------------------------------------------------------------
# Mistral (LLM) or fallback report generator
# -------------------------------------------------------------
def generate_report(filename, ratio_percent, density_class, suspicion_index, region_desc):
    """Generate structured clinical report using Mistral API or fallback."""
    system_prompt = prompts.get("system_prompt", "")
    prompt_payload = (
        f"{system_prompt}\n"
        f"File analyzed: {filename}\n"
        f"Suspicious area ratio: {ratio_percent:.1f}%\n"
        f"Density class: {density_class}\n"
        f"Region: {region_desc}\n"
        f"Suspicion index (0–100): {suspicion_index:.1f}\n\n"
        "Generate a structured radiology report summary addressed to the radiologist. "
        "Keep interpretation concise (1–2 sentences) and recommendations actionable."
    )

    if not MISTRAL_API_KEY:
        return _local_report_template(filename, ratio_percent, density_class, suspicion_index, region_desc)

    headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": MISTRAL_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt_payload},
        ],
        "temperature": 0.2,
        "max_tokens": 600,
    }

    try:
        response = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=data, timeout=8)
        if response.status_code == 200:
            res_json = response.json()
            text = (
                res_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                or "Report unavailable (unexpected API format)."
            )
            report_text = text.strip()
        else:
            report_text = _local_report_template(filename, ratio_percent, density_class, suspicion_index, region_desc)
            report_text += f"\n\n[⚠️ API error {response.status_code}]"
    except Exception as e:
        report_text = _local_report_template(filename, ratio_percent, density_class, suspicion_index, region_desc)
        report_text += f"\n\n[⚠️ API request failed: {e}]"

    ensure_dir(REPORTS_DIR)
    report_path = REPORTS_DIR / f"{Path(filename).stem}_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    return report_text


# -------------------------------------------------------------
# Extended commands handler
# -------------------------------------------------------------
def handle_extended_commands(messages, user_input: str):
    """Handle extended commands like 'analyze first/second/latest'."""
    text = user_input.strip().lower()

    if "analyze" in text or "analyse" in text:
        from analyser import get_images
        try:
            images = get_images()
            if not images:
                raise FileNotFoundError("No mammogram images found in the input folder.")

            if "first" in text:
                selected = images[0]
            elif "second" in text or "2nd" in text:
                selected = images[1] if len(images) >= 2 else None
            elif "third" in text or "3rd" in text:
                selected = images[2] if len(images) >= 3 else None
            else:
                selected = images[-1]

            if selected is None:
                raise IndexError("Not enough images available.")

            ratio, region, annotated_path, report_path = analyze_image(selected)

            if ratio < 5:
                density_class = "A – Almost entirely fatty"
            elif ratio < 15:
                density_class = "B – Scattered fibroglandular"
            elif ratio < 35:
                density_class = "C – Heterogeneously dense"
            else:
                density_class = "D – Extremely dense"

            suspicion_index = round(min(100, ratio * 2.1 + 5), 1)

            report_text = generate_report(selected.name, ratio, density_class, suspicion_index, region)

            response = (
                f"🩻 Full AI-Generated Report for {selected.name}\n\n"
                f"{report_text}\n\n"
                f"📄 Report saved at: {report_path}\n"
                f"🖼️ Annotated image: {annotated_path}\n\n"
                "⚠️ *AI-assisted analysis — not a diagnostic result.*"
            )
            return add_text_message(messages, "assistant", response), response

        except (FileNotFoundError, IndexError) as e:
            response = f"❌ {e}"
            return add_text_message(messages, "assistant", response), response
        except Exception as e:
            response = f"❌ Error during analysis: {e}"
            return add_text_message(messages, "assistant", response), response

    return None, None


# -------------------------------------------------------------
# Image selection logic
# -------------------------------------------------------------
def get_target_images(user_input: str) -> List[Path]:
    """Identify which mammogram(s) to analyze."""
    text = user_input.lower().strip()
    images = []

    if "all" in text or "each" in text or "every" in text:
        images = list(INPUT_DIR.glob("*.png")) + list(INPUT_DIR.glob("*.jpg")) + list(INPUT_DIR.glob("*.dcm"))
    elif "latest" in text or "last" in text or "recent" in text:
        image_files = sorted(
            list(INPUT_DIR.glob("*.png")) + list(INPUT_DIR.glob("*.jpg")) + list(INPUT_DIR.glob("*.dcm")),
            key=os.path.getmtime,
        )
        if image_files:
            images = [image_files[-1]]
    else:
        for file in INPUT_DIR.glob("*"):
            if file.name.lower() in text:
                images = [file]
                break

    if not images:
        image_files = sorted(
            list(INPUT_DIR.glob("*.png")) + list(INPUT_DIR.glob("*.jpg")) + list(INPUT_DIR.glob("*.dcm")),
            key=os.path.getmtime,
        )
        if image_files:
            images = [image_files[-1]]

    return images


# -------------------------------------------------------------
# Main conversational Agent
# -------------------------------------------------------------
class Agent:
    def __init__(self, console=None):
        self.console = console
        self.last_ratio = None
        self.last_region = None
        self.last_image = None

    def process_message(self, messages: List[Dict], user_input: str) -> Tuple[List[Dict], str]:
        text = user_input.strip().lower()

        extended_messages, extended_response = handle_extended_commands(messages, user_input)
        if extended_messages is not None:
            return extended_messages, extended_response

        if any(greet in text for greet in GENERIC_GREETINGS):
            response = (
                "👋 Hello Doctor. I'm your mammography analysis assistant.\n\n"
                "I can:\n"
                "• Analyze your recent mammogram images\n"
                "• Identify suspicious dense areas\n"
                "• Generate structured reports\n"
                "• Display annotated results\n\n"
                "Would you like me to analyze an image or show your latest annotation?"
            )
            return add_text_message(messages, "assistant", response), response

        if any(q in text for q in GENERIC_QUESTIONS):
            response = "✅ All modules are operational. Ready to process your next case."
            return add_text_message(messages, "assistant", response), response

        if any(k in text for k in ["show", "open", "display", "latest image", "view", "visualize", "/show"]):
            if not self.last_image or not Path(self.last_image).exists():
                annotated_files = sorted(ANNOTATED_DIR.glob("annotated_*.jpg"))
                if not annotated_files:
                    response = "❌ No annotated image found. Please analyze a mammogram first."
                    return add_text_message(messages, "assistant", response), response
                self.last_image = annotated_files[-1]

            image_path = Path(self.last_image)
            response = f"🖼️ Opening {image_path.name} in viewer..."
            try:
                if platform.system() == "Darwin":
                    subprocess.Popen(["open", "-a", "Preview", str(image_path)])
                elif platform.system() == "Windows":
                    os.startfile(image_path)
                else:
                    subprocess.Popen(["xdg-open", str(image_path)])
                response += "\n\n✅ Viewer launched successfully."
            except Exception as e:
                response += f"\n\n❌ Error opening viewer: {e}"

            return add_text_message(messages, "assistant", response), response

        if any(word in text for word in ["analyze", "analyse", "scan", "review"]):
            image_paths = get_target_images(user_input)
            if not image_paths:
                response = "❌ No mammogram images found in the input folder."
                return add_text_message(messages, "assistant", response), response

            analysis_results = []
            for image_path in image_paths:
                try:
                    ratio, region, annotated_path, report_path = analyze_image(image_path)

                    if ratio < 5:
                        density_class = "A – Almost entirely fatty"
                    elif ratio < 15:
                        density_class = "B – Scattered fibroglandular"
                    elif ratio < 35:
                        density_class = "C – Heterogeneously dense"
                    else:
                        density_class = "D – Extremely dense"

                    suspicion_index = round(min(100, ratio * 2.1 + 5), 1)
                    report_text = generate_report(image_path.name, ratio, density_class, suspicion_index, region)

                    analysis_results.append({
                        "filename": image_path.name,
                        "report": report_text,
                        "annotated_path": annotated_path,
                        "report_path": report_path,
                    })

                    self.last_ratio = ratio
                    self.last_region = region
                    self.last_image = annotated_path

                except Exception as e:
                    analysis_results.append({"error": f"❌ Error analyzing {image_path.name}: {e}"})

            if not analysis_results:
                response = "❌ No analysis could be performed."
                return add_text_message(messages, "assistant", response), response

            response = f"✅ **Analysis completed for {len(analysis_results)} image(s).**\n\n"
            for result in analysis_results:
                if "error" in result:
                    response += f"{result['error']}\n\n"
                else:
                    response += (
                        f"{result['report']}\n\n"
                        f"📄 Report saved at: {result['report_path']}\n"
                        f"🖼️ Annotated image: {result['annotated_path']}\n\n"
                        "---\n\n"
                    )

            response += "⚠️ *This AI-assisted analysis supports but does not replace radiological expertise.*"
            return add_report_message(messages, "assistant", {"summary": response}), response

        response = (
            "🩺 **Mammography Analysis Assistant**\n\n"
            "I can assist you with:\n"
            "• **Image analysis** — 'Analyze the latest mammogram'\n"
            "• **Visualization** — 'Show me the annotated image' or '/show'\n"
            "• **Reports** — Automatically saved in the output/reports folder\n\n"
            "How can I help you today?"
        )
        return add_text_message(messages, "assistant", response), response
