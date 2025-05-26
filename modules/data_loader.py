def load_portfolio(tickers, lots):
    return pd.DataFrame({
        "ticker": tickers,
        "lot": lots
    })
