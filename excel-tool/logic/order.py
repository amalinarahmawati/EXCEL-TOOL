import pandas as pd
import numpy as np
import re
from utils.calendar import load_holidays, next_working_day

# =========================
# LOAD HOLIDAY SEKALI
# =========================
holidays = load_holidays()


def proses_order(df):
holidays = load_holidays()
    # =========================
    # CLEAN COLUMN NAME
    # =========================
    df.columns = df.columns.str.strip()

    # =========================
    # HAPUS BARIS DARI TOTAL KE BAWAH
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
        df = df.loc[:baris_total - 1]

    # =========================
    # ISI TANGGAL KE BAWAH
    # =========================
    if "Tanggal" in df.columns:
        df["Tanggal"] = df["Tanggal"].ffill()

    # =========================
    # HAPUS KOLOM INDEX 17 (R column)
    # =========================
    if len(df.columns) > 17:
        df = df.drop(df.columns[17], axis=1)

    # =========================
    # HAPUS KOLOM TIDAK DIPAKAI
    # =========================
    hapus_kolom = [
        "No Reservasi",
        "Pembuat",
        "Customer",
        "Kota",
        "Tanggal Ekspedisi",
        "Jam Ekspedisi",
        "Selisih Terima dan Input",
        "Proses Order",
        "Ekstensi Garansi",
        "Biaya Garansi",
        "Jam Terima Order",
        "Jam Selesai",
        "Jadwal Delivery",
        "Cito",
        "Ketr Cito",
        "No Order Lanjutan",
        "No Resi"
    ]

    df = df.drop(
        columns=[col for col in hapus_kolom if col in df.columns],
        errors="ignore"
    )

    # =========================
    # JADWAL OTOMATIS
    # =========================

    # convert dulu ke datetime
    if "Jadwal Selesai" in df.columns:
        df["Jadwal Selesai"] = pd.to_datetime(
            df["Jadwal Selesai"],
            errors="coerce"
        )

    if "Jadwal/Janji Kirim" in df.columns:
        df["Jadwal/Janji Kirim"] = pd.to_datetime(
            df["Jadwal/Janji Kirim"],
            errors="coerce"
        )

        # isi yang kosong saja
        mask = df["Jadwal/Janji Kirim"].isna()

        if "Jadwal Selesai" in df.columns:
            df.loc[mask, "Jadwal/Janji Kirim"] = df.loc[
                mask,
                "Jadwal Selesai"
            ].apply(
                lambda x: next_working_day(x, holidays)
            )

    # =========================
    # COPY JADWAL
    # =========================
    if (
        "Jadwal/Janji Kirim" in df.columns
        and "Jadwal Selesai" in df.columns
    ):
        df["Jadwal Selesai"] = df["Jadwal/Janji Kirim"]

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
    # HAPUS PRODUK TERTENTU
    # =========================
    produk_hapus = [
        "22 COR MODEL STONE",
        "22 COR TYPE III"
    ]

    pattern = "|".join(produk_hapus)

    if "Produk Gigi / Tambahan" in df.columns:
        df = df[
            ~df["Produk Gigi / Tambahan"]
            .astype(str)
            .str.upper()
            .str.contains(pattern, na=False)
        ]

    # =========================
    # FIX NOMOR
    # =========================
    if "Nomor" in df.columns:

        def fix_nomor(x):
            if pd.isna(x):
                return x

            x = str(x)

            # K -> Konfirmasi
            x = re.sub(r"\bK\b", "Konfirmasi", x)

            # rapikan spasi
            x = re.sub(r"\s+", " ", x).strip()

            return x

        df["Nomor"] = df["Nomor"].apply(fix_nomor)

    # =========================
    # KONFIRMASI = JADWAL "-"
    # =========================
    if "Nomor" in df.columns:

        mask_konfirmasi = df["Nomor"].astype(str).str.contains(
            "Konfirmasi",
            case=False,
            na=False
        )

        if "Jadwal/Janji Kirim" in df.columns:
            df.loc[
                mask_konfirmasi,
                "Jadwal/Janji Kirim"
            ] = "-"

        if "Jadwal Selesai" in df.columns:
            df.loc[
                mask_konfirmasi,
                "Jadwal Selesai"
            ] = "-"

    # =========================
    # USER ID CLEAN
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

        if "User ID" in df.columns:
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
            id_member = str(row.get("ID Member", ""))

            is_special_id = (
                id_member.count("-") == 2
                and id_member != "nan"
            )

            # simpan row utama
            result.append(row.copy())

            # duplicate hanya jika special ID
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
