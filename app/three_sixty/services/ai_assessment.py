import os

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_community.document_loaders import PyPDFLoader
from pydantic import BaseModel, Field, SecretStr
from typing import List

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")

# --- SCHEMA STRUCTURE ---
class AssessmentOutput(BaseModel):
    justifikasi: str = Field(description="Narasi fakta realisasi dengan bahasa birokrasi")
    umpan_balik: str = Field(description="Komentar atasan")

class TargetItem(BaseModel):
    rhk: str = Field(description="Kalimat tujuan aktivitas utama")
    iki: str = Field(description="Objek yang diukur")
    target_value: str = Field(description="Angka target spesifik")
    aspek: str = Field(description="Kuantitas/Kualitas/Waktu")

class TargetList(BaseModel):
    targets: List[TargetItem]

# --- AI FUNCTIONS ---

def get_llm_smart(api_key = API_KEY):
    """Model Cerdas (GPT-4o) untuk Inference Struktur"""
    if not api_key:
        raise ValueError("API key is required")
    return ChatOpenAI(
    model="tngtech/deepseek-r1t-chimera:free", 
    api_key=SecretStr(api_key),
    base_url=BASE_URL,
    temperature=0
    )

def get_llm_fast(api_key = API_KEY):
    """Model Cepat (GPT-3.5/4o-mini) untuk Summarization"""
    if not api_key:
        raise ValueError("API key is required")
    return ChatOpenAI(
    model="x-ai/grok-4.1-fast:free", 
    api_key=SecretStr(api_key),
    base_url=BASE_URL,
    temperature=0
    )

def extract_targets_from_pdf(pdf_path,st, api_key = API_KEY):
    """
    Tahap 1: Mengubah Dokumen Target (Narasi/Tabel) menjadi Struktur RHK
    """
    try:
        loader = PyPDFLoader(pdf_path)
        text = " ".join([p.page_content for p in loader.load()])
        
        parser = PydanticOutputParser(pydantic_object=TargetList)
        
        prompt_text = """
        Anda adalah Job Analyst. Tugas Anda adalah membaca dokumen (surat/notulen/rencana) dan MENGUBAHNYA menjadi Tabel SKP Standar.
        
        DOKUMEN:
        "{text}"
        
        INSTRUKSI:
        1. Cari kalimat tugas/pekerjaan -> 'RHK'.
        2. Cari ukuran keberhasilan -> 'IKI'.
        3. Cari angka/tenggat -> 'Target Value'.
        4. Tentukan 'Aspek' (Kuantitas/Kualitas/Waktu).
        
        {format_instructions}
        """
        
        prompt = ChatPromptTemplate.from_template(prompt_text)
        chain = prompt | get_llm_smart(api_key) | parser
        
        result = chain.invoke({
            "text": text, 
            "format_instructions": parser.get_format_instructions()
        })
        return result.targets
    except Exception as e:
        st.error(f"Gagal mengekstrak target: {str(e)}")
        return []

def get_evidence_summary(pdf_path, api_key = API_KEY):
    """
    Tahap 2: Meringkas Dokumen Bukti Dukung menjadi Fakta Padat
    """
    try:
        loader = PyPDFLoader(pdf_path)
        text = " ".join([p.page_content for p in loader.load()])[:10000] # Limit token
        
        llm = get_llm_fast(api_key)
        return llm.invoke(f"Ringkas fakta angka, tanggal, dan nama kegiatan dari laporan ini. Abaikan kata sambutan: {text}").content
    except Exception as e:
        return f"Gagal membaca bukti: {str(e)}"

def assess_performance(rhk, iki, target, evidence_text, api_key = API_KEY):
    """
    Tahap 3: Comparative Reasoning (Menilai Capaian)
    """
    try:
        parser = PydanticOutputParser(pydantic_object=AssessmentOutput)
        
        prompt_text = """
        Bertindaklah sebagai Pejabat Penilai.
        
        TARGET (RHK): {rhk}
        INDIKATOR: {iki}
        NILAI TARGET: {target}
        
        FAKTA LAPANGAN:
        {evidence}
        
        TUGAS:
        1. Bandingkan Target vs Fakta.
        2. Tulis 'Justifikasi': Ceritakan apa yang tercapai dengan bahasa birokrasi.
        3. Tulis 'Umpan Balik': Berikan apresiasi atau teguran halus.
        
        {format_instructions}
        """
        
        prompt = ChatPromptTemplate.from_template(prompt_text)
        chain = prompt | get_llm_smart(api_key) | parser
        
        return chain.invoke({
            "rhk": rhk, "iki": iki, "target": target,
            "evidence": evidence_text,
            "format_instructions": parser.get_format_instructions()
        })
    except Exception as e:
        return AssessmentOutput(justifikasi="Gagal generate", umpan_balik="Error")