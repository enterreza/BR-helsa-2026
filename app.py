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
# Kita gunakan satu tema warna per tahun agar Bar dan Line menyatu
COLOR_2025 = "#AED6F1" # Blue Light
COLOR_2026 = "#2E86C1" # Blue Dark
COLOR_MAP_RS = {"Jatirahayu": "#636EFA", "Cikampek": "#EF553B", "Citeureup": "#00CC96", "Ciputat": "#AB63FA"}

# --- FUNGSI HELPER ---
def format_rupiah_human(n):
    prefix = "-" if n < 0 else ""
    val = abs(n)
    if val >= 1_000_000_000: return f"{prefix}Rp {val / 1_000_000_000:.2f} Miliar"
    if val >= 1_000_000: return f"{prefix}Rp {val / 1_000_000:.2f} Juta"
    return f"{prefix}Rp {val:,.0f}"

def clean_to_numeric(value):
    if pd.isna(value) or str(value).strip() == "": return 0.0
    val_str = str(value).strip().replace('(', '-').replace(')', '').replace(',', '')
    cleaned = re.sub(r'[^0-9.\-]', '', val_str)
    try: return float(cleaned) if cleaned != "" else 0.0
    except: return 0.0

def get_quarter(bulan):
    q_map = {'Januari':'Q1','Februari':'Q1','Maret':'Q1','April':'Q2','Mei':'Q2','Juni':'Q2',
             'Juli':'Q3','Agustus':'Q3','September':'Q3','Oktober':'Q4','November':'Q4','Desember':'Q4'}
    return q_map.get(bulan, 'Unknown')

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
            for col in ['Actual Revenue (Total)', 'Actual EBITDA']:
                df_tmp[col] = df_tmp[col].apply(clean_to_numeric)
            combined_list.append(df_tmp)
        except: continue
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

        def create_unified_chart(df_group, x_col, x_order, title):
            df_group[x_col] = pd.Categorical(df_group[x_col], categories=x_order, ordered=True)
            df_group = df_group.sort_values([x_col, 'Tahun'])
            x_indices = list(range(len(x_order)))
            
            fig = go.Figure()
            
            for yr, color, offset in zip(["2025", "2026"], [COLOR_2025, COLOR_2026], [-0.2, 0.2]):
                yr_data = df_group[df_group['Tahun'] == yr]
                
                # Bar Revenue - Dikelompokkan dalam legendgroup yang sama dengan EBITDA
                fig.add_trace(go.Bar(
                    x=yr_data[x_col], y=yr_data['Actual Revenue (Total)'],
                    name=f"Revenue {yr}", marker_color=color,
                    offsetgroup=yr, legendgroup=yr,
                    hovertemplate="Rev: %{y:,.0f}"
                ))
                
                # Line/Marker EBITDA - Diletakkan tepat di atas Bar masing-masing
                current_x = [x_indices[x_order.index(val)] + offset for val in yr_data[x_col]]
                fig.add_trace(go.Scatter(
                    x=current_x, y=yr_data['Actual EBITDA'],
                    name=f"EBITDA {yr}", mode='lines+markers',
                    line=dict(color=color, width=2),
                    marker=dict(size=8, symbol='diamond', line=dict(width=1, color='white')),
                    legendgroup=yr, showlegend=True,
                    hovertemplate="EBITDA: %{y:,.0f}"
                ))

            # Label Pertumbuhan Revenue di atas Bar 2026
            for i, x_val in enumerate(x_order):
                rows = df_group[df_group[x_col] == x_val]
                v26 = rows[rows['Tahun'] == '2026']['Actual Revenue (Total)'].sum()
                v25 = rows[rows['Tahun'] == '2025']['Actual Revenue (Total)'].sum()
                if v26 != 0 and v25 != 0:
                    pct = ((v26 - v25) / v25 * 100)
                    fig.add_annotation(x=i + 0.2, y=v26, text=f"{pct:.1f}%", showarrow=False, yshift=10, 
                                     font=dict(color="#1E8449" if pct>=0 else "#C0392B", size=11, family="Arial Bold"))

            fig.update_layout(
                title=title, yaxis_tickformat=',.0f', template="plotly_white",
                xaxis=dict(tickmode='array', tickvals=x_indices, ticktext=x_order),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                hovermode="x unified", barmode='group'
            )
            return fig

        # --- Display Charts ---
        st.subheader("📊 Analisis Tren Terintegrasi (Revenue & EBITDA)")
        
        # Kuartal
        df_q = df_filtered.groupby(['Kuartal', 'Tahun'])[['Actual Revenue (Total)', 'Actual EBITDA']].sum().reset_index()
        st.plotly_chart(create_unified_chart(df_q, 'Kuartal', quarter_order, "Tren per Kuartal"), use_container_width=True)
        
        # Bulanan
        df_m = df_filtered.groupby(['Bulan', 'Tahun'])[['Actual Revenue (Total)', 'Actual EBITDA']].sum().reset_index()
        st.plotly_chart(create_unified_chart(df_m, 'Bulan', month_order, "Tren per Bulan"), use_container_width=True)

        # --- Tabel Data ---
        with st.expander("🔍 Detail Tabel"):
            st.dataframe(df_filtered.sort_values(['Tahun', 'Bulan'], ascending=False), use_container_width=True)

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
