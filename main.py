import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
import json
import os

st.set_page_config(layout="wide", page_title="Analisis Portofolio Saham")

# ======= Fungsi Pembantu =======

def muat_portofolio(filename="portfolio.json"):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    else:
        return {}

def simpan_portofolio(data, filename="portfolio.json"):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

def ambil_data_saham(ticker):
    saham = yf.Ticker(ticker)
    hist = saham.history(period="1y")
    info = saham.info
    return hist, info

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
    fig = go.Figure(data=[go.Candlestick(x=df.index,
                                         open=df['Open'],
                                         high=df['High'],
                                         low=df['Low'],
                                         close=df['Close'],
                                         name=ticker),
                          go.Bar(x=df.index, y=df['Volume'], name="Volume", yaxis="y2")])
    fig.update_layout(
        yaxis=dict(title="Harga"),
        yaxis2=dict(title="Volume", overlaying='y', side='right', showgrid=False, position=0.15),
        xaxis_rangeslider_visible=False,
        height=500,
        margin=dict(t=30, b=0)
    )
    return fig

def golden_death_cross(ma50, ma200):
    if len(ma50) < 2 or len(ma200) < 2:
        return "Data tidak cukup"
    if ma50.iloc[-2] < ma200.iloc[-2] and ma50.iloc[-1] > ma200.iloc[-1]:
        return "Golden Cross"
    elif ma50.iloc[-2] > ma200.iloc[-2] and ma50.iloc[-1] < ma200.iloc[-1]:
        return "Death Cross"
    else:
        return "Tidak ada sinyal"

# ==== Antarmuka Streamlit ====

st.title("📈 Aplikasi Analisis Portofolio Saham")

portofolio = muat_portofolio()

# --- Sidebar: Manajemen Portofolio ---
st.sidebar.header("Kelola Portofolio")

with st.sidebar.form("form_portofolio", clear_on_submit=True):
    input_ticker = st.text_input("Tambahkan Kode Saham (contoh: AAPL, BBCA.JK)").upper().strip()
    input_lot = st.number_input("Jumlah Lot", min_value=1, step=1)
    tombol_tambah = st.form_submit_button("Tambah/Perbarui Saham")
    if tombol_tambah and input_ticker:
        if input_ticker in portofolio:
            portofolio[input_ticker] += input_lot
        else:
            portofolio[input_ticker] = input_lot
        simpan_portofolio(portofolio)
        st.sidebar.success(f"Menambahkan/memperbarui {input_lot} lot saham {input_ticker}")

st.sidebar.write("---")
st.sidebar.subheader("Portofolio Saat Ini")
for t, s in portofolio.items():
    col1, col2 = st.sidebar.columns([3,1])
    col1.write(f"{t}")
    col2.write(f"{s} lot")
hapus_ticker = st.sidebar.text_input("Hapus Saham")
if st.sidebar.button("Hapus Saham"):
    ticker_upper = hapus_ticker.upper()
    if ticker_upper in portofolio:
        portofolio.pop(ticker_upper)
        simpan_portofolio(portofolio)
        st.sidebar.success(f"Menghapus {ticker_upper} dari portofolio")
    else:
        st.sidebar.error("Saham tidak ditemukan dalam portofolio")

# --- Panel Utama: Analisis Portofolio ---

if not portofolio:
    st.info("Portofolio Anda kosong. Silakan tambahkan saham dari sidebar.")
    st.stop()

st.header("Analisis Portofolio Saham")

ringkasan = []
for ticker, lot in portofolio.items():
    st.subheader(f"{ticker} - {lot} lot")
    hist, info = ambil_data_saham(ticker)
    if hist.empty:
        st.warning(f"Tidak ada data historis untuk {ticker}")
        continue

    # Data fundamental (beberapa bisa kosong)
    per = info.get('trailingPE', None)
    forward_per = info.get('forwardPE', None)
    pbv = info.get('priceToBook', None)
    div_yield = info.get('dividendYield', None)
    industri = info.get('industry', 'Tidak tersedia')

    st.write(f"**Industri:** {industri}")
    st.write(f"PER (Trailing): {per if per else 'Tidak tersedia'}")
    st.write(f"PER (Forward): {forward_per if forward_per else 'Tidak tersedia'}")
    st.write(f"PBV: {pbv if pbv else 'Tidak tersedia'}")
    st.write(f"Dividen Yield: {div_yield if div_yield else 'Tidak tersedia'}")

    # Indikator teknikal
    df = hitung_indikator_teknikal(hist)
    cross = golden_death_cross(df['MA_50'], df['MA_200'])
    st.write(f"Status Golden/Death Cross: **{cross}**")
    st.line_chart(df[['RSI_14']].dropna())
    st.line_chart(df[['MACD', 'MACD_signal']].dropna())

    # Candlestick
    timeframe = st.selectbox("Pilih Periode Candlestick", ["1 Bulan", "3 Bulan", "1 Tahun"], key=f"timeframe_{ticker}")
    days_map = {"1 Bulan": 22, "3 Bulan": 66, "1 Tahun": 252}
    plot_df = df.tail(days_map[timeframe])
    fig = plot_candlestick(plot_df, ticker)
    st.plotly_chart(fig, use_container_width=True)

    harga_terakhir = hist['Close'][-1]
    nilai_investasi = lot * 100 * harga_terakhir  # 1 lot = 100 lembar
    ringkasan.append({
        "Saham": ticker,
        "Lot": lot,
        "Harga (Rp)": harga_terakhir,
        "Nilai Investasi (Rp)": nilai_investasi,
        "Dividen Yield": div_yield if div_yield else 0
    })

