import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="RS Group Dashboard 2026", layout="wide", page_icon="📊")

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
    
    # Konfigurasi Sheet (Pastikan nama sheet sesuai di Google Sheets Anda)
    sheets = {
        "2026": "app_data",      # Data Utama (Tahun Berjalan)
        "2025": "app_data_2025"  # Data Tahun Lalu untuk Pembanding
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
            continue # Jika sheet tahun lalu belum ada, lewati saja

    return pd.concat(combined_list, ignore_index=True) if combined_list else pd.DataFrame()

# --- MAIN APP ---
try:
    df_all = load_combined_data()
    
    # Standarisasi Urutan Bulan
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

    # --- SIDEBAR ---
    st.sidebar.header("⚙️ Filter Dashboard")
    
    list_cabang = sorted(df_all['Cabang'].unique())
    selected_cabang = st.sidebar.multiselect("Pilih Cabang (RS)", list_cabang, default=list_cabang)
    
    available_months = [m for m in month_order if m in df_all['Bulan'].unique()]
    selected_bulan = st.sidebar.multiselect("Pilih Periode Bulan", available_months, default=available_months)

    # Filter Data
    df_filtered = df_all[(df_all['Cabang'].isin(selected_cabang)) & (df_all['Bulan'].isin(selected_bulan))]
    df_2026 = df_filtered[df_filtered['Tahun'] == '2026']

    st.title("📊 Financial Performance RS Group 2026")
    st.markdown(f"Periode: **{', '.join(selected_bulan)}**")
    st.markdown("---")

    if df_2026.empty:
        st.warning("Data 2026 tidak ditemukan untuk filter ini.")
    else:
        # --- ROW 1: KPI GROUP ---
        rev_26 = df_2026['Actual Revenue (Total)'].sum()
        tar_26 = df_2026['Target Revenue (Total)'].sum()
        ach_26 = (rev_26 / tar_26 * 100) if tar_26 > 0 else 0
        
        ebitda_26 = df_2026['Actual EBITDA'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Group Revenue", f"Rp {rev_26:,.0f}", f"{ach_26:.1f}% Ach vs Target")
        c2.metric("Total Group EBITDA", f"Rp {ebitda_26:,.0f}")
        c3.metric("Total Group OPEX", f"Rp {df_2026['Actual OPEX'].sum():,.0f}")

        st.markdown("---")

        # --- ROW 2: GRAFIK PER GROUP (TOTAL SEMUA RS) ---
        st.subheader("📈 Tren Bulanan - Group Level (Total)")
        
        # Grouping data per bulan (menggabungkan semua RS)
        df_group_trend = df_2026.groupby('Bulan')[['Actual Revenue (Total)', 'Target Revenue (Total)']].sum().reindex(month_order).dropna().reset_index()
        
        fig_group = go.Figure()
        fig_group.add_trace(go.Bar(x=df_group_trend['Bulan'], y=df_group_trend['Target Revenue (Total)'], name='Target Group', marker_color='#D6DBDF'))
        fig_group.add_trace(go.Scatter(x=df_group_trend['Bulan'], y=df_group_trend['Actual Revenue (Total)'], name='Actual Group', line=dict(color='#2E86C1', width=4)))
        fig_group.update_layout(height=400, barmode='group', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_group, use_container_width=True)

        st.markdown("---")

        # --- ROW 3: GRAFIK PER RS (CABANG) ---
        st.subheader("🏥 Performa per Rumah Sakit (Jan - Des 2026)")
        
        # Chart 1: Revenue per RS
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.write("**Actual Revenue per RS (Bulan ke Bulan)**")
            df_rs_trend = df_2026.pivot_table(index='Bulan', columns='Cabang', values='Actual Revenue (Total)', aggfunc='sum').reindex(month_order).dropna()
            fig_rs = px.line(df_rs_trend.reset_index(), x='Bulan', y=df_rs_trend.columns, markers=True)
            fig_rs.update_layout(height=400)
            st.plotly_chart(fig_rs, use_container_width=True)

        with col_b:
            st.write("**Total Revenue Contribution per RS**")
            fig_pie = px.pie(df_2026, values='Actual Revenue (Total)', names='Cabang', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- ROW 4: TABEL DETAIL ---
        st.markdown("---")
        with st.expander("🔍 Lihat Detail Tabel Data 2026"):
            st.dataframe(df_2026.sort_values(['Bulan', 'Cabang']), use_container_width=True)

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
