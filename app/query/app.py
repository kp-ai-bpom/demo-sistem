# app.py - NL2SQL Streamlit, config hardcoded seperti Jupyter
import json, re
import streamlit as st
import pandas as pd
from collections import defaultdict
from sqlalchemy import create_engine, text, bindparam
from sqlalchemy.exc import SQLAlchemyError
from openai import OpenAI

import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("API_KEY")
OPENAI_BASE_URL = os.getenv("BASE_URL")
MODEL_NAME = "x-ai/grok-4.1-fast:free"

DATABASE_URL     = os.getenv("DATABASE_URL")

DEFAULT_SCHEMA     = "employee"
WHITELIST_SCHEMAS  = ("employee",)
DEFAULT_ROW_LIMIT   = 100
SQL_STMT_TIMEOUT_MS = 8000
EXPLAIN_TIMEOUT_MS  = 5000
SCHEMA_SNIPPET_CHARS = 60000
# ==================================================

# Validasi minimal
if not OPENAI_API_KEY or not DATABASE_URL:
    raise SystemExit("Isi OPENAI_API_KEY dan DATABASE_URL di bagian CONFIG.")

# Init klien LLM dan engine
client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL) if OPENAI_BASE_URL else OpenAI(api_key=OPENAI_API_KEY)

@st.cache_resource(show_spinner=False)
def get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)

engine = get_engine()

# ---------------- Utilities ----------------
BANNED = re.compile(r"\b(insert|update|delete|alter|drop|truncate|create|grant|revoke|comment|vacuum|analyze)\b", re.I)
IDENT = r'[A-Za-z_][A-Za-z0-9_$]*'
QIDENT = r'"[^"]+"'
NAME = rf'(?:{QIDENT}|{IDENT})'
TABLE_REF = rf'(?:{NAME}\.)?{NAME}'
ALIAS_REF = rf'(?:{NAME})'

def is_safe_sql(sql: str) -> bool:
    s = sql.strip()
    return s.lower().startswith("select ") and ";" not in s and not BANNED.search(s)

def normalize_params_style(sql: str, params):
    # $1 atau :1 -> :p1. dict key -> :pkey
    if isinstance(params, list):
        new_sql = sql
        for i in range(1, len(params) + 1):
            new_sql = re.sub(fr"\${i}\b", f":p{i}", new_sql)
            new_sql = re.sub(fr":{i}\b", f":p{i}", new_sql)
        pmap = {f"p{i}": v for i, v in enumerate(params, start=1)}
        return new_sql, pmap
    if isinstance(params, dict):
        new_sql = sql
        pmap = {}
        for k, v in params.items():
            kk = k if str(k).startswith("p") else f"p{k}"
            new_sql = re.sub(fr":{re.escape(str(k))}\b", f":{kk}", new_sql)
            pmap[kk] = v
        return new_sql, pmap
    return sql, {}

def run_explain(sql: str, p: dict):
    with engine.connect() as conn:
        conn.execute(text(f"SET statement_timeout = {EXPLAIN_TIMEOUT_MS}"))
        return conn.execute(text("EXPLAIN " + sql), p).all()

def run_query(sql: str, p: dict, limit=DEFAULT_ROW_LIMIT) -> pd.DataFrame:
    safe_sql = sql if " limit " in sql.lower() else f"{sql} LIMIT {limit}"
    with engine.connect() as conn:
        conn.execute(text(f"SET statement_timeout = {SQL_STMT_TIMEOUT_MS}"))
        rs = conn.execute(text(safe_sql), p)
        cols = rs.keys()
        rows = rs.fetchall()
    return pd.DataFrame(rows, columns=cols)

# ---------------- Schema snapshot ----------------
@st.cache_data(ttl=300, show_spinner=False)
def coerce_schemas(v):
    if isinstance(v, (list, tuple)):
        return tuple(s for s in v if s)
    return tuple(s.strip() for s in str(v).split(",") if s.strip())

