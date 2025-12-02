SKJ_DATA = {
    "Administrator": {
        "level_jabatan": "Eselon IV",
        "kompetensi": {
            "Integritas": {
                "deskripsi": "Menjaga kejujuran, konsistensi ucapan dan tindakan, serta mematuhi aturan.",
                "level_target": 2,
            },
            "Kerjasama": {
                "deskripsi": "Kemampuan bekerja sama dengan pihak lain untuk mencapai tujuan.",
                "level_target": 2,
            },
        },
    },
    "Inspektur": {
        "level_jabatan": "Eselon III",
        "kompetensi": {
            "Pengambilan Keputusan": {
                "deskripsi": "Mampu mengambil keputusan berdasarkan data dan risiko yang ada.",
                "level_target": 3,
            },
            "Orientasi Hasil": {
                "deskripsi": "Berfokus pada pencapaian target dan kualitas hasil kerja.",
                "level_target": 3,
            },
        },
    },
    "Kepala Seksi": {
        "level_jabatan": "Eselon IV",
        "kompetensi": {
            "Pengelolaan Kinerja": {
                "deskripsi": "Mengelola kinerja tim dan memonitor capaian.",
                "level_target": 3,
            },
            "Komunikasi": {
                "deskripsi": "Menyampaikan informasi secara jelas dan efektif.",
                "level_target": 3,
            },
        },
    },
}

# Soal dummy per kompetensi
# Struktur: {jabatan: {kompetensi: [list soal]}}
QUESTIONS_DATA = {
    "Administrator": {
        "Integritas": [
            {
                "id_soal": "ADM_INT_1",
                "teks": "Ceritakan pengalaman Anda ketika harus memilih antara kepentingan pribadi dan aturan yang berlaku.",
            },
            {
                "id_soal": "ADM_INT_2",
                "teks": "Apa yang Anda lakukan jika atasan meminta Anda mengubah data yang menurut Anda tidak sesuai fakta?",
            },
        ],
        "Kerjasama": [
            {
                "id_soal": "ADM_KER_1",
                "teks": "Berikan contoh situasi dimana Anda harus bekerja sama dengan unit lain untuk menyelesaikan tugas.",
            }
        ],
    },
    "Inspektur": {
        "Pengambilan Keputusan": [
            {
                "id_soal": "INS_PK_1",
                "teks": "Ceritakan saat Anda harus mengambil keputusan sulit dengan informasi yang terbatas.",
            }
        ],
        "Orientasi Hasil": [
            {
                "id_soal": "INS_OH_1",
                "teks": "Apa yang Anda lakukan ketika target kinerja hampir tidak tercapai menjelang akhir periode?",
            }
        ],
    },
    "Kepala Seksi": {
        "Pengelolaan Kinerja": [
            {
                "id_soal": "KS_PK_1",
                "teks": "Bagaimana cara Anda memonitor kinerja anggota tim dan menindaklanjuti jika ada yang menurun?",
            }
        ],
        "Komunikasi": [
            {
                "id_soal": "KS_KOM_1",
                "teks": "Ceritakan pengalaman Anda menyampaikan pesan yang sulit kepada bawahan atau atasan.",
            }
        ],
    },
}