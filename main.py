import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import plotly.graph_objects as go
from datetime import datetime, timedelta
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
import openai

# --- Helper Functions ---

PORTFOLIO_FILE = 'portfolio.json'

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_portfolio(data):
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def fetch_fundamental(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    # Basic fundamental data, fallback jika tidak ada:
    try:
        per = info.get('trailingPE', None)
        forward_per = info.get('forwardPE', None)
        pbv = info.get('priceToBook', None)
        div_yield = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
    except:
        per = forward_per = pbv = div_yield = None
    return {'PER': per, 'ForwardPER': forward_per, 'PBV': pbv, 'DividendYield': div_yield}

def fetch_price_data(ticker, period='1y'):
    df = yf.download(ticker, period=period, interval='1d')
    if df.empty:
        return None
    return df

def compute_technical_indicators(df):
    df = df.copy()
    df['RSI'] = RSIIndicator(df['Close'], window=14).rsi()
    macd = MACD(df['Close'], window_slow=26, window_fast=12, window_sign=9)
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['MA50'] = SMAIndicator(df['Close'], window=50).sma_indicator()
    df['MA200'] = SMAIndicator(df['Close'], window=200).sma_indicator()
    return df

def detect_golden_death_cross(df):
    cross = None
    if df['MA50'].iloc[-2] < df['MA200'].iloc[-2] and df['MA50'].iloc[-1] > df['MA200'].iloc[-1]:
        cross = 'Golden Cross'
    elif df['MA50'].iloc[-2] > df['MA200'].iloc[-2] and df['MA50'].iloc[-1] < df['MA200'].iloc[-1]:
        cross = 'Death Cross'
    return cross

def generate_candlestick_chart(df, title='Candlestick Chart'):
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        increasing_line_color='green',
        decreasing_line_color='red',
        name='Price'
    )])
    fig.update_layout(title=title, xaxis_rangeslider_visible=False)
    return fig

def openai_commentary(fundamental, technical, ticker):
    # Contoh sederhana, gunakan openai API key environment variable: OPENAI_API_KEY
    openai.api_key = st.secrets.get('OPENAI_API_KEY', None)
    if not openai.api_key:
        return "OpenAI API key tidak disediakan."

    prompt = (
        f"Berikan ringkasan analisis saham {ticker} berdasarkan data fundamental {fundamental} "
        f"dan data teknikal {technical}. Klasifikasikan apakah saham ini Undervalued, Fairly Valued, atau Overvalued, "
        "dan berikan rekomendasi Strong Buy, Hold, atau Sell dengan skala 1 sampai 5."
    )

    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].text.strip()
    except Exception as e:
        return f"Error OpenAI API: {e}"

def simulate_compound_growth(initial_value, annual_return, years, dividend_yield=0, reinvest_dividend=True):
    values = []
    total = initial_value
    for year in range(years+1):
        if year == 0:
            values.append(total)
            continue
        growth = total * annual_return
        dividend = total * dividend_yield if reinvest_dividend else 0
        total += growth + dividend
        values.append(total)
    return values

# --- Streamlit App ---

st.title("Aplikasi Analisis dan Manajemen Portofolio Saham")

# --- Load Portfolio ---
portfolio = load_portfolio()

# Sidebar for CRUD portofolio
st.sidebar.header("Manajemen Portofolio")
with st.sidebar.form("portfolio_form", clear_on_submit=True):
    st.write("Tambah Saham Baru")
    new_ticker = st.text_input("Kode Saham (contoh: AAPL, TLKM.JK)")
    new_lot = st.number_input("Jumlah Lot", min_value=1, step=1)
    submitted = st.form_submit_button("Tambah")
    if submitted:
        if new_ticker and new_lot > 0:
            portfolio[new_ticker.upper()] = {"lot": new_lot}
            save_portfolio(portfolio)
            st.sidebar.success(f"Saham {new_ticker.upper()} ditambahkan dengan {new_lot} lot.")
        else:
            st.sidebar.error("Isi semua field dengan benar.")

