import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="RS Group Dashboard", layout="wide", page_icon="🏥")

# --- FUNGSI PEMBERSIHAN DATA ---
def clean_to_numeric(value):
    if pd.isna(value) or str(value).strip() == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    
    val_str = str(value).strip()
    # Menghapus semua karakter non-angka
    cleaned = re.sub(r'[^\d]', '', val_str)
    
    try:
        return float(cleaned) if cleaned != "" else 0.0
    except ValueError:
        return 0.0

# --- FUNGSI LOAD DATA ---
@st.cache_data
def load_data():
    sheet_id = "1oqXKKPNnlMOSBhkWi9_7Isjo_NYtHE2ytfeO-bSNMxY"
    sheet_name = "app_data"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    
    df = pd.read_csv(url, dtype=str)
    df.columns = [col.strip() for col in df.columns]
    
    numeric_cols = [
        'Target Revenue (Total)', 'Actual Revenue (Total)',
        'Target Revenue (Opt)', 'Actual Revenue (Opt)',
        'Target Revenue (Ipt)', 'Actual Revenue (Ipt)',
        'Target HPP (Total)', 'Actual HPP (Total)',
        'Target HPP (Opt)', 'Actual HPP (Opt)',
        'Target HPP (Ipt)', 'Actual HPP (Ipt)',
        'Target OPEX', 'Actual OPEX',
        'Target EBITDA', 'Actual EBITDA'
    ]
    
    df['Bulan'] = df['Bulan'].str.strip()
    df['Cabang'] = df['Cabang'].str.strip()
    
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_to_numeric)
            
    return df

# --- MAIN APP ---
try:
    df = load_data()

    st.sidebar.header("⚙️ Filter Dashboard")
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    
    available_months = [m for m in month_order if m in df['Bulan'].unique()]
    
    selected_bulan = st.sidebar.multiselect("Pilih Bulan", available_months, default=available_months)
    selected_cabang = st.sidebar.multiselect("Pilih Cabang", df['Cabang'].unique(), default=df['Cabang'].unique())

    df_filtered = df[(df['Bulan'].isin(selected_bulan)) & (df['Cabang'].isin(selected_cabang))]

    st.title("🏥 RS Group Financial Performance")
    st.markdown("---")

    if df_filtered.empty:
        st.warning("Data tidak ditemukan. Silakan sesuaikan filter di sidebar.")
    else:
        # Metrics
        rev_act = df_filtered['Actual Revenue (Total)'].sum()
        rev_tar = df_filtered['Target Revenue (Total)'].sum()
        rev_ach = (rev_act / rev_tar * 100) if rev_tar > 0 else 0

        ebitda_act = df_filtered['Actual EBITDA'].sum()
        ebitda_tar = df_filtered['Target EBITDA'].sum()
        ebitda_ach = (ebitda_act / ebitda_tar * 100) if ebitda_tar > 0 else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Actual Revenue", f"Rp {rev_act:,.0f}", f"{rev_ach:.1f}% Ach.")
        m2.metric("Actual EBITDA", f"Rp {ebitda_act:,.0f}", f"{ebitda_ach:.1f}% Ach.")
        m3.metric("Actual OPEX", f"Rp {df_filtered['Actual OPEX'].sum():,.0f}")
        m4.metric("Actual HPP", f"Rp {df_filtered['Actual HPP (Total)'].sum():,.0f}")

        st.markdown("---")

        col_left, col_right = st.columns(2)
        with col_left:
            st.subheader("Revenue per Cabang")
            df_branch = df_filtered.groupby('Cabang')[['Target Revenue (Total)', 'Actual Revenue (Total)']].sum().reset_index()
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(x=df_branch['Cabang'], y=df_branch['Target Revenue (Total)'], name='Target', marker_color='#D6DBDF'))
            fig_bar.add_trace(go.Bar(x=df_branch['Cabang'], y=df_branch['Actual Revenue (Total)'], name='Actual', marker_color='#2E86C1'))
            fig_bar.update_layout(barmode='group', height=400)
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_right:
            st.subheader("EBITDA Trend")
            df_month = df_filtered.groupby('Bulan')[['Actual EBITDA', 'Target EBITDA']].sum().reindex(available_months).reset_index()
            fig_line = px.line(df_month, x='Bulan', y=['Actual EBITDA', 'Target EBITDA'], markers=True)
            st.plotly_chart(fig_line, use_container_width=True)

        st.markdown("---")
        with st.expander("🔍 Lihat Detail Tabel Data (Verifikasi Angka)"):
            # FIX: Menggunakan 'thousands' dengan s
            st.dataframe(df_filtered.style.format("{:,.0f}", thousands="."), use_container_width=True)

except Exception as e:
    st.error(f"Terjadi kesalahan sistem: {e}")
