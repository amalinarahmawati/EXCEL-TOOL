import pandas as pd

def proses_jadwal_klinik(df):
    df.columns = df.columns.str.strip()

    # =========================
    # 1. HAPUS KOLOM ALAMAT
    # =========================
    if "Alamat" in df.columns:
        df = df.drop(columns=["Alamat"])

    # =========================
    # 2. HAPUS DATA TANPA NO KARTU
    # =========================
    if "No Kartu" in df.columns:
        df = df[df["No Kartu"].notna()]
        df = df[df["No Kartu"].astype(str).str.strip() != ""]

    return df


def proses_point_klinik(df):
    df.columns = df.columns.str.strip()

    # =========================
    # 1. HAPUS KOLOM KODE PASIEN
    # =========================
    if "Kode Pasien" in df.columns:
        df = df.drop(columns=["Kode Pasien"])

    # =========================
    # 2. HAPUS DATA TANPA NO KARTU
    # =========================
    if "No Kartu" in df.columns:
        df = df[df["No Kartu"].notna()]
        df = df[df["No Kartu"].astype(str).str.strip() != ""]

    return df