def load_schema_snapshot(whitelist_schemas=WHITELIST_SCHEMAS, max_cols=4000):
    schemas = coerce_schemas(whitelist_schemas)
    
    # Query untuk mendapatkan columns DAN enum values
    q = """
    SELECT 
        c.table_schema, 
        c.table_name, 
        c.column_name, 
        c.data_type,
        c.udt_name,
        CASE 
            WHEN c.data_type = 'USER-DEFINED' THEN 
                (SELECT string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder)
                 FROM pg_type t
                 JOIN pg_enum e ON t.oid = e.enumtypid
                 WHERE t.typname = c.udt_name)
            ELSE NULL
        END as enum_values
    FROM information_schema.columns c
    WHERE c.table_schema IN :schemas
    ORDER BY c.table_schema, c.table_name, c.ordinal_position
    LIMIT :lim
    """
    stmt = text(q).bindparams(bindparam("schemas", expanding=True))
    with engine.connect() as conn:
        rows = conn.execute(stmt, {"schemas": list(schemas), "lim": max_cols}).mappings().all()

    tables = {}
    for r in rows:
        key = f"{r['table_schema']}.{r['table_name']}"
        tables.setdefault(key, {"schema": r["table_schema"], "name": r["table_name"], "columns": []})
        
        col_info = {
            "name": r["column_name"], 
            "type": r["data_type"],
            "udt_name": r["udt_name"]
        }
        
        # Tambahkan enum values jika ada
        if r["enum_values"]:
            col_info["enum_values"] = r["enum_values"].split(", ")
        
        tables[key]["columns"].append(col_info)
    
    return {"tables": list(tables.values())}

SCHEMA = load_schema_snapshot()

# Index nama_tabel -> set(schema) lowercase
TABLE_TO_SCHEMAS = defaultdict(set)
for t in SCHEMA["tables"]:
    TABLE_TO_SCHEMAS[t["name"].lower()].add(t["schema"])

# Build enum index and synonym mapping
def build_enum_index(schema):
    """Build index of all enum columns and their possible values."""
    enum_index = {}
    
    for table in schema["tables"]:
        table_key = f"{table['schema']}.{table['name']}"
        
        for col in table["columns"]:
            if "enum_values" in col:
                col_name = col["name"]
                enum_values = col["enum_values"]
                
                # Key: (table, column) -> list of valid enum values
                enum_index[(table_key, col_name)] = enum_values
    
    return enum_index

ENUM_INDEX = build_enum_index(SCHEMA)

# Definisikan synonym mapping yang bisa di-extend
ENUM_SYNONYMS = {
    # Format: "enum_value_in_db": ["synonym1", "synonym2", ...]
    "intern": ["magang", "internship", "trainee"],
    "probation": ["percobaan", "masa percobaan", "probasi", "trial"],
    "permanent": ["tetap", "karyawan tetap", "permanen", "full-time"],
    "contract": ["kontrak", "freelance", "kontrak kerja"],
}

def normalize_enum_values(sql: str, enum_index: dict, synonym_map: dict) -> str:
    """
    Replace synonym enum values dengan nilai yang benar dari database.
    Bekerja untuk semua enum di semua tabel.
    """
    # Untuk setiap enum column yang ada
    for (table_key, col_name), valid_values in enum_index.items():
        # Extract table name tanpa schema
        table_name = table_key.split(".")[-1]
        
        # Untuk setiap valid value, cek apakah ada synonym yang perlu di-replace
        for valid_value in valid_values:
            synonyms = synonym_map.get(valid_value.lower(), [])
            
            for synonym in synonyms:
                # Pattern untuk menangkap: column = 'synonym'
                # Case insensitive untuk synonym
                pattern = rf"(\b{col_name}\s*=\s*['\"])({re.escape(synonym)})(['\"])"
                replacement = rf"\1{valid_value}\3"
                sql = re.sub(pattern, replacement, sql, flags=re.I)
                
                # Pattern untuk menangkap: column IN ('synonym', ...)
                pattern_in = rf"(\b{col_name}\s+IN\s*\([^)]*['\"])({re.escape(synonym)})(['\"][^)]*\))"
                sql = re.sub(pattern_in, replacement, sql, flags=re.I)
    
    return sql

