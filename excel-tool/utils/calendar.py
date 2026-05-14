from pathlib import Path
import pandas as pd

# ambil lokasi file ini
BASE_DIR = Path(__file__).resolve().parent.parent

# arahkan ke file data/holiday.csv
DATA_PATH = BASE_DIR / "data" / "holiday.csv"


def load_holidays():
    try:
        df = pd.read_csv(DATA_PATH)
        return df
    except FileNotFoundError:
        raise FileNotFoundError(
            f"File tidak ditemukan di path: {DATA_PATH}. "
            "Pastikan file holiday.csv ada di folder data/"
        )
