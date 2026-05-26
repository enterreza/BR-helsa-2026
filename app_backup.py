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
    
    # Menambahkan kolom Rajal dan Ranap ke dalam daftar kolom numerik yang dibersihkan
    numeric_cols = [
        'Actual Revenue (Total)', 'Actual EBITDA', 'Target Revenue (Total)', 'Target EBITDA',
        'Volume Outpatient', 'Volume Inpatient'  # Menyesuaikan nama kolom Rajal/Ranap dari Sheets
    ]

    for year, s_name in sheets.items():
        try:
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={s_name}"
            df_tmp = pd.read_csv(url, dtype=str)
            df_tmp.columns = [str(col).strip() for col in df_tmp.columns]
            
            # Kecocokan nama kolom alternatif jika di sheet namanya berbeda (Rajal/Ranap)
            if 'Volume Rajal' in df_tmp.columns: df_tmp.rename(columns={'Volume Rajal': 'Volume Outpatient'}, inplace=True)
            if 'Volume Ranap' in df_tmp.columns: df_tmp.rename(columns={'Volume Ranap': 'Volume Inpatient'}, inplace=True)

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
                
                # KPI Volume Baru
                rajal_26 = df_2026['Volume Outpatient'].sum()
                ranap_26 = df_2026['Volume Inpatient'].sum()

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.subheader("Financial Performance")
                    st.write(f"**Revenue 2026:** {format_rupiah_human(rev_act_26)} ({ach_rev:.1f}% vs Tar)")
                    st.write(f"**EBITDA 2026:** {format_rupiah_human(ebit_act_26)} ({ach_ebit:.1f}% vs Tar)")
                with col2:
                    st.subheader("Profitability & Margin")
                    st.write(f"**EBITDA Margin:** {ebitda_margin_26:.2f}%")
                    st.write(":green[Kondisi Sehat]" if ebitda_margin_26 >= 15 else ":orange[Butuh Efisiensi]")
                with col3:
                    st.subheader("Operational Volume (2026)")
                    st.write(f"**Rawat Jalan (Rajal):** {rajal_26:,.0f} Pasien")
                    st.write(f"**Rawat Inap (Ranap):** {ranap_26:,.0f} Pasien")

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
                    yr_data = df_q_yoy[df_q_yoy['Tahun'] == yr]
                    fig_q_comb.add_trace(go.Scatter(x=yr_data['Kuartal'], y=yr_data['Actual EBITDA'], name=f"EBITDA {yr}", mode='lines+markers', line=dict(color=color, width=3, dash=dash)))

            # Growth Annotations
            if "2025" in selected_tahun and "2026" in selected_tahun:
                for q in df_q_yoy['Kuartal'].unique():
                    rows = df_q_yoy[df_q_yoy['Kuartal'] == q]
                    v26_r = rows[rows['Tahun'] == '2026']['Actual Revenue (Total)'].sum()
                    v25_r = rows[rows['Tahun'] == '2025']['Actual Revenue (Total)'].sum()
                    if v26_r != 0 and v25_r != 0:
                        pct_r = ((v26_r - v25_r) / v25_r * 100)
                        fig_q_comb.add_annotation(x=q, y=v26_r, text=f"{'▲' if pct_r >= 0 else '▼'} {abs(pct_r):.1f}%", showarrow=False, yshift=15, font=dict(color="#1E8449" if pct_r>=0 else "#C0392B", size=10, family="Arial Bold"))
                    v26_e = rows[rows['Tahun'] == '2026']['Actual EBITDA'].sum()
                    v25_e = rows[rows['Tahun'] == '2025']['Actual EBITDA'].sum()
                    if v26_e != 0 and v25_e != 0:
                        pct_e = ((v26_e - v25_e) / abs(v25_e) * 100)
                        fig_q_comb.add_annotation(x=q, y=v26_e, text=f"{'▲' if pct_e >= 0 else '▼'} {abs(pct_e):.1f}%", showarrow=False, yshift=-20, font=dict(color="#D35400", size=9, family="Arial"))

            st.plotly_chart(fig_q_comb, use_container_width=True)

            # --- ROW 3: GRAFIK BARU TREN OPERASIONAL (RAJAL & RANAP) ---
            st.subheader("📅 Analisis Tren Volume Operasional: Rawat Jalan vs Rawat Inap")
            df_m_ops = df_filtered.groupby(['Bulan', 'Tahun'])[['Volume Outpatient', 'Volume Inpatient']].sum().reset_index()
            df_m_ops['Bulan'] = pd.Categorical(df_m_ops['Bulan'], categories=month_order, ordered=True)
            df_m_ops = df_m_ops.sort_values(['Bulan', 'Tahun'])

            fig_ops = go.Figure()
            # Bar untuk Rawat Jalan (Outpatient)
            for yr, color in zip(["2025", "2026"], ["#A9DFBF", "#27AE60"]):
                if yr in selected_tahun:
                    data_yr = df_m_ops[df_m_ops['Tahun'] == yr]
                    fig_ops.add_trace(go.Bar(x=data_yr['Bulan'], y=data_yr['Volume Outpatient'], name=f"Rajal (Outpatient) {yr}", marker_color=color, offsetgroup=f"rajal_{yr}"))
            
            # Line untuk Rawat Inap (Inpatient) - Menggunakan Sumbu Y Kedua jika volumenya jomplang
            for yr, color, dash in zip(["2025", "2026"], ["#F9E79F", "#D4AC0D"], ["dash", "solid"]):
                if yr in selected_tahun:
                    data_yr = df_m_ops[df_m_ops['Tahun'] == yr]
                    fig_ops.add_trace(go.Scatter(x=data_yr['Bulan'], y=data_yr['Volume Inpatient'], name=f"Ranap (Inpatient) {yr}", mode='lines+markers', line=dict(color=color, width=3, dash=dash)))

            fig_ops.update_layout(yaxis_tickformat=',.0f', template="plotly_white", barmode='group', hovermode="x unified")
            st.plotly_chart(fig_ops, use_container_width=True)

            # --- ROW 4: TREN PER RS & KOMPOSISI ---
            col_x, col_y = st.columns(2)
            with col_x:
                st.subheader("🏥 Tren Pendapatan per RS")
                df_rs_actual = df_filtered.pivot_table(index='Bulan', columns='Cabang', values='Actual Revenue (Total)', aggfunc='sum').reindex(month_order)
                fig_line = go.Figure()
                for rs in df_rs_actual.columns:
                    fig_line.add_trace(go.Scatter(x=df_rs_actual.index, y=df_rs_actual[rs], name=rs, mode='lines+markers', line=dict(color=COLOR_MAP.get(rs, DEFAULT_COLORS[0]))))
                fig_line.update_layout(yaxis_tickformat=',.0f', template="plotly_white")
                st.plotly_chart(fig_line, use_container_width=True)
            with col_y:
                st.subheader("📊 Komposisi Volume Rawat Jalan per RS")
                fig_pie = px.pie(df_filtered, values='Volume Outpatient', names='Cabang', hole=0.4, color='Cabang', color_discrete_map=COLOR_MAP)
                fig_pie.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)

            # --- ROW 5: TABEL DETAIL ---
            st.markdown("---")
            st.subheader("🔍 Tabel Informasi Detail & Fitur Export")
            
            df_table = df_filtered.copy()
            df_table['EBITDA Margin %'] = (df_table['Actual EBITDA'] / df_table['Actual Revenue (Total)'] * 100).fillna(0)
            
            df_display = df_table[['Tahun', 'Kuartal', 'Bulan', 'Cabang', 'Actual Revenue (Total)', 'Actual EBITDA', 'EBITDA Margin %', 'Volume Outpatient', 'Volume Inpatient']].copy()
            df_display.rename(columns={'Volume Outpatient': 'Vol Rajal', 'Volume Inpatient': 'Vol Ranap'}, inplace=True)
            df_display = df_display.sort_values(['Cabang', 'Tahun', 'Bulan'], ascending=[True, False, True])

            csv_data = df_display.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Data Report (CSV Format)",
                data=csv_data,
                file_name="Performance_Report_Helsa_Operational.csv",
                mime="text/csv",
                use_container_width=True
            )

            st.dataframe(
                df_display, 
                use_container_width=True, 
                column_config={
                    "Actual Revenue (Total)": st.column_config.NumberColumn("Actual Revenue", format="%,.0f"), 
                    "Actual EBITDA": st.column_config.NumberColumn("Actual EBITDA", format="%,.0f"),
                    "EBITDA Margin %": st.column_config.NumberColumn("EBITDA Margin", format="%.2f%%"),
                    "Vol Rajal": st.column_config.NumberColumn("Vol Rajal", format="%,.0f"),
                    "Vol Ranap": st.column_config.NumberColumn("Vol Ranap", format="%,.0f")
                }
            )

except Exception as e:
    st.error(f"Sistem Error saat memuat fitur dashboard terbaru: {e}")
