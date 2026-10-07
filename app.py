import streamlit as st
import pandas as pd
import plotly.express as px

# Konfigurasi Halaman
st.set_page_config(page_title="Dashboard Monitoring FA Detail", layout="wide", page_icon="📊")

st.title("📊 Monitoring Ketersediaan Dana & Realisasi Anggaran")
st.caption("Upload Laporan FA Detail (16 Segmen) dari SAKTI untuk monitoring pagu, realisasi, dan evaluasi deviasi waktu.")

def get_jenis_belanja(akun):
    prefix = str(akun)[:2]
    if prefix == '51':
        return '51 - Belanja Pegawai'
    elif prefix == '52':
        return '52 - Belanja Barang'
    elif prefix == '53':
        return '53 - Belanja Modal'
    return f"{prefix} - Belanja Lainnya" if prefix else "-"

# 1. LOGIKA PARSER OTOMATIS
@st.cache_data
def parse_fa_detail(file):
    df_raw = pd.read_excel(file, header=None)
    
    # Deteksi periode otomatis dari header
    detected_month = 10  # default Oktober
    for i in range(5):
        txt = str(df_raw.iloc[i, 0]).lower()
        if "periode" in txt:
            bulan_map = {
                'januari': 1, 'februari': 2, 'maret': 3, 'april': 4,
                'mei': 5, 'juni': 6, 'juli': 7, 'agustus': 8,
                'september': 9, 'oktober': 10, 'november': 11, 'desember': 12
            }
            for b_name, b_val in bulan_map.items():
                if b_name in txt:
                    detected_month = b_val
                    break

    current_program = ""
    current_kegiatan = ""
    current_kro = ""
    current_ro = ""
    current_komponen = ""
    current_subkomponen = ""
    current_akun = ""
    current_nama_akun = ""
    
    records = []
    
    for _, row in df_raw.iterrows():
        c1 = str(row[1]).strip() if pd.notnull(row[1]) else ""
        c2 = str(row[2]).strip() if pd.notnull(row[2]) else ""
        c4 = str(row[4]).strip() if pd.notnull(row[4]) else ""
        c5 = str(row[5]).strip() if pd.notnull(row[5]) else ""
        c7 = str(row[7]).strip() if pd.notnull(row[7]) else ""
        c13 = str(row[13]).strip() if pd.notnull(row[13]) else ""
        
        pagu = row[16] if pd.notnull(row[16]) else 0
        lock_pagu = row[18] if pd.notnull(row[18]) else 0
        realisasi_total = row[25] if pd.notnull(row[25]) else (row[24] if pd.notnull(row[24]) else 0)
        sisa = row[30] if pd.notnull(row[30]) else (row[29] if pd.notnull(row[29]) else 0)

        # Hirarki SAKTI
        if c1 and '.' not in c1 and len(c1) <= 3 and pd.notnull(row[3]):
            current_program = f"{c1} - {row[3]}"
        elif c1 and '.' in c1 and pd.notnull(row[8]):
            current_kegiatan = f"{c1} - {row[8]}"
        elif c2 and '.' not in c2 and len(c2) <= 4 and pd.notnull(row[6]):
            current_kro = f"{c2} - {row[6]}"
        elif c2 and '.' in c2 and pd.notnull(row[10]):
            current_ro = f"{c2} - {row[10]}"
        elif c4 and pd.notnull(row[9]):
            komp = str(int(float(c4))) if c4.replace('.0','').isdigit() else c4
            current_komponen = f"{komp} - {row[9]}"
        elif c5 and pd.notnull(row[11]):
            current_subkomponen = f"{c5} - {row[11]}"
        elif c7 and pd.notnull(row[12]):
            acc = str(int(float(c7))) if c7.replace('.0','').isdigit() else c7
            current_akun = acc
            current_nama_akun = str(row[12])
        elif c13:  # Baris Item Belanja
            try:
                p_val = float(pagu)
                r_val = float(realisasi_total)
                s_val = float(sisa)
                l_val = float(lock_pagu) if str(lock_pagu).replace('.','').isdigit() else 0
            except:
                continue
                
            pct_val = (r_val / p_val * 100) if p_val > 0 else 0.0

            records.append({
                'Program': current_program,
                'Kegiatan': current_kegiatan,
                'Jenis Belanja': get_jenis_belanja(current_akun),
                'KRO': current_kro,
                'RO': current_ro,
                'Komponen': current_komponen,
                'Sub Komponen': current_subkomponen,
                'Akun': current_akun,
                'Nama Akun': current_nama_akun,
                'Item': c13,
                'Pagu': p_val,
                'Lock Pagu': l_val,
                'Realisasi': r_val,
                'Persen Realisasi': round(pct_val, 2),
                'Sisa': s_val
            })
            
    df_clean = pd.DataFrame(records)
    return df_clean, detected_month

