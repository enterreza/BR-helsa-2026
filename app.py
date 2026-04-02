import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Konfigurasi Halaman
st.set_page_config(page_title="Performance Dashboard RS", layout="wide")

# Fungsi Load Data
@st.cache_data
def load_data():
    sheet_id = "1oqXKKPNnlMOSBhkWi9_7Isjo_NYtHE2ytfeO-bSNMxY"
    sheet_name = "app_data"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    df = pd.read_csv(url)
    return df

try:
    df = load_data()

    # --- SIDEBAR FILTER ---
    st.sidebar.header("Filter Dashboard")
    list_cabang = df['Cabang'].unique().tolist()
    selected_cabang = st.sidebar.multiselect("Pilih Cabang", list_cabang, default=list_cabang)
    
    list_bulan = df['Bulan'].unique().tolist()
    selected_bulan = st.sidebar.multiselect("Pilih Bulan", list_bulan, default=list_bulan)

    # Filter Data
    df_filtered = df[(df['Cabang'].isin(selected_cabang)) & (df['Bulan'].isin(selected_bulan))]

    # --- HEADER ---
    st.title("🏥 RS Group Financial Performance Dashboard")
    st.markdown(f"Menampilkan data untuk **{', '.join(selected_cabang[:3])}{'...' if len(selected_cabang)>3 else ''}**")

    # --- ROW 1: KPI METRICS (TOTAL) ---
    st.subheader("Summary Performance (Total)")
    col1, col2, col3, col4 = st.columns(4)
    
    total_rev_act = df_filtered['Actual Revenue (Total)'].sum()
    total_rev_tar = df_filtered['Target Revenue (Total)'].sum()
    rev_ach = (total_rev_act / total_rev_tar) * 100 if total_rev_tar != 0 else 0

    total_ebitda_act = df_filtered['Actual EBITDA'].sum()
    total_ebitda_tar = df_filtered['Target EBITDA'].sum()
    ebitda_ach = (total_ebitda_act / total_ebitda_tar) * 100 if total_ebitda_tar != 0 else 0

    col1.metric("Total Actual Revenue", f"Rp {total_rev_act:,.0f}", f"{rev_ach:.1f}% Ach.")
    col2.metric("Total Actual EBITDA", f"Rp {total_ebitda_act:,.0f}", f"{ebitda_ach:.1f}% Ach.")
    col3.metric("Total Actual OPEX", f"Rp {df_filtered['Actual OPEX'].sum():,.0f}")
    col4.metric("Total Actual HPP", f"Rp {df_filtered['Actual HPP (Total)'].sum():,.0f}")

    st.markdown("---")

    # --- ROW 2: CHART REVENUE & EBITDA ---
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Revenue: Target vs Actual per Cabang")
        fig_rev = go.Figure()
        fig_rev.add_trace(go.Bar(x=df_filtered['Cabang'], y=df_filtered['Target Revenue (Total)'], name='Target', marker_color='lightgrey'))
        fig_rev.add_trace(go.Bar(x=df_filtered['Cabang'], y=df_filtered['Actual Revenue (Total)'], name='Actual', marker_color='#1f77b4'))
        fig_rev.update_layout(barmode='group', template='plotly_white')
        st.plotly_chart(fig_rev, use_container_width=True)

    with c2:
        st.subheader("Trend EBITDA per Bulan")
        df_trend = df_filtered.groupby('Bulan')[['Target EBITDA', 'Actual EBITDA']].sum().reset_index()
        fig_trend = px.line(df_trend, x='Bulan', y=['Target EBITDA', 'Actual EBITDA'], markers=True)
        st.plotly_chart(fig_trend, use_container_width=True)

    # --- ROW 3: REVENUE BREAKDOWN (Opt vs Ipt) ---
    st.subheader("Breakdown Revenue: Outpatient (Opt) vs Inpatient (Ipt)")
    col_a, col_b = st.columns(2)

    with col_a:
        # Pie Chart Actual Revenue Source
        opt_total = df_filtered['Actual Revenue (Opt)'].sum()
        ipt_total = df_filtered['Actual Revenue (Ipt)'].sum()
        fig_pie = px.pie(values=[opt_total, ipt_total], names=['Outpatient', 'Inpatient'], hole=0.4, title="Actual Revenue Mix")
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_b:
        # Comparison Table
        st.write("Detail Achievement per Cabang")
        df_table = df_filtered.groupby('Cabang').agg({
            'Actual Revenue (Total)': 'sum',
            'Target Revenue (Total)': 'sum',
            'Actual EBITDA': 'sum'
        }).reset_index()
        df_table['% Ach. Rev'] = (df_table['Actual Revenue (Total)'] / df_table['Target Revenue (Total)'] * 100).round(2)
        st.dataframe(df_table, use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
    st.info("Pastikan Spreadsheet dapat diakses oleh publik dan nama sheet sesuai.")
