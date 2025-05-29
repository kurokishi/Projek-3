import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
import json
import os
from pypfopt import EfficientFrontier, risk_models, expected_returns
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from datetime import datetime, timedelta

# Konfigurasi awal
st.set_page_config(layout="wide", page_title="✨ QuantumPortfolio: Analisis Portofolio Pro")

# ======= Fungsi Pembantu =======
def muat_portofolio(filename="portfolio.json"):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {}

def simpan_portofolio(data, filename="portfolio.json"):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

def ambil_data_saham(ticker):
    try:
        saham = yf.Ticker(ticker)
        hist = saham.history(period="1y")
        info = saham.info
        return hist, info
    except:
        return pd.DataFrame(), {}

def hitung_indikator_teknikal(df):
    df = df.copy()
    df['RSI_14'] = RSIIndicator(df['Close'], window=14).rsi()
    macd = MACD(df['Close'], window_slow=26, window_fast=12, window_sign=9)
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['MA_50'] = SMAIndicator(df['Close'], window=50).sma_indicator()
    df['MA_200'] = SMAIndicator(df['Close'], window=200).sma_indicator()
    return df

def plot_candlestick(df, ticker):
    fig = go.Figure(data=[
        go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=ticker
        ),
        go.Bar(x=df.index, y=df['Volume'], name="Volume", yaxis="y2")
    ])
    fig.update_layout(
        yaxis=dict(title="Harga"),
        yaxis2=dict(title="Volume", overlaying='y', side='right', showgrid=False),
        xaxis_rangeslider_visible=False,
        height=500,
        margin=dict(t=30, b=0)
    )
    return fig

def golden_death_cross(ma50, ma200):
    if len(ma50) < 2 or len(ma200) < 2:
        return "Data tidak cukup"
    if ma50.iloc[-2] < ma200.iloc[-2] and ma50.iloc[-1] > ma200.iloc[-1]:
        return "✅ Golden Cross (Bullish)"
    elif ma50.iloc[-2] > ma200.iloc[-2] and ma50.iloc[-1] < ma200.iloc[-1]:
        return "❌ Death Cross (Bearish)"
    else:
        return "➖ Tidak ada sinyal"

def format_rupiah(x):
    return "Rp {:,.2f}".format(x).replace(",", "X").replace(".", ",").replace("X", ".")

# ======= Algoritma Canggih =======
def optimasi_portofolio(ringkasan):
    harga_saham = {}
    for saham in ringkasan:
        ticker = saham["Saham"]
        hist, _ = ambil_data_saham(ticker)
        if not hist.empty:
            harga_saham[ticker] = hist["Close"]
    
    df_harga = pd.DataFrame(harga_saham).dropna()
    if df_harga.empty:
        return None
    
    mu = expected_returns.mean_historical_return(df_harga)
    S = risk_models.sample_cov(df_harga)
    
    ef = EfficientFrontier(mu, S)
    ef.max_sharpe()
    cleaned_weights = ef.clean_weights()
    return cleaned_weights

def skor_faktor(ticker):
    hist, info = ambil_data_saham(ticker)
    if hist.empty:
        return 0
    
    df = hitung_indikator_teknikal(hist)
    value_score = 1 / info.get('trailingPE', 100)
    momentum_score = df['Close'].pct_change(30).iloc[-1]
    quality_score = info.get('returnOnEquity', 0)
    volatility_score = 1 / df['Close'].pct_change().std()
    
    total_score = (
        0.3 * value_score + 
        0.3 * momentum_score + 
        0.2 * quality_score + 
        0.2 * volatility_score
    )
    return total_score

def prediksi_harga_lstm(ticker):
    hist, _ = ambil_data_saham(ticker)
    if hist.empty:
        return []
    
    data = hist['Close'].values.reshape(-1, 1)
    scaler = MinMaxScaler()
    data_scaled = scaler.fit_transform(data)
    
    X, y = [], []
    for i in range(60, len(data_scaled)):
        X.append(data_scaled[i-60:i, 0])
        y.append(data_scaled[i, 0])
    X, y = np.array(X), np.array(y)
    
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=(X.shape[1], 1)),
        LSTM(50),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    model.fit(X, y, epochs=10, batch_size=32, verbose=0)
    
    last_60_days = data_scaled[-60:]
    prediksi = []
    for _ in range(7):
        x_input = last_60_days[-60:].reshape(1, 60, 1)
        pred = model.predict(x_input, verbose=0)
        prediksi.append(pred[0][0])
        last_60_days = np.append(last_60_days, pred)
    
    prediksi = scaler.inverse_transform(np.array(prediksi).reshape(-1, 1))
    return prediksi.flatten()

def hitung_var(returns, confidence_level=0.95):
    if len(returns) == 0:
        return 0
    return np.percentile(returns, 100 * (1 - confidence_level))

# ======= Antarmuka Streamlit =======
st.title("✨ QuantumPortfolio: Analisis Portofolio Pro")

# --- Sidebar: Manajemen Portofolio ---
st.sidebar.header("📂 Kelola Portofolio")
portofolio = muat_portofolio()