def qualify_tables(sql: str) -> str:
    def _qualify(m):
        full = m.group(1)      # schema.table atau table
        alias = m.group(2) or ""
        if "." in full:        # sudah qualified
            return m.group(0)
        tbl_key = full.strip('"').lower()
        schema = DEFAULT_SCHEMA
        if tbl_key in TABLE_TO_SCHEMAS:
            schemas = TABLE_TO_SCHEMAS[tbl_key]
            if len(schemas) == 1:
                schema = next(iter(schemas))
            elif DEFAULT_SCHEMA in schemas:
                schema = DEFAULT_SCHEMA
        qualified = f"{schema}.{full}"
        kw = m.group(0).split()[0]  # FROM atau JOIN
        return f"{kw} {qualified}" + (f" {alias}" if alias else "")
    sql = re.sub(rf'(?i)\bFROM\s+({TABLE_REF})(?:\s+(?:AS\s+)?({ALIAS_REF}))?', _qualify, sql)
    sql = re.sub(rf'(?i)\bJOIN\s+({TABLE_REF})(?:\s+(?:AS\s+)?({ALIAS_REF}))?', _qualify, sql)
    return sql

def clean_unnecessary_qualifiers(sql: str) -> str:
    """
    Remove table/schema prefixes from columns in single-table queries.
    Also clean PostgreSQL built-in functions for all queries.
    Safety net for LLM inconsistencies.
    """
    # STEP 1: Clean PostgreSQL built-in functions that shouldn't have schema prefix
    # Pattern: employee.CURRENT_DATE, employee.NOW(), etc
    # This applies to ALL queries (single-table and JOINs)
    pg_functions = ['CURRENT_DATE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP', 'NOW', 'LOCALTIME', 'LOCALTIMESTAMP']
    for func in pg_functions:
        # Remove schema prefix from functions: employee.CURRENT_DATE -> CURRENT_DATE
        # Also handle: schema.table.CURRENT_DATE -> CURRENT_DATE
        sql = re.sub(rf'\b\w+\.\w+\.({func})\b', rf'\1', sql, flags=re.I)  # schema.table.FUNC
        sql = re.sub(rf'\b\w+\.({func})\b', rf'\1', sql, flags=re.I)       # schema.FUNC or table.FUNC
    
    # STEP 2: For single-table queries, also clean column qualifiers
    # Skip jika ada JOIN - kualifikasi mungkin diperlukan untuk columns
    if re.search(r'\bJOIN\b', sql, re.I):
        return sql
    
    # Ekstrak nama tabel dari FROM clause
    # Pattern: FROM schema.table atau FROM schema.table alias
    from_match = re.search(r'\bFROM\s+(\w+)\.(\w+)(?:\s+(?:AS\s+)?(\w+))?', sql, re.I)
    if not from_match:
        return sql
    
    schema, table, alias = from_match.groups()
    
    # Split SQL menjadi bagian FROM dan sisanya
    parts = re.split(r'\bFROM\b', sql, maxsplit=1, flags=re.I)
    if len(parts) != 2:
        return sql
    
    before_from = parts[0]  # SELECT ... 
    from_and_after = parts[1]  # schema.table WHERE ...
    
    # Clean di bagian before_from (SELECT clause)
    before_from = re.sub(rf'\b{re.escape(schema)}\.{re.escape(table)}\.(\w+)', r'\1', before_from)
    before_from = re.sub(rf'\b{re.escape(schema)}\.(\w+)', r'\1', before_from)  # schema.column
    if not alias:
        before_from = re.sub(rf'\b{re.escape(table)}\.(\w+)', r'\1', before_from)
    if alias:
        before_from = re.sub(rf'\b{re.escape(alias)}\.(\w+)', r'\1', before_from)
    
    # Split from_and_after menjadi table reference dan WHERE/ORDER BY/GROUP BY clause
    where_parts = re.split(r'\b(WHERE|ORDER BY|GROUP BY|HAVING|LIMIT)\b', from_and_after, maxsplit=1, flags=re.I)
    
    if len(where_parts) >= 3:
        table_part = where_parts[0]  # schema.table
        keyword = where_parts[1]      # WHERE, ORDER BY, etc
        rest_clause = where_parts[2]  # EXTRACT(...) = 2023
        
        # Clean di rest clause
        rest_clause = re.sub(rf'\b{re.escape(schema)}\.{re.escape(table)}\.(\w+)', r'\1', rest_clause)
        rest_clause = re.sub(rf'\b{re.escape(schema)}\.(\w+)', r'\1', rest_clause)  # schema.column
        if not alias:
            rest_clause = re.sub(rf'\b{re.escape(table)}\.(\w+)', r'\1', rest_clause)
        if alias:
            rest_clause = re.sub(rf'\b{re.escape(alias)}\.(\w+)', r'\1', rest_clause)
        
        # Reconstruct
        sql = before_from + ' FROM' + table_part + ' ' + keyword + rest_clause
    else:
        # Tidak ada WHERE/ORDER BY clause
        sql = before_from + ' FROM' + from_and_after
    
    return sql

