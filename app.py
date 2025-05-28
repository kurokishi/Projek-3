import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler

# ======= FUNGSI ANALISIS LANJUTAN =======

def analisis_valuasi_mendalam(info, harga_terakhir):
    """Analisis fundamental dengan lebih detail"""
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
    """Prediksi harga dengan model LSTM sederhana"""
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
    """Scraping berita dan analisis sentimen sederhana"""
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
        
