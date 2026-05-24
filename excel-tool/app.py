import streamlit as st
import pandas as pd
from io import BytesIO

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


uploaded_file = st.file_uploader("Upload Excel", type=["xlsx", "xls"])

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
# PROCESSING
# ======================
if uploaded_file:

    df = pd.read_excel(uploaded_file)

    # load master kalau ada
    df_master = None
    if master_file:
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
                    df = proses_redo(df, df_master)  # <-- penting

                elif menu == "Cabut Pending":
                    df = proses_cabut_pending(df)

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

        st.success("Selesai!")
        st.dataframe(df)

        st.download_button(
            "Download Excel",
            to_excel(df),
            file_name=f"hasil_{kategori}_{menu}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
