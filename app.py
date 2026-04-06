import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="RS Group Dashboard YoY", layout="wide", page_icon="🏥")

# --- FUNGSI PEMBERSIHAN DATA ---
def clean_to_numeric(value):
    if pd.isna(value) or str(value).strip() == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    val_str = str(value).strip()
    cleaned = re.sub(r'[^\d]', '', val_str)
    try:
        return float(cleaned) if cleaned != "" else 0.0
    except ValueError:
        return 0.0

# --- FUNGSI LOAD DATA (Dua Sheet) ---
@st.cache_data
def load_combined_data():
    sheet_id = "1oqXKKPNnlMOSBhkWi9_7Isjo_NYtHE2ytfeO-bSNMxY"
    
    # Konfigurasi Sheet
    sheets = {
        "2026": "app_data",      # Nama sheet tahun ini
        "2025": "app_data_2025"  # GANTI INI dengan nama sheet tahun lalu Anda
    }
    
    combined_list = []
    
    numeric_cols = [
        'Target Revenue (Total)', 'Actual Revenue (Total)', 'Actual EBITDA', 'Actual OPEX', 'Actual HPP (Total)'
    ]

    for year, s_name in sheets.items():
        try:
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={s_name}"
            df_tmp = pd.read_csv(url, dtype=str)
            df_tmp.columns = [col.strip() for col in df_tmp.columns]
            
            # Tambahkan kolom penanda tahun
            df_tmp['Tahun'] = year
            df_tmp['Bulan'] = df_tmp['Bulan'].str.strip()
            df_tmp['Cabang'] = df_tmp['Cabang'].str.strip()

            # Bersihkan angka
            for col in numeric_cols:
                if col in df_tmp.columns:
                    df_tmp[col] = df_tmp[col].apply(clean_to_numeric)
            
            combined_list.append(df_tmp)
        except Exception as e:
            st.error(f"Gagal memuat sheet {s_name}: {e}")

    return pd.concat(combined_list, ignore_index=True) if combined_list else pd.DataFrame()

# --- MAIN APP ---
try:
    df_all = load_combined_data()

    # --- SIDEBAR ---
    st.sidebar.header("⚙️ Filter & YoY Settings")
    
    list_cabang = df_all['Cabang'].unique()
    selected_cabang = st.sidebar.multiselect("Pilih Cabang", list_cabang, default=list_cabang)
    
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    available_months = [m for m in month_order if m in df_all['Bulan'].unique()]
    selected_bulan = st.sidebar.multiselect("Pilih Bulan", available_months, default=available_months[:2])

    # Filter Data
    df_filtered = df_all[(df_all['Cabang'].isin(selected_cabang)) & (df_all['Bulan'].isin(selected_bulan))]

    st.title("🏥 RS Group Performance - Year on Year Analysis")
    st.markdown("---")

    if df_filtered.empty:
        st.warning("Data tidak ditemukan.")
    else:
        # Pisahkan Data per Tahun untuk Perbandingan
        df_2024 = df_filtered[df_filtered['Tahun'] == '2024']
        df_2023 = df_filtered[df_filtered['Tahun'] == '2023']

        # Hitung Total
        rev_24 = df_2024['Actual Revenue (Total)'].sum()
        rev_23 = df_2023['Actual Revenue (Total)'].sum()
        
        # Hitung Pertumbuhan (Growth)
        growth = ((rev_24 - rev_23) / rev_23 * 100) if rev_23 > 0 else 0

        # --- ROW 1: KPI WITH DELTA ---
        c1, c2, c3 = st.columns(3)
        c1.metric("Actual Revenue 2024", f"Rp {rev_24:,.0f}", f"{growth:.1f}% vs 2023")
        
        ebitda_24 = df_2024['Actual EBITDA'].sum()
        ebitda_23 = df_2023['Actual EBITDA'].sum()
        ebitda_growth = ((ebitda_24 - ebitda_23) / ebitda_23 * 100) if ebitda_23 > 0 else 0
        c2.metric("Actual EBITDA 2024", f"Rp {ebitda_24:,.0f}", f"{ebitda_growth:.1f}% vs 2023")
        
        c3.metric("Total OPEX 2024", f"Rp {df_2024['Actual OPEX'].sum():,.0f}")

        st.markdown("---")

        # --- ROW 2: YoY CHART ---
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.subheader("Comparison: Revenue 2024 vs 2023")
            # Grouping per Bulan untuk Chart
            df_yoy = df_filtered.groupby(['Bulan', 'Tahun'])['Actual Revenue (Total)'].sum().reset_index()
            # Pastikan urutan bulan benar
            df_yoy['Bulan'] = pd.Categorical(df_yoy['Bulan'], categories=month_order, ordered=True)
            df_yoy = df_yoy.sort_values('Bulan')
            
            fig_yoy = px.bar(df_yoy, x='Bulan', y='Actual Revenue (Total)', color='Tahun', barmode='group',
                             color_discrete_map={"2024": "#2E86C1", "2023": "#AED6F1"})
            st.plotly_chart(fig_yoy, use_container_width=True)

        with col_chart2:
            st.subheader("Revenue Contribution per Cabang (2024)")
            fig_pie = px.pie(df_2024, values='Actual Revenue (Total)', names='Cabang', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

        # Detail Table
        with st.expander("🔍 Lihat Detail Data Gabungan (2023 & 2024)"):
            st.write(df_filtered.sort_values(['Tahun', 'Bulan']))

except Exception as e:
    st.error(f"Error: {e}")
