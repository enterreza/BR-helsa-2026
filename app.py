import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="RS Group Dashboard", layout="wide")

# --- FUNGSI PEMBERSIHAN DATA (KHUSUS FORMAT INDONESIA) ---
def clean_idr_logic(value):
    if pd.isna(value) or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    
    # Ubah ke string dan bersihkan
    val_str = str(value).strip()
    # Hapus 'Rp', spasi, dan titik (sebagai pemisah ribuan)
    val_str = val_str.replace('Rp', '').replace(' ', '').replace('.', '')
    # Ganti koma (desimal) menjadi titik agar bisa dibaca Python
    val_str = val_str.replace(',', '.')
    
    try:
        return float(val_str)
    except ValueError:
        return 0.0

# --- FUNGSI LOAD DATA ---
@st.cache_data
def load_data():
    sheet_id = "1oqXKKPNnlMOSBhkWi9_7Isjo_NYtHE2ytfeO-bSNMxY"
    sheet_name = "app_data"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    
    # Baca data, paksa semua kolom dibaca sebagai string dulu agar tidak rusak oleh parser otomatis
    df = pd.read_csv(url, dtype=str)
    
    # List kolom angka sesuai header Anda
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
    
    # Bersihkan kolom teks agar seragam
    df['Bulan'] = df['Bulan'].str.strip()
    df['Cabang'] = df['Cabang'].str.strip()
    
    # Terapkan pembersihan angka
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_idr_logic)
            
    return df

# --- MAIN APP ---
try:
    df = load_data()

    # --- SIDEBAR FILTER ---
    st.sidebar.header("Filter Dashboard")
    
    # Urutan bulan agar tidak berantakan di chart
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    available_months = [m for m in month_order if m in df['Bulan'].unique()]
    
    selected_bulan = st.sidebar.multiselect("Pilih Bulan", available_months, default=available_months[:2]) # Default Jan & Feb
    selected_cabang = st.sidebar.multiselect("Pilih Cabang", df['Cabang'].unique(), default=df['Cabang'].unique())

    # Filter proses
    df_filtered = df[(df['Bulan'].isin(selected_bulan)) & (df['Cabang'].isin(selected_cabang))]

    # --- TAMPILAN DASHBOARD ---
    st.title("🏥 RS Group Performance Dashboard")
    st.markdown("---")

    if df_filtered.empty:
        st.warning("Data tidak ditemukan untuk filter yang dipilih.")
    else:
        # Perhitungan Metrics
        rev_act = df_filtered['Actual Revenue (Total)'].sum()
        rev_tar = df_filtered['Target Revenue (Total)'].sum()
        rev_ach = (rev_act / rev_tar * 100) if rev_tar > 0 else 0

        ebitda_act = df_filtered['Actual EBITDA'].sum()
        ebitda_tar = df_filtered['Target EBITDA'].sum()
        ebitda_ach = (ebitda_act / ebitda_tar * 100) if ebitda_tar > 0 else 0

        # Baris KPI
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Actual Revenue", f"Rp {rev_act:,.0f}", f"{rev_ach:.1f}% Ach.")
        c2.metric("Actual EBITDA", f"Rp {ebitda_act:,.0f}", f"{ebitda_ach:.1f}% Ach.")
        c3.metric("Actual OPEX", f"Rp {df_filtered['Actual OPEX'].sum():,.0f}")
        c4.metric("Actual HPP", f"Rp {df_filtered['Actual HPP (Total)'].sum():,.0f}")

        st.markdown("---")

        # Baris Visualisasi
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Revenue per Cabang (Target vs Actual)")
            # Grouping agar jika pilih banyak bulan, datanya tergabung per cabang
            df_branch = df_filtered.groupby('Cabang')[['Target Revenue (Total)', 'Actual Revenue (Total)']].sum().reset_index()
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(x=df_branch['Cabang'], y=df_branch['Target Revenue (Total)'], name='Target', marker_color='#D6DBDF'))
            fig_bar.add_trace(go.Bar(x=df_branch['Cabang'], y=df_branch['Actual Revenue (Total)'], name='Actual', marker_color='#2E86C1'))
            fig_bar.update_layout(barmode='group', height=400)
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_right:
            st.subheader("EBITDA Trend (Monthly)")
            df_month = df_filtered.groupby('Bulan')[['Actual EBITDA', 'Target EBITDA']].sum().reindex(month_order).dropna().reset_index()
            fig_line = px.line(df_month, x='Bulan', y=['Actual EBITDA', 'Target EBITDA'], markers=True)
            fig_line.update_layout(height=400)
            st.plotly_chart(fig_line, use_container_width=True)

        # Tabel mentah di bawah untuk verifikasi
        with st.expander("Lihat Detail Tabel Data Terfilter"):
            st.write(df_filtered)

except Exception as e:
    st.error(f"Gagal memuat data: {e}")
