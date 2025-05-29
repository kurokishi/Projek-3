import streamlit as st
import sys
import os
import json
import traceback
from datetime import datetime

# ======== Konfigurasi Awal ========
st.set_page_config(layout="wide", page_title="Analisis Portofolio Saham")

# ======== System Check ========
st.sidebar.write(f"Python version: {sys.version.split()[0]}")

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
    st.sidebar.error("⚠️ yfinance tidak terinstall")

try:
    from ta.momentum import RSIIndicator
    from ta.trend import MACD, SMAIndicator
    TA_ENABLED = True
except ImportError:
    RSIIndicator = MACD = SMAIndicator = DummyModule()
    TA_ENABLED = False
    st.sidebar.error("⚠️ Library TA tidak terinstall")

try:
    from pypfopt import EfficientFrontier, risk_models, expected_returns
    OPTIMIZATION_ENABLED = True
except ImportError:
    OPTIMIZATION_ENABLED = False
    st.sidebar.error("⚠️ PyPortfolioOpt tidak terinstall")

try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense
    from sklearn.preprocessing import MinMaxScaler
    LSTM_ENABLED = True
except ImportError:
    LSTM_ENABLED = False
    st.sidebar.error("⚠️ TensorFlow tidak terinstall")

# ======== Fungsi dengan Error Handling ========
def muat_portofolio(filename="portfolio.json"):
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        st.error(f"❌ Gagal memuat portofolio: {str(e)}")
        st.code(traceback.format_exc())
        return {}

def simpan_portofolio(data, filename="portfolio.json"):
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        st.error(f"❌ Gagal menyimpan portofolio: {str(e)}")

def ambil_data_saham(ticker):
    if not YFINANCE_ENABLED:
        return pd.DataFrame(), {}
    
    try:
        saham = yf.Ticker(ticker)
        hist = saham.history(period="1y")
        info = saham.info
        return hist, info
    except Exception as e:
        st.error(f"❌ Gagal mengambil data {ticker}")
        st.code(traceback.format_exc())
        return pd.DataFrame(), {}

def hitung_indikator_teknikal(df):
    if not TA_ENABLED:
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
        st.error("❌ Gagal menghitung indikator teknikal")
        st.code(traceback.format_exc())
        return df

# ======== Main App ========
def main():
    st.title("📊 Aplikasi Analisis Portofolio Saham")
    
    # Status Dependency
    with st.expander("ℹ️ Status Sistem"):
        st.write(f"**yfinance:** {'✅' if YFINANCE_ENABLED else '❌'}")
        st.write(f"**Technical Analysis:** {'✅' if TA_ENABLED else '❌'}")
        st.write(f"**Portfolio Optimization:** {'✅' if OPTIMIZATION_ENABLED else '❌'}")
        st.write(f"**LSTM Prediction:** {'✅' if LSTM_ENABLED else '❌'}")
    
    # Manajemen Portofolio
    st.sidebar.header("Manajemen Portofolio")
    portofolio = muat_portofolio()
    
    with st.sidebar.form("tambah_saham"):
        ticker = st.text_input("Kode Saham").upper().strip()
        lot = st.number_input("Jumlah Lot", min_value=1)
        if st.form_submit_button("Tambah"):
            if ticker:
                portofolio[ticker] = portofolio.get(ticker, 0) + lot
                simpan_portofolio(portofolio)
    
    # Tampilkan Portofolio
    st.header("Portofolio Saat Ini")
    if not portofolio:
        st.info("Belum ada saham dalam portofolio")
        return
    
    for ticker, lot in portofolio.items():
        with st.expander(f"{ticker} ({lot} lot)"):
            if not YFINANCE_ENABLED:
                st.error("yfinance tidak tersedia untuk mengambil data")
                continue
                
            hist, info = ambil_data_saham(ticker)
            if hist.empty:
                st.warning(f"Data historis {ticker} tidak tersedia")
                continue
                
            df = hitung_indikator_teknikal(hist)
            st.line_chart(df['Close'])
            
            if TA_ENABLED:
                st.write(f"RSI Terakhir: {df['RSI_14'].iloc[-1]:.2f}")
                st.write(f"MACD Terakhir: {df['MACD'].iloc[-1]:.2f}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("❌ Aplikasi mengalami error yang tidak terduga")
        st.code(traceback.format_exc())
