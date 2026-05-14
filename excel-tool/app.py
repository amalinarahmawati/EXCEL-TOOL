import streamlit as st
import pandas as pd
from io import BytesIO

from logic.faktur import proses_faktur
from logic.mutasi import proses_mutasi
from logic.order import proses_order
from logic.redo import proses_redo
from logic.cabut_pending import proses_cabut_pending
from logic.order_dentcore import proses_order_dentcore
from logic.redo_dentcore import proses_redo_dentcore

st.set_page_config(page_title="Olah data ke web", layout="wide")

st.title("📊Processing System data")

menu = st.sidebar.selectbox(
    "📂 Pilih Modul",
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

uploaded_file = st.file_uploader("Upload Excel", type=["xlsx", "xls"])


def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output


if uploaded_file:

    df = pd.read_excel(uploaded_file)

    st.subheader(f"📌 Modul Aktif: {menu}")
    st.dataframe(df)

    if st.button("🚀 Proses Data"):

        with st.spinner("Memproses..."):

            if menu == "Faktur":
                df = proses_faktur(df)

            elif menu == "Mutasi":
                df = proses_mutasi(df)

            elif menu == "Order":
                df = proses_order(df)

            elif menu == "Redo":
                df = proses_redo(df)

            elif menu == "Cabut Pending":
                df = proses_cabut_pending(df)

            elif menu == "Order Dentcore":
                df = proses_order_dentcore(df)

            elif menu == "Redo Dentcore":
                df = proses_redo_dentcore(df)

        st.success("Selesai!")

        st.dataframe(df)

        st.download_button(
            "Download Excel",
            to_excel(df),
            file_name=f"hasil_{menu}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )