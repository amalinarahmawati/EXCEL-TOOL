import pandas as pd
import numpy as np
import re
from datetime import timedelta

# =========================
# HOLIDAY LIST
# =========================
TANGGAL_MERAH = pd.to_datetime([
    "2026-01-01", "2026-01-16", "2026-02-17",
    "2026-03-19", "2026-03-21", "2026-03-22",
    "2026-04-03", "2026-05-01", "2026-05-14",
    "2026-05-27", "2026-05-31", "2026-06-01",
    "2026-06-16", "2026-08-17", "2026-08-25",
    "2026-12-25"
]).normalize()


# =========================
# SAFE FUNCTIONS
# =========================
def safe_datetime(col):
    return pd.to_datetime(col, errors="coerce")

def safe_text(x):
    if pd.isna(x):
        return pd.NA
    return str(x)


# =========================
# MAIN FUNCTION
# =========================
def proses_redo(df: pd.DataFrame, df_master: pd.DataFrame = None):

    df = df.copy()
    df_master = df_master.copy() if df_master is not None else None

    # =========================
    # CLEAN COLUMN
    # =========================
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
    # FILL TANGGAL
    # =========================
    if "Tanggal" in df.columns:
        df["Tanggal"] = safe_datetime(df["Tanggal"]).ffill()

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
    # DATE CONVERT (IMPORTANT FIX 1970 ROOT)
    # =========================
    for col in ["Jadwal Selesai", "Jadwal/Janji Kirim"]:
        if col in df.columns:
            df[col] = safe_datetime(df[col])

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
    # AUTO FILL JADWAL (SAFE)
    # =========================
    if "Jadwal Selesai" in df.columns and "Jadwal/Janji Kirim" in df.columns:

        mask = df["Jadwal/Janji Kirim"].isna()

        df.loc[mask, "Jadwal/Janji Kirim"] = df.loc[mask, "Jadwal Selesai"].apply(next_working_day)

        # ❗JANGAN string "-"
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

        df["Nomor"] = df["Nomor"].apply(
            lambda x: re.sub(r"\s+", " ", x).strip() if pd.notna(x) else x
        )

        df["Nomor"] = df["Nomor"].apply(
            lambda x: re.sub(r"\bK\b", "Konfirmasi", x) if pd.notna(x) else x
        )

        mask_konfirmasi = df["Nomor"].astype(str).str.contains("Konfirmasi", na=False)

        # ❗JANGAN "-", pakai NaT biar gak rusak datetime
        if "Jadwal/Janji Kirim" in df.columns:
            df.loc[mask_konfirmasi, "Jadwal/Janji Kirim"] = pd.NaT

        if "Jadwal Selesai" in df.columns:
            df.loc[mask_konfirmasi, "Jadwal Selesai"] = pd.NaT

    # =========================
    # USER ID FROM MASTER (FIXED MAPPING)
    # =========================
    if df_master is not None and "ID Member" in df.columns:

        df_master.columns = df_master.columns.str.strip()

        if "Kode" in df_master.columns and "ID Member" in df_master.columns:

            df_master["Kode"] = df_master["Kode"].astype(str).str.strip()
            df_master["ID Member"] = df_master["ID Member"].astype(str).str.strip()

            mapping = dict(zip(df_master["Kode"], df_master["ID Member"]))

            df["User ID"] = df["ID Member"].astype(str).str.strip().map(mapping)

    # fallback SAFE
    if "User ID" not in df.columns:
        df["User ID"] = pd.NA

    if "ID Member" in df.columns:
        df["User ID"] = df["User ID"].fillna(df["ID Member"])

    # =========================
    # FINAL CLEAN DATE (ANTI 1970 BUG FIX)
    # =========================
    for col in ["Jadwal Selesai", "Jadwal/Janji Kirim"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # =========================
    # POSISI KOLOM
    # =========================
    cols = list(df.columns)

    if "Pasien" in cols and "User ID" in cols:
        cols.remove("Pasien")
        cols.insert(cols.index("User ID"), "Pasien")
        df = df[cols]

    if "Dokter" in df.columns:
        cols = list(df.columns)
        cols.remove("Dokter")
        cols.append("Dokter")
        df = df[cols]

    return df
