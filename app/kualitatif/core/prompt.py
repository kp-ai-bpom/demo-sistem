# Template untuk penilaian kompetensi manajerial
#Prompt
from langchain_core.prompts import PromptTemplate

# Template ini akan diisi dengan dokumen dari retriever dan pertanyaan dari pengguna (query)
prompt_template = """
Gunakan potongan-potongan konteks berikut untuk menjawab pertanyaan pengguna.
Jawablah secara ringkas dan jelas dalam Bahasa Indonesia.
Jika Anda tidak tahu jawabannya berdasarkan konteks yang diberikan, katakan saja bahwa Anda tidak dapat menemukan informasinya, jangan mencoba mengarang jawaban.

KONTEKS:
{context}

PERTANYAAN:
{question}

JAWABAN YANG MEMBANTU:
"""

CUSTOM_PROMPT = PromptTemplate(
    template=prompt_template, input_variables=["context", "question"]
)


# Template untuk query dasar RAG
BASIC_RAG_PROMPT = PromptTemplate(
    template="""
Gunakan potongan-potongan konteks berikut untuk menjawab pertanyaan pengguna.
Jawablah secara ringkas dan jelas dalam Bahasa Indonesia.
Jika Anda tidak tahu jawabannya berdasarkan konteks yang diberikan, katakan saja bahwa Anda tidak dapat menemukan informasinya, jangan mencoba mengarang jawaban.

KONTEKS:
{context}

PERTANYAAN:
{question}

JAWABAN YANG MEMBANTU:
""",
    input_variables=["context", "question"]
)

MANAGERIAL_ASSESSMENT_PROMPT = PromptTemplate(
    template="""
ANDA ADALAH PENILAI KOMPETENSI MANAJERIAL BERDASARKAN PERMENPAN RB NO. 38 TAHUN 2017.

KONTEKS STANDAR KOMPETENSI:
{context}

DATA TEST CASE:
- Nama: {nama}
- Jabatan: {jabatan}
- Jawaban Test Case: {jawaban}
- Kompetensi yang Dinilai: {kompetensi}
- Level Target: {level_target}

INSTRUKSI PENILAIAN:
1. Analisis jawaban berdasarkan indikator perilaku untuk level {level_target}
2. Berikan skor 1-4 (1: Tidak memenuhi, 2: Cukup, 3: Baik, 4: Sangat Baik)
3. Berikan justifikasi berdasarkan standar kompetensi
4. Berikan rekomendasi pengembangan

FORMAT OUTPUT:
SKOR: [angka 1-4]
JUSTIFIKASI: [penjelasan berdasarkan indikator perilaku]
REKOMENDASI: [saran pengembangan kompetensi]

HASIL PENILAIAN:
""",
    input_variables=["context", "nama", "jabatan", "jawaban", "kompetensi", "level_target"]
)



# Template untuk evaluasi kompetensi teknis
TECHNICAL_COMPETENCY_PROMPT = PromptTemplate(
    template="""
ANDA ADALAH PENILAI KOMPETENSI TEKNIS BERDASARKAN PERMENPAN RB NO. 38 TAHUN 2017.

KONTEKS STANDAR KOMPETENSI TEKNIS:
{context}

DATA PENILAIAN:
- Nama: {nama}
- Jabatan: {jabatan}
- Bidang Teknis: {bidang_teknis}
- Jawaban/Karya: {jawaban}
- Level yang Dinilai: {level_target}

INSTRUKSI:
1. Evaluasi berdasarkan standar kompetensi teknis untuk bidang {bidang_teknis}
2. Berikan penilaian kualitatif
3. Identifikasi kekuatan dan kelemahan
4. Rekomendasikan pengembangan teknis

HASIL EVALUASI TEKNIS:
""",
    input_variables=["context", "nama", "jabatan", "bidang_teknis", "jawaban", "level_target"]
)

# Template untuk analisis gap kompetensi
COMPETENCY_GAP_ANALYSIS_PROMPT = PromptTemplate(
    template="""
ANDA ADALAH ANALIS KOMPETENSI ASN BERDASARKAN PERMENPAN RB NO. 38 TAHUN 2017.

KONTEKS STANDAR KOMPETENSI:
{context}

DATA PROFIL:
- Nama: {nama}
- Jabatan: {jabatan}
- Level Saat Ini: {level_sekarang}
- Level Target: {level_target}
- Hasil Assessment: {hasil_assessment}

INSTRUKSI ANALISIS:
1. Identifikasi gap kompetensi antara level sekarang dan target
2. Rekomendasikan program pengembangan spesifik
3. Saran timeline pengembangan
4. Prioritas kompetensi yang perlu ditingkatkan

FORMAT OUTPUT:
KOMPETENSI MEMADAI: [daftar kompetensi yang sudah memadai]
KOMPETENSI PERLU DITINGKATKAN: [daftar kompetensi yang perlu ditingkatkan]
PROGRAM PENGEMBANGAN: [rekomendasi program spesifik]
TIMELINE: [estimasi timeline pengembangan]

HASIL ANALISIS:
""",
    input_variables=["context", "nama", "jabatan", "level_sekarang", "level_target", "hasil_assessment"]
)