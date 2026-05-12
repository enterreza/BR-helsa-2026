import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Dashboard Keuangan RS", layout="wide", page_icon="📈")

# --- LOGO ---
LOGO_FILE = "HELSA Rumah sakit.png"
if os.path.exists(LOGO_FILE):
    st.image(LOGO_FILE, use_container_width=False, width=250)

# --- DEFINISI WARNA ---
COLOR_MAP_RS = {
    "Jatirahayu": "#636EFA", 
    "Cikampek": "#EF553B",   
    "Citeureup": "#00CC96",  
    "Ciputat": "#AB63FA",    
}

# --- FUNGSI HELPER ---
def format_rupiah_human(n):
    prefix = "-" if n < 0 else ""
    val = abs(n)
    if val >= 1_000_000_000:
        return f"{prefix}Rp {val / 1_000_000_000:.2f} Miliar"
    elif val >= 1_000_000:
        return f"{prefix}Rp {val / 1_000_000:.2f} Juta"
    else:
        return f"{prefix}Rp {val:,.0f}"

def clean_to_numeric(value):
    if pd.isna(value) or str(value).strip() == "":
        return 0.0
    val_str = str(value).strip().replace('(', '-').replace(')', '').replace(',', '')
    cleaned = re.sub(r'[^0-9.\-]', '', val_str)
    try:
        return float(cleaned) if cleaned != "" else 0.0
    except:
        return 0.0

def get_quarter(bulan):
    q_map = {
        'Januari': 'Q1', 'Februari': 'Q1', 'Maret': 'Q1',
        'April': 'Q2', 'Mei': 'Q2', 'Juni': 'Q2',
        'Juli': 'Q3', 'Agustus': 'Q3', 'September': 'Q3',
        'Oktober': 'Q4', 'November': 'Q4', 'Desember': 'Q4'
    }
    return q_map.get(bulan, 'Unknown')

# --- LOAD DATA ---
@st.cache_data
def load_combined_data():
    sheet_id = "1oqXKKPNnlMOSBhkWi9_7Isjo_NYtHE2ytfeO-bSNMxY"
    sheets = {"2026": "app_data", "2025": "app_data_2025"}
    combined_list = []
    for year, s_name in sheets.items():
        try:
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={s_name}"
            df_tmp = pd.read_csv(url, dtype=str)
            df_tmp['Tahun'] = year
            df_tmp['Kuartal'] = df_tmp['Bulan'].apply(get_quarter)
            for col in ['Actual Revenue (Total)', 'Actual EBITDA', 'Target Revenue (Total)', 'Target EBITDA']:
                if col in df_tmp.columns:
                    df_tmp[col] = df_tmp[col].apply(clean_to_numeric)
            combined_list.append(df_tmp)
        except:
            continue
    return pd.concat(combined_list, ignore_index=True) if combined_list else pd.DataFrame()

# --- MAIN APP ---
try:
    df_all = load_combined_data()
    quarter_order = ['Q1', 'Q2', 'Q3', 'Q4']
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

    if not df_all.empty:
        st.sidebar.header("⚙️ Filter")
        list_cabang = sorted(df_all['Cabang'].unique())
        selected_cabang = st.sidebar.multiselect("Pilih Cabang", list_cabang, default=list_cabang)
        df_filtered = df_all[df_all['Cabang'].isin(selected_cabang)].copy()

        st.title("🏥 Performance Dashboard RS Group")
        st.markdown("---")

        # FUNGSI UNTUK MEMBUAT GRAFIK KOMBINASI
        def plot_yoy_combined(df_group, x_col, x_order, title):
            df_group[x_col] = pd.Categorical(df_group[x_col], categories=x_order, ordered=True)
            df_group = df_group.sort_values([x_col, 'Tahun'])
            
            fig = go.Figure()
            
            # Bar Revenue
            for yr, color in zip(["2025", "2026"], ["#AED6F1", "#2E86C1"]):
                data = df_group[df_group['Tahun'] == yr]
                fig.add_trace(go.Bar(
                    x=data[x_col], y=data['Actual Revenue (Total)'],
                    name=f"Rev {yr}", marker_color=color, offsetgroup=yr
                ))
            
            # Line EBITDA
            for yr, color, dash in zip(["2025", "2026"], ["#FAD7A0", "#D35400"], ["dash", "solid"]):
                data = df_group[df_group['Tahun'] == yr]
                fig.add_trace(go.Scatter(
                    x=data[x_col], y=data['Actual EBITDA'],
                    name=f"EBITDA {yr}", mode='lines+markers',
                    line=dict(color=color, width=3, dash=dash)
                ))

            # Label Growth % (Revenue)
            for x_val in df_group[x_col].unique():
                subset = df_group[df_group[x_col] == x_val]
                v26 = subset[subset['Tahun'] == '2026']['Actual Revenue (Total)'].sum()
                v25 = subset[subset['Tahun'] == '2025']['Actual Revenue (Total)'].sum()
                if v26 != 0 and v25 != 0:
                    pct = ((v26 - v25) / v25 * 100)
                    fig.add_annotation(x=x_val, y=v26, text=f"{pct:.1f}%", showarrow=False, yshift=10, 
                                     font=dict(color="#1E8449" if pct>=0 else "#C0392B", size=11, family="Arial Bold"))

            fig.update_layout(
                title=title, yaxis_tickformat=',.0f', template="plotly_white", 
                barmode='group', hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            return fig

        # --- ROW: GRAFIK KUARTAL & BULANAN ---
        st.subheader("📊 Analisis Tren YoY (Revenue & EBITDA)")
        
        # Kuartal
        df_q = df_filtered.groupby(['Kuartal', 'Tahun'])[['Actual Revenue (Total)', 'Actual EBITDA']].sum().reset_index()
        st.plotly_chart(plot_yoy_combined(df_q, 'Kuartal', quarter_order, "Tren YoY per Kuartal"), use_container_width=True)
        
        # Bulanan
        df_m = df_filtered.groupby(['Bulan', 'Tahun'])[['Actual Revenue (Total)', 'Actual EBITDA']].sum().reset_index()
        st.plotly_chart(plot_yoy_combined(df_m, 'Bulan', month_order, "Tren YoY per Bulan"), use_container_width=True)

        st.markdown("---")

        # --- ROW: TREN PER RS (2026) ---
        st.subheader("🏥 Tren Pendapatan per RS (2026)")
        df_2026 = df_filtered[df_filtered['Tahun'] == '2026']
        if not df_2026.empty:
            df_rs_actual = df_2026.pivot_table(index='Bulan', columns='Cabang', values='Actual Revenue (Total)', aggfunc='sum').reindex(month_order)
            fig_rs = go.Figure()
            for rs in df_rs_actual.columns:
                fig_rs.add_trace(go.Scatter(x=df_rs_actual.index, y=df_rs_actual[rs], name=rs, mode='lines+markers', line=dict(color=COLOR_MAP_RS.get(rs))))
            fig_rs.update_layout(yaxis_tickformat=',.0f', template="plotly_white", hovermode="x unified")
            st.plotly_chart(fig_rs, use_container_width=True)

        # --- TABEL DETAIL ---
        with st.expander("🔍 Lihat Detail Tabel Data"):
            st.dataframe(df_filtered.sort_values(['Tahun', 'Bulan'], ascending=[False, True]), use_container_width=True)

except Exception as e:
    st.error(f"Sistem Error: {e}")
