# app.py — Updated with Assistant Chat Tab (ChatGPT-style)
# Upload moved from sidebar → inside chat (Option A)

import json
import os  # ← AJOUTER CET IMPORT MANQUANT
from pathlib import Path
from datetime import datetime
import streamlit as st
from PIL import Image

from analyser import analyze_file
from agent import Agent     # ← FIX: Use your real class name

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

# ------------------------------------------------------------
# SIDEBAR — KEEP SETTINGS ONLY (UPLOAD REMOVED for Option A)
# ------------------------------------------------------------
with st.sidebar:
    st.title("🩺 Mammography AI Assistant")
    st.caption("Clinical analysis support dashboard")

    # Language selector kept, but assistant ALWAYS answers in English
    lang = st.radio("Language / Langue", ["English", "Français"], index=0, key="lang")

    st.divider()
    st.subheader("⚙️ Settings")

    st.number_input("Suspicion alert threshold", min_value=0, max_value=100,
                    value=50, key="alert_threshold")

    st.checkbox("Auto-generate report on upload", value=True, key="auto_report")

    st.divider()
    st.caption("© Research use only. Not a diagnostic tool.")


# ------------------------------------------------------------
# MAIN PAGE
# ------------------------------------------------------------
st.title("Mammography AI Dashboard")

tabs = st.tabs([
    "🤖 Assistant",
    "📁 Upload & Select",
    "🧠 Analyze",
    "🖼️ Annotated",
    "📄 Report",
    "🕓 History",
    
])

