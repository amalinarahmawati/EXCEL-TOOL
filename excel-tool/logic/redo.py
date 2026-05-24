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
])


# =========================
# SAFE DATETIME (ANTI 1970 FIX)
# =========================
def safe_datetime(col):
    return pd.to_datetime(col, errors="coerce")


# =========================
# MAIN FUNCTION
# =========================
def proses_redo(df: pd.DataFrame, df_master: pd.DataFrame):

    df = df.copy()
    df_master = df_master.copy() if df_master is not None else None

    # =========================
    # CLEAN COLUMN
    # =========================
    df.columns = df.columns.str.strip()

    # =========================
    # HAPUS DATA DARI TOTAL
    # =========================
    idx_total = df[
        df.astype(str).apply(
            lambda row: row.astype(str).str.contains("TOTAL", case=False, na=False).any(),
            axis=1
        )
    ].index

    if len(idx_total) > 0:
        df = df.loc[:idx_total[0] - 1]

    # =========================
    # FILL TANGGAL (SAFE)
    # =========================
    if "Tanggal" in df.columns:
        df["Tanggal"] = pd.to_datetime(df["Tanggal"], errors="coerce")
        df["Tanggal"] = df["Tanggal"].ffill()

    # =========================
    # DROP KOLOM TIDAK DIPAKAI
    # =========================
    hapus_kolom = [
        "No Reservasi", "Pembuat", "Customer", "Kota",
        "Proses Order", "Jam Terima Order", "Jam Selesai",
        "Jadwal Delivery", "Cito", "Ketr Cito",
        "No Order Lanjutan", "Personalia",
        "Melanjutkan Jadwal Order", "No Resi Pengiriman",
        "Alasan Redo"
    ]

    df = df.drop(columns=hapus_kolom, errors="ignore")

    # =========================
    # DATE FIX (INI YANG NGHILANGIN 1970)
    # =========================
    if "Jadwal Selesai" in df.columns:
        df["Jadwal Selesai"] = safe_datetime(df["Jadwal Selesai"])

    if "Jadwal/Janji Kirim" in df.columns:
        df["Jadwal/Janji Kirim"] = safe_datetime(df["Jadwal/Janji Kirim"])

    # =========================
    # NEXT WORKING DAY
    # =========================
    def next_working_day(tanggal):
        if pd.isna(tanggal):
            return pd.NaT

        tanggal = tanggal + timedelta(days=1)

        while tanggal.weekday() == 6 or tanggal.normalize() in TANGGAL_MERAH:
            tanggal = tanggal + timedelta(days=1)

        return tanggal

    # =========================
    # AUTO FILL JADWAL
    # =========================
    if "Jadwal Selesai" in df.columns and "Jadwal/Janji Kirim" in df.columns:

        mask = df["Jadwal/Janji Kirim"].isna()

        df.loc[mask, "Jadwal/Janji Kirim"] = df.loc[mask, "Jadwal Selesai"].apply(
            next_working_day
        )

        # COPY tanpa convert ke string "-"
        df["Jadwal Selesai"] = df["Jadwal/Janji Kirim"]

    # =========================
    # HAPUS PRODUK
    # =========================
    produk_hapus = ["22 COR MODEL STONE", "22 COR TYPE III"]

    if "Produk Gigi" in df.columns:
        pattern = "|".join(produk_hapus)
        df = df[~df["Produk Gigi"].astype(str).str.upper().str.contains(pattern, na=False)]

    # =========================
    # FIX NOMOR
    # =========================
    if "Nomor" in df.columns:
        df["Nomor"] = df["Nomor"].astype(str).apply(
            lambda x: re.sub(r'\bK\b', 'Konfirmasi',
                    re.sub(r'\s+', ' ', x)).strip()
        )

        mask_konfirmasi = df["Nomor"].str.contains("Konfirmasi", case=False, na=False)

        # IMPORTANT: pakai NaT (BUKAN "-")
        if "Jadwal/Janji Kirim" in df.columns:
            df.loc[mask_konfirmasi, "Jadwal/Janji Kirim"] = pd.NaT

        if "Jadwal Selesai" in df.columns:
            df.loc[mask_konfirmasi, "Jadwal Selesai"] = pd.NaT

    # =========================
    # USER ID FROM MASTER (FIXED TOTAL SAFE)
    # =========================
    if df_master is not None and "ID Member" in df.columns:

        df_master.columns = df_master.columns.str.strip()

        df_master = df_master.rename(columns={
            "kode": "Kode",
            "KODE": "Kode",
            "Kode ": "Kode"
        })

        if "Kode" in df_master.columns:

            df["ID Member"] = df["ID Member"].astype(str).str.strip()
            df_master["Kode"] = df_master["Kode"].astype(str).str.strip()

            df = df.merge(
                df_master[["Kode", "ID Member"]],
                left_on="ID Member",
                right_on="Kode",
                how="left"
            )

            df["User ID"] = df["ID Member_y"]

            df.drop(columns=["Kode", "ID Member_y"], inplace=True, errors="ignore")

            # fallback aman
            df["User ID"] = df["User ID"].replace(["nan", "", "None", "-", " "], pd.NA)
            df["User ID"] = df["User ID"].fillna(df["ID Member"])

    # =========================
    # FINAL CLEAN (ANTI ERROR TYPE)
    # =========================
    for col in ["Jadwal Selesai", "Jadwal/Janji Kirim"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # =========================
    # POSISI PASIEN
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

    return df
