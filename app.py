import streamlit as st
import sqlite3
import pandas as pd
from fpdf import FPDF
from utils.translator import detect_and_translate
from utils.speech import speech_to_text, text_to_speech, SUPPORTED_LANGS
from utils.ocr import extract_text_from_image
import base64
import time
import os

st.set_page_config(page_title="🌍 Lingua App", page_icon="🌍", layout="wide")

# ---------------- DB Helpers ----------------
DB_FILE = "history.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS history
                 (timestamp TEXT, input TEXT, detected_lang TEXT, target_lang TEXT, output TEXT)""")
    conn.commit()
    conn.close()

def save_history(input_text, detected_lang, target_lang, output_text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO history VALUES (?, ?, ?, ?, ?)",
              (time.strftime("%Y-%m-%d %H:%M:%S"), input_text, detected_lang, target_lang, output_text))
    conn.commit()
    conn.close()

def load_history():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM history ORDER BY timestamp DESC", conn)
    conn.close()
    return df

init_db()

# ---------------- PDF Export ----------------
def export_pdf(df, filename="translation_history.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, "Translation History", ln=True, align="C")
    pdf.ln(10)

    for _, row in df.iterrows():
        pdf.multi_cell(0, 10,
                       f"{row['timestamp']} | From: {row['detected_lang']} | To: {row['target_lang']}\n"
                       f"Input: {row['input']}\nOutput: {row['output']}\n")
        pdf.ln(5)

    pdf.output(filename)
    return filename

# ---------------- UI ----------------
st.title("🌍 Lingua App - Advanced Translator")

st.sidebar.header("Choose Action")
action = st.sidebar.radio("Mode", ["Text Translation", "Speech Translation", "Image OCR", "History"])

# ---------------- Text Translation ----------------
if action == "Text Translation":
    st.subheader("📝 Text Translation")

    input_text = st.text_area("Enter text to translate:")
    target_lang = st.selectbox(
        "Translate to:",
        list(SUPPORTED_LANGS.keys()),
        format_func=lambda x: SUPPORTED_LANGS[x]
    )

    if st.button("Translate"):
        if input_text.strip():
            detected, translated = detect_and_translate(input_text, target_lang)
            st.write(f"**Detected language:** {detected}")
            st.success(f"**Translated text ({SUPPORTED_LANGS[target_lang]}):** {translated}")

            save_history(input_text, detected, target_lang, translated)

            # 🔊 Optional TTS
            if st.checkbox("🔊 Convert translation to speech"):
                audio_bytes = text_to_speech_bytes(translated, lang=target_lang)
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3")
        else:
            st.warning("Please enter text before translating.")

# ---------------- Speech Translation ----------------
elif action == "Speech Translation":
    st.subheader("🎤 Speech Translation")

    audio_file = st.file_uploader("Upload an audio file", type=["wav", "mp3", "m4a"])
    target_lang = st.selectbox(
        "Translate to:",
        list(SUPPORTED_LANGS.keys()),
        format_func=lambda x: SUPPORTED_LANGS[x]
    )

    if audio_file is not None and st.button("Transcribe & Translate"):
        st.info("Processing audio...")
        text = speech_to_text(audio_file)
        st.write("**Transcribed text:**", text)

        detected, translated = detect_and_translate(text, target_lang)
        st.success(f"**Translated text ({SUPPORTED_LANGS[target_lang]}):** {translated}")

        save_history(text, detected, target_lang, translated)

        if st.checkbox("🔊 Convert translation to speech"):
            audio_bytes = text_to_speech_bytes(translated, lang=target_lang)
            if audio_bytes:
                st.audio(audio_bytes, format="audio/mp3")

# ---------------- Image OCR ----------------
elif action == "Image OCR":
    st.subheader("🖼️ OCR - Extract & Translate Text from Image")

    image_file = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])
    target_lang = st.selectbox(
        "Translate to:",
        list(SUPPORTED_LANGS.keys()),
        format_func=lambda x: SUPPORTED_LANGS[x]
    )

    if image_file is not None and st.button("Extract & Translate"):
        extracted = extract_text_from_image(image_file)
        st.write("**Extracted text:**", extracted)

        detected, translated = detect_and_translate(extracted, target_lang)
        st.success(f"**Translated text ({SUPPORTED_LANGS[target_lang]}):** {translated}")

        save_history(extracted, detected, target_lang, translated)

# ---------------- History ----------------
elif action == "History":
    st.subheader("📜 Translation History")

    df = load_history()
    if not df.empty:
        st.dataframe(df)

        if st.button("Export as PDF"):
            filename = export_pdf(df)
            with open(filename, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}">📥 Download PDF</a>'
            st.markdown(href, unsafe_allow_html=True)
    else:
        st.info("No history found yet.")
