import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Dashboard RS Group 2026", layout="wide", page_icon="🏥")

# --- FUNGSI FORMAT MATA UANG INDONESIA ---
def format_rupiah_human(n):
    """Mengubah angka besar menjadi format Juta atau Miliar agar mudah dibaca"""
    if abs(n) >= 1_000_000_000:
        return f"Rp {n / 1_000_000_000:.2f} Miliar"
    elif abs(n) >= 1_000_000:
        return f"Rp {n / 1_000_000:.2f} Juta"
    else:
        return f"Rp {n:,.0f}"

# --- FUNGSI PEMBERSIHAN DATA ---
def clean_to_numeric(value):
    if pd.isna(value) or str(value).strip() == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    val_str = str(value).strip()
    # Hapus semua karakter non-angka
    cleaned = re.sub(r'[^\d]', '', val_str)
    try:
        return float(cleaned) if cleaned != "" else 0.0
    except ValueError:
        return 0.0

# --- FUNGSI LOAD DATA ---
@st.cache_data
def load_combined_data():
    sheet_id = "1oqXKKPNnlMOSBhkWi9_7Isjo_NYtHE2ytfeO-bSNMxY"
    sheets = {
        "2026": "app_data",      # Sheet Tahun Berjalan
        "2025": "app_data_2025"  # Sheet Tahun Lalu
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
    st.sidebar.header("⚙️ Filter Dashboard")
    list_cabang = sorted(df_all['Cabang'].unique()) if 'Cabang' in df_all.columns else []
    selected_cabang = st.sidebar.multiselect("Pilih Cabang (RS)", list_cabang, default=list_cabang)
    
    available_months = [m for m in month_order if m in df_all['Bulan'].unique()]
    selected_bulan = st.sidebar.multiselect("Pilih Periode Bulan", available_months, default=available_months)

    # Filter Data
    df_filtered = df_all[(df_all['Cabang'].isin(selected_cabang)) & (df_all['Bulan'].isin(selected_bulan))]
    df_2026 = df_filtered[df_filtered['Tahun'] == '2026']
    df_2025 = df_filtered[df_filtered['Tahun'] == '2025']

    st.title("🏥 Performa Finansial RS Group 2026")
    st.markdown("---")

    if df_2026.empty:
        st.warning("Data tahun 2026 tidak ditemukan. Silakan cek nama sheet atau filter Anda.")
    else:
        # --- ROW 1: KPI UTAMA (Format Miliar/Juta) ---
        rev_26 = df_2026['Actual Revenue (Total)'].sum()
        rev_25 = df_2025['Actual Revenue (Total)'].sum()
        growth_rev = ((rev_26 - rev_25) / rev_25 * 100) if rev_25 > 0 else 0

        ebitda_26 = df_2026['Actual EBITDA'].sum()
        ebitda_25 = df_2025['Actual EBITDA'].sum()
        growth_ebitda = ((ebitda_26 - ebitda_25) / ebitda_25 * 100) if ebitda_25 > 0 else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Pendapatan Actual 2026", format_rupiah_human(rev_26), f"{growth_rev:.1f}% vs 2025")
        c2.metric("EBITDA Actual 2026", format_rupiah_human(ebitda_26), f"{growth_ebitda:.1f}% vs 2025")
        c3.metric("Total OPEX 2026", format_rupiah_human(df_2026['Actual OPEX'].sum()))

        st.markdown("---")

        # --- ROW 2: TREN YoY GROUP (Miliar) ---
        st.subheader("📈 Tren Pendapatan Group: 2026 vs 2025")
        df_yoy = df_filtered.groupby(['Bulan', 'Tahun'])['Actual Revenue (Total)'].sum().reset_index()
        df_yoy['Bulan'] = pd.Categorical(df_yoy['Bulan'], categories=month_order, ordered=True)
        df_yoy = df_yoy.sort_values(['Bulan', 'Tahun'])
        
        fig_yoy = px.bar(df_yoy, x='Bulan', y='Actual Revenue (Total)', color='Tahun', barmode='group',
                         labels={'Actual Revenue (Total)': 'Pendapatan (Rp)'},
                         color_discrete_map={"2026": "#2E86C1", "2025": "#AED6F1"})
        st.plotly_chart(fig_yoy, use_container_width=True)

        st.markdown("---")

        # --- ROW 3: ANALISIS PER CABANG (RS) ---
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("🏥 Tren Pendapatan per RS (2026)")
            df_rs = df_2026.pivot_table(index='Bulan', columns='Cabang', values='Actual Revenue (Total)', aggfunc='sum').reindex(month_order).dropna()
            fig_rs = px.line(df_rs.reset_index(), x='Bulan', y=df_rs.columns, markers=True)
            st.plotly_chart(fig_rs, use_container_width=True)

        with col_b:
            st.subheader("🎯 Target vs Actual per RS (2026)")
            df_ach = df_2026.groupby('Cabang')[['Target Revenue (Total)', 'Actual Revenue (Total)']].sum().reset_index()
            fig_ach = go.Figure()
            fig_ach.add_trace(go.Bar(x=df_ach['Cabang'], y=df_ach['Target Revenue (Total)'], name='Target', marker_color='#D6DBDF'))
            fig_ach.add_trace(go.Bar(x=df_ach['Cabang'], y=df_ach['Actual Revenue (Total)'], name='Actual', marker_color='#1E8449'))
            st.plotly_chart(fig_ach, use_container_width=True)

        # --- DETAIL DATA ---
        with st.expander("🔍 Lihat Detail Tabel Data"):
            # Menampilkan tabel dengan pemisah ribuan titik (.)
            st.dataframe(df_filtered.style.format("{:,.0f}", thousands="."), use_container_width=True)

except Exception as e:
    st.error(f"Terjadi kesalahan sistem: {e}")
