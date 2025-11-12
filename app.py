# app.py
# Streamlit dashboard for your Mammography AI Assistant

import json
from pathlib import Path
from datetime import datetime
import streamlit as st
from PIL import Image
from analyser import analyze_file  # <-- uses your real function

# ====== Folder paths ======
ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "input"
OUTPUT_DIR = ROOT / "output"
ANNOTATED_DIR = OUTPUT_DIR / "annotated"
REPORTS_DIR = OUTPUT_DIR / "reports"
MEMORY_FILE = ROOT / "memory.json"

for p in [INPUT_DIR, ANNOTATED_DIR, REPORTS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

# ====== Utility functions ======
def load_memory():
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def save_memory(memory_list):
    try:
        MEMORY_FILE.write_text(json.dumps(memory_list, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def append_to_memory(entry: dict):
    mem = load_memory()
    mem.append({"role": "assistant", "content": entry})
    save_memory(mem)

def list_local_images():
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".dcm"}
    return sorted([p for p in INPUT_DIR.glob("*") if p.suffix.lower() in exts])

def read_report_for(stem: str) -> str | None:
    for ext in (".txt", ".md"):
        p = REPORTS_DIR / f"report_{stem}{ext}"
        if p.exists():
            try:
                return p.read_text(encoding="utf-8")
            except Exception:
                return None
    return None

# ====== Streamlit configuration ======
st.set_page_config(page_title="Mammography AI Assistant", layout="wide", page_icon="🩺")

# Sidebar — settings and upload
with st.sidebar:
    st.title("🩺 Mammography AI Assistant")
    st.caption("Clinical analysis support dashboard")
    lang = st.radio("Language / Langue", ["English", "Français"], index=0, key="lang")
    st.divider()

    # Upload
    st.subheader("📤 Upload")
    uploaded = st.file_uploader(
        "Drop a mammogram (JPG/PNG/DCM)",
        type=["jpg", "jpeg", "png", "bmp", "tif", "tiff", "dcm"],
    )
    if uploaded:
        dest = INPUT_DIR / uploaded.name
        with open(dest, "wb") as f:
            f.write(uploaded.getbuffer())
        st.success(f"Saved to input/: {uploaded.name}")
    st.divider()

    # Settings
    st.subheader("⚙️ Settings")
    st.number_input("Suspicion alert threshold", min_value=0, max_value=100, value=50, key="alert_threshold")
    st.checkbox("Auto-generate report on upload", value=True, key="auto_report")
    st.divider()
    st.caption("© Research use only. Not a diagnostic tool.")

# ====== Main Page ======
st.title("Mammography AI Dashboard" if st.session_state.lang == "English" else "Tableau de bord IA Mammographie")

tabs = st.tabs([
    "📁 Upload & Select" if st.session_state.lang == "English" else "📁 Importer & Sélectionner",
    "🧠 Analyze" if st.session_state.lang == "English" else "🧠 Analyser",
    "🖼️ Annotated" if st.session_state.lang == "English" else "🖼️ Annotée",
    "📄 Report" if st.session_state.lang == "English" else "📄 Rapport",
    "🕓 History" if st.session_state.lang == "English" else "🕓 Historique",
])

# --- Tab 1: Upload & Select ---
with tabs[0]:
    st.subheader("Select an image" if st.session_state.lang == "English" else "Sélectionnez une image")
    images = list_local_images()
    if images:
        names = [p.name for p in images]
        choice = st.selectbox("Choose an image", names, index=0, key="selected_image")
        info = Path(INPUT_DIR) / choice
        st.info(f"Selected: {choice}")
        try:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Original preview**" if st.session_state.lang == "English" else "**Aperçu original**")
                st.image(Image.open(info), use_container_width=True)
            with col2:
                ann_guess = ANNOTATED_DIR / f"annotated_{info.stem}.jpg"
                if ann_guess.exists():
                    st.markdown("**Latest annotated image**" if st.session_state.lang == "English" else "**Dernière image annotée**")
                    st.image(Image.open(ann_guess), use_container_width=True)
        except Exception as e:
            st.warning(f"Preview unavailable: {e}")
    else:
        st.warning("No images in input/. Use the sidebar to upload." if st.session_state.lang == "English" else "Aucune image trouvée dans input/. Importez-en une via la barre latérale.")

# --- Tab 2: Analyze ---
with tabs[1]:
    st.subheader("Run analysis" if st.session_state.lang == "English" else "Lancer l'analyse")
    selected_name = st.session_state.get("selected_image")
    if selected_name:
        img_path = INPUT_DIR / selected_name
        if st.button("Analyze selected image" if st.session_state.lang == "English" else "Analyser l'image sélectionnée"):
            with st.spinner("Analyzing..." if st.session_state.lang == "English" else "Analyse en cours..."):
                result = analyze_file(str(img_path))
            st.success("Analysis complete." if st.session_state.lang == "English" else "Analyse terminée.")
            # Display metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Suspicious ratio (%)", f"{result['suspicious_ratio']:.1f}")
            m2.metric("Density class", result["density_class"])
            m3.metric("Region", result["region"])
            m4.metric("Suspicion index", f"{result['suspicion_index']:.1f} ({result['priority']})")
            st.markdown("**Interpretation**" if st.session_state.lang == "English" else "**Interprétation**")
            st.write(result["interpretation"])
            # Recommendations
            st.markdown("**Recommendations**" if st.session_state.lang == "English" else "**Recommandations**")
            for r in result["recommendations"]:
                st.write("- " + r)
            append_to_memory({
                "summary": f"{datetime.now().strftime('%Y-%m-%d %H:%M')} — {result['filename']} → {result['suspicious_ratio']:.1f}% suspicious in {result['region']}",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
    else:
        st.info("Select or upload an image first." if st.session_state.lang == "English" else "Sélectionnez ou importez d'abord une image.")

# --- Tab 3: Annotated ---
with tabs[2]:
    st.subheader("Annotated image" if st.session_state.lang == "English" else "Image annotée")
    selected_name = st.session_state.get("selected_image")
    if selected_name:
        ann = ANNOTATED_DIR / f"annotated_{Path(selected_name).stem}.jpg"
        if ann.exists():
            st.image(Image.open(ann), use_container_width=True)
            st.download_button("Download annotated image", ann.read_bytes(), file_name=ann.name)
        else:
            st.info("No annotated image found yet. Run analysis first." if st.session_state.lang == "English" else "Aucune image annotée trouvée. Lancez d'abord l'analyse.")
    else:
        st.info("Select or upload an image first." if st.session_state.lang == "English" else "Sélectionnez ou importez d'abord une image.")

# --- Tab 4: Report ---
with tabs[3]:
    st.subheader("Structured report" if st.session_state.lang == "English" else "Rapport structuré")
    selected_name = st.session_state.get("selected_image")
    if selected_name:
        stem = Path(selected_name).stem
        rpt = read_report_for(stem)
        if rpt:
            st.markdown(rpt)
            rpt_path = REPORTS_DIR / f"report_{stem}.txt"
            st.download_button("Download report", rpt_path.read_bytes(), file_name=rpt_path.name, mime="text/plain")
        else:
            st.info("No report found yet. Run analysis to generate one." if st.session_state.lang == "English" else "Aucun rapport trouvé. Lancez l'analyse pour en générer un.")
    else:
        st.info("Select or upload an image first." if st.session_state.lang == "English" else "Sélectionnez ou importez d'abord une image.")

# --- Tab 5: History ---
with tabs[4]:
    st.subheader("Recent analyses" if st.session_state.lang == "English" else "Analyses récentes")
    mem = load_memory()
    if not mem:
        st.info("No history yet." if st.session_state.lang == "English" else "Aucun historique pour l'instant.")
    else:
        for i, entry in enumerate(mem[::-1][:20], 1):
            content = entry.get("content", {})
            summary = content.get("summary") if isinstance(content, dict) else str(content)
            ts = content.get("timestamp") if isinstance(content, dict) else ""
            st.write(f"**{i}.** {summary}")
            if ts:
                st.caption(ts)

# Footer
st.caption("⚠️ This AI-assisted analysis is for research and educational purposes only. Not a diagnostic tool.")
