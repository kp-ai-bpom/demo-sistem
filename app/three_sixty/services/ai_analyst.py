import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import SecretStr

load_dotenv()

API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")

SYSTEM_PROMPT = """
Anda adalah Senior HR Performance Analyst. Tugas Anda adalah memberikan "Micro-Feedback" yang tajam untuk satu baris indikator penilaian kinerja.

KONTEKS DATA:
Anda akan menerima data JSON berisi: Indikator, Definisi, dan Skor (Nilai Konversi).

INSTRUKSI REASONING (Internal Process):
1. Cek Nilai: 
   - 100 (Di Atas Ekspektasi): Artinya pegawai melakukan lebih dari sekadar definisi standar (Role Model/Proaktif).
   - 80 (Sesuai Ekspektasi): Artinya pegawai memenuhi definisi standar dengan konsisten.
   - 60 (Di Bawah Ekspektasi): Artinya ada gap kompetensi berdasarkan definisi.
2. Hubungkan dengan Definisi: Gunakan kata kunci dari 'detail_definisi' untuk membuat konteks menjadi spesifik.

OUTPUT YANG DIHARAPKAN:
Hasilkan kalimat singkat (maksimal 25 kata) yang profesional, langsung pada inti (to-the-point), dan menyoroti perilaku spesifik. Jangan mengulang kata "Pegawai ini...". Langsung ke observasi.

Contoh Output (Nilai 100): "Sangat proaktif dalam mengantisipasi kebutuhan stakeholder bahkan sebelum diminta, menjadi teladan pelayanan prima."
Contoh Output (Nilai 60): "Perlu peningkatan ketelitian dalam bekerja agar sesuai standar mutu, disarankan supervisi lebih ketat."
"""

def generate_micro_feedback(item_data, api_key = API_KEY, base_url = BASE_URL):
    """
    Fungsi untuk menghasilkan interpretasi singkat per baris indikator.
    """
    if not api_key:
        return "⚠️ API Key Missing"

    if not base_url:
        return "⚠️ Base URL Missing"

    try:
        llm = ChatOpenAI(
            model="x-ai/grok-4.1-fast:free", 
            api_key=SecretStr(api_key),
            base_url=base_url,
            temperature=0
        )

        # Template Prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", "Data Indikator: \n{data_json}")
        ])

        # Chain
        chain = prompt | llm | StrOutputParser()
        
        # Eksekusi
        response = chain.invoke({"data_json": str(item_data)})
        return response

    except Exception as e:
        return f"Error: {str(e)}"