def truncate_for_prompt(s: str, max_chars: int) -> str:
    return s if len(s) <= max_chars else s[:max_chars]

def build_enum_documentation(enum_index: dict, synonym_map: dict) -> str:
    """Build documentation string for enum columns."""
    if not enum_index:
        return ""
    
    doc = "\n**ENUM Columns & Valid Values:**\n"
    
    for (table_key, col_name), valid_values in enum_index.items():
        doc += f"\n{table_key}.{col_name}:\n"
        # Format enum values dengan quotes
        quoted_values = [f"'{v}'" for v in valid_values]
        doc += f"  Valid values: {', '.join(quoted_values)}\n"
        
        # Add synonyms if any
        synonyms_doc = []
        for valid_value in valid_values:
            syns = synonym_map.get(valid_value.lower(), [])
            if syns:
                quoted_syns = [f"'{s}'" for s in syns]
                synonyms_doc.append(f"    '{valid_value}' can be expressed as: {', '.join(quoted_syns)}")
        
        if synonyms_doc:
            doc += "  Synonyms:\n" + "\n".join(synonyms_doc) + "\n"
    
    return doc

ENUM_DOC = build_enum_documentation(ENUM_INDEX, ENUM_SYNONYMS)

SYSTEM = f"""
You convert natural language to safe, read-only PostgreSQL for the connected database.

Rules:
- Output ONLY a JSON object with keys: sql, params, explanation.
- Exactly one SELECT statement, no semicolons.
- Always fully qualify every table as schema.table in FROM and JOIN clauses.
- Prefer schema "{DEFAULT_SCHEMA}" when user does not specify.
- SELECT * is allowed.
- Use positional parameters :p1, :p2, ... if you need parameters.
- **IMPORTANT**: Write the "explanation" field in simple, easy-to-understand Indonesian language for non-technical users. Avoid technical jargon. Explain what the query does in plain terms.

**IMPORTANT - Column References:**
- When selecting from a SINGLE table, use bare column names (e.g., hire_date, first_name)
- Only qualify columns (e.g., e.first_name) when joining MULTIPLE tables to avoid ambiguity
- WRONG: SELECT employee.first_name FROM employee.employees WHERE employee.hire_date = '2023-01-01'
- CORRECT: SELECT first_name FROM employee.employees WHERE hire_date = '2023-01-01'
- CORRECT (with JOIN): SELECT e.first_name, d.dept_name FROM employee.employees e JOIN employee.departments d ON e.dept_id = d.dept_id

**PostgreSQL Functions:**
- Use built-in functions WITHOUT schema prefix: CURRENT_DATE, NOW(), CURRENT_TIMESTAMP
- WRONG: employee.CURRENT_DATE or WHERE date = employee.NOW()
- CORRECT: CURRENT_DATE or WHERE date = NOW()

{ENUM_DOC}

Examples:
1. Single table query:
   Q: "Show employees hired in 2023"
   A: {{"sql": "SELECT emp_id, first_name, last_name, hire_date FROM employee.employees WHERE EXTRACT(YEAR FROM hire_date) = 2023", "params": [], "explanation": "Menampilkan daftar karyawan yang bergabung di tahun 2023"}}

2. Join query:
   Q: "Show employees with their department names"
   A: {{"sql": "SELECT e.emp_id, e.first_name, d.dept_name FROM employee.employees e JOIN employee.departments d ON e.dept_id = d.dept_id", "params": [], "explanation": "Menampilkan nama karyawan beserta departemen tempat mereka bekerja"}}

3. Enum handling:
   Q: "Show employees who are interns"
   A: {{"sql": "SELECT emp_id, first_name, last_name, status FROM employee.employees WHERE status = 'intern'", "params": [], "explanation": "Menampilkan daftar karyawan dengan status magang"}}

4. Current date query:
   Q: "Show leave requests this year"
   A: {{"sql": "SELECT emp_id, leave_type, start_date FROM employee.leave_requests WHERE EXTRACT(YEAR FROM start_date) = EXTRACT(YEAR FROM CURRENT_DATE)", "params": [], "explanation": "Menampilkan pengajuan cuti yang diajukan tahun ini"}}

5. Aggregation query:
   Q: "How many employees per department?"
   A: {{"sql": "SELECT d.dept_name, COUNT(e.emp_id) as employee_count FROM employee.employees e JOIN employee.departments d ON e.dept_id = d.dept_id GROUP BY d.dept_id, d.dept_name", "params": [], "explanation": "Menghitung jumlah karyawan di setiap departemen"}}

SCHEMA: {truncate_for_prompt(json.dumps(SCHEMA), SCHEMA_SNIPPET_CHARS)}
"""

