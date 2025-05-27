import streamlit as st
from .valuation_core import get_valuation_metrics  # jika Anda pisahkan fungsi

def display_valuation(df):
    st.subheader("Analisis Valuasi Saham")
    for _, row in df.iterrows():
        try:
            ticker = row["ticker"]
            st.markdown(f"**{ticker}**")
            metrics = get_valuation_metrics(ticker)
            for k, v in metrics.items():
                st.write(f"{k}: {v}")
        except Exception as e:
            st.error(f"Gagal analisis {ticker}: {e}")