if portfolio:
    st.subheader("Portofolio Saham Anda")
    df_port = pd.DataFrame([
        {"Ticker": k, "Lot": v["lot"]}
        for k, v in portfolio.items()
    ])
    st.table(df_port)

    # Pilih saham untuk analisis
    selected_ticker = st.selectbox("Pilih saham untuk analisis detail", list(portfolio.keys()))

    if selected_ticker:
        st.markdown(f"## Analisis Saham: {selected_ticker}")

        # Ambil data fundamental & harga
        fundamental = fetch_fundamental(selected_ticker)
        st.write("### Fundamental:")
        st.json(fundamental)

        price_data = fetch_price_data(selected_ticker, period='1y')
        if price_data is None:
            st.error("Data harga tidak ditemukan.")
        else:
            st.write("### Chart Candlestick 1 Tahun")
            candle_fig = generate_candlestick_chart(price_data)
            st.plotly_chart(candle_fig, use_container_width=True)

            # Hitung indikator teknikal
            tech_df = compute_technical_indicators(price_data)
            st.write("### Indikator Teknikal:")
            st.write(f"RSI terbaru: {tech_df['RSI'].iloc[-1]:.2f}")
            st.write(f"MACD terbaru: {tech_df['MACD'].iloc[-1]:.4f}, Signal: {tech_df['MACD_signal'].iloc[-1]:.4f}")
            st.write(f"MA50: {tech_df['MA50'].iloc[-1]:.2f}, MA200: {tech_df['MA200'].iloc[-1]:.2f}")

            cross = detect_golden_death_cross(tech_df)
            if cross:
                st.info(f"Terdeteksi: {cross}")

            # AI Commentary
            if st.button("Dapatkan AI Commentary"):
                comment = openai_commentary(fundamental, {
                    'RSI': tech_df['RSI'].iloc[-1],
                    'MACD': tech_df['MACD'].iloc[-1],
                    'MACD_signal': tech_df['MACD_signal'].iloc[-1],
                    'MA50': tech_df['MA50'].iloc[-1],
                    'MA200': tech_df['MA200'].iloc[-1],
                }, selected_ticker)
                st.write(comment)

# --- Alokasi Modal Baru ---
st.header("Rekomendasi Alokasi Modal Baru")

modal_baru = st.number_input("Masukkan Modal Tambahan (Rp)", min_value=100000, step=100000, value=5000000)
risk_profile = st.selectbox("Pilih Profil Risiko", ["Conservative", "Moderate", "Aggressive"])

if st.button("Hitung Rekomendasi Alokasi"):
    # Dummy data rekomendasi saham (harus dikembangkan untuk kalkulasi nyata)
    rekomendasi = [
        {"Ticker": "AAPL", "MOS": 0.3, "DividendGrowth": 0.05, "RSI": 45, "MACD_bullish": True},
        {"Ticker": "MSFT", "MOS": 0.25, "DividendGrowth": 0.04, "RSI": 40, "MACD_bullish": True},
        {"Ticker": "GOOG", "MOS": 0.2, "DividendGrowth": 0.0, "RSI": 48, "MACD_bullish": True},
    ]

    df_rekom = pd.DataFrame(rekomendasi)
    df_rekom = df_rekom.sort_values(by=['MOS', 'DividendGrowth'], ascending=False).head(3)
    
    st.write("### Top 3 Rekomendasi Saham:")
    st.table(df_rekom)

    # Alokasi modal (distribusi sederhana)
    total_mos = df_rekom['MOS'].sum()
    df_rekom['Alokasi (%)'] = df_rekom['MOS'] / total_mos * 100
    df_rekom['Alokasi (Rp)'] = df_rekom['Alokasi (%)'] / 100 * modal_baru

    st.write("### Alokasi Modal Optimal:")
    st.table(df_rekom[['Ticker', 'Alokasi (%)', 'Alokasi (Rp)']])

# --- Simulasi Bunga Majemuk ---
st.header("Simulasi Proyeksi Portofolio")

cagr_input = st.number_input("Asumsi CAGR Tahunan (%)", min_value=0.0, max_value=100.0, value=10.0)
dividend_yield_input = st.number_input("Asumsi Dividend Yield (%)", min_value=0.0, max_value=20.0, value=2.0)
reinvest_div = st.checkbox("Reinvest Dividen?", value=True)
years = st.slider("Jangka Waktu (tahun)", min_value=3, max_value=20, value=10)

if st.button("Hitung Proyeksi"):
    initial_val = 10000000  # Contoh nilai awal portofolio
    values = simulate_compound_growth(
        initial_val,
        cagr_input / 100,
        years,
        dividend_yield=dividend_yield_input / 100,
        reinvest_dividend=reinvest_div
    )
    st.line_chart(pd.DataFrame({'Proyeksi Nilai Portofolio (Rp)': values}))

st.write("---")
st.write("Aplikasi ini masih prototipe, silakan kembangkan fitur lanjutannya.")

