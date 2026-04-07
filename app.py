import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Dashboard Keuangan RS", layout="wide", page_icon="📈")

# --- TAMBAHAN LOGO DI POJOK KIRI ATAS ---
LOGO_FILE = "HELSA Rumah sakit.png"
if os.path.exists(LOGO_FILE):
    st.image(LOGO_FILE, use_container_width=False, width=250)
else:
    st.warning("⚠️ File logo 'HELSA Rumah sakit.png' tidak ditemukan.")

# --- DEFINISI WARNA TETAP PER RS ---
COLOR_MAP = {
    "Jatirahayu": "#636EFA", 
    "Cikampek": "#EF553B",   
    "Citeureup": "#00CC96",  
    "Ciputat": "#AB63FA",    
}
DEFAULT_COLORS = px.colors.qualitative.Plotly

# --- FUNGSI FORMAT MATA UANG ---
def format_rupiah_human(n):
    prefix = "-" if n < 0 else ""
    val = abs(n)
    if val >= 1_000_000_000:
        return f"{prefix}Rp {val / 1_000_000_000:.2f} Miliar"
    elif val >= 1_000_000:
        return f"{prefix}Rp {val / 1_000_000:.2f} Juta"
    else:
        return f"{prefix}Rp {val:,.0f}"

# --- FUNGSI PEMBERSIHAN DATA ---
def clean_to_numeric(value):
    if pd.isna(value) or str(value).strip() == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    val_str = str(value).strip()
    if val_str.startswith('(') and val_str.endswith(')'):
        val_str = '-' + val_str[1:-1]
    cleaned = re.sub(r'[^0-9\-]', '', val_str)
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
    numeric_cols = ['Actual Revenue (Total)', 'Actual EBITDA', 'Target Revenue (Total)', 'Target EBITDA']

    for year, s_name in sheets.items():
        try:
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={s_name}"
            df_tmp = pd.read_csv(url, dtype=str)
            df_tmp.columns = [str(col).strip() for col in df_tmp.columns]
            if 'Cabang' not in df_tmp.columns: df_tmp['Cabang'] = 'Unknown'
            if 'Bulan' not in df_tmp.columns: df_tmp['Bulan'] = 'Unknown'
            df_tmp['Tahun'] = year
            for col in numeric_cols:
                if col in df_tmp.columns:
                    df_tmp[col] = df_tmp[col].apply(clean_to_numeric)
                    df_tmp[col] = pd.to_numeric(df_tmp[col], errors='coerce').fillna(0)
                else:
                    df_tmp[col] = 0.0
            combined_list.append(df_tmp)
        except Exception:
            continue
    return pd.concat(combined_list, ignore_index=True) if combined_list else pd.DataFrame()