# 2. FITUR UPLOAD FILE
uploaded_file = st.sidebar.file_uploader("📂 Unggah File FA Detail (.xlsx)", type=["xlsx", "xls"])

if uploaded_file is not None:
    df, default_month = parse_fa_detail(uploaded_file)
    
    # 3. SIDEBAR PARAMETER WAKTU
    st.sidebar.header("⏱️ Parameter Waktu")
    bulan_list = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    selected_month_idx = st.sidebar.selectbox(
        "Posisi Bulan Pelaporan:", 
        range(1, 13), 
        index=default_month - 1,
        format_func=lambda x: f"Bulan ke-{x} ({bulan_list[x-1]})"
    )
    
    target_persen_waktu = round((selected_month_idx / 12) * 100, 2)
    custom_target = st.sidebar.number_input(
        "Target Realisasi Waktu (%) :", 
        min_value=0.0, max_value=100.0, 
        value=float(target_persen_waktu), step=1.0
    )

    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filter Anggaran")
    
    # Filter 0: Jenis Belanja (51 / 52 / 53)
    list_jenis = ["Semua"] + sorted([j for j in df['Jenis Belanja'].unique() if j and j != '-'])
    selected_jenis = st.sidebar.selectbox("Pilih Jenis Belanja:", list_jenis)
    df_step0 = df if selected_jenis == "Semua" else df[df['Jenis Belanja'] == selected_jenis]

    # Filter 1: KRO (Cascading)
    list_kro = ["Semua"] + sorted([k for k in df_step0['KRO'].unique() if k])
    selected_kro = st.sidebar.selectbox("Pilih KRO (Output):", list_kro)
    df_step1 = df_step0 if selected_kro == "Semua" else df_step0[df_step0['KRO'] == selected_kro]
    
    # Filter 2: RO (Cascading)
    list_ro = ["Semua"] + sorted([r for r in df_step1['RO'].unique() if r])
    selected_ro = st.sidebar.selectbox("Pilih RO (SubOutput):", list_ro)
    df_step2 = df_step1 if selected_ro == "Semua" else df_step1[df_step1['RO'] == selected_ro]
    
    # Filter 3: Komponen (Cascading)
    list_komponen = ["Semua"] + sorted([k for k in df_step2['Komponen'].unique() if k])
    selected_komponen = st.sidebar.selectbox("Pilih Komponen:", list_komponen)
    df_step3 = df_step2 if selected_komponen == "Semua" else df_step2[df_step2['Komponen'] == selected_komponen]
    
    # Filter 4: Sub Komponen (Cascading)
    list_subkomp = ["Semua"] + sorted([s for s in df_step3['Sub Komponen'].unique() if s])
    selected_subkomp = st.sidebar.selectbox("Pilih Sub Komponen:", list_subkomp)
    df_step4 = df_step3 if selected_subkomp == "Semua" else df_step3[df_step3['Sub Komponen'] == selected_subkomp]
    
    # Filter 5: Item Belanja (Multiselect)
    available_items = sorted(list(df_step4['Item'].unique()))
    selected_items = st.sidebar.multiselect(
        "Pilih Item Belanja:", 
        options=available_items, 
        placeholder="Semua Item (atau pilih beberapa)"
    )
    
    # Filter Tambahan: Pencarian Bebas
    search_keyword = st.sidebar.text_input("Cari Kata Kunci Bebas:")

    # Eksekusi Filter Akhir
    df_filtered = df_step4.copy()
    if selected_items:
        df_filtered = df_filtered[df_filtered['Item'].isin(selected_items)]
    if search_keyword:
        df_filtered = df_filtered[
            df_filtered['Item'].str.contains(search_keyword, case=False, na=False) |
            df_filtered['Nama Akun'].str.contains(search_keyword, case=False, na=False) |
            df_filtered['Sub Komponen'].str.contains(search_keyword, case=False, na=False) |
            df_filtered['RO'].str.contains(search_keyword, case=False, na=False)
        ]

    # Evaluasi Deviasi dengan Toleransi 5%
    df_filtered['Deviasi (%)'] = (df_filtered['Persen Realisasi'] - custom_target).round(2)
    df_filtered['Status Deviasi'] = df_filtered['Deviasi (%)'].apply(
        lambda x: "🟢 Sesuai/Melebihi Target" if x >= 0 else ("🟡 Sedikit Tertinggal (<5%)" if x >= -5 else "🔴 Kritis Tertinggal (≥5%)")
    )

    # 4. KARTU METRIK UTAMA (KPI)
    total_pagu = df_filtered['Pagu'].sum()
    total_real = df_filtered['Realisasi'].sum()
    total_lock = df_filtered['Lock Pagu'].sum()
    total_sisa = df_filtered['Sisa'].sum()
    persen_real = (total_real / total_pagu * 100) if total_pagu > 0 else 0
    deviasi_total = persen_real - custom_target
    underperforming_items = df_filtered[df_filtered['Deviasi (%)'] < 0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Total Pagu", f"Rp {total_pagu:,.0f}")
    col2.metric("⚡ Realisasi", f"Rp {total_real:,.0f}", f"{persen_real:.2f}% (Target: {custom_target}%)")
    col3.metric("📉 Deviasi Waktu", f"{deviasi_total:+.2f}%", delta_color="normal" if deviasi_total >= 0 else "inverse")
    col4.metric("🏷️ Sisa Anggaran", f"Rp {total_sisa:,.0f}", f"{len(underperforming_items)} item tertinggal")

    st.markdown("---")

    # 5. TAB VISUALISASI & TABEL DETAIL
    tab1, tab2, tab3 = st.tabs(["📋 Tabel Detail Data", "📈 Analisis Realisasi & Deviasi Waktu", "🏢 Komparasi Belanja & Hirarki"])

    with tab1:
        st.subheader("Data Rincian Anggaran Lengkap")
        
        only_lagging = st.checkbox("Tampilkan hanya item yang realisasinya di bawah target waktu", value=False)
        table_source = df_filtered[df_filtered['Deviasi (%)'] < 0] if only_lagging else df_filtered
        
        display_df = table_source[[
            'Jenis Belanja', 'KRO', 'RO', 'Komponen', 'Sub Komponen', 
            'Akun', 'Nama Akun', 'Item', 
            'Pagu', 'Realisasi', 'Persen Realisasi', 'Deviasi (%)', 'Sisa', 'Status Deviasi'
        ]].copy()
        
        for col in ['Pagu', 'Realisasi', 'Sisa']:
            display_df[col] = display_df[col].apply(lambda x: f"Rp {x:,.0f}")

        st.dataframe(
            display_df,
            column_config={
                "Persen Realisasi": st.column_config.ProgressColumn(
                    "Realisasi (%)",
                    help="Persentase Realisasi terhadap Pagu",
                    format="%.2f%%",
                    min_value=0,
                    max_value=100,
                ),
                "Deviasi (%)": st.column_config.NumberColumn(
                    "Deviasi (%)",
                    help=f"Selisih terhadap target waktu ({custom_target}%)",
                    format="%.2f%%"
                )
            },
            use_container_width=True,
            height=580
        )
        
        csv = table_source.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Unduh Data Tabel (CSV)", data=csv, file_name="FA_Detail_Monitoring.csv", mime="text/csv")

    with tab2:
        st.subheader("⚠️ Evaluasi Penyerapan Anggaran Terhadap Target Waktu")
        col_warn1, col_warn2 = st.columns([1, 2])
        with col_warn1:
            st.write(f"**Target Serapan Waktu:** `{custom_target}%` (s.d. Bulan {bulan_list[selected_month_idx-1]})")
            st.write(f"**Toleransi Deviasi:** `5%`")
            st.write(f"**Item di Bawah Target:** `{len(underperforming_items)}` dari `{len(df_filtered)}` item")
            st.write(f"**Sisa Anggaran Pos Tertinggal:** `Rp {underperforming_items['Sisa'].sum():,.0f}`")
            
            stat_counts = df_filtered['Status Deviasi'].value_counts().reset_index()
            stat_counts.columns = ['Status', 'Jumlah Item']
            fig_stat = px.pie(
                stat_counts, names='Status', values='Jumlah Item', 
                color='Status',
                color_discrete_map={
                    "🟢 Sesuai/Melebihi Target": "#2ecc71",
                    "🟡 Sedikit Tertinggal (<5%)": "#f1c40f",
                    "🔴 Kritis Tertinggal (≥5%)": "#e74c3c"
                },
                hole=0.45
            )
            st.plotly_chart(fig_stat, use_container_width=True)

        with col_warn2:
            lagging_top = underperforming_items.sort_values(by=['Deviasi (%)', 'Sisa'], ascending=[True, False]).head(10).copy()
            if not lagging_top.empty:
                lagging_top['Short_Item'] = lagging_top['Item'].str[:40]
                fig_lag = px.bar(
                    lagging_top, 
                    x='Deviasi (%)', 
                    y='Short_Item', 
                    orientation='h',
                    text='Persen Realisasi',
                    hover_data=['Jenis Belanja', 'Sub Komponen', 'Nama Akun', 'Pagu', 'Realisasi', 'Sisa'],
                    title="10 Pos Belanja Paling Tertinggal dari Target Waktu",
                    color='Deviasi (%)',
                    color_continuous_scale='Reds_r'
                )
                fig_lag.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig_lag.update_layout(yaxis={'categoryorder': 'total descending'})
                st.plotly_chart(fig_lag, use_container_width=True)
            else:
                st.success("🎉 Seluruh item yang dipilih telah memenuhi target realisasi waktu!")

    with tab3:
        # Ringkasan per Jenis Belanja (51, 52, 53)
        st.subheader("📊 Perbandingan per Jenis Belanja (51, 52, 53)")
        jb_summary = df.groupby('Jenis Belanja')[['Pagu', 'Realisasi', 'Sisa']].sum().reset_index()
        jb_summary['% Realisasi'] = (jb_summary['Realisasi'] / jb_summary['Pagu'] * 100).round(2)
        
        fig_jb = px.bar(
            jb_summary, x='Jenis Belanja', y=['Realisasi', 'Sisa'],
            barmode='group', title="Pagu Realisasi vs Sisa per Jenis Belanja",
            color_discrete_sequence=['#2ecc71', '#e74c3c']
        )
        st.plotly_chart(fig_jb, use_container_width=True)
        st.dataframe(jb_summary, use_container_width=True)

        st.markdown("---")
        st.subheader("Ringkasan Performa Realisasi per RO (Rincian Output)")
        ro_summary = df.groupby('RO')[['Pagu', 'Realisasi', 'Sisa']].sum().reset_index()
        ro_summary['% Realisasi'] = (ro_summary['Realisasi'] / ro_summary['Pagu'] * 100).round(2)
        
        fig_ro = px.bar(
            ro_summary, x='% Realisasi', y='RO', orientation='h',
            title="Persentase Realisasi per RO",
            color='% Realisasi', color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_ro, use_container_width=True)
else:
    st.info("👋 Silakan unggah file FA Detail Anda di menu sebelah kiri (sidebar) untuk mulai mengeksplorasi data.")