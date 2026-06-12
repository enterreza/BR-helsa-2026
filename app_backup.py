import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import os
from io import BytesIO

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Dashboard Performance Helsa", layout="wide", page_icon="📈")

# --- KONFIGURASI KREDENSIAL LOGIN ---
USER_CREDENTIALS = {
    "admin": "helsa2026",
    "management": "helsa2026"
}

# --- INISIALISASI SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# =====================================================================
# --- 1. PROSES PENGECEKAN HALAMAN LOGIN ---
# =====================================================================
if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("")
        st.write("")
        LOGO_FILE = "HELSA Rumah sakit.png"
        if os.path.exists(LOGO_FILE):
            st.image(LOGO_FILE, use_container_width=False, width=250)
        
        st.subheader("🔐 Silakan Login Terlebih Dahulu")
        
        username = st.text_input("Username", placeholder="Masukkan username Anda")
        password = st.text_input("Password", type="password", placeholder="Masukkan password Anda")
        
        if st.button("Login", use_container_width=True):
            if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
                st.session_state["logged_in"] = True
                st.success("Login Berhasil! Membuka Dashboard...")
                st.rerun()
            else:
                st.error("❌ Username atau Password salah. Silakan coba lagi.")
    st.stop()

# =====================================================================
# --- 2. JIKA SUDAH LOGIN, TAMPILKAN SELURUH DASHBOARD DI BAWAH INI ---
# =====================================================================

if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state["logged_in"] = False
    st.rerun()

LOGO_FILE = "HELSA Rumah sakit.png"
if os.path.exists(LOGO_FILE):
    st.image(LOGO_FILE, use_container_width=False, width=250)

COLOR_MAP = {
    "Jatirahayu": "#636EFA", 
    "Cikampek": "#EF553B",   
    "Citeureup": "#00CC96",  
    "Ciputat": "#AB63FA",    
}
DEFAULT_COLORS = px.colors.qualitative.Plotly

def format_rupiah_human(n):
    prefix = "-" if n < 0 else ""
    val = abs(n)
    if val >= 1_000_000_000:
        return f"{prefix}Rp {val / 1_000_000_000:.2f} Miliar"
    elif val >= 1_000_000:
        return f"{prefix}Rp {val / 1_000_000:.2f} Juta"
    else:
        return f"{prefix}Rp {val:,.0f}"

def clean_to_numeric(value):
    if pd.isna(value) or str(value).strip() == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    val_str = str(value).strip()
    if val_str.startswith('(') and val_str.endswith(')'):
        val_str = '-' + val_str[1:-1]
    cleaned = re.sub(r'[^0-9\-]', '', val_str)
    try:
        return float(cleaned) if cleaned != "" else 0.0
    except ValueError:
        return 0.0

def get_quarter(bulan):
    q_map = {
        'Januari': 'Q1', 'Februari': 'Q1', 'Maret': 'Q1',
        'April': 'Q2', 'Mei': 'Q2', 'Juni': 'Q2',
        'Juli': 'Q3', 'Agustus': 'Q3', 'September': 'Q3',
        'Oktober': 'Q4', 'November': 'Q4', 'Desember': 'Q4'
    }
    return q_map.get(bulan, 'Unknown')

@st.cache_data
def load_combined_data():
    sheet_id = "1oqXKKPNnlMOSBhkWi9_7Isjo_NYtHE2ytfeO-bSNMxY"
    sheets = {"2026": "app_data", "2025": "app_data_2025"}
    combined_list = []
    
    numeric_cols = [
        'Target Revenue (Total)', 'Actual Revenue (Total)',
        'Target Revenue (Rajal Total)', 'Actual Revenue (Rajal Total)',
        'Target Revenue (Rajal JKN)', 'Actual Revenue (Rajal JKN)',
        'Target Revenue (Rajal Non JKN)', 'Actual Revenue (Rajal Non JKN)',
        'Target Revenue (Ranap Total)', 'Actual Revenue (Ranap Total)',
        'Target Revenue (Ranap JKN)', 'Actual Revenue (Ranap JKN)',
        'Target Revenue (Ranap Non JKN)', 'Actual Revenue (Ranap Non JKN)',
        'Target EBITDA', 'Actual EBITDA',
        'Aktual Kunjungan (Rajal JKN)', 'Aktual Kunjungan (Rajal Non JKN)',
        'Aktual Kunjungan (Ranap JKN)', 'Aktual Kunjungan (Ranap Non JKN)',
        'Target Kunjungan (Rajal JKN)', 'Target Kunjungan (Rajal Non JKN)',
        'Target Kunjungan (Ranap JKN)', 'Target Kunjungan (Ranap Non JKN)'
    ]

    for year, s_name in sheets.items():
        try:
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={s_name}"
            df_tmp = pd.read_csv(url, dtype=str)
            df_tmp.columns = [str(col).strip() for col in df_tmp.columns]
            
            if 'Cabang' not in df_tmp.columns: df_tmp['Cabang'] = 'Unknown'
            if 'Bulan' not in df_tmp.columns: df_tmp['Bulan'] = 'Unknown'
            
            df_tmp['Tahun'] = year
            df_tmp['Kuartal'] = df_tmp['Bulan'].apply(get_quarter)
            
            for col in numeric_cols:
                if col in df_tmp.columns:
                    df_tmp[col] = df_tmp[col].apply(clean_to_numeric)
                    df_tmp[col] = pd.to_numeric(df_tmp[col], errors='coerce').fillna(0)
                else:
                    df_tmp[col] = 0.0
            combined_list.append(df_tmp)
        except Exception:
            continue
    return pd.concat(combined_list, ignore_index=True) if combined_list else pd.DataFrame()

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Performance_Data')
    return output.getvalue()

