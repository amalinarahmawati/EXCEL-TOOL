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
# SAFE DATE (ANTI 1970 TOTAL FIX)
# =========================
def safe_date(series):
    s = pd.to_numeric(series, errors="coerce")

    if s.notna().sum() > len(series) * 0.3:
        return pd.to_datetime(s, unit="D", origin="1899-12-30", errors="coerce")

    return pd.to_datetime(series, errors="coerce")


# =========================
# NEXT WORKING DAY
# =========================
def next_working_day(t):
    if pd.isna(t):
        return pd.NaT

    t = t + timedelta(days=1)

    while t.weekday() == 6 or t.normalize() in tanggal_merah:
        t = t + timedelta(days=1)

    return t


# =========================
# MAIN PROCESS
# =========================
def proses_redo_dentcore(df):

    df = df.copy()
    df.columns = df.columns.str.strip()

    # =========================
    # CUT TOTAL
    # =========================
    idx = df[
        df.astype(str).apply(
            lambda r: r.str.contains("TOTAL", case=False, na=False).any(),
            axis=1
        )
    ].index

    if len(idx) > 0:
        df = df.loc[:idx[0] - 1].copy()

    # =========================
    # DROP KOLOM
    # =========================
    drop_cols = [
        "No Reservasi","Pembuat","Customer","Kota",
        "Proses Order","Jam Terima Order","Jam Selesai",
        "Jadwal Delivery","Cito","Ketr Cito",
        "No Order Lanjutan","Personalia",
        "Melanjutkan Jadwal Order","No Resi Pengiriman",
        "Alasan Redo"
    ]

    df = df.drop(columns=drop_cols, errors="ignore")

    # =========================
    # DATE FIX (ANTI 1970)
    # =========================
    if "Jadwal Selesai" in df.columns:
        df["Jadwal Selesai"] = safe_date(df["Jadwal Selesai"])

    if "Jadwal/Janji Kirim" in df.columns:
        df["Jadwal/Janji Kirim"] = safe_date(df["Jadwal/Janji Kirim"])

    # =========================
    # AUTO FILL JADWAL
    # =========================
    if "Jadwal Selesai" in df.columns and "Jadwal/Janji Kirim" in df.columns:

        mask = df["Jadwal/Janji Kirim"].isna()

        df.loc[mask, "Jadwal/Janji Kirim"] = (
            df.loc[mask, "Jadwal Selesai"].apply(next_working_day)
        )

        # copy aman (TIDAK overwrite string "-")
        df["Jadwal Selesai"] = df["Jadwal/Janji Kirim"]

    # =========================
    # PRODUK FILTER
    # =========================
    produk_hapus = ["22 COR MODEL STONE", "22 COR TYPE III"]
    pattern = "|".join(produk_hapus)

    if "Produk Gigi / Tambahan" in df.columns:
        df = df[
            ~df["Produk Gigi / Tambahan"]
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
            .str.replace(r"\bK\b", "Konfirmasi", regex=True)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )

        mask_konfirmasi = df["Nomor"].str.contains("Konfirmasi", na=False)

        df.loc[mask_konfirmasi, ["Jadwal Selesai", "Jadwal/Janji Kirim"]] = pd.NaT

    # =========================
    # USER ID CLEAN
    # =========================
    for col in ["User ID", "ID Member"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .replace({"nan": pd.NA, "None": pd.NA, "-": pd.NA, "": pd.NA})
                .str.strip()
            )

    # fill User ID
    if "User ID" in df.columns and "ID Member" in df.columns:
        df["User ID"] = df["User ID"].fillna(df["ID Member"])

    # =========================
    # DUPLICATE LOGIC (SAFE)
    # =========================
    if "User ID" in df.columns and "ID Member" in df.columns:

        result = []

        for _, row in df.iterrows():

            result.append(row.copy())

            id_member = str(row.get("ID Member", ""))

            if id_member.count("-") == 2 and id_member != "nan":
                if row["User ID"] != id_member:
                    new_row = row.copy()
                    new_row["User ID"] = id_member
                    result.append(new_row)

        df = pd.DataFrame(result)
        df = df.drop(columns=["ID Member"], errors="ignore")

    # =========================
    # POSISI KOLOM
    # =========================
    cols = list(df.columns)

    if "Pasien" in cols and "User ID" in cols:
        cols.remove("Pasien")
        cols.insert(cols.index("User ID"), "Pasien")
        df = df[cols]

    if "Dokter" in cols:
        cols.remove("Dokter")
        cols.append("Dokter")
        df = df[cols]

    return df
