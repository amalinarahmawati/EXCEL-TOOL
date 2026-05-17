import pandas as pd
from datetime import timedelta


def load_holidays(path="data/holiday.csv"):
    df = pd.read_csv(path)

    # ubah jadi set of date (bukan datetime)
    holidays = set(
        pd.to_datetime(df["date"], errors="coerce")
        .dt.date
        .dropna()
    )

    return holidays


def next_working_day(tanggal, holidays):
    if pd.isna(tanggal):
        return pd.NaT

    # paksa jadi date
    tanggal = pd.to_datetime(
        tanggal,
        errors="coerce"
    )

    if pd.isna(tanggal):
        return pd.NaT

    tanggal = tanggal.date()

    # H+1 dulu
    tanggal = tanggal + timedelta(days=1)

    # skip Minggu + tanggal merah
    while (
        tanggal.weekday() == 6
        or tanggal in holidays
    ):
        tanggal = tanggal + timedelta(days=1)

    return pd.to_datetime(tanggal)
