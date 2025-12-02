# app.py

import os
import json
from typing import Any, Tuple

import streamlit as st
from dotenv import load_dotenv
from pydantic import SecretStr

from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_core.prompts import PromptTemplate

from app.kualitatif.core.data import SKJ_DATA, QUESTIONS_DATA
from app.kualitatif.core.llm import llm

# ================== CONFIG & SETUP ==================

load_dotenv()

OPENROUTER_API_KEY = os.getenv("API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "qwen/qwen3-embedding-8b")
DATABASE_URL = os.getenv("VECTOR_DB_URL")

st.set_page_config(
    page_title="Demo Penilaian Kompetensi ASN",
    page_icon="🧭",
    layout="wide",
)

st.markdown(
    "<h2 style='color:#3C6CE7;'>🧭 Sistem Penilaian Kualitatif</h2>",
    unsafe_allow_html=True,
)
st.caption("Mode Asesmen: Soal terstruktur & kasus/jawaban bebas")


# ================== PROMPT DEFINITIONS ==================

PROMPT_STRUCTURED = PromptTemplate(
    template="""
ANDA ADALAH ASESOR KOMPETENSI ASN BERDASARKAN:
- PERMENPAN RB No. 38 Tahun 2017
- STANDAR KOMPETENSI JABATAN (SKJ) UNTUK JABATAN TERKAIT

KONTEKS PERMENPAN (STRUKTUR KOMPETENSI & LEVEL 1–5):
{context_permenpan}

KONTEKS SKJ (UNTUK JABATAN & KOMPETENSI INI):
{context_skj}

DATA KASUS:
- Nama: {nama}
- Jabatan: {jabatan}
- Kompetensi yang Dinilai: {kompetensi}
- Level Target Jabatan: {level_target}
- Soal: {soal}
- Jawaban Peserta: {jawaban}

TUGAS ANDA:
1. Baca konteks PermenPAN dan SKJ di atas.
2. Petakan perilaku dalam jawaban peserta ke LEVEL KOMPETENSI 1–5.
3. Bandingkan level aktual dengan level target jabatan.
4. Berikan rekomendasi pengembangan yang spesifik.

ATURAN PENILAIAN (RINGKAS):
- Level 1: Perilaku dasar, belum konsisten.
- Level 2: Mulai konsisten, masih butuh banyak arahan.
- Level 3: Kompeten & cukup mandiri pada situasi umum.
- Level 4: Menjadi rujukan/teladan di unitnya.
- Level 5: Role model organisasi, dampak luas.

FORMAT OUTPUT (WAJIB, JANGAN TAMBAH LABEL LAIN):
LEVEL_PREDIKSI: [1-5] /n
RINGKASAN_PERILAKU: [...]
ALASAN: [...]
GAP: [di bawah / sesuai / di atas level_target + alasan singkat]
REKOMENDASI: [...]

HASIL PENILAIAN:
""",
    input_variables=[
        "context_permenpan",
        "context_skj",
        "nama",
        "jabatan",
        "kompetensi",
        "level_target",
        "soal",
        "jawaban",
    ],
)

PROMPT_FREE = PromptTemplate(
    template="""
ANDA ADALAH ASESOR KOMPETENSI ASN BERDASARKAN:
- PERMENPAN RB No. 38 Tahun 2017
- STANDAR KOMPETENSI JABATAN (SKJ) UNTUK JABATAN TERKAIT

KONTEKS PERMENPAN (STRUKTUR KOMPETENSI & LEVEL 1–5):
{context_permenpan}

KONTEKS SKJ (UNTUK JABATAN & KOMPETENSI INI):
{context_skj}

DATA KASUS BEBAS:
- Nama: {nama}
- Jabatan: {jabatan}
- Kompetensi yang Dinilai: {kompetensi}
- Level Target Jabatan: {level_target}
- Deskripsi Situasi/Kasus: {kasus}
- Jawaban/Perilaku Peserta: {jawaban}

TUGAS ANDA:
1. Baca konteks resmi dan data kasus bebas di atas.
2. Identifikasi perilaku utama peserta.
3. Petakan perilaku peserta ke LEVEL KOMPETENSI 1–5.
4. Bandingkan level aktual dengan level target jabatan.
5. Berikan rekomendasi pengembangan yang spesifik dan realistis.

FORMAT OUTPUT (WAJIB, JANGAN TAMBAH LABEL LAIN):
LEVEL_PREDIKSI: [1-5]
RINGKASAN_PERILAKU: [...]
ALASAN: [...]
GAP: [di bawah / sesuai / di atas level_target + alasan singkat]
REKOMENDASI: [...]

HASIL PENILAIAN:
""",
    input_variables=[
        "context_permenpan",
        "context_skj",
        "nama",
        "jabatan",
        "kompetensi",
        "level_target",
        "kasus",
        "jawaban",
    ],
)

# ================== HELPER: LOAD RETRIEVERS ==================

@st.cache_resource(show_spinner="Menghubungkan ke PGVector (PermenPAN & SKJ)...")
def load_retrievers() -> Tuple[Any | None, Any | None]:
    """
    Connect ke Postgres PGVector.
    Asumsi: Data sudah di-ingest ke tabel vector dengan collection_name:
    1. 'permenpan_index'
    2. 'skj_index'
    """
    
    if not DATABASE_URL:
        st.error("DATABASE_URL tidak ditemukan di .env")
        return None, None

    embeddings = OpenAIEmbeddings(
        api_key=SecretStr(OPENROUTER_API_KEY),
        base_url="https://openrouter.ai/api/v1",
        model=EMBEDDING_MODEL,
    )

    permenpan_retriever = None
    skj_retriever = None

    try:
        # --- PERUBAHAN 3: Inisialisasi PGVector Store ---
        
        # 1. Load PermenPAN Store
        permenpan_store = PGVector(
            embeddings=embeddings,
            collection_name="permenpan_index",
            connection=DATABASE_URL,
            use_jsonb=True,
        )
        permenpan_retriever = permenpan_store.as_retriever(search_kwargs={"k": 4})

        # 2. Load SKJ Store
        skj_store = PGVector(
            embeddings=embeddings,
            collection_name="skj_index",
            connection=DATABASE_URL,
            use_jsonb=True,
        )
        skj_retriever = skj_store.as_retriever(search_kwargs={"k": 4})
        
    except Exception as e:
        st.error(f"Gagal menghubungkan ke Database PGVector: {e}")
        st.info("Pastikan container Docker PostgreSQL sudah berjalan dan connection string benar.")

    return permenpan_retriever, skj_retriever


def _join_docs(docs) -> str:
    return "\n\n---\n\n".join(d.page_content for d in docs)


# ================== RAG ASSESSMENT FUNCTIONS ==================

def _build_contexts(
    jabatan_name: str,
    kompetensi_name: str,
    query: str,
    permenpan_retriever: Any | None,
    skj_retriever: Any | None,
    komp_info: dict,
) -> tuple[str, str]:
    """Ambil konteks PermenPAN & SKJ dari retriever, dengan fallback ke SKJ_DATA."""
    context_permenpan = ""
    context_skj = ""

    if permenpan_retriever is not None:
        docs_p = permenpan_retriever.invoke(query)
        context_permenpan = _join_docs(docs_p)

    if skj_retriever is not None:
        docs_s = skj_retriever.invoke(query)
        context_skj = _join_docs(docs_s)

    # Safety fallback kalau dua-duanya kosong
    if not context_permenpan and not context_skj:
        context_skj = json.dumps(
            {
                "jabatan": jabatan_name,
                "kompetensi": kompetensi_name,
                "deskripsi": komp_info["deskripsi"],
                "level_target": komp_info["level_target"],
            },
            ensure_ascii=False,
        )

    return context_permenpan, context_skj


def assess_answer_rag_structured(
    jabatan_name: str,
    kompetensi_name: str,
    soal_id: str,
    jawaban_peserta: str,
    nama_peserta: str,
    permenpan_retriever: Any | None,
    skj_retriever: Any | None,
) -> tuple[str, str, str]:
    """Mode 1: Soal terstruktur (ambil soal dari QUESTIONS_DATA)."""

    if jabatan_name not in SKJ_DATA:
        raise ValueError(f"Jabatan '{jabatan_name}' tidak dikenal.")

    skj_info = SKJ_DATA[jabatan_name]
    if kompetensi_name not in skj_info["kompetensi"]:
        raise ValueError(f"Kompetensi '{kompetensi_name}' tidak ada di jabatan '{jabatan_name}'.")

    komp = skj_info["kompetensi"][kompetensi_name]
    level_target = komp["level_target"]

    # Ambil soal
    soal_list = QUESTIONS_DATA.get(jabatan_name, {}).get(kompetensi_name, [])
    if not soal_list:
        raise ValueError(f"Tidak ada soal untuk jabatan '{jabatan_name}', kompetensi '{kompetensi_name}'.")

    try:
        soal_obj = next(s for s in soal_list if s["id_soal"] == soal_id)
    except StopIteration:
        raise ValueError(f"Soal dengan id '{soal_id}' tidak ditemukan.")

    soal_text = soal_obj["teks"]

    # Query untuk RAG
    query = (
        f"Jabatan: {jabatan_name}. Kompetensi: {kompetensi_name}. "
        f"Soal: {soal_text}. Jawaban: {jawaban_peserta}."
    )

    context_permenpan, context_skj = _build_contexts(
        jabatan_name, kompetensi_name, query, permenpan_retriever, skj_retriever, komp
    )

    chain = PROMPT_STRUCTURED | llm

    result = chain.invoke(
        {
            "context_permenpan": context_permenpan,
            "context_skj": context_skj,
            "nama": nama_peserta,
            "jabatan": jabatan_name,
            "kompetensi": kompetensi_name,
            "level_target": str(level_target),
            "soal": soal_text,
            "jawaban": jawaban_peserta,
        }
    )

    return result.content, context_permenpan, context_skj


def assess_answer_rag_free(
    jabatan_name: str,
    kompetensi_name: str,
    kasus_text: str,
    jawaban_peserta: str,
    nama_peserta: str,
    permenpan_retriever: Any | None,
    skj_retriever: Any | None,
) -> tuple[str, str, str]:
    """Mode 2: Kasus / jawaban bebas (user isi sendiri kasus & jawaban)."""

    if jabatan_name not in SKJ_DATA:
        raise ValueError(f"Jabatan '{jabatan_name}' tidak dikenal.")

    skj_info = SKJ_DATA[jabatan_name]
    if kompetensi_name not in skj_info["kompetensi"]:
        raise ValueError(f"Kompetensi '{kompetensi_name}' tidak ada di jabatan '{jabatan_name}'.")

    komp = skj_info["kompetensi"][kompetensi_name]
    level_target = komp["level_target"]

    # Query untuk RAG
    query = (
        f"Jabatan: {jabatan_name}. Kompetensi: {kompetensi_name}. "
        f"Kasus: {kasus_text}. Jawaban: {jawaban_peserta}."
    )

    context_permenpan, context_skj = _build_contexts(
        jabatan_name, kompetensi_name, query, permenpan_retriever, skj_retriever, komp
    )

    chain = PROMPT_FREE | llm

    result = chain.invoke(
        {
            "context_permenpan": context_permenpan,
            "context_skj": context_skj,
            "nama": nama_peserta,
            "jabatan": jabatan_name,
            "kompetensi": kompetensi_name,
            "level_target": str(level_target),
            "kasus": kasus_text,
            "jawaban": jawaban_peserta,
        }
    )

    return result.content, context_permenpan, context_skj


# ================== UI STREAMLIT (2 TAB) ==================

permenpan_retriever, skj_retriever = load_retrievers()

# Pilihan jabatan & kompetensi (global untuk kedua tab)
col_side, col_main = st.columns([1.1, 3])

with col_side:
    st.subheader("📂 Pilihan Asesmen")
    jabatan_list = list(SKJ_DATA.keys())
    jabatan = st.selectbox("Pilih Jabatan", jabatan_list)

    kompetensi_list = list(SKJ_DATA[jabatan]["kompetensi"].keys())
    kompetensi = st.selectbox("Pilih Kompetensi", kompetensi_list)

    komp_info = SKJ_DATA[jabatan]["kompetensi"][kompetensi]

with col_main:
    tab1, tab2 = st.tabs(["📌 Mode Soal Terstruktur", "📝 Mode Kasus / Jawaban Bebas"])

    # ===== TAB 1: Soal Terstruktur =====
    with tab1:
        st.markdown("### 📌 Soal Terstruktur")

        soal_list = QUESTIONS_DATA.get(jabatan, {}).get(kompetensi, [])
        if not soal_list:
            st.warning("Belum ada soal untuk kombinasi jabatan & kompetensi ini.")
        else:
            label_list = [f"{s['id_soal']} – {s['teks'][:100]}..." for s in soal_list]
            idx = st.selectbox(
                "Pilih Soal",
                options=range(len(soal_list)),
                format_func=lambda i: label_list[i],
            )
            soal = soal_list[idx]

            st.markdown(f"**Soal yang dipilih:** {soal['teks']}")
            jawaban_peserta = st.text_area("✍️ Tulis jawaban peserta:", height=200, key="jawaban_terstruktur")
            nama_peserta = st.text_input("Nama Peserta", value="Peserta Demo", key="nama_terstruktur")

            if st.button("🔍 Nilai Jawaban (Mode Soal Terstruktur)"):
                if not jawaban_peserta.strip():
                    st.error("Jawaban tidak boleh kosong.")
                else:
                    with st.spinner("Menilai jawaban dengan RAG (PermenPAN + SKJ)..."):
                        try:
                            hasil, ctx_perm, ctx_skj = assess_answer_rag_structured(
                                jabatan_name=jabatan,
                                kompetensi_name=kompetensi,
                                soal_id=soal["id_soal"],
                                jawaban_peserta=jawaban_peserta,
                                nama_peserta=nama_peserta,
                                permenpan_retriever=permenpan_retriever,
                                skj_retriever=skj_retriever,
                            )
                        except Exception as e:
                            st.error(f"Terjadi error saat penilaian: {e}")
                        else:
                            st.success("Penilaian selesai.")
                            st.markdown("#### 🎯 Hasil Penilaian")
                            st.write(hasil)

                            with st.expander("📁 Konteks RAG yang digunakan (PermenPAN + SKJ)"):
                                st.markdown("**Konteks PermenPAN (potongan):**")
                                st.text((ctx_perm or "")[:1500] or "[kosong]")
                                st.markdown("---")
                                st.markdown("**Konteks SKJ (potongan):**")
                                st.text((ctx_skj or "")[:1500] or "[kosong]")

    # ===== TAB 2: Kasus / Jawaban Bebas =====
    with tab2:
        st.markdown("### 📝 Mode Kasus / Jawaban Bebas")

        kasus_text = st.text_area(
            "🧾 Ceritakan situasi/kasus yang ingin dinilai (misalnya pengalaman nyata):",
            height=150,
            key="kasus_bebas",
        )
        jawaban_bebas = st.text_area(
            "✍️ Jelaskan apa yang Anda lakukan dalam situasi tersebut:",
            height=180,
            key="jawaban_bebas",
        )
        nama_peserta2 = st.text_input("Nama Peserta", value="Peserta Demo", key="nama_bebas")

        if st.button("🔍 Nilai Jawaban (Mode Kasus Bebas)"):
            if not kasus_text.strip() or not jawaban_bebas.strip():
                st.error("Deskripsi kasus dan jawaban tidak boleh kosong.")
            else:
                with st.spinner("Menilai kasus & jawaban dengan RAG (PermenPAN + SKJ)..."):
                    try:
                        hasil2, ctx_perm2, ctx_skj2 = assess_answer_rag_free(
                            jabatan_name=jabatan,
                            kompetensi_name=kompetensi,
                            kasus_text=kasus_text,
                            jawaban_peserta=jawaban_bebas,
                            nama_peserta=nama_peserta2,
                            permenpan_retriever=permenpan_retriever,
                            skj_retriever=skj_retriever,
                        )
                    except Exception as e:
                        st.error(f"Terjadi error saat penilaian: {e}")
                    else:
                        st.success("Penilaian selesai.")
                        st.markdown("#### 🎯 Hasil Penilaian (Mode Kasus Bebas)")
                        st.write(hasil2)

                        with st.expander("📁 Konteks RAG yang digunakan (PermenPAN + SKJ)"):
                            st.markdown("**Konteks PermenPAN (potongan):**")
                            st.text((ctx_perm2 or "")[:1500] or "[kosong]")
                            st.markdown("---")
                            st.markdown("**Konteks SKJ (potongan):**")
                            st.text((ctx_skj2 or "")[:1500] or "[kosong]")


# ===== Sidebar info SKJ ringkas =====
# with st.sidebar:
#     st.markdown("---")
#     st.markdown("### ℹ️ Ringkasan SKJ")
#     st.markdown(f"**Jabatan:** {jabatan}")
#     st.markdown(f"**Kompetensi:** {kompetensi}")
#     st.markdown(f"**Deskripsi:** {komp_info['deskripsi']}")
#     st.markdown(f"**Level Target:** {komp_info['level_target']}")