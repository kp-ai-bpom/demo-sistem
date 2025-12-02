import streamlit as st

st.set_page_config(page_title="Portal Aplikasi Utama", layout="wide")


page_1 = st.Page("app/query/app.py", title="BPOM Chatbot", icon="🤖", url_path="chatbot")
page_2 = st.Page("app/three_sixty/app.py", title="Penilaian 360", icon="📊", url_path="penilaian-360")
page_3 = st.Page("app/kualitatif/app.py", title="Penilaian Kualitatif", icon="🧭", url_path="penilaian-kualitatif")

pg = st.navigation({
    "Chatbot": [page_1],
    "Penilaian Karyawan": [page_2, page_3]
})

pg.run()