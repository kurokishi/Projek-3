import pandas as pd
import plotly.graph_objects as go
import ta  # library TA murni Python

def calculate_technical_indicators(data):
    # Pastikan format kolom sesuai
    data = data.copy()
    data = data.rename(columns={"close": "Close", "volume": "Volume"})

    # Inisialisasi indikator
    rsi = ta.momentum.RSIIndicator(close=data["Close"], window=14)
    macd = ta.trend.MACD(close=data["Close"])
    ma50 = ta.trend.SMAIndicator(close=data["Close"], window=50)
    ma200 = ta.trend.SMAIndicator(close=data["Close"], window=200)

    # Tambahkan ke DataFrame
    data["RSI"] = rsi.rsi()
    data["MACD"] = macd.macd()
    data["Signal"] = macd.macd_signal()
    data["MA50"] = ma50.sma_indicator()
    data["MA200"] = ma200.sma_indicator()

    return data

def plot_candlestick_chart(data, ticker):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=data['date'],
        open=data['open'],
        high=data['high'],
        low=data['low'],
        close=data['close'],
        name="Candlestick"
    ))

    if "MA50" in data.columns:
        fig.add_trace(go.Scatter(
            x=data['date'], y=data['MA50'],
            line=dict(color='blue', width=1),
            name='MA50'
        ))

    if "MA200" in data.columns:
        fig.add_trace(go.Scatter(
            x=data['date'], y=data['MA200'],
            line=dict(color='orange', width=1),
            name='MA200'
        ))

    fig.update_layout(
        title=f"Candlestick Chart: {ticker}",
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        template="plotly_white"
    )

    return fig
