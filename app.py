import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="RS Group YoY Dashboard 2026", layout="wide", page_icon="📈")

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

# --- FUNGSI LOAD DATA ---
@st.cache_data
def load_combined_data():
    sheet_id = "1oqXKKPNnlMOSBhkWi9_7Isjo_NYtHE2ytfeO-bSNMxY"
    
    # Konfigurasi Sheet: app_data (2026) dan app_data_2025 (Tahun Lalu)
    sheets = {
        "2026": "app_data",
        "2025": "app_data_2025" 
    }
    
    combined_list = []
    numeric_cols = [
        'Target Revenue (Total)', 'Actual Revenue (Total)', 'Actual EBITDA', 
        'Actual OPEX', 'Actual HPP (Total)', 'Target EBITDA'
    ]

    for year, s_name in sheets.items():
        try:
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={s_name}"
            df_tmp = pd.read_csv(url, dtype=str)
            df_tmp.columns = [col.strip() for col in df_tmp.columns]
            
            df_tmp['Tahun'] = year
            df_tmp['Bulan'] = df_tmp['Bulan'].str.strip()
            df_tmp['Cabang'] = df_tmp['Cabang'].str.strip()

            for col in numeric_cols:
                if col in df_tmp.columns:
                    df_tmp[col] = df_tmp[col].apply(clean_to_numeric)
            
            combined_list.append(df_tmp)
        except Exception:
            continue

    return pd.concat(combined_list, ignore_index=True) if combined_list else pd.DataFrame()

# --- MAIN APP ---
try:
    df_all = load_combined_data()
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

    # --- SIDEBAR ---
    st.sidebar.header("⚙️ Dashboard Filter")
    
    list_cabang = sorted(df_all['Cabang'].unique())
    selected_cabang = st.sidebar.multiselect("Pilih Cabang (RS)", list_cabang, default=list_cabang)
    
    available_months = [m for m in month_order if m in df_all['Bulan'].unique()]
    selected_bulan = st.sidebar.multiselect("Pilih Periode Bulan", available_months, default=available_months)

    # Filter Data Utama
    df_filtered = df_all[(df_all['Cabang'].isin(selected_cabang)) & (df_all['Bulan'].isin(selected_bulan))]
    df_2026 = df_filtered[df_filtered['Tahun'] == '2026']
    df_2025 = df_filtered[df_filtered['Tahun'] == '2025']

    st.title("🏥 RS Group Financial Performance 2026")
    st.info("Analisis Perbandingan Year-on-Year (2026 vs 2025) & Performa Cabang")

    if df_2026.empty:
        st.warning("Data 2026 tidak ditemukan. Pastikan nama sheet dan filter sudah benar.")
    else:
        # --- ROW 1: KPI GROUP DENGAN DELTA YoY ---
        rev_26 = df_2026['Actual Revenue (Total)'].sum()
        rev_25 = df_2025['Actual Revenue (Total)'].sum()
        growth_rev = ((rev_26 - rev_25) / rev_25 * 100) if rev_25 > 0 else 0

        ebitda_26 = df_2026['Actual EBITDA'].sum()
        ebitda_25 = df_2025['Actual EBITDA'].sum()
        growth_ebitda = ((ebitda_26 - ebitda_25) / ebitda_25 * 100) if ebitda_25 > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Revenue Group 2026", f"Rp {rev_26:,.0f}", f"{growth_rev:.1f}% vs 2025")
        c2.metric("EBITDA Group 2026", f"Rp {ebitda_26:,.0f}", f"{growth_ebitda:.1f}% vs 2025")
        c3.metric("Total OPEX 2026", f"Rp {df_2026['Actual OPEX'].sum():,.0f}")

        st.markdown("---")

        # --- ROW 2: YoY TREND (GROUP LEVEL) ---
        st.subheader("📈 Tren Bulanan: Group Revenue YoY (2026 vs 2025)")
        df_yoy_group = df_filtered.groupby(['Bulan', 'Tahun'])['Actual Revenue (Total)'].sum().reset_index()
        df_yoy_group['Bulan'] = pd.Categorical(df_yoy_group['Bulan'], categories=month_order, ordered=True)
        df_yoy_group = df_yoy_group.sort_values(['Bulan', 'Tahun'])
        
        fig_yoy = px.bar(df_yoy_group, x='Bulan', y='Actual Revenue (Total)', color='Tahun', barmode='group',
                         color_discrete_map={"2026": "#2E86C1", "2025": "#AED6F1"}, template="plotly_white")
        st.plotly_chart(fig_yoy, use_container_width=True)

        st.markdown("---")

        # --- ROW 3: RS LEVEL ANALYSIS (CABANG) ---
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("🏥 Revenue per Cabang (2026)")
            # Line chart tren bulanan per RS
            df_rs_trend = df_2026.pivot_table(index='Bulan', columns='Cabang', values='Actual Revenue (Total)', aggfunc='sum').reindex(month_order).dropna()
            fig_rs = px.line(df_rs_trend.reset_index(), x='Bulan', y=df_rs_trend.columns, markers=True, title="Tren Bulanan per RS")
            st.plotly_chart(fig_rs, use_container_width=True)

        with col_b:
            st.subheader("📊 Komposisi Revenue per RS (2026)")
            fig_pie = px.pie(df_2026, values='Actual Revenue (Total)', names='Cabang', hole=0.4, 
                             color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- ROW 4: TARGET VS ACTUAL PER RS ---
        st.subheader("🎯 Achievement per Cabang (Target vs Actual 2026)")
        df_ach = df_2026.groupby('Cabang')[['Target Revenue (Total)', 'Actual Revenue (Total)']].sum().reset_index()
        fig_ach = go.Figure()
        fig_ach.add_trace(go.Bar(x=df_ach['Cabang'], y=df_ach['Target Revenue (Total)'], name='Target 2026', marker_color='#D6DBDF'))
        fig_ach.add_trace(go.Bar(x=df_ach['Cabang'], y=df_ach['Actual Revenue (Total)'], name='Actual 2026', marker_color='#1E8449'))
        fig_ach.update_layout(barmode='group', height=400)
        st.plotly_chart(fig_ach, use_container_width=True)

        # --- TABEL DETAIL ---
        with st.expander("🔍 Lihat Detail Data Mentah (YoY)"):
            st.dataframe(df_filtered.sort_values(['Tahun', 'Bulan', 'Cabang']), use_container_width=True)

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
