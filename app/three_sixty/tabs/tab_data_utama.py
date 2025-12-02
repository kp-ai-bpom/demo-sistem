# tabs/tab_data_utama.py
import streamlit as st

def show():
    st.header("👤 Data Utama Pegawai")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("Nama Pegawai", value="John Doe", disabled=True)
        st.text_input("NIP", value="123456", disabled=True)
        st.text_input("Jabatan", value="HRD", disabled=True)
    
    with col2:
        st.text_input("Unit Kerja", value="Biro Sumber Daya Manusia", disabled=True)
        st.text_input("Atasan Penilai", value="Dr. Jane Doe", disabled=True)
        st.text_input("Periode Penilaian", value="Triwulan 2 Tahun 2025", disabled=True)