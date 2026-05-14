from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

# lokasi file utils/
BASE_DIR = Path(__file__).resolve().parent

# root project
ROOT_DIR = BASE_DIR.parent

# path data holiday
DATA_PATH = ROOT_DIR / "data" / "holiday.csv"


def load_holidays():
    """
    Load data holiday dari file CSV
    """
    try:
        if not DATA_PATH.exists():
            raise FileNotFoundError

        df = pd.read_csv(DATA_PATH)
        return df

    except FileNotFoundError:
        raise FileNotFoundError(
            f"[ERROR] holiday.csv tidak ditemukan di: {DATA_PATH}"
        )


def next_working_day(date):
    """
    Mengembalikan hari kerja berikutnya (skip Sabtu & Minggu)
    """
    if isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d")

    next_day = date + timedelta(days=1)

    # skip weekend
    while next_day.weekday() >= 5:
        next_day += timedelta(days=1)

    return next_day.date()
