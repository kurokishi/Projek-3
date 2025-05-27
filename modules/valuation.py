import streamlit as st

def get_valuation_metrics(ticker):
    return {
        "Price": 1000,
        "PER": 12.5,
        "PBV": 1.8,
        "Dividend Yield": "3.2%",
        "DCF": 1100
    }

def display_valuation(df):
    st.subheader("Valuasi Saham")
    for _, row in df.iterrows():
        ticker = row['ticker']
        st.markdown(f"**{ticker}**")
        val = get_valuation_metrics(ticker)
        for k, v in val.items():
            st.write(f"{k}: {v}")
