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
    st.sidebar.error("⚠️ yfinance tidak terinstall (pip install yfinance)")

try:
    from ta.momentum import RSIIndicator
    from ta.trend import MACD, SMAIndicator
    TA_ENABLED = True
except ImportError:
    RSIIndicator = MACD = SMAIndicator = DummyModule()
    TA_ENABLED = False
    st.sidebar.error("⚠️ Library TA tidak terinstall (pip install ta)")

# ======== Fungsi Utama dengan Error Handling ========
def muat_portofolio(filename="portfolio.json"):
    """Memuat data portofolio dari file JSON"""
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        st.error(f"❌ Gagal memuat portofolio: {str(e)}")
        return {}

def simpan_portofolio(data, filename="portfolio.json"):
    """Menyimpan data portofolio ke file JSON"""
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        st.error(f"❌ Gagal menyimpan portofolio: {str(e)}")

def ambil_data_saham(ticker):
    """Mengambil data saham dari Yahoo Finance"""
    if not YFINANCE_ENABLED:
        return pd.DataFrame(), {}
    
    try:
        saham = yf.Ticker(ticker)
        hist = saham.history(period="1y")
        info = saham.info
        return hist, info
    except Exception as e:
        st.error(f"❌ Gagal mengambil data {ticker}: {str(e)}")
        return pd.DataFrame(), {}

def format_rupiah(nilai):
    """Memformat angka menjadi format mata uang Rupiah"""
    return f"Rp{round(nilai):,}".replace(",", ".")

def tampilkan_status_sistem():
    """Menampilkan panel status dependency"""
    with st.expander("ℹ️ Status Sistem", expanded=True):
        st.write(f"**yfinance:** {'✅' if YFINANCE_ENABLED else '❌'}")
        st.write(f"**Technical Analysis:** {'✅' if TA_ENABLED else '❌'}")
        
        if not YFINANCE_ENABLED:
            st.warning("Fitur utama tidak tersedia tanpa yfinance")

# ======== Antarmuka Aplikasi ========
def main():
    st.title("📊 Aplikasi Analisis Portofolio Saham")
    
    # Sidebar - Manajemen Portofolio
    st.sidebar.header("Manajemen Portofolio")
    portofolio = muat_portofolio()
    
    with st.sidebar.form("tambah_saham"):
        st.write("**Tambahkan Saham Baru**")
        ticker = st.text_input("Kode Saham (contoh: AAPL, BBCA.JK)", key="input_ticker").upper().strip()
        lot = st.number_input("Jumlah Lot", min_value=1, step=1, key="input_lot")
        harga_per_lembar = st.number_input("Harga per Lembar (Rp)", min_value=1, step=100, key="input_harga")
        
        if st.form_submit_button("💾 Simpan"):
            if ticker:
                # Simpan data saham dalam format dictionary yang lebih lengkap
                if ticker not in portofolio:
                    portofolio[ticker] = {
                        'lot': 0,
                        'harga_per_lembar': 0,
                        'total_investasi': 0
                    }
                
                portofolio[ticker]['lot'] += lot
                portofolio[ticker]['harga_per_lembar'] = harga_per_lembar
                portofolio[ticker]['total_investasi'] += lot * 100 * harga_per_lembar  # 1 lot = 100 lembar
                
                simpan_portofolio(portofolio)
                st.success(f"Berhasil menambahkan {ticker}")
            else:
                st.error("Kode saham tidak boleh kosong")

    # Status Sistem
    tampilkan_status_sistem()
    
    # Konten Utama
    st.header("Portofolio Saat Ini")
    
    if not portofolio:
        st.info("Belum ada saham dalam portofolio. Silakan tambahkan saham dari sidebar.")
        return
    
    for ticker, data in portofolio.items():
        lot = data['lot']
        harga_per_lembar = data.get('harga_per_lembar', 0)
        total_investasi = data.get('total_investasi', 0)
        
        with st.expander(f"📈 {ticker} ({lot} lot)", expanded=True):
            if not YFINANCE_ENABLED:
                st.error("Tidak bisa mengambil data: yfinance tidak tersedia")
                continue
                
            hist, info = ambil_data_saham(ticker)
            if hist.empty:
                st.warning(f"Data historis untuk {ticker} tidak tersedia")
                continue
                
            # Tampilkan data dasar
            col1, col2, col3 = st.columns(3)
            col1.metric("Harga Terakhir", format_rupiah(hist['Close'].iloc[-1]))
            col2.metric("Harga Beli", format_rupiah(harga_per_lembar))
            col3.metric("Total Investasi", format_rupiah(total_investasi))
            
            if info:
                st.write(f"**Industri:** {info.get('industry', 'N/A')}")
            
            # Tampilkan grafik harga
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hist.index,
                y=hist['Close'],
                name="Harga Penutupan"
            ))
            fig.update_layout(
                title=f"Performa {ticker}",
                xaxis_title="Tanggal",
                yaxis_title="Harga (Rp)",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Tampilkan indikator teknikal jika tersedia
            if TA_ENABLED:
                st.subheader("Analisis Teknikal")
                df_teknikal = hist.copy()
                df_teknikal['RSI'] = RSIIndicator(df_teknikal['Close'], window=14).rsi()
                
                fig_rsi = go.Figure()
                fig_rsi.add_trace(go.Scatter(
                    x=df_teknikal.index,
                    y=df_teknikal['RSI'],
                    name="RSI 14"
                ))
                fig_rsi.update_layout(height=300)
                st.plotly_chart(fig_rsi, use_container_width=True)

if __name__ == "__main__":
    main()
