import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Dashboard RS Group 2026", layout="wide", page_icon="📈")

# --- FUNGSI FORMAT MATA UANG INDONESIA ---
def format_rupiah_human(n):
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
    cleaned = re.sub(r'[^\d]', '', val_str)
    try:
        return float(cleaned) if cleaned != "" else 0.0
    except ValueError:
        return 0.0

# --- FUNGSI LOAD DATA (2026 & 2025) ---
@st.cache_data
def load_combined_data():
    sheet_id = "1oqXKKPNnlMOSBhkWi9_7Isjo_NYtHE2ytfeO-bSNMxY"
    # app_data = 2026, app_data_2025 = 2025
    sheets = {"2026": "app_data", "2025": "app_data_2025"}
    combined_list = []
    numeric_cols = ['Target Revenue (Total)', 'Actual Revenue (Total)', 'Actual EBITDA', 'Actual OPEX']

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
        except:
            continue
    return pd.concat(combined_list, ignore_index=True) if combined_list else pd.DataFrame()

# --- MAIN APP ---
try:
    df_all = load_combined_data()
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

    # --- SIDEBAR ---
    st.sidebar.header("⚙️ Filter")
    list_cabang = sorted(df_all['Cabang'].unique())
    selected_cabang = st.sidebar.multiselect("Pilih Cabang", list_cabang, default=list_cabang)
    
    available_months = [m for m in month_order if m in df_all['Bulan'].unique()]
    selected_bulan = st.sidebar.multiselect("Pilih Bulan", available_months, default=available_months)

    # Filter Data
    df_filtered = df_all[(df_all['Cabang'].isin(selected_cabang)) & (df_all['Bulan'].isin(selected_bulan))]
    df_2026 = df_filtered[df_filtered['Tahun'] == '2026']
    df_2025 = df_filtered[df_filtered['Tahun'] == '2025']

    st.title("🏥 Performa Finansial RS Group 2026")
    st.markdown("---")

    if not df_2026.empty:
        # --- ROW 1: KPI UTAMA ---
        rev_26 = df_2026['Actual Revenue (Total)'].sum()
        rev_25 = df_2025['Actual Revenue (Total)'].sum()
        growth_rev = ((rev_26 - rev_25) / rev_25 * 100) if rev_25 > 0 else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Pendapatan 2026", format_rupiah_human(rev_26), f"{growth_rev:.1f}% vs 2025")
        c2.metric("EBITDA 2026", format_rupiah_human(df_2026['Actual EBITDA'].sum()))
        c3.metric("OPEX 2026", format_rupiah_human(df_2026['Actual OPEX'].sum()))

        st.markdown("---")

        # --- ROW 2: YoY TREND (PENGHILANGAN G/B) ---
        st.subheader("📈 Tren Pendapatan Group: 2026 vs 2025")
        
        df_group = df_filtered.groupby(['Bulan', 'Tahun'])['Actual Revenue (Total)'].sum().reset_index()
        df_group['Bulan'] = pd.Categorical(df_group['Bulan'], categories=month_order, ordered=True)
        df_group = df_group.sort_values(['Bulan', 'Tahun'])

        # Grafik Bar YoY
        fig_yoy = px.bar(df_group, x='Bulan', y='Actual Revenue (Total)', color='Tahun', barmode='group',
                         color_discrete_map={"2026": "#2E86C1", "2025": "#AED6F1"},
                         hover_data={'Actual Revenue (Total)': ':,.0f', 'Tahun': True})

        # MENGHAPUS SATUAN "G" DAN MENGGANTI LABEL KE INDONESIA
        fig_yoy.update_layout(
            yaxis_tickformat=',.0f', # Menampilkan angka penuh dengan titik pemisah
            yaxis_title="Pendapatan (Rp)",
            xaxis_title="Bulan",
            template="plotly_white",
            hovermode="x unified"
        )

        # TAMBAHKAN LABEL % GROWTH DI ATAS BATANG 2026
        for m in selected_bulan:
            val_26 = df_group[(df_group['Bulan'] == m) & (df_group['Tahun'] == '2026')]['Actual Revenue (Total)'].sum()
            val_25 = df_group[(df_group['Bulan'] == m) & (df_group['Tahun'] == '2025')]['Actual Revenue (Total)'].sum()
            if val_26 > 0: # Hanya muncul jika ada data 2026
                pct = ((val_26 - val_25) / val_25 * 100) if val_25 > 0 else 0
                arrow = "▲" if pct >= 0 else "▼"
                color = "#1E8449" if pct >= 0 else "#C0392B"
                fig_yoy.add_annotation(
                    x=m, y=val_26, text=f"{arrow} {abs(pct):.1f}%", 
                    showarrow=False, yshift=12, font=dict(color=color, size=12, family="Arial Bold")
                )
        
        st.plotly_chart(fig_yoy, use_container_width=True)

        st.markdown("---")

        # --- ROW 3: ANALISIS PER RS ---
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("🏥 Tren Pendapatan per RS (2026)")
            df_rs = df_2026.pivot_table(index='Bulan', columns='Cabang', values='Actual Revenue (Total)', aggfunc='sum').reindex(month_order).dropna()
            fig_rs = px.line(df_rs.reset_index(), x='Bulan', y=df_rs.columns, markers=True)
            fig_rs.update_layout(yaxis_tickformat=',.0f', yaxis_title="Pendapatan (Rp)")