def llm_propose_sql(nl_query: str) -> dict:
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": nl_query},
        ],
        temperature=0.1,
    )
    content = resp.choices[0].message.content
    try:
        return json.loads(content)
    except Exception:
        m = re.search(r"\{.*\}", content, re.S)
        if not m:
            raise RuntimeError("LLM tidak mengembalikan JSON yang valid.")
        return json.loads(m.group(0))

# ---------------- UI ----------------
st.set_page_config(page_title="NL2SQL", page_icon="🧠", layout="wide")
st.title("🧠 NL2SQL")
st.caption("Tanya database menggunakan natural language.")

tab_chat, tab_detail = st.tabs(["💬 Chatbot", "🔍 Detail"])

# ========== TAB DETAIL ==========
with tab_detail:
    # Diagnostik ringkas
    with st.expander("Diagnostik koneksi dan schema"):
        try:
            with engine.connect() as conn:
                db = conn.execute(text("select current_database()")).scalar_one()
                schemata = conn.execute(text("select schema_name from information_schema.schemata order by 1")).scalars().all()
                cnt = conn.execute(text("select count(*) from information_schema.tables where table_schema = :s"), {"s": DEFAULT_SCHEMA}).scalar_one()
            st.write("DB:", db)
            st.write("Schemata terlihat:", schemata)
            st.write(f"Jumlah tabel di {DEFAULT_SCHEMA}:", cnt)
            st.write(f"Tabel terdeteksi oleh snapshot: {len(SCHEMA['tables'])}")
        except Exception as e:
            st.error(f"Gagal diagnostik: {e}")

    # Input NL
    q = st.text_area(
        "Pertanyaan natural language",
        value="Tampilkan semua perusahaan urutkan berdasarkan company_id ascending",
        height=100,
    )

    if st.button("Jalankan", type="primary", use_container_width=True):
        if not q.strip():
            st.warning("Masukkan pertanyaan.")
            st.stop()

        with st.spinner("Menghasilkan SQL dari LLM..."):
            try:
                args = llm_propose_sql(q.strip())
            except Exception as e:
                st.error(f"Gagal memanggil LLM: {e}")
                st.stop()

        with st.expander("LLM raw JSON", expanded=False):
            st.code(json.dumps(args, indent=2), language="json")

        sql_raw = (args.get("sql") or "").strip()
        params_raw = args.get("params", [])
        explanation = args.get("explanation", "")

        if not sql_raw:
            st.error("LLM tidak mengembalikan field 'sql'.")
            st.stop()

        # Schema qualification
        sql_qualified = qualify_tables(sql_raw)
        
        # Clean unnecessary qualifiers
        sql_cleaned = clean_unnecessary_qualifiers(sql_qualified)
        
        # Normalize enum synonyms
        sql_final = normalize_enum_values(sql_cleaned, ENUM_INDEX, ENUM_SYNONYMS)

        # Safety guard
        st.markdown("### SQL - setelah post-processing")
        st.code(sql_final, language="sql")
        if explanation:
            st.markdown(f"**Penjelasan LLM:** {explanation}")

        if not is_safe_sql(sql_final):
            st.error("Query tidak aman. Hanya SELECT tanpa semicolon yang diizinkan.")
            st.stop()

        # Normalize params
        sql_norm, pmap = normalize_params_style(sql_final, params_raw)
        st.markdown("### SQL - normalized untuk eksekusi")
        st.code(sql_norm, language="sql")
        with st.expander("Parameter map"):
            st.json(pmap)

        # EXPLAIN
        with st.spinner("EXPLAIN..."):
            try:
                plan = run_explain(sql_norm, pmap)
                st.markdown("### EXPLAIN")
                st.code("\n".join(" ".join(map(str, r)) for r in plan))
            except SQLAlchemyError as e:
                st.error(f"SQL invalid saat EXPLAIN: {e}")
                st.stop()

        # Eksekusi
        with st.spinner("Menjalankan query..."):
            try:
                df = run_query(sql_norm, pmap, limit=DEFAULT_ROW_LIMIT)
                if df.empty:
                    st.info("Tidak ada hasil.")
                else:
                    st.markdown("### Hasil")
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    csv_bytes = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "Download CSV",
                        data=csv_bytes,
                        file_name="result.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
            except SQLAlchemyError as e:
                st.error(f"DB error: {e}")

