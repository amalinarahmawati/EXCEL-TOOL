import pandas as pd

def proses_jadwal_klinik(df):
    df.columns = df.columns.str.strip()

    if "tanggal" in df.columns:
        df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")

    return df


def proses_point_klinik(df):
    df.columns = df.columns.str.strip()

    if "tindakan" in df.columns:
        df["point"] = df["tindakan"].apply(lambda x: 10 if pd.notna(x) else 0)

    return df
