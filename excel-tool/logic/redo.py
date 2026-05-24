import pandas as pd
import numpy as np
import re
from datetime import timedelta


# =========================
# HOLIDAY LIST
# =========================
tanggal_merah = pd.to_datetime([
    "2026-01-01", "2026-01-16", "2026-02-17",
    "2026-03-19", "2026-03-21", "2026-03-22",
    "2026-04-03", "2026-05-01", "2026-05-14",
    "2026-05-27", "2026-05-31", "2026-06-01",
    "2026-06-16", "2026-08-17", "2026-08-25",
    "2026-12-25"
])


def next_working_day(tanggal):
    if pd.isna(tanggal):
        return pd.NaT

    tanggal = pd.to_datetime(tanggal, errors="coerce")
    if pd.isna(tanggal):
        return pd.NaT

    tanggal = tanggal + timedelta(days=1)

    while tanggal.weekday() == 6 or tanggal.normalize() in tanggal_merah:
        tanggal = tanggal + timedelta(days=1)

    return tanggal


# =========================
# MAIN FUNCTION
# =========================
def proses_redo(df, df_master):

    if df is None:
        return df

    df = df.copy()
    df.columns = df.columns.str.strip()

    # =========================
    # MASTER CHECK
    # =========================
    if df_master is None or df_master.empty:
        raise ValueError("Master belum diupload")

    df_master = df_master.copy()
    df_master.columns = df_master.columns.str.strip()

    # =========================
    # CUT TOTAL
    # =========================
    idx_total = df[df.astype(str).apply(
        lambda row: row.str.contains("TOTAL", case=False, na=False).any(),
        axis=1
    )].index

    if len(idx_total) > 0:
        df = df.loc[:idx_total[0] - 1]

    # =========================
    # FILL TANGGAL
    # =========================
    if "Tanggal" in df.columns:
        df["Tanggal"] = df["Tanggal"].ffill()

    # =========================
    # DROP UNUSED COLUMNS
    # =========================
    hapus_kolom = [
        "No Reservasi", "Pembuat", "Customer", "Kota",
        "Proses Order", "Jam Terima Order", "Jam Selesai",
        "Jadwal Delivery", "Cito", "Ketr Cito",
        "No Order Lanjutan", "Personalia",
        "Melanjutkan Jadwal Order",
        "No Resi Pengiriman", "Alasan Redo"
    ]

    df = df.drop(columns=[c for c in hapus_kolom if c in df.columns], errors="ignore")

    # =========================
    # DATE LOGIC
    # =========================
    if "Jadwal Selesai" in df.columns:
        df["Jadwal Selesai"] = pd.to_datetime(df["Jadwal Selesai"], errors="coerce")

    if "Jadwal/Janji Kirim" in df.columns:
        df["Jadwal/Janji Kirim"] = pd.to_datetime(df["Jadwal/Janji Kirim"], errors="coerce")

        mask = df["Jadwal/Janji Kirim"].isna()
        df.loc[mask, "Jadwal/Janji Kirim"] = df.loc[mask, "Jadwal Selesai"].apply(next_working_day)

        df["Jadwal Selesai"] = df["Jadwal/Janji Kirim"]

    # =========================
    # REMOVE PRODUCT
    # =========================
    if "Produk Gigi" in df.columns:
        produk_hapus = ["22 COR MODEL STONE", "22 COR TYPE III"]
        pattern = "|".join(produk_hapus)

        df = df[~df["Produk Gigi"].astype(str).str.upper().str.contains(pattern, na=False)]

    # =========================
    # FIX NOMOR (FIXED INDENT ERROR)
    # =========================
    if "Nomor" in df.columns:

        def fix_nomor(x):
            if pd.isna(x):
                return x
            x = str(x)
            x = re.sub(r"\s+", " ", x)
            x = re.sub(r"\bK\b", "Konfirmasi", x)
            return x.strip()

        df["Nomor"] = df["Nomor"].apply(fix_nomor)

    # =========================
    # MASTER MERGE SAFE
    # =========================
    if "ID Member" in df.columns and "Kode" in df_master.columns:

        df["ID Member"] = df["ID Member"].astype(str).str.strip()
        df_master["Kode"] = df_master["Kode"].astype(str).str.strip()

        df = df.merge(
            df_master[["Kode", "ID Member"]],
            left_on="ID Member",
            right_on="Kode",
            how="left"
        )

        df["User ID"] = df["ID Member_y"]
        df = df.drop(columns=["Kode", "ID Member_y"], errors="ignore")

    # =========================
    # USER ID CLEAN (ANTI "-")
    # =========================
    if "User ID" in df.columns:

        df["User ID"] = (
            df["User ID"]
            .astype(str)
            .str.strip()
            .replace(["nan", "None", "", "-", "–", "—"], pd.NA)
        )

    if "ID Member" in df.columns:
        df["ID Member"] = df["ID Member"].astype(str).str.strip()
        df["User ID"] = df["User ID"].fillna(df["ID Member"])

    df["User ID"] = df["User ID"].replace(["-", "–", "—"], pd.NA)

    # =========================
    # DUPLICATE LOGIC
    # =========================
    result = []

    for _, row in df.iterrows():

        user_id = row.get("User ID")
        id_member = str(row.get("ID Member", ""))

        is_special = id_member.count("-") == 2 and id_member != "nan"

        result.append(row.copy())

        if pd.notna(user_id) and is_special and user_id != id_member:
            new_row = row.copy()
            new_row["User ID"] = id_member
            result.append(new_row)

    df = pd.DataFrame(result)

    df = df.drop(columns=["ID Member"], errors="ignore")

    # =========================
    # POSITIONING PASIEN
    # =========================
    if "Pasien" in df.columns and "User ID" in df.columns:
        cols = list(df.columns)
        cols.remove("Pasien")
        cols.insert(cols.index("User ID"), "Pasien")
        df = df[cols]

    # =========================
    # OUTPUT CLEAN
    # =========================
    if "Jadwal/Janji Kirim" in df.columns:
        df["Jadwal/Janji Kirim"] = df["Jadwal/Janji Kirim"].fillna("-")

    if "Jadwal Selesai" in df.columns:
        df["Jadwal Selesai"] = df["Jadwal Selesai"].fillna("-")

    return df
