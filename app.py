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
    
    # Daftarkan semua breakdown kolom finansial pendapatan dan kunjungan dari spreadsheet Anda
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
        'Aktual Kunjungan (Ranap JKN)', 'Aktual Kunjungan (Ranap Non JKN)'
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

        # 1. FILTER LAYANAN (RAJAL / RANAP)
        st.sidebar.markdown("---")
        st.sidebar.subheader("🏥 Dimensi Pelayanan")
        layanan_opsi = ["Total", "Rawat Jalan (Rajal)", "Rawat Inap (Ranap)"]
        selected_layanan = st.sidebar.radio("Pilih Tipe Pelayanan", layanan_opsi, index=0)

        # 2. SCRIPT BARU: FILTER SEGMEN PENJAMIN PASIEN (JKN / NON JKN)
        st.sidebar.subheader("💳 Segmen Pasien")
        segmen_opsi = ["Total Pasien", "JKN", "Non JKN"]
        selected_segmen = st.sidebar.selectbox("Pilih Segmen Penjamin", segmen_opsi, index=0)

        # LOGIKA MATRIKS DINAMIS BERDASARKAN KOMBINASI DUA FILTER UTAMA
        if selected_layanan == "Rawat Jalan (Rajal)":
            if selected_segmen == "JKN":
                target_rev_column = "Target Revenue (Rajal JKN)"
                actual_rev_column = "Actual Revenue (Rajal JKN)"
                kunjungan_columns = ['Aktual Kunjungan (Rajal JKN)']
            elif selected_segmen == "Non JKN":
                target_rev_column = "Target Revenue (Rajal Non JKN)"
                actual_rev_column = "Actual Revenue (Rajal Non JKN)"
                kunjungan_columns = ['Aktual Kunjungan (Rajal Non JKN)']
            else:
                target_rev_column = "Target Revenue (Rajal Total)"
                actual_rev_column = "Actual Revenue (Rajal Total)"
                kunjungan_columns = ['Aktual Kunjungan (Rajal JKN)', 'Aktual Kunjungan (Rajal Non JKN)']
        
        elif selected_layanan == "Rawat Inap (Ranap)":
            if selected_segmen == "JKN":
                target_rev_column = "Target Revenue (Ranap JKN)"
                actual_rev_column = "Actual Revenue (Ranap JKN)"
                kunjungan_columns = ['Aktual Kunjungan (Ranap JKN)']
            elif selected_segmen == "Non JKN":
                target_rev_column = "Target Revenue (Ranap Non JKN)"
                actual_rev_column = "Actual Revenue (Ranap Non JKN)"
                kunjungan_columns = ['Aktual Kunjungan (Ranap Non JKN)']
            else:
                target_rev_column = "Target Revenue (Ranap Total)"
                actual_rev_column = "Actual Revenue (Ranap Total)"
                kunjungan_columns = ['Aktual Kunjungan (Ranap JKN)', 'Aktual Kunjungan (Ranap Non JKN)']
        
        else: # Tipe Pelayanan = Total
            if selected_segmen == "JKN":
                # Jika Layanan Total tapi segmen JKN, kita akumulasikan Rajal JKN + Ranap JKN secara manual di baris kalkulasi bawah
                target_rev_column = ["Target Revenue (Rajal JKN)", "Target Revenue (Ranap JKN)"]
                actual_rev_column = ["Actual Revenue (Rajal JKN)", "Actual Revenue (Ranap JKN)"]
                kunjungan_columns = ['Aktual Kunjungan (Rajal JKN)', 'Aktual Kunjungan (Ranap JKN)']
            elif selected_segmen == "Non JKN":
                target_rev_column = ["Target Revenue (Rajal Non JKN)", "Target Revenue (Ranap Non JKN)"]
                actual_rev_column = ["Actual Revenue (Rajal Non JKN)", "Actual Revenue (Ranap Non JKN)"]
                kunjungan_columns = ['Aktual Kunjungan (Rajal Non JKN)', 'Aktual Kunjungan (Ranap Non JKN)']
            else:
                target_rev_column = "Target Revenue (Total)"
                actual_rev_column = "Actual Revenue (Total)"
                kunjungan_columns = [
                    'Aktual Kunjungan (Rajal JKN)', 'Aktual Kunjungan (Rajal Non JKN)',
                    'Aktual Kunjungan (Ranap JKN)', 'Aktual Kunjungan (Ranap Non JKN)'
                ]

        # Membuat suffix title dinamis agar user tahu filter apa yang sedang aktif
        segmen_suffix = f" - {selected_segmen}" if selected_segmen != "Total Pasien" else ""
        layanan_suffix = f" ({selected_layanan})" if selected_layanan != "Total" else ""
        title_addon = f"{layanan_suffix}{segmen_suffix}"

        # Proses Filtering Data Dasar
        df_filtered = df_all[
            (df_all['Tahun'].isin(selected_tahun)) & 
            (df_all['Cabang'].isin(selected_cabang)) & 
            (df_all['Bulan'].isin(selected_bulan))
        ].copy()

        df_2026 = df_all[(df_all['Tahun'] == '2026') & (df_all['Cabang'].isin(selected_cabang)) & (df_all['Bulan'].isin(selected_bulan))]

        st.title(f"🏥 Performance Dashboard Helsa Group{title_addon}")
        st.markdown("---")

        if not df_filtered.empty:
            # Fungsi pembantu untuk menjumlahkan kolom pendapaatan baik berupa string tunggal maupun list
            def sum_revenue(df_target):
                if isinstance(actual_rev_column, list):
                    return df_target[actual_rev_column].sum(axis=1)
                return df_target[actual_rev_column]

            def sum_target_revenue(df_target):
                if isinstance(target_rev_column, list):
                    return df_target[target_rev_column].sum(axis=1)
                return df_target[target_rev_column]

            # Mengaplikasikan penjumlahan dinamis untuk grafik & analisis
            df_filtered['Calculated_Actual_Revenue'] = sum_revenue(df_filtered)

            # =====================================================================
            # --- ROW 1: KPI CARDS WITH ARPP ---
            # =====================================================================
            if not df_2026.empty:
                rev_act_26 = sum_revenue(df_2026).sum()
                rev_tar_26 = sum_target_revenue(df_2026).sum()
                ach_rev = (rev_act_26 / rev_tar_26 * 100) if rev_tar_26 > 0 else 0
                
                ebit_act_26 = df_2026['Actual EBITDA'].sum()
                ebit_tar_26 = df_2026['Target EBITDA'].sum()
                ach_ebit = (ebit_act_26 / ebit_tar_26 * 100) if ebit_tar_26 > 0 else 0
                ebitda_margin_26 = (ebit_act_26 / rev_act_26 * 100) if rev_act_26 > 0 else 0

                total_kunjungan_26 = df_2026[kunjungan_columns].sum().sum()
                arpp_26 = (rev_act_26 / total_kunjungan_26) if total_kunjungan_26 > 0 else 0

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.subheader("Revenue 2026")
                    st.write(f"### {format_rupiah_human(rev_act_26)}")
                    st.caption(f"Target: {format_rupiah_human(rev_tar_26)}")
                    st.write(f":green[{ach_rev:.1f}% vs Target]" if ach_rev >= 100 else f":orange[{ach_rev:.1f}% vs Target]")
                with col2:
                    st.subheader("Total EBITDA & Margin")
                    st.write(f"### {format_rupiah_human(ebit_act_26)} ({ebitda_margin_26:.1f}%)")
                    st.caption(f"Target EBITDA: {format_rupiah_human(ebit_tar_26)}")
                    st.write(f":green[{ach_ebit:.1f}% vs Target]" if ach_ebit >= 100 else f":orange[{ach_ebit:.1f}% vs Target]")
                with col3:
                    st.subheader("ARPP 2026")
                    st.write(f"### Rp {arpp_26:,.0f}")
                    st.caption("Rata-rata pendapatan finansial per satu pasien")
                    st.write(f"Total Vol: {total_kunjungan_26:,.0f} Kunjungan Pasien")

                st.markdown("---")

            # --- ROW 2: TREN YOY GRAPH ---
            st.subheader("📊 Analisis Tren & Growth YoY per Kuartal")
            df_q_yoy = df_filtered.groupby(['Kuartal', 'Tahun'])[['Calculated_Actual_Revenue', 'Actual EBITDA']].sum().reset_index()
            df_q_yoy['Kuartal'] = pd.Categorical(df_q_yoy['Kuartal'], categories=quarter_order, ordered=True)
            df_q_yoy = df_q_yoy.sort_values(['Kuartal', 'Tahun'])
            
            fig_q_comb = go.Figure()
            for yr, color in zip(["2025", "2026"], ["#AED6F1", "#2E86C1"]):
                if yr in selected_tahun:
                    yr_data = df_q_yoy[df_q_yoy['Tahun'] == yr]
                    fig_q_comb.add_trace(go.Bar(x=yr_data['Kuartal'], y=yr_data['Calculated_Actual_Revenue'], name=f"Rev {yr}", marker_color=color, offsetgroup=yr))
            
            for yr, color, dash in zip(["2025", "2026"], ["#FAD7A0", "#D35400"], ["dash", "solid"]):
                if yr in selected_tahun:
                    yr_data = df_q_yoy[df_q_yoy['Tahun'] == yr]
                    fig_q_comb.add_trace(go.Scatter(x=yr_data['Kuartal'], y=yr_data['Actual EBITDA'], name=f"EBITDA {yr}", mode='lines+markers', line=dict(color=color, width=3, dash=dash)))

            if "2025" in selected_tahun and "2026" in selected_tahun:
                for q in df_q_yoy['Kuartal'].unique():
                    rows = df_q_yoy[df_q_yoy['Kuartal'] == q]
                    v26_r = rows[rows['Tahun'] == '2026']['Calculated_Actual_Revenue'].sum()
                    v25_r = rows[rows['Tahun'] == '2025']['Calculated_Actual_Revenue'].sum()
                    if v26_r != 0 and v25_r != 0:
                        pct_r = ((v26_r - v25_r) / v25_r * 100)
                        fig_q_comb.add_annotation(x=q, y=v26_r, text=f"Growth Rev: {'▲' if pct_r >= 0 else '▼'} {abs(pct_r):.1f}%", showarrow=False, yshift=15, font=dict(color="#1E8449" if pct_r>=0 else "#C0392B", size=10, family="Arial Bold"))
                    
                    v26_e = rows[rows['Tahun'] == '2026']['Actual EBITDA'].sum()
                    v25_e = rows[rows['Tahun'] == '2025']['Actual EBITDA'].sum()
                    if v26_e != 0 and v25_e != 0:
                        pct_e = ((v26_e - v25_e) / abs(v25_e) * 100)
                        fig_q_comb.add_annotation(x=q, y=v26_e, text=f"Growth EBIT: {'▲' if pct_e >= 0 else '▼'} {abs(pct_e):.1f}%", showarrow=False, yshift=-20, font=dict(color="#D35400", size=9, family="Arial"))

            fig_q_comb.update_layout(yaxis_tickformat=',.0f', template="plotly_white", barmode='group', hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_q_comb, use_container_width=True)

            # Grafik Bulanan Finansial
            st.subheader("📅 Analisis Tren & Growth YoY per Bulan")
            df_m_yoy = df_filtered.groupby(['Bulan', 'Tahun'])[['Calculated_Actual_Revenue', 'Actual EBITDA']].sum().reset_index()
            df_m_yoy['Bulan'] = pd.Categorical(df_m_yoy['Bulan'], categories=month_order, ordered=True)
            df_m_yoy = df_m_yoy.sort_values(['Bulan', 'Tahun'])
            
            fig_m_comb = go.Figure()
            for yr, color in zip(["2025", "2026"], ["#AED6F1", "#2E86C1"]):
                if yr in selected_tahun:
                    yr_data = df_m_yoy[df_m_yoy['Tahun'] == yr]
                    fig_m_comb.add_trace(go.Bar(x=yr_data['Bulan'], y=yr_data['Calculated_Actual_Revenue'], name=f"Rev {yr}", marker_color=color, offsetgroup=yr))
            
            for yr, color, dash in zip(["2025", "2026"], ["#FAD7A0", "#D35400"], ["dash", "solid"]):
                if yr in selected_tahun:
                    yr_data = df_m_yoy[df_m_yoy['Tahun'] == yr]
                    fig_m_comb.add_trace(go.Scatter(x=yr_data['Bulan'], y=yr_data['Actual EBITDA'], name=f"EBITDA {yr}", mode='lines+markers', line=dict(color=color, width=3, dash=dash)))

            if "2025" in selected_tahun and "2026" in selected_tahun:
                for b in selected_bulan:
                    rows = df_m_yoy[df_m_yoy['Bulan'] == b]
                    v26_r = rows[rows['Tahun'] == '2026']['Calculated_Actual_Revenue'].sum()
                    v25_r = rows[rows['Tahun'] == '2025']['Calculated_Actual_Revenue'].sum()
                    if v26_r != 0 and v25_r != 0:
                        pct_r = ((v26_r - v25_r) / v25_r * 100)
                        fig_m_comb.add_annotation(x=b, y=v26_r, text=f"{'▲' if pct_r >= 0 else '▼'} {abs(pct_r):.0f}%", showarrow=False, yshift=10, font=dict(color="#1E8449" if pct_r>=0 else "#C0392B", size=9, family="Arial Bold"))
                    
                    v26_e = rows[rows['Tahun'] == '2026']['Actual EBITDA'].sum()
                    v25_e = rows[rows['Tahun'] == '2025']['Actual EBITDA'].sum()
                    if v26_e != 0 and v25_e != 0:
                        pct_e = ((v26_e - v25_e) / abs(v25_e) * 100)
                        fig_m_comb.add_annotation(x=b, y=v26_e, text=f"{'▲' if pct_e >= 0 else '▼'} {abs(pct_e):.0f}%", showarrow=False, yshift=-15, font=dict(color="#D35400", size=8, family="Arial"))

            fig_m_comb.update_layout(yaxis_tickformat=',.0f', template="plotly_white", barmode='group', hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_m_comb, use_container_width=True)

            # --- ROW 3: TREN PER RS & KONTRIBUSI ---
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("🏥 Tren Pencapaian per RS")
                df_rs_actual = df_filtered.pivot_table(index='Bulan', columns='Cabang', values='Calculated_Actual_Revenue', aggfunc='sum').reindex(month_order)
                
                fig_line = go.Figure()
                for rs in df_rs_actual.columns:
                    color = COLOR_MAP.get(rs, DEFAULT_COLORS[0])
                    fig_line.add_trace(go.Scatter(x=df_rs_actual.index, y=df_rs_actual[rs], name=f"Act {rs}", mode='lines+markers', line=dict(color=color)))
                fig_line.update_layout(yaxis_tickformat=',.0f', template="plotly_white", hovermode="x unified")
                st.plotly_chart(fig_line, use_container_width=True)
                
            with col_b:
                st.subheader("📊 Komposisi Pendapatan per RS")
                fig_pie = px.pie(df_filtered, values='Calculated_Actual_Revenue', names='Cabang', hole=0.4, color='Cabang', color_discrete_map=COLOR_MAP)
                fig_pie.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)

            # --- ROW 4: TABEL DETAIL ---
            st.markdown("---")
            st.subheader("🔍 Tabel Informasi Detail & Fitur Export")
            
            df_table = df_filtered.copy()
            df_table['EBITDA Margin %'] = (df_table['Actual EBITDA'] / df_table['Calculated_Actual_Revenue'] * 100).fillna(0)
            df_table['Total Kunjungan'] = df_table[kunjungan_columns].sum(axis=1)
            df_table['ARPP (Per Pasien)'] = (df_table['Calculated_Actual_Revenue'] / df_table['Total Kunjungan']).fillna(0)
            
            df_display = df_table[['Tahun', 'Kuartal', 'Bulan', 'Cabang', 'Calculated_Actual_Revenue', 'Actual EBITDA', 'EBITDA Margin %', 'Total Kunjungan', 'ARPP (Per Pasien)']].copy()
            df_display.rename(columns={'Calculated_Actual_Revenue': 'Actual Revenue'}, inplace=True)
            df_display = df_display.sort_values(['Cabang', 'Tahun', 'Bulan'], ascending=[True, False, True])

            col_btn1, col_btn2, _ = st.columns([1, 1, 4])
            with col_btn1:
                excel_data = to_excel(df_display)
                st.download_button(
                    label="🟢 Export to Excel",
                    data=excel_data,
                    file_name=f"Performance_Report_Helsa.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            with col_btn2:
                csv_data = df_display.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="🔵 Export to CSV",
                    data=csv_data,
                    file_name=f"Performance_Report_Helsa.csv",
                    mime="text/csv"
                )

            st.dataframe(
                df_display, 
                use_container_width=True, 
                column_config={
                    "Actual Revenue": st.column_config.NumberColumn("Actual Revenue", format="%,.0f"), 
                    "Actual EBITDA": st.column_config.NumberColumn("Actual EBITDA", format="%,.0f"),
                    "EBITDA Margin %": st.column_config.NumberColumn("EBITDA Margin", format="%.2f%%"),
                    "Total Kunjungan": st.column_config.NumberColumn("Total Volume Pasien", format="%,.0f"),
                    "ARPP (Per Pasien)": st.column_config.NumberColumn("ARPP (Pasien)", format="Rp %,.0f")
                }
            )

except Exception as e:
    st.error(f"Sistem Error saat memuat fitur dashboard terbaru: {e}")
