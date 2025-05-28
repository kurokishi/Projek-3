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
            data = json.load(f)
            # Migrasi otomatis dari format lama ke format baru
            if data and isinstance(next(iter(data.values())), (int, float)):
                data = {ticker: {"lot": lot, "harga_beli": None} for ticker, lot in data.items()}
                # Simpan format baru
                with open(filename, "w") as f:
                    json.dump(data, f, indent=2)
            return data
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

def format_rupiah(x):
    return "Rp {:,.2f}".format(x).replace(",", "X").replace(".", ",").replace("X", ".")

# ==== Antarmuka Streamlit ====

st.title("📈 Aplikasi Analisis Portofolio Saham")

portofolio = muat_portofolio()

# --- Sidebar: Manajemen Portofolio ---
st.sidebar.header("Kelola Portofolio")

with st.sidebar.form("form_portofolio", clear_on_submit=True):
    input_ticker = st.text_input("Tambahkan Kode Saham (contoh: AAPL, BBCA.JK)").upper().strip()
    input_lot = st.number_input("Jumlah Lot", min_value=1, step=1)
    input_harga = st.number_input("Harga Beli per Lembar", min_value=0.0, step=0.01, format="%.2f")
    tombol_tambah = st.form_submit_button("Tambah/Perbarui Saham")
    
    if tombol_tambah and input_ticker:
        if input_ticker in portofolio:
            # Hitung harga beli rata-rata tertimbang
            total_lot_sekarang = portofolio[input_ticker]["lot"] + input_lot
            total_nilai_sebelum = portofolio[input_ticker]["harga_beli"] * portofolio[input_ticker]["lot"] * 100 if portofolio[input_ticker]["harga_beli"] else 0
            total_nilai_tambah = input_harga * input_lot * 100
            harga_rata_rata = (total_nilai_sebelum + total_nilai_tambah) / (total_lot_sekarang * 100)
            
            portofolio[input_ticker]["lot"] = total_lot_sekarang
            portofolio[input_ticker]["harga_beli"] = harga_rata_rata
        else:
            portofolio[input_ticker] = {
                "lot": input_lot,
                "harga_beli": input_harga
            }
        simpan_portofolio(portofolio)
        st.sidebar.success(f"Menambahkan/memperbarui {input_lot} lot saham {input_ticker} @ {format_rupiah(input_harga)}")

st.sidebar.write("---")
st.sidebar.subheader("Portofolio Saat Ini")
for t, data in portofolio.items():
    col1, col2, col3 = st.sidebar.columns([3,1,2])
    col1.write(f"{t}")
    col2.write(f"{data['lot']} lot")
    col3.write(f"@{format_rupiah(data['harga_beli']) if data['harga_beli'] else '-'}")

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
for ticker, data in portofolio.items():
    lot = data["lot"]
    harga_beli = data["harga_beli"]
    
    st.subheader(f"{ticker} - {lot} lot")
    hist, info = ambil_data_saham(ticker)
    if hist.empty:
        st.warning(f"Tidak ada data historis untuk {ticker}")
        continue

    # Data fundamental
    per = info.get('trailingPE', None)
    forward_per = info.get('forwardPE', None)
    pbv = info.get('priceToBook', None)
    div_yield = info.get('dividendYield', None)
    industri = info.get('industry', 'Tidak tersedia')

    st.write(f"**Industri:** {industri}")
    st.write(f"PER (Trailing): {per if per else 'Tidak tersedia'}")
    st.write(f"PER (Forward): {forward_per if forward_per else 'Tidak tersedia'}")
    st.write(f"PBV: {pbv if pbv else 'Tidak tersedia'}")
    st.write(f"Dividen Yield: {div_yield*100 if div_yield else '0'}%")

    # Indikator teknikal
    df = hitung_indikator_teknikal(hist)
    cross = golden_death_cross(df['MA_50'], df['MA_200'])
    st.write(f"Status Golden/Death Cross: **{cross}**")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**RSI 14 Hari**")
        st.line_chart(df[['RSI_14']].dropna())
    with col2:
        st.write("**MACD**")
        st.line_chart(df[['MACD', 'MACD_signal']].dropna())

    # Candlestick
    timeframe = st.selectbox("Pilih Periode Candlestick", ["1 Bulan", "3 Bulan", "1 Tahun"], key=f"timeframe_{ticker}")
    days_map = {"1 Bulan": 22, "3 Bulan": 66, "1 Tahun": 252}
    plot_df = df.tail(days_map[timeframe])
    fig = plot_candlestick(plot_df, ticker)
    st.plotly_chart(fig, use_container_width=True)

    harga_terakhir = hist['Close'][-1]
    nilai_investasi = lot * 100 * harga_terakhir
    nilai_beli = lot * 100 * harga_beli if harga_beli else nilai_investasi
    untung_rugi = nilai_investasi - nilai_beli
    persen_untung = (untung_rugi / nilai_beli * 100) if nilai_beli != 0 else 0
    
    ringkasan.append({
        "Saham": ticker,
        "Lot": lot,
        "Harga Beli (Rp)": harga_beli if harga_beli else harga_terakhir,
        "Harga Sekarang (Rp)": harga_terakhir,
        "Nilai Investasi (Rp)": nilai_investasi,
        "Untung/Rugi (Rp)": untung_rugi,
        "% Untung/Rugi": persen_untung,
        "Dividen Yield": div_yield if div_yield else 0
    })

# --- Ringkasan Portofolio ---
st.header("Ringkasan Portofolio")
ringkasan_df = pd.DataFrame(ringkasan)
total_nilai = ringkasan_df['Nilai Investasi (Rp)'].sum()
total_beli = ringkasan_df['Harga Beli (Rp)'].mul(ringkasan_df['Lot'] * 100).sum()
total_untung = total_nilai - total_beli
persen_total_untung = (total_untung / total_beli * 100) if total_beli != 0 else 0

ringkasan_df['Persentase Portofolio (%)'] = (ringkasan_df['Nilai Investasi (Rp)'] / total_nilai * 100).round(2)

# Format mata uang
ringkasan_df['Harga Beli (Rp)'] = ringkasan_df['Harga Beli (Rp)'].apply(format_rupiah)
ringkasan_df['Harga Sekarang (Rp)'] = ringkasan_df['Harga Sekarang (Rp)'].apply(format_rupiah)
ringkasan_df['Nilai Investasi (Rp)'] = ringkasan_df['Nilai Investasi (Rp)'].apply(format_rupiah)
ringkasan_df['Untung/Rugi (Rp)'] = ringkasan_df['Untung/Rugi (Rp)'].apply(format_rupiah)
ringkasan_df['% Untung/Rugi'] = ringkasan_df['% Untung/Rugi'].apply(lambda x: f"{x:.2f}%")

st.dataframe(ringkasan_df)
st.write(f"**Total Nilai Portofolio: {format_rupiah(total_nilai)}**")
st.write(f"**Total Keuntungan/Rugi: {format_rupiah(total_untung)} ({persen_total_untung:.2f}%)**")

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
        alokasi.append({
            "Saham": saham['Saham'],
            "Alokasi (Rp)": alok,
            "Lot yang bisa dibeli": int(alok // (saham['Harga Sekarang (Rp)'] * 100))
        })
        st.write(f"{saham['Saham']} - Alokasi: {format_rupiah(alok)} (~{int(alok // (saham['Harga Sekarang (Rp)'] * 100))} lot)")

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