# --- MAIN APP ---
try:
    df_all = load_combined_data()
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

    st.sidebar.header("⚙️ Filter")
    if not df_all.empty:
        list_cabang = sorted(df_all['Cabang'].unique())
        selected_cabang = st.sidebar.multiselect("Pilih Cabang", list_cabang, default=list_cabang)
        available_months = [m for m in month_order if m in df_all['Bulan'].unique()]
        selected_bulan = st.sidebar.multiselect("Pilih Bulan", available_months, default=available_months)

        df_filtered = df_all[(df_all['Cabang'].isin(selected_cabang)) & (df_all['Bulan'].isin(selected_bulan))].copy()
        df_2026 = df_filtered[df_filtered['Tahun'] == '2026']

        st.title("🏥 Performance Dashboard RS Group")
        st.markdown("---")

        if not df_2026.empty:
            # KPI Section (Row 1)
            rev_act_26 = df_2026['Actual Revenue (Total)'].sum()
            rev_tar_26 = df_2026['Target Revenue (Total)'].sum()
            ach_rev = (rev_act_26 / rev_tar_26 * 100) if rev_tar_26 > 0 else 0
            ebit_act_26 = df_2026['Actual EBITDA'].sum()
            ebit_tar_26 = df_2026['Target EBITDA'].sum()
            ach_ebit = (ebit_act_26 / ebit_tar_26 * 100) if ebit_tar_26 > 0 else 0

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Total Pendapatan 2026")
                st.write(f"### {format_rupiah_human(rev_act_26)}")
                st.caption(f"Target: {format_rupiah_human(rev_tar_26)}")
                st.write(f":green[{ach_rev:.1f}% vs Target 2026]" if ach_rev >= 100 else f":orange[{ach_rev:.1f}% vs Target 2026]")
            with col2:
                st.subheader("Total EBITDA 2026")
                st.write(f"### {format_rupiah_human(ebit_act_26)}")
                st.caption(f"Target: {format_rupiah_human(ebit_tar_26)}")
                st.write(f":green[{ach_ebit:.1f}% vs Target 2026]" if ach_ebit >= 100 else f":orange[{ach_ebit:.1f}% vs Target 2026]")

            st.markdown("---")

            # YoY Trend (Row 2)
            st.subheader("📈 Tren Pendapatan: 2026 vs 2025")
            df_group = df_filtered.groupby(['Bulan', 'Tahun'])['Actual Revenue (Total)'].sum().reset_index()
            df_group['Bulan'] = pd.Categorical(df_group['Bulan'], categories=month_order, ordered=True)
            df_group = df_group.sort_values(['Bulan', 'Tahun'])
            fig_yoy = px.bar(df_group, x='Bulan', y='Actual Revenue (Total)', color='Tahun', barmode='group',
                             color_discrete_map={"2026": "#2E86C1", "2025": "#AED6F1"})
            fig_yoy.update_layout(yaxis_tickformat=',.0f', yaxis_title="Pendapatan (Rp)", template="plotly_white", hovermode="x unified")
            for m in selected_bulan:
                rows = df_group[df_group['Bulan'] == m]
                v26 = rows[rows['Tahun'] == '2026']['Actual Revenue (Total)'].sum()
                v25 = rows[rows['Tahun'] == '2025']['Actual Revenue (Total)'].sum()
                if v26 != 0:
                    pct = ((v26 - v25) / v25 * 100) if v25 != 0 else 0
                    color = "#1E8449" if pct >= 0 else "#C0392B"
                    fig_yoy.add_annotation(x=m, y=v26, text=f"{'▲' if pct>=0 else '▼'} {abs(pct):.1f}%", 
                                           showarrow=False, yshift=15, font=dict(color=color, size=14, family="Arial Bold"))
            st.plotly_chart(fig_yoy, use_container_width=True)

            # RS Trend (Row 3)
            st.subheader("🏥 Tren Pertumbuhan Pendapatan per RS (2026)")
            df_rs_actual = df_2026.pivot_table(index='Bulan', columns='Cabang', values='Actual Revenue (Total)', aggfunc='sum').reindex(month_order)
            df_rs_target = df_2026.pivot_table(index='Bulan', columns='Cabang', values='Target Revenue (Total)', aggfunc='sum').reindex(month_order)
            fig_line = go.Figure()
            for rs in df_rs_actual.columns:
                color = COLOR_MAP.get(rs, DEFAULT_COLORS[0])
                fig_line.add_trace(go.Scatter(x=df_rs_actual.index, y=df_rs_actual[rs], name=f"Actual {rs}", mode='lines+markers', line=dict(color=color)))
                fig_line.add_trace(go.Scatter(x=df_rs_target.index, y=df_rs_target[rs], name=f"Target {rs}", mode='lines', line=dict(color=color, dash='dash', width=1.5), opacity=0.4))
            fig_line.update_layout(yaxis_tickformat=',.0f', yaxis_title="Pendapatan (Rp)", hovermode="x unified", template="plotly_white")
            st.plotly_chart(fig_line, use_container_width=True)

            # Pie & Bar Chart (Row 4)
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("📊 Komposisi Pendapatan per RS")
                fig_pie = px.pie(df_2026, values='Actual Revenue (Total)', names='Cabang', hole=0.4, color='Cabang', color_discrete_map=COLOR_MAP)
                fig_pie.update_traces(textinfo='percent+label', hovertemplate='RS: %{label}<br>Total: Rp %{value:,.0f}')
                st.plotly_chart(fig_pie, use_container_width=True)
            with col_b:
                st.subheader("🎯 Pencapaian EBITDA per RS")
                df_ebitda_rs = df_2026.groupby('Cabang')['Actual EBITDA'].sum().reset_index()
                fig_ebitda = px.bar(df_ebitda_rs, x='Cabang', y='Actual EBITDA', color='Cabang', color_discrete_map=COLOR_MAP)
                fig_ebitda.update_layout(yaxis_tickformat=',.0f', yaxis_title="EBITDA (Rp)", showlegend=False)
                st.plotly_chart(fig_ebitda, use_container_width=True)

            # --- ROW 5: TABEL DETAIL (DENGAN FORMAT NUMERIC) ---
            st.markdown("---")
            with st.expander("🔍 Lihat Detail Tabel Data"):
                df_display = df_filtered[['Tahun', 'Bulan', 'Cabang', 'Actual Revenue (Total)', 'Actual EBITDA']].sort_values(['Tahun', 'Bulan'], ascending=[False, True])
                
                # Gunakan st.dataframe dengan format pemisah ribuan
                st.dataframe(
                    df_display, 
                    use_container_width=True,
                    column_config={
                        "Actual Revenue (Total)": st.column_config.NumberColumn("Actual Revenue (Total)", format="%d"),
                        "Actual EBITDA": st.column_config.NumberColumn("Actual EBITDA", format="%d")
                    }
                )

except Exception as e:
    st.error(f"Sistem Error: {e}")
