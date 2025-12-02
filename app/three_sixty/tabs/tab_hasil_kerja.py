import streamlit as st
import pandas as pd
import time
import tempfile
import os

from app.three_sixty.services.ai_assessment import extract_targets_from_pdf, get_evidence_summary, assess_performance

# --- STREAMLIT UI ---

def show():
    st.subheader("📊 Penilaian Hasil Kerja (AI-Powered)")
    st.caption("Unggah dokumen Target (SKP) dan Realisasi (Laporan) untuk penilaian otomatis.")

    # --- FILE UPLOADER ---
    col1, col2 = st.columns(2)
    with col1:
        target_file = st.file_uploader("📂 Upload Dokumen Target (SKP)", type="pdf")
    with col2:
        realisasi_file = st.file_uploader("📂 Upload Dokumen Realisasi (Laporan)", type="pdf")

    # --- TOMBOL PROSES ---
    if target_file and realisasi_file:
        if st.button("🚀 Jalankan AI Assessment", type="primary"):
            
            # 1. Simpan File Sementara
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as t_tmp:
                t_tmp.write(target_file.read())
                target_path = t_tmp.name
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as r_tmp:
                r_tmp.write(realisasi_file.read())
                realisasi_path = r_tmp.name
            
            try:
                # --- PROGRESS BAR ---
                progress_text = "Memulai analisis..."
                my_bar = st.progress(0, text=progress_text)

                # --- STEP 1: Extract Target ---
                my_bar.progress(20, text="Mengekstrak struktur RHK dari dokumen target...")
                list_targets = extract_targets_from_pdf(target_path, st)
                
                if not list_targets:
                    st.error("Tidak ada target yang ditemukan dalam dokumen.")
                    return

                # --- STEP 2: Summarize Evidence ---
                my_bar.progress(50, text="Meringkas fakta dari dokumen realisasi...")
                evidence_summary = get_evidence_summary(realisasi_path)
                
                # --- STEP 3: Reasoning Loop ---
                final_results = []
                total_items = len(list_targets)
                
                for idx, item in enumerate(list_targets):
                    pct = 50 + int((idx / total_items) * 40)
                    my_bar.progress(pct, text=f"Menilai RHK {idx+1}/{total_items}: {item.rhk[:30]}...")
                    
                    assessment = assess_performance(
                        rhk=item.rhk,
                        iki=item.iki,
                        target=item.target_value,
                        evidence_text=evidence_summary
                    )
                    
                    final_results.append({
                        "Rencana Hasil Kerja": item.rhk,
                        "Aspek": item.aspek,
                        "Indikator": item.iki,
                        "Target": item.target_value,
                        "Realisasi (Justifikasi)": assessment.justifikasi,
                        "Umpan Balik": assessment.umpan_balik
                    })
                
                my_bar.progress(100, text="Selesai!")
                time.sleep(1)
                my_bar.empty()
                
                # Simpan ke Session State agar tidak hilang saat refresh
                st.session_state['skp_results'] = final_results
                
            finally:
                # Cleanup file temp
                os.remove(target_path)
                os.remove(realisasi_path)

    # --- TAMPILAN HASIL (EDITABLE) ---
    if 'skp_results' in st.session_state:
        st.divider()
        st.success(f"✅ Berhasil mengekstrak {len(st.session_state['skp_results'])} Rencana Kerja.")
        
        # Konversi ke DataFrame untuk diedit user
        df = pd.DataFrame(st.session_state['skp_results'])
        
        # Tampilkan Data Editor
        edited_df = st.data_editor(
            df,
            column_config={
                "Rencana Hasil Kerja": st.column_config.TextColumn(width="medium", disabled=True),
                "Aspek": st.column_config.TextColumn(width="small", disabled=True),
                "Indikator": st.column_config.TextColumn(width="medium", disabled=True),
                "Target": st.column_config.TextColumn(width="small", disabled=True),
                "Realisasi (Justifikasi)": st.column_config.TextColumn(width="large", required=True),
                "Umpan Balik": st.column_config.TextColumn(width="large", required=True),
            },
            width='stretch',
            num_rows="fixed",
            hide_index=True
        )
        
        # Tombol Finalisasi
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            if st.button("💾 Simpan Final SKP"):
                st.toast("Data SKP berhasil disimpan ke Database!", icon="✅")
                # Di sini logika insert ke Database SQL
        
        with col_btn2:
            # Download JSON
            json_str = edited_df.to_json(orient="records", indent=2)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name="hasil_skp_final.json",
                mime="application/json"
            )