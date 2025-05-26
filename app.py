# Aplikasi utama Streamlit
import streamlit as st
from modules import (
    data_loader, portfolio_analysis, valuation, technicals, ai_commentary, add_funds, indicator,
    portfolio_crud, compound_simulation, sentiment, risk_analyst, auto_rebalance,
    multi_portfolio, price_prediction, notifikasi, tax_fee
)

st.sidebar.title("Smart Stock Dashboard")
menu = st.sidebar.selectbox("Pilih Menu", [
    "📊 Portfolio Analysis", "➕ Add Funds Strategy", "📈 Compound Growth Simulation",
    "⚠️ Sell/Hold Indicators", "📌 Portfolio Management", "📰 Sentiment & News",
    "📉 Risk Analysis", "⚖️ Auto-Rebalancing", "🔀 Compare Portfolios",
    "🤖 Price Prediction", "🔔 Notifikasi", "🧾 Tax & Fee Calculator"
])

tickers = st.session_state.get("portfolio_tickers", ["BBCA.JK", "TLKM.JK", "SIDO.JK"])
lots = st.session_state.get("portfolio_lots", [10, 20, 15])

if menu == "📊 Portfolio Analysis":
    st.header("Portfolio Analysis")
    df = data_loader.load_portfolio(tickers, lots)
    st.dataframe(df)
    valuation.display_valuation(df)
    technicals.display_technical(df)
    ai_commentary.generate_commentary(df)

elif menu == "➕ Add Funds Strategy":
    st.header("Rekomendasi Alokasi Modal Baru")
    add_funds.display_add_funds_interface(df)

elif menu == "📈 Compound Growth Simulation":
    st.header("Simulasi Pertumbuhan Bunga Majemuk")
    compound_simulation.run_simulation(df)

elif menu == "⚠️ Sell/Hold Indicators":
    st.header("Indikator Jual/Tahan")
    indicator.display_sell_hold(df)

elif menu == "📌 Portfolio Management":
    st.header("Manajemen Portofolio")
    portfolio_crud.manage_portfolio()

elif menu == "📰 Sentiment & News":
    st.header("Sentiment Analysis & Berita")
    sentiment.display_sentiment(tickers)

elif menu == "📉 Risk Analysis":
    st.header("Risk Management & Stress Test")
    risk_analyst.run_risk_analysis(df)

elif menu == "⚖️ Auto-Rebalancing":
    st.header("Rekomendasi Auto Rebalancing")
    auto_rebalance.rebalance_portfolio(df)

elif menu == "🔀 Compare Portfolios":
    st.header("Bandingkan Beberapa Portofolio")
    multi_portfolio.compare_multiple_portfolios()

elif menu == "🤖 Price Prediction":
    st.header("Prediksi Harga Saham (AI)")
    price_prediction.predict_price(tickers)

elif menu == "🔔 Notifikasi":
    st.header("Notifikasi Saham")
    target_prices = {"BBCA.JK": 9500, "SIDO.JK": 970}
    notes = notifikasi.run_notifikasi(tickers, target_prices)
    for n in notes:
        st.warning(n)

elif menu == "🧾 Tax & Fee Calculator":
    st.header("Kalkulator Pajak & Fee")
    col1, col2 = st.columns(2)
    with col1:
        saham = st.selectbox("Pilih Saham", tickers)
        jumlah = st.number_input("Jumlah Saham", 1, 10000, 100)
        harga = st.number_input("Harga per Lembar", 100, 20000, 8000)
    with col2:
        dividen = st.number_input("Dividen per Saham", 0.0, 1000.0, 300.0)
    biaya = tax_fee.hitung_biaya_transaksi(jumlah, harga)
    yield_after = tax_fee.dividend_yield_after_tax(dividen, harga)
    st.info(f"Biaya Transaksi: Rp{biaya:,.0f}")
    st.success(f"Dividend Yield Setelah Pajak: {yield_after:.2f}%")