# --- Ringkasan Portofolio ---
st.header("Ringkasan Portofolio")
ringkasan_df = pd.DataFrame(ringkasan)
total_nilai = ringkasan_df['Nilai Investasi (Rp)'].sum()
ringkasan_df['Persentase Portofolio (%)'] = (ringkasan_df['Nilai Investasi (Rp)'] / total_nilai * 100).round(2)

# Format mata uang Rupiah
def format_rupiah(x):
    return "Rp {:,.2f}".format(x).replace(",", "X").replace(".", ",").replace("X", ".")

ringkasan_df['Harga (Rp)'] = ringkasan_df['Harga (Rp)'].apply(format_rupiah)
ringkasan_df['Nilai Investasi (Rp)'] = ringkasan_df['Nilai Investasi (Rp)'].apply(format_rupiah)

st.dataframe(ringkasan_df)
st.write(f"**Total Nilai Portofolio: {format_rupiah(total_nilai)}**")

# --- Modal Baru & Rekomendasi Alokasi ---
st.header("Tambahan Modal & Rekomendasi Alokasi")

modal = st.number_input("Modal Tambahan (Rp)", min_value=0, step=100000)
profil_risiko = st.selectbox("Profil Risiko", ["Konservatif", "Moderat", "Agresif"])

if st.button("Dapatkan Rekomendasi") and modal > 0:
    # Rekomendasi sederhana: alokasikan ke 3 saham dengan dividend yield tertinggi
    saham_terurut = sorted(ringkasan, key=lambda x: x['Dividen Yield'], reverse=True)
    top3 = saham_terurut[:3]

    if profil_risiko == "Konservatif":
        bobot = [0.6, 0.3, 0.1]
    elif profil_risiko == "Moderat":
        bobot = [0.5, 0.3, 0.2]
    else:
        bobot = [0.4, 0.3, 0.3]

    st.subheader("3 Saham Rekomendasi Teratas")
    alokasi = []
    for i, saham in enumerate(top3):
        alok = modal * bobot[i]
        alokasi.append({"Saham": saham['Saham'], "Alokasi (Rp)": alok})
        st.write(f"{saham['Saham']} - Alokasi: {format_rupiah(alok)}")

    alokasi_df = pd.DataFrame(alokasi)
    alokasi_df['Alokasi (Rp)'] = alokasi_df['Alokasi (Rp)'].apply(format_rupiah)
    st.table(alokasi_df)

# --- Simulasi Bunga Majemuk ---
st.header("Simulasi Bunga Majemuk & Proyeksi Portofolio")

tahun = st.slider("Periode Proyeksi (tahun)", 3, 10, 5)
cagr = st.number_input("Tingkat Pertumbuhan Tahunan (CAGR %) per tahun", min_value=0.0, max_value=50.0, value=10.0, step=0.1)
reinvest_div = st.radio("Reinvestasi Dividen?", ("Ya", "Tidak")) == "Ya"

nilai_awal = total_nilai
nilai_proyeksi = []
# Hitung rata-rata dividend yield portofolio
rata_dividen = (ringkasan_df['Dividen Yield'] * ringkasan_df['Persentase Portofolio (%)'] / 100).sum()

for tahun_ke in range(1, tahun+1):
    if reinvest_div:
        nilai_awal *= (1 + (cagr / 100) + rata_dividen)
    else:
        nilai_awal *= (1 + (cagr / 100))
    nilai_proyeksi.append(nilai_awal)

proyeksi_df = pd.DataFrame({
    "Tahun": list(range(1, tahun+1)),
    "Nilai Portofolio (Rp)": nilai_proyeksi
})

proyeksi_df['Nilai Portofolio (Rp)'] = proyeksi_df['Nilai Portofolio (Rp)'].apply(format_rupiah)
st.line_chart(pd.DataFrame({
    "Tahun": list(range(1, tahun+1)),
    "Nilai Portofolio": nilai_proyeksi
}).set_index('Tahun'))
