import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
import json
import os

st.set_page_config(layout="wide", page_title="Stock Portfolio Analysis")

# ======= Helper Functions =======

def load_portfolio(filename="portfolio.json"):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    else:
        return {}

def save_portfolio(data, filename="portfolio.json"):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

def fetch_stock_data(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1y")
    info = stock.info
    return hist, info

def calc_technical_indicators(df):
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
        yaxis=dict(title="Price"),
        yaxis2=dict(title="Volume", overlaying='y', side='right', showgrid=False, position=0.15),
        xaxis_rangeslider_visible=False,
        height=500,
        margin=dict(t=30, b=0)
    )
    return fig

def golden_death_cross(ma50, ma200):
    if len(ma50) < 2 or len(ma200) < 2:
        return "Not enough data"
    if ma50.iloc[-2] < ma200.iloc[-2] and ma50.iloc[-1] > ma200.iloc[-1]:
        return "Golden Cross"
    elif ma50.iloc[-2] > ma200.iloc[-2] and ma50.iloc[-1] < ma200.iloc[-1]:
        return "Death Cross"
    else:
        return "No Cross"

# ==== Streamlit UI ====

st.title("📈 Stock Portfolio Analysis App (Tanpa AI Commentary)")

portfolio = load_portfolio()

# --- Sidebar: Portfolio Management ---
st.sidebar.header("Manage Portfolio")

with st.sidebar.form("portfolio_form", clear_on_submit=True):
    ticker_input = st.text_input("Add Stock Ticker (e.g. AAPL, BBCA.JK)").upper().strip()
    shares_input = st.number_input("Number of Shares", min_value=1, step=1)
    submit_add = st.form_submit_button("Add / Update Stock")
    if submit_add and ticker_input:
        if ticker_input in portfolio:
            portfolio[ticker_input] += shares_input
        else:
            portfolio[ticker_input] = shares_input
        save_portfolio(portfolio)
        st.sidebar.success(f"Added/Updated {shares_input} shares of {ticker_input}")

st.sidebar.write("---")
st.sidebar.subheader("Current Portfolio")
for t, s in portfolio.items():
    col1, col2 = st.sidebar.columns([3,1])
    col1.write(f"{t}")
    col2.write(f"{s}")
remove_ticker = st.sidebar.text_input("Remove Stock Ticker")
if st.sidebar.button("Remove Stock"):
    ticker_upper = remove_ticker.upper()
    if ticker_upper in portfolio:
        portfolio.pop(ticker_upper)
        save_portfolio(portfolio)
        st.sidebar.success(f"Removed {ticker_upper} from portfolio")
    else:
        st.sidebar.error("Ticker not found in portfolio")

# --- Main Panel: Portfolio Analysis ---

if not portfolio:
    st.info("Your portfolio is empty. Please add stocks from sidebar.")
    st.stop()

st.header("Portfolio Holdings Analysis")

summary = []
for ticker, shares in portfolio.items():
    st.subheader(f"{ticker} - {shares} shares")
    hist, info = fetch_stock_data(ticker)
    if hist.empty:
        st.warning(f"No historical data for {ticker}")
        continue

    # Fundamental data (beberapa bisa kosong)
    per = info.get('trailingPE', None)
    forward_per = info.get('forwardPE', None)
    pbv = info.get('priceToBook', None)
    div_yield = info.get('dividendYield', None)
    industry = info.get('industry', 'N/A')

    st.write(f"**Industry:** {industry}")
    st.write(f"PER (Trailing): {per if per else 'N/A'}")
    st.write(f"PER (Forward): {forward_per if forward_per else 'N/A'}")
    st.write(f"PBV: {pbv if pbv else 'N/A'}")
    st.write(f"Dividend Yield: {div_yield if div_yield else 'N/A'}")

    # Technical indicators
    df = calc_technical_indicators(hist)
    cross = golden_death_cross(df['MA_50'], df['MA_200'])
    st.write(f"Golden/Death Cross Status: **{cross}**")
    st.line_chart(df[['RSI_14']].dropna())
    st.line_chart(df[['MACD', 'MACD_signal']].dropna())

    # Candlestick
    timeframe = st.selectbox("Select Candlestick Timeframe", ["1M", "3M", "1Y"], key=f"timeframe_{ticker}")
    days_map = {"1M": 22, "3M": 66, "1Y": 252}
    plot_df = df.tail(days_map[timeframe])
    fig = plot_candlestick(plot_df, ticker)
    st.plotly_chart(fig, use_container_width=True)

    last_price = hist['Close'][-1]
    summary.append({
        "Ticker": ticker,
        "Shares": shares,
        "Price": last_price,
        "Value": shares * last_price,
        "Dividend Yield": div_yield if div_yield else 0
    })

# --- Portfolio Summary ---
st.header("Portfolio Summary")
summary_df = pd.DataFrame(summary)
total_value = summary_df['Value'].sum()
summary_df['Portfolio %'] = (summary_df['Value'] / total_value * 100).round(2)
st.dataframe(summary_df)
st.write(f"**Total Portfolio Value: Rp {total_value:,.2f}**")

# --- Modal Baru & Alokasi Rekomendasi ---
st.header("Add Capital & Get Allocation Recommendation")

capital = st.number_input("Additional Capital (Rp)", min_value=0, step=100000)
risk_profile = st.selectbox("Risk Profile", ["Conservative", "Moderate", "Aggressive"])

if st.button("Get Recommendations") and capital > 0:
    # Simple dummy recommendation: alokasikan ke 3 saham dengan dividend yield tertinggi
    sorted_stocks = sorted(summary, key=lambda x: x['Dividend Yield'], reverse=True)
    top3 = sorted_stocks[:3]

    if risk_profile == "Conservative":
        weights = [0.6, 0.3, 0.1]
    elif risk_profile == "Moderate":
        weights = [0.5, 0.3, 0.2]
    else:
        weights = [0.4, 0.3, 0.3]

    st.subheader("Top 3 Recommended Stocks")
    allocs = []
    for i, stock in enumerate(top3):
        alloc = capital * weights[i]
        allocs.append({"Ticker": stock['Ticker'], "Allocation Rp": alloc})
        st.write(f"{stock['Ticker']} - Allocation: Rp {alloc:,.0f}")

    alloc_df = pd.DataFrame(allocs)
    st.table(alloc_df)

# --- Simulasi Bunga Majemuk ---
st.header("Compound Interest & Portfolio Projection")

years = st.slider("Projection Period (years)", 3, 10, 5)
cagr = st.number_input("Annual Growth Rate (CAGR %) per year", min_value=0.0, max_value=50.0, value=10.0, step=0.1)
reinvest_div = st.radio("Reinvest Dividends?", ("Yes", "No")) == "Yes"

initial_value = total_value
values = []
# Ambil rata-rata dividend yield portfolio
avg_dividend_pct = (summary_df['Dividend Yield'] * summary_df['Portfolio %'] / 100).sum()

for year in range(1, years+1):
    if reinvest_div:
        initial_value *= (1 + (cagr / 100) + avg_dividend_pct)
    else:
        initial_value *= (1 + (cagr / 100))
    values.append(initial_value)

proj_df = pd.DataFrame({
    "Year": list(range(1, years+1)),
    "Portfolio Value (Rp)": values
})

st.line_chart(proj_df.set_index('Year'))
