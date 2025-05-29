import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os

# ======= Error Handling untuk Dependency =======
DEPENDENCY_ERRORS = []

try:
    import yfinance as yf
except ImportError:
    DEPENDENCY_ERRORS.append("yfinance (pip install yfinance)")
    yf = None

try:
    from ta.momentum import RSIIndicator
    from ta.trend import MACD, SMAIndicator
except ImportError:
    DEPENDENCY_ERRORS.append("ta (pip install ta)")
    RSIIndicator, MACD, SMAIndicator = None, None, None

try:
    from pypfopt import EfficientFrontier, risk_models, expected_returns
    OPTIMIZATION_ENABLED = True
except ImportError:
    OPTIMIZATION_ENABLED = False
    DEPENDENCY_ERRORS.append("pypfopt (pip install pypfopt)")

try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense
    from sklearn.preprocessing import MinMaxScaler
    LSTM_ENABLED = True
except ImportError:
    LSTM_ENABLED = False
    DEPENDENCY_ERRORS.append("tensorflow/scikit-learn (pip install tensorflow scikit-learn)")

# ======= Fungsi dengan Error Handling =======
def muat_portofolio(filename="portfolio.json"):
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        st.error(f"Gagal memuat portofolio: {str(e)}")
        return {}

def simpan_portofolio(data, filename="portfolio.json"):
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        st.error(f"Gagal menyimpan portofolio: {str(e)}")

def ambil_data_saham(ticker):
    if yf is None:
        st.error("Library yfinance tidak tersedia!")
        return pd.DataFrame(), {}
    
    try:
        saham = yf.Ticker(ticker)
        hist = saham.history(period="1y")
        info = saham.info
        if hist.empty:
            st.warning(f"Data historis untuk {ticker} kosong!")
        return hist, info
    except Exception as e:
        st.error(f"Gagal mengambil data {ticker}: {str(e)}")
        return pd.DataFrame(), {}

def hitung_indikator_teknikal(df):
    if RSIIndicator is None or MACD is None or SMAIndicator is None:
        st.error("Library TA tidak tersedia!")
        return df
    
    try:
        df = df.copy()
        df['RSI_14'] = RSIIndicator(df['Close'], window=14).rsi()
        macd = MACD(df['Close'], window_slow=26, window_fast=12, window_sign=9)
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()
        df['MA_50'] = SMAIndicator(df['Close'], window=50).sma_indicator()
        df['MA_200'] = SMAIndicator(df['Close'], window=200).sma_indicator()
        return df
    except Exception as e:
        st.error(f"Gagal menghitung indikator: {str(e)}")
        return df

# ======= Antarmuka Streamlit =======
st.set_page_config(layout="wide", page_title="Analisis Portofolio Saham")

# Tampilkan warning dependency yang missing
if DEPENDENCY_ERRORS:
    st.warning(
        f"⚠️ Beberapa fitur dinonaktifkan karena dependency tidak terinstall: {', '.join(DEPENDENCY_ERRORS)}"
    )

# --- Sidebar ---
st.sidebar.header("Kelola Portofolio")
portofolio = muat_portofolio()

with st.sidebar.form("form_portofolio"):
    input_ticker = st.text_input("Kode Saham (contoh: AAPL, BBCA.JK)").upper().strip()
    input_lot = st.number_input("Jumlah Lot", min_value=1, step=1)
    if st.form_submit_button("Tambah/Perbarui") and input_ticker:
        portofolio[input_ticker] = portofolio.get(input_ticker, 0) + input_lot
        simpan_portofolio(portofolio)

# --- Main Content ---
if not portofolio:
    st.info("Portofolio kosong. Tambahkan saham dari sidebar.")
    st.stop()

# Tab utama
tab1, tab2, tab3 = st.tabs(["Analisis Saham", "Optimasi Portofolio", "Prediksi AI"])

with tab1:
    for ticker, lot in portofolio.items():
        with st.expander(f"{ticker} - {lot} lot"):
            hist, info = ambil_data_saham(ticker)
            if not hist.empty:
                df = hitung_indikator_teknikal(hist)
                st.plotly_chart(plot_candlestick(df.tail(90), ticker))

with tab2:
    if OPTIMIZATION_ENABLED:
        if st.button("Jalankan Optimasi"):
            try:
                weights = optimasi_portofolio(ringkasan)
                for ticker, weight in weights.items():
                    st.write(f"{ticker}: {weight*100:.1f}%")
            except Exception as e:
                st.error(f"Optimasi gagal: {str(e)}")
    else:
        st.error("Fitur optimasi membutuhkan library 'pypfopt'")

with tab3:
    if LSTM_ENABLED:
        ticker = st.selectbox("Pilih Saham", list(portofolio.keys()))
        if st.button("Prediksi Harga"):
            try:
                prediksi = prediksi_harga_lstm(ticker)
                # Tampilkan hasil prediksi
            except Exception as e:
                st.error(f"Prediksi gagal: {str(e)}")
    else:
        st.error("Fitur prediksi membutuhkan library 'tensorflow'")
