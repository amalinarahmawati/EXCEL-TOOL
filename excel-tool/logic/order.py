import pandas as pd
import numpy as np
import re
from datetime import timedelta


# =========================
# HOLIDAY
# =========================
tanggal_merah = pd.to_datetime([
    "2026-01-01","2026-01-16","2026-02-17",
    "2026-03-19","2026-03-21","2026-03-22",
    "2026-04-03","2026-05-01","2026-05-14",
    "2026-05-27","2026-05-31","2026-06-01",
    "2026-06-16","2026-08-17","2026-08-25",
    "2026-12-25"
]).normalize()


# =========================
# 🔥 FIX UTAMA (ANTI 1970 TOTAL FIX)
# =========================
def normalize_excel_date(series):

    # STEP 1: paksa numeric dulu
    num = pd.to_numeric(series, errors="coerce")

    # STEP 2: deteksi Excel serial valid
    # (Excel date normal range ~ 20000 - 80000)
    mask = (num > 20000) & (num < 80000)

    result = pd.Series(pd.NaT, index=series.index)

    # Excel serial convert
    result.loc[mask] = pd.to_datetime(
        num.loc[mask],
        unit="D",
        origin="1899-12-30",
        errors="coerce"
    )

    # STEP 3: string fallback (yang bukan numeric)
    result.loc[~mask] = pd.to_datetime(series[~mask], errors="coerce")

    return result


# =========================
# NEXT WORKDAY
# =========================
def next_working_day(t):
    if pd.isna(t):
        return pd.NaT

    t = t + timedelta(days=1)

    while t.weekday() == 6 or t.normalize() in tanggal_merah:
        t = t + timedelta(days=1)

    return t


