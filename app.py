# ---------------- app.py ----------------
import streamlit as st
import sqlite3
import pandas as pd
from fpdf import FPDF
import zipfile, io, base64, time, os 
from pathlib import Path
from datetime import datetime
import bcrypt

# utils
from utils.translator import detect_and_translate, SUPPORTED_LANGS
from utils.ocr import extract_text_from_image, draw_bounding_boxes, export_ocr_pdf
from utils.speech import speech_to_text, text_to_speech_bytes, SUPPORTED_SPEECH_LANGS

try:
    from audiorecorder import audiorecorder
    AUDIORECORDER_AVAILABLE = True
except Exception:
    audiorecorder = None
    AUDIORECORDER_AVAILABLE = False

# ---------------- CONFIG ----------------
st.set_page_config(page_title="🌍 Linguistix App", page_icon="🌍", layout="wide")

APP_DIR = Path(__file__).parent
DB_FILE = APP_DIR / "history.db"

# Basic logging
import logging
LOG_FILE = APP_DIR / "app.log"
logging.basicConfig(filename=str(LOG_FILE), level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Set session state defaults for safety
for key, default in [
    ("last_input", ""),
    ("input_text", ""),
    ("last_translated", ""),
    ("last_detected", ""),
    ("output_text", ""),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ---------------- CSS STYLING (UPDATED TOPBAR + EXAMPLES) ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
:root{ --bg:#F7F8FA; --panel:#FFFFFF; --accent:#5EBEC4; --accent-2:#F92C85; --muted:#98A1B3; --navy:#0F172A; }
body, .stApp { font-family: 'Poppins', sans-serif; background: var(--bg); color:var(--navy); }

/* topbar */
.topbar { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:10px 6px 14px 6px; }
.logo { display:flex; gap:12px; align-items:center; }
.logo svg { width:44px; height:44px; }
.logo-badge { font-weight:700; color:var(--panel); padding:6px 10px; border-radius:999px;
  background: linear-gradient(90deg,var(--accent),#8FD6E0); box-shadow:0 6px 18px rgba(15,23,42,0.06);}
.app-title { font-weight:700; color:var(--navy); font-size:20px; letter-spacing:0.2px; }
.slogan { color:var(--muted); font-size:13px; margin-top:2px; }

/* little animation to make header lively */
@keyframes float { 0% {transform: translateY(0);} 50% {transform: translateY(-4px);} 100% {transform: translateY(0);} }
.logo svg { animation: float 4s ease-in-out infinite; transform-origin: center; }

/* example buttons row */
.examples { margin-top:10px; display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.example-btn { background:#fff; border-radius:8px; padding:6px 10px; box-shadow:0 6px 18px rgba(15,23,42,0.03); font-size:13px; color:var(--navy); cursor:pointer; border:1px solid rgba(15,23,42,0.03); }
.example-hint { color:var(--muted); font-size:12px; margin-left:8px; }

/* responsive */
@media (max-width:900px){ .topbar { flex-direction:column; align-items:flex-start; gap:8px; } }
</style>
<style>
.panel {
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 2px 16px rgba(94,190,196,0.08);
    padding: 24px 18px 18px 18px;
    margin-bottom: 18px;
    border: 1px solid #e6f2f3;
}
.section-title {
    font-size: 1.3rem;
    font-weight: 600;
    color: #5EBEC4;
    margin-bottom: 12px;
    letter-spacing: 0.5px;
    display: flex;
    align-items: center;
    gap: 8px;
}
</style>                                        
<div class="topbar">
  <div class="logo">
    <!-- friendly globe + chat bubble logo -->
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <circle cx="12" cy="12" r="10" stroke="#5EBEC4" stroke-width="1.2" fill="#E9FBFC"/>
      <path d="M3 12h18M12 3c2 2.5 2 16 0 18M6 6c2.2 3 2.2 13 0 18M18 6c-2.2 3-2.2 13 0 18" stroke="#7DD7D9" stroke-width="0.9" stroke-linecap="round"/>
      <g transform="translate(16,16)"><path d="M0 0 l4 2 v-4 z" fill="#F92C85" opacity="0.95"/></g>
    </svg>
    <div>
      <div style="display:flex;align-items:center;gap:8px">
        <div class="app-title">Linguistix</div>
        <div class="logo-badge">Local • Fast</div>
      </div>
      <div class="slogan">Translate faster. Speak clearer. Your words, every language.</div>
    </div>
  </div>

  <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;">
    <div style="display:flex;gap:10px;align-items:center;">
      <div style="font-size:13px;color:var(--muted)">Two-column translator • offline history</div>
      <div style="font-size:12px;color:var(--muted);background:#fff;padding:6px;border-radius:8px;border:1px solid rgba(15,23,42,0.03)">Tip: Ctrl+Enter to Translate</div>
    </div>
    <div style="font-size:12px;color:var(--muted)">Try quick examples below — click to populate input</div>
  </div>
</div>
""", unsafe_allow_html=True)

# quick examples (fills the input area)
examples = [
    ("Greeting", "Hello — how are you?"),
    ("Request", "Can you translate this to Spanish, please?"),
    ("Directions", "Where is the nearest cafe?"),
    ("Short Bio", "I am a software developer from India."),
]
st.write("")  # small spacer
cols = st.columns([1,5,6,6,6,2])
cols[0].markdown("")  # spacer
for i, (label, text) in enumerate(examples, start=1):
    if cols[i].button(f"{label}"):
        # set both keys used for prefill and component state to be safe
        st.session_state["last_input"] = text
        st.session_state["input_text"] = text
        # optional: focus UI by rerunning so text_area shows the example
        st.rerun()
cols[-1].markdown("<div class='example-hint'>Examples</div>", unsafe_allow_html=True)
# ...existing code...

# ---------------- DB HELPERS ----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    # Add users table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            password_hash TEXT
        )
        """
    )
    # Add user_id to history
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT,
            type TEXT, 
            detected_lang TEXT,
            target_lang TEXT,
            input TEXT,
            output TEXT,
            extra BLOB,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    conn.commit()
    conn.close()

init_db() 

conn = sqlite3.connect(DB_FILE)

# --- AUTH HELPERS ---
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def get_user(username):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash FROM users WHERE username=?", (username,))
    user = cur.fetchone()
    conn.close()
    return user  # (id, username, password_hash) or None

def create_user(username, email, password):
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        pw_hash = hash_password(password)
        cur.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)", (username, email, pw_hash))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    
def save_history(entry_type, input_text, detected_lang, target_lang, output_text, extra_blob=None):
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        ts = datetime.utcnow().isoformat()
        user_id = st.session_state.get("user_id")  # Set this after login
        cur.execute(
            "INSERT INTO history (user_id, timestamp, type, detected_lang, target_lang, input, output, extra) VALUES (?,?,?,?,?,?,?,?)",
            (user_id, ts, entry_type, detected_lang, target_lang, input_text, output_text, extra_blob),
        )
        conn.commit()
        conn.close()
    except Exception:
        logging.exception("save_history failed")

@st.cache_data
def load_history_df():
    try:
        conn = sqlite3.connect(DB_FILE)
        user_id = st.session_state.get("user_id")
        df = pd.read_sql_query(
            "SELECT * FROM history WHERE user_id=? ORDER BY id DESC",
            conn,
            params=(user_id,)
        )
        conn.close()
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).astype(str)
        return df
    except Exception:
        logging.exception("load_history_df failed")
        return pd.DataFrame(columns=["id","timestamp","type","detected_lang","target_lang","input","output"])

def clear_history():
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        user_id = st.session_state.get("user_id")
        cur.execute("DELETE FROM history WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()
    except Exception:
        logging.exception("clear_history failed")

# ---------------- PDF EXPORT ----------------
def export_history_pdf(df, filename="translation_history.pdf"):
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("helvetica", "B", 14)  # changed from Arial
        pdf.cell(0, 10, "Translation History", ln=True, align="C")
        pdf.ln(8)
        pdf.set_font("helvetica", size=11)  # changed from Arial
        for _, row in df.iterrows():
            ts = row.get("timestamp", "")
            ttype = row.get("type", "unknown")
            detected = row.get("detected_lang", "")
            target = row.get("target_lang", "")
            input_text = (row.get("input") or "")[:800]
            output_text = (row.get("output") or "")[:800]
            pdf.multi_cell(0, 7, f"{ts} | {ttype} | {detected} -> {target}")
            pdf.multi_cell(0, 7, f"Input: {input_text}")
            pdf.multi_cell(0, 7, f"Output: {output_text}")
            pdf.ln(4)
        pdf.output(str(APP_DIR / filename))
        return str(APP_DIR / filename)
    except Exception:
        logging.exception("export_history_pdf failed")
        return None

def export_history_pdf_bytes(df):
    try:
        buf = io.BytesIO()
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("helvetica", "B", 14)  # changed from Arial
        pdf.cell(0, 10, "Translation History", ln=True, align="C")
        pdf.ln(8)
        pdf.set_font("helvetica", size=11)  # changed from Arial
        for _, row in df.iterrows():
            ts = row.get("timestamp", "")
            ttype = row.get("type", "unknown")
            detected = row.get("detected_lang", "")
            target = row.get("target_lang", "")
            input_text = (row.get("input") or "")[:800]
            output_text = (row.get("output") or "")[:800]
            pdf.multi_cell(0, 7, f"{ts} | {ttype} | {detected} -> {target}")
            pdf.multi_cell(0, 7, f"Input: {input_text}")
            pdf.multi_cell(0, 7, f"Output: {output_text}")
            pdf.ln(4)
        pdf.output(buf, 'F')  # changed from pdf.output(buf)
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        logging.exception("export_history_pdf_bytes failed")
        return b""
    
# ---------------- APP TITLE ----------------
st.title("🌍 Linguistix App - Modern Translator")
sidebar = st.sidebar
sidebar.image("https://img.icons8.com/color/96/000000/language.png", width=64)
sidebar.markdown("### 🌟 Welcome to Linguistix!")
sidebar.markdown("---")
with sidebar.expander("ℹ️ About this app", expanded=False):
    sidebar.write("Linguistix is your all-in-one translation, OCR, and speech tool. Secure, fast, and local!")
sidebar.header("App Info")
sidebar.markdown("""
- Upload image/audio or type text
- History saved in `history.db`
""")

sidebar.markdown("**Supported text languages:**")
sidebar.write(", ".join([f"{k} ({v})" for k, v in SUPPORTED_LANGS.items()]))

tabs = st.tabs(["📝 Text", "🎤 Speech", "🖼️ Image OCR", "📜 History"])

# --- LOGIN/SIGNUP UI ---
def login_ui():
    st.sidebar.subheader("🔐 Login / Signup")
    auth_mode = st.sidebar.radio("Choose action", ["Login", "Sign Up"])
    username = st.sidebar.text_input("Username", key="auth_username")
    password = st.sidebar.text_input("Password", type="password", key="auth_password")
    if auth_mode == "Sign Up":
        email = st.sidebar.text_input("Email", key="auth_email")
        if st.sidebar.button("Sign Up"):
            if not username or not password or not email:
                st.sidebar.warning("Fill all fields.")
            elif get_user(username):
                st.sidebar.error("Username already exists.")
            else:
                if create_user(username, email, password):
                    st.sidebar.success("Account created! Please log in.")
                else:
                    st.sidebar.error("Signup failed.")
    else:
        if st.sidebar.button("Login"):
            user = get_user(username)
            if user and check_password(password, user[2]):
                st.session_state["user_id"] = user[0]
                st.session_state["username"] = user[1]
                st.sidebar.success(f"Welcome, {user[1]}!")
                st.rerun()
            else:
                st.sidebar.error("Invalid credentials.")

def logout_ui():
    if st.sidebar.button("Logout"):
        for k in ["user_id", "username"]:
            st.session_state.pop(k, None)
        st.rerun()

# --- Require login before showing app ---
if "user_id" not in st.session_state:
    login_ui()
    st.stop()
else:
    st.sidebar.markdown(f"**Logged in as:** {st.session_state['username']}")
    logout_ui()

# ---------------- TEXT TAB ----------------
with tabs[0]:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📝 Text Translation</div>', unsafe_allow_html=True)

    # language selectors + swap
    cols = st.columns([5,1,5])
    with cols[0]:
        src_lang = st.selectbox(
            "From",
            options=["auto"] + list(SUPPORTED_LANGS.keys()),
            format_func=lambda x: "Detect language" if x == "auto" else SUPPORTED_LANGS[x],
            key="src_lang",
            help="Select source language or 'Detect language'"
        )
    with cols[1]:
        if st.button("⇄", key="swap_langs"):
            # swap the selected languages (auto stays allowed)
            a = st.session_state.get("src_lang", "auto")
            b = st.session_state.get("target_lang", list(SUPPORTED_LANGS.keys())[0])
            st.session_state["src_lang"] = b
            st.session_state["target_lang"] = a if a != "auto" else b
            st.rerun() 
    with cols[2]:
        target_lang = st.selectbox("To", list(SUPPORTED_LANGS.keys()), format_func=lambda x: SUPPORTED_LANGS[x], key="target_lang")

    # main two-panel translator layout
    c1, c2, c3 = st.columns([5,0.4,5])  # middle narrow col for visual spacing
    with c1:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        input_text = st.text_area("Input", value=st.session_state.get("last_input",""), height=260, key="input_text", placeholder="Type or paste text here...")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.write("")  # spacer column
    with c3:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        output_placeholder = st.empty()
        output_area = st.text_area("Translation", value="", height=260, key="output_text", disabled=True)
        # actions: translate / tts / copy / download
        action_cols = st.columns([1,1,1,1])
        with action_cols[0]:
            if st.button("Translate", key="translate_main"):
                if not input_text or not input_text.strip():
                    st.warning("Please enter text to translate.")
                else:
                    with st.spinner("Translating..."):
                        translated, detected = detect_and_translate(input_text, target_lang)
                    st.session_state["last_input"] = input_text
                    st.session_state["last_translated"] = translated
                    st.session_state["last_detected"] = detected
                    output_area = st.empty()
                    output_area.text_area("Translation", value=translated, height=260, disabled=True, key="translated_result_area")
                    st.markdown(f'<div class="detected">Detected: <strong>{detected}</strong></div>', unsafe_allow_html=True)
                    save_history("text", input_text, detected, target_lang, translated)
                    st.cache_data.clear()
        with action_cols[1]:
            if st.button("🔊 TTS", key="tts_button"):
                txt = st.session_state.get("last_translated", "")
                if txt:
                    try:
                        audio_bytes = text_to_speech_bytes(txt, lang=target_lang)
                        st.audio(audio_bytes, format="audio/mp3")
                        st.download_button("Download Audio", data=audio_bytes, file_name="translation.mp3", mime="audio/mpeg")
                    except Exception as e:
                        st.error(f"TTS failed: {e}")
                else:
                    st.info("Translate text first.")
        with action_cols[2]:
            # copy via small downloadable .txt fallback
            if st.button("Copy", key="copy_button"):
                txt = st.session_state.get("last_translated","")
                if txt:
                    st.write("Select and copy the translation (or download).")
                else:
                    st.info("Translate text first.")
        with action_cols[3]:
            txt = st.session_state.get("last_translated","")
            if txt:
                txt_bytes = txt.encode("utf-8")
                st.download_button("Download", data=txt_bytes, file_name="translation.txt", mime="text/plain")
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------- SPEECH TAB ----------------
with tabs[1]:
    st.subheader("🎤 Speech Translation")
    st.markdown("Upload an audio file (wav/mp3/m4a) or record in-browser.")

    audio_file = st.file_uploader("Upload an audio file", type=["wav","mp3","m4a"])
    recorded_audio = None
    if AUDIORECORDER_AVAILABLE:
        try:
            recorded_audio = audiorecorder("Record", "Stop")
        except Exception:
            st.info("In-browser recorder not available. Upload audio instead.")
    else:
        st.info("In-browser recorder not installed. Install: `pip install streamlit-audiorecorder` or upload audio files.")

    target_lang_speech = st.selectbox("Translate to:", list(SUPPORTED_LANGS.keys()), format_func=lambda x: SUPPORTED_LANGS[x], key="speech_target")
    tts_speech = st.checkbox("🔊 Convert translation to speech (TTS) - speech tab")

    if st.button("Transcribe & Translate", key="translate_speech_btn"):
        file_obj = None
        # normalize recorded_audio to a file-like object if present
        if recorded_audio:
            try:
                if isinstance(recorded_audio, (bytes, bytearray)):
                    file_obj = io.BytesIO(recorded_audio)
                elif hasattr(recorded_audio, "getvalue"):
                    file_obj = io.BytesIO(recorded_audio.getvalue())
                else:
                    # fallback: try to convert to bytes
                    file_obj = io.BytesIO(bytes(recorded_audio))
            except Exception:
                file_obj = None
        elif audio_file:
            file_obj = audio_file
        else:
            st.warning("Please record or upload an audio file.")

        if file_obj:
            with st.spinner("Transcribing audio..."):
                try:
                    transcript = speech_to_text(file_obj)
                except Exception as e:
                    st.error(f"Speech -> text failed: {e}")
                    transcript = ""
            if transcript:
                st.write("**Transcribed:**", transcript)
                with st.spinner("Translating..."):
                    translated, detected = detect_and_translate(transcript, target_lang_speech)
                st.success(f"Translated ({SUPPORTED_LANGS[target_lang_speech]}):")
                st.write(translated)
                save_history("speech", transcript, detected, target_lang_speech, translated)
                st.cache_data.clear()
                if tts_speech:
                    try:
                        audio_bytes = text_to_speech_bytes(translated, lang=target_lang_speech)
                        st.audio(audio_bytes, format="audio/mp3")
                        st.download_button("📥 Download Audio", data=audio_bytes, file_name="speech_translation.mp3", mime="audio/mpeg")
                    except Exception as e:
                        st.error(f"TTS failed: {e}")

# ---------------- IMAGE OCR TAB ----------------
with tabs[2]:
    st.subheader("🖼️ OCR - Extract & Translate")
    image_files = st.file_uploader("Upload images", type=["png","jpg","jpeg"], accept_multiple_files=True)
    target_lang_ocr = st.selectbox("Translate to:", list(SUPPORTED_LANGS.keys()), format_func=lambda x: SUPPORTED_LANGS[x], key="ocr_target")
    if st.button("Extract & Translate (Images)", key="translate_images_btn"):
        if not image_files:
            st.warning("Please upload at least one image.")
        else:
            translated_images = []
            ocr_results = []
            for idx, image_file in enumerate(image_files):
                with st.spinner(f"Processing image {idx+1}/{len(image_files)}..."):
                    extracted, boxes = extract_text_from_image(image_file)
                st.write(f"Extracted text: {extracted}")
                st.write(extracted or "*No text detected*")
                translated, detected = detect_and_translate(extracted, target_lang_ocr)
                st.success(f"Translated ({SUPPORTED_LANGS[target_lang_ocr]}):")
                st.write(translated or "*—*")
                save_history("image", extracted, detected, target_lang_ocr, translated)

                translated_boxes = []
                for bbox, text in boxes:
                    ttxt, _ = detect_and_translate(text, target_lang_ocr)
                    translated_boxes.append(ttxt)
                img_with_boxes = draw_bounding_boxes(image_file.getvalue(), boxes, translated_boxes)
                col1, col2 = st.columns(2)
                with col1: st.image(image_file, caption=f"Original {idx+1}", width=350)
                with col2: st.image(img_with_boxes, caption=f"Translated {idx+1}", width=350)

                img_bytes = io.BytesIO()
                img_with_boxes.save(img_bytes, format="PNG")
                translated_images.append((f"translated_{idx+1}.png", img_bytes.getvalue()))
                ocr_results.append({"original_img": image_file.getvalue(), "translated_img": img_bytes.getvalue(), "extracted": extracted, "translated": translated})
                st.divider()

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for fname, data in translated_images:
                    zipf.writestr(fname, data)
            zip_buffer.seek(0)
            st.download_button("📥 Download Translated Images (ZIP)", data=zip_buffer, file_name="translated_images.zip", mime="application/zip")

            if ocr_results:
                pdf_path = export_ocr_pdf(ocr_results, output_path=str(APP_DIR / "ocr_report.pdf"))
                with open(pdf_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                href = f'<a href="data:application/pdf;base64,{b64}" download="ocr_report.pdf">📥 Download OCR Report (PDF)</a>'
                st.markdown(href, unsafe_allow_html=True)

# ---------------- HISTORY TAB ----------------
with tabs[3]:
    st.subheader("📜 Translation History")
    df = load_history_df()
    if df.empty:
        st.info("No history found yet.")
    else:
        st.markdown("**Filters**")
        cols = st.columns([2,2,2])
        with cols[0]:
            ft_type = st.selectbox("Type", options=["All"] + sorted(df["type"].unique().tolist()))
        with cols[1]:
            ft_source = st.text_input("Search text contains...")
        with cols[2]:
            date_range = st.date_input("Date range", [])

        df_display = df.copy()
        if ft_type != "All": df_display = df_display[df_display["type"]==ft_type]
        if ft_source:
            mask = df_display["input"].str.contains(ft_source, case=False, na=False) | df_display["output"].str.contains(ft_source, case=False, na=False)
            df_display = df_display[mask]
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            start_dt = datetime.combine(date_range[0], datetime.min.time())
            end_dt = datetime.combine(date_range[1], datetime.max.time())
            df_display["ts_dt"] = pd.to_datetime(df_display["timestamp"])
            df_display = df_display[(df_display["ts_dt"] >= start_dt) & (df_display["ts_dt"] <= end_dt)]
            df_display = df_display.drop(columns=["ts_dt"])
        elif isinstance(date_range, (list, tuple)) and len(date_range) == 1:
            single_dt = datetime.combine(date_range[0], datetime.min.time())
            df_display["ts_dt"] = pd.to_datetime(df_display["timestamp"])
            df_display = df_display[df_display["ts_dt"].dt.date == single_dt.date()]
            df_display = df_display.drop(columns=["ts_dt"])
        st.dataframe(df_display[["timestamp","type","detected_lang","target_lang","input","output"]], height=300)
        c1,c2,c3 = st.columns(3)
        with c1:
            if st.button("Export PDF"):
                pdf_bytes = export_history_pdf_bytes(df_display)
                st.download_button("📥 Download PDF", data=pdf_bytes, file_name="translation_history.pdf", mime="application/pdf")
        with c2:
            csv_bytes = df_display.to_csv(index=False).encode()
            st.download_button("📥 Export CSV", data=csv_bytes, file_name="translation_history.csv", mime="text/csv")
        with c3:
            if st.button("Clear History"):
                clear_history()
                st.cache_data.clear()
                st.success("History cleared.")
                st.rerun()
# ---------------- END OF APP ----------------
