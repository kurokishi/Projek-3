import streamlit as st
st.set_page_config(page_title="Analisis Saham", layout="wide")

import yfinance as yf
def format_rupiah(x):
    try:
        return f"Rp{x:,.0f}".replace(",", ".")
    except:
        return "Rp0"

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler

# Inisialisasi session state
if 'portofolio' not in st.session_state:
    st.session_state.portofolio = {}

# ======= FORM INPUT PORTOFOLIO =======
st.sidebar.header("📝 Input Saham Anda")

with st.sidebar.form("input_saham_form"):
    kode = st.text_input("Kode Saham (misal: UNVR)", "")
    jumlah = st.number_input("Jumlah Lot", min_value=1, value=1)
    harga_beli = st.number_input("Harga Beli per Lembar", min_value=1, value=1000)
    submit = st.form_submit_button("Tambah ke Portofolio")

if submit and kode:
    total_saham = jumlah * 100
    st.session_state.portofolio[kode.upper()] = total_saham
    st.success(f"{total_saham} lembar saham {kode.upper()} berhasil ditambahkan.")

# ======= FUNGSI ANALISIS LANJUTAN =======

def analisis_valuasi_mendalam(info, harga_terakhir):
    hasil = {
        'PER_vs_Industri': 'N/A',
        'Margin_Keamanan': 'N/A',
        'Nilai_Intrinsik': 'N/A'
    }

    try:
        avg_industry_pe = info.get('industryPe', None)
        current_pe = info.get('trailingPE', None)

        if current_pe and avg_industry_pe:
            selisih = ((current_pe - avg_industry_pe) / avg_industry_pe) * 100
            hasil['PER_vs_Industri'] = f"{'Di bawah' if selisih < 0 else 'Di atas'} rata-rata industri ({selisih:.1f}%)"

        growth = info.get('earningsGrowth', 0.05)
        div = info.get('dividendRate', 0)
        discount_rate = 0.1

        if growth and div:
            nilai_intrinsik = div / (discount_rate - growth)
            margin_keamanan = ((nilai_intrinsik - harga_terakhir) / harga_terakhir) * 100
            hasil['Nilai_Intrinsik'] = format_rupiah(nilai_intrinsik)
            hasil['Margin_Keamanan'] = f"{margin_keamanan:.1f}%"

    except Exception as e:
        st.error(f"Error valuasi: {str(e)}")

    return hasil

def prediksi_harga_lstm(df, periode=30):
    try:
        from keras.models import Sequential
        from keras.layers import LSTM, Dense

        scaler = MinMaxScaler()
        data = scaler.fit_transform(df['Close'].values.reshape(-1,1))

        X, y = [], []
        for i in range(periode, len(data)):
            X.append(data[i-periode:i, 0])
            y.append(data[i, 0])

        X, y = np.array(X), np.array(y)
        X = np.reshape(X, (X.shape[0], X.shape[1], 1))

        model = Sequential()
        model.add(LSTM(50, return_sequences=True, input_shape=(X.shape[1], 1)))
        model.add(LSTM(50))
        model.add(Dense(1))
        model.compile(optimizer='adam', loss='mean_squared_error')

        model.fit(X, y, epochs=10, batch_size=32, verbose=0)

        inputs = data[-periode:]
        inputs = scaler.transform(inputs)

        X_test = np.array([inputs])
        X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))

        pred = model.predict(X_test)
        pred = scaler.inverse_transform(pred)[0][0]

        return pred
    except Exception as e:
        st.warning(f"Prediksi LSTM gagal: {str(e)}")
        return None

def scrape_sentimen(ticker):
    try:
        berita = {
            'judul': [],
            'sentimen': []
        }

        sample_news = [
            ("Laba {ticker} tumbuh 20% di Q3 2023", "positif"),
            ("{ticker} hadapi risiko regulasi baru", "negatif")
        ]

        for judul, sentimen in sample_news:
            berita['judul'].append(judul.format(ticker=ticker))
            berita['sentimen'].append(sentimen)

        return berita
    except:
        return None

# ======= TABEL PORTOFOLIO PENGGUNA =======
portofolio = st.session_state.portofolio

# Struktur portofolio: { 'UNVR': {'jumlah': 300, 'harga_beli': 4500} }
# Update struktur jika hanya berisi angka (lama)
for kode, data in portofolio.items():
    if isinstance(data, int):
        portofolio[kode] = {'jumlah': data, 'harga_beli': 1000}

# Ambil harga pasar terbaru
def ambil_harga_terakhir(ticker):
    try:
        ticker_obj = yf.Ticker(ticker + ".JK")
        harga_terakhir = ticker_obj.info.get("regularMarketPrice")
        return harga_terakhir
    except:
        return None
if portofolio:
    data_porto = []
    for kode, data in portofolio.items():
        jumlah = data['jumlah']
        harga_beli = data['harga_beli']
        total = jumlah * harga_beli
        harga_now = ambil_harga_terakhir(kode)
        data_porto.append({
            'Kode Saham': kode,
            'Jumlah Lembar': jumlah,
            'Harga Beli': format_rupiah(harga_beli),
            'Total Investasi': format_rupiah(total),
            'Harga Terakhir': format_rupiah(harga_now) if harga_now else 'N/A',
            'Keuntungan/Rugi (%)': f"{((harga_now - harga_beli) / harga_beli * 100):.2f}%" if harga_now else 'N/A'
        })
    df_porto = pd.DataFrame(data_porto)
    st.subheader("📋 Portofolio Saat Ini")
    st.dataframe(df_porto, use_container_width=True)
else:
    st.info("Portofolio kosong. Silakan masukkan data di sidebar.")

def format_rupiah(x):
    try:
        return f"Rp{x:,.0f}".replace(",", ".")
    except:
        return "Rp0"

# ======= START APLIKASI STREAMLIT =======
st.title("📈 Aplikasi Analisis Saham Kurokishi")
st.write("Selamat datang! Silakan eksplorasi fitur analisis saham di bawah.")

portofolio = st.session_state.portofolio

# Dummy total nilai awal
total_nilai = 100_000_000

def format_rupiah(x):
    return f"Rp{x:,.0f}".replace(",", ".")

st.success("Portofolio berhasil dimuat.")
        
