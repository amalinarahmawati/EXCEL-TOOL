import pandas as pd
import numpy as np
import re
from datetime import timedelta

TANGGAL_MERAH = pd.to_datetime([
    "2026-01-01", "2026-01-16", "2026-02-17",
    "2026-03-19", "2026-03-21", "2026-03-22",
    "2026-04-03", "2026-05-01", "2026-05-14",
    "2026-05-27", "2026-05-31", "2026-06-01",
    "2026-06-16", "2026-08-17", "2026-08-25",
    "2026-12-25"
]).normalize()


def safe_text(x):
    if pd.isna(x):
        return pd.NA
    return str(x)


# =========================
# 🔥 FIX DATE TOTAL (ANTI 1970 FULL)
# =========================
def fix_excel_datetime(series):

    # kalau sudah datetime → langsung return
    if pd.api.types.is_datetime64_any_dtype(series):
        return series

    # numeric Excel serial (INI FIX UTAMA)
    if pd.api.types.is_numeric_dtype(series):
        s = pd.to_numeric(series, errors="coerce")

        # filter angka valid Excel date (hindari noise)
        s = s.where(s > 20000)

        return pd.to_datetime(
            s,
            unit="D",  # 🔥 HARUS D BESAR
            origin="1899-12-30",
            errors="coerce"
        )

    # string / object
    return pd.to_datetime(series, errors="coerce")


# =========================
# MAIN FUNCTION
# =========================
def proses_redo(df: pd.DataFrame, df_master: pd.DataFrame = None):

    df = df.copy()
    df_master = df_master.copy() if df_master is not None else None

    df.columns = df.columns.str.strip()

    # =========================
    # CUT TOTAL
    # =========================
    idx_total = df[
        df.astype(str).apply(
            lambda row: row.str.contains("TOTAL", case=False, na=False).any(),
            axis=1
        )
    ].index

    if len(idx_total) > 0:
        df = df.loc[:idx_total[0] - 1].copy()

    # =========================
    # TANGGAL
    # =========================
    if "Tanggal" in df.columns:
        df["Tanggal"] = fix_excel_datetime(df["Tanggal"]).ffill().dt.normalize()

    # =========================
    # DROP KOLOM
    # =========================
    drop_cols = [
        "No Reservasi", "Pembuat", "Customer", "Kota",
        "Proses Order", "Jam Terima Order", "Jam Selesai",
        "Jadwal Delivery", "Cito", "Ketr Cito",
        "No Order Lanjutan", "Personalia",
        "Melanjutkan Jadwal Order", "No Resi Pengiriman",
        "Alasan Redo"
    ]
    df = df.drop(columns=drop_cols, errors="ignore")

    # =========================
    # DATE FIX (ANTI DOUBLE BUG)
    # =========================
    for col in ["Jadwal Selesai", "Jadwal/Janji Kirim"]:

        if col in df.columns:
            df[col] = fix_excel_datetime(df[col]).dt.normalize()

    # =========================
    # NEXT WORKING DAY
    # =========================
    def next_working_day(t):
        if pd.isna(t):
            return pd.NaT

        t = t + timedelta(days=1)

        while t.weekday() == 6 or t.normalize() in TANGGAL_MERAH:
            t = t + timedelta(days=1)

        return t

    # =========================
    # AUTO FILL JADWAL
    # =========================
    if "Jadwal Selesai" in df.columns and "Jadwal/Janji Kirim" in df.columns:

        mask = df["Jadwal/Janji Kirim"].isna()

        df.loc[mask, "Jadwal/Janji Kirim"] = df.loc[mask, "Jadwal Selesai"].apply(next_working_day)

        df["Jadwal Selesai"] = df["Jadwal/Janji Kirim"]

    # =========================
    # HAPUS PRODUK
    # =========================
    produk_hapus = ["22 COR MODEL STONE", "22 COR TYPE III"]

    if "Produk Gigi" in df.columns:
        pattern = "|".join(produk_hapus)
        df = df[~df["Produk Gigi"].astype(str).str.upper().str.contains(pattern, na=False)]

    # =========================
    # NOMOR CLEAN
    # =========================
    if "Nomor" in df.columns:

        df["Nomor"] = df["Nomor"].apply(safe_text)
        df["Nomor"] = df["Nomor"].str.replace(r"\s+", " ", regex=True)
        df["Nomor"] = df["Nomor"].str.replace(r"\bK\b", "Konfirmasi", regex=True)

        mask_konfirmasi = df["Nomor"].str.contains("Konfirmasi", na=False)

        df.loc[mask_konfirmasi, "Jadwal/Janji Kirim"] = pd.NaT
        df.loc[mask_konfirmasi, "Jadwal Selesai"] = pd.NaT

    # =========================
    # USER ID
    # =========================
    if df_master is not None and "ID Member" in df.columns:

        df_master.columns = df_master.columns.str.strip()

        if "Kode" in df_master.columns:

            mapping = dict(zip(
                df_master["Kode"].astype(str).str.strip(),
                df_master["ID Member"].astype(str).str.strip()
            ))

            df["User ID"] = df["ID Member"].astype(str).str.strip().map(mapping)

    if "User ID" not in df.columns:
        df["User ID"] = pd.NA

    if "ID Member" in df.columns:
        df["User ID"] = df["User ID"].fillna(df["ID Member"])

    return df
