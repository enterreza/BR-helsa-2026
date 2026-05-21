import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import os
from io import BytesIO

# =========================================================
# PAGE CONFIG
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
    st.warning("⚠️ File logo 'HELSA Rumah sakit.png' tidak ditemukan.")

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

    prefix = "-" if n < 0 else ""
    val = abs(n)

    if val >= 1_000_000_000:
        return f"{prefix}Rp {val / 1_000_000_000:.2f} Miliar"

    elif val >= 1_000_000:
        return f"{prefix}Rp {val / 1_000_000:.2f} Juta"

    else:
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

    # format negatif: (1000000)
    if val_str.startswith("(") and val_str.endswith(")"):
        val_str = "-" + val_str[1:-1]

    # hapus selain angka dan minus
    cleaned = re.sub(r'[^0-9\-]', '', val_str)

    try:
        return float(cleaned) if cleaned != "" else 0.0

    except ValueError:
        return 0.0

# =========================================================
# QUARTER MAPPING
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

    combined_list = []

    numeric_cols = [
        'Actual Revenue (Total)',
        'Actual EBITDA',
        'Target Revenue (Total)',
        'Target EBITDA'
    ]

    for year, s_name in sheets.items():

        try:

            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={s_name}"

            df_tmp = pd.read_csv(url, dtype=str)

            df_tmp.columns = [str(col).strip() for col in df_tmp.columns]

            if 'Cabang' not in df_tmp.columns:
                df_tmp['Cabang'] = 'Unknown'

            if 'Bulan' not in df_tmp.columns:
                df_tmp['Bulan'] = 'Unknown'

            df_tmp['Tahun'] = str(year)

            df_tmp['Kuartal'] = df_tmp['Bulan'].apply(get_quarter)

            for col in numeric_cols:

                if col in df_tmp.columns:

                    df_tmp[col] = df_tmp[col].apply(clean_to_numeric)

                    df_tmp[col] = pd.to_numeric(
                        df_tmp[col],
                        errors='coerce'
                    ).fillna(0)

                else:
                    df_tmp[col] = 0.0

            combined_list.append(df_tmp)

        except Exception as e:
            st.warning(f"Gagal load sheet {s_name}: {e}")

    if combined_list:
        return pd.concat(combined_list, ignore_index=True)

    return pd.DataFrame()

# =========================================================
# EXPORT EXCEL
# =========================================================
def create_excel(df):

    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dashboard')

    processed_data = output.getvalue()

    return processed_data

# =========================================================
# MAIN APP
# =========================================================
try:

    df_all = load_combined_data()

    quarter_order = ['Q1', 'Q2', 'Q3', 'Q4']

    month_order = [
        'Januari',
        'Februari',
        'Maret',
        'April',
        'Mei',
        'Juni',
        'Juli',
        'Agustus',
        'September',
        'Oktober',
        'November',
        'Desember'
    ]

    # =====================================================
    # SIDEBAR
    # =====================================================
    st.sidebar.header("⚙️ Filter")

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

        # =====================================================
        # DEBUG
        # =====================================================
        # st.write(df_filtered.head())
        # st.write(df_filtered.shape)

        # =====================================================
        # YEAR TERBARU
        # =====================================================
        latest_year = str(max([int(y) for y in selected_years]))

        df_latest = df_filtered[
            df_filtered['Tahun'] == latest_year
        ]

        # =====================================================
        # TITLE
        # =====================================================
        st.title("🏥 Performance Dashboard Helsa Group")

        st.markdown("---")

        # =====================================================
        # KPI
        # =====================================================
        if not df_latest.empty:

            rev_act = df_latest['Actual Revenue (Total)'].sum()

            rev_tar = df_latest['Target Revenue (Total)'].sum()

            ach_rev = (
                rev_act / rev_tar * 100
            ) if rev_tar > 0 else 0

            ebit_act = df_latest['Actual EBITDA'].sum()

            ebit_tar = df_latest['Target EBITDA'].sum()

            ach_ebit = (
                ebit_act / ebit_tar * 100
            ) if ebit_tar > 0 else 0

            # EBITDA MARGIN
            ebit_margin = (
                ebit_act / rev_act * 100
            ) if rev_act > 0 else 0

            # YoY Growth
            prev_year = str(int(latest_year) - 1)

            df_prev = df_filtered[
                df_filtered['Tahun'] == prev_year
            ]

            prev_rev = df_prev['Actual Revenue (Total)'].sum()

            yoy_growth = (
                (rev_act - prev_rev) / prev_rev * 100
            ) if prev_rev > 0 else 0

            # KPI DISPLAY
            col1, col2, col3, col4 = st.columns(4)

            with col1:

                st.metric(
                    "Revenue",
                    format_rupiah_human(rev_act),
                    f"{ach_rev:.1f}% vs Target"
                )

            with col2:

                st.metric(
                    "EBITDA",
                    format_rupiah_human(ebit_act),
                    f"{ach_ebit:.1f}% vs Target"
                )

            with col3:

                st.metric(
                    "EBITDA Margin",
                    f"{ebit_margin:.1f}%"
                )

            with col4:

                st.metric(
                    "YoY Growth",
                    f"{yoy_growth:.1f}%"
                )

            st.markdown("---")

            # =====================================================
            # QUARTER YOY
            # =====================================================
            st.subheader("📊 Analisis Tren YoY per Kuartal")

            df_q_yoy = df_filtered.groupby(
                ['Kuartal', 'Tahun']
            )[
                ['Actual Revenue (Total)', 'Actual EBITDA']
            ].sum().reset_index()

            df_q_yoy['Kuartal'] = pd.Categorical(
                df_q_yoy['Kuartal'],
                categories=quarter_order,
                ordered=True
            )

            df_q_yoy = df_q_yoy.sort_values(
                ['Kuartal', 'Tahun']
            )

            fig_q_comb = go.Figure()

            # Revenue Bar
            revenue_colors = [
                "#AED6F1",
                "#2E86C1",
                "#1B4F72"
            ]

            for idx, yr in enumerate(available_years):

                yr_data = df_q_yoy[
                    df_q_yoy['Tahun'] == yr
                ]

                fig_q_comb.add_trace(
                    go.Bar(
                        x=yr_data['Kuartal'],
                        y=yr_data['Actual Revenue (Total)'],
                        name=f"Revenue {yr}",
                        marker_color=revenue_colors[idx % len(revenue_colors)],
                        offsetgroup=yr
                    )
                )

            # EBITDA Line
            ebit_colors = [
                "#FAD7A0",
                "#D35400",
                "#6E2C00"
            ]

            for idx, yr in enumerate(available_years):

                yr_data = df_q_yoy[
                    df_q_yoy['Tahun'] == yr
                ]

                fig_q_comb.add_trace(
                    go.Scatter(
                        x=yr_data['Kuartal'],
                        y=yr_data['Actual EBITDA'],
                        name=f"EBITDA {yr}",
                        mode='lines+markers',
                        line=dict(
                            color=ebit_colors[idx % len(ebit_colors)],
                            width=3
                        )
                    )
                )

            fig_q_comb.update_layout(
                template="plotly_white",
                barmode='group',
                hovermode="x unified",
                yaxis_tickformat=',.0f',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )

            st.plotly_chart(
                fig_q_comb,
                use_container_width=True
            )

            # =====================================================
            # MONTHLY YOY
            # =====================================================
            st.subheader("📅 Analisis Tren YoY per Bulan")

            df_m_yoy = df_filtered.groupby(
                ['Bulan', 'Tahun']
            )[
                ['Actual Revenue (Total)', 'Actual EBITDA']
            ].sum().reset_index()

            df_m_yoy['Bulan'] = pd.Categorical(
                df_m_yoy['Bulan'],
                categories=month_order,
                ordered=True
            )

            df_m_yoy = df_m_yoy.sort_values(
                ['Bulan', 'Tahun']
            )

            fig_m_comb = go.Figure()

            for idx, yr in enumerate(available_years):

                yr_data = df_m_yoy[
                    df_m_yoy['Tahun'] == yr
                ]

                fig_m_comb.add_trace(
                    go.Bar(
                        x=yr_data['Bulan'],
                        y=yr_data['Actual Revenue (Total)'],
                        name=f"Revenue {yr}",
                        marker_color=revenue_colors[idx % len(revenue_colors)],
                        offsetgroup=yr
                    )
                )

            for idx, yr in enumerate(available_years):

                yr_data = df_m_yoy[
                    df_m_yoy['Tahun'] == yr
                ]

                fig_m_comb.add_trace(
                    go.Scatter(
                        x=yr_data['Bulan'],
                        y=yr_data['Actual EBITDA'],
                        name=f"EBITDA {yr}",
                        mode='lines+markers',
                        line=dict(
                            color=ebit_colors[idx % len(ebit_colors)],
                            width=3
                        )
                    )
                )

            fig_m_comb.update_layout(
                template="plotly_white",
                barmode='group',
                hovermode="x unified",
                yaxis_tickformat=',.0f'
            )

            st.plotly_chart(
                fig_m_comb,
                use_container_width=True
            )

            # =====================================================
            # TREN RS
            # =====================================================
            st.subheader("🏥 Tren Pendapatan per RS")

            df_rs_actual = df_latest.pivot_table(
                index='Bulan',
                columns='Cabang',
                values='Actual Revenue (Total)',
                aggfunc='sum'
            ).reindex(month_order)

            df_rs_target = df_latest.pivot_table(
                index='Bulan',
                columns='Cabang',
                values='Target Revenue (Total)',
                aggfunc='sum'
            ).reindex(month_order)

            fig_line = go.Figure()

            for rs in df_rs_actual.columns:

                color = COLOR_MAP.get(
                    rs,
                    DEFAULT_COLORS[0]
                )

                fig_line.add_trace(
                    go.Scatter(
                        x=df_rs_actual.index,
                        y=df_rs_actual[rs],
                        name=f"Actual {rs}",
                        mode='lines+markers',
                        line=dict(color=color)
                    )
                )

                fig_line.add_trace(
                    go.Scatter(
                        x=df_rs_target.index,
                        y=df_rs_target[rs],
                        name=f"Target {rs}",
                        mode='lines',
                        line=dict(
                            color=color,
                            dash='dash',
                            width=1.5
                        ),
                        opacity=0.5
                    )
                )

            fig_line.update_layout(
                template="plotly_white",
                hovermode="x unified",
                yaxis_tickformat=',.0f'
            )

            st.plotly_chart(
                fig_line,
                use_container_width=True
            )

            # =====================================================
            # PIE + EBITDA BAR
            # =====================================================
            col_a, col_b = st.columns(2)

            with col_a:

                st.subheader("📊 Komposisi Pendapatan per RS")

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

                st.plotly_chart(
                    fig_pie,
                    use_container_width=True
                )

            with col_b:

                st.subheader("🎯 EBITDA per RS")

                df_ebitda_rs = df_latest.groupby(
                    'Cabang'
                )[
                    'Actual EBITDA'
                ].sum().reset_index()

                fig_ebitda = px.bar(
                    df_ebitda_rs,
                    x='Cabang',
                    y='Actual EBITDA',
                    color='Cabang',
                    color_discrete_map=COLOR_MAP
                )

                fig_ebitda.update_layout(
                    template="plotly_white",
                    yaxis_tickformat=',.0f',
                    showlegend=False
                )

                st.plotly_chart(
                    fig_ebitda,
                    use_container_width=True
                )

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
                /
                ranking_df['Target Revenue (Total)']
                * 100
            ).round(1)

            ranking_df['EBITDA Margin %'] = (
                ranking_df['Actual EBITDA']
                /
                ranking_df['Actual Revenue (Total)']
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
            excel_file = create_excel(ranking_df)

            st.download_button(
                label="📥 Download Ranking Excel",
                data=excel_file,
                file_name="ranking_performance_helsa.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # =====================================================
            # DETAIL TABLE
            # =====================================================
            st.markdown("---")

            with st.expander("🔍 Lihat Detail Tabel Data"):

                df_display = df_filtered[
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
                    df_display,
                    use_container_width=True
                )

    else:

        st.error("❌ Data tidak ditemukan.")

except Exception as e:

    st.error(f"❌ Sistem Error: {e}")
