import streamlit as st
import sys
import os
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ======== Konfigurasi Awal ========
st.set_page_config(layout="wide", page_title="Analisis Portofolio Saham")

# ======== System Check ========
python_version = sys.version.split()[0]
st.sidebar.write(f"Python version: {python_version}")

# ======== Dependency Fallbacks ========
class DummyModule:
    def __call__(self, *args, **kwargs):
        st.error("Fitur dinonaktifkan: Dependency tidak tersedia")
        return None
    def __getattr__(self, name):
        return self

# Setup fallbacks
try:
    import yfinance as yf
    YFINANCE_ENABLED = True
except ImportError:
    yf = DummyModule()
    YFINANCE_ENABLED = False

try:
    from ta.momentum import RSIIndicator
    from ta.trend import MACD, SMAIndicator
    TA_ENABLED = True
except ImportError:
    RSIIndicator = MACD = SMAIndicator = DummyModule()
    TA_ENABLED = False

try:
    from pypfopt import EfficientFrontier, risk_models, expected_returns
    OPTIMIZATION_ENABLED = True
except ImportError:
    OPTIMIZATION_ENABLED = False

try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense
    from sklearn.preprocessing import MinMaxScaler
    LSTM_ENABLED = True
except ImportError:
    LSTM_ENABLED = False

# ======== Fungsi Utama ========
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
    if not YFINANCE_ENABLED:
        st.error("yfinance tidak tersedia!")
        return pd.DataFrame(), {}
    
    try:
        saham = yf.Ticker(ticker)
        hist = saham.history(period="1y")
        info = saham.info
        return hist, info
    except Exception as e:
        st.error(f"Gagal mengambil data {ticker}: {str(e)}")
        return pd.DataFrame(), {}

def hitung_indikator_teknikal(df):
    if not TA_ENABLED:
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

def plot_candlestick(df, ticker):
    fig = go.Figure(data=[
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name=ticker
        )
    ])
    fig.update_layout(
        title=f"Harga {ticker}",
        xaxis_rangeslider_visible=False,
        height=500
    )
    return fig

# ======== Antarmuka Aplikasi ========
def main():
    st.title("📊 Aplikasi Analisis Portofolio Saham")
    
    # Sidebar - Manajemen Portofolio
    st.sidebar.header("Manajemen Portofolio")
    portofolio = muat_portofolio()
    
    with st.sidebar.form("form_portofolio"):
        input_ticker = st.text_input("Kode Saham (contoh: AAPL, BBCA.JK)").upper().strip()
        input_lot = st.number_input("Jumlah Lot", min_value=1, step=1)
        if st.form_submit_button("Tambah/Perbarui"):
            if input_ticker:
                portofolio[input_ticker] = portofolio.get(input_ticker, 0) + input_lot
                simpan_portofolio(portofolio)
                st.sidebar.success(f"Berhasil update {input_ticker}")
    
    # Status Sistem
    with st.expander("ℹ️ Status Sistem", expanded=True):
        col1, col2 = st.columns(2)
        col1.write(f"**yfinance:** {'✅' if YFINANCE_ENABLED else '❌'}")
        col1.write(f"**Technical Analysis:** {'✅' if TA_ENABLED else '❌'}")
        col2.write(f"**Portfolio Optimization:** {'✅' if OPTIMIZATION_ENABLED else '❌'}")
        col2.write(f"**LSTM Prediction:** {'✅' if LSTM_ENABLED else '❌'}")
        
        if not OPTIMIZATION_ENABLED:
            st.warning("Fitur optimasi portofolio tidak tersedia (pypfopt tidak terinstall)")
        if not LSTM_ENABLED:
            st.warning("Fitur prediksi tidak tersedia (tensorflow tidak terinstall)")
    
    # Konten Utama
    st.header("Portofolio Saat Ini")
    
    if not portofolio:
        st.info("Belum ada saham dalam portofolio. Silakan tambahkan saham dari sidebar.")
        return
    
    for ticker, lot in portofolio.items():
        with st.expander(f"{ticker} - {lot} lot", expanded=True):
            if not YFINANCE_ENABLED:
                st.error("Tidak bisa mengambil data: yfinance tidak tersedia")
                continue
                
            hist, info = ambil_data_saham(ticker)
            if hist.empty:
                st.warning(f"Data historis untuk {ticker} tidak tersedia")
                continue
                
            # Tampilkan data fundamental
            st.subheader("Data Fundamental")
            col1, col2 = st.columns(2)
            col1.metric("Harga Terakhir", f"${hist['Close'].iloc[-1]:.2f}" if 'Close' in hist else "N/A")
            
            if info:
                col2.metric("Market Cap", f"${info.get('marketCap', 'N/A'):,}" if 'marketCap' in info else "N/A")
                st.write(f"**Sektor:** {info.get('sector', 'N/A')}")
                st.write(f"**Industri:** {info.get('industry', 'N/A')}")
                st.write(f"**PER:** {info.get('trailingPE', 'N/A')}")
                st.write(f"**Dividen Yield:** {info.get('dividendYield', 'N/A')}")
            
            # Tampilkan grafik candlestick
            st.subheader("Grafik Harga")
            fig = plot_candlestick(hist.tail(60), ticker)
            st.plotly_chart(fig, use_container_width=True)
            
            # Tampilkan indikator teknikal jika tersedia
            if TA_ENABLED:
                st.subheader("Indikator Teknikal")
                df_teknikal = hitung_indikator_teknikal(hist)
                
                if not df_teknikal.empty:
                    col1, col2 = st.columns(2)
                    col1.line_chart(df_teknikal[['RSI_14']], height=300)
                    col2.line_chart(df_teknikal[['MACD', 'MACD_signal']], height=300)

if __name__ == "__main__":
    main()
