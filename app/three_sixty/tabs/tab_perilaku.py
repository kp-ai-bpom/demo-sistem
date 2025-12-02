# tabs/tab_perilaku.py
import streamlit as st
import pandas as pd
from app.three_sixty.utils.data_master import BEHAVIOR_DATA, RATING_OPTIONS, RATING_MAP
from app.three_sixty.services import ai_analyst

# --- HELPER FUNCTIONS (Lokal di modul ini) ---
def calculate_score(scores):
    if not scores: return 0, "Belum Dinilai", "#f0f2f6", "#31333f"
    total, count = 0, 0
    for key, val in scores.items():
        if val in RATING_MAP:
            total += RATING_MAP[val]
            count += 1
    if count == 0: return 0, "Belum Dinilai", "#f0f2f6", "#31333f"
    
    avg = total / count
    if avg > 90: return avg, "DIATAS EKSPEKTASI", "#d4edda", "#155724"
    elif avg >= 76: return avg, "SESUAI EKSPEKTASI", "#fff3cd", "#856404"
    else: return avg, "DIBAWAH EKSPEKTASI", "#f8d7da", "#721c24"

def generate_assessment_json(final_score, predikat, feedback_text):
    assessment_details = []
    for aspect, item_list in BEHAVIOR_DATA.items():
        aspect_obj = {"aspek": aspect, "items": []}
        sub_total = 0
        for i, item_dict in enumerate(item_list):
            indicator_name = list(item_dict.keys())[0]
            indicator_detail = list(item_dict.values())[0]
            key = f"{aspect}_{i}"
            emoji = st.session_state['scores'].get(key, None)
            score = RATING_MAP.get(emoji, 0)
            
            label = "BELUM DINILAI"
            if score == 100: label = "DIATAS EKSPEKTASI"
            elif score == 80: label = "SESUAI EKSPEKTASI"
            elif score == 60: label = "DIBAWAH EKSPEKTASI"

            item_detail = {
                "indikator": indicator_name,
                "detail_definisi": indicator_detail,
                "rating_user": emoji,
                "nilai_konversi": score,
                "label_level": label
            }
            aspect_obj["items"].append(item_detail)
            sub_total += score
        aspect_obj["skor_aspek"] = round(sub_total / 3, 2) if item_list else 0
        assessment_details.append(aspect_obj)

    payload = {
        "header": {"pegawai": "Fajar Fachrudin, S.E", "periode": "Triwulan 2 - 2025"},
        "summary": {"skor_akhir": round(final_score, 2), "predikat": predikat, "feedback_text": feedback_text},
        "data_perilaku": assessment_details
    }
    return payload

# --- MAIN FUNCTION UNTUK TAB INI ---
def show():
    st.subheader("🧠 Form Penilaian Perilaku Kerja")
    
    if 'scores' not in st.session_state: st.session_state['scores'] = {}

    # HEADER TABEL
    c1, c2, c3, c4 = st.columns([0.5, 2, 4, 2.5])
    c1.markdown('<div class="header-style">No</div>', unsafe_allow_html=True)
    c2.markdown('<div class="header-style">Standar Perilaku</div>', unsafe_allow_html=True)
    c3.markdown('<div class="header-style">Indikator & Detail</div>', unsafe_allow_html=True)
    c4.markdown('<div class="header-style" style="text-align:center;">Rating</div>', unsafe_allow_html=True)

    # LOOPING UI
    row_num = 1
    for aspect, item_list in BEHAVIOR_DATA.items():
        for i, item_dict in enumerate(item_list):
            indicator_name = list(item_dict.keys())[0]
            indicator_detail = list(item_dict.values())[0]
            
            with st.container():
                col1, col2, col3, col4 = st.columns([0.5, 2, 4, 2.5])
                
                if i == 0:
                    col1.markdown(f"<div style='padding-top:10px;'><b>{row_num}</b></div>", unsafe_allow_html=True)
                    col2.markdown(f"<div style='padding-top:10px;'><b>{aspect}</b></div>", unsafe_allow_html=True)
                    row_num += 1
                
                with col3:
                    st.markdown(f"<div class='indicator-title'>{indicator_name}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='indicator-desc'>{indicator_detail}</div>", unsafe_allow_html=True)
                
                with col4:
                    key = f"{aspect}_{i}"
                    sel = st.radio("Rating", options=RATING_OPTIONS, horizontal=True, key=key, label_visibility="collapsed", index=None)
                    if sel: st.session_state['scores'][key] = sel
                
                st.markdown("<div class='separator'></div>", unsafe_allow_html=True)

    # FOOTER & SAVE
    final_score, predikat, bg_color, tx_color = calculate_score(st.session_state['scores'])
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background-color: {bg_color}; padding: 20px; border-radius: 10px; border: 1px solid {tx_color};">
        <h4 style="margin:0; color: {tx_color};">HASIL PENILAIAN PERILAKU</h4>
        <h2 style="margin:0; color: {tx_color};">{predikat} ({final_score:.0f})</h2>
    </div>
    """, unsafe_allow_html=True)

    feedback = st.text_area("💬 Catatan / Umpan Balik:", height=100)
    st.markdown("<br>", unsafe_allow_html=True)

    # LOGIKA PROSES SIMPAN & AI
    if st.button("Simpan & Analisis dengan AI", type="primary", width="stretch"):
        # 1. SIMPAN DATA & GENERATE JSON PAYLOAD
        json_payload = generate_assessment_json(final_score, predikat, feedback)
        st.balloons()
        st.success("✅ Data berhasil disimpan!")
        
        with st.expander("📦 Lihat Raw JSON Payload"):
            st.json(json_payload)
            
        # 2. PROSES AI INTERPRETASI
        st.markdown("---")
        st.subheader("🤖 AI Interpretation Matrix")
        
        process_ai_analysis(json_payload)
            

def process_ai_analysis(json_payload):
    """Helper function untuk memproses tabel analisis AI"""
    table_rows = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_items = sum(len(items) for items in BEHAVIOR_DATA.values())
    processed_count = 0
    
    for aspect_data in json_payload['data_perilaku']:
        aspect_name = aspect_data['aspek']
        for item in aspect_data['items']:
            status_text.text(f"Menganalisis indikator: {item['indikator']}...")
            
            llm_feedback = ai_analyst.generate_micro_feedback(item)
            
            table_rows.append({
                "Standar Perilaku": aspect_name,
                "Indikator Perilaku": item['indikator'],
                "Nilai": f"{item['nilai_konversi']} {item['rating_user']}",
                "LLM Feedback (Analisis)": llm_feedback
            })
            
            processed_count += 1
            progress_bar.progress(processed_count / total_items)
    
    status_text.text("✅ Analisis Selesai!")
    progress_bar.empty()
    
    df_analysis = pd.DataFrame(table_rows)
    df_analysis.insert(0, 'No', range(1, 1 + len(df_analysis)))
    
    st.dataframe(
        df_analysis,
        column_config={
            "No": st.column_config.NumberColumn(width="small"),
            "Standar Perilaku": st.column_config.TextColumn(width="medium"),
            "Indikator Perilaku": st.column_config.TextColumn(width="large"),
            "Nilai": st.column_config.TextColumn(width="small"),
            "LLM Feedback (Analisis)": st.column_config.TextColumn(width="large"),
        },
        hide_index=True,
        width="stretch"
    )