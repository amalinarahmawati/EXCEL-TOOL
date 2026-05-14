import pandas as pd
import numpy as np


def proses_faktur(df):
    # =========================
    # 1. bersihin nama kolom
    # =========================
    df.columns = df.columns.str.strip()

    # =========================
    # 2. Isi tanggal kosong ke bawah
    # =========================
    if "Tanggal" in df.columns:
        df["Tanggal"] = df["Tanggal"].ffill()

    # buang total
    if "Nomor" in df.columns:
        df = df[~df["Nomor"].astype(str)
                .str.contains("Total", case=False, na=False)]

    # =========================
    # 3. Nilai Akumulasi handling
    # =========================
    if "Nilai Akumulasi" in df.columns:
        df["Nilai Akumulasi"] = ""

    # =========================
    # 4. Hapus produk tertentu
    # =========================
    if "Produk Gigi / Tambahan" in df.columns:
        df = df[
            ~df["Produk Gigi / Tambahan"].astype(str).str.contains(
                "unit pertama|tambah gigi",
                case=False,
                na=False
            )
        ]

    # =========================
    # 5. Hapus kolom tidak dibutuhkan
    # =========================
    hapus_kolom = [
        "Pembuat",
        "Customer",
        "Kota",
        "Nominal Produk Tambahan",
        "Produk Tambahan",
        "No order",
        "No resi",
        "Status Print Faktur"
    ]

    df = df.drop(
        columns=[col for col in hapus_kolom if col in df.columns],
        errors="ignore"
    )

    # =========================
    # reset strip lagi
    # =========================
    df.columns = df.columns.str.strip()

    # =========================
    # isi nomor kosong
    # =========================
    if "Nomor" in df.columns:
        df["Nomor"] = df["Nomor"].ffill()
        df["Nomor"] = df["Nomor"].astype(str).str.strip()

    # =========================
    # AGGREGATION
    # =========================
    agg_dict = {}

    for col in df.columns:

        if col == "Produk Gigi / Tambahan":
            agg_dict[col] = lambda x: ", ".join(x.dropna().astype(str))

        elif col == "Regio":
            agg_dict[col] = lambda x: ", ".join(x.dropna().astype(str))

        elif col == "Qty Gigi":
            agg_dict[col] = "sum"

        else:
            agg_dict[col] = "first"

    if "Nomor" in df.columns:
        df_final = df.groupby("Nomor", as_index=False).agg(agg_dict)
    else:
        df_final = df.copy()

    # =========================
    # CLEAN USER ID & MEMBER
    # =========================
    if "User ID" in df_final.columns:
        df_final["User ID"] = df_final["User ID"].replace(
            ["nan", "", "None", "-", " "], pd.NA
        )

    if "ID Member" in df_final.columns:
        df_final["ID Member"] = df_final["ID Member"].replace(
            ["nan", "", "None", " "], pd.NA
        )
        df_final["User ID"] = df_final["User ID"].fillna(df_final["ID Member"])

    # =========================
    # DUPLICATE LOGIC FIX
    # =========================
    if "User ID" in df_final.columns and "ID Member" in df_final.columns:

        result = []

        for _, row in df_final.iterrows():

            user_id = row.get("User ID")
            id_member = str(row.get("ID Member", ""))

            is_special_id = id_member.count("-") == 2 and id_member != "nan"

            if pd.isna(user_id):
                result.append(row.copy())
            else:
                result.append(row.copy())

                if is_special_id and user_id != id_member:
                    new_row = row.copy()
                    new_row["User ID"] = id_member
                    result.append(new_row)

        df_final = pd.DataFrame(result)

        df_final = df_final.drop(columns=["ID Member"], errors="ignore")

    # =========================
    # POSISI KOLOM PASIEN
    # =========================
    cols = list(df_final.columns)

    if "Pasien" in cols and "User ID" in cols:
        cols.remove("Pasien")
        cols.insert(cols.index("User ID"), "Pasien")
        df_final = df_final[cols]

    # =========================
    # Dokter ke akhir
    # =========================
    if "Dokter" in df_final.columns:
        cols = list(df_final.columns)
        cols.remove("Dokter")
        cols.append("Dokter")
        df_final = df_final[cols]

    # =========================
    # FORMAT RESI
    # =========================
    if "No Resi" in df_final.columns and "Ekspedisi" in df_final.columns:

        def format_resi(row):

            ekspedisi = str(row.get("Ekspedisi", "")).strip()
            resi = row.get("No Resi")

            if pd.isna(resi):
                return ""

            resi = str(resi).strip()

            if resi == "" or resi.lower() in ["nan", "none"]:
                return ""

            if ekspedisi == "JNE - B":
                return "0" + resi

            return resi

        df_final["No Resi"] = df_final.apply(format_resi, axis=1)

    # =========================
    # CLEAN NUMERIC
    # =========================
    kolom_cek = [
        "Qty Prd. Tambahan",
        "Harga",
        "Nominal Gigi",
        "Sub Total",
        "Disc",
        "DPP",
        "Ongkos Kirim",
        "Total"
    ]

    kolom_cek = [col for col in kolom_cek if col in df_final.columns]

    if kolom_cek:
        df_final[kolom_cek] = df_final[kolom_cek].apply(
            lambda x: pd.to_numeric(
                x.astype(str)
                .str.replace(",", "")
                .str.strip(),
                errors="coerce"
            ).fillna(0)
        )

        before = len(df_final)

        df_final = df_final[df_final[kolom_cek].sum(axis=1) != 0]

        after = len(df_final)

        print(f"Total sebelum: {before}")
        print(f"Total sesudah: {after}")

    return df_final