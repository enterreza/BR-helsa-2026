import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import os

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
    
    # Standar penamaan kolom internal script
    numeric_cols = [
        'Actual Revenue (Total)', 'Actual EBITDA', 'Target Revenue (Total)', 'Target EBITDA',
        'Actual Revenue Outpatient', 'Actual Revenue Inpatient',
        'Volume Outpatient', 'Volume Inpatient'
    ]

    for year, s_name in sheets.items():
        try:
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={s_name}"
            df_tmp = pd.read_csv(url, dtype=str)
            df_tmp.columns = [str(col).strip() for col in df_tmp.columns]
            
            # --- AGRESF COLUMN MAPPING (MEMPROSES SEGALA VARIASI NAMA KOLOM SPREADSHEET) ---
            for col in df_tmp.columns:
                # 1. Mapping Revenue Rajal
                if col in ['Revenue Rajal', 'Actual Revenue Rajal', 'Rev Rajal', 'Revenue Outpatient', 'Actual Outpatient Revenue']:
                    df_tmp.rename(columns={col: 'Actual Revenue Outpatient'}, inplace=True)
                # 2. Mapping Revenue Ranap
                if col in ['Revenue Ranap', 'Actual Revenue Ranap', 'Rev Ranap', 'Revenue Inpatient', 'Actual Inpatient Revenue']:
                    df_tmp.rename(columns={col: 'Actual Revenue Inpatient'}, inplace=True)
                # 3. Mapping Volume Rajal
                if col in ['Volume Rajal', 'Vol Rajal', 'Volume Outpatient', 'Outpatient Volume']:
                    df_tmp.rename(columns={col: 'Volume Outpatient'}, inplace=True)
                # 4. Mapping Volume Ranap
                if col in ['Volume Ranap', 'Vol Ranap', 'Volume Inpatient', 'Inpatient Volume']:
                    df_tmp.rename(columns={col: 'Volume Inpatient'}, inplace=True)

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

        df_filtered = df_all[
            (df_all['Tahun'].isin(selected_tahun)) & 
            (df_all['Cabang'].isin(selected_cabang)) & 
            (df_all['Bulan'].isin(selected_bulan))
        ].copy()

        df_2026 = df_all[(df_all['Tahun'] == '2026') & (df_all['Cabang'].isin(selected_cabang)) & (df_all['Bulan'].isin(selected_bulan))]

        st.title("🏥 Performance Dashboard Helsa Group")
        st.markdown("---")

        if not df_filtered.empty:
            # --- ROW 1: KPI CARDS ---
            if not df_2026.empty:
                rev_act_26 = df_2026['Actual Revenue (Total)'].sum()
                rev_tar_26 = df_2026['Target Revenue (Total)'].sum()
                ach_rev = (rev_act_26 / rev_tar_26 * 100) if rev_tar_26 > 0 else 0
                
                ebit_act_26 = df_2026['Actual EBITDA'].sum()
                ebit_tar_26 = df_2026['Target EBITDA'].sum()
                ach_ebit = (ebit_act_26 / ebit_tar_26 * 100) if ebit_tar_26 > 0 else 0
                ebitda_margin_26 = (ebit_act_26 / rev_act_26 * 100) if rev_act_26 > 0 else 0
                
                rev_rajal_26 = df_2026['Actual Revenue Outpatient'].sum()
                rev_ranap_26 = df_2026['Actual Revenue Inpatient'].sum()

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.subheader("Financial Revenue")
                    st.write(f"**Total Revenue:** {format_rupiah_human(rev_act_26)} ({ach_rev:.1f}% vs Tar)")
                    st.write(f"**EBITDA:** {format_rupiah_human(ebit_act_26)} ({ach_ebit:.1f}% vs Tar)")
                with col2:
                    st.subheader("Revenue Breakdown (2026)")
                    st.write(f"**Revenue Rajal:** {format_rupiah_human(rev_rajal_26)}")
                    st.write(f"**Revenue Ranap:** {format_rupiah_human(rev_ranap_26)}")
                with col3:
                    st.subheader("Profitability & Margin")
                    st.write(f"**EBITDA Margin:** {ebitda_margin_26:.2f}%")
                    st.write(":green[Kondisi Sehat]" if ebitda_margin_26 >= 15 else ":orange[Butuh Efisiensi]")

                st.markdown("---")

            # --- ROW 2: TREN YOY FINANSIAL ---
            st.subheader("📊 Analisis Tren Financial YoY per Kuartal")
            df_q_yoy = df_filtered.groupby(['Kuartal', 'Tahun'])[['Actual Revenue (Total)', 'Actual EBITDA']].sum().reset_index()
            df_q_yoy['Kuartal'] = pd.Categorical(df_q_yoy['Kuartal'], categories=quarter_order, ordered=True)
            df_q_yoy = df_q_yoy.sort_values(['Kuartal', 'Tahun'])
            
            fig_q_comb = go.Figure()
            for yr, color in zip(["2025", "2026"], ["#AED6F1", "#2E86C1"]):
                if yr in selected_tahun:
                    yr_data = df_q_yoy[df_q_yoy['Tahun'] == yr]
                    fig_q_comb.add_trace(go.Bar(x=yr_data['Kuartal'], y=yr_data['Actual Revenue (Total)'], name=f"Rev {yr}", marker_color=color, offsetgroup=yr))
            for yr, color, dash in zip(["2025", "2026"], ["#FAD7A0", "#D35400"], ["dash", "solid"]):
                if yr in selected_tahun:
