import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import os
from io import BytesIO

# =========================================================
# KONFIGURASI HALAMAN
# =========================================================
st.set_page_config(
    page_title="Dashboard Performance Helsa",
    layout="wide",
    page_icon="📈"
)

# =========================================================
# LOGO
# =========================================================
LOGO_FILE = "HELSA Rumah sakit.png"

if os.path.exists(LOGO_FILE):
    st.image(LOGO_FILE, width=250)
else:
    st.warning("⚠️ File logo tidak ditemukan")

# =========================================================
# COLOR MAP
# =========================================================
COLOR_MAP = {
    "Jatirahayu": "#636EFA",
    "Cikampek": "#EF553B",
    "Citeureup": "#00CC96",
    "Ciputat": "#AB63FA",
}

DEFAULT_COLORS = px.colors.qualitative.Plotly

# =========================================================
# FORMAT RUPIAH
# =========================================================
def format_rupiah_human(n):

    if pd.isna(n):
        return "Rp 0"

    prefix = "-" if n < 0 else ""
    val = abs(n)

    if val >= 1_000_000_000:
        return f"{prefix}Rp {val / 1_000_000_000:.2f} Miliar"

    elif val >= 1_000_000:
        return f"{prefix}Rp {val / 1_000_000:.2f} Juta"

    return f"{prefix}Rp {val:,.0f}"

# =========================================================
# CLEAN NUMERIC
# =========================================================
def clean_to_numeric(value):

    if pd.isna(value) or str(value).strip() == "":
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    val_str = str(value).strip()

    # format negatif (1.000.000)
    if val_str.startswith("(") and val_str.endswith(")"):
        val_str = "-" + val_str[1:-1]

    # hapus Rp dan spasi
    val_str = val_str.replace("Rp", "").replace(" ", "")

    # format indo 1.234.567,89
    val_str = val_str.replace(".", "").replace(",", ".")

    cleaned = re.sub(r"[^0-9\.-]", "", val_str)

    try:
        return float(cleaned)
    except:
        return 0.0

# =========================================================
# QUARTER
# =========================================================
def get_quarter(bulan):

    q_map = {
        'Januari': 'Q1',
        'Februari': 'Q1',
        'Maret': 'Q1',
        'April': 'Q2',
        'Mei': 'Q2',
        'Juni': 'Q2',
        'Juli': 'Q3',
        'Agustus': 'Q3',
        'September': 'Q3',
        'Oktober': 'Q4',
        'November': 'Q4',
        'Desember': 'Q4'
    }

    return q_map.get(bulan, 'Unknown')

# =========================================================
# LOAD DATA
# =========================================================
@st.cache_data(ttl=300)
def load_combined_data():

    sheet_id = "1oqXKKPNnlMOSBhkWi9_7Isjo_NYtHE2ytfeO-bSNMxY"

    sheets = {
        "2025": "app_data_2025",
        "2026": "app_data_2026"
    }

    combined = []

    numeric_cols = [
        'Actual Revenue (Total)',
        'Actual EBITDA',
        'Target Revenue (Total)',
        'Target EBITDA'
    ]

    for year, sheet_name in sheets.items():

        try:

            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

            df_tmp = pd.read_csv(url, dtype=str)

            df_tmp.columns = [str(c).strip() for c in df_tmp.columns]

            if 'Cabang' not in df_tmp.columns:
                df_tmp['Cabang'] = 'Unknown'

            if 'Bulan' not in df_tmp.columns:
                df_tmp['Bulan'] = 'Unknown'

            df_tmp['Tahun'] = year
            df_tmp['Kuartal'] = df_tmp['Bulan'].apply(get_quarter)

            for col in numeric_cols:

                if col in df_tmp.columns:
                    df_tmp[col] = df_tmp[col].apply(clean_to_numeric)
                    df_tmp[col] = pd.to_numeric(df_tmp[col], errors='coerce').fillna(0)

                else:
                    df_tmp[col] = 0

            combined.append(df_tmp)

        except Exception as e:
            st.warning(f"Gagal load sheet {sheet_name}: {e}")

    if combined:
        return pd.concat(combined, ignore_index=True)

    return pd.DataFrame()

# =========================================================
# EXPORT EXCEL
# =========================================================
def create_excel(df):

    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dashboard Data')

    processed_data = output.getvalue()

    return processed_data

# =========================================================
# MAIN APP
# =========================================================
try:

    df_all = load_combined_data()

    month_order = [
        'Januari', 'Februari', 'Maret',
        'April', 'Mei', 'Juni',
        'Juli', 'Agustus', 'September',
        'Oktober', 'November', 'Desember'
    ]

    quarter_order = ['Q1', 'Q2', 'Q3', 'Q4']

    # =====================================================
    # SIDEBAR
    # =====================================================
    st.sidebar.header("⚙️ Filter Dashboard")

    if not df_all.empty:

        available_years = sorted(df_all['Tahun'].unique())

        selected_years = st.sidebar.multiselect(
            "Pilih Tahun",
            available_years,
            default=available_years
        )

        list_cabang = sorted(df_all['Cabang'].unique())

        selected_cabang = st.sidebar.multiselect(
            "Pilih Cabang",
            list_cabang,
            default=list_cabang
        )

        available_months = [
            m for m in month_order
            if m in df_all['Bulan'].unique()
        ]

        selected_bulan = st.sidebar.multiselect(
            "Pilih Bulan",
            available_months,
            default=available_months
        )

        # =====================================================
        # FILTER DATA
        # =====================================================
        df_filtered = df_all[
            (df_all['Tahun'].isin(selected_years)) &
            (df_all['Cabang'].isin(selected_cabang)) &
            (df_all['Bulan'].isin(selected_bulan))
        ].copy()

        latest_year = max(selected_years)

        df_latest = df_filtered[
            df_filtered['Tahun'] == latest_year
        ]

        # =====================================================
        # TITLE
        # =====================================================
        st.title("🏥 Performance Dashboard Helsa Group")
        st.caption("Corporate Performance Monitoring Dashboard")

        st.markdown("---")

        # =====================================================
        # KPI SECTION
        # =====================================================
        if not df_latest.empty:

            rev_actual = df_latest['Actual Revenue (Total)'].sum()
            rev_target = df_latest['Target Revenue (Total)'].sum()

            ebit_actual = df_latest['Actual EBITDA'].sum()
            ebit_target = df_latest['Target EBITDA'].sum()

            ach_rev = (rev_actual / rev_target * 100) if rev_target > 0 else 0
            ach_ebit = (ebit_actual / ebit_target * 100) if ebit_target > 0 else 0

            margin = (ebit_actual / rev_actual * 100) if rev_actual > 0 else 0

            prev_year = str(int(latest_year) - 1)

            df_prev = df_filtered[
                df_filtered['Tahun'] == prev_year
            ]

            prev_revenue = df_prev['Actual Revenue (Total)'].sum()

            yoy_growth = (
                (rev_actual - prev_revenue) / prev_revenue * 100
            ) if prev_revenue > 0 else 0

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Revenue",
                    format_rupiah_human(rev_actual),
                    f"{ach_rev:.1f}% vs Target"
                )

            with col2:
                st.metric(
                    "EBITDA",
                    format_rupiah_human(ebit_actual),
                    f"{ach_ebit:.1f}% vs Target"
                )

            with col3:
                st.metric(
                    "EBITDA Margin",
                    f"{margin:.1f}%"
                )

            with col4:
                st.metric(
                    "YoY Revenue Growth",
                    f"{yoy_growth:.1f}%"
                )

            st.markdown("---")

            # =====================================================
            # QUARTER YOY
            # =====================================================
            st.subheader("📊 Analisis YoY per Kuartal")

            df_q = df_filtered.groupby(
                ['Kuartal', 'Tahun']
            )[
                ['Actual Revenue (Total)', 'Actual EBITDA']
            ].sum().reset_index()

            df_q['Kuartal'] = pd.Categorical(
                df_q['Kuartal'],
                categories=quarter_order,
                ordered=True
            )

            df_q = df_q.sort_values(['Kuartal', 'Tahun'])

            fig_q = go.Figure()

            for yr, color in zip(
                available_years,
                ["#AED6F1", "#2E86C1", "#1B4F72"]
            ):

                yr_data = df_q[df_q['Tahun'] == yr]

                fig_q.add_trace(
                    go.Bar(
                        x=yr_data['Kuartal'],
                        y=yr_data['Actual Revenue (Total)'],
                        name=f"Revenue {yr}",
                        marker_color=color,
                        offsetgroup=yr
                    )
                )

            for yr, color in zip(
                available_years,
                ["#FAD7A0", "#D35400", "#6E2C00"]
            ):

                yr_data = df_q[df_q['Tahun'] == yr]

                fig_q.add_trace(
                    go.Scatter(
                        x=yr_data['Kuartal'],
                        y=yr_data['Actual EBITDA'],
                        name=f"EBITDA {yr}",
                        mode='lines+markers',
                        line=dict(color=color, width=3)
                    )
                )

            fig_q.update_layout(
                template="plotly_white",
                hovermode="x unified",
                barmode='group',
                yaxis_tickformat=',.0f'
            )

            st.plotly_chart(fig_q, use_container_width=True)

            # =====================================================
            # MONTHLY TREND
            # =====================================================
            st.subheader("📅 Tren Pendapatan per Bulan")

            df_month = df_latest.groupby(
                ['Bulan', 'Cabang']
            )[
                'Actual Revenue (Total)'
            ].sum().reset_index()

            df_month['Bulan'] = pd.Categorical(
                df_month['Bulan'],
                categories=month_order,
                ordered=True
            )

            df_month = df_month.sort_values('Bulan')

            fig_month = px.line(
                df_month,
                x='Bulan',
                y='Actual Revenue (Total)',
                color='Cabang',
                markers=True,
                color_discrete_map=COLOR_MAP
            )

            fig_month.update_layout(
                template="plotly_white",
                hovermode="x unified",
                yaxis_tickformat=',.0f'
            )

            st.plotly_chart(fig_month, use_container_width=True)

            # =====================================================
            # PIE + EBITDA
            # =====================================================
            col_a, col_b = st.columns(2)

            with col_a:

                st.subheader("📊 Komposisi Revenue")

                fig_pie = px.pie(
                    df_latest,
                    values='Actual Revenue (Total)',
                    names='Cabang',
                    hole=0.4,
                    color='Cabang',
                    color_discrete_map=COLOR_MAP
                )

                fig_pie.update_traces(
                    textinfo='percent+label'
                )

                st.plotly_chart(fig_pie, use_container_width=True)

            with col_b:

                st.subheader("🎯 EBITDA per RS")

                df_ebit = df_latest.groupby(
                    'Cabang'
                )[
                    'Actual EBITDA'
                ].sum().reset_index()

                fig_ebit = px.bar(
                    df_ebit,
                    x='Cabang',
                    y='Actual EBITDA',
                    color='Cabang',
                    color_discrete_map=COLOR_MAP
                )

                fig_ebit.update_layout(
                    template="plotly_white",
                    yaxis_tickformat=',.0f',
                    showlegend=False
                )

                st.plotly_chart(fig_ebit, use_container_width=True)

            # =====================================================
            # RANKING RS
            # =====================================================
            st.markdown("---")

            st.subheader("🏆 Ranking Performance RS")

            ranking_df = df_latest.groupby('Cabang').agg({
                'Actual Revenue (Total)': 'sum',
                'Target Revenue (Total)': 'sum',
                'Actual EBITDA': 'sum'
            }).reset_index()

            ranking_df['Achievement %'] = (
                ranking_df['Actual Revenue (Total)']
                / ranking_df['Target Revenue (Total)']
                * 100
            ).round(1)

            ranking_df['EBITDA Margin %'] = (
                ranking_df['Actual EBITDA']
                / ranking_df['Actual Revenue (Total)']
                * 100
            ).round(1)

            ranking_df = ranking_df.sort_values(
                'Actual Revenue (Total)',
                ascending=False
            )

            st.dataframe(
                ranking_df,
                use_container_width=True
            )

            # =====================================================
            # DOWNLOAD EXCEL
            # =====================================================
            st.markdown("---")

            excel_data = create_excel(ranking_df)

            st.download_button(
                label="📥 Download Ranking Excel",
                data=excel_data,
                file_name="ranking_performance_helsa.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # =====================================================
            # DETAIL TABLE
            # =====================================================
            with st.expander("🔍 Detail Data"):

                display_df = df_filtered[
                    [
                        'Tahun',
                        'Kuartal',
                        'Bulan',
                        'Cabang',
                        'Actual Revenue (Total)',
                        'Target Revenue (Total)',
                        'Actual EBITDA',
                        'Target EBITDA'
                    ]
                ].sort_values(
                    ['Tahun', 'Bulan'],
                    ascending=[False, True]
                )

                st.dataframe(
                    display_df,
                    use_container_width=True
                )

    else:
        st.error("Data tidak ditemukan")

except Exception as e:

    st.error(f"Sistem Error: {e}")
