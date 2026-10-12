import streamlit as st
import pandas as pd
import plotly.express as px


# ============================================================
# 1. KONFIGURASI HALAMAN
# ============================================================

st.set_page_config(
    page_title="Dashboard Monitoring FA Detail SAKTI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# 2. CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }

        div[data-testid="stMetric"] {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            padding: 12px 18px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
        }

        h1, h2, h3 {
            font-family: 'Inter', sans-serif;
            color: #1f2937;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 3. JUDUL
# ============================================================

st.title("📊 Monitoring Ketersediaan Dana & Realisasi Anggaran")

st.caption(
    "Dashboard Interaktif Laporan FA Detail (16 Segmen) SAKTI — "
    "Evaluasi Pagu, Realisasi, Belanja 51/52/53, dan Deviasi Waktu."
)


# ============================================================
# 4. FUNGSI BANTU
# ============================================================

def get_jenis_belanja(akun):
    """
    Menentukan jenis belanja berdasarkan 2 digit awal kode akun.
    """
    akun = str(akun).strip()

    if not akun or akun == "-":
        return "-"

    prefix = akun[:2]

    if prefix == "51":
        return "51 - Belanja Pegawai"
    elif prefix == "52":
        return "52 - Belanja Barang"
    elif prefix == "53":
        return "53 - Belanja Modal"

    return f"{prefix} - Belanja Lainnya"


def normalize_account(value):
    """
    Menormalisasi kode akun agar konsisten.
    Contoh:
        511111.0 -> 511111
        511111   -> 511111
    """
    if pd.isna(value):
        return ""

    value = str(value).strip()

    if value.endswith(".0"):
        value = value[:-2]

    return value


def safe_float(value):
    """
    Konversi nilai ke float dengan aman.
    """
    if pd.isna(value):
        return 0.0

    try:
        if isinstance(value, str):
            value = value.replace(",", "").replace(" ", "")

        return float(value)

    except (ValueError, TypeError):
        return 0.0


def format_rupiah(value):
    """
    Format angka menjadi Rupiah.
    """
    return f"Rp {value:,.0f}"


# ============================================================
# 5. PARSER FA DETAIL
# ============================================================

@st.cache_data
def parse_fa_detail(file):

    df_raw = pd.read_excel(file, header=None)

    # --------------------------------------------------------
    # Deteksi bulan pelaporan
    # --------------------------------------------------------

    detected_month = 10

    bulan_map = {
        "januari": 1,
        "februari": 2,
        "maret": 3,
        "april": 4,
        "mei": 5,
        "juni": 6,
        "juli": 7,
        "agustus": 8,
        "september": 9,
        "oktober": 10,
        "november": 11,
        "desember": 12
    }

    for i in range(min(5, len(df_raw))):

        txt = str(df_raw.iloc[i, 0]).lower()

        if "periode" in txt:

            for bulan, nomor in bulan_map.items():

                if bulan in txt:
                    detected_month = nomor
                    break

    # --------------------------------------------------------
    # Variabel hirarki
    # --------------------------------------------------------

    current_program = ""
    current_kegiatan = ""
    current_kro = ""
    current_ro = ""
    current_komponen = ""
    current_subkomponen = ""
    current_akun = ""
    current_nama_akun = ""

    records = []

    # --------------------------------------------------------
    # Loop data Excel
    # --------------------------------------------------------

    for _, row in df_raw.iterrows():

        # Pastikan jumlah kolom mencukupi
        if len(row) < 31:
            continue

        c1 = str(row[1]).strip() if pd.notnull(row[1]) else ""
        c2 = str(row[2]).strip() if pd.notnull(row[2]) else ""
        c4 = str(row[4]).strip() if pd.notnull(row[4]) else ""
        c5 = str(row[5]).strip() if pd.notnull(row[5]) else ""
        c7 = str(row[7]).strip() if pd.notnull(row[7]) else ""
        c13 = str(row[13]).strip() if pd.notnull(row[13]) else ""

        pagu = row[16] if pd.notnull(row[16]) else 0
        lock_pagu = row[18] if pd.notnull(row[18]) else 0

        realisasi_total = (
            row[25]
            if pd.notnull(row[25])
            else (row[24] if pd.notnull(row[24]) else 0)
        )

        sisa = (
            row[30]
            if pd.notnull(row[30])
            else (row[29] if pd.notnull(row[29]) else 0)
        )

        # ----------------------------------------------------
        # Hirarki SAKTI
        # ----------------------------------------------------

        # Program
        if (
            c1
            and "." not in c1
            and len(c1) <= 3
            and pd.notnull(row[3])
        ):
            current_program = f"{c1} - {row[3]}"

        # Kegiatan
        elif (
            c1
            and "." in c1
            and pd.notnull(row[8])
        ):
            current_kegiatan = f"{c1} - {row[8]}"

        # KRO
        elif (
            c2
            and "." not in c2
            and len(c2) <= 4
            and pd.notnull(row[6])
        ):
            current_kro = f"{c2} - {row[6]}"

        # RO
        elif (
            c2
            and "." in c2
            and pd.notnull(row[10])
        ):
            current_ro = f"{c2} - {row[10]}"

        # Komponen
        elif (
            c4
            and pd.notnull(row[9])
        ):
            try:
                komp = str(int(float(c4)))
            except (ValueError, TypeError):
                komp = c4

            current_komponen = f"{komp} - {row[9]}"

        # Sub Komponen
        elif (
            c5
            and pd.notnull(row[11])
        ):
            current_subkomponen = f"{c5} - {row[11]}"

        # Akun
        elif (
            c7
            and pd.notnull(row[12])
        ):

            current_akun = normalize_account(c7)

            current_nama_akun = str(row[12]).strip()

        # Item Belanja
        elif c13:

            p_val = safe_float(pagu)
            r_val = safe_float(realisasi_total)
            s_val = safe_float(sisa)
            l_val = safe_float(lock_pagu)

            pct_val = (
                (r_val / p_val * 100)
                if p_val > 0
                else 0.0
            )

            records.append(
                {
                    "Program": current_program,
                    "Kegiatan": current_kegiatan,
                    "Jenis Belanja": get_jenis_belanja(
                        current_akun
                    ),
                    "KRO": current_kro,
                    "RO": current_ro,
                    "Komponen": current_komponen,
                    "Sub Komponen": current_subkomponen,
                    "Akun": current_akun,
                    "Nama Akun": current_nama_akun,
                    "Item": c13,
                    "Pagu": p_val,
                    "Lock Pagu": l_val,
                    "Realisasi": r_val,
                    "Persen Realisasi": round(
                        pct_val,
                        2
                    ),
                    "Sisa": s_val
                }
            )

    df_clean = pd.DataFrame(records)

    # --------------------------------------------------------
    # Pastikan kolom selalu tersedia
    # --------------------------------------------------------

    expected_columns = [
        "Program",
        "Kegiatan",
        "Jenis Belanja",
        "KRO",
        "RO",
        "Komponen",
        "Sub Komponen",
        "Akun",
        "Nama Akun",
        "Item",
        "Pagu",
        "Lock Pagu",
        "Realisasi",
        "Persen Realisasi",
        "Sisa"
    ]

    for col in expected_columns:

        if col not in df_clean.columns:

            if col in [
                "Pagu",
                "Lock Pagu",
                "Realisasi",
                "Persen Realisasi",
                "Sisa"
            ]:
                df_clean[col] = 0.0

            else:
                df_clean[col] = ""

    return df_clean, detected_month


# ============================================================
# 6. SIDEBAR - UPLOAD FILE
# ============================================================

uploaded_file = st.sidebar.file_uploader(
    "📂 Unggah File FA Detail (.xlsx)",
    type=["xlsx", "xls"]
)


# ============================================================
# 7. JIKA FILE SUDAH DIUPLOAD
# ============================================================

if uploaded_file is not None:

    df, default_month = parse_fa_detail(uploaded_file)

    # --------------------------------------------------------
    # Validasi data
    # --------------------------------------------------------

    if df.empty:

        st.error(
            "❌ Data FA Detail tidak berhasil dibaca "
            "dari file yang diunggah."
        )

        st.stop()

    # ========================================================
    # PARAMETER WAKTU
    # ========================================================

    st.sidebar.header("⏱️ Parameter Waktu")

    bulan_list = [
        "Januari",
        "Februari",
        "Maret",
        "April",
        "Mei",
        "Juni",
        "Juli",
        "Agustus",
        "September",
        "Oktober",
        "November",
        "Desember"
    ]

    selected_month_idx = st.sidebar.selectbox(
        "Posisi Bulan Pelaporan:",
        range(1, 13),
        index=max(
            0,
            min(
                default_month - 1,
                11
            )
        ),
        format_func=lambda x:
            f"Bulan ke-{x} ({bulan_list[x - 1]})"
    )

    target_persen_waktu = round(
        (selected_month_idx / 12) * 100,
        2
    )

    custom_target = st.sidebar.number_input(
        "Target Realisasi Waktu (%):",
        min_value=0.0,
        max_value=100.0,
        value=float(target_persen_waktu),
        step=1.0
    )

    # ========================================================
    # FILTER
    # ========================================================

    st.sidebar.markdown("---")

    st.sidebar.header(
        "🔍 Filter Data"
    )

    # --------------------------------------------------------
    # FILTER JENIS BELANJA
    # --------------------------------------------------------

    list_jenis = [
        "Semua"
    ] + sorted(
        [
            j
            for j in df["Jenis Belanja"].dropna().unique()
            if j and j != "-"
        ]
    )

    selected_jenis = st.sidebar.selectbox(
        "Jenis Belanja:",
        list_jenis
    )

    if selected_jenis == "Semua":

        df_step0 = df.copy()

    else:

        df_step0 = df[
            df["Jenis Belanja"] == selected_jenis
        ].copy()

    # --------------------------------------------------------
    # FILTER KODE AKUN
    # --------------------------------------------------------

    list_akun = sorted(
        [
            normalize_account(a)
            for a in df_step0["Akun"].dropna().unique()
            if normalize_account(a)
        ]
    )

    selected_akun = st.sidebar.multiselect(
        "Kode Akun:",
        options=list_akun,
        placeholder="Semua Akun (atau pilih beberapa)"
    )

    if selected_akun:

        df_step1 = df_step0[
            df_step0["Akun"]
            .astype(str)
            .isin(selected_akun)
        ].copy()

    else:

        df_step1 = df_step0.copy()

    # --------------------------------------------------------
    # FILTER KRO
    # --------------------------------------------------------

    list_kro = [
        "Semua"
    ] + sorted(
        [
            k
            for k in df_step1["KRO"].dropna().unique()
            if k
        ]
    )

    selected_kro = st.sidebar.selectbox(
        "KRO (Output):",
        list_kro
    )

    if selected_kro == "Semua":

        df_step2 = df_step1.copy()

    else:

        df_step2 = df_step1[
            df_step1["KRO"] == selected_kro
        ].copy()

    # --------------------------------------------------------
    # FILTER RO
    # --------------------------------------------------------

    list_ro = [
        "Semua"
    ] + sorted(
        [
            r
            for r in df_step2["RO"].dropna().unique()
            if r
        ]
    )

    selected_ro = st.sidebar.selectbox(
        "RO (SubOutput):",
        list_ro
    )

    if selected_ro == "Semua":

        df_step3 = df_step2.copy()

    else:

        df_step3 = df_step2[
            df_step2["RO"] == selected_ro
        ].copy()

    # --------------------------------------------------------
    # FILTER KOMPONEN
    # --------------------------------------------------------

    list_komponen = [
        "Semua"
    ] + sorted(
        [
            k
            for k in df_step3["Komponen"].dropna().unique()
            if k
        ]
    )

    selected_komponen = st.sidebar.selectbox(
        "Komponen:",
        list_komponen
    )

    if selected_komponen == "Semua":

        df_step4 = df_step3.copy()

    else:

        df_step4 = df_step3[
            df_step3["Komponen"] == selected_komponen
        ].copy()

    # --------------------------------------------------------
    # FILTER SUB KOMPONEN
    # --------------------------------------------------------

    list_subkomp = [
        "Semua"
    ] + sorted(
        [
            s
            for s in df_step4["Sub Komponen"].dropna().unique()
            if s
        ]
    )

    selected_subkomp = st.sidebar.selectbox(
        "Sub Komponen:",
        list_subkomp
    )

    if selected_subkomp == "Semua":

        df_step5 = df_step4.copy()

    else:

        df_step5 = df_step4[
            df_step4["Sub Komponen"] == selected_subkomp
        ].copy()

    # --------------------------------------------------------
    # FILTER ITEM
    # --------------------------------------------------------

    available_items = sorted(
        [
            i
            for i in df_step5["Item"].dropna().unique()
            if str(i).strip()
        ]
    )

    selected_items = st.sidebar.multiselect(
        "Item Belanja:",
        options=available_items,
        placeholder="Semua Item (atau pilih beberapa)"
    )

    # ========================================================
    # PENCARIAN BEBAS
    # ========================================================

    st.sidebar.markdown("---")

    search_keyword = st.sidebar.text_input(
        "🔎 Cari Kata Kunci:"
    )

    # ========================================================
    # FILTER AKHIR
    # ========================================================

    df_filtered = df_step5.copy()

    # Filter item
    if selected_items:

        df_filtered = df_filtered[
            df_filtered["Item"].isin(selected_items)
        ]

    # Pencarian bebas
    if search_keyword:

        keyword = search_keyword.strip()

        if keyword:

            search_columns = [
                "Program",
                "Kegiatan",
                "KRO",
                "RO",
                "Komponen",
                "Sub Komponen",
                "Akun",
                "Nama Akun",
                "Item",
                "Jenis Belanja"
            ]

            mask = pd.Series(
                False,
                index=df_filtered.index
            )

            for col in search_columns:

                mask |= (
                    df_filtered[col]
                    .astype(str)
                    .str.contains(
                        keyword,
                        case=False,
                        na=False,
                        regex=False
                    )
                )

            df_filtered = df_filtered[mask]

    # ========================================================
    # DEViasi
    # ========================================================

    df_filtered = df_filtered.copy()

    df_filtered["Deviasi (%)"] = (
        df_filtered["Persen Realisasi"]
        - custom_target
    ).round(2)

    df_filtered["Status Deviasi"] = (
        df_filtered["Deviasi (%)"]
        .apply(
            lambda x:
            "🟢 Sesuai/Melebihi Target"
            if x >= 0
            else (
                "🟡 Sedikit Tertinggal (<5%)"
                if x >= -5
                else "🔴 Kritis Tertinggal (≥5%)"
            )
        )
    )

    # ========================================================
    # 8. KPI
    # ========================================================

    total_pagu = df_filtered["Pagu"].sum()

    total_real = df_filtered["Realisasi"].sum()

    total_lock = df_filtered["Lock Pagu"].sum()

    total_sisa = df_filtered["Sisa"].sum()

    persen_real = (
        total_real / total_pagu * 100
        if total_pagu > 0
        else 0
    )

    deviasi_total = (
        persen_real - custom_target
    )

    underperforming_items = df_filtered[
        df_filtered["Deviasi (%)"] < 0
    ]

    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "💰 Total Pagu",
        format_rupiah(total_pagu)
    )

    col2.metric(
        "⚡ Realisasi",
        format_rupiah(total_real),
        f"{persen_real:.2f}% "
        f"(Target: {custom_target:.2f}%)"
    )

    col3.metric(
        "📉 Deviasi Waktu",
        f"{deviasi_total:+.2f}%",
        delta_color=(
            "normal"
            if deviasi_total >= 0
            else "inverse"
        )
    )

    col4.metric(
        "🏷️ Sisa Anggaran",
        format_rupiah(total_sisa),
        f"{len(underperforming_items)} item tertinggal"
    )

    # ========================================================
    # INFORMASI FILTER AKTIF
    # ========================================================

    st.markdown("---")

    active_filters = []

    if selected_jenis != "Semua":
        active_filters.append(
            f"Jenis: **{selected_jenis}**"
        )

    if selected_akun:
        active_filters.append(
            f"Akun: **{', '.join(selected_akun)}**"
        )

    if selected_kro != "Semua":
        active_filters.append(
            f"KRO: **{selected_kro}**"
        )

    if selected_ro != "Semua":
        active_filters.append(
            f"RO: **{selected_ro}**"
        )

    if selected_komponen != "Semua":
        active_filters.append(
            f"Komponen: **{selected_komponen}**"
        )

    if selected_subkomp != "Semua":
        active_filters.append(
            f"Sub Komponen: **{selected_subkomp}**"
        )

    if selected_items:
        active_filters.append(
            f"Item: **{len(selected_items)} pilihan**"
        )

    if search_keyword:
        active_filters.append(
            f"Pencarian: **{search_keyword}**"
        )

    if active_filters:

        st.info(
            "🔍 **Filter aktif:** "
            + " | ".join(active_filters)
        )

    else:

        st.caption(
            f"Menampilkan seluruh data — "
            f"{len(df_filtered):,} baris."
        )

    # ========================================================
    # 9. TABS
    # ========================================================

    tab1, tab2, tab3 = st.tabs(
        [
            "📋 Tabel Detail Data",
            "📈 Analisis Realisasi & Deviasi Waktu",
            "🏢 Komparasi Belanja & Hirarki"
        ]
    )

    # ========================================================
    # TAB 1 - DATA DETAIL
    # ========================================================

    with tab1:

        st.subheader(
            "Rincian Data Anggaran Lengkap"
        )

        only_lagging = st.checkbox(
            "Tampilkan hanya item yang "
            "realisasinya di bawah target waktu "
            "(Toleransi 5%)",
            value=False
        )

        if only_lagging:

            table_source = df_filtered[
                df_filtered["Deviasi (%)"] < 0
            ].copy()

        else:

            table_source = df_filtered.copy()

        display_columns = [
            "Jenis Belanja",
            "KRO",
            "RO",
            "Komponen",
            "Sub Komponen",
            "Akun",
            "Nama Akun",
            "Item",
            "Pagu",
            "Realisasi",
            "Persen Realisasi",
            "Deviasi (%)",
            "Sisa",
            "Status Deviasi"
        ]

        display_df = table_source[
            display_columns
        ].copy()

        for col in [
            "Pagu",
            "Realisasi",
            "Sisa"
        ]:

            display_df[col] = display_df[col].apply(
                format_rupiah
            )

        st.dataframe(
            display_df,
            column_config={
                "Persen Realisasi":
                    st.column_config.ProgressColumn(
                        "Realisasi (%)",
                        help=(
                            "Persentase Realisasi "
                            "terhadap Pagu"
                        ),
                        format="%.2f%%",
                        min_value=0,
                        max_value=100
                    ),

                "Deviasi (%)":
                    st.column_config.NumberColumn(
                        "Deviasi (%)",
                        help=(
                            f"Selisih terhadap target "
                            f"waktu ({custom_target:.2f}%)"
                        ),
                        format="%.2f%%"
                    )
            },
            use_container_width=True,
            height=550
        )

        # ----------------------------------------------------
        # Download CSV
        # ----------------------------------------------------

        csv = table_source.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "📥 Unduh Data Tabel (CSV)",
            data=csv,
            file_name="FA_Detail_Monitoring_Filtered.csv",
            mime="text/csv"
        )

    # ========================================================
    # TAB 2 - ANALISIS REALISASI
    # ========================================================

    with tab2:

        st.subheader(
            "⚠️ Evaluasi Penyerapan Anggaran "
            "Terhadap Target Waktu"
        )

        col_warn1, col_warn2 = st.columns(
            [1, 2]
        )

        with col_warn1:

            st.write(
                f"**Target Serapan Waktu:** "
                f"`{custom_target:.2f}%` "
                f"(s.d. Bulan "
                f"{bulan_list[selected_month_idx - 1]})"
            )

            st.write(
                "**Toleransi Deviasi:** `5%`"
            )

            st.write(
                f"**Item di Bawah Target:** "
                f"`{len(underperforming_items):,}` "
                f"dari "
                f"`{len(df_filtered):,}` item"
            )

            st.write(
                f"**Sisa Anggaran Pos Tertinggal:** "
                f"`{format_rupiah(underperforming_items['Sisa'].sum())}`"
            )

            # ------------------------------------------------
            # Status
            # ------------------------------------------------

            stat_counts = (
                df_filtered["Status Deviasi"]
                .value_counts()
                .reset_index()
            )

            stat_counts.columns = [
                "Status",
                "Jumlah Item"
            ]

            if not stat_counts.empty:

                fig_stat = px.pie(
                    stat_counts,
                    names="Status",
                    values="Jumlah Item",
                    color="Status",
                    color_discrete_map={
                        "🟢 Sesuai/Melebihi Target":
                            "#2ecc71",

                        "🟡 Sedikit Tertinggal (<5%)":
                            "#f1c40f",

                        "🔴 Kritis Tertinggal (≥5%)":
                            "#e74c3c"
                    },
                    hole=0.45
                )

                st.plotly_chart(
                    fig_stat,
                    use_container_width=True
                )

        with col_warn2:

            lagging_top = (
                underperforming_items
                .sort_values(
                    by=[
                        "Deviasi (%)",
                        "Sisa"
                    ],
                    ascending=[
                        True,
                        False
                    ]
                )
                .head(10)
                .copy()
            )

            if not lagging_top.empty:

                lagging_top["Short_Item"] = (
                    lagging_top["Item"]
                    .astype(str)
                    .str[:40]
                )

                fig_lag = px.bar(
                    lagging_top,
                    x="Deviasi (%)",
                    y="Short_Item",
                    orientation="h",
                    text="Persen Realisasi",
                    hover_data=[
                        "Jenis Belanja",
                        "Akun",
                        "Sub Komponen",
                        "Nama Akun",
                        "Pagu",
                        "Realisasi",
                        "Sisa"
                    ],
                    title=(
                        "10 Pos Belanja "
                        "Paling Tertinggal "
                        "dari Target Waktu"
                    ),
                    color="Deviasi (%)",
                    color_continuous_scale="Reds_r"
                )

                fig_lag.update_traces(
                    texttemplate="%{text:.1f}%",
                    textposition="outside"
                )

                fig_lag.update_layout(
                    yaxis={
                        "categoryorder":
                            "total descending"
                    }
                )

                st.plotly_chart(
                    fig_lag,
                    use_container_width=True
                )

            else:

                st.success(
                    "🎉 Seluruh item yang dipilih "
                    "telah memenuhi target "
                    "realisasi waktu!"
                )

    # ========================================================
    # TAB 3 - KOMPARASI
    # ========================================================

    with tab3:

        st.subheader(
            "📊 Perbandingan per Jenis Belanja "
            "(51, 52, 53)"
        )

        # ----------------------------------------------------
        # Gunakan DATA FILTER
        # ----------------------------------------------------

        jb_summary = (
            df_filtered
            .groupby("Jenis Belanja")[
                [
                    "Pagu",
                    "Realisasi",
                    "Sisa"
                ]
            ]
            .sum()
            .reset_index()
        )

        jb_summary["% Realisasi"] = (
            jb_summary["Realisasi"]
            / jb_summary["Pagu"]
            * 100
        ).round(2)

        if not jb_summary.empty:

            fig_jb = px.bar(
                jb_summary,
                x="Jenis Belanja",
                y=[
                    "Realisasi",
                    "Sisa"
                ],
                barmode="group",
                title=(
                    "Pagu Realisasi vs Sisa "
                    "per Jenis Belanja"
                ),
                color_discrete_sequence=[
                    "#2ecc71",
                    "#e74c3c"
                ]
            )

            st.plotly_chart(
                fig_jb,
                use_container_width=True
            )

        st.dataframe(
            jb_summary,
            use_container_width=True
        )

        # ----------------------------------------------------
        # PER RO
        # ----------------------------------------------------

        st.markdown("---")

        st.subheader(
            "Ringkasan Performa Realisasi "
            "per RO (Rincian Output)"
        )

        ro_summary = (
            df_filtered
            .groupby("RO")[
                [
                    "Pagu",
                    "Realisasi",
                    "Sisa"
                ]
            ]
            .sum()
            .reset_index()
        )

        ro_summary["% Realisasi"] = (
            ro_summary["Realisasi"]
            / ro_summary["Pagu"]
            * 100
        ).round(2)

        if not ro_summary.empty:

            fig_ro = px.bar(
                ro_summary,
                x="% Realisasi",
                y="RO",
                orientation="h",
                title=(
                    "Persentase Realisasi per RO"
                ),
                color="% Realisasi",
                color_continuous_scale="Blues"
            )

            st.plotly_chart(
                fig_ro,
                use_container_width=True
            )

        st.dataframe(
            ro_summary,
            use_container_width=True
        )

        # ----------------------------------------------------
        # RINGKASAN PER AKUN
        # ----------------------------------------------------

        st.markdown("---")

        st.subheader(
            "💳 Ringkasan Realisasi per Kode Akun"
        )

        akun_summary = (
            df_filtered
            .groupby(
                [
                    "Akun",
                    "Nama Akun",
                    "Jenis Belanja"
                ]
            )[
                [
                    "Pagu",
                    "Realisasi",
                    "Sisa"
                ]
            ]
            .sum()
            .reset_index()
        )

        akun_summary["% Realisasi"] = (
            akun_summary["Realisasi"]
            / akun_summary["Pagu"]
            * 100
        ).round(2)

        st.dataframe(
            akun_summary,
            use_container_width=True
        )

else:

    # ========================================================
    # BELUM ADA FILE
    # ========================================================

    st.info(
        "👋 Silakan unggah file FA Detail Anda "
        "di menu sebelah kiri (sidebar) untuk "
        "mulai mengeksplorasi data."
    )# Footer diletakkan di luar blok if/else
st.markdown(
    """
    <div class="charno-footer">
        <div class="brand">🚀 Charno Tech</div>
        <div class="tagline">
            Solusi Digital • Dashboard • Automasi & Teknologi
        </div>
        <p>
            Bantu tingkatkan efisiensi kerja dengan solusi digital.
        </p>
        <a
            class="wa-button"
            href="https://wa.me/6281259096935"
            target="_blank"
        >
            💬 Konsultasi via WhatsApp
        </a>
        <div class="promo">
            WhatsApp: 0812-5909-6935
        </div>
        <div class="promo">
            © 2026 Charno Tech — All Rights Reserved
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
