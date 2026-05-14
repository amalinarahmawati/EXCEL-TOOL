from pathlib import Path
import pandas as pd

# lokasi file ini (utils/)
BASE_DIR = Path(__file__).resolve().parent

# naik 1 level ke root project
ROOT_DIR = BASE_DIR.parent

DATA_PATH = ROOT_DIR / "data" / "holiday.csv"


def load_holidays():
    try:
        df = pd.read_csv(DATA_PATH)
        return df
    except FileNotFoundError:
        raise FileNotFoundError(
            f"holiday.csv tidak ditemukan di: {DATA_PATH}"
        )
