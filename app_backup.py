import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import os
from io import BytesIO

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Dashboard Performance Helsa", layout="wide", page_icon="📈")

# --- KONFIGURASI KREDENSIAL LOGIN ---
USER_CREDENTIALS = {
    "admin": "helsa2026",
    "management": "helsa2026"
}

# --- INISIALISASI SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# =====================================================================
# --- 1. PROSES PENGECEKAN HALAMAN LOGIN ---
# =====================================================================
if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("")
        st.write("")
        LOGO_FILE = "HELSA Rumah sakit.png"
        if os.path.exists(LOGO_FILE):
            st.image(LOGO_FILE, use_container_width=False, width=250)
        
        st.subheader("🔐 Silakan Login Terlebih Dahulu")
        
        username = st.text_input("Username", placeholder="Masukkan username Anda")
        password = st.text_input("Password", type="password", placeholder="Masukkan password Anda")
        
        if st.button("Login", use_container_width=True):
            if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
                st.session_state["logged_in"] = True
                st.success("Login Berhasil! Membuka Dashboard...")
                st.rerun()
            else:
                st.error("❌ Username atau Password salah. Silakan coba lagi.")
    st.stop()

# =====================================================================
# --- 2. JIKA SUDAH LOGIN, TAMPILKAN SELURUH DASHBOARD DI BAWAH INI ---
# =====================================================================

if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state["logged_in"] = False
    st.rerun()

LOGO_FILE = "HELSA Rumah sakit.png"
if os.path.exists(LOGO_FILE):
    st.image(LOGO_FILE, use_container_width=False, width=250)

COLOR_MAP = {
    "Jatirahayu": "#636EFA", 
    "Cikampek": "#EF553B",   
    "Citeureup": "#00CC96",  
    "Ciputat": "#AB63FA",    
    "Bunda Nanda": "#FFA15A",
    "Rawalumbu": "#19D3F3"
}
DEFAULT_COLORS = px.colors.qualitative.Plotly

DAYS_IN_MONTH = {
    'Januari': 31, 'Februari': 28, 'Maret': 31,
    'April': 30, 'Mei': 31, 'Juni': 30,
    'Juli': 31, 'Agustus': 31, 'September': 30,
    'Oktober': 31, 'November': 30, 'Desember': 31
}

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

def get_quarter(bulan):
    q_map = {
        'Januari': 'Q1', 'Februari': 'Q1', 'Maret': 'Q1',
        'April': 'Q2', 'Mei': 'Q2', 'Juni': 'Q2',
        'Juli': 'Q3', 'Agustus': 'Q3', 'September': 'Q3',
        'Oktober': 'Q4', 'November': 'Q4', 'Desember': 'Q4'
    }
    return q_map.get(bulan, 'Unknown')

@st.cache_data
def load_combined_data():
    sheet_id = "1oqXKKPNnlMOSBhkWi9_7Isjo_NYtHE2ytfeO-bSNMxY"
    sheets = {"2026": "app_data", "2025": "app_data_2025"}
    combined_list = []
    
    numeric_cols = [
        'Target Revenue (Total)', 'Actual Revenue (Total)',
        'Target Revenue (Rajal Total)', 'Actual Revenue (Rajal Total)',
        'Target Revenue (Rajal JKN)', 'Actual Revenue (Rajal JKN)',
        'Target Revenue (Rajal Non JKN)', 'Actual Revenue (Rajal Non JKN)',
        'Target Revenue (Ranap Total)', 'Actual Revenue (Ranap Total)',
        'Target Revenue (Ranap JKN)', 'Actual Revenue (Ranap JKN)',
        'Target Revenue (Ranap Non JKN)', 'Actual Revenue (Ranap Non JKN)',
        'Target EBITDA', 'Actual EBITDA',
        'Aktual Kunjungan (Rajal JKN)', 'Aktual Kunjungan (Rajal Non JKN)',
        'Aktual Kunjungan (Ranap JKN)', 'Aktual Kunjungan (Ranap Non JKN)',
        'Target Kunjungan (Rajal JKN)', 'Target Kunjungan (Rajal Non JKN)',
        'Target Kunjungan (Ranap JKN)', 'Target Kunjungan (Ranap Non JKN)',
        'Trajectory Revenue', 'Trajectory EBITDA',
        'Bed', 'Jumlah Bed', 'Kapasitas Bed', 'Bed Terpasang', 'Jumlah TT'
    ]

    for year, s_name in sheets.items():
        try:
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={s_name}"
            df_tmp = pd.read_csv(url, dtype=str)
            df_tmp.columns = [str(col).strip() for col in df_tmp.columns]
            
            for col in df_tmp.columns:
                if any(k in col.lower() for k in ['trajectory', 'bed', ' tt', 'tempat tidur']) and col not in numeric_cols:
                    numeric_cols.append(col)

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

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Performance_Data')
    return output.getvalue()

