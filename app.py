import streamlit as st
from modules import data_loader, valuation

st.set_page_config(page_title="Smart Stock Dashboard", layout="wide")
st.title("📈 Aplikasi Analisis Saham")
st.sidebar.success("Menu berhasil dimuat.")

menu = st.sidebar.selectbox("Pilih Menu", ["📊 Portfolio Analysis", "📄 Tentang"])

if menu == "📊 Portfolio Analysis":
    st.header("📊 Portfolio Analysis")
    df = data_loader.load_portfolio_data()
    if df.empty:
        st.warning("Portofolio kosong.")
    else:
        st.dataframe(df)
        valuation.display_valuation(df)

elif menu == "📄 Tentang":
    st.markdown("Aplikasi analisis saham berbasis Streamlit. Dibuat oleh ChatGPT dan pengguna.")
