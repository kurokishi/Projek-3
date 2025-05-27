import streamlit as st
from modules import (
    data_loader, valuation, technicals, ai_commentary, add_funds, indicator,
    portfolio_crud, compound_simulation, sentiment_analysis, risk_analysis,
    auto_rebalancer, multi_portfolio, price_prediction, notifikasi, tax_fee
)

# Setup halaman
st.set_page_config(page_title="Smart Stock Dashboard", layout="wide")
st.title("📈 Smart Stock Dashboard")
st.sidebar.title("📊 Navigasi")

# Menu
menu = st.sidebar.selectbox("Pilih Fitur", [
    "📊 Portfolio Analysis",
    "➕ Add Funds Strategy",
    "📈 Compound Growth Simulation",
    "⚠️ Sell/Hold Indicators",
    "📌 Portfolio Management",
    "📰 Sentiment & News",
    "📉 Risk Analysis",
    "⚖️ Auto-Rebalancing",
    "🔀 Compare Portfolios",
    "🤖 Price Prediction",
    "🔔 Notifikasi",
    "🧾 Tax & Fee Calculator",
    "❓ Tentang"
])

# Load data portofolio
portfolio_df = data_loader.load_portfolio_data()

# Routing antar fitur
if menu == "📊 Portfolio Analysis":
    st.header("📊 Analisis Portofolio")
    if portfolio_df.empty:
        st.warning("Portofolio kosong. Tambahkan saham terlebih dahulu.")
    else:
        st.dataframe(portfolio_df)
        valuation.display_valuation(portfolio_df)
        technicals.display_technical(portfolio_df)
        ai_commentary.generate_commentary(portfolio_df)

elif menu == "➕ Add Funds Strategy":
    st.header("➕ Strategi Alokasi Modal Baru")
    add_funds.display_add_funds_interface(portfolio_df)

elif menu == "📈 Compound Growth Simulation":
    st.header("📈 Simulasi Pertumbuhan Bunga Majemuk")
    compound_simulation.run_simulation(portfolio_df)

elif menu == "⚠️ Sell/Hold Indicators":
    st.header("⚠️ Rekomendasi Jual / Tahan")
    indicator.display_sell_hold(portfolio_df)

elif menu == "📌 Portfolio Management":
    st.header("📌 Tambah / Hapus Saham")
    portfolio_crud.manage_portfolio()

elif menu == "📰 Sentiment & News":
    st.header("📰 Analisis Sentimen dan Berita Saham")
    sentiment_analysis.display_sentiment(portfolio_df["ticker"].tolist())

elif menu == "📉 Risk Analysis":
    st.header("📉 Manajemen Risiko dan Stress Test")
    risk_analysis.run_risk_analysis(portfolio_df)

elif menu == "⚖️ Auto-Rebalancing":
    st.header("⚖️ Rekomendasi Rebalancing Otomatis")
    auto_rebalancer.rebalance_portfolio(portfolio_df)

elif menu == "🔀 Compare Portfolios":
    st.header("🔀 Perbandingan Multi-Portofolio")
    multi_portfolio.compare_multiple_portfolios()

elif menu == "🤖 Price Prediction":
    st.header("🤖 Prediksi Harga Saham (AI - LSTM)")
    try:
        price_prediction.predict_price(portfolio_df["ticker"].tolist())
    except:
        st.warning("Modul prediksi harga belum aktif atau error.")

elif menu == "🔔 Notifikasi":
    st.header("🔔 Notifikasi Penting Saham")
    tickers = portfolio_df["ticker"].tolist()
    target_prices = {t: 10000 for t in tickers}  # contoh target
    notifs = notifikasi.run_notifikasi(tickers, target_prices)
    for note in notifs:
        st.info(note)

elif menu == "🧾 Tax & Fee Calculator":
    st.header("🧾 Kalkulator Pajak & Biaya Transaksi")
    col1, col2 = st.columns(2)
    with col1:
        ticker = st.selectbox("Pilih Saham", portfolio_df["ticker"].tolist())
        jumlah = st.number_input("Jumlah Saham", 1, 10000, 100)
        harga = st.number_input("Harga/Lembar", 100, 20000, 8000)
    with col2:
        dividen = st.number_input("Dividen/Lembar", 0.0, 1000.0, 300.0)
    biaya = tax_fee.hitung_biaya_transaksi(jumlah, harga)
    yield_bersih = tax_fee.dividend_yield_after_tax(dividen, harga)
    st.metric("Biaya Transaksi", f"Rp {biaya:,.0f}")
    st.metric("Dividend Yield Setelah Pajak", f"{yield_bersih:.2f} %")

elif menu == "❓ Tentang":
    st.subheader("Tentang Aplikasi")
    st.markdown("""
    Aplikasi ini membantu Anda menganalisis portofolio saham pribadi secara menyeluruh:
    - Valuasi fundamental dan teknikal
    - Strategi tambah modal & bunga majemuk
    - Rebalancing, notifikasi, simulasi AI

    Dibuat dengan ❤️ menggunakan Python + Streamlit.
    """)