try:
    df_all = load_combined_data()
    quarter_order = ['Q1', 'Q2', 'Q3', 'Q4']
    month_order = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                   'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']

    st.sidebar.header("⚙️ Filter Panel")
    if not df_all.empty:
        list_tahun = sorted(df_all['Tahun'].unique(), reverse=True)
        selected_tahun = st.sidebar.multiselect("Pilih Tahun Analisis", list_tahun, default=list_tahun)
        
        list_cabang = sorted(df_all['Cabang'].unique())
        selected_cabang = st.sidebar.multiselect("Pilih Cabang", list_cabang, default=list_cabang)
        
        available_months = [m for m in month_order if m in df_all['Bulan'].unique()]
        selected_bulan = st.sidebar.multiselect("Pilih Bulan", available_months, default=available_months)

        # 1. FILTER LAYANAN
        st.sidebar.markdown("---")
        st.sidebar.subheader("🏥 Dimensi Pelayanan")
        layanan_opsi = ["Total", "Rawat Jalan (Rajal)", "Rawat Inap (Ranap)"]
        selected_layanan = st.sidebar.radio("Pilih Tipe Pelayanan", layanan_opsi, index=0)

        # 2. FILTER SEGMEN PASIEN
        st.sidebar.subheader("💳 Segmen Pasien")
        segmen_opsi = ["Total Pasien", "JKN", "Non JKN"]
        selected_segmen = st.sidebar.selectbox("Pilih Segmen Penjamin", segmen_opsi, index=0)

        # --- MAPPING VARIABEL FILTER ---
        if selected_layanan == "Rawat Jalan (Rajal)":
            jkn_rev_source = "Actual Revenue (Rajal JKN)"
            non_jkn_rev_source = "Actual Revenue (Rajal Non JKN)"
            jkn_kunj_cols = ['Aktual Kunjungan (Rajal JKN)']
            non_jkn_kunj_cols = ['Aktual Kunjungan (Rajal Non JKN)']
            
            if selected_segmen == "JKN":
                target_rev_column = "Target Revenue (Rajal JKN)"
                actual_rev_column = "Actual Revenue (Rajal JKN)"
                kunjungan_columns = jkn_kunj_cols
                target_kunj_cols = ['Target Kunjungan (Rajal JKN)']
            elif selected_segmen == "Non JKN":
                target_rev_column = "Target Revenue (Rajal Non JKN)"
                actual_rev_column = "Actual Revenue (Rajal Non JKN)"
                kunjungan_columns = non_jkn_kunj_cols
                target_kunj_cols = ['Target Kunjungan (Rajal Non JKN)']
            else:
                target_rev_column = "Target Revenue (Rajal Total)"
                actual_rev_column = "Actual Revenue (Rajal Total)"
                kunjungan_columns = jkn_kunj_cols + non_jkn_kunj_cols
                target_kunj_cols = ['Target Kunjungan (Rajal JKN)', 'Target Kunjungan (Rajal Non JKN)']
        
        elif selected_layanan == "Rawat Inap (Ranap)":
            jkn_rev_source = "Actual Revenue (Ranap JKN)"
            non_jkn_rev_source = "Actual Revenue (Ranap Non JKN)"
            jkn_kunj_cols = ['Aktual Kunjungan (Ranap JKN)']
            non_jkn_kunj_cols = ['Aktual Kunjungan (Ranap Non JKN)']
            
            if selected_segmen == "JKN":
                target_rev_column = "Target Revenue (Ranap JKN)"
                actual_rev_column = "Actual Revenue (Ranap JKN)"
                kunjungan_columns = jkn_kunj_cols
                target_kunj_cols = ['Target Kunjungan (Ranap JKN)']
            elif selected_segmen == "Non JKN":
                target_rev_column = "Target Revenue (Ranap Non JKN)"
                actual_rev_column = "Actual Revenue (Ranap Non JKN)"
                kunjungan_columns = non_jkn_kunj_cols
                target_kunj_cols = ['Target Kunjungan (Ranap Non JKN)']
            else:
                target_rev_column = "Target Revenue (Ranap Total)"
                actual_rev_column = "Actual Revenue (Ranap Total)"
                kunjungan_columns = jkn_kunj_cols + non_jkn_kunj_cols
                target_kunj_cols = ['Target Kunjungan (Ranap JKN)', 'Target Kunjungan (Ranap Non JKN)']
        
        else: # TOTAL
            jkn_rev_source = ["Actual Revenue (Rajal JKN)", "Actual Revenue (Ranap JKN)"]
            non_jkn_rev_source = ["Actual Revenue (Rajal Non JKN)", "Actual Revenue (Ranap Non JKN)"]
            jkn_kunj_cols = ['Aktual Kunjungan (Rajal JKN)', 'Aktual Kunjungan (Ranap JKN)']
            non_jkn_kunj_cols = ['Aktual Kunjungan (Rajal Non JKN)', 'Aktual Kunjungan (Ranap Non JKN)']
            
            if selected_segmen == "JKN":
                target_rev_column = ["Target Revenue (Rajal JKN)", "Target Revenue (Ranap JKN)"]
                actual_rev_column = ["Actual Revenue (Rajal JKN)", "Actual Revenue (Ranap JKN)"]
                kunjungan_columns = jkn_kunj_cols
                target_kunj_cols = ['Target Kunjungan (Rajal JKN)', 'Target Kunjungan (Ranap JKN)']
            elif selected_segmen == "Non JKN":
                target_rev_column = ["Target Revenue (Rajal Non JKN)", "Target Revenue (Ranap Non JKN)"]
                actual_rev_column = ["Actual Revenue (Rajal Non JKN)", "Actual Revenue (Ranap Non JKN)"]
                kunjungan_columns = non_jkn_kunj_cols
                target_kunj_cols = ['Target Kunjungan (Rajal Non JKN)', 'Target Kunjungan (Ranap Non JKN)']
            else:
                target_rev_column = "Target Revenue (Total)"
                actual_rev_column = "Actual Revenue (Total)"
                kunjungan_columns = jkn_kunj_cols + non_jkn_kunj_cols
                target_kunj_cols = ['Target Kunjungan (Rajal JKN)', 'Target Kunjungan (Rajal Non JKN)', 'Target Kunjungan (Ranap JKN)', 'Target Kunjungan (Ranap Non JKN)']

        segmen_suffix = f" - {selected_segmen}" if selected_segmen != "Total Pasien" else ""
        layanan_suffix = f" ({selected_layanan})" if selected_layanan != "Total" else ""
        title_addon = f"{layanan_suffix}{segmen_suffix}"

        df_filtered = df_all[
            (df_all['Tahun'].isin(selected_tahun)) & 
            (df_all['Cabang'].isin(selected_cabang)) & 
            (df_all['Bulan'].isin(selected_bulan))
        ].copy()

        df_2026 = df_all[(df_all['Tahun'] == '2026') & (df_all['Cabang'].isin(selected_cabang)) & (df_all['Bulan'].isin(selected_bulan))].copy()

        # =====================================================================
        # --- PROSES UTAMA KALKULASI LOGIKA BARIS ---
        # =====================================================================
        def apply_row_logic(df_target):
            if df_target.empty:
                return df_target
            
            if isinstance(actual_rev_column, list):
                df_target['Calculated_Actual_Revenue'] = df_target[actual_rev_column].sum(axis=1)
            else:
                df_target['Calculated_Actual_Revenue'] = df_target[actual_rev_column]

            if isinstance(target_rev_column, list):
                df_target['Target_Rev_Sum_Row'] = df_target[target_rev_column].sum(axis=1)
            else:
                df_target['Target_Rev_Sum_Row'] = df_target[target_rev_column]

            traj_rev_cols = [c for c in df_target.columns if 'trajectory' in c.lower() and ('revenue' in c.lower() or 'rev' in c.lower())]
            if not traj_rev_cols:
                traj_rev_cols = [c for c in ['Trajectory', 'Trajectory Revenue', 'Target Trajectory', 'Trajectory (Total)'] if c in df_target.columns]
            df_target['Calculated_Trajectory_Revenue'] = df_target[traj_rev_cols].sum(axis=1) if traj_rev_cols else 0.0

            traj_ebit_cols = [c for c in df_target.columns if 'trajectory' in c.lower() and 'ebitda' in c.lower()]
            df_target['Calculated_Trajectory_EBITDA'] = df_target[traj_ebit_cols].sum(axis=1) if traj_ebit_cols else 0.0

            def sum_cols_safe(df_obj, cols):
                if isinstance(cols, list): return df_obj[cols].sum(axis=1)
                return df_obj[cols]
                
            df_target['Calculated_JKN_Revenue'] = sum_cols_safe(df_target, jkn_rev_source)
            df_target['Calculated_Non_JKN_Revenue'] = sum_cols_safe(df_target, non_jkn_rev_source)
            
            df_target['Total_Kunjungan_Row'] = df_target[kunjungan_columns].sum(axis=1)
            df_target['Total_Target_Kunjungan_Row'] = df_target[[c for c in target_kunj_cols if c in df_target.columns]].sum(axis=1)
            df_target['EBITDA Margin %'] = (df_target['Actual EBITDA'] / df_target['Calculated_Actual_Revenue'] * 100).fillna(0)
            
            # Kolom khusus breakdown Rajal & Ranap
            df_target['Aktual_Kunjungan_Rajal_Total'] = df_target[['Aktual Kunjungan (Rajal JKN)', 'Aktual Kunjungan (Rajal Non JKN)']].sum(axis=1)
            df_target['Target_Kunjungan_Rajal_Total'] = df_target[['Target Kunjungan (Rajal JKN)', 'Target Kunjungan (Rajal Non JKN)']].sum(axis=1)
            df_target['Aktual_Kunjungan_Ranap_Total'] = df_target[['Aktual Kunjungan (Ranap JKN)', 'Aktual Kunjungan (Ranap Non JKN)']].sum(axis=1)
            df_target['Target_Kunjungan_Ranap_Total'] = df_target[['Target Kunjungan (Ranap JKN)', 'Target Kunjungan (Ranap Non JKN)']].sum(axis=1)
            
            # Kolom deteksi kapasitas Bed
            bed_col_candidates = [c for c in df_target.columns if any(k in c.lower() for k in ['bed', 'tt', 'tempat tidur'])]
            df_target['Kapasitas_Bed_Row'] = df_target[bed_col_candidates].max(axis=1) if bed_col_candidates else 0.0

            # Pendapatan Ranap Total (Murni dari Actual Revenue (Ranap Total))
            df_target['Actual_Revenue_Ranap_Total_Row'] = df_target['Actual Revenue (Ranap Total)']

            def process_single_row(row):
                if row['Total_Kunjungan_Row'] == 0:
                    return 0.0
                arpp_act = row['Calculated_Actual_Revenue'] / row['Total_Kunjungan_Row']
                if row['Total_Target_Kunjungan_Row'] > 0:
                    arpp_tar = row['Target_Rev_Sum_Row'] / row['Total_Target_Kunjungan_Row']
                else:
                    arpp_tar = arpp_act
                    
                if arpp_act < arpp_tar:
                    return row['Total_Kunjungan_Row'] * arpp_tar
                else:
                    return row['Calculated_Actual_Revenue']

            df_target['Pendapatan_Potensial_Row'] = df_target.apply(process_single_row, axis=1)
            return df_target

        df_filtered = apply_row_logic(df_filtered)
        if not df_2026.empty:
            df_2026 = apply_row_logic(df_2026)

        st.title(f"🏥 Performance Dashboard Helsa Group{title_addon}")
        st.markdown("---")

        if not df_filtered.empty:
            # =====================================================================
            # --- ROW 1: KPI CARDS ---
            # =====================================================================
            if not df_2026.empty:
                rev_act_26 = df_2026['Calculated_Actual_Revenue'].sum()
                rev_tar_26 = df_2026['Target_Rev_Sum_Row'].sum()
                traj_rev_26 = df_2026['Calculated_Trajectory_Revenue'].sum()
                traj_ebit_26 = df_2026['Calculated_Trajectory_EBITDA'].sum()
                    
                ach_rev = (rev_act_26 / rev_tar_26 * 100) if rev_tar_26 > 0 else 0
                ach_traj_rev = (rev_act_26 / traj_rev_26 * 100) if traj_rev_26 > 0 else 0
                
                ebit_act_26 = df_2026['Actual EBITDA'].sum()
                ebit_tar_26 = df_2026['Target EBITDA'].sum()
                ach_ebit = (ebit_act_26 / ebit_tar_26 * 100) if ebit_tar_26 > 0 else 0
                ach_traj_ebit = (ebit_act_26 / traj_ebit_26 * 100) if traj_ebit_26 > 0 else 0
                ebitda_margin_26 = (ebit_act_26 / rev_act_26 * 100) if rev_act_26 > 0 else 0

                total_kunjungan_26 = df_2026['Total_Kunjungan_Row'].sum()
                rev_potensial_26 = df_2026['Pendapatan_Potensial_Row'].sum()
                loss_revenue = max(0.0, rev_potensial_26 - rev_act_26)
                
                arpp_aktual_26 = (rev_act_26 / total_kunjungan_26) if total_kunjungan_26 > 0 else 0

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.subheader("Revenue 2026")
                    st.write(f"### {format_rupiah_human(rev_act_26)}")
                    st.caption(f"Target: {format_rupiah_human(rev_tar_26)}")
                    st.write(f":green[{ach_rev:.1f}% vs Target]" if ach_rev >= 100 else f":orange[{ach_rev:.1f}% vs Target]")
                    if traj_rev_26 > 0:
                        st.caption(f"📈 IPO Traj: :blue[{ach_traj_rev:.1f}%] ({format_rupiah_human(traj_rev_26)})")
                with col2:
                    st.subheader("Total EBITDA & Margin")
                    st.write(f"### {format_rupiah_human(ebit_act_26)} ({ebitda_margin_26:.1f}%)")
                    st.caption(f"Target EBITDA: {format_rupiah_human(ebit_tar_26)}")
                    st.write(f":green[{ach_ebit:.1f}% vs Target]" if ach_ebit >= 100 else f":orange[{ach_ebit:.1f}% vs Target]")
                    if traj_ebit_26 > 0:
                        st.caption(f"📈 IPO Traj: :blue[{ach_traj_ebit:.1f}%] ({format_rupiah_human(traj_ebit_26)})")
                with col3:
                    st.subheader("ARPP Aktual 2026")
                    st.write(f"### Rp {arpp_aktual_26:,.0f}")
                    st.caption("Rata-rata pendapatan per satu kunjungan pasien")
                    st.write(f"Vol: {total_kunjungan_26:,.0f} Kunjungan Pasien")
                with col4:
                    st.subheader(
                        "Pendapatan Potensial", 
                        help="Estimasi total pendapatan yang seharusnya diperoleh dari volume kunjungan pasien saat ini jika nilai transaksi rata-rata (ARPP) minimal memenuhi Target ARPP. Jika ARPP Target sudah tercapai atau periode belum berjalan, maka menggunakan nilai Pendapatan Aktual."
                    )
                    st.write(f"### {format_rupiah_human(rev_potensial_26)}")
                    if loss_revenue > 0:
                        st.write(f":orange[⚠️ Potential Loss: {format_rupiah_human(loss_revenue)}]")
                    else:
                        st.write(":green[✅ Target ARPP Terpenuhi]")

                st.markdown("---")

            # =====================================================================
            # --- ROW: INPATIENT PERFORMANCE (ARPOB DENGAN FORMULA TERBARU) ---
            # =====================================================================
            if not df_2026.empty:
                st.subheader(
                    "🛏️ Inpatient Performance Metrics: ARPOB & ARPD 2026",
                    help="ARPOB = Actual Revenue (Ranap Total) / (BOR x Jumlah Bed x Periode).\nARPD = Actual Revenue (Ranap Total) / (Jumlah Bed x Periode)."
                )

                # 1. Hari Rawat (HP) Akumulasi
                hari_rawat_26 = df_2026['Aktual_Kunjungan_Ranap_Total'].sum()

                # 2. Pembilang: Actual Revenue (Ranap Total)
                rev_ranap_total_26 = df_2026['Actual_Revenue_Ranap_Total_Row'].sum()

                # 3. Jumlah Bed Periode Terakhir
                df_sorted_m = df_2026.copy()
                df_sorted_m['Bulan_Idx'] = df_sorted_m['Bulan'].apply(lambda x: month_order.index(x) if x in month_order else -1)
                latest_bed_per_rs = df_sorted_m.sort_values('Bulan_Idx').groupby('Cabang')['Kapasitas_Bed_Row'].last()
                total_bed_terakhir_26 = latest_bed_per_rs.sum()

                # 4. Periode (Jumlah Hari Kalender dari Bulan yang Dipilih)
                total_days_period = sum([DAYS_IN_MONTH.get(m, 30) for m in selected_bulan])

                # 5. BOR (Desimal)
                total_bed_days = total_bed_terakhir_26 * total_days_period
                bor_decimal = (hari_rawat_26 / total_bed_days) if total_bed_days > 0 else 0.0
                bor_pct = bor_decimal * 100

                # 6. Parameter ARPOB = Actual Revenue (Ranap Total) / (BOR * Jumlah Bed * periode)
                pembagi_arpob = bor_decimal * total_bed_terakhir_26 * total_days_period
                arpob_26 = (rev_ranap_total_26 / pembagi_arpob) if pembagi_arpob > 0 else 0.0

                # 7. Parameter ARPD = Actual Revenue (Ranap Total) / (Jumlah Bed * periode)
                arpd_26 = (rev_ranap_total_26 / total_bed_days) if total_bed_days > 0 else 0.0

                c_arp1, c_arp2, c_arp3, c_arp4 = st.columns(4)
                with c_arp1:
                    st.metric(
                        label="ARPOB (Per Occupied Bed)",
                        value=f"Rp {arpob_26:,.0f}",
                        help="Rumus: Actual Revenue (Ranap Total) / (BOR x Jumlah Bed x Periode)"
                    )
                    st.caption(f"Actual Revenue Ranap Total: {format_rupiah_human(rev_ranap_total_26)}")
                with c_arp2:
                    st.metric(
                        label="ARPD (Per Available Bed)",
                        value=f"Rp {arpd_26:,.0f}",
                        help="Rumus: Actual Revenue (Ranap Total) / (Jumlah Bed x Periode)"
                    )
                    st.caption(f"Hari Rawat (HP): {hari_rawat_26:,.0f} Hari")
                with c_arp3:
                    st.metric(
                        label="Bed Terpasang (Periode Terakhir)",
                        value=f"{total_bed_terakhir_26:,.0f} Tempat Tidur",
                        help="Kapasitas tempat tidur terpasang pada periode bulan terakhir yang dipilih."
                    )
                    st.caption(f"Durasi Periode: {total_days_period} Hari Kalender")
                with c_arp4:
                    st.metric(
                        label="Bed Occupancy Rate (BOR)",
                        value=f"{bor_pct:.1f}%",
                        help="Tingkat pemanfaatan tempat tidur rawat inap (Hari Rawat / Kapasitas Bed-Days x 100%)."
                    )
                    st.caption(f"BOR Desimal: {bor_decimal:.4f}")

                # Grafik ARPOB & ARPD per Cabang Rumah Sakit
                df_arp_rs_list = []
                for rs_name in df_2026['Cabang'].unique():
                    df_sub_rs = df_2026[df_2026['Cabang'] == rs_name]
                    rs_rev_ranap = df_sub_rs['Actual_Revenue_Ranap_Total_Row'].sum()
                    rs_hp = df_sub_rs['Aktual_Kunjungan_Ranap_Total'].sum()
                    
                    rs_bed_latest = latest_bed_per_rs.get(rs_name, 0.0)
                    rs_bed_days = rs_bed_latest * total_days_period
                    rs_bor_dec = (rs_hp / rs_bed_days) if rs_bed_days > 0 else 0.0
                    
                    # Rumus ARPOB per RS: Actual Revenue (Ranap Total) / (BOR * Jumlah Bed * periode)
                    rs_pembagi_arpob = rs_bor_dec * rs_bed_latest * total_days_period
                    rs_arpob = (rs_rev_ranap / rs_pembagi_arpob) if rs_pembagi_arpob > 0 else 0.0
                    rs_arpd = (rs_rev_ranap / rs_bed_days) if rs_bed_days > 0 else 0.0
                    
                    df_arp_rs_list.append({
                        'Cabang': rs_name,
                        'Actual Revenue (Ranap Total)': rs_rev_ranap,
                        'Hari Rawat': rs_hp,
                        'Bed Terakhir': rs_bed_latest,
                        'BOR (%)': rs_bor_dec * 100,
                        'ARPOB': rs_arpob,
                        'ARPD': rs_arpd
                    })

                df_arp_rs = pd.DataFrame(df_arp_rs_list)
                if not df_arp_rs.empty:
                    fig_arp_rs = go.Figure()
                    fig_arp_rs.add_trace(go.Bar(
                        x=df_arp_rs['Cabang'], y=df_arp_rs['ARPOB'],
                        name="ARPOB (Rp / Occupied Bed)", marker_color="#00CC96"
                    ))
                    fig_arp_rs.add_trace(go.Bar(
                        x=df_arp_rs['Cabang'], y=df_arp_rs['ARPD'],
                        name="ARPD (Rp / Available Bed)", marker_color="#FFA15A"
                    ))
                    fig_arp_rs.update_layout(
                        barmode='group', template='plotly_white', yaxis_tickformat=',.0f',
                        hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    fig_arp_rs.update_traces(hovertemplate='<b>RS:</b> %{x}<br><b>%{trace.name}:</b> Rp %{y:,.0f}')
                    st.plotly_chart(fig_arp_rs, use_container_width=True)

                st.markdown("---")

            # =====================================================================
            # --- SEKSI: ACTUAL VS TRAJECTORY IPO (REVENUE & EBITDA) ---
            # =====================================================================
            if not df_2026.empty and (df_2026['Calculated_Trajectory_Revenue'].sum() > 0 or df_2026['Calculated_Trajectory_EBITDA'].sum() > 0):
                st.subheader(
                    "🚀 Strategic IPO Readiness: Actual vs Trajectory 2026", 
                    help="Trajectory adalah target finansial strategis (Revenue & EBITDA) yang dirancang untuk kesiapan menuju IPO guna mendongkrak valuasi korporasi."
                )
                
                col_traj1, col_traj2 = st.columns(2)
                
                # --- GRAFIK 1: TREN BULANAN ---
                with col_traj1:
                    st.markdown("<h5 style='text-align: center; color:#2c3e50;'>Tren Bulanan: Actual vs Trajectory IPO</h5>", unsafe_allow_html=True)
                    df_m_traj = df_2026.groupby('Bulan')[['Calculated_Actual_Revenue', 'Calculated_Trajectory_Revenue', 'Actual EBITDA', 'Calculated_Trajectory_EBITDA']].sum().reindex(month_order).dropna(how='all').reset_index()
                    
                    fig_traj_m = go.Figure()
                    fig_traj_m.add_trace(go.Bar(
                        x=df_m_traj['Bulan'], y=df_m_traj['Calculated_Actual_Revenue'],
                        name="Actual Revenue", marker_color="#2E86C1", offsetgroup="Rev"
                    ))
                    fig_traj_m.add_trace(go.Scatter(
                        x=df_m_traj['Bulan'], y=df_m_traj['Calculated_Trajectory_Revenue'],
                        name="Trajectory Revenue", mode='lines+markers',
                        line=dict(color="#E74C3C", width=3, dash='dash')
                    ))
                    fig_traj_m.add_trace(go.Bar(
                        x=df_m_traj['Bulan'], y=df_m_traj['Actual EBITDA'],
                        name="Actual EBITDA", marker_color="#F39C12", offsetgroup="Ebit"
                    ))
                    fig_traj_m.add_trace(go.Scatter(
                        x=df_m_traj['Bulan'], y=df_m_traj['Calculated_Trajectory_EBITDA'],
                        name="Trajectory EBITDA", mode='lines+markers',
                        line=dict(color="#8E44AD", width=3, dash='dot')
                    ))

                    fig_traj_m.update_layout(
                        yaxis_tickformat=',.0f', template="plotly_white", barmode='group',
                        hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    fig_traj_m.update_traces(hovertemplate='<b>Bulan:</b> %{x}<br><b>%{trace.name}:</b> Rp %{y:,.0f}')
                    st.plotly_chart(fig_traj_m, use_container_width=True)

                # --- GRAFIK 2: KESIAPAN IPO PER CABANG RS ---
                with col_traj2:
                    st.markdown("<h5 style='text-align: center; color:#2c3e50;'>Kesiapan IPO per Cabang RS (Actual vs Trajectory)</h5>", unsafe_allow_html=True)
                    df_rs_traj = df_2026.groupby('Cabang')[['Calculated_Actual_Revenue', 'Calculated_Trajectory_Revenue', 'Actual EBITDA', 'Calculated_Trajectory_EBITDA']].sum().reset_index()
                    
                    fig_traj_rs = go.Figure()
                    fig_traj_rs.add_trace(go.Bar(
                        x=df_rs_traj['Cabang'], y=df_rs_traj['Calculated_Actual_Revenue'],
                        name="Actual Revenue", marker_color="#2E86C1", offsetgroup="Rev"
                    ))
                    fig_traj_rs.add_trace(go.Scatter(
                        x=df_rs_traj['Cabang'], y=df_rs_traj['Calculated_Trajectory_Revenue'],
                        name="Trajectory Revenue", mode='lines+markers',
                        line=dict(color="#E74C3C", width=3, dash='dash')
                    ))
                    fig_traj_rs.add_trace(go.Bar(
                        x=df_rs_traj['Cabang'], y=df_rs_traj['Actual EBITDA'],
                        name="Actual EBITDA", marker_color="#F39C12", offsetgroup="Ebit"
                    ))
                    fig_traj_rs.add_trace(go.Scatter(
                        x=df_rs_traj['Cabang'], y=df_rs_traj['Calculated_Trajectory_EBITDA'],
                        name="Trajectory EBITDA", mode='lines+markers',
                        line=dict(color="#8E44AD", width=3, dash='dot')
                    ))

                    fig_traj_rs.update_layout(
                        yaxis_tickformat=',.0f', template="plotly_white", barmode='group',
                        hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    fig_traj_rs.update_traces(hovertemplate='<b>RS:</b> %{x}<br><b>%{trace.name}:</b> Rp %{y:,.0f}')
                    st.plotly_chart(fig_traj_rs, use_container_width=True)

                st.markdown("---")

            # --- ROW 2: TREN YOY GRAPH ---
            st.subheader("📊 Analisis Tren & Growth YoY per Kuartal")
            df_q_yoy = df_filtered.groupby(['Kuartal', 'Tahun'])[['Calculated_Actual_Revenue', 'Actual EBITDA']].sum().reset_index()
            df_q_yoy['Kuartal'] = pd.Categorical(df_q_yoy['Kuartal'], categories=quarter_order, ordered=True)
            df_q_yoy = df_q_yoy.sort_values(['Kuartal', 'Tahun'])
            
            fig_q_comb = go.Figure()
            for yr, color in zip(["2025", "2026"], ["#AED6F1", "#2E86C1"]):
                if yr in selected_tahun:
                    yr_data = df_q_yoy[df_q_yoy['Tahun'] == yr]
                    fig_q_comb.add_trace(go.Bar(x=yr_data['Kuartal'], y=yr_data['Calculated_Actual_Revenue'], name=f"Rev {yr}", marker_color=color, offsetgroup=yr))
            
            for yr, color, dash in zip(["2025", "2026"], ["#FAD7A0", "#D35400"], ["dash", "solid"]):
                if yr in selected_tahun:
                    yr_data = df_q_yoy[df_q_yoy['Tahun'] == yr]
                    fig_q_comb.add_trace(go.Scatter(x=yr_data['Kuartal'], y=yr_data['Actual EBITDA'], name=f"EBITDA {yr}", mode='lines+markers', line=dict(color=color, width=3, dash=dash)))

            if "2025" in selected_tahun and "2026" in selected_tahun:
                for q in df_q_yoy['Kuartal'].unique():
                    rows = df_q_yoy[df_q_yoy['Kuartal'] == q]
                    v26_r = rows[rows['Tahun'] == '2026']['Calculated_Actual_Revenue'].sum()
                    v25_r = rows[rows['Tahun'] == '2025']['Calculated_Actual_Revenue'].sum()
                    if v26_r != 0 and v25_r != 0:
                        pct_r = ((v26_r - v25_r) / v25_r * 100)
                        fig_q_comb.add_annotation(x=q, y=v26_r, text=f"Growth Rev: {'▲' if pct_r >= 0 else '▼'} {abs(pct_r):.1f}%", showarrow=False, yshift=15, font=dict(color="#1E8449" if pct_r>=0 else "#C0392B", size=10, family="Arial Bold"))
                    
                    v26_e = rows[rows['Tahun'] == '2026']['Actual EBITDA'].sum()
                    v25_e = rows[rows['Tahun'] == '2025']['Actual EBITDA'].sum()
                    if v26_e != 0 and v25_e != 0:
                        pct_e = ((v26_e - v25_e) / abs(v25_e) * 100)
                        fig_q_comb.add_annotation(x=q, y=v26_e, text=f"Growth EBITDA: {'▲' if pct_e >= 0 else '▼'} {abs(pct_e):.1f}%", showarrow=False, yshift=-20, font=dict(color="#D35400", size=9, family="Arial"))

            fig_q_comb.update_layout(yaxis_tickformat=',.0f', template="plotly_white", barmode='group', hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_q_comb, use_container_width=True)

            # Grafik Bulanan Finansial
            st.subheader("📅 Analisis Tren & Growth YoY per Bulan")
            df_m_yoy = df_filtered.groupby(['Bulan', 'Tahun'])[['Calculated_Actual_Revenue', 'Actual EBITDA']].sum().reset_index()
            df_m_yoy['Bulan'] = pd.Categorical(df_m_yoy['Bulan'], categories=month_order, ordered=True)
            df_m_yoy = df_m_yoy.sort_values(['Bulan', 'Tahun'])
            
            fig_m_comb = go.Figure()
            for yr, color in zip(["2025", "2026"], ["#AED6F1", "#2E86C1"]):
                if yr in selected_tahun:
                    yr_data = df_m_yoy[df_m_yoy['Tahun'] == yr]
                    fig_m_comb.add_trace(go.Bar(x=yr_data['Bulan'], y=yr_data['Calculated_Actual_Revenue'], name=f"Rev {yr}", marker_color=color, offsetgroup=yr))
            
            for yr, color, dash in zip(["2025", "2026"], ["#FAD7A0", "#D35400"], ["dash", "solid"]):
                if yr in selected_tahun:
                    yr_data = df_m_yoy[df_m_yoy['Tahun'] == yr]
                    fig_m_comb.add_trace(go.Scatter(x=yr_data['Bulan'], y=yr_data['Actual EBITDA'], name=f"EBITDA {yr}", mode='lines+markers', line=dict(color=color, width=3, dash=dash)))

            if "2025" in selected_tahun and "2026" in selected_tahun:
                for b in selected_bulan:
                    rows = df_m_yoy[df_m_yoy['Bulan'] == b]
                    v26_r = rows[rows['Tahun'] == '2026']['Calculated_Actual_Revenue'].sum()
                    v25_r = rows[rows['Tahun'] == '2025']['Calculated_Actual_Revenue'].sum()
                    if v26_r != 0 and v25_r != 0:
                        pct_r = ((v26_r - v25_r) / v25_r * 100)
                        fig_m_comb.add_annotation(x=b, y=v26_r, text=f"{'▲' if pct_r >= 0 else '▼'} {abs(pct_r):.0f}%", showarrow=False, yshift=10, font=dict(color="#1E8449" if pct_r>=0 else "#C0392B", size=9, family="Arial Bold"))
                    
                    v26_e = rows[rows['Tahun'] == '2026']['Actual EBITDA'].sum()
                    v25_e = rows[rows['Tahun'] == '2025']['Actual EBITDA'].sum()
                    if v26_e != 0 and v25_e != 0:
                        pct_e = ((v26_e - v25_e) / abs(v25_e) * 100)
                        fig_m_comb.add_annotation(x=b, y=v26_e, text=f"{'▲' if pct_e >= 0 else '▼'} {abs(pct_e):.0f}%", showarrow=False, yshift=-15, font=dict(color="#D35400", size=8, family="Arial"))

            fig_m_comb.update_layout(yaxis_tickformat=',.0f', template="plotly_white", barmode='group', hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_m_comb, use_container_width=True)

            # =====================================================================
            # --- SEKSI: PENCAPAIAN KUNJUNGAN PASIEN PER RS (BREAKDOWN RAJAL & RANAP) ---
            # =====================================================================
            st.markdown("---")
            st.subheader("👥 Pencapaian Kunjungan Pasien per RS (Khusus Tahun 2026)")
            if not df_2026.empty:
                col_rajal, col_ranap = st.columns(2)
                
                with col_rajal:
                    st.markdown("<h5 style='text-align: center; color:#2c3e50;'>Pencapaian Kunjungan Rawat Jalan (Rajal)</h5>", unsafe_allow_html=True)
                    df_rajal_kunj = df_2026.groupby('Cabang')[['Aktual_Kunjungan_Rajal_Total', 'Target_Kunjungan_Rajal_Total']].sum().reset_index()
                    
                    fig_rajal = go.Figure()
                    fig_rajal.add_trace(go.Bar(
                        x=df_rajal_kunj['Cabang'], y=df_rajal_kunj['Aktual_Kunjungan_Rajal_Total'],
                        name="Aktual Rajal 2026", marker_color="#3498DB"
                    ))
                    fig_rajal.add_trace(go.Bar(
                        x=df_rajal_kunj['Cabang'], y=df_rajal_kunj['Target_Kunjungan_Rajal_Total'],
                        name="Target Rajal 2026", marker_color="#BDC3C7"
                    ))

                    for idx, row in df_rajal_kunj.iterrows():
                        act_k = row['Aktual_Kunjungan_Rajal_Total']
                        tar_k = row['Target_Kunjungan_Rajal_Total']
                        if act_k > 0 and tar_k > 0:
                            ach_k = (act_k / tar_k) * 100
                            fig_rajal.add_annotation(
                                x=row['Cabang'], y=max(act_k, tar_k),
                                text=f"Ach: {ach_k:.1f}%", showarrow=False, yshift=12,
                                font=dict(color="#2980B9", size=10, family="Arial Bold")
                            )

                    fig_rajal.update_layout(
                        barmode='group', template='plotly_white', yaxis_tickformat=',.0f',
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    fig_rajal.update_traces(hovertemplate='<b>RS:</b> %{x}<br><b>%{trace.name}:</b> %{y:,.0f} Pasien')
                    st.plotly_chart(fig_rajal, use_container_width=True)

                with col_ranap:
                    st.markdown("<h5 style='text-align: center; color:#2c3e50;'>Pencapaian Kunjungan Rawat Inap (Ranap)</h5>", unsafe_allow_html=True)
                    df_ranap_kunj = df_2026.groupby('Cabang')[['Aktual_Kunjungan_Ranap_Total', 'Target_Kunjungan_Ranap_Total']].sum().reset_index()