# ------------------------------------------------------------
# TAB 1 — ASSISTANT (ChatGPT-style) – CORRIGÉ
# ------------------------------------------------------------
with tabs[0]:
    st.header("AI Assistant")
    st.caption("Chat + 📎 upload inside chat. English only.")

    # Keep chat history persistent
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # ✅ CORRECTION: Add email consent state
    if "awaiting_email_consent" not in st.session_state:
        st.session_state.awaiting_email_consent = False

    # --- Container pour la zone de chat ---
    chat_container = st.container()

    # --- Afficher les messages dans le container ---
    with chat_container:
        for entry in st.session_state.chat_history:
            if isinstance(entry["content"], dict) and entry["content"].get("type") == "show_image":
                # Handle image display from history
                st.chat_message("assistant").write("🖼️ Previously displayed image:")
                content = entry["content"]
                if content.get("original"):
                    st.image(
                        content["original"],
                        caption="Original Image (preview)",
                        width=350
                    )
                if content.get("annotated"):
                    st.image(
                        content["annotated"],
                        caption="Annotated Image (preview)", 
                        width=350
                    )
            else:
                # Normal text message
                st.chat_message(entry["role"]).write(entry["content"])

    # --- Zone de saisie et trombone SIMPLIFIÉE ---
    col1, col2 = st.columns([0.9, 0.1])
    
    with col1:
        user_msg = st.chat_input("How can I help? (English only)")
    
    with col2:
        st.write("")  # Espacement
        st.write("")
        if st.button("📎", key="attach_btn", use_container_width=True, help="Attach file"):
            st.session_state.trigger_upload = True

    # --- Uploader déclenché par le bouton 📎 ---
    if st.session_state.get("trigger_upload", False):
        uploaded_file = st.file_uploader(
            "Upload medical images",
            type=["jpg","jpeg","png","bmp","tif","tiff","dcm"],
            key="manual_upload",
            label_visibility="visible"
        )
        
        if uploaded_file:
            # Sauvegarder le fichier
            dest = INPUT_DIR / uploaded_file.name
            with open(dest, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Ajouter le message d'upload au chat
            upload_message = f"📎 File uploaded: {uploaded_file.name}"
            st.session_state.chat_history.append({"role": "user", "content": upload_message})
            
            # Réponse AI
            try:
                agent = Agent()
                updated_messages, bot_reply = agent.process_message(st.session_state.chat_history, f"User uploaded file: {uploaded_file.name}")
                
                # Mettre à jour l'historique
                st.session_state.chat_history = updated_messages
                st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
                
            except Exception as e:
                st.session_state.chat_history.append({"role": "assistant", "content": f"I've received the file {uploaded_file.name}. How would you like me to analyze it? (Error: {str(e)})"})
            
            st.session_state.trigger_upload = False
            st.rerun()

    # --- Gestion des messages utilisateur ---
    if user_msg:
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_msg})
        
        # ✅ CORRECTION: Gérer les réponses OUI/NON pour les emails
        if st.session_state.get("awaiting_email_consent", False):
            if user_msg.lower() in ["oui", "yes", "ok", "send", "envoie"]:
                # Envoyer l'email
                try:
                    # ✅ CORRECTION: Import send_gmail directly in app.py
                    from gmail_service import send_email as send_gmail
                    
                    success = send_gmail(
                        to_email="patient@example.com",  # Remplacer par vrai email
                        subject="Urgent Follow-Up Required - Mammography Results",
                        message_text=f"""
Dear Patient,

Following your recent mammogram, our analysis indicates the need for additional follow-up.

Please contact our radiology center as soon as possible to schedule an additional appointment for further evaluation.

Best regards,
Radiology Department
"""
                    )
                    if success:
                        st.session_state.chat_history.append({"role": "assistant", "content": "✅ Email sent successfully to the patient!"})
                    else:
                        st.session_state.chat_history.append({"role": "assistant", "content": "❌ Failed to send email. Please try again."})
                    
                except Exception as e:
                    error_msg = f"❌ Error sending email: {str(e)}"
                    # ✅ CORRECTION: Message spécial pour l'erreur Google verification
                    if "access_denied" in str(e) or "verification" in str(e).lower():
                        error_msg = "❌ Email service temporarily unavailable (Google verification in progress). Please contact the patient manually."
                    
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                
                st.session_state.awaiting_email_consent = False
                st.rerun()
            
            elif user_msg.lower() in ["non", "no", "stop"]:
                st.session_state.chat_history.append({"role": "assistant", "content": "✅ No email will be sent to the patient."})
                st.session_state.awaiting_email_consent = False
                st.rerun()
            else:
                st.session_state.chat_history.append({"role": "assistant", "content": "Please answer YES or NO to send the patient notification."})
                st.rerun()
        
        else:
            # AI response normale
            try:
                agent = Agent()
                updated_messages, bot_reply = agent.process_message(st.session_state.chat_history, user_msg)
                
                # ✅ CORRECTION: Handle image display responses
                if isinstance(bot_reply, dict) and bot_reply.get("type") == "show_image":
                    st.chat_message("assistant").write("🖼️ Displaying requested image:")
                    
                    if bot_reply.get("original"):
                        st.image(
                            bot_reply["original"],
                            caption="Original Image (preview)",
                            width=350
                        )
                    
                    if bot_reply.get("annotated"):
                        st.image(
                            bot_reply["annotated"],
                            caption="Annotated Image (preview)",
                            width=350
                        )
                    
                    # Save inside chat history
                    st.session_state.chat_history.append({
                        "role": "assistant", 
                        "content": {
                            "type": "show_image",
                            "original": bot_reply.get("original"),
                            "annotated": bot_reply.get("annotated")
                        }
                    })
                    
                    st.session_state.chat_history = updated_messages
                    st.rerun()
                    st.stop()
                
                # ✅ CORRECTION: Détecter si la réponse propose un email
                if isinstance(bot_reply, str) and "would you like me to send" in bot_reply.lower() and "email" in bot_reply.lower():
                    st.session_state.awaiting_email_consent = True
                
                st.session_state.chat_history = updated_messages
                st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
                
            except Exception as e:
                st.session_state.chat_history.append({"role": "assistant", "content": f"I encountered an error: {str(e)}"})
            
            st.rerun()
            
# ------------------------------------------------------------
# TAB 2 — UPLOAD & SELECT (still available here)
# ------------------------------------------------------------
with tabs[1]:
    st.subheader("Select an image")
    images = list_local_images()

    # MOVE upload here if user does not use chat tab
    upload_here = st.file_uploader(
        "Upload a mammogram (JPG / PNG / DCM)",
        type=["jpg", "jpeg", "png", "bmp", "tif", "tiff", "dcm"]
    )

    if upload_here:
        dest = INPUT_DIR / upload_here.name
        with open(dest, "wb") as f:
            f.write(upload_here.getbuffer())
        st.success(f"Saved to input/: {upload_here.name}")

    if images:
        names = [p.name for p in images]
        choice = st.selectbox("Choose an image", names, index=0, key="selected_image")
        info = Path(INPUT_DIR) / choice
        st.info(f"Selected: {choice}")

        try:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Original preview**")
                st.image(Image.open(info), use_container_width=True)
            with col2:
                ann_guess = ANNOTATED_DIR / f"annotated_{info.stem}.jpg"
                if ann_guess.exists():
                    st.markdown("**Latest annotated image**")
                    st.image(Image.open(ann_guess), use_container_width=True)
        except Exception as e:
            st.warning(f"Preview unavailable: {e}")

    else:
        st.warning("No images in input/.")


