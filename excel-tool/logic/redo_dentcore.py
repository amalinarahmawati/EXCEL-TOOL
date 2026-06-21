import pandas as pd
import numpy as np
from datetime import timedelta

# =========================
# HOLIDAY
# =========================
TANGGAL_MERAH = pd.to_datetime([
    "2026-01-01","2026-01-16","2026-02-17",
    "2026-03-19","2026-03-21","2026-03-22",
    "2026-04-03","2026-05-01","2026-05-14",
    "2026-05-27","2026-05-31","2026-06-01",
    "2026-06-16","2026-08-17","2026-08-25",
    "2026-12-25"
]).normalize()


# =========================
# SAFE TEXT
# =========================
def safe_text(x):
    if pd.isna(x):
        return pd.NA
    return str(x)


# =========================
# SAFE DATETIME (ANTI 1970)
# =========================
def fix_excel_datetime(series):

    if pd.api.types.is_datetime64_any_dtype(series):
        return series

    s = pd.to_numeric(series, errors="coerce")

    mask_small = (s > 0) & (s < 1000)
    s.loc[mask_small] = s.loc[mask_small] * 100000

    s = s.where((s > 20000) & (s < 80000))

    return pd.to_datetime(
        s,
        unit="D",
        origin="1899-12-30",
        errors="coerce"
    )


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
# MAIN PROCESS
# =========================
def proses_redo_dentcore(df, df_master=None):

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
    # TANGGAL
    # =========================
    if "Tanggal" in df.columns:
        df["Tanggal"] = fix_excel_datetime(df["Tanggal"]).ffill()

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
    # DATE FIX
    # =========================
    for col in ["Jadwal Selesai", "Jadwal/Janji Kirim"]:
        if col in df.columns:
            df[col] = fix_excel_datetime(df[col])

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
    # AUTO FILL
    # =========================
    if "Jadwal Selesai" in df.columns and "Jadwal/Janji Kirim" in df.columns:

        mask = df["Jadwal/Janji Kirim"].isna()

        df.loc[mask, "Jadwal/Janji Kirim"] = df.loc[
            mask, "Jadwal Selesai"
        ].apply(next_working_day)

        df["Jadwal Selesai"] = df["Jadwal/Janji Kirim"]

    # =========================
    # PRODUK FILTER
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

        df.loc[mask_konfirmasi, ["Jadwal Selesai", "Jadwal/Janji Kirim"]] = pd.NaT

     # =========================
    # USER ID REBUILD (MASTER ONLY, DROP TOTAL OLD)
    # =========================
    if df_master is not None:

        df_master = df_master.copy()
        df_master.columns = df_master.columns.str.strip()

        df_master = df_master.rename(columns={
            "kode": "Kode",
            "KODE": "Kode",
            "Kode ": "Kode"
        })

        if "Kode" in df_master.columns and "ID Member" in df_master.columns:

            mapping = dict(zip(
                df_master["Kode"].astype(str).str.strip(),
                df_master["ID Member"].astype(str).str.strip()
            ))

            df["User ID"] = df["ID Member"].astype(str).str.strip().map(mapping)

    # fallback
    if "User ID" not in df.columns:
        df["User ID"] = df.get("ID Member", pd.NA)

    # =========================
    # CLEAN USER ID (ANTI NAN CRASH)
    # =========================
    for col in ["User ID", "ID Member"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .replace({"nan": pd.NA, "None": pd.NA, "-": pd.NA, "": pd.NA})
                .str.strip()
            )

    if "User ID" in df.columns and "ID Member" in df.columns:
        df["User ID"] = df["User ID"].fillna(df["ID Member"])

    # =========================
    # DUPLICATE FIX (SAFE VERSION)
    # =========================
    if "ID Member" in df.columns:

        result = []

        for _, row in df.iterrows():

            result.append(row.copy())

            id_member = str(row.get("ID Member", ""))

            if id_member.count("-") == 2 and id_member not in ["nan", "", "None"]:

                if row.get("User ID") != id_member:
                    new_row = row.copy()
                    new_row["User ID"] = id_member
                    result.append(new_row)

        df = pd.DataFrame(result)
        df = df.drop(columns=["ID Member"], errors="ignore")

      # =========================
        # POSISI KOLOM FINAL
        # Pasien | User ID | Produk Gigi
        # =========================
        cols = list(df.columns)
        
        # cari kolom produk
        kolom_produk = None
        
        if "Produk Gigi / Tambahan" in cols:
            kolom_produk = "Produk Gigi / Tambahan"
        
        elif "Produk Gigi" in cols:
            kolom_produk = "Produk Gigi"
        
        if (
            kolom_produk
            and "Pasien" in cols
            and "User ID" in cols
        ):
        
            cols.remove("Pasien")
            cols.remove("User ID")
        
            posisi_produk = cols.index(kolom_produk)
        
            cols.insert(posisi_produk, "Pasien")
            cols.insert(posisi_produk + 1, "User ID")
        
        # Dokter paling kanan
        if "Dokter" in cols:
        
            cols.remove("Dokter")
            cols.append("Dokter")
        
        df = df[cols]

    return df
