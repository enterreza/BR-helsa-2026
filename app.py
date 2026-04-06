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

# --- FUNGSI LOAD DATA ---
@st.cache_data
def load_combined_data():
    sheet_id = "1oqXKKPNnlMOSBhkWi9_7Isjo_NYtHE2ytfeO-bSNMxY"
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

    st.sidebar.header("⚙️ Filter")
    list_cabang = sorted(df_all['Cabang'].unique())
    selected_cabang = st.sidebar.multiselect("Pilih Cabang", list_cabang, default=list_cabang)
    
    available_months = [m for m in month_order if m in df_all['Bulan'].unique()]
    selected_bulan = st.sidebar.multiselect("Pilih Bulan", available_months, default=available_months)

    df_filtered = df_all[(df_all['Cabang'].isin(selected_cabang)) & (df_all['Bulan'].isin(selected_bulan))]
    df_2026 = df_filtered[df_filtered['Tahun'] == '2026']
    df_2025 = df_filtered[df_filtered['Tahun'] == '2025']

    st.title("🏥 Performa RS Group 2026 (YoY)")
    st.markdown("---")

    if not df_2026.empty:
        # --- ROW 1: KPI ---
        rev_26 = df_2026['Actual Revenue (Total)'].sum()
        rev_25 = df_2025['Actual Revenue (Total)'].sum()
        growth_rev = ((rev_26 - rev_25) / rev_25 * 100) if rev_25 > 0 else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Pendapatan 2026", format_rupiah_human(rev_26), f"{growth_rev:.1f}% vs 2025")
        c2.metric("EBITDA 2026", format_rupiah_human(df_2026['Actual EBITDA'].sum()))
        c3.metric("OPEX 2026", format_rupiah_human(df_2026['Actual OPEX'].sum()))

        st.markdown("---")

        # --- ROW 2: YoY CHART DENGAN LABEL % GROWTH ---
        st.subheader("📈 Tren Pendapatan: 2026 vs 2025 (Miliar Rp)")
        
        # Siapkan data YoY
        df_group = df_filtered.groupby(['Bulan', 'Tahun'])['Actual Revenue (Total)'].sum().reset_index()
        df_group['Bulan'] = pd.Categorical(df_group['Bulan'], categories=month_order, ordered=True)
        df_group = df_group.sort_values(['Bulan', 'Tahun'])

        # Hitung Persentase Growth untuk anotasi grafik
        growth_labels = []
        for m in selected_bulan:
            val_26 = df_group[(df_group['Bulan'] == m) & (df_group['Tahun'] == '2026')]['Actual Revenue (Total)'].sum()
            val_25 = df_group[(df_group['Bulan'] == m) & (df_group['Tahun'] == '2025')]['Actual Revenue (Total)'].sum()
            pct = ((val_26 - val_25) / val_25 * 100) if val_25 > 0 else 0
            growth_labels.append({'Bulan': m, 'text': f"▲ {pct:.1f}%" if pct > 0 else f"▼ {pct:.1f}%"})

        # Buat Grafik Bar
        fig_yoy = px.bar(df_group, x='Bulan', y='Actual Revenue (Total)', color='Tahun', barmode='group',
                         color_discrete_map={"2026": "#2E86C1", "2025": "#AED6F1"},
                         labels={'Actual Revenue (Total)': 'Pendapatan (Rp)'})

        # Atur Satuan Sumbu Y ke Miliar (Format Indonesia)
        fig_yoy.update_layout(yaxis_tickformat='.2s', yaxis_title="Pendapatan (Miliar Rp)", template="plotly_white")
        
        # Tambahkan teks growth di atas batang
        for label in growth_labels:
            y_pos = df_group[(df_group['Bulan'] == label['Bulan']) & (df_group['Tahun'] == '2026')]['Actual Revenue (Total)'].sum()
            fig_yoy.add_annotation(x=label['Bulan'], y=y_pos, text=label['text'], 
                                   showarrow=False, yshift=10, font=dict(color="#1E8449" if "▲" in label['text'] else "#C0392B", size=12))
        
        st.plotly_chart(fig_yoy, use_container_width=True)

        st.markdown("---")
        
        # --- ROW 3: DETAIL PER RS ---
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("🏥 Tren per RS (Miliar Rp)")
            df_rs = df_2026.pivot_table(index='Bulan', columns='Cabang', values='Actual Revenue (Total)', aggfunc='sum').reindex(month_order).dropna()
            fig_rs = px.line(df_rs.reset_index(), x='Bulan', y=df_rs.columns, markers=True)
            fig_rs.update_layout(yaxis_title="Miliar Rp")
            st.plotly_chart(fig_rs, use_container_width=True)
            
        with col_b:
            st.subheader("🎯 Pencapaian Target 2026")
            df_ach = df_2026.groupby('Cabang')[['Target Revenue (Total)', 'Actual Revenue (Total)']].sum().reset_index()
            fig_ach = go.Figure()
            fig_ach.add_trace(go.Bar(x=df_ach['Cabang'], y=df_ach['Target Revenue (Total)'], name='Target', marker_color='#D6DBDF'))
            fig_ach.add_trace(go.Bar(x=df_ach['Cabang'], y=df_ach['Actual Revenue (Total)'], name='Actual', marker_color='#1E8449'))
            st.plotly_chart(fig_ach, use_container_width=True)

except Exception as e:
    st.error(f"Sistem Error: {e}")