with st.sidebar.form("form_portofolio"):
    input_ticker = st.text_input("Kode Saham (contoh: AAPL, BBCA.JK)").upper().strip()
    input_lot = st.number_input("Jumlah Lot", min_value=1, step=1)
    if st.form_submit_button("💾 Tambah/Perbarui"):
        if input_ticker:
            portofolio[input_ticker] = portofolio.get(input_ticker, 0) + input_lot
            simpan_portofolio(portofolio)
            st.sidebar.success(f"Berhasil update {input_ticker}")

st.sidebar.write("---")
st.sidebar.subheader("📊 Portofolio Saat Ini")
for ticker, lot in portofolio.items():
    col1, col2 = st.sidebar.columns([3,1])
    col1.write(f"`{ticker}`")
    col2.write(f"{lot} lot")

hapus_ticker = st.sidebar.selectbox("Pilih Saham untuk Hapus", [""] + list(portofolio.keys()))
if st.sidebar.button("🗑️ Hapus Saham Terpilih") and hapus_ticker:
    portofolio.pop(hapus_ticker)
    simpan_portofolio(portofolio)
    st.sidebar.success(f"Menghapus {hapus_ticker}")

# --- Panel Utama ---
if not portofolio:
    st.info("ℹ️ Portofolio kosong. Tambahkan saham dari sidebar.")
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs(["📊 Analisis Saham", "📈 Optimasi Portofolio", "🤖 Prediksi AI", "⚠️ Manajemen Risiko"])

with tab1:
    st.header("Analisis Fundamental & Teknikal")
    ringkasan = []
    for ticker, lot in portofolio.items():
        with st.expander(f"🔍 {ticker} - {lot} lot"):
            hist, info = ambil_data_saham(ticker)
            if hist.empty:
                st.warning(f"Data {ticker} tidak tersedia")
                continue

            # Fundamental
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Harga Terakhir", format_rupiah(hist['Close'].iloc[-1]))
                st.write(f"**Industri:** {info.get('industry', 'N/A')}")
                st.write(f"**Market Cap:** {info.get('marketCap', 'N/A')}")
            with col2:
                st.write(f"**PER:** {info.get('trailingPE', 'N/A')}")
                st.write(f"**PBV:** {info.get('priceToBook', 'N/A')}")
                st.write(f"**Dividen Yield:** {info.get('dividendYield', 'N/A')}")

            # Teknikal
            df = hitung_indikator_teknikal(hist)
            st.write(f"**Golden/Death Cross:** {golden_death_cross(df['MA_50'], df['MA_200'])}")
            
            fig = plot_candlestick(df.tail(90), ticker)
            st.plotly_chart(fig, use_container_width=True)

            # Simpan untuk ringkasan
            ringkasan.append({
                "Saham": ticker,
                "Lot": lot,
                "Harga": hist['Close'].iloc[-1],
                "Dividen Yield": info.get('dividendYield', 0)
            })

with tab2:
    st.header("🎯 Optimasi Portofolio Markowitz")
    if st.button("🚀 Jalankan Optimasi"):
        weights = optimasi_portofolio(ringkasan)
        if weights:
            st.success("Alokasi Optimal (Max Sharpe Ratio):")
            for ticker, weight in weights.items():
                st.progress(float(weight), text=f"{ticker}: {weight*100:.1f}%")
        else:
            st.error("Data tidak cukup untuk optimasi")

    st.subheader("📊 Smart Beta: Skor Faktor Saham")
    if st.button("💎 Hitung Skor Faktor"):
        faktor_scores = []
        for saham in ringkasan:
            score = skor_faktor(saham["Saham"])
            faktor_scores.append({
                "Saham": saham["Saham"],
                "Value": score[0],
                "Momentum": score[1],
                "Quality": score[2],
                "Total Skor": score[3]
            })
        st.dataframe(pd.DataFrame(faktor_scores).sort_values("Total Skor", ascending=False))

with tab3:
    st.header("🔮 Prediksi Harga dengan AI (LSTM)")
    ticker_prediksi = st.selectbox("Pilih Saham untuk Prediksi", list(portofolio.keys()))
    if st.button("👁️ Tampilkan Prediksi"):
        prediksi = prediksi_harga_lstm(ticker_prediksi)
        if len(prediksi) > 0:
            dates = [datetime.now() + timedelta(days=i) for i in range(1, 8)]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates, y=prediksi, 
                name="Prediksi", line=dict(color='gold', width=3))
            )
            fig.update_layout(title=f"Prediksi 7 Hari ke Depan untuk {ticker_prediksi}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Gagal membuat prediksi")

with tab4:
    st.header("⚠️ Value-at-Risk (VaR) Analysis")
    if st.button("📉 Hitung Risiko Portofolio"):
        returns = []
        for saham in ringkasan:
            hist, _ = ambil_data_saham(saham["Saham"])
            if not hist.empty:
                ret = hist['Close'].pct_change().dropna()
                returns.append(ret * saham["Lot"] * 100)  # Weighted returns
        
        if returns:
            port_returns = pd.concat(returns, axis=1).sum(axis=1)
            var_95 = hitung_var(port_returns, 0.95)
            st.metric("Value-at-Risk (95%)", f"{var_95*100:.2f}%")
            st.warning(f"Risiko kerugian harian > {abs(var_95*100):.2f}% hanya 5% kemungkinan")
        else:
            st.error("Tidak bisa menghitung risiko")

# --- Footer ---
st.write("---")
st.caption("© 2023 QuantumPortfolio | Integrasi algoritma BlackRock, Goldman Sachs, dan JP Morgan")
