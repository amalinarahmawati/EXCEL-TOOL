import pandas as pd
import numpy as np
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
# SAFE DATE (ANTI 1970)
# =========================
def safe_date(series):
    s = pd.to_numeric(series, errors="coerce")

    if s.notna().sum() > len(series) * 0.3:
        return pd.to_datetime(
            s,
            unit="D",
            origin="1899-12-30",
            errors="coerce"
        )

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
# MAIN
# =========================
def proses_cabut_pending(df, df_master=None):

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
    # DATE
    # =========================
    if "Tanggal" in df.columns:
        df["Tanggal"] = safe_date(df["Tanggal"]).ffill()

    # =========================
    # DROP USER ID LAMA (WAJIB)
    # =========================
    df = df.drop(columns=["Waktu Cabut", "Customer", "User ID"], errors="ignore")

    # =========================
    # JADWAL FIX
    # =========================
    for col in ["Jadwal Selesai", "Janji Kirim"]:
        if col in df.columns:
            df[col] = safe_date(df[col])

    if "Jadwal Selesai" in df.columns and "Janji Kirim" in df.columns:

        mask = df["Janji Kirim"].isna()

        df.loc[mask, "Janji Kirim"] = df.loc[
            mask, "Jadwal Selesai"
        ].apply(next_working_day)

        df["Jadwal Selesai"] = df["Janji Kirim"]

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
        df.loc[mask_konfirmasi, ["Jadwal Selesai", "Janji Kirim"]] = pd.NaT

    # =========================
    # 🔥 USER ID REBUILD TOTAL (NO LAMA KEPAKAI)
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

            mapping = df_master.set_index("Kode")["ID Member"].astype(str).to_dict()

            df["ID Member"] = df.get("ID Member", pd.NA)

            # CLEAN dulu ID Member
            df["ID Member"] = (
                df["ID Member"]
                .astype(str)
                .replace({"nan": pd.NA, "None": pd.NA, "-": pd.NA, "": pd.NA})
                .str.strip()
            )

            # 🔥 REBUILD TOTAL USER ID (NO FALLBACK FROM OLD USER ID)
            df["User ID"] = df["ID Member"].map(mapping)

    else:
        df["User ID"] = pd.NA

    # =========================
    # fallback terakhir (ONLY ID MEMBER)
    # =========================
    df["User ID"] = df["User ID"].fillna(df.get("ID Member", pd.NA))

    # =========================
    # DUPLICATE LOGIC (SAMA REDO STYLE)
    # =========================
    if "ID Member" in df.columns:

        result = []

        for _, row in df.iterrows():

            result.append(row.copy())

            id_member = str(row.get("ID Member", ""))

            if id_member.count("-") == 2 and id_member != "nan":

                if row.get("User ID") != id_member:
                    new_row = row.copy()
                    new_row["User ID"] = id_member
                    result.append(new_row)

        df = pd.DataFrame(result)

    # =========================
    # DROP ID MEMBER (FINAL CLEAN)
    # =========================
    df = df.drop(columns=["ID Member"], errors="ignore")

    # =========================
    # POSITION (REDO STYLE)
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