# =========================
# MAIN FUNCTION
# =========================
def proses_order(df):

    df = df.copy()
    df.columns = df.columns.str.strip()

    # =========================
    # CUT TOTAL
    # =========================
    idx_total = df[
        df.astype(str).apply(
            lambda r: r.str.contains("TOTAL", case=False, na=False).any(),
            axis=1
        )
    ].index

    if len(idx_total) > 0:
        df = df.loc[:idx_total[0] - 1].copy()

    # =========================
    # DATE FIX (SEMUA HARUS LEWAT SINI)
    # =========================
    if "Tanggal" in df.columns:
        df["Tanggal"] = normalize_excel_date(df["Tanggal"]).ffill()

    # =========================
    # DROP COLUMN INDEX 17
    # =========================
    if len(df.columns) > 17:
        df = df.drop(df.columns[17], axis=1)

    # =========================
    # DROP UNUSED
    # =========================
    hapus_kolom = [
        "No Reservasi","Pembuat","Customer","Kota",
        "Tanggal Ekspedisi","Jam Ekspedisi",
        "Selisih Terima dan Input","Proses Order",
        "Ekstensi Garansi","Biaya Garansi",
        "Jam Terima Order","Jam Selesai",
        "Jadwal Delivery","Cito","Ketr Cito",
        "No Order Lanjutan","No Resi"
    ]

    df = df.drop(columns=hapus_kolom, errors="ignore")

    # =========================
    # DATE FIX (WAJIB SEMUA COL)
    # =========================
    for col in ["Jadwal Selesai", "Jadwal/Janji Kirim"]:
        if col in df.columns:
            df[col] = normalize_excel_date(df[col])

    # =========================
    # AUTO JADWAL
    # =========================
    if "Jadwal Selesai" in df.columns and "Jadwal/Janji Kirim" in df.columns:

        mask = df["Jadwal/Janji Kirim"].isna()

        df.loc[mask, "Jadwal/Janji Kirim"] = (
            df.loc[mask, "Jadwal Selesai"].apply(next_working_day)
        )

        df["Jadwal Selesai"] = df["Jadwal/Janji Kirim"]

    # =========================
    # HAPUS PRODUK TERTENTU
    # =========================
    produk_hapus = [
        "22 COR MODEL STONE",
        "22 COR TYPE III"
    ]
    
    kolom_produk = None
    
    if "Produk Gigi / Tambahan" in df.columns:
        kolom_produk = "Produk Gigi / Tambahan"
    
    elif "Produk Gigi" in df.columns:
        kolom_produk = "Produk Gigi"
    
    if kolom_produk:
    
        pattern = "|".join(produk_hapus)
    
        df = df[
            ~df[kolom_produk]
            .astype(str)
            .str.upper()
            .str.contains(pattern, na=False)
        ]

    # =========================
    # NOMOR CLEAN
    # =========================
    if "Nomor" in df.columns:

        df["Nomor"] = (
            df["Nomor"]
            .astype(str)
            .str.replace(r"\bK\b","Konfirmasi",regex=True)
            .str.replace(r"\s+"," ",regex=True)
            .str.strip()
        )

        mask_konfirmasi = df["Nomor"].str.contains("Konfirmasi", na=False)

        df.loc[mask_konfirmasi, ["Jadwal/Janji Kirim","Jadwal Selesai"]] = pd.NaT

     # =========================
        # USER ID & ID MEMBER CLEAN
        # =========================
        for col in ["User ID", "ID Member"]:
        
            if col in df.columns:
        
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.strip()
                    .replace(
                        r"^[-–—\s]*$",
                        pd.NA,
                        regex=True
                    )
                    .replace({
                        "nan": pd.NA,
                        "None": pd.NA,
                        "none": pd.NA,
                        "NaT": pd.NA
                    })
                )
        
        # =========================
        # FILL USER ID DARI ID MEMBER
        # =========================
        if "User ID" in df.columns and "ID Member" in df.columns:
            df["User ID"] = df["User ID"].fillna(df["ID Member"])
        
        # =========================
        # DUPLICATE LOGIC
        # =========================
        if "User ID" in df.columns and "ID Member" in df.columns:
        
            result = []
        
            for _, row in df.iterrows():
        
                result.append(row.copy())
        
                user_id = row.get("User ID")
                id_member = row.get("ID Member")
        
                if pd.isna(id_member):
                    continue
        
                id_member = str(id_member).strip()
        
                is_special_id = id_member.count("-") == 2
        
                if (
                    pd.notna(user_id)
                    and is_special_id
                    and str(user_id).strip() != id_member
                ):
                    new_row = row.copy()
                    new_row["User ID"] = id_member
                    result.append(new_row)
        
            df = pd.DataFrame(result)
        
        # =========================
        # FINAL USER ID SAFETY
        # =========================
        if "User ID" in df.columns:
        
            df["User ID"] = (
                df["User ID"]
                .astype(str)
                .str.strip()
                .replace(
                    r"^[-–—\s]*$",
                    pd.NA,
                    regex=True
                )
                .replace({
                    "nan": pd.NA,
                    "None": pd.NA,
                    "none": pd.NA
                })
            )
        
        # =========================
        # HAPUS ID MEMBER
        # =========================
        df = df.drop(columns=["ID Member"], errors="ignore")

    # =========================
    # POSISI KOLOM PASIEN
    # =========================
    cols = list(df.columns)

    if "Pasien" in cols and "User ID" in cols:
        cols.remove("Pasien")
        cols.insert(cols.index("User ID"), "Pasien")
        df = df[cols]

    # =========================
    # DOKTER KE AKHIR
    # =========================
    if "Dokter" in df.columns:
        cols = list(df.columns)
        cols.remove("Dokter")
        cols.append("Dokter")
        df = df[cols]

    # =========================
    # OPTIONAL: TAMPILKAN "-"
    # DI OUTPUT EXCEL
    # =========================
    if "Jadwal/Janji Kirim" in df.columns:
        df["Jadwal/Janji Kirim"] = df[
            "Jadwal/Janji Kirim"
        ].fillna("-")

    if "Jadwal Selesai" in df.columns:
        df["Jadwal Selesai"] = df[
            "Jadwal Selesai"
        ].fillna("-")

    return df