try:
    df_all = load_combined_data()
    quarter_order = ['Q1', 'Q2', 'Q3', 'Q4']
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

    st.sidebar.header("⚙️ Filter Panel")
    if not df_all.empty:
        list_tahun = sorted(df_all['Tahun'].unique(), reverse=True)
        selected_tahun = st.sidebar.multiselect("Pilih Tahun Analisis", list_tahun, default=list_tahun)
        
        list_cabang = sorted(df_all['Cabang'].unique())
        selected_cabang = st.sidebar.multiselect("Pilih Cabang", list_cabang, default=list_cabang)
        
        available_months = [m for m in month_order if m in df_all['Bulan'].unique()]
        selected_bulan = st.sidebar.multiselect("Pilih Bulan", available_months, default=available_months)

        # 1. FILTER LAYANAN
        st.sidebar.markdown("---")
        st.sidebar.subheader("🏥 Dimensi Pelayanan")
        layanan_opsi = ["Total", "Rawat Jalan (Rajal)", "Rawat Inap (Ranap)"]
        selected_layanan = st.sidebar.radio("Pilih Tipe Pelayanan", layanan_opsi, index=0)

        # 2. FILTER SEGMEN PASIEN
        st.sidebar.subheader("💳 Segmen Pasien")
        segmen_opsi = ["Total Pasien", "JKN", "Non JKN"]
        selected_segmen = st.sidebar.selectbox("Pilih Segmen Penjamin", segmen_opsi, index=0)

        if selected_layanan == "Rawat Jalan (Rajal)":
            jkn_rev_source = "Actual Revenue (Rajal JKN)"
            non_jkn_rev_source = "Actual Revenue (Rajal Non JKN)"
            jkn_kunj_cols = ['Aktual Kunjungan (Rajal JKN)']
            non_jkn_kunj_cols = ['Aktual Kunjungan (Rajal Non JKN)']
            target_kunj_cols = ['Target Kunjungan (Rajal JKN)'] if selected_segmen == "JKN" else (['Target Kunjungan (Rajal Non JKN)'] if selected_segmen == "Non JKN" else ['Target Kunjungan (Rajal JKN)', 'Target Kunjungan (Rajal Non JKN)'])
            
            if selected_segmen == "JKN":
                target_rev_column = "Target Revenue (Rajal JKN)"
                actual_rev_column = "Actual Revenue (Rajal JKN)"
            elif selected_segmen == "Non JKN":
                target_rev_column = "Target Revenue (Rajal Non JKN)"
                actual_rev_column = "Actual Revenue (Rajal Non JKN)"
            else:
                target_rev_column = "Target Revenue (Rajal Total)"
                actual_rev_column = "Actual Revenue (Rajal Total)"
        
        elif selected_layanan == "Rawat Inap (Ranap)":
            jkn_rev_source = "Actual Revenue (Ranap JKN)"
            non_jkn_rev_source = "Actual Revenue (Ranap Non JKN)"
            jkn_kunj_cols = ['Aktual Kunjungan (Ranap JKN)']
            non_jkn_kunj_cols = ['Aktual Kunjungan (Ranap Non JKN)']
            target_kunj_cols = ['Target Kunjungan (Ranap JKN)'] if selected_segmen == "JKN" else (['Target Kunjungan (Ranap Non JKN)'] if selected_segmen == "Non JKN" else ['Target Kunjungan (Ranap JKN)', 'Target Kunjungan (Ranap Non JKN)'])
            
            if selected_segmen == "JKN":
                target_rev_column = "Target Revenue (Ranap JKN)"
                actual_rev_column = "Actual Revenue (Ranap JKN)"
            elif selected_segmen == "Non JKN":
                target_rev_column = "Target Revenue (Ranap Non JKN)"
                actual_rev_column = "Actual Revenue (Ranap Non JKN)"
            else:
                target_rev_column = "Target Revenue (Ranap Total)"
                actual_rev_column = "Actual Revenue (Ranap Total)"
        
        else:
            jkn_rev_source = ["Actual Revenue (Rajal JKN)", "Actual Revenue (Ranap JKN)"]
            non_jkn_rev_source = ["Actual Revenue (Rajal Non JKN)", "Actual Revenue (Ranap Non JKN)"]
            jkn_kunj_cols = ['Aktual Kunjungan (Rajal JKN)', 'Aktual Kunjungan (Ranap JKN)']
            non_jkn_kunj_cols = ['Aktual Kunjungan (Rajal Non JKN)', 'Aktual Kunjungan (Ranap Non JKN)']
            target_kunj_cols = ['Target Kunjungan (Rajal JKN)', 'Target Kunjungan (Rajal Non JKN)', 'Target Kunjungan (Ranap JKN)', 'Target Kunjungan (Ranap Non JKN)']
            
            if selected_segmen == "JKN":
                target_rev_column = ["Target Revenue (Rajal JKN)", "Target Revenue (Ranap JKN)"]
                actual_rev_column = ["Actual Revenue (Rajal JKN)", "Actual Revenue (Ranap JKN)"]
            elif selected_segmen == "Non JKN":
                target_rev_column = ["Target Revenue (Rajal Non JKN)", "Target Revenue (Ranap Non JKN)"]
                actual_rev_column = ["Actual Revenue (Rajal Non JKN)", "Actual Revenue (Ranap Non JKN)"]
            else:
                target_rev_column = "Target Revenue (Total)"
                actual_rev_column = "Actual Revenue (Total)"

        kunjungan_columns = jkn_kunj_cols + non_jkn_kunj_cols

        segmen_suffix = f" - {selected_segmen}" if selected_segmen != "Total Pasien" else ""
        layanan_suffix = f" ({selected_layanan})" if selected_layanan !=
