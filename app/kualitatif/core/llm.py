# core/llm.py
import os
import json
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from .data import SKJ_DATA
from .prompt import MANAGERIAL_ASSESSMENT_PROMPT

# load .env kalau ada
load_dotenv()

LLM_MODEL = os.getenv("LLM_MODEL", "mistralai/mistral-7b-instruct-v0.2")
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL", "https://openrouter.ai/api/v1")

llm = ChatOpenAI(
    base_url =BASE_URL,
    api_key = API_KEY,
    model=LLM_MODEL,
    temperature=0.7,
    max_tokens=256,
    streaming=True,
    verbose=True,
)

def assess_answer(jabatan_name: str, kompetensi_name: str, jawaban_peserta: str, nama_peserta: str = "Peserta Demo") -> str:
    """
    Menggunakan MANAGERIAL_ASSESSMENT_PROMPT untuk menilai jawaban peserta.
    Return: string teks berisi SKOR, JUSTIFIKASI, REKOMENDASI.
    """
    if jabatan_name not in SKJ_DATA:
        raise ValueError(f"Jabatan '{jabatan_name}' tidak dikenal.")

    skj = SKJ_DATA[jabatan_name]
    if kompetensi_name not in skj["kompetensi"]:
        raise ValueError(f"Kompetensi '{kompetensi_name}' tidak ada di jabatan '{jabatan_name}'.")

    komp = skj["kompetensi"][kompetensi_name]

    context_obj = {
        "jabatan": jabatan_name,
        "kompetensi": kompetensi_name,
        "deskripsi": komp["deskripsi"],
        "level_target": komp["level_target"],
    }
    context_text = json.dumps(context_obj, ensure_ascii=False)

    chain = MANAGERIAL_ASSESSMENT_PROMPT | llm

    result = chain.invoke(
        {
            "context": context_text,
            "nama": nama_peserta,
            "jabatan": jabatan_name,
            "jawaban": jawaban_peserta,
            "kompetensi": kompetensi_name,
            "level_target": str(komp["level_target"]),
        }
    )

    # LangChain ChatOpenAI mengembalikan AIMessage
    return result.content