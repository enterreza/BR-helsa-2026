import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Financial Dashboard RS", layout="wide")

# --- FUNGSI PEMBERSIHAN DATA (Mencegah Error String) ---
def clean_numeric(value):
    if pd.isna(value) or value == "":
        return 0
    if isinstance(value, (int, float)):
        return value
    # Hapus Rp, titik pemisah ribuan, dan spasi
    cleaned = re.sub(r'[Rp\s\.]', '', str(value))
    # Ganti koma desimal menjadi titik jika ada
    cleaned = cleaned.replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        return 0

# --- FUNGSI LOAD DATA ---
@st.cache_data
def load_data():
    sheet_id = "1oqXKKPNnlMOSBhkWi9_7Isjo_NYtHE2ytfeO-bSNMxY"
    sheet_name = "app_data"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    
    df = pd.read_csv(url)
    
    # List kolom yang harus berupa angka
    numeric_cols = [
        'Target Revenue (Total)', 'Actual Revenue (Total)',
        'Target Revenue (Opt)', 'Actual Revenue (Opt)',
        'Target Revenue (Ipt)', 'Actual Revenue (Ipt)',
        'Target HPP (Total)', 'Actual HPP (Total)',
        'Target OPEX', 'Actual OPEX',
        'Target EBITDA', 'Actual EBITDA'
    ]
    
    # Terapkan pembersihan ke semua kolom angka
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_numeric)
            
    return df

# --- MAIN APP ---
try:
    df = load_data()

    # --- SIDEBAR FILTER ---
    st.sidebar.header("Filter Dashboard")
    
    list_cabang = sorted(df['Cabang'].unique().tolist())
    selected_cabang = st.sidebar.multiselect("Pilih Cabang", list_cabang, default=list_cabang)
    
    list_bulan = df['Bulan'].unique().tolist()
    selected_bulan = st.sidebar.multiselect("Pilih Bulan", list_bulan, default=list_bulan)

    # Filter Data berdasarkan pilihan sidebar
    df_filtered = df[(df['Cabang'].isin(selected_cabang)) & (df['Bulan'].isin(selected_bulan))]

    # --- HEADER ---
    st.title("📊 RS Group Performance Dashboard")
    st.markdown("---")

    # --- BARIS 1: KPI METRICS ---
    col1, col2, col3, col4 = st.columns(4)
    
    # Perhitungan Total
    rev_act = df_filtered['Actual Revenue (Total)'].sum()
    rev_tar = df_filtered['Target Revenue (Total)'].sum()
    rev_ach = (rev_act / rev_tar * 100) if rev_tar != 0 else 0

    ebitda_act = df_filtered['Actual EBITDA'].sum()
    ebitda_tar = df_filtered['Target EBITDA'].sum()
    ebitda_ach = (ebitda_act / ebitda_tar * 100) if ebitda_tar != 0 else 0

    with col1:
        st.metric("Total Actual Revenue", f"Rp {rev_act:,.0f}", f"{rev_ach:.1f}% vs Target")
    with col2:
        st.metric("Total Actual EBITDA", f"Rp {ebitda_act:,.0f}", f"{ebitda_ach:.1f}% vs Target")
    with col3:
        st.metric("Total Actual OPEX", f"Rp {df_filtered['Actual OPEX'].sum():,.0f}")
    with col4:
        st.metric("Total Actual HPP", f"Rp {df_filtered['Actual HPP (Total)'].sum():,.0f}")

    st.markdown("---")

    # --- BARIS 2: VISUALISASI UTAMA ---
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Revenue per Cabang: Target vs Actual")
        fig_rev = go.Figure()
        fig_rev.add_trace(go.Bar(x=df_filtered['Cabang'], y=df_filtered['Target Revenue (Total)'], name='Target', marker_color='#E5E7E9'))
        fig_rev.add_trace(go.Bar(x=df_filtered['Cabang'], y=df_filtered['Actual Revenue (Total)'], name='Actual', marker_color='#1E88E5'))
        fig_rev.update_layout(barmode='group', height=400, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_rev, use_container_width=True)

    with c2:
        st.subheader("Profitability: EBITDA Trend")
        df_trend = df_filtered.groupby('Bulan')[['Actual EBITDA', 'Target EBITDA']].sum().reset_index()
        fig_trend = px.line(df_trend, x='Bulan', y=['Actual EBITDA', 'Target EBITDA'], markers=True,
                            color_discrete_map={"Actual EBITDA": "#1E88E5", "Target EBITDA": "#E5E7E9"})
        fig_trend.update_layout(height=400)
        st.plotly_chart(fig_trend, use_container_width=True)

    # --- BARIS 3: BREAKDOWN & DATA ---
    st.markdown("---")
    c3, c4 = st.columns([1, 2])

    with c3:
        st.subheader("Revenue Mix (Opt vs Ipt)")
        opt = df_filtered['Actual Revenue (Opt)'].sum()
        ipt = df_filtered['Actual Revenue (Ipt)'].sum()
        fig_pie = px.pie(values=[opt, ipt], names=['Outpatient', 'Inpatient'], hole=0.4,
                         color_discrete_sequence=['#42A5F5', '#90CAF9'])
        st.plotly_chart(fig_pie, use_container_width=True)

    with c4:
        st.subheader("Detail Data Table")
        # Format table untuk ditampilkan
        df_display = df_filtered[['Bulan', 'Cabang', 'Actual Revenue (Total)', 'Target Revenue (Total)', 'Actual EBITDA']].copy()
        st.dataframe(df_display.style.format("{:,.0f}", subset=['Actual Revenue (Total)', 'Target Revenue (Total)', 'Actual EBITDA']), use_container_width=True)

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
    st.info("Saran: Pastikan nama kolom di Google Sheets sama persis dengan script ini.")
