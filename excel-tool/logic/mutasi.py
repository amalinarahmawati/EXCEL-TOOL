import pandas as pd
import numpy as np


def proses_mutasi(df):

    # =========================
    # CLEAN COLUMN NAME
    # =========================
    df.columns = df.columns.str.strip()

    # =========================
    # HAPUS SEMUA BARIS
    # DARI "TOTAL" SAMPAI BAWAH
    # =========================
    idx_total = df[
        df.astype(str).apply(
            lambda row: row.astype(str).str.contains(
                "TOTAL",
                case=False,
                na=False
            ).any(),
            axis=1
        )
    ].index

    if len(idx_total) > 0:
        baris_total = idx_total[0]

        # ambil hanya data sebelum TOTAL
        df = df.loc[:baris_total - 1]

    # =========================
    # ISI TANGGAL KOSONG KE BAWAH
    # =========================
    if "Tanggal" in df.columns:
        df["Tanggal"] = df["Tanggal"].ffill()

    # =========================
    # HAPUS BARIS NOMOR YANG MENGANDUNG TOTAL
    # =========================
    if "Nomor" in df.columns:
        df = df[
            ~df["Nomor"].astype(str)
            .str.contains(
                "Total",
                case=False,
                na=False
            )
        ]

    # =========================
    # HAPUS KOLOM NO FAKTUR
    # =========================
    df = df.drop(
        columns=["No Faktur"],
        errors="ignore"
    )

    # =========================
    # BERSIHKAN CUSTOMER
    # (kolom tetap ada)
    # =========================
    if "Customer" in df.columns:
        df["Customer"] = ""

    # =========================
    # HAPUS BARIS NOMINAL
    # -, kosong, null,
    # dan nilai kecil (1 s/d 1000)
    # =========================
    if "Jumlah" in df.columns:

        # ubah nilai kosong jadi NaN
        df["Jumlah"] = df["Jumlah"].replace(
            ["-", "", "None", "nan"],
            np.nan
        )

        # ubah ke numeric
        df["Jumlah"] = pd.to_numeric(
            df["Jumlah"],
            errors="coerce"
        )

        # hapus null, 0, dan <= 1000
        df = df[
            df["Jumlah"].notna() &
            (df["Jumlah"] > 1000)
        ]

    # =========================
    # FORMAT JUMLAH
    # =========================
    if "Jumlah" in df.columns:

        # pastikan numeric
        df["Jumlah"] = pd.to_numeric(
            df["Jumlah"],
            errors="coerce"
        )

        # format ribuan pakai koma
        df["Jumlah"] = df["Jumlah"].apply(
            lambda x: f"{int(x):,}"
            if pd.notna(x)
            else ""
        )

    # =========================
    # CLEAN USER ID
    # =========================
    if "User ID" in df.columns:
        df["User ID"] = df["User ID"].replace(
            ["nan", "", "None", "-", " "],
            pd.NA
        )

    if "ID Member" in df.columns:
        df["ID Member"] = df["ID Member"].replace(
            ["nan", "", "None", " "],
            pd.NA
        )

    # isi User ID kalau kosong
    if "User ID" in df.columns and "ID Member" in df.columns:
        df["User ID"] = df["User ID"].fillna(
            df["ID Member"]
        )

    # =========================
    # DUPLICATE LOGIC FIX
    # =========================
    if (
        "User ID" in df.columns
        and "ID Member" in df.columns
    ):

        result = []

        for _, row in df.iterrows():

            user_id = row.get("User ID")
            id_member = str(
                row.get("ID Member", "")
            )

            is_special_id = (
                id_member.count("-") == 2
                and id_member != "nan"
            )

            # selalu simpan row utama
            result.append(row.copy())

            # duplicate hanya jika:
            # User ID ada + ID special
            if (
                pd.notna(user_id)
                and is_special_id
                and user_id != id_member
            ):
                new_row = row.copy()
                new_row["User ID"] = id_member
                result.append(new_row)

        df = pd.DataFrame(result)

        # hapus ID Member
        df = df.drop(
            columns=["ID Member"],
            errors="ignore"
        )

    return df