# ------------------------------------------------------------
# TAB 3 — ANALYZE
# ------------------------------------------------------------
with tabs[2]:
    st.subheader("Run analysis")
    selected_name = st.session_state.get("selected_image")

    if selected_name:
        img_path = INPUT_DIR / selected_name

        if st.button("Analyze selected image"):
            with st.spinner("Analyzing..."):
                result = analyze_file(str(img_path))

            st.success("Analysis complete.")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Suspicious ratio (%)", f"{result['suspicious_ratio']:.1f}")
            m2.metric("Density class", result["density_class"])
            m3.metric("Region", result["region"])
            m4.metric("Suspicion index", f"{result['suspicion_index']:.1f} ({result['priority']})")

            st.markdown("**Interpretation**")
            st.write(result["interpretation"])

            st.markdown("**Recommendations**")
            for r in result["recommendations"]:
                st.write("- " + r)

            append_to_memory({
                "summary": f"{datetime.now().strftime('%Y-%m-%d %H:%M')} — "
                           f"{result['filename']} → {result['suspicious_ratio']:.1f}% suspicious in {result['region']}",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })

    else:
        st.info("Select or upload an image first.")


# ------------------------------------------------------------
# TAB 4 — ANNOTATED (CORRECTED)
# ------------------------------------------------------------
with tabs[3]:
    st.subheader("Annotated Image")
    
    # Get ALL annotated images, not just the selected one
    annotated_files = list(ANNOTATED_DIR.glob("annotated_*"))
    
    if annotated_files:
        # Show the most recent annotated image by default
        latest_annotated = max(annotated_files, key=os.path.getctime)
        
        st.info(f"Showing: {latest_annotated.name}")
        
        try:
            # Display the annotated image
            st.image(Image.open(latest_annotated), use_container_width=True, 
                    caption=f"Annotated Image: {latest_annotated.name}")
            
            # Download button
            with open(latest_annotated, "rb") as f:
                st.download_button(
                    "📥 Download Annotated Image", 
                    f.read(), 
                    file_name=latest_annotated.name,
                    mime="image/jpeg"
                )
                
        except Exception as e:
            st.error(f"Error displaying annotated image: {e}")
            
        # Show all available annotated images
        if len(annotated_files) > 1:
            st.divider()
            st.subheader("All Annotated Images")
            for ann_file in sorted(annotated_files, key=os.path.getctime, reverse=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"• {ann_file.name}")
                with col2:
                    if st.button("View", key=f"view_{ann_file.name}"):
                        st.session_state.current_annotated = ann_file
                        st.rerun()
                        
    else:
        st.info("No annotated images found yet. Please run an analysis first.")


# ------------------------------------------------------------
# TAB 5 — REPORT
# ------------------------------------------------------------
with tabs[4]:
    st.subheader("Structured report")

    selected_name = st.session_state.get("selected_image")
    if selected_name:
        stem = Path(selected_name).stem
        rpt = read_report_for(stem)

        if rpt:
            st.markdown(rpt)
            rpt_path = REPORTS_DIR / f"report_{stem}.txt"
            st.download_button("Download report", rpt_path.read_bytes(), file_name=rpt_path.name)
        else:
            st.info("No report found.")
    else:
        st.info("Select or upload an image first.")


# ------------------------------------------------------------
# TAB 6 — HISTORY
# ------------------------------------------------------------
with tabs[5]:
    st.subheader("Recent analyses")
    mem = load_memory()

    if not mem:
        st.info("No history yet.")
    else:
        for i, entry in enumerate(mem[::-1][:20], 1):
            content = entry.get("content", {})
            summary = content.get("summary") if isinstance(content, dict) else str(content)
            ts = content.get("timestamp") if isinstance(content, dict) else ""
            st.write(f"**{i}.** {summary}")
            if ts:
                st.caption(ts)

# ------------------------------------------------------------
# Footer
# ------------------------------------------------------------
st.caption("⚠️ AI-assisted analysis for research only. Not a diagnostic tool.")