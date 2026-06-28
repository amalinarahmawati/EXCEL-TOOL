import streamlit as st
import pandas as pd
from io import BytesIO
import re

# ===== LAB =====
from logic.faktur import proses_faktur
from logic.mutasi import proses_mutasi
from logic.order import proses_order
from logic.redo import proses_redo
from logic.cabut_pending import proses_cabut_pending
from logic.order_dentcore import proses_order_dentcore
from logic.redo_dentcore import proses_redo_dentcore

# ===== KLINIK =====
from logic.klinik import proses_jadwal_klinik, proses_point_klinik


st.set_page_config(page_title="Olah data ke web", layout="wide")

st.title("📊 Processing System Data")

# ======================
# SIDEBAR
# ======================
st.sidebar.title("📂 Menu Sistem")

kategori = st.sidebar.radio(
    "Pilih Kategori",
    ["LAB", "KLINIK"]
)

menu = None

if kategori == "LAB":
    menu = st.sidebar.selectbox(
        "🧪 Modul LAB",
        [
            "Faktur",
            "Mutasi",
            "Order",
            "Redo",
            "Cabut Pending",
            "Order Dentcore",
            "Redo Dentcore"
        ]
    )

elif kategori == "KLINIK":
    menu = st.sidebar.selectbox(
        "🏥 Modul KLINIK",
        [
            "Jadwal Klinik",
            "Point Klinik"
        ]
    )


uploaded_file = st.file_uploader(
    "Upload Excel",
    type=["xls", "xlsx"]
)

# ======================
# MASTER FILE (UNTUK REDO SAJA)
# ======================
master_file = None

if menu in ["Redo", "Cabut Pending", "Redo Dentcore"]:
    st.subheader("📌 Upload Master Data (WAJIB)")
    master_file = st.file_uploader("Upload Master Excel", type=["xlsx", "xls"], key="master")

    if master_file is None:
        st.warning("⚠️ Kamu belum upload file master. User ID tidak bisa dibuat.")
        st.stop()


def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output
# ======================
# VALIDASI FILE
# ======================
def validasi_file(uploaded_file, menu):

    nama_file = uploaded_file.name.lower().strip()

    # ======================
    # HARUS FORMAT .XLS
    # ======================
    if nama_file.endswith(".xlsx"):
        st.error("""
❌ Format file tidak didukung!

Silakan gunakan file Excel tipe (*.xls)

File *.xlsx tidak dapat diproses.
""")
        st.stop()

    if not nama_file.endswith(".xls"):
        st.error("""
❌ Format file tidak dikenali!

Silakan upload file dengan format *.xls
""")
        st.stop()

    # ======================
    # VALIDASI NAMA FILE
    # ======================
    pola = {
        "Faktur": r"^(faktur|faktur dentcore)(\s+\d+)?\.xls$",
        "Mutasi": r"^mutasi(\s+\d+)?\.xls$",
        "Order": r"^order(\s+\d+)?\.xls$",
        "Redo": r"^redo(\s+\d+)?\.xls$",
        "Cabut Pending": r"^cabut pending(\s+\d+)?\.xls$",
        "Order Dentcore": r"^order dentcore(\s+\d+)?\.xls$",
        "Redo Dentcore": r"^redo dentcore(\s+\d+)?\.xls$",
        "Jadwal Klinik": r"^jadwal klinik(\s+\d+)?\.xls$",
        "Point Klinik": r"^point(\s+\d+)?\.xls$",
    }

    if menu in pola:
        if not re.match(pola[menu], nama_file):
            st.error(f"""
🚫 File yang dipilih tidak sesuai!

Menu yang dipilih :
➡️ {menu}

File yang diupload :
➡️ {uploaded_file.name}

Silakan upload file yang sesuai.
""")
            st.stop()

    # ======================
# VALIDASI MASTER FILE
# ======================
def validasi_master(master_file):

    nama_file = master_file.name.lower().strip()

    # master boleh xls atau xlsx
    if not (nama_file.endswith(".xls") or nama_file.endswith(".xlsx")):
        st.error("""
File master harus berupa Excel (.xls atau .xlsx).
""")
        st.stop()

    pola_master = r"^member user master\s*\d*\.xlsx?$"

    if not re.match(pola_master, nama_file):
        st.error(f"""
File Master tidak sesuai.

Nama file yang diperbolehkan:

• Member User Master.xlsx
• Member User Master2.xlsx
• Member User Master 3.xlsx

File yang dipilih:
{master_file.name}
""")
        st.stop()

    # ======================
# PROCESSING
# ======================
if uploaded_file:

    # validasi file utama
    validasi_file(uploaded_file, menu)

    # baca file utama
    df = pd.read_excel(uploaded_file)

    # baca master jika ada
    df_master = None
    if master_file:
        validasi_master(master_file)
        df_master = pd.read_excel(master_file)

    st.subheader(f"📌 Modul Aktif: {kategori} - {menu}")
    st.dataframe(df)

    if st.button("🚀 Proses Data"):

        with st.spinner("Memproses..."):

            # ===== LAB =====
            if kategori == "LAB":

                if menu == "Faktur":
                    df = proses_faktur(df)

                elif menu == "Mutasi":
                    df = proses_mutasi(df)

                elif menu == "Order":
                    df = proses_order(df)

                elif menu == "Redo":
                    df = proses_redo(df, df_master)

                elif menu == "Cabut Pending":
                    df = proses_cabut_pending(df, df_master)

                elif menu == "Order Dentcore":
                    df = proses_order_dentcore(df)

                elif menu == "Redo Dentcore":
                    df = proses_redo_dentcore(df, df_master)

            # ===== KLINIK =====
            elif kategori == "KLINIK":

                if menu == "Jadwal Klinik":
                    df = proses_jadwal_klinik(df)

                elif menu == "Point Klinik":
                    df = proses_point_klinik(df)

        st.success("✅ Selesai!")
        st.dataframe(df)

        st.download_button(
            "📥 Download Excel",
            to_excel(df),
            file_name=f"hasil_{kategori}_{menu}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