# ========== TAB CHATBOT ==========
with tab_chat:
    # Initialize loading state
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False

    # Shortcut buttons untuk pertanyaan umum
    st.markdown("**📌 Shortcut Pertanyaan:**")
    col1, col2, col3 = st.columns(3)
    
    shortcuts = {
        "📋 Semua karyawan": "tampilkan semua karyawan",
        "👥 Karyawan tetap": "tampilkan karyawan dengan status tetap",
        "🎓 Karyawan magang": "tampilkan karyawan yang sedang magang",
        "📅 Rekrut 2023": "siapa saja karyawan yang direkrut tahun 2023?",
        "💰 Gaji tertinggi": "tampilkan 10 karyawan dengan gaji tertinggi",
        "🏢 Per departemen": "berapa jumlah karyawan di setiap departemen?",
    }
    
    if "selected_shortcut" not in st.session_state:
        st.session_state.selected_shortcut = None
    
    for i, (label, query) in enumerate(shortcuts.items()):
        col_idx = i % 3
        cols = [col1, col2, col3]
        with cols[col_idx]:
            if st.button(label, key=f"shortcut_{i}", use_container_width=True):
                st.session_state.selected_shortcut = query

    st.markdown("---")

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # Container untuk chat messages (agar input selalu di bawah)
    chat_container = st.container()
    
    with chat_container:
        # render history
        for m in st.session_state.chat_messages:
            with st.chat_message(m["role"]):
                if m["role"] == "assistant" and isinstance(m["content"], dict):
                    # render paket hasil (tanpa SQL dan EXPLAIN untuk chatbot)
                    pkg = m["content"]
                    if "text" in pkg:
                        st.write(pkg["text"])
                    # SQL dan EXPLAIN tidak ditampilkan di chatbot
                    if "df" in pkg and isinstance(pkg["df"], pd.DataFrame):
                        if not pkg["df"].empty:
                            st.dataframe(pkg["df"], use_container_width=True, hide_index=True)
                        else:
                            st.info("Tidak ada hasil.")
                else:
                    st.write(m["content"])

    # Input selalu di-render di luar container, jadi selalu di bawah
    user_q = st.chat_input("Tanyakan data kamu...")
    
    # Check if shortcut was clicked
    if st.session_state.selected_shortcut:
        user_q = st.session_state.selected_shortcut
        st.session_state.selected_shortcut = None
    
    if user_q:
        # Set processing flag dan tambahkan user message
        st.session_state.is_processing = True
        st.session_state.chat_messages.append({"role": "user", "content": user_q})
        
        # Tambahkan placeholder untuk loading
        st.session_state.chat_messages.append({
            "role": "assistant", 
            "content": {"text": "⏳ Menghasilkan SQL dan menjalankan query..."}
        })
        
        # Rerun untuk menampilkan loading message
        st.rerun()
    
    # Proses query jika ada yang pending
    if st.session_state.is_processing and len(st.session_state.chat_messages) > 0:
        last_msg = st.session_state.chat_messages[-1]
        if last_msg["role"] == "assistant" and last_msg["content"].get("text", "").startswith("⏳"):
            # Ambil user query dari message sebelumnya
            user_query = st.session_state.chat_messages[-2]["content"]
            
            # Hapus loading message
            st.session_state.chat_messages.pop()
            
            # Proses pipeline
            try:
                args = llm_propose_sql(user_query.strip())
                sql_raw = (args.get("sql") or "").strip()
                params_raw = args.get("params", [])
                explanation = args.get("explanation", "")

                if not sql_raw:
                    raise RuntimeError("LLM tidak mengembalikan field 'sql'.")

                sql_qualified = qualify_tables(sql_raw)
                sql_cleaned = clean_unnecessary_qualifiers(sql_qualified)
                sql_final = normalize_enum_values(sql_cleaned, ENUM_INDEX, ENUM_SYNONYMS)
                
                if not is_safe_sql(sql_final):
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": {"text": "Query diblokir karena tidak aman."}
                    })
                else:
                    sql_norm, pmap = normalize_params_style(sql_final, params_raw)

                    # EXPLAIN (hanya untuk validasi, tidak disimpan)
                    try:
                        _ = run_explain(sql_norm, pmap)
                    except SQLAlchemyError as e:
                        st.session_state.chat_messages.append({
                            "role": "assistant",
                            "content": {
                                "text": f"❌ SQL tidak valid: {e}"
                            }
                        })
                        st.session_state.is_processing = False
                        st.rerun()

                    # RUN
                    df = None
                    try:
                        df = run_query(sql_norm, pmap, limit=DEFAULT_ROW_LIMIT)
                    except SQLAlchemyError as e:
                        st.session_state.chat_messages.append({
                            "role": "assistant",
                            "content": {
                                "text": f"❌ Database error: {e}"
                            }
                        })
                        st.session_state.is_processing = False
                        st.rerun()

                    # Render hasil (tanpa SQL dan EXPLAIN)
                    pkg = {
                        "text": explanation or "Berikut hasil query:",
                    }
                    if isinstance(df, pd.DataFrame):
                        pkg["df"] = df
                    else:
                        pkg["df"] = pd.DataFrame()

                    st.session_state.chat_messages.append({"role": "assistant", "content": pkg})

            except Exception as e:
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": {"text": f"Gagal memproses: {e}"}
                })
            
            # Reset processing flag
            st.session_state.is_processing = False
            
            # Rerun untuk menampilkan pesan baru
            st.rerun()
