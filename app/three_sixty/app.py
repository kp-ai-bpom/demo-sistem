# app.py
import streamlit as st
from app.three_sixty.tabs import tab_data_utama, tab_hasil_kerja, tab_perilaku

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Aplikasi Penilaian Kinerja 360", layout="wide")

# --- CSS GLOBAL ---
st.markdown("""
    <style>
    .header-style { font-weight: bold; background-color: #f8f9fa; padding: 12px; border-bottom: 2px solid #dee2e6; font-size: 14px; }
    .indicator-title { font-weight: 600; font-size: 15px; margin-bottom: 4px; }
    .indicator-desc { font-size: 13px; color: #6c757d; font-style: italic; margin-bottom: 10px; }
    .stRadio > label { display: none; }
    div[role="radiogroup"] { justify-content: center; gap: 15px; }
    div[role="radiogroup"] p { font-size: 24px !important; margin-bottom: 0px; }
    .separator { border-bottom: 1px solid #f0f0f0; margin-bottom: 10px; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- MAIN CONTENT ---
st.title("📝 Sistem Penilaian Kinerja 360°")

# Navigasi Tab
tab1, tab2, tab3 = st.tabs(["👤 Data Utama", "📊 Hasil Kerja (SKP)", "🧠 Perilaku Kerja"])

with tab1:
    tab_data_utama.show()

with tab2:
    tab_hasil_kerja.show()

with tab3:
    tab_perilaku.show()