import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Dashboard Keuangan RS", layout="wide", page_icon="📈")

# --- LOGO DI POJOK KIRI ATAS ---
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

# --- FUNGSI PEMETAAN KUARTAL ---
def get_quarter(bulan):
    q_map = {
        'Januari': 'Q1', 'Februari': 'Q1', 'Maret': 'Q1',
        'April': 'Q2', 'Mei': 'Q2', 'Juni': 'Q2',
        'Juli': 'Q3', 'Agustus': 'Q3', 'September': 'Q3',
        'Oktober': 'Q4', 'November': 'Q4', 'Desember': 'Q4'
    }
    return q_map.get(bulan, 'Unknown')

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
            df_tmp['Kuartal'] = df_tmp['Bulan'].apply(get_quarter)
            
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
    quarter_order = ['Q1', 'Q2', 'Q3', 'Q4']
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
            # --- KPI ---
            rev_act_26 = df_2026['Actual Revenue (Total)'].sum()
            rev_tar_26 = df_2026['Target Revenue (Total)'].sum()
            ach_rev = (rev_act_26 / rev_tar_26 * 100) if rev_tar_26 > 0 else 0
            ebit_act_26 = df_2026['Actual EBITDA'].sum()
            ebit_tar_26 = df_2026['Target EBITDA'].sum()
            ach_ebit = (ebit_act_26 / ebit_tar_26 * 100) if ebit_tar_26 > 0 else 0

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Total Pendapatan 2026")
                st.write(f"### {format_rupiah_human(rev_act_26)}")
                st.caption(f"Target: {format_rupiah_human(rev_tar_26)}")
                st.write(f":green[{ach_rev:.1f}% vs Target 2026]" if ach_rev >= 100 else f":orange[{ach_rev:.1f}% vs Target 2026]")
            with c2:
                st.subheader("Total EBITDA 2026")
                st.write(f"### {format_rupiah_human(ebit_act_26)}")
                st.caption(f"Target: {format_rupiah_human(ebit_tar_26)}")
                st.write(f":green[{ach_ebit:.1f}% vs Target 2026]" if ach_ebit >= 100 else f":orange[{ach_ebit:.1f}% vs Target 2026]")

            st.markdown("---")

            # --- ROW 2: TREN YoY (EBITDA INSIDE BARS) ---
            def create_combined_chart(df_group, x_col, x_order, title):
                df_group[x_col] = pd.Categorical(df_group[x_col], categories=x_order, ordered=True)
                df_group = df_group.sort_values([x_col, 'Tahun'])
                
                fig = go.Figure()
                
                # Revenue Bars
                for yr, color in zip(["2025", "2026"], ["#AED6F1", "#2E86C1"]):
                    yr_data = df_group[df_group['Tahun'] == yr]
                    fig.add_trace(go.Bar(
                        x=yr_data[x_col], y=yr_data['Actual Revenue (Total)'],
                        name=f"Rev {yr}", marker_color=color,
                        offsetgroup=yr
                    ))
                
                # EBITDA Points & Line (Using numeric mapping for X-axis positioning)
                # This places the markers exactly in the middle of the grouped bars
                x_indices = list(range(len(x_order)))
                for yr, color, dash, offset in zip(["2025", "2026"], ["#FAD7A0", "#D35400"], ["dash", "solid"], [-0.2, 0.2]):
                    yr_data = df_group[df_group['Tahun'] == yr]
                    # Create numeric X positions for the markers
                    # We map categories to numbers and add the offset
                    current_x = [x_indices[x_order.index(val)] + offset for val in yr_data[x_col]]
                    
                    fig.add_trace(go.Scatter(
                        x=current_x, y=yr_data['Actual EBITDA'],
                        name=f"EBITDA {yr}", mode='lines+markers',
                        line=dict(color=color, width=3, dash=dash),
                        marker=dict(size=10, symbol='diamond'),
                        hoverinfo='y+name'
                    ))

                # Growth Label
                for i, x_val in enumerate(x_order):
                    rows = df_group[df_group[x_col] == x_val]
                    v26 = rows[rows['Tahun'] == '2026']['Actual Revenue (Total)'].sum()
                    v25 = rows[rows['Tahun'] == '2025']['Actual Revenue (Total)'].sum()
                    if v26 != 0 and v25 != 0:
                        pct = ((v26 - v25) / v25 * 100)
                        fig.add_annotation(x=i + 0.2, y=v26, text=f"{pct:.1f}%", showarrow=False, yshift=10, font=dict(color="#1E8449" if pct>=0 else "#C0392B", size=12, family="Arial Bold"))

                fig.update_layout(
                    title=title, yaxis_tickformat=',.0f', template="plotly_white", 
                    barmode='group',
                    xaxis=dict(tickmode='array', tickvals=x_indices, ticktext=x_order),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                return fig

            st.subheader("📊 Analisis Tren YoY (EBITDA di Dalam Batang Pendapatan)")
            df_q_yoy = df_filtered.groupby(['Kuartal', 'Tahun'])[['Actual Revenue (Total)', 'Actual EBITDA']].sum().reset_index()
            st.plotly_chart(create_combined_chart(df_q_yoy, 'Kuartal', quarter_order, "Analisis per Kuartal"), use_container_width=True)
            
            df_m_yoy = df_filtered.groupby(['Bulan', 'Tahun'])[['Actual Revenue (Total)', 'Actual EBITDA']].sum().reset_index()
            st.plotly_chart(create_combined_chart(df_m_yoy, 'Bulan', month_order, "Analisis per Bulan"), use_container_width=True)

            # --- ROW 3: TREN PER RS ---
            st.subheader("🏥 Tren Pendapatan per RS (2026)")
            df_rs_actual = df_2026.pivot_table(index='Bulan', columns='Cabang', values='Actual Revenue (Total)', aggfunc='sum').reindex(month_order)
            df_rs_target = df_2026.pivot_table(index='Bulan', columns='Cabang', values='Target Revenue (Total)', aggfunc='sum').reindex(month_order)
            fig_line = go.Figure()
            for rs in df_rs_actual.columns:
                color = COLOR_MAP.get(rs, DEFAULT_COLORS[0])
                fig_line.add_trace(go.Scatter(x=df_rs_actual.index, y=df_rs_actual[rs], name=f"Act {rs}", mode='lines+markers', line=dict(color=color)))
                fig_line.add_trace(go.Scatter(x=df_rs_target.index, y=df_rs_target[rs], name=f"Tar {rs}", mode='lines', line=dict(color=color, dash='dash', width=1.5), opacity=0.4))
            fig_line.update_layout(yaxis_tickformat=',.0f', template="plotly_white", hovermode="x unified")
            st.plotly_chart(fig_line, use_container_width=True)

            # --- ROW 4: KOMPOSISI & EBITDA ---
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("📊 Komposisi Pendapatan per RS")
                fig_pie = px.pie(df_2026, values='Actual Revenue (Total)', names='Cabang', hole=0.4, color='Cabang', color_discrete_map=COLOR_MAP)
                fig_pie.update_traces(textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
            with col_b:
                st.subheader("🎯 Pencapaian EBITDA per RS")
                df_ebitda_rs = df_2026.groupby('Cabang')['Actual EBITDA'].sum().reset_index()
                fig_ebitda = px.bar(df_ebitda_rs, x='Cabang', y='Actual EBITDA', color='Cabang', color_discrete_map=COLOR_MAP)
                fig_ebitda.update_layout(yaxis_tickformat=',.0f', showlegend=False)
                st.plotly_chart(fig_ebitda, use_container_width=True)

            # --- ROW 5: TABEL DETAIL ---
            st.markdown("---")
            with st.expander("🔍 Lihat Detail Tabel Data"):
                df_display = df_filtered[['Tahun', 'Kuartal', 'Bulan', 'Cabang', 'Actual Revenue (Total)', 'Actual EBITDA']].sort_values(['Tahun', 'Bulan'], ascending=[False, True])
                st.dataframe(df_display, use_container_width=True, column_config={"Actual Revenue (Total)": st.column_config.NumberColumn(format="%d"), "Actual EBITDA": st.column_config.NumberColumn(format="%d")})

except Exception as e:
    st.error(f"Sistem Error: {e}")
