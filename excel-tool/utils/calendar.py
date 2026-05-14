import pandas as pd
from datetime import timedelta

def load_holidays(path="data/holiday.csv"):
    df = pd.read_csv(path)
    return pd.to_datetime(df["date"]).tolist()


def next_working_day(date, holidays):
    if pd.isna(date):
        return pd.NaT

    date = date + timedelta(days=1)

    while date.weekday() == 6 or date in holidays:
        date = date + timedelta(days=1)

    return date